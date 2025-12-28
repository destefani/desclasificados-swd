"""Tests for the document explorer module."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from app.explorer import generate_documents_json, generate_explorer_page
from app.visualizations.document_explorer import generate_explorer_html


class TestGenerateDocumentsJson:
    """Tests for generate_documents_json function."""

    def test_generates_valid_json_structure(self) -> None:
        """Test that the output has the correct structure."""
        documents = [
            {
                "basename": "12345",
                "doc_id": "DOC-001",
                "date": "1975-03-15",
                "classification": "SECRET",
                "doc_type": "MEMORANDUM",
                "title": "Test Document Title",
                "summary": "This is a test summary.",
                "page_count": 5,
                "keywords": ["KEYWORD1", "KEYWORD2"],
                "people": ["PERSON, ONE", "PERSON, TWO"],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_documents_json(documents, output_dir=tmpdir)

            assert output_path.exists()
            with open(output_path) as f:
                data = json.load(f)

            assert "generated" in data
            assert "total_count" in data
            assert "schema_version" in data
            assert "documents" in data
            assert "facets" in data

            assert data["total_count"] == 1
            assert data["schema_version"] == "1.0.0"

    def test_truncates_long_titles(self) -> None:
        """Test that long titles are truncated to 100 characters."""
        long_title = "A" * 150  # 150 character title
        documents = [
            {
                "basename": "12345",
                "doc_id": "DOC-001",
                "date": "1975-03-15",
                "classification": "SECRET",
                "doc_type": "MEMO",
                "title": long_title,
                "summary": "",
                "page_count": 1,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_documents_json(documents, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            # Title should be truncated to 97 chars + "..."
            assert len(data["documents"][0]["title"]) == 100
            assert data["documents"][0]["title"].endswith("...")

    def test_truncates_long_summaries(self) -> None:
        """Test that long summaries are truncated to 200 characters."""
        long_summary = "B" * 300  # 300 character summary
        documents = [
            {
                "basename": "12345",
                "doc_id": "DOC-001",
                "date": "1975-03-15",
                "classification": "SECRET",
                "doc_type": "MEMO",
                "title": "Test",
                "summary": long_summary,
                "page_count": 1,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_documents_json(documents, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            # Summary should be truncated to 197 chars + "..."
            assert len(data["documents"][0]["summary"]) == 200
            assert data["documents"][0]["summary"].endswith("...")

    def test_extracts_year_from_date(self) -> None:
        """Test that year is correctly extracted from date."""
        documents = [
            {
                "basename": "12345",
                "doc_id": "DOC-001",
                "date": "1976-08-25",
                "classification": "SECRET",
                "doc_type": "MEMO",
                "title": "Test",
                "summary": "",
                "page_count": 1,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_documents_json(documents, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            assert data["documents"][0]["year"] == 1976

    def test_handles_unknown_date(self) -> None:
        """Test that documents with 0000 dates have null year."""
        documents = [
            {
                "basename": "12345",
                "doc_id": "DOC-001",
                "date": "0000-00-00",
                "classification": "SECRET",
                "doc_type": "MEMO",
                "title": "Test",
                "summary": "",
                "page_count": 1,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_documents_json(documents, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            assert data["documents"][0]["year"] is None

    def test_builds_facets(self) -> None:
        """Test that facets are correctly built from documents."""
        documents = [
            {
                "basename": "1",
                "doc_id": "DOC-001",
                "date": "1975-01-01",
                "classification": "SECRET",
                "doc_type": "MEMO",
                "title": "Test 1",
                "summary": "",
                "page_count": 1,
            },
            {
                "basename": "2",
                "doc_id": "DOC-002",
                "date": "1980-06-15",
                "classification": "CONFIDENTIAL",
                "doc_type": "TELEGRAM",
                "title": "Test 2",
                "summary": "",
                "page_count": 2,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_documents_json(documents, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            facets = data["facets"]
            assert "SECRET" in facets["classifications"]
            assert "CONFIDENTIAL" in facets["classifications"]
            assert "MEMO" in facets["types"]
            assert "TELEGRAM" in facets["types"]
            assert facets["year_range"]["min"] == 1975
            assert facets["year_range"]["max"] == 1980

    def test_limits_keywords_and_people(self) -> None:
        """Test that keywords and people are limited to 5 items."""
        documents = [
            {
                "basename": "12345",
                "doc_id": "DOC-001",
                "date": "1975-03-15",
                "classification": "SECRET",
                "doc_type": "MEMO",
                "title": "Test",
                "summary": "",
                "page_count": 1,
                "keywords": ["K1", "K2", "K3", "K4", "K5", "K6", "K7"],
                "people": ["P1", "P2", "P3", "P4", "P5", "P6", "P7"],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_documents_json(documents, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            assert len(data["documents"][0]["keywords"]) == 5
            assert len(data["documents"][0]["people"]) == 5

    def test_sorts_by_date_descending(self) -> None:
        """Test that documents are sorted by date descending."""
        documents = [
            {"basename": "1", "doc_id": "DOC-001", "date": "1970-01-01", "classification": "SECRET", "doc_type": "MEMO", "title": "Oldest", "summary": "", "page_count": 1},
            {"basename": "2", "doc_id": "DOC-002", "date": "1990-12-31", "classification": "SECRET", "doc_type": "MEMO", "title": "Newest", "summary": "", "page_count": 1},
            {"basename": "3", "doc_id": "DOC-003", "date": "1980-06-15", "classification": "SECRET", "doc_type": "MEMO", "title": "Middle", "summary": "", "page_count": 1},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_documents_json(documents, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            # Should be sorted newest first
            assert data["documents"][0]["title"] == "Newest"
            assert data["documents"][1]["title"] == "Middle"
            assert data["documents"][2]["title"] == "Oldest"


class TestGenerateExplorerHtml:
    """Tests for generate_explorer_html function."""

    def test_generates_valid_html(self) -> None:
        """Test that valid HTML is generated."""
        html = generate_explorer_html()

        assert html.startswith("<!DOCTYPE html>")
        assert "<html lang=\"en\">" in html
        assert "</html>" in html

    def test_includes_fuse_js(self) -> None:
        """Test that Fuse.js is included for search."""
        html = generate_explorer_html()

        assert "fuse.js" in html.lower() or "fuse.min.js" in html.lower()

    def test_includes_external_pdf_viewer_url(self) -> None:
        """Test that the external PDF viewer URL is included."""
        viewer_url = "https://example.com/viewer"
        html = generate_explorer_html(external_pdf_viewer=viewer_url)

        assert viewer_url in html

    def test_includes_filter_elements(self) -> None:
        """Test that filter UI elements are included."""
        html = generate_explorer_html()

        assert 'id="search-input"' in html
        assert 'id="year-start"' in html
        assert 'id="year-end"' in html
        assert 'id="classification-filters"' in html
        assert 'id="type-filters"' in html
        assert 'id="sort-select"' in html

    def test_includes_pagination(self) -> None:
        """Test that pagination container is included."""
        html = generate_explorer_html()

        assert 'id="pagination"' in html

    def test_includes_document_cards_container(self) -> None:
        """Test that document cards container is included."""
        html = generate_explorer_html()

        assert 'id="document-cards"' in html

    def test_includes_back_link(self) -> None:
        """Test that back link to dashboard is included."""
        html = generate_explorer_html()

        assert 'href="../"' in html or "Back to Dashboard" in html


class TestGenerateExplorerPage:
    """Tests for generate_explorer_page function."""

    def test_creates_explorer_file(self) -> None:
        """Test that the explorer HTML file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_explorer_page(output_dir=tmpdir)

            assert output_path.exists()
            assert output_path.name == "index.html"

            content = output_path.read_text()
            assert "<!DOCTYPE html>" in content

    def test_uses_custom_pdf_viewer(self) -> None:
        """Test that custom PDF viewer URL is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viewer_url = "https://custom-viewer.com"
            output_path = generate_explorer_page(
                output_dir=tmpdir,
                external_pdf_viewer=viewer_url
            )

            content = output_path.read_text()
            assert viewer_url in content
