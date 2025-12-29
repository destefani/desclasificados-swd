"""Tests for the document and entity explorer modules."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from app.explorer import (
    generate_documents_json,
    generate_entities_json,
    generate_entity_explorer_page,
    generate_explorer_page,
)
from app.visualizations.document_explorer import generate_explorer_html
from app.visualizations.entity_explorer import generate_entity_explorer_html


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

    def test_includes_about_link(self) -> None:
        """Test that about link is included in header."""
        html = generate_explorer_html()

        assert 'href="../about.html"' in html
        assert 'class="about-link"' in html


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


class TestGenerateEntitiesJson:
    """Tests for generate_entities_json function."""

    @pytest.fixture
    def sample_results(self) -> dict:
        """Sample results dictionary mimicking process_documents output."""
        return {
            "people_count": {
                "PINOCHET, AUGUSTO": 100,
                "LETELIER, ORLANDO": 50,
                "ALLENDE, SALVADOR": 25,
            },
            "people_docs": {
                "PINOCHET, AUGUSTO": [
                    ("DOC-001", "/path/to/1.pdf", "12345"),
                    ("DOC-002", "/path/to/2.pdf", "12346"),
                ],
                "LETELIER, ORLANDO": [
                    ("DOC-003", "/path/to/3.pdf", "12347"),
                ],
            },
            "org_count": {
                "DINA": 75,
                "CIA": 200,
            },
            "org_docs": {
                "DINA": [("DOC-004", "/path/to/4.pdf", "12348")],
            },
            "keywords_count": {
                "HUMAN RIGHTS": 150,
                "OPERATION CONDOR": 80,
            },
            "keyword_docs": {
                "HUMAN RIGHTS": [("DOC-005", "/path/to/5.pdf", "12349")],
            },
            "country_count": {
                "CHILE": 500,
                "ARGENTINA": 100,
            },
            "city_count": {
                "SANTIAGO": 300,
                "BUENOS AIRES": 50,
            },
            "other_place_count": {
                "VILLA GRIMALDI": 20,
            },
        }

    def test_generates_valid_json_structure(self, sample_results: dict) -> None:
        """Test that the output has the correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_entities_json(sample_results, output_dir=tmpdir)

            assert output_path.exists()
            with open(output_path) as f:
                data = json.load(f)

            assert "generated" in data
            assert "total_count" in data
            assert "schema_version" in data
            assert "entities" in data
            assert "facets" in data

            assert data["schema_version"] == "1.0.0"
            assert data["total_count"] > 0

    def test_creates_entities_for_all_types(self, sample_results: dict) -> None:
        """Test that entities are created for people, orgs, keywords, and places."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_entities_json(sample_results, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            types = {e["type"] for e in data["entities"]}
            assert "person" in types
            assert "organization" in types
            assert "keyword" in types
            assert "place" in types

    def test_entity_structure(self, sample_results: dict) -> None:
        """Test that each entity has required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_entities_json(sample_results, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            for entity in data["entities"]:
                assert "id" in entity
                assert "name" in entity
                assert "type" in entity
                assert "doc_count" in entity
                assert "first_letter" in entity
                assert "sample_docs" in entity

    def test_sorts_by_doc_count_descending(self, sample_results: dict) -> None:
        """Test that entities are sorted by document count descending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_entities_json(sample_results, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            counts = [e["doc_count"] for e in data["entities"]]
            assert counts == sorted(counts, reverse=True)

    def test_extracts_first_letter(self, sample_results: dict) -> None:
        """Test that first letter is correctly extracted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_entities_json(sample_results, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            # Find Pinochet
            pinochet = next(
                (e for e in data["entities"] if "PINOCHET" in e["name"]), None
            )
            assert pinochet is not None
            assert pinochet["first_letter"] == "P"

    def test_includes_sample_docs(self, sample_results: dict) -> None:
        """Test that sample documents are included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_entities_json(sample_results, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            # Find Pinochet who has 2 docs in the test data
            pinochet = next(
                (e for e in data["entities"] if "PINOCHET" in e["name"]), None
            )
            assert pinochet is not None
            assert len(pinochet["sample_docs"]) == 2

    def test_builds_facets(self, sample_results: dict) -> None:
        """Test that facets are correctly built."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_entities_json(sample_results, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            facets = data["facets"]
            assert "types" in facets
            assert "subtypes" in facets
            assert "letters" in facets
            assert "doc_count_range" in facets

            # Check type counts
            assert facets["types"]["person"] == 3  # 3 people in test data
            assert facets["types"]["organization"] == 2
            assert facets["types"]["keyword"] == 2

    def test_place_subtypes(self, sample_results: dict) -> None:
        """Test that place subtypes are correctly assigned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_entities_json(sample_results, output_dir=tmpdir)

            with open(output_path) as f:
                data = json.load(f)

            places = [e for e in data["entities"] if e["type"] == "place"]

            # Should have countries, cities, and other
            subtypes = {p.get("subtype") for p in places}
            assert "country" in subtypes
            assert "city" in subtypes
            assert "other" in subtypes


class TestGenerateEntityExplorerHtml:
    """Tests for generate_entity_explorer_html function."""

    def test_generates_valid_html(self) -> None:
        """Test that valid HTML is generated."""
        html = generate_entity_explorer_html()

        assert html.startswith("<!DOCTYPE html>")
        assert '<html lang="en">' in html
        assert "</html>" in html

    def test_includes_fuse_js(self) -> None:
        """Test that Fuse.js is included for search."""
        html = generate_entity_explorer_html()

        assert "fuse.js" in html.lower() or "fuse.min.js" in html.lower()

    def test_includes_alphabetical_index(self) -> None:
        """Test that alphabetical index is included."""
        html = generate_entity_explorer_html()

        assert 'id="alpha-index"' in html
        assert 'class="alpha-btn' in html

    def test_includes_entity_type_filters(self) -> None:
        """Test that entity type filter elements are included."""
        html = generate_entity_explorer_html()

        assert 'id="type-filters"' in html
        assert 'id="subtype-filters"' in html

    def test_includes_count_range_filters(self) -> None:
        """Test that document count range filters are included."""
        html = generate_entity_explorer_html()

        assert 'id="count-min"' in html
        assert 'id="count-max"' in html
        assert 'class="preset-btn"' in html

    def test_includes_entity_cards_container(self) -> None:
        """Test that entity cards container is included."""
        html = generate_entity_explorer_html()

        assert 'id="entity-cards"' in html

    def test_includes_pagination(self) -> None:
        """Test that pagination container is included."""
        html = generate_entity_explorer_html()

        assert 'id="pagination"' in html

    def test_includes_back_link(self) -> None:
        """Test that back link to dashboard is included."""
        html = generate_entity_explorer_html()

        assert 'href="../"' in html or "Back to Dashboard" in html

    def test_includes_documents_explorer_link(self) -> None:
        """Test that link to document explorer is included."""
        html = generate_entity_explorer_html()

        assert 'href="../explorer/"' in html

    def test_includes_about_link(self) -> None:
        """Test that about link is included."""
        html = generate_entity_explorer_html()

        assert 'href="../about.html"' in html

    def test_includes_external_pdf_viewer_url(self) -> None:
        """Test that the external PDF viewer URL is included."""
        viewer_url = "https://example.com/viewer"
        html = generate_entity_explorer_html(external_pdf_viewer=viewer_url)

        assert viewer_url in html

    def test_includes_type_icons(self) -> None:
        """Test that entity type icons are defined."""
        html = generate_entity_explorer_html()

        assert "TYPE_ICONS" in html
        assert "person" in html
        assert "organization" in html
        assert "keyword" in html
        assert "place" in html


class TestGenerateEntityExplorerPage:
    """Tests for generate_entity_explorer_page function."""

    def test_creates_entity_explorer_file(self) -> None:
        """Test that the entity explorer HTML file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_entity_explorer_page(output_dir=tmpdir)

            assert output_path.exists()
            assert output_path.name == "index.html"

            content = output_path.read_text()
            assert "<!DOCTYPE html>" in content
            assert "Entity Explorer" in content

    def test_uses_custom_pdf_viewer(self) -> None:
        """Test that custom PDF viewer URL is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viewer_url = "https://custom-viewer.com"
            output_path = generate_entity_explorer_page(
                output_dir=tmpdir,
                external_pdf_viewer=viewer_url
            )

            content = output_path.read_text()
            assert viewer_url in content
