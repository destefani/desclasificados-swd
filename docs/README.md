# Documentation Overview

This directory contains research, design decisions, and contextual information for the Desclasificados project.

## Documents

### [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)
Comprehensive overview of the project including:
- Background on CIA document declassification
- The problem of document volume and accessibility
- Use cases and applications
- Important caveats and limitations
- Ethical considerations
- Project impact goals

### [DATA_INVENTORY.md](./DATA_INVENTORY.md)
Complete inventory of the data directory including:
- 21,512 documents across multiple formats
- Processing pipeline status and completion rates
- Data quality assessment and known issues
- File format details and storage breakdown
- Recommendations for data use and analysis
- Action items for completing the dataset

### [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md)
Detailed plan for implementing a Retrieval-Augmented Generation system including:
- System architecture and data flow
- Technology stack options (ChromaDB, Pinecone, etc.)
- Data preparation strategy
- Four implementation phases (MVP, Enhanced, Production, Advanced)
- Cost analysis and risk assessment
- Success metrics and evaluation criteria
- Complete feature specifications

### [RAG_TESTING_METHODOLOGIES.md](./RAG_TESTING_METHODOLOGIES.md)
Comprehensive research on RAG system evaluation covering:
- Core evaluation frameworks (RAGAS, RAGChecker, TruLens, ARES)
- Evaluation metrics (faithfulness, answer relevancy, context precision/recall)
- Testing methodologies (iterative, component isolation, end-to-end)
- Test dataset creation (golden vs silver datasets, synthetic data)
- Human evaluation best practices
- Production monitoring and continuous testing
- A/B testing strategies
- Tools, platforms, and implementation recommendations
- Based on 50+ authoritative sources from 2024-2025

### [RESEARCH_QUESTIONS.md](./RESEARCH_QUESTIONS.md)
Structured list of 166 research questions answerable using CIA documents:
- The 1973 Coup (15 questions)
- Operation Condor (15 questions)
- DINA and Intelligence Operations (15 questions)
- Human Rights and Repression (15 questions)
- Assassinations and Targeted Killings (15 questions)
- Economic Policy and the Chicago Boys (12 questions)
- US Foreign Policy and CIA Involvement (19 questions)
- Key Figures (18 questions)
- Political Opposition and Resistance (12 questions)
- Regional Context and International Relations (12 questions)
- Transition to Democracy (18 questions)
- Includes methodology notes for RAG evaluation
- Based on historical research from authoritative sources

## Contributing to Documentation

When adding new documentation, please:
1. Use clear, descriptive filenames
2. Include a brief summary in this README
3. Use Markdown formatting for consistency
4. Add cross-references where relevant
5. Update the table of contents as needed

## Documentation Categories

### Project Context (Current)
- Historical background
- Problem statement
- Use cases
- Ethical framework

### Technical Documentation (Current)
- RAG system architecture and implementation
- Evaluation methodologies and testing frameworks
- API documentation (future)
- Data schema specifications (future)
- Performance benchmarks (future)

### Research & Analysis (Current)
- Document collection statistics (DATA_INVENTORY.md)
- Quality assessments (DATA_INVENTORY.md)
- RAG evaluation research (RAG_TESTING_METHODOLOGIES.md)
- Metadata analysis (future)
- Case studies (future)

### User Guides (Future)
- How to query the dataset
- Interpretation guidelines
- Best practices for research
- Citation recommendations
