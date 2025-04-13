import os
import base64
import argparse
import json
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI
from app.config import ROOT_DIR, DATA_DIR, logging

# Load environment variables
load_dotenv(ROOT_DIR / '.env')

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_TEST_KEY"))

prompt = """
You are given an image of a declassified CIA document related to the Chilean dictatorship. The goal is to transcribe, summarize, and correct scanning issues so it can be organized and analyzed for historical research.

Please return your answer strictly in JSON format (with no Markdown formatting or code fences). The structure is:

{
    "metadata": {
        "document_id": "",
        "case_number": "",
        "document_date": "",
        "classification_level": "",
        "declassification_date": "",
        "document_type": "",
        "author": "",
        "recipients": [],
        "people_mentioned": [],
        "places_mentioned": [],
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

Guidelines:
1. **original_text**: Provide an as-faithful-as-possible transcription, including unusual formatting, scanning artifacts, or uncertain content.
2. **reviewed_text**: Provide a “cleaned-up” version of the text, removing or correcting obvious OCR/scanning errors. Do not invent or alter the factual content.
3. **metadata**: 
   - **document_id** / **case_number**: Use any references you find, or leave blank if none appear.
   - **document_date**: Use the date provided in the document, or note “[unknown]” if not found.
   - **classification_level** / **declassification_date**: Note the classification (“Secret,” “Top Secret,” etc.) and the date it was declassified, if visible. Otherwise leave blank.
   - **document_type**: E.g., telegram, memorandum, intelligence brief, letter, etc. Use best guess or leave blank.
   - **author** / **recipients**: List individuals or entities that wrote or received the document; if unsure, leave them blank.
   - **people_mentioned** / **places_mentioned**: Capture relevant names of people or places from the text.
   - **document_title** / **document_description**: Summarize the main subject or purpose of the document.
   - **archive_location**: If there is an archival reference, note it here or leave blank.
   - **observations**: Mention any illegible or uncertain parts (e.g., “[illegible]”) and any additional notes or doubts.
   - **language**: If you can identify the language, note it here (e.g., “English,” “Spanish”); otherwise leave blank.
   - **keywords**: Provide relevant tags or themes if apparent (e.g., “human rights,” “Operation Condor,” “US-Chile relations,” etc.).
   - **page_count**: If the total number of pages is indicated, fill it in; otherwise leave 0 or blank.
   - **document_summary**: Write a concise 1-3 sentence synopsis of the document’s overall content or significance.
4. If you are unsure about any field, leave it blank or mark it as “[unknown]” in “observations.”
5. Return only the JSON object and nothing else. No code fences, no extra commentary. 
"""

def process_images_in_directory(max_files=0, resume=False):
    """
    Processes images from DATA_DIR / 'images'.

    :param max_files: Number of files to process; 0 means process all.
    :param resume: If True, skip any files that already have a .json transcript.
    """
    image_dir = DATA_DIR / "images"
    # Gather all JPEG files in a list (sorted for consistency) so we can display a progress bar
    all_images = sorted(f for f in os.listdir(image_dir) if f.lower().endswith((".jpg", ".jpeg")))

    # Ensure the output directory exists
    output_dir = DATA_DIR / "generated_transcripts"
    output_dir.mkdir(parents=True, exist_ok=True)

    processed_count = 0

    # Set up the progress bar
    with tqdm(total=len(all_images), desc="Processing images", unit="image") as pbar:
        for filename in all_images:
            # Stop early if max_files is set and we've already processed that many
            if max_files != 0 and processed_count >= max_files:
                pbar.update(1)
                continue

            file_path = image_dir / filename
            output_filename = output_dir / (os.path.splitext(filename)[0] + ".json")

            # If resume mode is ON, skip files that already have a JSON transcript
            if resume and output_filename.exists():
                logging.info(f"Resume mode: {output_filename} already exists; skipping.")
                pbar.update(1)
                continue

            logging.info(f"Processing {file_path}...")

            # Read and base64-encode the image
            with open(file_path, "rb") as f:
                image_bytes = f.read()
            encoded_image = base64.b64encode(image_bytes).decode("utf-8")
            data_url = f"data:image/jpeg;base64,{encoded_image}"

            # Send the request to the model
            response = client.responses.create(
                model="gpt-4o-mini",  # Update to "gpt-4o" if your environment supports it
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": data_url,
                            "detail": "high"
                        },
                    ],
                }],
            )

            # Clean the response to remove ```json ...``` blocks or extraneous markdown
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
                logging.error(f"Failed to parse JSON for '{filename}': {e}")
                pbar.update(1)
                continue

            # If parsing is successful, write the JSON to file
            with open(output_filename, "w", encoding="utf-8") as out_file:
                json.dump(response_data, out_file, ensure_ascii=False, indent=4)

            logging.info(f"Saved output JSON to {output_filename}")
            processed_count += 1

            pbar.update(1)  # Mark 1 item processed in the progress bar


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
        help="If specified, skip any images that already have a .json transcript."
    )
    args = parser.parse_args()

    process_images_in_directory(max_files=args.max_files, resume=args.resume)