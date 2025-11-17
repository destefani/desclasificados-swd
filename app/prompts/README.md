# Discussion on Prompt structure 
Metadata para Archivos Desclasificados de la CIA

## Current structure
```
{
    "metadata": {
        "document_id": STRING: Unique Document Identificator. The format variates from only numbers to combination with strings
        "case_number": STRING, 
        "document_date": STRING Date with format DD/MM/YYYY,
        "classification_level": STRING,
        "declassification_date": DATE DD/MM/YYYY,
        "document_type": STRING, 
        "author": STRING,
        "recipients": ARRAY[STRING],
        "people_mentioned": ARRAY[STRING],
        "places_mentioned": ARRAY[STRING],
        "document_title": STRING,
        "document_description": STRING,
        "archive_location": STRING,
        "observations": STRING,
        "language": STRING,
        "keywords": ARRAY[STRING],
        "page_count": INT,
        "document_summary": STRING
    },
    "original_text": STRING,
    "reviewed_text": STRING
}
```

## Potential Fixtures
* Date formats differ between different files
* Figure out the different "projects" and their meaning. 
* Case numbers that repeat (Work in progress)
    * Chile Project (+5199990030)


## Addition of new fields
* Add references to important events
* References to wellknown "projects"
* References to other documents