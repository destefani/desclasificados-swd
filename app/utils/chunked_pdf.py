"""
Chunked PDF processing for large documents.

Large PDFs (>30 pages) often exceed the model's output token limit when
transcribed in a single API call. This module provides utilities to:
1. Split PDFs into smaller chunks
2. Process each chunk separately
3. Merge the results into a single transcript

Usage:
    from app.utils.chunked_pdf import process_large_pdf, needs_chunking

    if needs_chunking(pdf_path):
        result = process_large_pdf(pdf_path, output_dir, model)
"""

from __future__ import annotations

import base64
import io
import json
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import fitz  # PyMuPDF

# Default threshold: PDFs with more than this many pages will be chunked
DEFAULT_CHUNK_THRESHOLD = 30
DEFAULT_CHUNK_SIZE = 20  # pages per chunk


@dataclass
class ChunkResult:
    """Result from processing a single chunk."""

    chunk_index: int
    start_page: int
    end_page: int
    success: bool
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None


def get_pdf_page_count(pdf_path: Path) -> int:
    """Get the number of pages in a PDF file."""
    doc = fitz.open(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()


def needs_chunking(pdf_path: Path, threshold: int = DEFAULT_CHUNK_THRESHOLD) -> bool:
    """Check if a PDF needs to be processed in chunks."""
    return get_pdf_page_count(pdf_path) > threshold


def split_pdf(
    pdf_path: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[tuple[int, int, bytes]]:
    """
    Split a PDF into chunks.

    Args:
        pdf_path: Path to the PDF file
        chunk_size: Number of pages per chunk

    Returns:
        List of tuples: (start_page, end_page, pdf_bytes)
        Page numbers are 1-indexed for readability.
    """
    doc = fitz.open(pdf_path)
    chunks = []

    try:
        total_pages = len(doc)

        for start in range(0, total_pages, chunk_size):
            end = min(start + chunk_size, total_pages)

            # Create a new PDF with just these pages
            chunk_doc = fitz.open()
            chunk_doc.insert_pdf(doc, from_page=start, to_page=end - 1)

            # Get PDF bytes
            pdf_bytes = chunk_doc.tobytes()
            chunk_doc.close()

            # Store with 1-indexed page numbers
            chunks.append((start + 1, end, pdf_bytes))

    finally:
        doc.close()

    return chunks


def merge_chunk_results(
    chunks: list[ChunkResult],
    original_filename: str,
    total_pages: int,
) -> dict[str, Any]:
    """
    Merge results from multiple chunks into a single transcript.

    Strategy:
    - original_text: Concatenate with page markers
    - reviewed_text: Concatenate with page markers
    - metadata: Take from first chunk, merge arrays (people, places, keywords)
    - confidence: Average across chunks, combine concerns
    """
    # Filter successful chunks
    successful = [c for c in chunks if c.success and c.data]

    if not successful:
        return {
            "metadata": {"document_title": f"Failed to process: {original_filename}"},
            "original_text": "",
            "reviewed_text": "",
            "confidence": {"overall": 0.0, "concerns": ["All chunks failed to process"]},
        }

    # Initialize merged result from first chunk
    first_data = successful[0].data
    merged: dict[str, Any] = {
        "metadata": dict(first_data.get("metadata", {})),
        "original_text": "",
        "reviewed_text": "",
        "confidence": {"overall": 0.0, "concerns": []},
    }

    # Merge text fields with page markers
    original_texts = []
    reviewed_texts = []

    for chunk in successful:
        data = chunk.data
        marker = f"\n\n--- Pages {chunk.start_page}-{chunk.end_page} ---\n\n"

        if data.get("original_text"):
            original_texts.append(marker + data["original_text"])
        if data.get("reviewed_text"):
            reviewed_texts.append(marker + data["reviewed_text"])

    merged["original_text"] = "".join(original_texts).strip()
    merged["reviewed_text"] = "".join(reviewed_texts).strip()

    # Merge metadata arrays
    array_fields = [
        "people_mentioned", "recipients", "country", "city",
        "other_place", "keywords", "observations"
    ]

    for field in array_fields:
        all_values = []
        for chunk in successful:
            chunk_meta = chunk.data.get("metadata", {})
            values = chunk_meta.get(field, [])
            if isinstance(values, list):
                all_values.extend(values)
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for v in all_values:
            if v not in seen:
                seen.add(v)
                unique.append(v)
        merged["metadata"][field] = unique

    # Update page count
    merged["metadata"]["page_count"] = total_pages

    # Merge confidence scores
    confidences = []
    all_concerns = []

    for chunk in successful:
        conf = chunk.data.get("confidence", {})
        if isinstance(conf.get("overall"), (int, float)):
            confidences.append(conf["overall"])
        concerns = conf.get("concerns", [])
        if isinstance(concerns, list):
            all_concerns.extend(concerns)

    if confidences:
        merged["confidence"]["overall"] = round(sum(confidences) / len(confidences), 2)

    # Deduplicate concerns
    seen_concerns = set()
    unique_concerns = []
    for c in all_concerns:
        if c not in seen_concerns:
            seen_concerns.add(c)
            unique_concerns.append(c)

    merged["confidence"]["concerns"] = unique_concerns[:10]  # Limit to 10

    # Add note about chunked processing
    if "observations" not in merged["metadata"]:
        merged["metadata"]["observations"] = []
    merged["metadata"]["observations"].append(
        f"Document processed in {len(successful)} chunks due to size ({total_pages} pages)"
    )

    # Merge sensitive content tracking
    for ref_type in ["financial_references", "violence_references", "torture_references"]:
        merged_refs = _merge_references(successful, ref_type)
        if merged_refs:
            merged["metadata"][ref_type] = merged_refs

    return merged


def _merge_references(chunks: list[ChunkResult], ref_type: str) -> Optional[dict[str, Any]]:
    """Merge reference fields (financial, violence, torture) from chunks."""
    all_refs = []
    for chunk in chunks:
        if chunk.data:
            refs = chunk.data.get("metadata", {}).get(ref_type)
            if refs:
                all_refs.append(refs)

    if not all_refs:
        return None

    # Merge based on reference type
    if ref_type == "financial_references":
        merged = {
            "amounts": [],
            "financial_actors": [],
            "purposes": [],
        }
        for refs in all_refs:
            merged["amounts"].extend(refs.get("amounts", []))
            merged["financial_actors"].extend(refs.get("financial_actors", []))
            merged["purposes"].extend(refs.get("purposes", []))
        # Deduplicate
        merged["financial_actors"] = list(set(merged["financial_actors"]))
        merged["purposes"] = list(set(merged["purposes"]))
        return merged

    elif ref_type == "violence_references":
        merged = {
            "incident_types": [],
            "victims": [],
            "perpetrators": [],
            "has_violence_content": False,
        }
        for refs in all_refs:
            merged["incident_types"].extend(refs.get("incident_types", []))
            merged["victims"].extend(refs.get("victims", []))
            merged["perpetrators"].extend(refs.get("perpetrators", []))
            if refs.get("has_violence_content"):
                merged["has_violence_content"] = True
        # Deduplicate
        merged["incident_types"] = list(set(merged["incident_types"]))
        merged["victims"] = list(set(merged["victims"]))
        merged["perpetrators"] = list(set(merged["perpetrators"]))
        return merged

    elif ref_type == "torture_references":
        merged = {
            "detention_centers": [],
            "victims": [],
            "perpetrators": [],
            "methods_mentioned": [],
            "has_torture_content": False,
        }
        for refs in all_refs:
            merged["detention_centers"].extend(refs.get("detention_centers", []))
            merged["victims"].extend(refs.get("victims", []))
            merged["perpetrators"].extend(refs.get("perpetrators", []))
            merged["methods_mentioned"].extend(refs.get("methods_mentioned", []))
            if refs.get("has_torture_content"):
                merged["has_torture_content"] = True
        # Deduplicate
        merged["detention_centers"] = list(set(merged["detention_centers"]))
        merged["victims"] = list(set(merged["victims"]))
        merged["perpetrators"] = list(set(merged["perpetrators"]))
        merged["methods_mentioned"] = list(set(merged["methods_mentioned"]))
        return merged

    return None
