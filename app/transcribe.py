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

prompt = """
You are given an image of a declassified CIA document related to the Chilean dictatorship (1973-1990). Your task is to transcribe, summarize, correct scanning errors, and organize the information in a highly standardized way for historical research.

Return your response strictly as a JSON object without any Markdown formatting or code fences:

{
    "metadata": {
        "document_id": "",
        "case_number": "",
        "document_date": "YYYY-MM-DD",
        "classification_level": "",
        "declassification_date": "YYYY-MM-DD",
        "document_type": "",
        "author": "",
        "recipients": [],
        "people_mentioned": [],
        "country": [],
        "city: [],
        "other_place: [],
        "document_title": "",
        "document_description": "",
        "archive_location": "",
        "observations": "",
        "language": "",
        "keywords": [],
        "page_count": 0,
        "document_summary": ""
    },
    "original_text": "",
    "reviewed_text": ""
}

Mandatory Formatting Guidelines:

1. **Dates**:
   - Always use the ISO 8601 format: "YYYY-MM-DD".
   - If the exact day or month is unknown, use "00". Example: "1974-05-00" (if month is known but day unknown) or "1974-00-00" (if only the year is known).
   - If no date is available at all, leave blank.

2. **Names**:
   - Standardize names strictly as "LAST NAME, FIRST NAME" (uppercase).
   - Example: "PINCHET, AUGUSTO"

3. **Places**:
   - All place names must be standardized in uppercase (e.g., "SANTIAGO", "VALPARAÍSO").

4. **Classification Level**:
   - Use exactly one of: "TOP SECRET", "SECRET", "CONFIDENTIAL", "UNCLASSIFIED". If unclear or missing, leave blank.

5. **Document Type**:
   - Standardize strictly to one of: "MEMORANDUM", "LETTER", "TELEGRAM", "INTELLIGENCE BRIEF", "REPORT", "MEETING MINUTES", "CABLE". Leave blank if uncertain.

6. **Keywords**:
   - Always uppercase, short, consistent thematic tags.
   - Common examples: "HUMAN RIGHTS", "OPERATION CONDOR", "US-CHILE RELATIONS", "MILITARY COUP", "ECONOMIC POLICY", "REPRESSION".

7. **Original vs Reviewed Text**:
   - **original_text**: Faithful transcription with original artifacts and scanning issues.
   - **reviewed_text**: Correct scanning errors, improve readability without altering factual content.

8. **Observations**:
   - Explicitly note "[ILLEGIBLE]" for unreadable content or "[UNCERTAIN]" when the content meaning is ambiguous.

9. **Language**:
   - Exactly one of: "ENGLISH", "SPANISH". Leave blank if uncertain.

10. **Document Summary**:
    - Concise (1-3 sentences), clear, and historically informative.

Return only the JSON object as instructed.
"""


def transcribe_single_image(
    filename: str,
    image_dir: Path,
    output_dir: Path,
    resume: bool
) -> bool:
    """
    Transcribe a single image. Returns True if successful, False otherwise.
    """
    file_path = image_dir / filename
    output_filename = output_dir / (os.path.splitext(filename)[0] + ".json")

    # If resume mode is ON, skip if the JSON file already exists
    if resume and output_filename.exists():
        logging.info(f"[RESUME] Skipping {filename}, JSON already exists.")
        return True

    logging.debug(f"Processing {file_path}...")

    # Read and base64-encode the image
    with open(file_path, "rb") as f:
        image_bytes = f.read()
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{encoded_image}"

    # Send the request to the model
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL"),  # or "gpt-4o" if your environment supports it
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": data_url,
                        "detail": "high",
                    },
                ],
            }
        ],
    )

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


def process_images_in_directory(max_files=0, resume=False, max_workers=2):
    """
    Processes images from DATA_DIR / 'images' in parallel threads.
    :param max_files: Number of files to process; 0 means process all.
    :param resume: If True, skip already transcribed (existing .json).
    :param max_workers: How many parallel threads to run.
    """
    image_dir = DATA_DIR / "images"
    output_dir = DATA_DIR / "generated_transcripts"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Gather all JPEG files, sorted for consistent ordering
    all_images = sorted(
        f for f in os.listdir(image_dir) if f.lower().endswith((".jpg", ".jpeg"))
    )

    # If max_files != 0, truncate the list
    if max_files > 0:
        all_images = all_images[:max_files]

    # Create a ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # We use futures for each job, so we can update TQDM when they finish
        futures = {
            executor.submit(transcribe_single_image, filename, image_dir, output_dir, resume): filename
            for filename in all_images
        }

        # Create a TQDM progress bar for total files
        with tqdm(total=len(futures), desc="Processing images", unit="image") as pbar:
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
    parser = argparse.ArgumentParser(description="Process images and generate transcripts.")
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Number of files to process; 0 means process all files."
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip any images that already have a .json transcript if set."
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=32,
        help="Number of parallel threads for API calls."
    )

    args = parser.parse_args()

    process_images_in_directory(
        max_files=args.max_files,
        resume=args.resume,
        max_workers=args.max_workers
    )
