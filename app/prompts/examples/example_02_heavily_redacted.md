# Example 2: Heavily Redacted Telegram

## Document Characteristics
- Multiple black redaction bars
- Partial names and amounts obscured
- Classification stamps and routing marks
- Some handwritten annotations
- Telegram/cable format

## Teaching Points
- Mark redacted content as [REDACTED], not [ILLEGIBLE]
- Extract partial information where visible
- Handle incomplete names: "LAST, [FIRST NAME UNKNOWN]"
- Describe redactions in observations
- Moderate confidence for partial extraction

## Expected Output

```json
{
  "metadata": {
    "document_id": "00000921",
    "case_number": "",
    "document_date": "1977-05-00",
    "classification_level": "SECRET",
    "declassification_date": "2001-04-27",
    "document_type": "MEMORANDUM",
    "author": "UNKNOWN, JIM",
    "recipients": [
      "UNKNOWN, JOHN"
    ],
    "people_mentioned": [
      "GOFFIELD, MARGARET R."
    ],
    "country": [
      "CHILE",
      "UNITED STATES"
    ],
    "city": [
      "SANTIAGO"
    ],
    "other_place": [],
    "document_title": "QUESTIONS PUT TO EMBASSY SANTIAGO IN RESPONSE TO 17 MAY MESSAGE ON AID TO PDC",
    "document_description": "Heavily redacted U.S. Department of State document posing follow-up questions to the U.S. Embassy in Santiago regarding financial aid to the Chilean PDC.",
    "archive_location": "U.S. DEPARTMENT OF STATE, CHILE PROJECT (#5199900030)",
    "observations": "Document is a poor-quality photocopy with extensive redactions and handwritten annotations. Several lines are partially or fully illegible. Bracketed areas appear to indicate redacted monetary amounts or specific terms. Declassification block indicates release under excision review. Exact date visible as month only (May 1977).",
    "language": "ENGLISH",
    "keywords": [
      "US-CHILE RELATIONS",
      "FOREIGN AID",
      "PDC",
      "EMBASSY SANTIAGO"
    ],
    "page_count": 1,
    "document_summary": "The document lists questions from Washington to the U.S. Embassy in Santiago concerning a 17 May message about financial aid to the Chilean PDC, asking the embassy to clarify earlier paragraphs and whether an immediate dollar payment is being requested. Most specific figures and details are redacted."
  },
  "original_text": "UNCLASSIFIED   SECRE[ ]\nEXCISE\n\nQuestions put to Embassy Santiago in\nResponse to 17 May Message on Aid to\nPDC  TO [ ]  7/7 my [ILLEGIBLE]\n\n1. Please service first two sentences of paragraph 5.\n\n2. As we reed your paragrph 1 and the last sentence of paragrph 5,\n   you Are requesting that we take a decision now to provide the dollar\n   equivalent of [ ] presented\n   [ ] with immediate\n   payment of [ ]  on [ ]...",
  "reviewed_text": "UNCLASSIFIED   SECRET\nEXCISE\n\nQuestions put to Embassy Santiago in\nresponse to 17 May message on aid to PDC\n\n1. Please service first two sentences of paragraph 5.\n\n2. As we read your paragraph 1 and the last sentence of paragraph 5,\n   you are requesting that we take a decision now to provide the dollar\n   equivalent of [REDACTED], presented [REDACTED] with immediate\n   payment of [REDACTED] on [REDACTED]...",
  "confidence": {
    "overall": 0.72,
    "concerns": [
      "Author and recipient first names not visible",
      "Exact date unknown (only month visible)",
      "Extensive redactions obscure key details",
      "Poor scan quality makes some text illegible"
    ]
  }
}
```
