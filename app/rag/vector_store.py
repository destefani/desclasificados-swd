"""Vector database operations using ChromaDB."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from app.rag.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    get_rag_dir,
)


class VectorStore:
    """ChromaDB vector store for document chunks."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        version: Optional[str] = None,
    ):
        """Initialize ChromaDB client.

        Args:
            persist_directory: Explicit directory path (overrides version).
            version: RAG version string. If None, uses latest or legacy.
        """
        if persist_directory:
            self.persist_directory = persist_directory
        elif version:
            self.persist_directory = str(get_rag_dir(version))
        else:
            self.persist_directory = str(get_rag_dir())

        self.version = version

        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="cia_documents",
            metadata={
                "description": "Declassified CIA documents on Chilean dictatorship"
            },
        )

    def add_documents(self, chunks: List[Dict[str, Any]]) -> None:
        """Add document chunks to the vector database.

        Args:
            chunks: List of chunk dictionaries with embeddings
        """
        if not chunks:
            print("No chunks to add")
            return

        # Extract required fields
        ids = [chunk["chunk_id"] for chunk in chunks]
        embeddings = [chunk["embedding"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]

        # Prepare metadata (ChromaDB requires all values to be strings, ints, floats, or bools)
        metadatas = []
        for chunk in chunks:
            metadata = {
                "document_id": chunk["document_id"],
                "chunk_index": chunk["chunk_index"],
                "total_chunks": chunk["total_chunks"],
                "document_date": str(chunk["document_date"]),
                "classification_level": str(chunk["classification_level"]),
                "document_type": str(chunk["document_type"]),
                "author": str(chunk["author"]),
                # Convert lists to comma-separated strings
                "keywords": ",".join(chunk.get("keywords", [])),
                "countries": ",".join(chunk.get("countries", [])),
                "people_mentioned": ",".join(chunk.get("people_mentioned", [])),
            }
            metadatas.append(metadata)

        # Add to collection in batches
        batch_size = 1000
        total = len(ids)

        for i in range(0, total, batch_size):
            batch_end = min(i + batch_size, total)
            print(f"Adding chunks {i} to {batch_end} of {total}...")

            self.collection.add(
                ids=ids[i:batch_end],
                embeddings=embeddings[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
            )

        print(f"Successfully added {total} chunks to vector database")

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query the vector database.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            where: Optional metadata filters

        Returns:
            Query results with documents, metadatas, and distances
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
        )

        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
        }

    def count(self) -> int:
        """Get the number of chunks in the database.

        Returns:
            Number of chunks
        """
        return self.collection.count()

    def reset(self) -> None:
        """Reset the vector database (delete all data)."""
        self.client.delete_collection(name="cia_documents")
        self.collection = self.client.get_or_create_collection(
            name="cia_documents",
            metadata={
                "description": "Declassified CIA documents on Chilean dictatorship"
            },
        )
        print("Vector database reset successfully")

    def get_by_document_id(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document.

        Args:
            document_id: Document ID to retrieve

        Returns:
            List of chunks for the document
        """
        results = self.collection.get(
            where={"document_id": document_id},
        )

        chunks = []
        for i in range(len(results["ids"])):
            chunk = {
                "chunk_id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i],
            }
            chunks.append(chunk)

        return chunks

    def get_manifest_path(self) -> Path:
        """Get path to manifest.json."""
        return Path(self.persist_directory) / "manifest.json"

    def load_manifest(self) -> Optional[Dict[str, Any]]:
        """Load manifest.json if it exists.

        Returns:
            Manifest dictionary or None if not found
        """
        manifest_path = self.get_manifest_path()
        if manifest_path.exists():
            with open(manifest_path) as f:
                return json.load(f)
        return None

    def save_manifest(self, manifest: Dict[str, Any]) -> None:
        """Save manifest.json.

        Args:
            manifest: Manifest dictionary to save
        """
        manifest_path = self.get_manifest_path()
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"Manifest saved to {manifest_path}")


def init_vector_store(
    persist_directory: Optional[str] = None,
    version: Optional[str] = None,
) -> VectorStore:
    """Initialize and return a VectorStore instance.

    Args:
        persist_directory: Optional custom persist directory
        version: RAG version string. If None, uses latest or legacy.

    Returns:
        VectorStore instance
    """
    return VectorStore(persist_directory=persist_directory, version=version)


def build_index(
    chunks: List[Dict[str, Any]],
    reset: bool = False,
    version: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
) -> VectorStore:
    """Build the vector index from chunks.

    Args:
        chunks: List of chunk dictionaries with embeddings
        reset: Whether to reset the database before adding
        version: RAG version to create (e.g., "1.0.0")
        sources: Source transcript metadata for manifest

    Returns:
        VectorStore instance with indexed chunks
    """
    store = init_vector_store(version=version)

    if reset:
        print("Resetting vector database...")
        store.reset()

    print(f"Current database size: {store.count()} chunks")
    store.add_documents(chunks)
    print(f"New database size: {store.count()} chunks")

    # Save manifest if version and sources provided
    if version and sources:
        manifest = {
            "rag_version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "embedding_model": EMBEDDING_MODEL,
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "sources": sources,
            "total_documents": sum(s.get("documents_count", 0) for s in sources),
            "total_chunks": store.count(),
        }
        store.save_manifest(manifest)

    return store
