# Document Transcription Assessment Report

**Date:** 2025-12-07
**Project:** Desclasificados - CIA Chilean Dictatorship Documents
**Branch:** feature/sensitive-content-tracking

---

## Executive Summary

The project aims to transcribe **21,512 declassified CIA documents** related to the Chilean dictatorship (1973-1990). Current transcription coverage stands at **22.9%** (4,937 unique documents), with the best quality transcriptions coming from **gpt-4.1-mini** (4,924 files). The remaining **16,575 documents** (77.1%) require processing.

| Metric | Value |
|--------|-------|
| Total Source PDFs | 21,512 |
| Unique Transcriptions | 4,937 (22.9%) |
| Remaining | 16,575 (77.1%) |
| Primary Model | gpt-4.1-mini |
| Est. Cost to Complete | ~$50-100 |

---

## 1. Current Transcription Coverage

### 1.1 Source Materials

| Source | Count | Status |
|--------|-------|--------|
| Original PDFs | 21,512 | Complete |
| Extracted Images (first page) | 21,512 | Complete |
| Total Pages (estimated) | ~76,152 | 3.54 avg pages/PDF |

### 1.2 Transcription by Model

| Model | Files | Coverage | Quality | Notes |
|-------|-------|----------|---------|-------|
| **gpt-4.1-mini** | 4,924 | 22.9% | Best | Full OCR, structured metadata |
| chatgpt-5-1 | 1,352 | 6.3% | Good | Earlier transcription pass |
| claude-3-5-haiku | 122 | 0.6% | Metadata only | No full OCR (placeholder text) |
| gpt-4.1-nano | 5 | <0.1% | Test | Testing only |
| claude-sonnet-4-5 | 2 | <0.1% | Best quality | Very expensive |

### 1.3 Overlap Analysis

- **gpt-4.1-mini** and **chatgpt-5-1** overlap: 1,339 files
- Unique to gpt-4.1-mini: 3,585 files
- Unique to chatgpt-5-1: 13 files
- **Total unique transcripts**: 4,937 files

### 1.4 Archive (Legacy)

| Archive | Files | Status |
|---------|-------|--------|
| generated_transcripts_v1 | 5,611 | Deprecated (non-standardized format) |
| transcripts_txt | 18,363 | Raw OCR text (85% coverage) |
| transcripts_pdf | 21,512 | PDF format transcripts |

---

## 2. Quality Assessment

### 2.1 Confidence Scores (gpt-4.1-mini, n=500 sample)

| Metric | Value |
|--------|-------|
| Average Confidence | **0.87** |
| Minimum | 0.50 |
| Maximum | 0.95 |

The confidence scores indicate good overall quality. Documents with confidence < 0.7 should be flagged for human review.

### 2.2 Classification Levels

| Classification | Count | Percentage |
|----------------|-------|------------|
| UNCLASSIFIED | 246 | 49.2% |
| CONFIDENTIAL | 123 | 24.6% |
| SECRET | 62 | 12.4% |
| (empty) | 53 | 10.6% |
| LIMITED OFFICIAL USE | 16 | 3.2% |

### 2.3 Document Types

| Type | Count | Percentage |
|------|-------|------------|
| MEMORANDUM | 237 | 47.4% |
| LETTER | 120 | 24.0% |
| TELEGRAM | 53 | 10.6% |
| REPORT | 39 | 7.8% |
| (empty) | 20 | 4.0% |
| MEETING MINUTES | 7 | 1.4% |
| CABLE | 5 | 1.0% |
| INTELLIGENCE BRIEF | 3 | 0.6% |

### 2.4 Language Distribution

| Language | Count | Percentage |
|----------|-------|------------|
| ENGLISH | 459 | 91.8% |
| SPANISH | 39 | 7.8% |
| GERMAN | 2 | 0.4% |

### 2.5 Date Coverage

| Metric | Count | Percentage |
|--------|-------|------------|
| Valid Dates | 471 | 94.2% |
| Missing/Invalid | 29 | 5.8% |

---

## 3. Content Analysis

### 3.1 Temporal Distribution

Documents span primarily from **1967 to 1991**, with peaks in:

| Period | Files | Notes |
|--------|-------|-------|
| 1987-1988 | 2,293 | Peak period (47%) - Late dictatorship |
| 1989-1991 | 1,349 | Transition to democracy |
| 1970-1976 | 334 | Allende era + early dictatorship |
| 1979-1986 | 473 | Mid-dictatorship |

**Key years:**
- 1987: 1,137 documents
- 1988: 1,156 documents (Plebiscite year)
- 1989: 540 documents
- 1990: 386 documents (Return to democracy)

### 3.2 Top Keywords (4,924 documents)

| Keyword | Count | Documents |
|---------|-------|-----------|
| US-CHILE RELATIONS | 3,622 | 73.6% |
| HUMAN RIGHTS | 2,307 | 46.9% |
| DIPLOMACY | 2,225 | 45.2% |
| STATE DEPARTMENT | 1,912 | 38.8% |
| EMBASSY | 1,751 | 35.6% |
| LETELIER ASSASSINATION | 1,402 | 28.5% |
| MILITARY | 1,013 | 20.6% |
| REPRESSION | 729 | 14.8% |
| PINOCHET REGIME | 571 | 11.6% |
| 1988 PLEBISCITE | 533 | 10.8% |
| POLITICAL PRISONERS | 469 | 9.5% |
| DINA | 317 | 6.4% |
| OPERATION CONDOR | 234 | 4.8% |
| DISAPPEARANCES | 251 | 5.1% |

### 3.3 Key People Mentioned

| Person | Count | Context |
|--------|-------|---------|
| LETELIER, ORLANDO | 739 | Assassination victim, former diplomat |
| PINOCHET, AUGUSTO | 506 | Dictator |
| AYLWIN, PATRICIO | 259 | First post-dictatorship president |
| ALLENDE, SALVADOR | 236 | Former president, 1973 coup victim |
| MOFFITT, RONNI | 219 | Assassination victim |
| CONTRERAS, MANUEL | 150 | DINA director |
| TOWNLEY, MICHAEL | 155 | DINA operative |
| FERNANDEZ LARIOS, ARMANDO | 153 | DINA agent |
| WEISFEILER, BORIS | 99 | Disappeared American |
| LAGOS, RICARDO | 69 | Opposition leader |

### 3.4 Geographic Coverage

| Country | Count | Role |
|---------|-------|------|
| CHILE | 4,821 | Primary subject |
| UNITED STATES | 4,315 | Document origin |
| ARGENTINA | 443 | Operation Condor partner |
| URUGUAY | 228 | Operation Condor partner |
| PARAGUAY | 169 | Operation Condor partner |
| CUBA | 176 | Regional context |
| BRAZIL | 121 | Operation Condor partner |
| BOLIVIA | 103 | Operation Condor partner |

### 3.5 Sensitive Content Detection

New schema fields track sensitive content (added in feature/sensitive-content-tracking):

| Category | Documents | Percentage |
|----------|-----------|------------|
| Violence References | 231 | 46.2% |
| Financial References | 66 | 13.2% |
| Torture References | 32 | 6.4% |

---

## 4. Schema Quality

### 4.1 Current Schema (gpt-4.1-mini)

The current schema includes:

```json
{
  "original_text": "Raw OCR transcription",
  "reviewed_text": "Cleaned transcription",
  "confidence": {
    "overall": 0.0-1.0,
    "concerns": []
  },
  "metadata": {
    "document_id": "",
    "case_number": "",
    "document_date": "YYYY-MM-DD",
    "declassification_date": "YYYY-MM-DD",
    "classification_level": "TOP SECRET|SECRET|CONFIDENTIAL|UNCLASSIFIED",
    "document_type": "MEMORANDUM|LETTER|TELEGRAM|...",
    "author": "LAST, FIRST",
    "recipients": [],
    "people_mentioned": [],
    "country": [],
    "city": [],
    "document_title": "",
    "document_summary": "",
    "language": "ENGLISH|SPANISH",
    "page_count": 1,
    "keywords": [],
    "financial_references": {},
    "violence_references": {},
    "torture_references": {}
  }
}
```

### 4.2 Schema Improvements Over v1

| Aspect | v1 (Legacy) | Current |
|--------|-------------|---------|
| Date Format | Multiple formats | ISO 8601 (YYYY-MM-DD) |
| Document Types | 949 variations | Standardized vocabulary |
| Names | Inconsistent | LAST, FIRST (uppercase) |
| Confidence Scores | No | Yes (0.0-1.0) |
| Sensitive Content | No | Yes (financial, violence, torture) |
| JSON Validation | No | Yes (schema enforced) |

### 4.3 Data Quality Issues

1. **Empty classification levels**: 10.6% of documents
2. **Empty document types**: 4% of documents
3. **Invalid dates**: 7% have year 0000 (345 documents)
4. **Incomplete names**: Many entries show "[FIRST NAME UNKNOWN]"
5. **Keyword inconsistency**: "PINOCHET REGIME" vs "PINOCCHET REGIME" (typo)

---

## 5. Model Comparison

### 5.1 OCR Quality

| Model | Full OCR | Text Quality | Cost/Doc |
|-------|----------|--------------|----------|
| gpt-4.1-mini | YES | High | ~$0.005 |
| chatgpt-5-1 | YES | High | ~$0.027 |
| claude-3-5-haiku | NO (placeholder) | N/A | ~$0.013 |
| gpt-4.1-nano | YES | Medium | ~$0.001 |
| claude-sonnet-4-5 | YES | Highest | ~$0.047 |

### 5.2 Recommended Model for Completion

**gpt-4.1-mini** is recommended:
- Full OCR capability verified
- Best cost/quality balance (~$0.005 per document)
- Consistent structured output
- ~$83 to complete remaining 16,575 documents

---

## 6. Completion Estimates

### 6.1 Remaining Work

| Task | Documents | Est. Cost | Est. Time |
|------|-----------|-----------|-----------|
| Transcribe remaining PDFs | 16,575 | ~$83 | 6-8 hours |
| Quality review (low confidence) | ~500 | Manual | TBD |
| Data normalization | All | $0 | 2-4 hours |

### 6.2 Cost Breakdown

Using **gpt-4.1-mini** for remaining documents:

| Component | Calculation | Cost |
|-----------|-------------|------|
| Input tokens | 16,575 docs x ~8K tokens x $0.40/M | ~$53 |
| Output tokens | 16,575 docs x ~2K tokens x $1.60/M | ~$53 |
| **Total** | | **~$83-100** |

### 6.3 Recommended Approach

```bash
# Resume transcription with gpt-4.1-mini
uv run python -m app.transcribe_openai \
  --model gpt-4.1-mini \
  --use-pdf \
  --max-workers 5 \
  --resume \
  --yes
```

---

## 7. Recommendations

### 7.1 Immediate Actions

1. **Complete transcription** using gpt-4.1-mini (~$83, 6-8 hours)
2. **Fix date errors**: Convert 345 documents with year "0000" to valid dates
3. **Standardize keywords**: Fix typos like "PINOCCHET" → "PINOCHET"

### 7.2 Quality Improvements

1. **Flag low-confidence documents** (confidence < 0.7) for manual review
2. **Validate classification levels**: Fill in 10.6% empty values
3. **Complete author names**: Resolve "[FIRST NAME UNKNOWN]" entries

### 7.3 Future Enhancements

1. **Build RAG system** using completed transcriptions
2. **Create timeline visualizations** using document dates
3. **Network analysis** using people_mentioned relationships
4. **Geographic mapping** using country/city data

---

## 8. Appendix: File Locations

| Data Type | Path | Count |
|-----------|------|-------|
| Source PDFs | `data/original_pdfs/` | 21,512 |
| Images | `data/images/` | 21,512 |
| gpt-4.1-mini transcripts | `data/generated_transcripts/gpt-4.1-mini/` | 4,924 |
| chatgpt-5-1 transcripts | `data/generated_transcripts/chatgpt-5-1/` | 1,352 |
| Archive v1 | `data/archive/generated_transcripts_v1/` | 5,611 |

---

## 9. Conclusion

The transcription project is **22.9% complete** with high-quality outputs from gpt-4.1-mini. The remaining 77.1% can be completed for approximately **$83-100** using the same model. The schema has been significantly improved over v1 with standardized formats, confidence scoring, and sensitive content tracking.

**Priority actions:**
1. Resume gpt-4.1-mini transcription to reach 100% coverage
2. Data quality cleanup (dates, classifications, keywords)
3. Build search and analysis tools on completed dataset

---

*Report generated for Desclasificados project assessment*
