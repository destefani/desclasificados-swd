"""Unit tests for app.analyze_documents module."""
import json
import os
import tempfile
from collections import Counter

import pytest

from app.analyze_documents import process_documents, generate_html_report


@pytest.fixture
def sample_transcript():
    """Create a sample transcript matching the v2.2.0 schema."""
    return {
        "metadata": {
            "document_id": "TEST-001",
            "case_number": "C5199900030",
            "document_date": "1976-09-21",
            "date_range": {
                "start_date": "",
                "end_date": "",
                "is_approximate": False
            },
            "classification_level": "SECRET",
            "declassification_date": "1999-06-30",
            "document_type": "CABLE",
            "author": "SMITH, JOHN",
            "recipients": ["EMBASSY SANTIAGO", "CIA HEADQUARTERS"],
            "people_mentioned": ["PINOCHET, AUGUSTO", "CONTRERAS, MANUEL"],
            "organizations_mentioned": [
                {"name": "DINA", "type": "INTELLIGENCE_AGENCY", "country": "CHILE"},
                {"name": "CIA", "type": "INTELLIGENCE_AGENCY", "country": "UNITED STATES"}
            ],
            "country": ["CHILE", "UNITED STATES"],
            "city": ["SANTIAGO", "WASHINGTON"],
            "other_place": ["LA MONEDA"],
            "document_title": "Intelligence Report on Chile",
            "document_description": "Cable reporting on political situation",
            "archive_location": "CIA FOIA Reading Room",
            "observations": "",
            "language": "ENGLISH",
            "keywords": ["MILITARY COUP", "HUMAN RIGHTS", "OPERATION CONDOR"],
            "page_count": 3,
            "document_summary": "This cable reports on the political situation in Chile following the military coup.",
            "financial_references": {
                "amounts": [
                    {"value": "$1,000,000", "normalized_usd": 1000000, "context": "covert funding"}
                ],
                "financial_actors": ["CIA"],
                "purposes": ["POLITICAL ACTION"],
                "has_financial_content": True
            },
            "violence_references": {
                "incident_types": ["MILITARY COUP", "REPRESSION"],
                "victims": ["POLITICAL PRISONERS"],
                "perpetrators": ["DINA"],
                "has_violence_content": True
            },
            "torture_references": {
                "detention_centers": ["VILLA GRIMALDI"],
                "victims": ["DETAINED ACTIVISTS"],
                "perpetrators": ["DINA"],
                "methods_mentioned": ["ELECTRIC SHOCK"],
                "has_torture_content": True
            },
            "disappearance_references": {
                "victims": ["UNKNOWN DETAINEE"],
                "perpetrators": ["DINA"],
                "locations": ["SANTIAGO"],
                "dates_mentioned": ["1976-09-21"],
                "has_disappearance_content": True
            }
        },
        "original_text": "This is the original transcription.",
        "reviewed_text": "This is the reviewed transcription.",
        "confidence": {
            "overall": 0.85,
            "concerns": ["Partial redaction visible", "Some text illegible"]
        }
    }


@pytest.fixture
def sample_transcript_no_sensitive():
    """Create a transcript without sensitive content."""
    return {
        "metadata": {
            "document_id": "TEST-002",
            "case_number": "C5199900031",
            "document_date": "1975-03-15",
            "date_range": {"start_date": "", "end_date": "", "is_approximate": False},
            "classification_level": "CONFIDENTIAL",
            "declassification_date": "",
            "document_type": "MEMORANDUM",
            "author": "DOE, JANE",
            "recipients": ["STATE DEPARTMENT"],
            "people_mentioned": ["ALLENDE, SALVADOR"],
            "organizations_mentioned": [
                {"name": "STATE DEPARTMENT", "type": "GOVERNMENT", "country": "UNITED STATES"}
            ],
            "country": ["CHILE"],
            "city": ["VALPARAISO"],
            "other_place": [],
            "document_title": "Economic Briefing",
            "document_description": "Memo on economic conditions",
            "archive_location": "",
            "observations": "",
            "language": "ENGLISH",
            "keywords": ["ECONOMY", "COPPER"],
            "page_count": 2,
            "document_summary": "Memo discussing economic conditions in Chile.",
            "financial_references": {
                "amounts": [],
                "financial_actors": [],
                "purposes": [],
                "has_financial_content": False
            },
            "violence_references": {
                "incident_types": [],
                "victims": [],
                "perpetrators": [],
                "has_violence_content": False
            },
            "torture_references": {
                "detention_centers": [],
                "victims": [],
                "perpetrators": [],
                "methods_mentioned": [],
                "has_torture_content": False
            },
            "disappearance_references": {
                "victims": [],
                "perpetrators": [],
                "locations": [],
                "dates_mentioned": [],
                "has_disappearance_content": False
            }
        },
        "original_text": "Economic report text.",
        "reviewed_text": "Economic report text.",
        "confidence": {
            "overall": 0.95,
            "concerns": []
        }
    }


@pytest.fixture
def temp_transcripts_dir(sample_transcript, sample_transcript_no_sensitive):
    """Create a temporary directory with sample transcripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write sample transcripts
        with open(os.path.join(tmpdir, "doc_001.json"), "w") as f:
            json.dump(sample_transcript, f)
        with open(os.path.join(tmpdir, "doc_002.json"), "w") as f:
            json.dump(sample_transcript_no_sensitive, f)

        # Write a file that should be skipped
        with open(os.path.join(tmpdir, "failed_documents.json"), "w") as f:
            json.dump([{"id": "failed_doc"}], f)

        yield tmpdir


class TestProcessDocuments:
    """Tests for the process_documents function."""

    def test_processes_all_valid_files(self, temp_transcripts_dir):
        """Should process all valid JSON files and skip failed_* files."""
        results = process_documents(temp_transcripts_dir)

        assert results["total_docs"] == 2
        assert results["files_skipped"] == 1

    def test_counts_total_pages(self, temp_transcripts_dir):
        """Should sum up page counts from all documents."""
        results = process_documents(temp_transcripts_dir)

        # 3 pages + 2 pages = 5 total
        assert results["total_pages"] == 5

    def test_aggregates_classification_levels(self, temp_transcripts_dir):
        """Should count documents by classification level."""
        results = process_documents(temp_transcripts_dir)

        assert results["classification_count"]["SECRET"] == 1
        assert results["classification_count"]["CONFIDENTIAL"] == 1

    def test_aggregates_document_types(self, temp_transcripts_dir):
        """Should count documents by type."""
        results = process_documents(temp_transcripts_dir)

        assert results["doc_type_count"]["CABLE"] == 1
        assert results["doc_type_count"]["MEMORANDUM"] == 1

    def test_aggregates_timeline_yearly(self, temp_transcripts_dir):
        """Should aggregate documents by year."""
        results = process_documents(temp_transcripts_dir)

        assert results["timeline_yearly"]["1976"] == 1
        assert results["timeline_yearly"]["1975"] == 1

    def test_aggregates_people_mentioned(self, temp_transcripts_dir):
        """Should count people mentioned across documents."""
        results = process_documents(temp_transcripts_dir)

        assert "PINOCHET, AUGUSTO" in results["people_count"]
        assert "ALLENDE, SALVADOR" in results["people_count"]

    def test_aggregates_organizations(self, temp_transcripts_dir):
        """Should count organizations and their types/countries."""
        results = process_documents(temp_transcripts_dir)

        assert "DINA" in results["org_count"]
        assert "CIA" in results["org_count"]
        assert results["org_type_count"]["INTELLIGENCE_AGENCY"] == 2
        assert results["org_country_count"]["CHILE"] == 1

    def test_aggregates_locations(self, temp_transcripts_dir):
        """Should count countries, cities, and other places."""
        results = process_documents(temp_transcripts_dir)

        assert results["country_count"]["CHILE"] == 2
        assert results["city_count"]["SANTIAGO"] == 1
        assert results["city_count"]["VALPARAISO"] == 1
        assert results["other_place_count"]["LA MONEDA"] == 1

    def test_counts_violence_content(self, temp_transcripts_dir):
        """Should count documents with violence content."""
        results = process_documents(temp_transcripts_dir)

        assert results["docs_with_violence"] == 1
        assert "MILITARY COUP" in results["violence_incident_types"]
        assert "DINA" in results["violence_perpetrators"]

    def test_counts_torture_content(self, temp_transcripts_dir):
        """Should count documents with torture content."""
        results = process_documents(temp_transcripts_dir)

        assert results["docs_with_torture"] == 1
        assert "VILLA GRIMALDI" in results["torture_detention_centers"]
        assert "ELECTRIC SHOCK" in results["torture_methods"]

    def test_counts_disappearance_content(self, temp_transcripts_dir):
        """Should count documents with disappearance content."""
        results = process_documents(temp_transcripts_dir)

        assert results["docs_with_disappearance"] == 1
        assert "DINA" in results["disappearance_perpetrators"]

    def test_counts_financial_content(self, temp_transcripts_dir):
        """Should count documents with financial content."""
        results = process_documents(temp_transcripts_dir)

        assert results["docs_with_financial"] == 1
        assert "POLITICAL ACTION" in results["financial_purposes_count"]

    def test_aggregates_confidence_scores(self, temp_transcripts_dir):
        """Should collect confidence scores from all documents."""
        results = process_documents(temp_transcripts_dir)

        assert len(results["confidence_scores"]) == 2
        assert 0.85 in results["confidence_scores"]
        assert 0.95 in results["confidence_scores"]

    def test_aggregates_confidence_concerns(self, temp_transcripts_dir):
        """Should count confidence concerns."""
        results = process_documents(temp_transcripts_dir)

        assert "Partial redaction visible" in results["confidence_concerns"]
        assert results["confidence_concerns"]["Partial redaction visible"] == 1

    def test_handles_empty_directory(self):
        """Should handle directory with no JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = process_documents(tmpdir)

            assert results["total_docs"] == 0
            assert results["total_pages"] == 0

    def test_handles_unknown_dates(self):
        """Should handle documents with unknown dates (0000-00-00)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = {
                "metadata": {
                    "document_date": "0000-00-00",
                    "classification_level": "UNCLASSIFIED",
                    "document_type": "REPORT",
                    "people_mentioned": [],
                    "recipients": [],
                    "keywords": [],
                    "country": [],
                    "city": [],
                    "other_place": [],
                    "organizations_mentioned": [],
                    "page_count": 1,
                    "language": "ENGLISH",
                    "financial_references": {"has_financial_content": False, "amounts": [], "financial_actors": [], "purposes": []},
                    "violence_references": {"has_violence_content": False, "incident_types": [], "victims": [], "perpetrators": []},
                    "torture_references": {"has_torture_content": False, "detention_centers": [], "victims": [], "perpetrators": [], "methods_mentioned": []},
                    "disappearance_references": {"has_disappearance_content": False, "victims": [], "perpetrators": [], "locations": [], "dates_mentioned": []}
                },
                "original_text": "Text",
                "reviewed_text": "Text",
                "confidence": {"overall": 0.5, "concerns": []}
            }
            with open(os.path.join(tmpdir, "doc.json"), "w") as f:
                json.dump(doc, f)

            results = process_documents(tmpdir)

            assert results["timeline_yearly"]["Unknown"] == 1

    def test_skips_processing_files(self):
        """Should skip files with processing_ prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "processing_batch_001.json"), "w") as f:
                json.dump({"status": "processing"}, f)

            results = process_documents(tmpdir)

            assert results["total_docs"] == 0
            assert results["files_skipped"] == 1

    def test_skips_incomplete_files(self):
        """Should skip files with incomplete_ prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "incomplete_doc.json"), "w") as f:
                json.dump({"partial": True}, f)

            results = process_documents(tmpdir)

            assert results["total_docs"] == 0
            assert results["files_skipped"] == 1


class TestGenerateHtmlReport:
    """Tests for the generate_html_report function."""

    def test_creates_output_directory(self, temp_transcripts_dir):
        """Should create the output directory if it doesn't exist."""
        results = process_documents(temp_transcripts_dir)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "new_reports_dir")
            generate_html_report(results, output_dir=output_dir)

            assert os.path.exists(output_dir)
            assert os.path.exists(os.path.join(output_dir, "report.html"))

    def test_generates_html_file(self, temp_transcripts_dir):
        """Should generate an HTML report file."""
        results = process_documents(temp_transcripts_dir)

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_html_report(results, output_dir=tmpdir)

            report_path = os.path.join(tmpdir, "report.html")
            assert os.path.exists(report_path)

            with open(report_path, "r") as f:
                content = f.read()

            assert "<!DOCTYPE html>" in content
            assert "Declassified CIA Documents Analysis Report" in content

    def test_includes_summary_stats(self, temp_transcripts_dir):
        """Should include summary statistics in the report."""
        results = process_documents(temp_transcripts_dir)

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_html_report(results, output_dir=tmpdir)

            with open(os.path.join(tmpdir, "report.html"), "r") as f:
                content = f.read()

            assert "Total Documents" in content
            assert "Violence Content" in content
            assert "Torture Content" in content
            assert "Disappearances" in content

    def test_generates_charts_standalone(self, temp_transcripts_dir):
        """Should embed charts as base64 in standalone mode (default)."""
        results = process_documents(temp_transcripts_dir)

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_html_report(results, output_dir=tmpdir, standalone=True)

            # PNG files should be cleaned up
            assert not os.path.exists(os.path.join(tmpdir, "timeline_yearly.png"))
            assert not os.path.exists(os.path.join(tmpdir, "classification.png"))

            # Images should be embedded as base64 in HTML
            with open(os.path.join(tmpdir, "report.html"), "r") as f:
                content = f.read()
            assert "data:image/png;base64," in content

    def test_generates_charts_separate(self, temp_transcripts_dir):
        """Should save chart images as separate files when standalone=False."""
        results = process_documents(temp_transcripts_dir)

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_html_report(results, output_dir=tmpdir, standalone=False)

            # PNG files should exist
            assert os.path.exists(os.path.join(tmpdir, "timeline_yearly.png"))
            assert os.path.exists(os.path.join(tmpdir, "classification.png"))
            assert os.path.exists(os.path.join(tmpdir, "doc_types.png"))
            assert os.path.exists(os.path.join(tmpdir, "confidence.png"))

    def test_includes_sensitive_content_sections(self, temp_transcripts_dir):
        """Should include sensitive content sections with warnings."""
        results = process_documents(temp_transcripts_dir)

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_html_report(results, output_dir=tmpdir)

            with open(os.path.join(tmpdir, "report.html"), "r") as f:
                content = f.read()

            assert "Violence References" in content
            assert "Torture References" in content
            assert "Disappearance References" in content
            assert "Content Warning" in content

    def test_custom_output_filename(self, temp_transcripts_dir):
        """Should allow custom output filename."""
        results = process_documents(temp_transcripts_dir)

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_html_report(results, output_dir=tmpdir, output_file="custom_report.html")

            assert os.path.exists(os.path.join(tmpdir, "custom_report.html"))


class TestFullMode:
    """Tests for the full mode functionality with PDF links."""

    @pytest.fixture
    def temp_dir_with_pdfs(self, sample_transcript, sample_transcript_no_sensitive):
        """Create a temporary directory with sample transcripts and mock PDF directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create transcripts directory
            transcripts_dir = os.path.join(tmpdir, "transcripts")
            os.makedirs(transcripts_dir)

            # Create PDFs directory (just empty placeholder files for testing)
            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(pdfs_dir)

            # Write sample transcripts
            with open(os.path.join(transcripts_dir, "doc_001.json"), "w") as f:
                json.dump(sample_transcript, f)
            with open(os.path.join(transcripts_dir, "doc_002.json"), "w") as f:
                json.dump(sample_transcript_no_sensitive, f)

            # Create placeholder PDF files
            open(os.path.join(pdfs_dir, "doc_001.pdf"), "w").close()
            open(os.path.join(pdfs_dir, "doc_002.pdf"), "w").close()

            yield {"transcripts": transcripts_dir, "pdfs": pdfs_dir, "root": tmpdir}

    def test_full_mode_returns_document_list(self, temp_dir_with_pdfs):
        """Should return list of all documents in full mode."""
        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        assert results["full_mode"] is True
        assert len(results["all_documents"]) == 2

        # Check document structure
        doc = results["all_documents"][0]
        assert "basename" in doc
        assert "doc_id" in doc
        assert "pdf_path" in doc
        assert "date" in doc
        assert "classification" in doc

    def test_full_mode_returns_entity_doc_mappings(self, temp_dir_with_pdfs):
        """Should return entity-to-document mappings in full mode."""
        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        # Check people_docs mapping
        assert "PINOCHET, AUGUSTO" in results["people_docs"]
        assert len(results["people_docs"]["PINOCHET, AUGUSTO"]) == 1

        # Check keyword_docs mapping
        assert "MILITARY COUP" in results["keyword_docs"]
        assert len(results["keyword_docs"]["MILITARY COUP"]) == 1

        # Check org_docs mapping
        assert "DINA" in results["org_docs"]

    def test_full_mode_returns_sensitive_content_doc_mappings(self, temp_dir_with_pdfs):
        """Should return sensitive content entity-to-document mappings."""
        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        # Violence references
        assert "DINA" in results["violence_perp_docs"]

        # Torture references
        assert "VILLA GRIMALDI" in results["torture_center_docs"]

        # Disappearance references
        assert "UNKNOWN DETAINEE" in results["disappearance_victim_docs"]

    def test_full_mode_pdf_paths_are_correct(self, temp_dir_with_pdfs):
        """Should construct correct PDF paths."""
        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        # Check that PDF paths are correctly formed
        for doc in results["all_documents"]:
            expected_pdf = os.path.join(temp_dir_with_pdfs["pdfs"], f"{doc['basename']}.pdf")
            assert doc["pdf_path"] == expected_pdf

    def test_non_full_mode_returns_empty_collections(self, temp_dir_with_pdfs):
        """Should return empty document collections when not in full mode."""
        results = process_documents(temp_dir_with_pdfs["transcripts"])

        assert results["full_mode"] is False
        assert results["all_documents"] == []
        assert results["people_docs"] == {}
        assert results["keyword_docs"] == {}


class TestGenerateFullHtmlReport:
    """Tests for the generate_full_html_report function."""

    @pytest.fixture
    def temp_dir_with_pdfs(self, sample_transcript, sample_transcript_no_sensitive):
        """Create a temporary directory with sample transcripts and mock PDFs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcripts_dir = os.path.join(tmpdir, "transcripts")
            os.makedirs(transcripts_dir)

            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(pdfs_dir)

            with open(os.path.join(transcripts_dir, "doc_001.json"), "w") as f:
                json.dump(sample_transcript, f)
            with open(os.path.join(transcripts_dir, "doc_002.json"), "w") as f:
                json.dump(sample_transcript_no_sensitive, f)

            open(os.path.join(pdfs_dir, "doc_001.pdf"), "w").close()
            open(os.path.join(pdfs_dir, "doc_002.pdf"), "w").close()

            yield {"transcripts": transcripts_dir, "pdfs": pdfs_dir, "root": tmpdir}

    def test_generates_full_report_file(self, temp_dir_with_pdfs):
        """Should generate full report HTML file."""
        from app.analyze_documents import generate_full_html_report

        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        output_dir = os.path.join(temp_dir_with_pdfs["root"], "reports")
        generate_full_html_report(results, output_dir=output_dir)

        assert os.path.exists(os.path.join(output_dir, "report_full.html"))

    def test_full_report_contains_document_index(self, temp_dir_with_pdfs):
        """Should include document index section with PDF links."""
        from app.analyze_documents import generate_full_html_report

        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        output_dir = os.path.join(temp_dir_with_pdfs["root"], "reports")
        generate_full_html_report(results, output_dir=output_dir)

        with open(os.path.join(output_dir, "report_full.html"), "r") as f:
            content = f.read()

        assert "Document Index" in content
        assert "View PDF" in content
        assert "file://" in content

    def test_full_report_contains_expandable_entity_lists(self, temp_dir_with_pdfs):
        """Should include expandable entity lists using details element."""
        from app.analyze_documents import generate_full_html_report

        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        output_dir = os.path.join(temp_dir_with_pdfs["root"], "reports")
        generate_full_html_report(results, output_dir=output_dir)

        with open(os.path.join(output_dir, "report_full.html"), "r") as f:
            content = f.read()

        # Check for details/summary HTML elements
        assert "<details>" in content
        assert "<summary>" in content
        assert "documents</summary>" in content

    def test_full_report_has_full_mode_badge(self, temp_dir_with_pdfs):
        """Should display full mode badge in header."""
        from app.analyze_documents import generate_full_html_report

        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        output_dir = os.path.join(temp_dir_with_pdfs["root"], "reports")
        generate_full_html_report(results, output_dir=output_dir)

        with open(os.path.join(output_dir, "report_full.html"), "r") as f:
            content = f.read()

        assert "Full Report" in content
        assert "full-mode-badge" in content

    def test_full_report_embeds_images_by_default(self, temp_dir_with_pdfs):
        """Should embed chart images as base64 by default."""
        from app.analyze_documents import generate_full_html_report

        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        output_dir = os.path.join(temp_dir_with_pdfs["root"], "reports")
        generate_full_html_report(results, output_dir=output_dir, standalone=True)

        with open(os.path.join(output_dir, "report_full.html"), "r") as f:
            content = f.read()

        # Check for base64 embedded images
        assert "data:image/png;base64" in content

        # PNG files should not exist (cleaned up)
        assert not os.path.exists(os.path.join(output_dir, "timeline_yearly.png"))

    def test_external_pdf_viewer_generates_external_links(self, temp_dir_with_pdfs):
        """Should generate external PDF viewer links when external_pdf_viewer is provided."""
        from app.analyze_documents import generate_full_html_report

        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        output_dir = os.path.join(temp_dir_with_pdfs["root"], "reports")
        generate_full_html_report(
            results,
            output_dir=output_dir,
            external_pdf_viewer="https://declasseuucl.vercel.app"
        )

        with open(os.path.join(output_dir, "report_full.html"), "r") as f:
            content = f.read()

        # Check for external viewer URL pattern
        assert "https://declasseuucl.vercel.app/api/" in content
        assert "/download/pdf" in content
        assert 'class="pdf-link external"' in content
        # Should not have file:// URLs in href attributes (PDF links)
        assert 'href="file://' not in content

    def test_external_pdf_viewer_with_github_pages_mode(self, temp_dir_with_pdfs):
        """External PDF viewer should work with GitHub Pages mode."""
        from app.analyze_documents import generate_full_html_report

        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        output_dir = os.path.join(temp_dir_with_pdfs["root"], "reports")
        generate_full_html_report(
            results,
            output_dir=output_dir,
            github_pages_mode=True,
            external_pdf_viewer="https://declasseuucl.vercel.app"
        )

        with open(os.path.join(output_dir, "report_full.html"), "r") as f:
            content = f.read()

        # Should have external viewer links, not "PDFs not available" spans
        assert "https://declasseuucl.vercel.app/api/" in content
        assert 'class="pdf-link external"' in content
        # Check that no PDF links use the unavailable span (CSS class definition is ok)
        assert '<span class="pdf-unavailable"' not in content

    def test_github_pages_without_external_viewer_disables_links(self, temp_dir_with_pdfs):
        """GitHub Pages mode without external viewer should disable PDF links."""
        from app.analyze_documents import generate_full_html_report

        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        output_dir = os.path.join(temp_dir_with_pdfs["root"], "reports")
        generate_full_html_report(
            results,
            output_dir=output_dir,
            github_pages_mode=True,
            external_pdf_viewer=None
        )

        with open(os.path.join(output_dir, "report_full.html"), "r") as f:
            content = f.read()

        # Should have unavailable spans, not file:// links
        assert '<span class="pdf-unavailable"' in content
        assert 'href="file://' not in content

    def test_external_link_css_class_present(self, temp_dir_with_pdfs):
        """Should include CSS for external link indicator."""
        from app.analyze_documents import generate_full_html_report

        results = process_documents(
            temp_dir_with_pdfs["transcripts"],
            full_mode=True,
            pdf_dir=temp_dir_with_pdfs["pdfs"]
        )

        output_dir = os.path.join(temp_dir_with_pdfs["root"], "reports")
        generate_full_html_report(
            results,
            output_dir=output_dir,
            external_pdf_viewer="https://declasseuucl.vercel.app"
        )

        with open(os.path.join(output_dir, "report_full.html"), "r") as f:
            content = f.read()

        # Check for CSS rule for external links
        assert ".pdf-link.external::after" in content
