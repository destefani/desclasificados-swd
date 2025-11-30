# Data Inventory Report

**Generated:** 2025-11-30
**Repository:** Desclasificados - CIA Chilean Dictatorship Documents

## Executive Summary

The data directory contains **21,512 declassified CIA documents** in multiple formats, representing approximately **7+ GB** of processed data. The collection spans document IDs from **24736 to 46919**, though processing into structured JSON format is still in early stages.

### Current Status

- ✅ **100% Complete**: PDF extraction, image conversion, PDF transcripts
- ⚠️ **85% Complete**: Text transcripts (18,363/21,512)
- ⚠️ **26% Complete**: V1 JSON structured metadata (5,611/21,512)
- 🔴 **0.06% Complete**: Current generation JSON (12/21,512)

## Directory Structure

```
data/
├── original_pdfs/          21,512 files    2.8 GB    Source documents
├── images/                 21,512 files    3.8 GB    Document scans (PNG despite .jpg extension)
├── transcripts/            21,512 files     99 MB    OCR transcript PDFs
├── transcript_text/        18,363 files    116 MB    Plain text transcripts
├── generated_transcripts_v1/ 5,611 files    33 MB    Legacy JSON metadata
├── generated_transcripts/      12 files     64 KB    Current JSON metadata
├── session.json                 1 file     2.2 MB    Document ID index
└── original_pdfs.zip            1 file     2.6 GB    Archived source
```

**Total Size:** ~9.7 GB (including zip archive)

## Detailed Breakdown

### 1. Original PDFs (`original_pdfs/`)

- **Count:** 21,512 documents
- **Size:** 2.8 GB
- **Format:** PDF (various versions)
- **Naming:** Sequential IDs (24736.pdf → 46919.pdf)
- **Status:** ✅ Complete collection

**Characteristics:**
- Source material from CIA declassification
- Varying quality scans
- Contains redactions, stamps, handwritten notes
- Multiple pages possible per document

### 2. Images (`images/`)

- **Count:** 21,512 files
- **Size:** 3.8 GB
- **Format:** PNG (despite .jpg file extension!)
- **Resolution:** Varies (example: 637x828 pixels)
- **Average Size:** ~156 KB per file
- **Status:** ✅ Complete (1:1 mapping with PDFs)

**Important Notes:**
- Files are named with `.jpg` extension but are actually **PNG format**
- This should be noted in any image processing code
- Single-page extractions from PDFs
- RGB 8-bit color depth

### 3. Transcript PDFs (`transcripts/`)

- **Count:** 21,512 files
- **Size:** 99 MB
- **Format:** PDF v1.4, single page
- **Naming:** `{id}_transcript.pdf`
- **Status:** ✅ Complete

**Purpose:**
- OCR-processed versions of original scans
- Searchable text layer
- Lower file size than originals

### 4. Transcript Text (`transcript_text/`)

- **Count:** 18,363 files (85% coverage)
- **Size:** 116 MB
- **Format:** Plain text (.txt)
- **Naming:** `{id}_transcript.txt`
- **Status:** ⚠️ Missing 3,149 transcripts

**Missing Files:**
- ~15% of documents lack text extraction
- May indicate:
  - Processing failures
  - Image-only documents (no extractable text)
  - Heavily redacted documents
  - Handwritten content

**Quality Issues:**
- OCR errors present
- Inconsistent formatting
- Special characters may be corrupted
- Line breaks and spacing vary

### 5. Generated Transcripts V1 (`generated_transcripts_v1/`)

- **Count:** 5,611 files (26% coverage)
- **Size:** 33 MB
- **Format:** JSON
- **Average Size:** ~6 KB per file
- **Status:** ⚠️ Legacy format, incomplete

**Content Sample:**
```json
{
  "metadata": {
    "document_id": "STATE 219986",
    "document_date": "1976-08-27",
    "classification_level": "UNCLASSIFIED",
    "document_type": "TELEGRAM",
    "author": "JACOBSON, MARK",
    "recipients": [...],
    "people_mentioned": [...],
    "country": [...],
    "keywords": ["OPERATION CONDOR", "HUMAN RIGHTS", ...]
  },
  "original_text": "...",
  "reviewed_text": "..."
}
```

**Known Issues:**

#### Date Inconsistencies
- 1,168 documents have `[unknown]` dates
- Multiple date formats present:
  - ISO: "1976-08-27" ✓
  - US: "September 21, 1976"
  - Short: "SEP 88", "FEB 87"
  - Long: "June 18, 1987"
- **Action Required:** Standardization needed

#### Document Type Variations
- **949** variations of document types found
- Major inconsistencies:
  - "telegram" vs "Telegram" vs "TELEGRAM" (975 + 499 + 27 = 1,525 total)
  - "letter" vs "Letter" (621 + 505 = 1,126 total)
  - "memorandum" vs "Memorandum" vs "MEMORANDUM" vs "Memo" vs "memo" (many variants)
  - 269 marked as `[unknown]`
  - 237 empty strings

**Top Document Types (Combined):**
1. Telegrams: ~1,500+ (various capitalizations)
2. Letters: ~1,100+ (various capitalizations)
3. Memoranda: ~1,200+ (including memos, various capitalizations)
4. Reports: ~200+
5. Intelligence Briefs: ~40+

#### Geographic Focus
From sample data, documents cover:
- **Chile** (primary focus)
- **Argentina, Uruguay, Paraguay** (Operation Condor context)
- **Brazil, Bolivia** (regional connections)
- **United States** (sender/author)

#### Time Period Coverage
Preliminary analysis shows concentration in:
- **1976** (Operation Condor era)
- **1987-1988** (late dictatorship period)
- Additional years present but less represented

### 6. Generated Transcripts Current (`generated_transcripts/`)

- **Count:** 12 files (0.06% coverage)
- **Size:** 64 KB
- **Format:** JSON with strict schema validation
- **Status:** 🔴 Just started

**Improvements over V1:**
- Strict ISO 8601 date formatting (YYYY-MM-DD)
- Standardized document types (controlled vocabulary)
- Consistent name formatting (LAST, FIRST in uppercase)
- JSON schema validation
- Better error handling and OCR correction

**Files Processed:**
- 24736, 24737, 24738, 24740-24744, 24746, 24747

**Remaining:** 21,500 documents (~99.94%)

### 7. Session Data (`session.json`)

- **Size:** 2.2 MB
- **Format:** JSON array
- **Content:** List of "known_documents" IDs
- **Purpose:** Tracking which documents exist in the collection

**Contains:** Document IDs as strings, appears to be a processing tracker or index.

### 8. Original PDFs Archive (`original_pdfs.zip`)

- **Size:** 2.6 GB (compressed)
- **Purpose:** Backup/distribution of source materials
- **Status:** Archive copy of `original_pdfs/` directory

## Data Quality Assessment

### Strengths

1. ✅ **Complete Source Collection**: All 21,512 original documents present
2. ✅ **Consistent Extraction**: 100% have images and transcript PDFs
3. ✅ **High Coverage**: 85% have text transcripts
4. ✅ **Rich Metadata**: V1 JSONs contain detailed structured data
5. ✅ **Multi-Format**: Multiple representations enable different use cases

### Weaknesses

1. ❌ **Incomplete Structured Data**: Only 26% have JSON metadata
2. ❌ **Format Inconsistencies**: V1 JSONs have standardization issues
3. ❌ **Missing Transcripts**: 3,149 documents lack text extraction
4. ❌ **Image Extension Mismatch**: Files are PNG but named .jpg
5. ❌ **Date Format Chaos**: Multiple date formats across v1 JSONs
6. ❌ **Document Type Chaos**: 949 variations need normalization

## Processing Pipeline Gaps

### Completed Stages
```
Original PDFs (21,512)
    ↓ 100%
Images (21,512)
    ↓ 100%
Transcript PDFs (21,512)
    ↓ 85%
Transcript Text (18,363)
```

### In-Progress Stages
```
Transcript Text (18,363)
    ↓ 31% (of text files)
V1 JSON (5,611)
    ↓ 0.2% (reprocessing)
Current JSON (12)
```

### Missing Processing
- **15,901 documents** need V1 JSON generation
- **21,500 documents** need current JSON generation
- **3,149 documents** need text transcript generation (or are not extractable)

## Data Use Recommendations

### For Analysis & Visualization
✅ **Use:** `generated_transcripts_v1/*.json`
- Largest structured dataset available
- Contains rich metadata
- Sufficient for timeline analysis, keyword extraction, network graphs
⚠️ **Caveat:** Apply normalization to dates and document types

### For Text Search & NLP
✅ **Use:** `transcript_text/*.txt`
- Plain text format
- Good coverage (85%)
- Direct OCR output
⚠️ **Caveat:** Contains OCR errors, check quality before analysis

### For Image Processing & ML
✅ **Use:** `images/*.{jpg|png}`
- Full collection available
- Consistent format (PNG)
- Good resolution
⚠️ **Note:** Despite .jpg extension, files are PNG format

### For Document Verification
✅ **Use:** `original_pdfs/*.pdf`
- Original source material
- Highest authority
- Contains all visual information (stamps, redactions, handwriting)

## Immediate Action Items

### High Priority
1. 🔥 **Continue Current JSON Generation**: Process remaining 21,500 documents with improved pipeline
2. 🔥 **Fix Image Extensions**: Rename .jpg → .png or update documentation
3. 🔴 **Standardize V1 Dates**: Convert all dates to ISO 8601 format
4. 🔴 **Normalize Document Types**: Map variations to standard types

### Medium Priority
5. 🟡 **Investigate Missing Transcripts**: Determine why 3,149 text files are missing
6. 🟡 **Quality Assessment**: Sample-check OCR accuracy across different document types
7. 🟡 **Create Data Dictionary**: Document all metadata fields and allowed values

### Low Priority
8. 🟢 **Compress Archives**: Consider separate compression for each data type
9. 🟢 **Add Checksums**: Create manifest with file hashes for integrity verification
10. 🟢 **Document ID Mapping**: Create cross-reference between sequential IDs and document IDs

## Storage Optimization

### Current Storage: ~9.7 GB

**Recommendations:**
- Archive `original_pdfs.zip` separately (saves 2.6 GB locally)
- Consider compressing `transcript_text/` (currently uncompressed, ~116 MB → ~30-40 MB)
- `generated_transcripts_v1/` JSON could be minified (saves ~40%)
- Images are largest (3.8 GB) but necessary for vision processing

## Document ID Analysis

**ID Range:** 24736 - 46919
**Total Range:** 22,184 possible IDs
**Actual Documents:** 21,512
**Missing IDs:** ~672 (gaps in sequence)

**Possible Reasons for Gaps:**
- Removed duplicates
- Documents not declassified
- Processing errors
- Intentional exclusions

## Next Steps for Complete Dataset

1. **Resume Current JSON Generation**
   - Process all 21,512 documents with `transcribe_v2.py`
   - Estimate: ~10,756 hours API time (with rate limiting)
   - Cost estimate: ~$4,000-$8,000 (GPT-4o-mini)

2. **Create Master Index**
   - Combine session.json with file system scan
   - Document which files exist in which formats
   - Flag missing or incomplete documents

3. **Build Quality Dashboard**
   - Completion percentages by processing stage
   - Error rates and common issues
   - Date coverage visualization
   - Geographic distribution

4. **Establish Data Validation**
   - Automated checks for file format mismatches
   - JSON schema validation for all transcripts
   - Orphan file detection
   - Duplicate identification

---

**Report End**

For questions or data access issues, refer to the project documentation in `docs/PROJECT_CONTEXT.md` and `CLAUDE.md`.
