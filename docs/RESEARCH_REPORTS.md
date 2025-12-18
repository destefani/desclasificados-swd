# Research Reports from Declassified Documents

## Overview

One of the most valuable use cases of the Desclasificados archive is answering **historical research questions** with evidence from declassified CIA documents. This transforms raw archival data into actionable intelligence for researchers, journalists, historians, and the public.

## The Research Question Pattern

### Concept

A **Research Question** is a specific historical inquiry that can be answered (or partially answered) by evidence contained in the declassified documents. The RAG (Retrieval Augmented Generation) system enables semantic search across thousands of documents to find relevant evidence.

### Key Components

1. **Research Question**: A clear, specific historical question
2. **Evidence Retrieval**: Semantic search to find relevant document chunks
3. **Source Attribution**: Each claim linked to specific documents with metadata
4. **Synthesis**: AI-assisted analysis that connects evidence to answer the question
5. **Balanced Assessment**: Acknowledgment of limitations and alternative factors

### Value Proposition

| Traditional Research | RAG-Powered Research |
|---------------------|---------------------|
| Manual search through 5,666+ documents | Semantic search in seconds |
| Days/weeks to find relevant passages | Relevant excerpts ranked by relevance |
| Easy to miss relevant documents | Comprehensive coverage |
| No cross-referencing | Multiple documents synthesized |
| Requires archival expertise | Accessible to any researcher |

## Document Evidence Format

When citing evidence from declassified documents, include:

### Required Metadata

```
Document ID:      25031
Date:             1976-05-00 (May 1976)
Classification:   TOP SECRET
Type:             REPORT
Author:           CHAPMAN, MARY P.
Relevance Score:  41.63%
URL:              https://declasseuucl.vercel.app/?currentPage=1&documentId=25031
```

### Evidence Presentation

> "Direct quote from the document that supports the claim being made."
>
> — [Document 25031](https://declasseuucl.vercel.app/?currentPage=1&documentId=25031), TOP SECRET Report, May 1976

### URL Format

**Web Viewer URL (preferred):**
```
https://declasseuucl.vercel.app/?currentPage=1&documentId={DOCUMENT_ID}
```

This matches the format used in the GitHub Pages report and opens documents in the web-based PDF viewer with pagination and zoom controls.

**Direct PDF Download (alternative):**
```
https://declasseuucl.vercel.app/api/{DOCUMENT_ID}/download/pdf
```

### Why This Matters

1. **Verifiability**: Readers can locate the original document
2. **Credibility**: Classification level indicates sensitivity/authenticity
3. **Context**: Date and type help interpret the evidence
4. **Transparency**: Relevance score shows search confidence

## Example Research Questions

### Successfully Answered

| Question | Key Finding | Top Source |
|----------|-------------|------------|
| US economic intervention during Allende | $8M+ covert funding, credit blockade | Doc 25031 (TOP SECRET) |
| CIA knowledge of Operation Condor | [To be researched] | — |
| Letelier assassination intelligence | 42.93% relevance match | [See test results] |

### Question Categories

1. **Policy Questions**: What was US policy toward Chile?
2. **Operational Questions**: What specific actions did the CIA take?
3. **Knowledge Questions**: What did the US know about X event?
4. **Timeline Questions**: When did the US learn about X?
5. **Attribution Questions**: Who authorized/knew about X?

## Generating Research Reports

### CLI Workflow

```bash
# 1. Query the RAG system with your research question
uv run python -m app.rag.cli query \
  "Your research question here?" \
  --llm claude \
  --top-k 15 \
  --rag-version 1.0.0

# 2. Run multiple queries to gather comprehensive evidence
uv run python -m app.rag.cli query \
  "Follow-up question for more specific evidence?" \
  --llm claude \
  --top-k 10 \
  --rag-version 1.0.0

# 3. Generate PDF report (see scripts/generate_economic_report.py)
uv run python scripts/generate_economic_report.py
```

### Report Structure

A well-structured research report includes:

```
1. TITLE & METADATA
   - Research question
   - Generation date
   - RAG version and document count

2. RESEARCH QUESTION
   - Clear statement of the question
   - Why this question matters
   - Historical context

3. EVIDENCE SECTIONS
   - Thematic organization
   - Direct quotes with full attribution
   - Document metadata (ID, date, classification, author)
   - Relevance scores

4. DATA TABLES
   - Scale/scope summaries
   - Key document index
   - Timeline of events (if applicable)

5. CONCLUSIONS
   - What the documents prove
   - Limitations and caveats
   - Balanced assessment

6. METHODOLOGY
   - RAG version used
   - Number of documents searched
   - Query parameters
   - LLM used for synthesis
```

## Best Practices

### Formulating Questions

**Good Questions:**
- "What actions did the United States take to destabilize Chile's economy during Allende's government?"
- "What did the CIA know about Operation Condor coordination between South American dictatorships?"
- "Who in the US government authorized covert funding to opposition groups in Chile?"

**Poor Questions:**
- "Tell me about Chile" (too broad)
- "Was the coup bad?" (opinion, not factual)
- "What happened in 1973?" (too vague)

### Handling Limitations

Always acknowledge:

1. **Redactions**: Many documents have redacted sections
2. **Gaps**: Not all documents have been declassified
3. **Bias**: Documents reflect the CIA's perspective
4. **Incompleteness**: Some transcriptions may have OCR errors
5. **Context**: Documents may lack full context

### Ethical Considerations

- Present evidence accurately without distortion
- Acknowledge multiple interpretations when they exist
- Don't overstate conclusions beyond what documents support
- Respect the gravity of historical events discussed
- Make findings accessible for public understanding

## Technical Implementation

### PDF Report Generation

Reports are generated using `reportlab`. See `scripts/generate_economic_report.py` for the template.

Key features:
- Professional formatting with headers and styles
- Quote blocks for document excerpts
- Tables for structured data
- Source attribution throughout
- Methodology section for transparency

### Extending the System

To create a new research report:

1. Copy `scripts/generate_economic_report.py` as template
2. Run RAG queries for your research question
3. Extract key quotes and document metadata from results
4. Update the report content sections
5. Generate PDF

Future enhancements:
- [ ] Automated report generation from RAG queries
- [ ] Interactive web-based report builder
- [ ] Multi-language report generation (Spanish)
- [ ] Citation export (BibTeX, Chicago, etc.)

## Sample Reports

| Report | Question | Location |
|--------|----------|----------|
| US Economic Intervention 1970-1973 | How much was Allende's economic crisis influenced by the US? | `reports/us_economic_intervention_chile_1970-1973.pdf` |

## References

- [RAG System Documentation](../app/rag/README.md)
- [Project Context](PROJECT_CONTEXT.md)
- [Test Query Results](../tests/TEST_QUERIES_RESULTS.md)
