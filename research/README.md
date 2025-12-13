# Research Directory

This directory contains research notes, analyses, and findings for the Chilean declassified CIA documents project. Research here falls into two main categories:

1. **Technical Research** - Investigation of algorithms, methods, and software implementations
2. **Historical Research** - Analysis and findings from the CIA documents themselves

## Purpose

The research directory serves as a repository for:

### Technical Research
- Algorithm exploration and comparisons (e.g., RAG approaches, LLM performance)
- Software architecture investigations
- Performance benchmarking and optimization studies
- Machine learning methods and experiments
- OCR and vision model evaluations
- Embedding and retrieval technique comparisons

### Historical Research
- Document findings and insights
- Thematic investigations (Operation Condor, human rights, political interference)
- Case studies (Letelier assassination, Caravan of Death, etc.)
- Chronological analyses and timelines
- Network analysis (people, organizations, relationships)
- Academic papers and citations
- Preliminary findings and hypotheses

## Current Structure

```
research/
├── README.md                           # This file
│
├── technical/                          # Technical research
│   ├── batch-processing/               # Batch transcription implementation
│   │   ├── PHASE1_IMPLEMENTATION.md    # Full pass processing implementation
│   │   └── VALIDATION_BATCH_RESULTS.md # Batch validation results (100 docs)
│   │
│   ├── prompts/                        # Prompt engineering research
│   │   ├── PROMPT_IMPROVEMENT_PLAN.md  # Prompt optimization strategy
│   │   ├── PROMPT_MANAGEMENT_RESEARCH.md # Best practices research
│   │   └── IMPLEMENTATION_SUMMARY.md   # Implementation summary
│   │
│   ├── rag-methods/                    # RAG implementation studies
│   │   └── agentic-search.md           # Agentic search paradigm research
│   │
│   └── visualizations/                 # Visualization research
│       ├── README.md                   # Visualizations overview
│       ├── VISUALIZATIONS_RESEARCH.md  # Visualization strategies
│       └── TIMELINE_PLAN.md            # Timeline implementation plan
│
├── investigations/                     # Issue tracking & debugging
│   ├── README.md                       # Investigation index & template
│   ├── 001-empty-reviewed-text.md      # Empty reviewed_text issue
│   ├── 002-low-chars-per-page-documents.md  # Low chars/page ratio
│   ├── 003-batch-api-implementation.md # Batch API (50% cost savings)
│   ├── 004-gpt5-mini-quality-evaluation.md  # GPT-5-mini evaluation
│   └── assets/                         # Supporting files for investigations
│
└── historical/                         # Historical research
    ├── README.md                       # Historical research overview
    ├── RESEARCH_PLAN.md               # Comprehensive research plan
    ├── themes/                         # Thematic research areas
    │   ├── operation-condor/          # Regional intelligence coordination
    │   ├── human-rights/              # Human rights violations
    │   ├── political-interference/    # US intervention in Chilean politics
    │   ├── economic-policy/           # Economic warfare and influence
    │   └── media-propaganda/          # Media manipulation and psyops
    ├── cases/                          # Specific case studies
    │   ├── letelier-assassination/    # Orlando Letelier murder (1976)
    │   ├── caravan-of-death/          # Caravana de la Muerte (1973)
    │   ├── allende-overthrow/         # Coup planning (1970-1973)
    │   └── dina-operations/           # DINA intelligence operations
    ├── timelines/                      # Chronological analyses
    ├── networks/                       # Network analysis (people, orgs)
    ├── literature/                     # Academic papers, bibliographies
    └── findings/                       # Consolidated findings
```

## Guidelines

- Use markdown for all research notes
- Include sources and citations in all documents
- Date your research entries
- Cross-reference related research files
- Link to specific transcripts using relative paths when referencing documents

## Relationship to Other Directories

- **docs/** - Project documentation, implementation guides, technical specifications, formal documentation
- **research/technical/** - Experimental technical investigations, algorithm comparisons, performance studies
- **research/historical/** - Historical analysis, document findings, thematic investigations
- **notebooks/** - Jupyter notebooks for exploratory data analysis and quick experiments
- **data/generated_transcripts/** - Source material for historical research
- **app/** - Production code implementations
- **tests/** - Automated tests and test applications

## Getting Started

Create subdirectories as needed based on your research focus. Each major research area should have its own directory with a README explaining the scope and findings.
