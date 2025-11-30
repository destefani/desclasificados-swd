"""
transcribe_v4.py
================
Multimodal batch transcription with **robust rate‑limit handling**
----------------------------------------------------------------
• Works with GPT‑4o‑mini (or GPT‑4o) vision endpoint.
• Guards against **RPS**, **concurrency**, and **TPM** limits.
• JSON schema validation + auto‑repair of common issues.
• Thread‑safe, resumable, configurable via CLI.
"""

import os
import base64
import argparse
import json
import logging
import time
import random
import re
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import openai
from dotenv import load_dotenv
from tqdm import tqdm
from jsonschema import Draft7Validator, ValidationError

# ---------------------------------------------------------------------------
# Environment + OpenAI client
# ---------------------------------------------------------------------------
from app.config import ROOT_DIR, DATA_DIR  # adjust if needed

load_dotenv(ROOT_DIR / '.env')
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_TEST_KEY"),
    max_retries=0,        # we implement our own
    timeout=120,
)

# ---------------------------------------------------------------------------
# Hard quotas – tune to match your org limits (see dashboard)
# ---------------------------------------------------------------------------
MAX_RPS          = 2                  # requests per second
MAX_CONCURRENT   = 3                  # simultaneous calls
MAX_TOKENS_MIN   = 180_000            # stay below 200k/min default
TOKENS_PER_CALL  = 4_000              # empirical cost of one vision prompt

# ---------------------------------------------------------------------------
# Rate + concurrency + TPM limiter
# ---------------------------------------------------------------------------
_rps_interval = 1.0 / MAX_RPS
_last_start   = 0.0
_rps_lock     = threading.Lock()

concurrency_sem = threading.Semaphore(MAX_CONCURRENT)

token_lock   = threading.Lock()
token_usage  = deque()  # (timestamp, tokens) for last 60 s

def _wait_for_rps_slot():
    global _last_start
    with _rps_lock:
        now = time.time()
        diff = now - _last_start
        if diff < _rps_interval:
            time.sleep(_rps_interval - diff)
        _last_start = time.time()


def _wait_for_token_budget():
    while True:
        with token_lock:
            now = time.time()
            # Drop entries older than 60 s
            while token_usage and now - token_usage[0][0] > 60:
                token_usage.popleft()
            spent = sum(t for _, t in token_usage)
            if spent + TOKENS_PER_CALL < MAX_TOKENS_MIN:
                token_usage.append((now, TOKENS_PER_CALL))
                return
        time.sleep(0.25)


def with_backoff(fn, *args, tries=6, base_delay=0.5, **kwargs):
    for attempt in range(1, tries + 1):
        try:
            _wait_for_rps_slot()
            _wait_for_token_budget()
            with concurrency_sem:
                return fn(*args, **kwargs)
        except openai.RateLimitError:  # pragma: no cover
            if attempt == tries:
                raise
            delay = base_delay * (2 ** (attempt - 1)) + random.random() * 0.3
            logging.warning(f"429 received; sleeping {delay:.2f}s (attempt {attempt}/{tries})")
            time.sleep(delay)

# ---------------------------------------------------------------------------
# JSON schema + helpers
# ---------------------------------------------------------------------------
SCHEMA = {
    "type": "object",
    "required": ["metadata", "original_text", "reviewed_text"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": [
                "document_id", "case_number", "document_date",
                "classification_level", "declassification_date",
                "document_type", "author", "recipients",
                "people_mentioned", "country", "city",
                "other_place", "document_title", "document_description",
                "archive_location", "observations", "language",
                "keywords", "page_count", "document_summary"
            ],
            "properties": {
                k: {"type": "string"} for k in [
                    "document_id", "case_number", "document_date",
                    "classification_level", "declassification_date",
                    "document_type", "author", "document_title",
                    "document_description", "archive_location",
                    "observations", "language", "document_summary"
                ]
            } | {
                k: {"type": "array"} for k in [
                    "recipients", "people_mentioned", "country", "city", "other_place", "keywords"
                ]
            } | {
                "page_count": {"type": "number"}
            }
        },
        "original_text": {"type": "string"},
        "reviewed_text": {"type": "string"}
    }
}

ARRAY_FIELDS  = ["recipients", "people_mentioned", "country", "city", "other_place", "keywords"]
STR_FIELDS    = [
    "document_id", "case_number", "document_date",
    "classification_level", "declassification_date", "document_type", "author",
    "document_title", "document_description", "archive_location",
    "observations", "language", "document_summary",
]

DATE_FIX_RE = re.compile(r"^00-00-(\d{4})$")


def normalize_and_fill(data: dict):
    meta = data.setdefault("metadata", {})
    # fix bad date
    m = DATE_FIX_RE.match(meta.get("document_date", ""))
    if m:
        meta["document_date"] = f"{m.group(1)}-00-00"

    # defaults / type‑coercion
    for f in ARRAY_FIELDS:
        v = meta.get(f)
        if isinstance(v, str):
            meta[f] = [v] if v else []
        elif v is None:
            meta[f] = []
    for f in STR_FIELDS:
        if not isinstance(meta.get(f), str):
            meta[f] = ""
    if not isinstance(meta.get("page_count"), (int, float)):
        meta["page_count"] = 0

# ---------------------------------------------------------------------------
# Prompt (truncated for brevity)
# ---------------------------------------------------------------------------
PROMPT = """You are given an image of a declassified CIA document related to the Chilean dictatorship (1973-1990).
Your task is to transcribe, summarize, correct scanning errors, and organize the information in a highly standardized JSON schema for historical research.
Return ONLY the JSON object described in the following template without markdown fences."""

# ---------------------------------------------------------------------------
# Core call + validation
# ---------------------------------------------------------------------------

def chat_json(messages):
    return with_backoff(
        client.chat.completions.create,
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )


def validate_json(messages, retries=1):
    for i in range(retries + 1):
        resp = chat_json(messages)
        content = resp.choices[0].message.content
        data = content if isinstance(content, dict) else json.loads(content)
        normalize_and_fill(data)
        errs = list(Draft7Validator(SCHEMA).iter_errors(data))
        if not errs:
            return data
        if i < retries:
            err_text = "\n".join(f"- {e.message}" for e in errs)
            messages.append({
                "role": "user",
                "content": "The JSON did not match the schema: \n" + err_text + "\nPlease return corrected JSON only."
            })
        else:
            raise ValidationError("; ".join(e.message for e in errs))

# ---------------------------------------------------------------------------
# Worker: single image file → JSON transcript
# ---------------------------------------------------------------------------

def transcribe_image(file: Path, out_dir: Path, resume: bool=False) -> bool:
    out_path = out_dir / (file.stem + '.json')
    if resume and out_path.exists():
        logging.info(f"[skip] {file.name} exists")
        return True

    img_b64 = base64.b64encode(file.read_bytes()).decode()
    data_url = f"data:image/jpeg;base64,{img_b64}"

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
    }]

    try:
        result = validate_json(messages, retries=1)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        logging.info(f"[ok] {file.name}")
        return True
    except Exception as e:
        logging.error(f"[fail] {file.name}: {e}")
        return False

# ---------------------------------------------------------------------------
# Batch driver
# ---------------------------------------------------------------------------

def process_batch(max_files: int, workers: int, resume: bool):
    img_dir = DATA_DIR / 'images'
    out_dir = DATA_DIR / 'generated_transcripts'
    out_dir.mkdir(parents=True, exist_ok=True)
    files = [p for p in sorted(img_dir.iterdir()) if p.suffix.lower() in ('.jpg', '.jpeg')]
    if max_files:
        files = files[:max_files]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks = {pool.submit(transcribe_image, f, out_dir, resume): f.name for f in files}
        with tqdm(total=len(tasks), desc='Processing images', unit='img') as bar:
            for fut in as_completed(tasks):
                fut.result()
                bar.update(1)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    ap = argparse.ArgumentParser(description='Batch transcribe CIA document images')
    ap.add_argument('--max-files', type=int, default=0, help='Only process first N images')
    ap.add_argument('--max-workers', type=int, default=MAX_CONCURRENT, help='Thread pool size (<= concurrency limit)')
    ap.add_argument('--resume', action='store_true', help='Skip already‑transcribed images')
    args = ap.parse_args()

    process_batch(args.max_files, args.max_workers, args.resume)
