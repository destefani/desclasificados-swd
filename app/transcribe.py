import os
import base64
import argparse
import json
import logging
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.config import ROOT_DIR, DATA_DIR  # Adjust if needed

# Load environment variables
load_dotenv(ROOT_DIR / '.env')

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load the transcription prompt from the markdown file in `app/prompts`.
# This allows editing the prompt outside of the code. If the file cannot
# be read, fall back to the original inline prompt to preserve behaviour.
prompt_path = Path(__file__).parent / "prompts" / "metadata_prompt.md"
try:
    prompt = prompt_path.read_text(encoding="utf-8")
except Exception as e:
    logging.error(f"Failed to read prompt file {prompt_path}: {e}")
    # Fail fast: do not continue without the canonical prompt file.
    raise RuntimeError(f"Prompt file missing or unreadable: {prompt_path}: {e}")


def transcribe_single_document(
    filename: str,
    document_dir: Path,
    output_dir: Path,
    resume: bool
) -> bool:
    """
    Transcribe a single document. Returns True if successful, False otherwise.
    """
    file_path = document_dir / filename
    output_filename = output_dir / (os.path.splitext(filename)[0] + ".json")

    # If resume mode is ON, skip if the JSON file already exists
    if resume and output_filename.exists():
        logging.info(f"[RESUME] Skipping {filename}, JSON already exists.")
        return True

    logging.debug(f"Processing {file_path}...")
    
    # Read the PDF file and encode it in base64
    try:
        with open(file_path, "rb") as f:
            data = f.read()
            
        base64_string = base64.b64encode(data).decode("utf-8")
        logging.info(f"Encoded {filename} to base64")
    except Exception as e:
        logging.error(f"Failed to read or encode file {filename}: {e}")
        return False


    # Send the request to the model. Provide the prompt text and attach the
    # encoded PDF file.
    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL"),
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_file",
                            "filename": filename,
                            "file_data": f"data:application/pdf;base64,{base64_string}",
                        },
                    ],
                }
            ],
        )
    except Exception as e:
        logging.error(f"API request failed for {filename}: {e}")
        return False

    # Clean the response to remove ```json ...``` blocks
    response_text = response.output_text
    cleaned_text = (
        response_text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    # Attempt to parse the cleaned text as JSON
    try:
        response_data = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logging.error(f"JSON parse error on {filename}: {e}")
        return False

    # Write the JSON to file
    with open(output_filename, "w", encoding="utf-8") as out_file:
        json.dump(response_data, out_file, ensure_ascii=False, indent=4)

    logging.info(f"Saved output JSON to {output_filename}")
    return True


def process_documents_in_directory(max_files=0, resume=False, max_workers=2):
    """
    Processes PDF documents from DATA_DIR / 'original_pdfs' in parallel threads.
    :param max_files: Number of files to process; 0 means process all.
    :param resume: If True, skip already transcribed (existing .json).
    :param max_workers: How many parallel threads to run.
    """
    document_dir = DATA_DIR / "original_pdfs"
    output_dir = DATA_DIR / "generated_transcripts"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Gather all PDF files, sorted for consistent ordering
    all_documents = sorted(
        f for f in os.listdir(document_dir) if f.lower().endswith(".pdf")
    )

    # If max_files != 0, truncate the list
    if max_files > 0:
        all_documents = all_documents[:max_files]

    # Create a ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # We use futures for each job, so we can update TQDM when they finish
        futures = {
            executor.submit(transcribe_single_document, filename, document_dir, output_dir, resume): filename
            for filename in all_documents
        }

        # Create a TQDM progress bar for total files
        with tqdm(total=len(futures), desc="Processing unclassified documents", unit="document") as pbar:
            # As each future completes, we update the progress bar
            for future in as_completed(futures):
                filename = futures[future]
                try:
                    result = future.result()
                    if not result:
                        logging.error(f"Transcription failed for file: {filename}")
                except Exception as e:
                    logging.error(f"Unexpected error for file: {filename}, {e}")
                finally:
                    pbar.update(1)  # Move the bar forward by 1 job




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process unclassified documents and generate transcripts.")
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Number of files to process; 0 means process all files."
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip any documents that already have a .json transcript if set."
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=32,
        help="Number of parallel threads for API calls."
    )

    args = parser.parse_args()

    process_documents_in_directory(
        max_files=args.max_files,
        resume=args.resume,
        max_workers=args.max_workers
    )

