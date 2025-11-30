# RAG System Implementation Plan
**Declassified CIA Documents Project**

**Created:** 2025-11-30
**Status:** Planning Phase
**Goal:** Enable natural language question answering over 21,512 declassified CIA documents

---

## Executive Summary

This plan outlines the implementation of a Retrieval-Augmented Generation (RAG) system to enable researchers, journalists, and the public to ask natural language questions about declassified CIA documents on the Chilean dictatorship. The system will combine vector similarity search with metadata filtering to retrieve relevant documents and use LLMs to generate accurate, cited answers.

**Key Use Cases:**
- "What did the CIA know about human rights violations in 1975?"
- "How did the CIA assess Pinochet's economic policies?"
- "What was the CIA's involvement in Operation Condor?"
- Fact-checking historical claims against primary sources
- Timeline analysis and pattern discovery

---

## System Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Indexing (One-Time Setup)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  JSON Transcripts (21,512 docs)                             │
│         ↓                                                    │
│  Text Extraction + Chunking                                 │
│         ↓                                                    │
│  Embedding Generation (OpenAI API)                          │
│         ↓                                                    │
│  Vector Database Storage (ChromaDB/Pinecone)                │
│         ↓                                                    │
│  Metadata Index (dates, keywords, people, classification)   │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Query (Runtime)                                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User Question ("What did CIA know about X?")               │
│         ↓                                                    │
│  Query Embedding                                            │
│         ↓                                                    │
│  Hybrid Search:                                             │
│    - Vector Similarity (semantic)                           │
│    - Metadata Filters (date, keywords, classification)      │
│         ↓                                                    │
│  Retrieve Top K Documents (k=5-20)                          │
│         ↓                                                    │
│  Optional: Reranking                                        │
│         ↓                                                    │
│  Context Assembly                                           │
│         ↓                                                    │
│  LLM Generation (GPT-4)                                     │
│         ↓                                                    │
│  Answer + Citations (document IDs, dates, excerpts)         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Option A: Simple & Fast (Recommended for MVP)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Vector DB** | ChromaDB | - Free, open source<br>- Runs locally or hosted<br>- Simple Python API<br>- Built-in metadata filtering<br>- Persistent storage |
| **Embeddings** | OpenAI text-embedding-3-small | - $0.02 per 1M tokens<br>- 1536 dimensions<br>- Good quality/cost ratio<br>- Already using OpenAI |
| **LLM** | GPT-4o-mini | - Already in use<br>- Good for answers<br>- Cost-effective |
| **Framework** | LlamaIndex | - Document-focused<br>- Excellent for Q&A<br>- Built-in chunking<br>- Citation support |
| **Interface** | Streamlit | - Already in use (tests/test_app.py)<br>- Easy to extend |

**Estimated MVP Cost:**
- Initial embedding: ~$0.20 (one-time)
- Query cost: ~$0.0001 per search
- Answer generation: ~$0.01-0.05 per question (GPT-4o-mini)

### Option B: Production Scale

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Vector DB** | Pinecone | - Managed service<br>- Scales to billions of vectors<br>- Fast queries<br>- Built-in hybrid search |
| **Embeddings** | OpenAI text-embedding-3-large | - Higher quality<br>- 3072 dimensions<br>- Better retrieval accuracy |
| **Reranker** | Cohere Rerank API | - Improves precision<br>- Cross-encoder reranking<br>- Multilingual support |
| **LLM** | GPT-4o | - Higher quality answers<br>- Better reasoning<br>- Citation accuracy |
| **Framework** | LangChain | - More integrations<br>- Advanced features<br>- Production-ready |
| **Interface** | Custom FastAPI + React | - Better UX<br>- API for integrations<br>- Mobile-friendly |

**Estimated Production Cost:**
- Pinecone: $70/month (1M vectors, standard plan)
- Embeddings: ~$1.30 for initial load
- Queries: ~$0.001 per search (including reranking)
- Answers: ~$0.05-0.15 per question (GPT-4o)

### Option C: Fully Open Source

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Vector DB** | Weaviate (self-hosted) | - Open source<br>- No vendor lock-in<br>- Advanced features<br>- GraphQL API |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 | - Free (local model)<br>- Fast inference<br>- Good quality for English |
| **LLM** | Llama 3.1 70B (via Ollama) | - Free (self-hosted)<br>- Privacy-preserving<br>- Competitive quality |
| **Framework** | Custom RAG pipeline | - Full control<br>- No external dependencies<br>- Optimized for use case |

**Estimated Cost:**
- Hosting: $50-200/month (GPU instance for Llama)
- No API costs
- Higher development time

---

## Data Preparation Strategy

### Current State Analysis

**Available Data:**
- `generated_transcripts/` - 12 documents (current schema)
- `generated_transcripts_v1/` - 5,611 documents (legacy schema)
- `transcript_text/` - 18,363 plain text files
- `images/` - 21,512 images (for future vision RAG)

**Recommended Approach:**
1. Use `generated_transcripts_v1/` as primary source (best coverage: 26%)
2. Fall back to `transcript_text/` for documents without JSON
3. Continue processing remaining documents with `transcribe_v2.py`
4. Progressive enhancement as new JSONs are created

### Document Processing Pipeline

#### Step 1: Text Extraction

**For JSON files (generated_transcripts_v1/):**
```
Extract fields:
- reviewed_text (primary content)
- original_text (fallback)
- metadata.document_date
- metadata.classification_level
- metadata.document_type
- metadata.keywords
- metadata.people_mentioned
- metadata.country
- metadata.author
- Document ID (from filename)
```

**For plain text files (transcript_text/):**
```
- Load .txt content
- Extract document ID from filename
- Mark as "text-only" (no rich metadata)
```

#### Step 2: Text Chunking

**Strategy:** Sliding window with overlap

```
Chunk size: 512 tokens
Overlap: 128 tokens
Reasoning:
- Balance between context and precision
- Standard for semantic search
- Works well with text-embedding-3-small (8191 token limit)
```

**Chunking Logic:**
```
For each document:
1. Split on paragraph boundaries (preserve context)
2. If paragraph > 512 tokens, split on sentence boundaries
3. Create overlapping chunks
4. Maintain chunk_index and total_chunks metadata
```

**Example:**
```
Document 24736 (2,048 tokens)
→ Chunk 1: tokens 0-512 (chunk 1/4)
→ Chunk 2: tokens 384-896 (chunk 2/4)  [128 overlap]
→ Chunk 3: tokens 768-1280 (chunk 3/4)
→ Chunk 4: tokens 1152-2048 (chunk 4/4)
```

#### Step 3: Metadata Enrichment

**Per Chunk:**
```json
{
  "chunk_id": "24736_chunk_001",
  "document_id": "24736",
  "document_date": "1976-08-27",
  "document_year": 1976,
  "document_month": 8,
  "classification_level": "UNCLASSIFIED",
  "document_type": "TELEGRAM",
  "author": "JACOBSON, MARK",
  "keywords": ["OPERATION CONDOR", "HUMAN RIGHTS"],
  "countries": ["CHILE", "ARGENTINA"],
  "people_mentioned": ["PINOCHET, AUGUSTO"],
  "chunk_index": 1,
  "total_chunks": 4,
  "text": "..."
}
```

**Metadata Index Schema:**
```
- document_date (filterable, sortable)
- year, month (for temporal queries)
- classification_level (filterable)
- document_type (filterable)
- keywords (multi-select filter)
- countries (multi-select filter)
- people_mentioned (multi-select filter)
- has_redactions (boolean, future feature)
```

#### Step 4: Embedding Generation

**Process:**
```
For each chunk:
1. Prepare text: reviewed_text + key metadata in natural language
   Example: "TELEGRAM from JACOBSON, MARK on 1976-08-27 regarding OPERATION CONDOR: [text content]"

2. Call OpenAI embedding API:
   - Model: text-embedding-3-small
   - Input: prepared text
   - Output: 1536-dimensional vector

3. Store in vector database with metadata

4. Rate limiting:
   - 3,000 requests per minute (OpenAI tier 2)
   - Batch processing in groups of 100
   - Retry logic with exponential backoff
```

**Estimated Processing:**
- 21,512 documents
- Average 3 chunks per document = 64,536 chunks
- Processing time: ~2-3 hours (with rate limiting)
- Cost: ~$0.60 for all embeddings

---

## Implementation Phases

### Phase 0: Preparation & Setup (Week 1)

**Tasks:**
1. ✅ Create implementation plan (this document)
2. Install dependencies:
   ```
   uv add llama-index
   uv add chromadb
   uv add openai>=1.0.0
   uv add tiktoken  # token counting
   ```
3. Set up development environment variables:
   ```
   OPENAI_API_KEY=xxx
   CHROMA_DB_PATH=data/vector_db
   EMBEDDING_MODEL=text-embedding-3-small
   LLM_MODEL=gpt-4o-mini
   ```
4. Create project structure:
   ```
   app/rag/
   ├── __init__.py
   ├── config.py
   ├── embeddings.py
   ├── chunking.py
   ├── vector_store.py
   ├── retrieval.py
   ├── qa_pipeline.py
   └── utils.py
   ```

**Deliverables:**
- Environment configured
- Dependencies installed
- Project structure created
- Configuration files ready

---

### Phase 1: MVP - Basic Q&A (Weeks 2-3)

**Goal:** Answer simple questions from 5,611 existing JSON documents

#### Task 1.1: Data Loading & Chunking

**Script:** `app/rag/embeddings.py`

**Functions:**
- `load_json_transcripts(directory)` → Load all JSON files
- `extract_text_and_metadata(json_obj)` → Parse JSON schema
- `chunk_text(text, chunk_size=512, overlap=128)` → Split into chunks
- `create_document_chunks(transcripts)` → Generate chunk objects with metadata

**Output:** List of chunk dictionaries ready for embedding

#### Task 1.2: Embedding Generation

**Script:** `app/rag/embeddings.py`

**Functions:**
- `generate_embeddings(chunks, model="text-embedding-3-small")` → Call OpenAI API
- `batch_embed(chunks, batch_size=100)` → Process in batches with rate limiting
- `save_embeddings(chunks_with_embeddings, output_path)` → Cache results

**Output:** Embedded chunks saved to disk (pickle/json)

#### Task 1.3: Vector Database Setup

**Script:** `app/rag/vector_store.py`

**Functions:**
- `init_chroma_db(persist_directory)` → Initialize ChromaDB
- `add_documents(db, chunks)` → Index all chunks
- `create_metadata_index(db, chunks)` → Set up filtering
- `test_query(db, query)` → Validation queries

**Output:** ChromaDB instance at `data/vector_db/` with all chunks indexed

#### Task 1.4: Basic Retrieval

**Script:** `app/rag/retrieval.py`

**Functions:**
- `semantic_search(query, top_k=5)` → Vector similarity search
- `filter_by_date(results, start_date, end_date)` → Temporal filtering
- `filter_by_keywords(results, keywords)` → Keyword filtering
- `deduplicate_documents(chunks)` → Keep best chunks per document

**Output:** Retrieval pipeline returning ranked document chunks

#### Task 1.5: Q&A Pipeline

**Script:** `app/rag/qa_pipeline.py`

**Functions:**
- `build_context(retrieved_chunks)` → Format context for LLM
- `generate_prompt(question, context)` → Create prompt with instructions
- `call_llm(prompt, model="gpt-4o-mini")` → Get answer
- `format_answer_with_citations(answer, sources)` → Add document references
- `ask_question(question)` → End-to-end pipeline

**Prompt Template:**
```
You are a research assistant analyzing declassified CIA documents about the Chilean dictatorship (1973-1990).

Answer the following question based ONLY on the provided documents. Include specific citations.

QUESTION: {question}

CONTEXT:
{retrieved_documents_with_metadata}

INSTRUCTIONS:
1. Answer based only on the provided documents
2. Cite specific document IDs for all claims
3. If documents don't contain relevant information, say so
4. Note any limitations or gaps in the available information
5. Include dates and classification levels when relevant

ANSWER:
```

**Output:** Function that takes question string, returns answer with citations

#### Task 1.6: CLI Interface

**Script:** `app/rag/cli.py`

**Commands:**
```bash
# Build embeddings
uv run python -m app.rag.cli build --source generated_transcripts_v1

# Query
uv run python -m app.rag.cli query "What did CIA know about Operation Condor?"

# Query with filters
uv run python -m app.rag.cli query "Human rights violations" --year 1976 --keywords "PINOCHET"

# Interactive mode
uv run python -m app.rag.cli interactive
```

**Features:**
- Command parsing with argparse
- Interactive REPL mode
- Citation display
- Query history

**Deliverables:**
- Working Q&A system on 5,611 documents
- CLI interface
- Example queries demonstrated
- Performance metrics (retrieval accuracy, latency)

---

### Phase 2: Enhanced Retrieval (Weeks 4-5)

**Goal:** Improve answer quality and coverage

#### Task 2.1: Hybrid Search

**Enhancement:** Combine vector similarity + BM25 keyword search

**Implementation:**
- Install: `uv add rank-bm25`
- Create BM25 index alongside vector index
- Combine scores with weighted average (0.7 vector + 0.3 BM25)
- Improves recall for specific terms (names, places, dates)

**Rationale:**
- Vector search: good for semantic similarity
- BM25: good for exact term matches
- Hybrid: best of both worlds

#### Task 2.2: Query Rewriting

**Enhancement:** Generate multiple search queries from user question

**Example:**
```
Original: "What did CIA know about Pinochet's human rights abuses?"

Rewritten queries:
1. "Pinochet human rights violations Chile"
2. "CIA intelligence reports disappearances torture Chile"
3. "Augusto Pinochet regime repression 1973-1990"
4. "Secret police DINA political prisoners"
```

**Implementation:**
- Use GPT-4o-mini to generate 3-5 alternative queries
- Retrieve documents for each query
- Merge and deduplicate results
- Increases coverage by 20-30%

#### Task 2.3: Reranking

**Enhancement:** Improve precision of top results

**Options:**

**Option A: Cross-Encoder (Recommended)**
- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Process: Retrieve top 20, rerank to top 5
- Cost: Free (local inference)
- Latency: +100ms

**Option B: Cohere Rerank API**
- Model: `rerank-english-v2.0` or `rerank-multilingual-v2.0`
- Process: Same as Option A
- Cost: $0.002 per 1000 searches
- Latency: +200ms

**Benefit:** 15-25% improvement in answer relevance

#### Task 2.4: Context Window Optimization

**Challenge:** GPT-4o-mini context limit (128k tokens, but optimal ~8k)

**Strategy:**
- Retrieve top 20 candidates
- Rerank to top 5-10
- Intelligently select chunks:
  - Prioritize document diversity (different docs over same doc)
  - Temporal diversity (spread across time period)
  - Source diversity (different authors/classifications)
- Fit within 6k tokens (leave room for question + answer)

**Implementation:**
- Maximal Marginal Relevance (MMR) algorithm
- Balance relevance vs. diversity
- Configurable diversity parameter (λ = 0.5)

#### Task 2.5: Advanced Metadata Filtering

**Enhancement:** Rich filtering language

**Examples:**
```python
# Date range
query("Operation Condor", filters={
    "date_range": ("1976-01-01", "1976-12-31")
})

# Multiple keywords (OR)
query("Pinochet", filters={
    "keywords": ["HUMAN RIGHTS", "TORTURE", "DISAPPEARANCES"]
})

# Classification level
query("Secret operations", filters={
    "classification": ["SECRET", "TOP SECRET"]
})

# People mentioned
query("Chilean military", filters={
    "people": ["PINOCHET, AUGUSTO", "CONTRERAS, MANUEL"]
})

# Complex boolean
query("...", filters={
    "AND": [
        {"year": {"gte": 1976, "lte": 1978}},
        {"keywords": ["OPERATION CONDOR"]},
        {"countries": ["ARGENTINA", "CHILE"]}
    ]
})
```

**Deliverables:**
- Hybrid search implemented
- Query rewriting active
- Reranking pipeline
- Advanced filtering
- A/B testing showing improvement metrics

---

### Phase 3: Production Features (Weeks 6-7)

**Goal:** Production-ready system with full coverage

#### Task 3.1: Full Dataset Processing

**Expand from 5,611 to 21,512 documents**

**Strategy:**
1. Process all `generated_transcripts_v1/` (5,611) ✓ Already done
2. Add `transcript_text/` files without JSON (12,752 additional)
3. Progressive updates as `generated_transcripts/` grows
4. Incremental indexing (add new docs without rebuilding)

**Implementation:**
```python
# Incremental update
def update_index(new_documents):
    """Add new documents without rebuilding entire index"""
    chunks = create_chunks(new_documents)
    embeddings = generate_embeddings(chunks)
    vector_db.add(chunks, embeddings)

# Schedule: run weekly as transcription progresses
```

#### Task 3.2: Streamlit Web Interface

**Extend existing:** `tests/test_app.py`

**Features:**

**Page 1: Q&A Interface**
```
┌────────────────────────────────────────┐
│  Ask a Question                        │
│  [Text input with examples]            │
│                                        │
│  Filters (optional):                   │
│  ☐ Date range: [1976] to [1990]      │
│  ☐ Keywords: [multiselect]            │
│  ☐ Classification: [dropdown]         │
│  ☐ Document type: [dropdown]          │
│                                        │
│  [Ask Question] button                 │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Answer                                │
│  [Generated answer with inline         │
│   citations as links]                  │
│                                        │
│  Sources (5)                           │
│  ├─ Document 24736 (1976-08-27)       │
│  │  TELEGRAM - UNCLASSIFIED            │
│  │  Keywords: OPERATION CONDOR         │
│  │  [View excerpt] [View PDF]          │
│  │                                     │
│  ├─ Document 24850 (1976-09-15)       │
│  ...                                   │
└────────────────────────────────────────┘
```

**Page 2: Document Explorer**
- Browse all indexed documents
- Filter by metadata
- View full text
- Download PDFs

**Page 3: Analytics**
- Query statistics
- Common questions
- Coverage by time period
- Most-cited documents

#### Task 3.3: Citation & Provenance

**Enhancement:** Traceable answers

**Features:**
1. **Document-level citations**
   - Every claim links to specific document ID
   - Format: `[Doc 24736, Aug 27 1976]`

2. **Excerpt highlighting**
   - Show exact passage that supports claim
   - Display context (±2 sentences)

3. **Confidence scoring**
   - Mark low-confidence answers
   - "Based on limited information..."
   - "No documents found matching..."

4. **PDF linking**
   - Click citation → view original PDF
   - Highlight relevant section
   - Show classification stamps, redactions

**Implementation:**
```python
def format_citation(chunk, claim):
    return {
        "document_id": chunk.document_id,
        "date": chunk.document_date,
        "excerpt": extract_relevant_passage(chunk.text, claim),
        "pdf_path": f"data/original_pdfs/{chunk.document_id}.pdf",
        "classification": chunk.classification_level,
        "confidence": calculate_relevance_score(chunk, claim)
    }
```

#### Task 3.4: Caching & Performance

**Optimizations:**

1. **Query cache**
   - Cache exact question matches
   - TTL: 24 hours
   - Storage: Redis or local SQLite
   - Hit rate: ~30-40% for common queries

2. **Embedding cache**
   - Cache query embeddings
   - Deduplication for similar questions
   - Reduces API calls by 20%

3. **Retrieval cache**
   - Cache search results
   - Invalidate on index updates
   - 10x faster for repeat queries

4. **Database optimization**
   - Pre-compute common filters
   - Index on frequently queried fields
   - Connection pooling

**Target Performance:**
- Query latency: <2s (cold) / <500ms (cached)
- Concurrent users: 10-20
- Throughput: 100 queries/minute

#### Task 3.5: Monitoring & Logging

**Metrics to track:**

```python
# Query metrics
- total_queries
- avg_latency
- cache_hit_rate
- retrieval_accuracy (manual eval)

# Usage metrics
- unique_users
- popular_topics
- date_range_distribution
- filter_usage

# System metrics
- embedding_api_calls
- llm_api_calls
- database_size
- query_failures
```

**Logging:**
```python
# app/rag/logger.py
{
    "timestamp": "2025-11-30T10:30:00Z",
    "query": "What did CIA know about Operation Condor?",
    "filters": {"year": 1976},
    "retrieved_docs": 5,
    "latency_ms": 1250,
    "cache_hit": false,
    "user_id": "anonymous_123"
}
```

**Dashboards:**
- Streamlit analytics page
- Export to CSV for analysis
- Alert on failures/errors

**Deliverables:**
- Full 21,512 document coverage
- Streamlit web interface
- Citation system with PDF links
- Caching and performance optimization
- Monitoring and analytics

---

### Phase 4: Advanced Features (Weeks 8-10)

**Goal:** Cutting-edge capabilities

#### Task 4.1: Multi-Modal RAG (Vision + Text)

**Enhancement:** Use original document images, not just text

**Rationale:**
- OCR misses handwritten notes
- Visual context (stamps, redactions, signatures)
- Tables and diagrams
- Deteriorated or low-quality scans

**Implementation:**

1. **Vision Embeddings**
   - Model: CLIP (OpenAI) or GPT-4 Vision
   - Embed `data/images/*.jpg` files
   - Store alongside text embeddings
   - Dual retrieval: text + image similarity

2. **Hybrid Retrieval**
   ```python
   def multimodal_search(query, top_k=5):
       # Text retrieval
       text_results = vector_search(query)

       # Image retrieval (if query mentions visual elements)
       if contains_visual_cues(query):
           image_results = image_search(query)
           results = merge_results(text_results, image_results)

       return results
   ```

3. **Vision-based Q&A**
   - Send retrieved images to GPT-4 Vision
   - Extract information not in OCR text
   - Example: "What stamps appear on this document?"

**Use cases:**
- "Show me documents with TOP SECRET stamps"
- "Find handwritten annotations about Pinochet"
- "Documents with redacted sections on Operation Condor"

**Cost increase:** +$0.01-0.03 per vision-based query

#### Task 4.2: Multilingual Support

**Enhancement:** Spanish/English cross-language search

**Challenge:** Documents are mixed language

**Solutions:**

**Option A: Multilingual Embeddings**
- Model: `multilingual-e5-large` or Cohere multilingual
- Single embedding space for both languages
- Query in Spanish, retrieve English docs (and vice versa)

**Option B: Query Translation**
- Detect query language
- Translate to both English/Spanish
- Search with both queries
- Merge results

**Option C: Dual Indexing**
- Separate indices for English/Spanish docs
- Language detection at index time
- Selective search based on query language

**Recommended:** Option A (multilingual embeddings)

**Example:**
```python
query = "¿Qué sabía la CIA sobre Pinochet?"
# Returns both English and Spanish documents
# Answer generated in Spanish
```

#### Task 4.3: Temporal Analysis

**Enhancement:** Time-aware retrieval

**Features:**

1. **Temporal context**
   ```python
   # What changed over time?
   compare_periods(
       topic="Operation Condor",
       period1="1976-01-01 to 1976-12-31",
       period2="1977-01-01 to 1977-12-31"
   )
   ```

2. **Timeline generation**
   - Auto-generate event timelines
   - Key developments by month/year
   - Frequency analysis (when was topic most discussed?)

3. **Before/after queries**
   ```python
   query_with_temporal_context(
       "CIA assessment of Pinochet",
       before="1973-09-11",  # Coup date
       after="1973-09-11"
   )
   ```

4. **Temporal recency weighting**
   - Boost more recent documents (or older, depending on query)
   - Date-aware ranking

#### Task 4.4: Entity Extraction & Network Analysis

**Enhancement:** Understand relationships

**Implementation:**

1. **Extract entities from all documents**
   - People (PINOCHET, AUGUSTO; KISSINGER, HENRY)
   - Organizations (DINA, CIA, STATE DEPARTMENT)
   - Locations (SANTIAGO, BUENOS AIRES)
   - Events (OPERATION CONDOR, COUP)

2. **Build knowledge graph**
   - Nodes: entities
   - Edges: co-occurrences, relationships
   - Metadata: dates, document types, classification

3. **Graph-based retrieval**
   ```python
   # Who did Pinochet interact with?
   find_connections("PINOCHET, AUGUSTO", max_degree=2)

   # What organizations were involved in Operation Condor?
   find_related_entities("OPERATION CONDOR", entity_type="organization")
   ```

4. **Network visualization**
   - Interactive graph in Streamlit
   - Filter by date range
   - Color by classification level
   - Size by frequency

**Tools:**
- spaCy for entity extraction
- NetworkX for graph analysis
- Pyvis or Plotly for visualization

#### Task 4.5: Conversational RAG (Chat Interface)

**Enhancement:** Multi-turn conversations

**Features:**

1. **Context retention**
   ```
   User: What did CIA know about Operation Condor?
   AI: [Answer with citations]

   User: When did it start?
   AI: [Understands "it" refers to Operation Condor]

   User: Which countries were involved?
   AI: [Continues same context]
   ```

2. **Follow-up questions**
   - Track conversation history
   - Reference previous answers
   - Clarification questions

3. **Summarization**
   - "Summarize the last 5 answers"
   - "What are the key takeaways?"

4. **Chat history**
   - Save sessions
   - Resume conversations
   - Export chat transcripts

**Implementation:**
- Message history in session state
- Context injection in prompts
- Reference resolution (pronouns → entities)

#### Task 4.6: Evaluation & Quality Assurance

**Enhancement:** Systematic quality measurement

**Metrics:**

1. **Retrieval Metrics**
   - Precision@k: Fraction of retrieved docs that are relevant
   - Recall@k: Fraction of relevant docs retrieved
   - MRR (Mean Reciprocal Rank): Position of first relevant doc
   - NDCG (Normalized Discounted Cumulative Gain): Ranking quality

2. **Answer Metrics**
   - Faithfulness: Answer supported by retrieved docs
   - Answer relevance: Directly addresses question
   - Context relevance: Retrieved docs match question

3. **Human Evaluation**
   - Expert review (historians, journalists)
   - Accuracy assessment
   - Citation quality
   - Bias detection

**Evaluation Framework:**

```python
# Create test set
test_questions = [
    {
        "question": "What did CIA know about Operation Condor in 1976?",
        "expected_keywords": ["OPERATION CONDOR", "1976", "CHILE", "ARGENTINA"],
        "expected_doc_ids": [24736, 24850, ...],
        "ground_truth_answer": "..."
    },
    # ... 50-100 questions
]

# Automated evaluation
def evaluate_rag(test_set):
    results = []
    for item in test_set:
        answer, sources = ask_question(item["question"])

        metrics = {
            "retrieval_precision": calculate_precision(sources, item["expected_doc_ids"]),
            "retrieval_recall": calculate_recall(sources, item["expected_doc_ids"]),
            "answer_faithfulness": check_faithfulness(answer, sources),
            "keyword_coverage": check_keywords(answer, item["expected_keywords"])
        }
        results.append(metrics)

    return aggregate_metrics(results)
```

**Continuous Improvement:**
- Weekly evaluation runs
- A/B testing new retrieval strategies
- User feedback collection (👍👎 on answers)
- Failure analysis and iteration

**Deliverables:**
- Multi-modal RAG with vision support
- Spanish/English cross-language search
- Temporal analysis features
- Entity extraction and network graph
- Conversational chat interface
- Comprehensive evaluation framework

---

## Data Pipeline Integration

### Interaction with Existing Systems

```
┌──────────────────────────────────────────────────────────────┐
│ Existing Pipeline                                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  PDFs → Images → Transcription (transcribe_v2.py)           │
│                          ↓                                   │
│                  generated_transcripts/*.json                │
│                                                              │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────────────────┐
│ NEW: RAG Pipeline                                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Watch generated_transcripts/ directory                      │
│         ↓                                                    │
│  On new JSON file:                                           │
│    1. Extract text + metadata                                │
│    2. Chunk document                                         │
│    3. Generate embeddings                                    │
│    4. Add to vector database                                 │
│         ↓                                                    │
│  Incremental update (no full rebuild)                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Automated Sync

**Script:** `app/rag/sync.py`

```python
# Pseudo-code
def watch_and_sync():
    """Monitor transcripts directory and auto-index new documents"""

    while True:
        new_files = find_new_transcripts()

        if new_files:
            logger.info(f"Found {len(new_files)} new transcripts")

            # Process new files
            chunks = process_transcripts(new_files)
            embeddings = generate_embeddings(chunks)
            add_to_vector_db(chunks, embeddings)

            # Update metadata index
            update_search_filters()

            logger.info("Index updated successfully")

        time.sleep(300)  # Check every 5 minutes
```

**Deployment:**
- Run as background service
- Systemd unit or Docker container
- Health checks and monitoring
- Error notifications (Slack/email)

---

## Cost Analysis

### One-Time Setup Costs

| Item | Quantity | Unit Cost | Total |
|------|----------|-----------|-------|
| Initial embeddings (21,512 docs, 64k chunks) | 64,536 chunks × 500 tokens avg | $0.02 per 1M tokens | **$0.65** |
| Development time | 80 hours | $100/hour (contractor) | $8,000 |
| **Total Setup** | | | **~$8,000.65** |

### Monthly Operating Costs (MVP)

| Item | Estimate | Cost |
|------|----------|------|
| Query embeddings | 1,000 queries/month | $0.01 |
| Answer generation (GPT-4o-mini) | 1,000 queries × $0.03 avg | $30.00 |
| ChromaDB hosting | Self-hosted (free) | $0 |
| Monitoring/logs | Included | $0 |
| **Monthly Total (MVP)** | | **~$30** |

### Monthly Operating Costs (Production)

| Item | Estimate | Cost |
|------|----------|------|
| Pinecone (1M vectors, standard) | Fixed | $70.00 |
| Query embeddings | 10,000 queries/month | $0.10 |
| Reranking (Cohere) | 10,000 queries | $20.00 |
| Answer generation (GPT-4o) | 10,000 queries × $0.08 avg | $800.00 |
| Server hosting (Streamlit) | 2 vCPU, 4GB RAM | $40.00 |
| **Monthly Total (Production)** | | **~$930** |

### Cost per Query

| Configuration | Cost per Query |
|---------------|----------------|
| MVP (ChromaDB + GPT-4o-mini) | $0.03 |
| Production (Pinecone + GPT-4o) | $0.09 |
| High-volume (10k+ queries/month) | $0.06 (volume discounts) |

---

## Risk Assessment & Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Poor retrieval quality** | Medium | High | - Use hybrid search<br>- Implement reranking<br>- Continuous evaluation<br>- A/B testing |
| **Hallucinations in answers** | Medium | High | - Strict prompts ("only from documents")<br>- Citation requirements<br>- Confidence scoring<br>- Human review for critical queries |
| **Scalability bottlenecks** | Low | Medium | - Start with ChromaDB (handles 1M+ vectors)<br>- Migrate to Pinecone if needed<br>- Caching layer<br>- Load testing |
| **API rate limits** | Low | Low | - Implement backoff/retry<br>- Request batching<br>- Cache frequently accessed data |
| **OCR errors propagate** | High | Medium | - Use reviewed_text (corrected)<br>- Flag low-confidence extractions<br>- Multi-modal fallback (vision) |

### Data Quality Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Incomplete metadata (v1 JSONs)** | High | Medium | - Use available metadata<br>- Fall back to text-only<br>- Progressive enhancement as v2 JSONs created |
| **Date inconsistencies** | High | Low | - Normalize dates at index time<br>- Use date ranges for robustness<br>- Flag [unknown] dates |
| **Mixed language content** | Medium | Medium | - Use multilingual embeddings<br>- Language detection<br>- Separate indices if needed |
| **Missing documents (3,149 no text)** | Medium | Low | - Use images for vision RAG<br>- Flag gaps in coverage<br>- Continue transcription efforts |

### Ethical & Accuracy Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Misinterpretation of sensitive content** | Medium | High | - Disclaimer: "CIA perspective only"<br>- Encourage cross-referencing<br>- Clear limitations in UI<br>- Expert review process |
| **Decontextualization** | Medium | Medium | - Provide full document context<br>- Show surrounding text<br>- Link to original PDFs<br>- Metadata visible |
| **Bias amplification** | Low | Medium | - Prompt engineering for neutrality<br>- Diverse test questions<br>- Bias audits<br>- User feedback |
| **Privacy concerns** | Low | Low | - Documents already declassified<br>- Follow FOIA guidelines<br>- Respect existing redactions |

---

## Success Metrics

### Phase 1 (MVP)

- ✅ System answers 80% of test questions correctly
- ✅ Average retrieval precision@5 > 0.6
- ✅ All answers include document citations
- ✅ Query latency < 3 seconds
- ✅ Zero hallucinations (claims without document support)

### Phase 2 (Enhanced)

- ✅ Hybrid search improves precision by 15%+
- ✅ Reranking improves answer quality by 20%+
- ✅ Advanced filtering works for 95%+ of metadata fields
- ✅ System covers all 21,512 documents

### Phase 3 (Production)

- ✅ Web interface handles 50+ concurrent users
- ✅ 95%+ uptime
- ✅ User satisfaction > 4/5 (survey)
- ✅ 100+ real-world queries successfully answered
- ✅ Citation accuracy > 95%

### Phase 4 (Advanced)

- ✅ Multi-modal search improves coverage by 10%+
- ✅ Temporal analysis supports historical research workflows
- ✅ Network graph surfaces 50+ new connections
- ✅ Conversational interface sustains 5+ turn conversations
- ✅ Expert validation: 90%+ accuracy on historical questions

---

## Maintenance & Operations

### Ongoing Tasks

**Weekly:**
- Monitor query performance
- Review failed/low-quality queries
- Check system health metrics
- User feedback review

**Monthly:**
- Evaluate answer quality on test set
- Update embeddings for new documents
- Performance optimization
- Cost analysis

**Quarterly:**
- Full evaluation with domain experts
- System architecture review
- Feature prioritization
- User interviews

### Update Procedures

**Adding new documents:**
```bash
# New transcripts available
make transcribe  # Generate JSON

# Sync to RAG system
uv run python -m app.rag.sync

# Verify
uv run python -m app.rag.cli test-coverage
```

**Model updates:**
```bash
# Test new embedding model
uv run python -m app.rag.test-model --model text-embedding-3-large

# If better, rebuild index
uv run python -m app.rag.rebuild --model text-embedding-3-large

# A/B test in production
uv run python -m app.rag.ab-test --control old --treatment new
```

**Prompt improvements:**
```bash
# Edit prompt template
vim app/rag/prompts.py

# Test on validation set
uv run python -m app.rag.evaluate --prompt-version v2

# Deploy if better
git commit -m "Improve QA prompt for citation accuracy"
```

---

## Team & Skills Required

### For MVP (Phase 1)

**Roles:**
- 1 Python developer with ML experience (80 hours)

**Skills needed:**
- Python, LangChain/LlamaIndex
- OpenAI API
- Vector databases (ChromaDB)
- Basic NLP concepts

### For Production (Phases 2-3)

**Roles:**
- 1 ML engineer (120 hours)
- 1 Full-stack developer for Streamlit (40 hours)
- 1 DevOps engineer for deployment (20 hours)

**Skills needed:**
- Advanced RAG techniques
- Frontend development
- Cloud deployment (AWS/GCP)
- Performance optimization

### For Advanced Features (Phase 4)

**Roles:**
- 1 Research engineer (80 hours)
- 1 Domain expert (historian) for evaluation (20 hours)
- 1 UX designer for interface (20 hours)

**Skills needed:**
- Multi-modal ML
- NLP research
- Historical research methods
- User experience design

---

## Alternative Approaches Considered

### 1. Fine-Tuned LLM (Rejected)

**Approach:** Fine-tune GPT-3.5/4 on document corpus

**Pros:**
- No retrieval step needed
- Potentially faster
- More natural answers

**Cons:**
- ❌ No citations/provenance
- ❌ Hallucination risk higher
- ❌ Expensive to update ($1000+ per update)
- ❌ Can't easily update with new docs
- ❌ Harder to debug wrong answers

**Verdict:** RAG better for this use case (citations critical)

### 2. Keyword Search Only (Rejected)

**Approach:** Traditional search engine (Elasticsearch)

**Pros:**
- Fast and reliable
- Exact match guarantees
- Lower cost

**Cons:**
- ❌ No semantic understanding
- ❌ Requires exact terminology
- ❌ No natural language answers
- ❌ User must read all documents

**Verdict:** Doesn't solve accessibility problem

### 3. Zero-Shot LLM (Rejected)

**Approach:** Prompt GPT-4 without retrieval

**Pros:**
- Simple to implement
- Good general knowledge

**Cons:**
- ❌ Knowledge cutoff (Jan 2025)
- ❌ Doesn't use your documents
- ❌ Will hallucinate specifics
- ❌ No access to declassified info

**Verdict:** Defeats purpose of having documents

### 4. Graph Database Only (Rejected)

**Approach:** Neo4j knowledge graph

**Pros:**
- Excellent for relationships
- Complex queries possible
- Visual exploration

**Cons:**
- ❌ Requires extensive entity extraction
- ❌ Doesn't handle unstructured text well
- ❌ No semantic search
- ❌ Steep learning curve

**Verdict:** Could be Phase 4 addition, not replacement

---

## Conclusion & Recommendation

### Recommended Path

**Start:** Phase 1 MVP with ChromaDB + LlamaIndex (2-3 weeks)
**Evaluate:** User testing with historians/journalists
**Iterate:** Phase 2 enhancements based on feedback (2 weeks)
**Deploy:** Phase 3 production features (2 weeks)
**Expand:** Phase 4 advanced features as needed (ongoing)

### Why This Plan

1. **Aligned with project goals:** Directly enables Q&A and fact-checking use cases
2. **Scalable:** Start simple, add complexity as needed
3. **Cost-effective:** MVP costs <$100/month to operate
4. **Measurable:** Clear success metrics at each phase
5. **Flexible:** Can pivot based on user feedback

### Next Immediate Steps

1. Review this plan with stakeholders
2. Allocate development time/resources
3. Set up development environment
4. Begin Phase 0 (setup) immediately
5. Target Phase 1 completion in 3 weeks

---

## References & Resources

### Documentation
- LlamaIndex: https://docs.llamaindex.ai/
- ChromaDB: https://docs.trychroma.com/
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings

### Academic Papers
- "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al., 2020)
- "Dense Passage Retrieval for Open-Domain Question Answering" (Karpukhin et al., 2020)
- "RAG vs Fine-tuning: Pipelines, Tradeoffs, and a Case Study" (Jiang et al., 2024)

### Similar Projects
- ChatPDF: Document Q&A system
- Perplexity AI: RAG for web search
- NotebookLM: RAG for research documents

### Code Examples
- LlamaIndex RAG tutorial: https://github.com/run-llama/llama_index/tree/main/docs/examples
- ChromaDB quickstart: https://docs.trychroma.com/getting-started

---

**Document Version:** 1.0
**Last Updated:** 2025-11-30
**Author:** Implementation Planning
**Review Status:** Draft - Pending stakeholder review
