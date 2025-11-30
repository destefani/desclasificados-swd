"""Data loading, chunking, and embedding generation."""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import tiktoken
from openai import OpenAI
from app.rag.config import (
    TRANSCRIPTS_V1_DIR,
    TRANSCRIPTS_DIR,
    TRANSCRIPT_TEXT_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_RPS,
    OPENAI_API_KEY,
)

client = OpenAI(api_key=OPENAI_API_KEY)


def load_json_transcripts(directory: Path) -> List[Dict[str, Any]]:
    """Load all JSON transcript files from a directory.

    Args:
        directory: Path to directory containing JSON files

    Returns:
        List of transcript dictionaries with metadata
    """
    transcripts = []
    json_files = list(directory.glob("*.json"))

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract document ID from filename
            doc_id = json_file.stem
            data["document_id"] = doc_id
            data["source_file"] = str(json_file)

            transcripts.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {json_file}: {e}")
            continue

    return transcripts


def extract_text_and_metadata(transcript: Dict[str, Any]) -> Dict[str, Any]:
    """Extract text content and metadata from a transcript.

    Args:
        transcript: Dictionary containing transcript data

    Returns:
        Dictionary with extracted text and metadata
    """
    # Prefer reviewed_text over original_text
    text = transcript.get("reviewed_text") or transcript.get("original_text", "")

    metadata = transcript.get("metadata", {})

    return {
        "document_id": transcript.get("document_id"),
        "text": text,
        "document_date": metadata.get("document_date", "[unknown]"),
        "classification_level": metadata.get("classification_level", "[unknown]"),
        "document_type": metadata.get("document_type", "[unknown]"),
        "author": metadata.get("author", "[unknown]"),
        "keywords": metadata.get("keywords", []),
        "countries": metadata.get("country", []),
        "people_mentioned": metadata.get("people_mentioned", []),
    }


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for
        encoding_name: Name of the encoding to use

    Returns:
        Number of tokens
    """
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """Split text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in tokens
        overlap: Number of overlapping tokens between chunks

    Returns:
        List of text chunks
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)

    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)

        # Move start forward by chunk_size - overlap
        start += chunk_size - overlap

        # Break if we've covered the entire text
        if end == len(tokens):
            break

    return chunks


def create_document_chunks(transcripts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create chunks from transcripts with metadata.

    Args:
        transcripts: List of transcript dictionaries

    Returns:
        List of chunk dictionaries with metadata
    """
    all_chunks = []

    for transcript in transcripts:
        doc_data = extract_text_and_metadata(transcript)

        if not doc_data["text"]:
            print(f"Warning: No text found for document {doc_data['document_id']}")
            continue

        text_chunks = chunk_text(doc_data["text"])

        for i, text_chunk in enumerate(text_chunks):
            chunk = {
                "chunk_id": f"{doc_data['document_id']}_chunk_{i:03d}",
                "document_id": doc_data["document_id"],
                "chunk_index": i,
                "total_chunks": len(text_chunks),
                "text": text_chunk,
                "document_date": doc_data["document_date"],
                "classification_level": doc_data["classification_level"],
                "document_type": doc_data["document_type"],
                "author": doc_data["author"],
                "keywords": doc_data["keywords"],
                "countries": doc_data["countries"],
                "people_mentioned": doc_data["people_mentioned"],
            }
            all_chunks.append(chunk)

    return all_chunks


def generate_embeddings(
    chunks: List[Dict[str, Any]],
    model: str = EMBEDDING_MODEL,
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> List[Dict[str, Any]]:
    """Generate embeddings for chunks with rate limiting.

    Args:
        chunks: List of chunk dictionaries
        model: OpenAI embedding model to use
        batch_size: Number of chunks to process per batch

    Returns:
        List of chunks with embeddings added
    """
    chunks_with_embeddings = []
    total_batches = (len(chunks) + batch_size - 1) // batch_size

    print(f"Generating embeddings for {len(chunks)} chunks in {total_batches} batches...")

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_num = i // batch_size + 1

        print(f"Processing batch {batch_num}/{total_batches}...")

        # Extract text for embedding
        texts = [chunk["text"] for chunk in batch]

        try:
            # Generate embeddings
            response = client.embeddings.create(input=texts, model=model)

            # Add embeddings to chunks
            for j, chunk in enumerate(batch):
                chunk_with_embedding = chunk.copy()
                chunk_with_embedding["embedding"] = response.data[j].embedding
                chunks_with_embeddings.append(chunk_with_embedding)

            # Rate limiting
            time.sleep(1.0 / EMBEDDING_RPS)

        except Exception as e:
            print(f"Error processing batch {batch_num}: {e}")
            # Add chunks without embeddings
            chunks_with_embeddings.extend(batch)
            continue

    print(f"Successfully generated {len(chunks_with_embeddings)} embeddings")
    return chunks_with_embeddings


def load_all_data() -> List[Dict[str, Any]]:
    """Load all available transcript data.

    Priority:
    1. generated_transcripts/ (current schema)
    2. generated_transcripts_v1/ (legacy schema)
    3. transcript_text/ (plain text fallback)

    Returns:
        List of all loaded transcripts
    """
    all_transcripts = []

    # Load current transcripts
    if TRANSCRIPTS_DIR.exists():
        print(f"Loading transcripts from {TRANSCRIPTS_DIR}...")
        current = load_json_transcripts(TRANSCRIPTS_DIR)
        all_transcripts.extend(current)
        print(f"Loaded {len(current)} current transcripts")

    # Load v1 transcripts
    if TRANSCRIPTS_V1_DIR.exists():
        print(f"Loading transcripts from {TRANSCRIPTS_V1_DIR}...")
        v1 = load_json_transcripts(TRANSCRIPTS_V1_DIR)
        all_transcripts.extend(v1)
        print(f"Loaded {len(v1)} v1 transcripts")

    # TODO: Add support for plain text files from transcript_text/

    print(f"Total transcripts loaded: {len(all_transcripts)}")
    return all_transcripts
