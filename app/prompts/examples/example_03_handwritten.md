# Example 3: Handwritten Note

## Document Characteristics
- Primarily handwritten text
- Attached to declassified cover sheet
- Several words illegible or uncertain
- Informal communication
- No formal header structure

## Teaching Points
- Use [ILLEGIBLE] for completely unreadable handwriting
- Use [UNCERTAIN] for ambiguous words
- Lower confidence scores for handwritten content
- Extract what's visible from cover sheet (declassification info)
- List specific illegibility concerns

## Expected Output

```json
{
  "metadata": {
    "document_id": "",
    "case_number": "C5199900030",
    "document_date": "1977-05-11",
    "classification_level": "SECRET",
    "declassification_date": "2001-04-27",
    "document_type": "",
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
    "city": [],
    "other_place": [],
    "document_title": "",
    "document_description": "Handwritten note attached to a Chile Project file within the U.S. Department of State, discussing timing and agenda status of an unspecified issue before a committee.",
    "archive_location": "U.S. DEPARTMENT OF STATE, CHILE PROJECT (C5199900030)",
    "observations": "Handwritten text is partially illegible; several words and names are uncertain. The note appears on a declassified cover sheet with release and exemption markings. Some marginal numbers and notations are not clearly interpretable.",
    "language": "ENGLISH",
    "keywords": [
      "CHILE PROJECT",
      "US-CHILE RELATIONS",
      "COMMITTEE"
    ],
    "page_count": 1,
    "document_summary": "A brief handwritten note, dated 1977-05-11, indicates that an issue related to the Chile Project is unlikely to come before a committee soon and may not need to be placed on the agenda. The writer sees no reason for urgency and notes that the committee will discuss the matter at a later, unspecified meeting."
  },
  "original_text": "UNCLASSIFIED  SECRET\nEXCISE\n\nARA - Mr. Optomins [UNCERTAIN]\n\nJohn:\n\nThis came live from John\nF[illegible] today - I agree that the\ntone it takes may be too rang, but\nis not desiral to make an issue of it...",
  "reviewed_text": "UNCLASSIFIED  SECRET\nEXCISE\n\nARA - MR. [ILLEGIBLE]\n\nJOHN:\n\nTHIS CAME IN FROM JOHN\n[ILLEGIBLE] TODAY. I AGREE THAT THE\nTONE IT TAKES MAY BE TOO STRONG, BUT\nIT IS NOT DESIRABLE TO MAKE AN ISSUE OF IT...",
  "confidence": {
    "overall": 0.62,
    "concerns": [
      "Handwritten text is partially illegible throughout",
      "Author signature unclear (appears to be 'Jim')",
      "Several words uncertain or require contextual inference",
      "No formal document title visible",
      "Recipient last name illegible"
    ]
  }
}
```
