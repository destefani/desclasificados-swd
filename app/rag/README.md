# RAG System for Declassified CIA Documents

This module implements a Retrieval-Augmented Generation (RAG) system for querying declassified CIA documents about the Chilean dictatorship (1973-1990).

## Architecture

The RAG system consists of several components:

1. **embeddings.py** - Data loading, text chunking, and embedding generation
2. **vector_store.py** - ChromaDB vector database operations
3. **retrieval.py** - Semantic search and document retrieval
4. **qa_pipeline.py** - Question-answering pipeline with OpenAI
5. **qa_pipeline_claude.py** - Question-answering pipeline with Claude (Anthropic)
6. **cli.py** - Command-line interface
7. **config.py** - Configuration settings

## LLM Selection

The system supports two LLM providers for answer generation:

- **Claude (Anthropic)** - Default, recommended for better citation accuracy and lower hallucination
- **OpenAI** - Alternative option, uses GPT-4o-mini

**Note**: Embeddings always use OpenAI's `text-embedding-3-small` regardless of LLM choice (Claude does not offer embeddings).

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
# Simple query (uses Claude by default)
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?"

# Use OpenAI instead
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?" --llm openai

# Use specific Claude model
uv run python -m app.rag.cli query "Complex question..." --llm claude --model claude-3-5-sonnet-20241022

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
# Use Claude (default)
uv run python -m app.rag.cli interactive

# Use OpenAI
uv run python -m app.rag.cli interactive --llm openai

# Use specific model
uv run python -m app.rag.cli interactive --llm claude --model claude-3-5-sonnet-20241022
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

### Environment Variables

Create a `.env` file (see `.env.example`):

```bash
# Required for embeddings and OpenAI mode
OPENAI_API_KEY=your_openai_api_key_here

# Required for Claude mode (default)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

Get your API keys:
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys

### Code Configuration

Edit `app/rag/config.py` to customize:

```python
# Chunking
CHUNK_SIZE = 512          # tokens per chunk
CHUNK_OVERLAP = 128       # overlapping tokens

# Retrieval
DEFAULT_TOP_K = 5         # default number of documents to retrieve
MAX_CONTEXT_TOKENS = 6000 # max context for LLM

# OpenAI Models
EMBEDDING_MODEL = "text-embedding-3-small"  # Used for all embeddings
LLM_MODEL = "gpt-4o-mini"                    # Used when --llm openai

# Claude Models
CLAUDE_MODEL = "claude-3-5-haiku-20241022"   # Used when --llm claude (default)
CLAUDE_MODEL_SONNET = "claude-3-5-sonnet-20241022"  # For complex queries
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

**With Claude 3.5 Haiku (default)**:
- Query embedding (OpenAI): ~$0.0001
- Answer generation (Claude): ~$0.02-0.03
- **Total per query: ~$0.02-0.03**

**With Claude 3.5 Sonnet (complex queries)**:
- Query embedding (OpenAI): ~$0.0001
- Answer generation (Claude): ~$0.06-0.10
- **Total per query: ~$0.06-0.10**

**With OpenAI GPT-4o-mini**:
- Query embedding: ~$0.0001
- Answer generation: ~$0.02-0.03
- **Total per query: ~$0.02-0.03**

### Monthly Costs (Estimated with Claude Haiku)
- 100 queries/month: ~$2-3
- 1,000 queries/month: ~$20-30
- 10,000 queries/month: ~$200-300

ChromaDB storage is free (local/self-hosted).

**Note**: Claude offers better citation accuracy and lower hallucination rates, making it the recommended choice despite similar pricing to OpenAI.

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
from app.rag.qa_pipeline_claude import ask_question_claude  # or qa_pipeline for OpenAI

# Initialize
vector_store = init_vector_store()

# Query with Claude (recommended)
result = ask_question_claude(
    vector_store=vector_store,
    question="What did CIA know about Operation Condor?",
    top_k=5,
    date_range=("1976-01-01", "1976-12-31"),
    keywords=["OPERATION CONDOR"],
    model="claude-3-5-haiku-20241022",  # Optional, uses default if not specified
)

# Or use OpenAI
from app.rag.qa_pipeline import ask_question
result = ask_question(
    vector_store=vector_store,
    question="What did CIA know about Operation Condor?",
    top_k=5,
    model="gpt-4o-mini",
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

## LLM Provider Comparison

| Feature | Claude 3.5 Haiku | Claude 3.5 Sonnet | OpenAI GPT-4o-mini |
|---------|------------------|-------------------|-------------------|
| **Context Window** | 200k tokens | 200k tokens | 128k tokens |
| **Cost/Query** | ~$0.02-0.03 | ~$0.06-0.10 | ~$0.02-0.03 |
| **Citation Accuracy** | Excellent | Excellent | Good |
| **Hallucination Rate** | Very Low | Very Low | Low |
| **Speed** | Fast | Moderate | Fast |
| **Best For** | Most queries | Complex analysis | Alternative option |

**Recommendation**: Use **Claude 3.5 Haiku** (default) for most queries, upgrade to **Sonnet** for complex temporal analysis or multi-document synthesis.

## Future Enhancements

See `docs/RAG_IMPLEMENTATION_PLAN.md` for planned features:

- **Phase 2**: Hybrid search (BM25 + vector), query rewriting, reranking
- **Phase 3**: Streamlit web interface, caching, monitoring
- **Phase 4**: Multi-modal RAG (vision), multilingual support, entity extraction

## References

- [Claude Migration Analysis](../../docs/CLAUDE_MIGRATION_ANALYSIS.md)
- [RAG Implementation Plan](../../docs/RAG_IMPLEMENTATION_PLAN.md)
- [Project Context](../../docs/PROJECT_CONTEXT.md)
- [Data Inventory](../../docs/DATA_INVENTORY.md)
- [RAG Testing Methodologies](../../docs/RAG_TESTING_METHODOLOGIES.md)
