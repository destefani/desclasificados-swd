# Claude Migration Analysis

**Date:** 2025-11-30
**Status:** Investigation & Planning

## Executive Summary

This document analyzes migrating LLM operations from OpenAI to Claude (Anthropic) for the Desclasificados RAG system. The migration requires a **hybrid approach**: Claude for answer generation and vision tasks, while maintaining OpenAI or alternative providers for embeddings.

### Current OpenAI Usage

| Component | Model | Purpose | Monthly Est. |
|-----------|-------|---------|--------------|
| Document Embeddings | text-embedding-3-small | Vector generation for 21k docs | One-time: $40-80 |
| Query Embeddings | text-embedding-3-small | Real-time query vectorization | ~$0.10/1000 queries |
| Answer Generation | gpt-4o-mini | RAG answer synthesis | ~$0.15/query |
| Document Transcription | gpt-4o-mini (vision) | PDF→JSON conversion | One-time: $4k-8k |

**Total Current Monthly**: ~$10-50 (after initial processing)
**One-time Processing**: $4k-8k (full document transcription)

---

## Migration Strategy: Hybrid Approach

### What Can Migrate to Claude ✅

#### 1. Answer Generation (RAG QA Pipeline)
**Current**: OpenAI `gpt-4o-mini` (app/rag/qa_pipeline.py:109)
**Target**: Claude 3.5 Haiku or Claude 3.5 Sonnet

**Reasons to Migrate**:
- ✅ **Longer context window**: Claude 3.5 Sonnet = 200k tokens (vs GPT-4o-mini = 128k)
- ✅ **Better instruction following**: Superior for citation tasks
- ✅ **Lower hallucination rates**: More faithful to source documents
- ✅ **Competitive pricing**: Similar or better than GPT-4o-mini
- ✅ **Extended thinking**: Claude 3.5 Sonnet's extended thinking mode for complex synthesis

**Pricing Comparison (Answer Generation)**:

| Model | Input (MTok) | Output (MTok) | Context | Est. Cost/Query |
|-------|--------------|---------------|---------|-----------------|
| GPT-4o-mini | $0.150 | $0.600 | 128k | $0.12-0.18 |
| Claude 3.5 Haiku | $0.80 | $4.00 | 200k | $0.15-0.25 |
| Claude 3.5 Sonnet | $3.00 | $15.00 | 200k | $0.50-0.80 |

**Recommendation**: Start with **Claude 3.5 Haiku** for cost-effectiveness, upgrade to Sonnet for complex queries.

#### 2. Document Transcription (Vision Tasks)
**Current**: OpenAI `gpt-4o-mini` (app/transcribe_v2.py:25)
**Target**: Claude 3.5 Sonnet (vision)

**Reasons to Migrate**:
- ✅ **Superior vision capabilities**: Better OCR and document understanding
- ✅ **Better structured output**: More reliable JSON schema adherence
- ✅ **Lower error rates**: Better at handling redacted/degraded documents
- ✅ **Batch processing**: Claude supports batch API (50% discount)

**Pricing Comparison (Document Transcription)**:

| Model | Input (MTok) | Output (MTok) | Est. Cost/Doc | Total (21k docs) |
|-------|--------------|---------------|---------------|------------------|
| GPT-4o-mini | $0.150 | $0.600 | $0.20-0.40 | $4,200-8,400 |
| GPT-4o | $2.50 | $10.00 | $1.50-3.00 | $31,500-63,000 |
| Claude 3.5 Sonnet | $3.00 | $15.00 | $1.80-3.60 | $37,800-75,600 |
| Claude 3.5 Sonnet (Batch) | $1.50 | $7.50 | $0.90-1.80 | $18,900-37,800 |

**Recommendation**:
- **Short-term**: Keep GPT-4o-mini for cost (already processed 5,611 docs)
- **Long-term**: Use Claude 3.5 Sonnet Batch API for remaining docs (higher quality, acceptable cost)

### What CANNOT Migrate to Claude ❌

#### 3. Embeddings (Vector Generation)
**Current**: OpenAI `text-embedding-3-small`
**Target**: Cannot migrate - Claude has no embedding API

**Options**:

**Option A: Keep OpenAI Embeddings** (Recommended)
- ✅ Already implemented and tested
- ✅ Proven compatibility with ChromaDB
- ✅ Very low cost ($0.02/MTok)
- ✅ No migration effort
- ❌ Vendor lock-in for embeddings

**Option B: Migrate to Voyage AI**
- ✅ Purpose-built for RAG (better retrieval quality)
- ✅ Competitive pricing ($0.10/MTok)
- ✅ Multiple model sizes
- ❌ Requires code changes
- ❌ Requires regenerating all embeddings (~$700 for 21k docs)

**Option C: Migrate to Cohere Embed**
- ✅ Good multilingual support (English + Spanish)
- ✅ Competitive pricing ($0.10/MTok)
- ✅ Semantic search optimized
- ❌ Requires code changes
- ❌ Requires regenerating all embeddings (~$700 for 21k docs)

**Option D: Open Source Models (HuggingFace)**
- ✅ Free (local inference)
- ✅ Full control and privacy
- ✅ Models: `all-MiniLM-L6-v2`, `e5-large-v2`
- ❌ Requires GPU infrastructure
- ❌ Slower inference
- ❌ Lower quality than commercial models

**Recommendation**: **Keep OpenAI embeddings** for now. Reconsider when:
- Monthly query volume justifies alternative
- Voyage AI proves superior retrieval quality
- Privacy concerns require local embeddings

---

## Implementation Plan

### Phase 1: Answer Generation Migration (IMMEDIATE)

#### 1.1 Add Anthropic SDK
```bash
uv add anthropic
```

#### 1.2 Create Claude QA Module
Create `app/rag/qa_pipeline_claude.py`:

```python
"""Question answering pipeline using Claude."""

import os
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from app.rag.vector_store import VectorStore
from app.rag.retrieval import retrieve_documents

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

QA_SYSTEM_PROMPT = """[Same as current OpenAI prompt]"""

def call_llm_claude(
    prompt: str,
    model: str = "claude-3-5-haiku-20241022"
) -> str:
    """Call Claude to generate an answer."""

    message = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0.3,
        system=QA_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text

def ask_question_claude(
    vector_store: VectorStore,
    question: str,
    top_k: int = 5,
    model: str = "claude-3-5-haiku-20241022",
) -> Dict[str, Any]:
    """End-to-end QA pipeline with Claude."""

    # Retrieve documents (same as before)
    results = retrieve_documents(vector_store, question, top_k=top_k)

    # Build context (same as before)
    context = build_context(results)

    # Generate prompt (same as before)
    prompt = generate_prompt(question, context)

    # Get answer from Claude
    answer = call_llm_claude(prompt, model=model)

    # Format response (same as before)
    return format_answer_with_sources(answer, results)
```

#### 1.3 Update CLI to Support Claude
Modify `app/rag/cli.py`:

```python
@cli.command()
@click.argument("question")
@click.option("--llm", type=click.Choice(["openai", "claude"]), default="claude")
@click.option("--model", default=None, help="Specific model to use")
def query(question: str, llm: str, model: str):
    """Ask a question using the RAG system."""

    store = init_vector_store()

    if llm == "claude":
        from app.rag.qa_pipeline_claude import ask_question_claude
        model = model or "claude-3-5-haiku-20241022"
        response = ask_question_claude(store, question, model=model)
    else:
        from app.rag.qa_pipeline import ask_question
        model = model or "gpt-4o-mini"
        response = ask_question(store, question, model=model)

    # Display results...
```

#### 1.4 Environment Variables
Update `.env`:
```bash
# Existing
OPENAI_API_KEY=your_key_here
OPENAI_TEST_KEY=your_key_here

# New
ANTHROPIC_API_KEY=your_key_here
```

#### 1.5 Testing & Comparison
Run side-by-side comparison:

```bash
# Test with OpenAI
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?" --llm openai

# Test with Claude
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?" --llm claude
```

Compare:
- Answer quality
- Citation accuracy
- Hallucination rate
- Response time
- Cost per query

### Phase 2: Document Transcription Migration (OPTIONAL)

#### 2.1 Create Claude Transcription Module
Create `app/transcribe_claude.py`:

```python
"""Document transcription using Claude vision."""

import base64
import os
from pathlib import Path
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def transcribe_document_claude(image_path: Path) -> dict:
    """Transcribe document image using Claude vision."""

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    # Determine media type
    media_type = "image/png"  # All images are PNG despite .jpg extension

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": TRANSCRIPTION_PROMPT  # Same as current prompt
                    }
                ],
            }
        ],
    )

    # Parse JSON response
    json_text = message.content[0].text
    # Extract JSON from response...

    return parsed_json
```

#### 2.2 Batch Processing for Cost Savings
Use Claude Batch API for 50% discount:

```python
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Create batch requests
batch_requests = []
for image_path in image_paths:
    batch_requests.append({
        "custom_id": str(image_path.stem),
        "params": {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4096,
            "messages": [...]  # Same as above
        }
    })

# Submit batch
batch = client.batches.create(requests=batch_requests)

# Poll for completion
# Process results when ready (24h max)
```

**Cost Savings**:
- Standard: $1.80-3.60/doc × 15,901 docs = $28,622-57,244
- Batch (50% off): $0.90-1.80/doc × 15,901 docs = $14,311-28,622

---

## Cost Analysis: Full Migration

### Scenario 1: Answer Generation Only (Recommended)

**One-time Costs**:
- None (existing embeddings work)

**Ongoing Costs** (per 1,000 queries):
- Embeddings (OpenAI): $0.10
- Answer Generation (Claude 3.5 Haiku): $150-250
- **Total**: ~$150-250/1k queries

**vs Current** (OpenAI):
- Embeddings: $0.10
- Answer Generation (GPT-4o-mini): $120-180
- **Total**: ~$120-180/1k queries

**Verdict**: Slightly more expensive (+$30-70/1k queries) but potentially higher quality.

### Scenario 2: Full Migration (Answer + Transcription)

**One-time Costs**:
- Remaining transcription (15,901 docs): $14,311-28,622 (batch)
- vs Current OpenAI: $3,180-6,360
- **Additional Cost**: +$11,131-22,262

**Ongoing Costs**: Same as Scenario 1

**Verdict**: Significantly more expensive upfront. Only justify if:
- Quality improvement is substantial
- Budget allows for premium processing
- Remaining OpenAI transcripts have unacceptable error rates

### Scenario 3: Hybrid Optimal (Recommended)

**One-time Costs**:
- Keep existing OpenAI transcriptions (5,611 docs)
- Use GPT-4o-mini for remaining docs (15,901 docs): $3,180-6,360
- **Total**: $3,180-6,360

**Ongoing Costs**:
- Use Claude 3.5 Haiku for answers: $150-250/1k queries
- Use OpenAI for embeddings: $0.10/1k queries
- **Total**: $150-260/1k queries

**Verdict**: **Best balance** of cost and quality.

---

## Advantages of Claude for RAG

### 1. Longer Context Windows
- Claude 3.5 Sonnet: 200k tokens
- Can include more retrieved documents
- Better for complex multi-document synthesis

### 2. Better Citation Accuracy
- Superior at following structured output instructions
- More reliable [Doc XXXXX] citation format
- Lower risk of citation hallucination

### 3. Lower Hallucination Rates
- More conservative when information is missing
- Better at saying "I don't know" vs making up facts
- Critical for historical research accuracy

### 4. Extended Thinking Mode
- Claude 3.5 Sonnet supports extended thinking
- Better for complex temporal analysis (e.g., "How did CIA assessment change over time?")
- More thorough multi-step reasoning

### 5. System Prompt Compliance
- Better adherence to system instructions
- More consistent with caveats (e.g., "CIA perspective only")
- Stronger ethical guardrails for sensitive content

---

## Disadvantages / Risks

### 1. No Embedding Support
- Must keep OpenAI or use third-party
- Cannot be fully Claude-only
- Creates vendor dependency

### 2. Higher Cost for Transcription
- 4-5x more expensive than GPT-4o-mini
- Batch API helps but still 2-3x more
- May not justify quality improvement

### 3. Rate Limits
- Claude has stricter rate limits on lower tiers
- May need higher tier for batch processing
- Could slow down bulk operations

### 4. API Differences
- Different API structure vs OpenAI
- More code changes required
- Need to maintain two implementations during transition

---

## Testing Protocol

Before full migration, run comprehensive tests:

### Test 1: Golden Dataset Evaluation
- Run all 6 test queries through both OpenAI and Claude
- Compare:
  - Answer accuracy
  - Citation quality
  - Hallucination detection
  - Caveat inclusion
  - Response time

### Test 2: RAGAS Evaluation
Install RAGAS first:
```bash
uv add ragas
```

Run automated evaluation:
```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

# Test both pipelines
openai_results = evaluate_pipeline(pipeline="openai", questions=test_set)
claude_results = evaluate_pipeline(pipeline="claude", questions=test_set)

# Compare scores
```

### Test 3: Cost Tracking
```python
# Track actual costs
import tiktoken

def estimate_cost(question, answer, model):
    enc = tiktoken.encoding_for_model(model)
    input_tokens = len(enc.encode(question + context))
    output_tokens = len(enc.encode(answer))

    # Calculate cost based on model pricing
    return calculate_cost(input_tokens, output_tokens, model)
```

### Test 4: Transcription Quality
- Transcribe 100 random documents with both models
- Compare:
  - OCR accuracy
  - Metadata extraction quality
  - JSON schema compliance
  - Handling of redactions/degraded text
  - Error rates

---

## Recommendation Summary

### Immediate Action: Migrate Answer Generation
1. ✅ **Add Claude integration** for QA pipeline
2. ✅ **Run A/B testing** on golden dataset
3. ✅ **Keep OpenAI embeddings** (no migration needed)
4. ✅ **Start with Claude 3.5 Haiku** for cost-effectiveness
5. ✅ **Upgrade to Sonnet** for complex queries if needed

**Estimated Timeline**: 1-2 days implementation + 1 week testing

### Later Consideration: Transcription Migration
1. ⏸️ **Wait for evidence** that Claude transcription quality justifies 4-5x cost
2. ⏸️ **Complete OpenAI transcription** of remaining docs first
3. ⏸️ **Re-evaluate** if error rates are unacceptable
4. ⏸️ **Consider batch API** if migration proceeds (50% discount)

**Estimated Timeline**: Hold until quality issues emerge

### Never Migrate: Embeddings
1. ❌ **Keep OpenAI embeddings** (no Claude alternative)
2. ✅ **Monitor** for better embedding providers (Voyage AI, Cohere)
3. ✅ **Re-evaluate** only if:
   - Monthly query volume justifies optimization
   - Privacy concerns require local embeddings
   - Retrieval quality becomes limiting factor

---

## Implementation Checklist

- [ ] Install Anthropic SDK: `uv add anthropic`
- [ ] Add `ANTHROPIC_API_KEY` to `.env`
- [ ] Create `app/rag/qa_pipeline_claude.py`
- [ ] Update `app/rag/cli.py` with `--llm` option
- [ ] Run test queries on golden dataset
- [ ] Compare RAGAS scores (OpenAI vs Claude)
- [ ] Track cost per query for both
- [ ] Document quality differences
- [ ] Decide on default LLM based on results
- [ ] Update documentation (`app/rag/README.md`, `CLAUDE.md`)

---

## Next Steps

1. **Implement Phase 1** (Answer Generation)
2. **Run comprehensive testing**
3. **Document results**
4. **Make data-driven decision** on default LLM
5. **Consider Phase 2** (Transcription) only if justified by testing

---

**Questions?** See:
- Anthropic Docs: https://docs.anthropic.com
- Claude Pricing: https://www.anthropic.com/pricing
- RAGAS Framework: https://docs.ragas.io
