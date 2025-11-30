"""Question answering pipeline using RAG."""

from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.rag.config import OPENAI_API_KEY, LLM_MODEL, MAX_CONTEXT_TOKENS
from app.rag.vector_store import VectorStore
from app.rag.retrieval import retrieve_documents


client = OpenAI(api_key=OPENAI_API_KEY)


QA_SYSTEM_PROMPT = """You are a research assistant analyzing declassified CIA documents about the Chilean dictatorship (1973-1990).

Your role is to answer questions based ONLY on the provided documents. You must:

1. Answer based exclusively on the provided context documents
2. Cite specific document IDs for all claims (use format: [Doc XXXXX])
3. If the documents don't contain relevant information, explicitly say so
4. Note any limitations or gaps in the available information
5. Include dates and classification levels when relevant
6. Maintain objectivity - these are CIA documents representing their perspective only
7. Never make claims without documentary support

Remember: These documents represent the CIA's perspective, which may contain intelligence errors, reflect US interests and biases, and is incomplete (many documents remain classified). The complete historical record requires multiple sources."""


def build_context(results: List[Dict[str, Any]], max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
    """Build context string from retrieved documents.

    Args:
        results: List of retrieved document chunks
        max_tokens: Maximum tokens for context

    Returns:
        Formatted context string
    """
    if not results:
        return "No relevant documents found."

    context_parts = []
    estimated_tokens = 0

    for i, result in enumerate(results, 1):
        metadata = result["metadata"]
        text = result["text"]

        # Format document snippet
        doc_snippet = f"""
--- Document {i} ---
Document ID: {metadata['document_id']}
Date: {metadata['document_date']}
Type: {metadata['document_type']}
Classification: {metadata['classification_level']}
Author: {metadata['author']}

Content:
{text}
"""

        # Rough token estimation (4 chars ≈ 1 token)
        snippet_tokens = len(doc_snippet) // 4

        if estimated_tokens + snippet_tokens > max_tokens:
            context_parts.append("\n[Additional documents omitted due to length limits]")
            break

        context_parts.append(doc_snippet)
        estimated_tokens += snippet_tokens

    return "\n".join(context_parts)


def generate_prompt(question: str, context: str) -> str:
    """Generate the complete prompt for the LLM.

    Args:
        question: User's question
        context: Retrieved document context

    Returns:
        Formatted prompt
    """
    return f"""QUESTION: {question}

CONTEXT (Declassified CIA Documents):
{context}

INSTRUCTIONS:
- Answer the question using ONLY the information in the context documents above
- Cite specific document IDs in your answer (e.g., [Doc 24736])
- If the context doesn't contain relevant information, say so clearly
- Include dates and classification levels when relevant
- Note any limitations or uncertainties in the available information

ANSWER:"""


def call_llm(prompt: str, model: str = LLM_MODEL) -> str:
    """Call the LLM to generate an answer.

    Args:
        prompt: Complete prompt with question and context
        model: OpenAI model to use

    Returns:
        Generated answer
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,  # Lower temperature for more factual responses
        max_tokens=1000,
    )

    return response.choices[0].message.content


def format_answer_with_sources(
    answer: str,
    sources: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Format the answer with source citations.

    Args:
        answer: Generated answer
        sources: Retrieved source documents

    Returns:
        Dictionary with answer and formatted sources
    """
    formatted_sources = []

    for source in sources:
        metadata = source["metadata"]
        formatted_source = {
            "document_id": metadata["document_id"],
            "date": metadata["document_date"],
            "type": metadata["document_type"],
            "classification": metadata["classification_level"],
            "author": metadata["author"],
            "excerpt": source["text"][:200] + "..." if len(source["text"]) > 200 else source["text"],
            "relevance_score": source.get("relevance_score", 0.0),
        }
        formatted_sources.append(formatted_source)

    return {
        "answer": answer,
        "sources": formatted_sources,
        "num_sources": len(formatted_sources),
    }


def ask_question(
    vector_store: VectorStore,
    question: str,
    top_k: int = 5,
    date_range: Optional[tuple] = None,
    keywords: Optional[List[str]] = None,
    model: str = LLM_MODEL,
) -> Dict[str, Any]:
    """End-to-end question answering pipeline.

    Args:
        vector_store: VectorStore instance
        question: User's question
        top_k: Number of documents to retrieve
        date_range: Optional (start_date, end_date) filter
        keywords: Optional keyword filters
        model: LLM model to use

    Returns:
        Dictionary with answer and sources
    """
    # Retrieve relevant documents
    print(f"Retrieving relevant documents for: '{question}'")
    results = retrieve_documents(
        vector_store=vector_store,
        query=question,
        top_k=top_k,
        date_range=date_range,
        keywords=keywords,
    )

    print(f"Retrieved {len(results)} relevant documents")

    # Build context
    context = build_context(results)

    # Generate prompt
    prompt = generate_prompt(question, context)

    # Get answer from LLM
    print("Generating answer...")
    answer = call_llm(prompt, model=model)

    # Format response with sources
    response = format_answer_with_sources(answer, results)

    return response
