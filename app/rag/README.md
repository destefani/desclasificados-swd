# RAG System for Declassified CIA Documents

This module implements a Retrieval-Augmented Generation (RAG) system for querying declassified CIA documents about the Chilean dictatorship (1973-1990).

## Architecture

The RAG system consists of several components:

1. **embeddings.py** - Data loading, text chunking, and embedding generation
2. **vector_store.py** - ChromaDB vector database operations
3. **retrieval.py** - Semantic search and document retrieval
4. **qa_pipeline.py** - Question-answering pipeline with LLM
5. **cli.py** - Command-line interface
6. **config.py** - Configuration settings

## Quick Start

### 1. Build the Index

First, build the vector database from existing transcripts:

```bash
# Build from all available transcripts
uv run python -m app.rag.cli build

# Reset and rebuild
uv run python -m app.rag.cli build --reset
```

This will:
- Load transcripts from `data/generated_transcripts_v1/` and `data/generated_transcripts/`
- Chunk documents into 512-token segments with 128-token overlap
- Generate embeddings using OpenAI's `text-embedding-3-small`
- Store in ChromaDB at `data/vector_db/`

**Note**: Initial build with 5,611 documents (~17,000 chunks) takes approximately 10-15 minutes and costs ~$0.60 in API fees.

### 2. Query the System

Ask questions using the CLI:

```bash
# Simple query
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?"

# Query with filters
uv run python -m app.rag.cli query "Human rights violations" --start-date 1976-01-01 --end-date 1976-12-31

# Query with keyword filter
uv run python -m app.rag.cli query "Pinochet" --keywords "OPERATION CONDOR,HUMAN RIGHTS"

# Retrieve more documents
uv run python -m app.rag.cli query "CIA assessment of Pinochet" --top-k 10
```

### 3. Interactive Mode

For exploratory research, use interactive mode:

```bash
uv run python -m app.rag.cli interactive
```

Commands in interactive mode:
- Type any question to query the system
- `help` - Show available commands
- `exit`, `quit`, `q` - Exit interactive mode

### 4. Database Statistics

Check the database status:

```bash
uv run python -m app.rag.cli stats
```

## Usage Examples

### Example 1: Historical Question

```bash
uv run python -m app.rag.cli query "What was the CIA's assessment of Pinochet's economic policies?"
```

**Output:**
```
ANSWER:
Based on the provided documents, the CIA assessed Pinochet's economic policies as...
[Doc 24850] indicates that... [Doc 25123] notes that...

SOURCES (5 documents):
1. Document 24850
   Date: 1976-09-15
   Type: INTELLIGENCE BRIEF
   Classification: SECRET
   ...
```

### Example 2: Time-Filtered Query

```bash
uv run python -m app.rag.cli query "Operation Condor activities" \
  --start-date 1976-01-01 \
  --end-date 1976-12-31 \
  --keywords "OPERATION CONDOR"
```

### Example 3: Fact-Checking

```bash
uv run python -m app.rag.cli query "Did the CIA have advance knowledge of the Letelier assassination?"
```

## Configuration

Edit `app/rag/config.py` to customize:

```python
# Chunking
CHUNK_SIZE = 512          # tokens per chunk
CHUNK_OVERLAP = 128       # overlapping tokens

# Retrieval
DEFAULT_TOP_K = 5         # default number of documents to retrieve
MAX_CONTEXT_TOKENS = 6000 # max context for LLM

# Models
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"
```

## Data Sources

The system loads data from multiple sources in priority order:

1. `data/generated_transcripts/` - Current schema (v2)
2. `data/generated_transcripts_v1/` - Legacy schema
3. `data/transcript_text/` - Plain text fallback (TODO)

## Cost Estimates

### One-Time Setup
- Embedding generation (5,611 docs): ~$0.60
- Total setup: **~$0.60**

### Per-Query Costs
- Query embedding: ~$0.0001
- Answer generation (GPT-4o-mini): ~$0.02-0.03
- **Total per query: ~$0.03**

### Monthly Costs (Estimated)
- 100 queries/month: ~$3
- 1,000 queries/month: ~$30
- 10,000 queries/month: ~$300

ChromaDB storage is free (local/self-hosted).

## Architecture Details

### Document Processing Pipeline

```
1. Load JSON transcripts
   ↓
2. Extract text and metadata
   ↓
3. Chunk into 512-token segments (128 overlap)
   ↓
4. Generate embeddings (OpenAI API)
   ↓
5. Store in ChromaDB with metadata
```

### Query Pipeline

```
1. User question
   ↓
2. Generate query embedding
   ↓
3. Semantic search in ChromaDB
   ↓
4. Apply metadata filters (date, keywords)
   ↓
5. Build context from top-k chunks
   ↓
6. Generate answer with LLM
   ↓
7. Format answer + citations
```

### Metadata Schema

Each chunk stores:
- `document_id` - Source document ID
- `chunk_index` - Position within document
- `document_date` - ISO 8601 date
- `classification_level` - Security classification
- `document_type` - Document type
- `author` - Document author
- `keywords` - Thematic keywords
- `countries` - Countries mentioned
- `people_mentioned` - People mentioned

## Advanced Usage

### Programmatic Usage

```python
from app.rag.vector_store import init_vector_store
from app.rag.qa_pipeline import ask_question

# Initialize
vector_store = init_vector_store()

# Query
result = ask_question(
    vector_store=vector_store,
    question="What did CIA know about Operation Condor?",
    top_k=5,
    date_range=("1976-01-01", "1976-12-31"),
    keywords=["OPERATION CONDOR"],
)

print(result["answer"])
for source in result["sources"]:
    print(f"- {source['document_id']}: {source['excerpt']}")
```

### Incremental Updates

When new transcripts are created, update the index:

```python
from app.rag.embeddings import load_json_transcripts, create_document_chunks, generate_embeddings
from app.rag.vector_store import init_vector_store

# Load new transcripts
new_transcripts = load_json_transcripts(Path("data/generated_transcripts"))

# Process
chunks = create_document_chunks(new_transcripts)
chunks_with_embeddings = generate_embeddings(chunks)

# Add to existing database
vector_store = init_vector_store()
vector_store.add_documents(chunks_with_embeddings)
```

## Troubleshooting

### "Vector database is empty"
Run `uv run python -m app.rag.cli build` to create the index.

### "No transcripts found"
Ensure `data/generated_transcripts_v1/` contains JSON files.

### Rate limit errors
Adjust `EMBEDDING_RPS` in `config.py` based on your OpenAI tier.

### Out of memory
Reduce `EMBEDDING_BATCH_SIZE` in `config.py`.

## Future Enhancements

See `docs/RAG_IMPLEMENTATION_PLAN.md` for planned features:

- **Phase 2**: Hybrid search (BM25 + vector), query rewriting, reranking
- **Phase 3**: Streamlit web interface, caching, monitoring
- **Phase 4**: Multi-modal RAG (vision), multilingual support, entity extraction

## References

- [RAG Implementation Plan](../../docs/RAG_IMPLEMENTATION_PLAN.md)
- [Project Context](../../docs/PROJECT_CONTEXT.md)
- [Data Inventory](../../docs/DATA_INVENTORY.md)
