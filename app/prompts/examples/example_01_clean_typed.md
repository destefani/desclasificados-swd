# Example 1: Clean Typed Document

## Document Characteristics
- High-quality typed document
- Clear classification markings
- Complete metadata visible
- Minimal redactions
- Standard State Department format

## Teaching Points
- Extract all visible metadata comprehensively
- High confidence scores for clear content
- Proper date format (YYYY-MM-DD)
- Name format: "LAST, FIRST" (uppercase)
- Distinguish original_text (with typos) vs reviewed_text (corrected)

## Expected Output

```json
{
  "metadata": {
    "document_id": "00009C1D",
    "case_number": "C5199900030",
    "document_date": "1971-04-21",
    "classification_level": "UNCLASSIFIED",
    "declassification_date": "2001-04-27",
    "document_type": "MEMORANDUM",
    "author": "CRIMMINS, JOHN",
    "recipients": [
      "JOHNSON, J."
    ],
    "people_mentioned": [
      "ALLENDE, SALVADOR",
      "COERR, WYMBERLEY"
    ],
    "country": [
      "CHILE",
      "UNITED STATES"
    ],
    "city": [
      "WASHINGTON",
      "SANTIAGO"
    ],
    "other_place": [],
    "document_title": "ADDITIONAL AID TO THE CHILEAN CHRISTIAN DEMOCRATIC PARTY FOR THE APRIL 1971 ELECTIONS",
    "document_description": "U.S. Department of State memorandum discussing additional electoral support to the Chilean Christian Democratic Party (PDC) for the April 1971 municipal elections.",
    "archive_location": "U.S. DEPARTMENT OF STATE, CHILE PROJECT (C5199900030)",
    "observations": "Clean typed document with minimal redactions. Some monetary amounts redacted with black boxes. Handwritten routing marks and stamps present.",
    "language": "ENGLISH",
    "keywords": [
      "US-CHILE RELATIONS",
      "ELECTIONS",
      "CHRISTIAN DEMOCRATIC PARTY",
      "CIA FUNDING",
      "POLITICAL INTERVENTION"
    ],
    "page_count": 1,
    "document_summary": "State Department memorandum recommends 40 Committee approval of additional CIA funding for Chile's Christian Democratic Party (PDC) in the April 1971 municipal elections, arguing the elections will be viewed as a referendum on Allende and that opposition support is important despite uncertain prospects."
  },
  "original_text": "DEPARTMENT OF STATE\n\nWashington, D.C. 20520\n\nUNCLASSIFIED\n\nMEMORANDUM\n\nTO      :  J - Ambassador Johnson\n\nTHROUGH:  INR/DDC - Mr. Wymberley Coerr\n\nFROM    :  ARA - John Crimmins\n\nSUBJECT:  Additional Aid to the Chilean Christian Democratic\n          Party for the April 1971 Elections.\n\nAttached is a CIA memorandum to the 40 Committee recommending that\nan additional [REDACTED] be authorized...",
  "reviewed_text": "DEPARTMENT OF STATE\n\nWashington, D.C. 20520\n\nUNCLASSIFIED\n\nMEMORANDUM\n\nTO:  J - Ambassador Johnson\n\nTHROUGH:  INR/DDC - Mr. Wymberley Coerr\n\nFROM:  ARA - John Crimmins\n\nSUBJECT:  Additional Aid to the Chilean Christian Democratic\n          Party for the April 1971 Elections\n\nAttached is a CIA memorandum to the 40 Committee recommending that\nan additional [REDACTED] be authorized...",
  "confidence": {
    "overall": 0.95,
    "concerns": []
  }
}
```
