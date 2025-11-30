"""Document retrieval and search functionality."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI
from app.rag.config import OPENAI_API_KEY, EMBEDDING_MODEL, DEFAULT_TOP_K
from app.rag.vector_store import VectorStore


client = OpenAI(api_key=OPENAI_API_KEY)


def generate_query_embedding(query: str, model: str = EMBEDDING_MODEL) -> List[float]:
    """Generate embedding for a query string.

    Args:
        query: Query text
        model: OpenAI embedding model to use

    Returns:
        Embedding vector
    """
    response = client.embeddings.create(input=[query], model=model)
    return response.data[0].embedding


def semantic_search(
    vector_store: VectorStore,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Perform semantic search on the vector database.

    Args:
        vector_store: VectorStore instance
        query: Query text
        top_k: Number of results to return
        filters: Optional metadata filters

    Returns:
        List of search results with metadata
    """
    # Generate query embedding
    query_embedding = generate_query_embedding(query)

    # Query vector database
    results = vector_store.query(
        query_embedding=query_embedding,
        top_k=top_k,
        where=filters,
    )

    # Format results
    formatted_results = []
    for i in range(len(results["ids"])):
        result = {
            "chunk_id": results["ids"][i],
            "text": results["documents"][i],
            "metadata": results["metadatas"][i],
            "distance": results["distances"][i],
            "relevance_score": 1.0 - results["distances"][i],  # Convert distance to similarity
        }
        formatted_results.append(result)

    return formatted_results


def filter_by_date_range(
    results: List[Dict[str, Any]],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filter results by date range.

    Args:
        results: List of search results
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Filtered results
    """
    if not start_date and not end_date:
        return results

    filtered = []
    for result in results:
        doc_date = result["metadata"].get("document_date", "[unknown]")

        if doc_date == "[unknown]":
            continue

        try:
            doc_date_obj = datetime.fromisoformat(doc_date)

            if start_date:
                start_obj = datetime.fromisoformat(start_date)
                if doc_date_obj < start_obj:
                    continue

            if end_date:
                end_obj = datetime.fromisoformat(end_date)
                if doc_date_obj > end_obj:
                    continue

            filtered.append(result)

        except ValueError:
            # Skip documents with invalid dates
            continue

    return filtered


def filter_by_keywords(
    results: List[Dict[str, Any]],
    keywords: List[str],
) -> List[Dict[str, Any]]:
    """Filter results by keywords.

    Args:
        results: List of search results
        keywords: List of keywords to filter by

    Returns:
        Filtered results containing at least one keyword
    """
    if not keywords:
        return results

    filtered = []
    keywords_upper = [k.upper() for k in keywords]

    for result in results:
        doc_keywords = result["metadata"].get("keywords", "").split(",")
        doc_keywords = [k.strip().upper() for k in doc_keywords if k.strip()]

        # Check if any keyword matches
        if any(kw in doc_keywords for kw in keywords_upper):
            filtered.append(result)

    return filtered


def deduplicate_documents(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only the best chunk from each document.

    Args:
        results: List of search results

    Returns:
        Deduplicated results (one chunk per document)
    """
    seen_docs = set()
    deduplicated = []

    for result in results:
        doc_id = result["metadata"]["document_id"]

        if doc_id not in seen_docs:
            deduplicated.append(result)
            seen_docs.add(doc_id)

    return deduplicated


def retrieve_documents(
    vector_store: VectorStore,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    date_range: Optional[tuple] = None,
    keywords: Optional[List[str]] = None,
    deduplicate: bool = True,
) -> List[Dict[str, Any]]:
    """High-level document retrieval with filtering.

    Args:
        vector_store: VectorStore instance
        query: Query text
        top_k: Number of results to return
        date_range: Optional (start_date, end_date) tuple
        keywords: Optional list of keywords to filter by
        deduplicate: Whether to keep only one chunk per document

    Returns:
        List of retrieved documents with metadata
    """
    # Perform semantic search
    results = semantic_search(vector_store, query, top_k=top_k * 2)

    # Apply filters
    if date_range:
        start_date, end_date = date_range
        results = filter_by_date_range(results, start_date, end_date)

    if keywords:
        results = filter_by_keywords(results, keywords)

    # Deduplicate if requested
    if deduplicate:
        results = deduplicate_documents(results)

    # Return top K results
    return results[:top_k]
