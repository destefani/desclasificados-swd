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
