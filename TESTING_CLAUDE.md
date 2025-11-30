# Testing Claude Integration

This guide helps you verify that the Claude integration is working correctly.

## Quick Test

Once you've added your `ANTHROPIC_API_KEY` to `.env`, run:

```bash
# Comprehensive test suite
uv run python test_claude_integration.py
```

This will test:
- ✅ API key configuration
- ✅ Module imports
- ✅ Anthropic client initialization
- ✅ Vector database access
- ✅ End-to-end query with Claude
- ✅ Comparison with OpenAI (optional)

## Manual Testing

### Test 1: Simple Query with Claude (Default)

```bash
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?"
```

**Expected output:**
```
Database loaded: 6929 chunks
LLM: claude
================================================================================
Retrieving relevant documents for: 'What did the CIA know about Operation Condor?'
Retrieved 3 relevant documents
Generating answer using claude-3-5-haiku-20241022...

================================================================================
ANSWER:
================================================================================
[Detailed answer with citations like [Doc 25029], [Doc 25024]]

================================================================================
SOURCES (3 documents):
================================================================================
1. Document 25029
   Date: AUG 76
   Type: TELEGRAM
   ...
```

### Test 2: Compare Claude vs OpenAI

```bash
# With Claude (default)
uv run python -m app.rag.cli query "What was the CIA's relationship with Manuel Contreras?"

# With OpenAI
uv run python -m app.rag.cli query "What was the CIA's relationship with Manuel Contreras?" --llm openai
```

Compare:
- Citation quality ([Doc XXXXX] format)
- Hallucination (does it make up info not in docs?)
- Caveats (does it acknowledge gaps?)
- Response quality

### Test 3: Interactive Mode

```bash
# With Claude
uv run python -m app.rag.cli interactive

# With OpenAI
uv run python -m app.rag.cli interactive --llm openai
```

Try multiple questions in sequence:
1. "What did the CIA know about Operation Condor?"
2. "When was DINA dissolved and why?"
3. "What did the CIA know about the Letelier assassination?"

### Test 4: Use Sonnet for Complex Query

```bash
uv run python -m app.rag.cli query \
  "How did the CIA's assessment of Pinochet change over time?" \
  --model claude-3-5-sonnet-20241022
```

This tests the more powerful (but expensive) Sonnet model.

### Test 5: Filters and Parameters

```bash
# Date range filter
uv run python -m app.rag.cli query "Operation Condor activities" \
  --start-date 1976-01-01 \
  --end-date 1976-12-31

# Keyword filter
uv run python -m app.rag.cli query "Pinochet" \
  --keywords "OPERATION CONDOR,HUMAN RIGHTS"

# More documents
uv run python -m app.rag.cli query "CIA assessment of Pinochet" \
  --top-k 10
```

## What to Look For

### ✅ Good Signs

1. **Proper Citations**: Answer includes `[Doc XXXXX]` references
2. **No Hallucination**: Only claims what's in documents
3. **Acknowledges Gaps**: Says "documents do not provide..." when info is missing
4. **Includes Caveats**: Mentions "CIA perspective only", "may contain biases"
5. **Dates and Context**: Includes dates from documents (e.g., "August 1976")

### ❌ Red Flags

1. **No Citations**: Claims without [Doc XXXXX] references
2. **Made-up Info**: Specific claims not found in retrieved documents
3. **Overconfident**: Doesn't acknowledge gaps or limitations
4. **Missing Context**: No dates or classification levels

## Troubleshooting

### Error: "ANTHROPIC_API_KEY not found"

**Solution**: Add to `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

Get your key from: https://console.anthropic.com/settings/keys

### Error: "Vector database is empty"

**Solution**: Build the index first:
```bash
uv run python -m app.rag.cli build
```

### Error: "Could not import anthropic"

**Solution**: Install the package:
```bash
uv add anthropic
```

### API Rate Limit Errors

**Solution**: Claude has rate limits based on your tier. Wait a moment and retry.

## Expected Costs

### Test Suite (~6 queries)
- Claude 3.5 Haiku: ~$0.12-0.18 total
- Claude 3.5 Sonnet: ~$0.36-0.60 total

### Per Query
- Claude 3.5 Haiku: ~$0.02-0.03
- Claude 3.5 Sonnet: ~$0.06-0.10

## Success Criteria

The Claude integration is working correctly if:

1. ✅ Test script completes all tests successfully
2. ✅ Queries return well-cited answers with proper [Doc XXXXX] format
3. ✅ System acknowledges gaps honestly (no hallucination)
4. ✅ Both `--llm claude` and `--llm openai` work
5. ✅ Interactive mode works smoothly
6. ✅ Filters (date, keywords) work as expected

## Next Steps After Testing

If all tests pass:

1. **Compare Quality**: Run the same query with both models and compare
2. **Review Costs**: Monitor actual API costs vs estimates
3. **Production Use**: Start using Claude as default for research queries
4. **Feedback**: Note any issues or improvements needed

See `docs/CLAUDE_MIGRATION_ANALYSIS.md` for detailed cost/quality analysis.
