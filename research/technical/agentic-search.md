# Agentic Search Research

**Research Date:** 2025-11-30
**Researcher:** Claude Code
**Topic:** Agentic Search - Evolution of Retrieval Systems in AI

## Executive Summary

Agentic search represents a paradigm shift from traditional keyword-based and semantic search to autonomous, goal-oriented information retrieval systems. Unlike traditional RAG (Retrieval Augmented Generation) that performs single-hop retrieval based on semantic similarity, agentic search uses AI agents to break down complex queries, iteratively refine searches, and synthesize information from multiple sources.

## Definition and Core Concept

**Agentic Search** is an AI-powered search system that actively understands a user's underlying intent, performs iterative queries, synthesizes information from multiple sources, and refines results to achieve a comprehensive answer or solution.

Key characteristics of agentic systems:
- Takes actions on a human's behalf
- Follows multi-step instructions
- Maintains memory and context
- Uses tool calling capabilities
- Works more like a research helper than a simple search tool

## Evolution: From Traditional Search to Agentic Retrieval

### Traditional Search (Pre-2020s)
- Keyword matching
- Static query processing
- Single-shot retrieval
- User must refine queries manually

### Semantic Search / Basic RAG (2020-2023)
- Embedding-based similarity matching
- Understanding meaning and context
- Single-hop retrieval
- **Limitation:** Retrieves contextually irrelevant (but semantically similar) documents
- **Limitation:** Struggles with nuanced queries requiring precise answers

### Agentic Search / Agentic RAG (2024-2025)
- Multi-query pipeline for complex questions
- Agent breaks down queries into sub-questions
- Iterative refinement of search
- Dynamic decision-making about if, what, where, and how to retrieve
- Works well for asynchronous tasks including research, summarization, and code correction

## Agentic RAG vs Traditional RAG

| Aspect | Traditional RAG | Agentic RAG |
|--------|----------------|-------------|
| **Retrieval Strategy** | Single-hop, semantic similarity only | Multi-hop, agent-planned retrieval |
| **Query Processing** | Fixed, single query | Deconstructed into sub-queries |
| **Adaptation** | Static | Dynamic, self-correcting |
| **Decision Making** | Retrieves blindly | Decides if/what/where/how to retrieve |
| **Context** | Single interaction | Maintains context over time |
| **Use Cases** | Simple Q&A | Complex research, synthesis, analysis |

## How Agentic Search Works

### Core Workflow

1. **Query Analysis**: LLM analyzes the complex query and user intent
2. **Query Decomposition**: Breaks down query into smaller, focused sub-queries
3. **Parallel Execution**: Runs sub-queries in parallel for better coverage
4. **Iterative Refinement**: Agent reflects on intermediate results and adapts strategy
5. **Synthesis**: Combines best results into a unified, coherent response
6. **Citation**: Backs up findings with sources and references

### Additional Capabilities

- **Spelling correction** - Automatically fixes typos in queries
- **Synonym expansion** - Uses synonym maps for broader coverage
- **LLM-generated paraphrasing** - Rewrites queries for better matches
- **Semantic reranking** - Promotes most relevant matches
- **Tool selection** - Chooses appropriate tools/indices for retrieval

## Implementation Platforms

### Microsoft Azure AI Search
- **Feature**: Agentic Retrieval pipeline
- **Use Case**: Chat and copilot apps, RAG patterns, agent-to-agent workflows
- **Key Capability**: Multi-query pipeline for complex questions

### OpenSearch
- **Feature**: Agentic search with QueryPlanningTool
- **Approach**: Preconfigured agent reads question, plans search, executes retrieval
- **Interface**: Natural language queries

### Elasticsearch
- **Feature**: LLM agents for intelligent hybrid search
- **Approach**: Beyond vectors - combines multiple retrieval strategies
- **Focus**: Agentic LLM integration

### LlamaIndex
- **Position**: "RAG is dead, long live agentic retrieval"
- **Product**: LlamaCloud with agentic retrieval services
- **Philosophy**: Autonomous agents plan multiple retrieval steps

## RAG in 2025: Key Trends

According to recent industry analysis, RAG is evolving into:
- **Agentic Retrieval** - Agent-driven, multi-step retrieval
- **RAG 2.0** - Modular, decision-based retrieval
- **Context Engineering** - Intelligent context management
- **Semantic Layers** - Beyond simple embedding similarity

**Key Principle**: "RAG in 2025 is modular and should decide if, what, where, and how to retrieve, not retrieve blindly."

## Relevance to This Project

### Current State
Our project currently uses **traditional RAG** with:
- Single-hop semantic search using ChromaDB
- OpenAI embeddings (`text-embedding-3-small`)
- Claude/GPT for answer generation
- Basic filtering by date, keywords, classification

### Potential Improvements with Agentic Search

1. **Complex Historical Queries**
   - Example: "What did the CIA know about Operation Condor between 1975-1977, and how did this relate to Letelier's assassination?"
   - Agentic approach could break this into:
     - Sub-query 1: Operation Condor documents 1975-1977
     - Sub-query 2: Letelier-related documents
     - Sub-query 3: Documents linking both topics
     - Synthesis: Timeline and relationship analysis

2. **Multi-Document Synthesis**
   - Current: Retrieves top-k most similar chunks
   - Agentic: Could iteratively search different time periods, cross-reference names, follow document trails

3. **Adaptive Retrieval Strategy**
   - Current: Always uses same embedding search
   - Agentic: Could decide when to use:
     - Keyword search (for specific names/dates)
     - Semantic search (for conceptual queries)
     - Hybrid search (combination)
     - Network analysis (relationship queries)

4. **Query Refinement**
   - Current: User must manually refine queries
   - Agentic: System could auto-correct Spanish names, expand acronyms, handle OCR artifacts

## Implementation Considerations

### Pros
- Better handling of complex research questions
- More comprehensive document coverage
- Reduced user burden for query refinement
- Improved accuracy for multi-faceted queries
- Natural fit for historical research workflows

### Cons
- Increased complexity in implementation
- Higher computational cost (multiple LLM calls)
- Longer latency for query responses
- Need for careful prompt engineering
- Requires robust error handling for agent failures

### Cost Analysis
- Traditional RAG: ~$0.02-0.03 per query
- Agentic RAG: Estimated ~$0.05-0.15 per query (multiple LLM calls for query decomposition + retrieval)

## Next Steps for Research

1. **Proof of Concept**
   - Implement simple agentic retrieval using LangChain or LlamaIndex
   - Test with 3-5 complex historical queries
   - Compare results vs current RAG implementation

2. **Platform Evaluation**
   - Test Azure AI Search agentic retrieval
   - Evaluate OpenSearch agentic search
   - Consider LlamaIndex/LangGraph for custom implementation

3. **Benchmark Development**
   - Create test suite of complex queries requiring multi-step retrieval
   - Measure accuracy, latency, cost
   - Compare traditional RAG vs agentic RAG

4. **Hybrid Approach**
   - Investigate routing: simple queries → traditional RAG, complex → agentic
   - Implement query complexity classifier

## References and Sources

### Definitions and Concepts
- [What Is Agentic Search? Breaking Down the Concept and Definition - Nine Peaks Media](https://ninepeaks.io/what-is-agentic-search)
- [What is agentic search, and how will it shift your strategy? - Conductor](https://www.conductor.com/academy/agentic-search/)
- [What Is Agentic Search? Agentic AI Explained - Swirl AI](https://swirlaiconnect.com/what-is-agentic-search/)
- [What is agentic AI? Definition and differentiators - Google Cloud](https://cloud.google.com/discover/what-is-agentic-ai)
- [Agentic AI - Wikipedia](https://en.wikipedia.org/wiki/Agentic_AI)
- [What is Agentic AI? - IBM](https://www.ibm.com/think/topics/agentic-ai)

### RAG Evolution and Comparisons
- [Is RAG Dead? The Rise of Context Engineering and Semantic Layers for Agentic AI - Towards Data Science](https://towardsdatascience.com/beyond-rag/)
- [Traditional RAG vs. Agentic RAG - NVIDIA Technical Blog](https://developer.nvidia.com/blog/traditional-rag-vs-agentic-rag-why-ai-agents-need-dynamic-knowledge-to-get-smarter/)
- [Stop Building Vanilla RAG: Embrace Agentic RAG with DeepSearcher - Milvus Blog](https://milvus.io/blog/stop-use-outdated-rag-deepsearcher-agentic-rag-approaches-changes-everything.md)
- [RAG vs. Semantic Search: A Deep Dive for Generative AI - Medium](https://tsaiprabhanj.medium.com/rag-vs-semantic-search-a-deep-dive-for-generative-ai-0ada1e2d7cd0)
- [RAG vs Agentic RAG: A Comprehensive Guide - Analytics Vidhya](https://www.analyticsvidhya.com/blog/2024/11/rag-vs-agentic-rag/)
- [RAG in 2025: The enterprise guide - Data Nucleus](https://datanucleus.dev/rag-and-agentic-ai/what-is-rag-enterprise-guide-2025)
- [RAG is Dead, Long Live RAG: Retrieval in the Age of Agents - LightOn](https://www.lighton.ai/lighton-blogs/rag-is-dead-long-live-rag-retrieval-in-the-age-of-agents)

### Implementation Guides
- [Agentic Retrieval - Azure AI Search - Microsoft Learn](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-overview)
- [Quickstart: Agentic Retrieval - Azure AI Search - Microsoft Learn](https://learn.microsoft.com/en-us/azure/search/search-get-started-agentic-retrieval)
- [Tutorial: Build an agentic retrieval solution - Azure AI Search](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-create-pipeline)
- [Agentic Search in Action: A Practical Guide to Building from Scratch - Google Cloud Medium](https://medium.com/google-cloud/agentic-search-in-action-a-practical-guide-to-building-from-scratch-e100422f27b2)
- [RAG is dead, long live agentic retrieval - LlamaIndex](https://www.llamaindex.ai/blog/rag-is-dead-long-live-agentic-retrieval)
- [Agentic search - OpenSearch Documentation](https://docs.opensearch.org/latest/vector-search/ai-search/agentic-search/index)
- [Agentic LLM: hybrid search with agents in Elasticsearch](https://www.elastic.co/search-labs/blog/llm-agents-intelligent-hybrid-search)
- [Beyond vectors: Intelligent hybrid search with LLM agents - Elasticsearch Labs](https://www.elastic.co/search-labs/blog/agentic-llm-intelligent-hybrid-search)
- [How Agentic Hybrid Search Creates Smarter RAG Apps - DataStax Medium](https://medium.com/building-the-open-data-stack/how-agentic-hybrid-search-creates-smarter-rag-apps-b860417448d7)
- [How to Perform Agentic Information Retrieval - Towards Data Science](https://towardsdatascience.com/how-to-perform-agentic-information-retrieval/)
- [What is Agentic RAG? - IBM](https://www.ibm.com/think/topics/agentic-rag)

### Related Resources
- [The Future of Search: How Agentic AI Powered Search Engines Work - Antematter](https://antematter.io/blogs/how-agentic-powered-search-engines-work)
- [How Agentic AI Will Reshape Search - Razorfish](https://www.razorfish.com/articles/perspectives/how-agentic-ai-will-reshape-search/)
- [Retrieval - LangChain Docs](https://docs.langchain.com/oss/python/langchain/retrieval)

---

**Next Research Steps:**
1. Deep dive into LlamaIndex agentic retrieval implementation
2. Test Azure AI Search agentic retrieval with sample queries
3. Prototype comparison: traditional vs agentic RAG on complex historical queries
4. Cost-benefit analysis for production deployment
