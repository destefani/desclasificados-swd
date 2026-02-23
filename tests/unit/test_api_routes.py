# tests/unit/test_api_routes.py
import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(tmp_path: Path) -> TestClient:
    """Create a test client with sample data."""
    # Create separate subdirectories to avoid cross-contamination
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    misc_dir = tmp_path / "misc"
    misc_dir.mkdir()

    # Create sample transcripts
    for i, (doc_id, date, classification) in enumerate([
        ("00001", "1973-09-11", "TOP SECRET"),
        ("00002", "1976-09-21", "SECRET"),
    ]):
        data = {
            "metadata": {
                "document_id": doc_id,
                "case_number": f"C00{i}",
                "document_date": date,
                "classification_level": classification,
                "document_type": "CABLE",
                "document_title": f"Test Doc {doc_id}",
                "document_summary": f"Summary {doc_id}",
                "author": "",
                "recipients": [],
                "people_mentioned": ["PINOCHET, AUGUSTO"],
                "organizations_mentioned": [],
                "keywords": ["CIA"],
                "country": ["CHILE"],
                "city": [],
                "other_place": [],
                "language": "ENGLISH",
                "page_count": 1,
                "financial_references": {"has_financial_content": False, "amounts": [], "financial_actors": [], "purposes": []},
                "violence_references": {"has_violence_content": False, "incident_types": [], "victims": [], "perpetrators": []},
                "torture_references": {"has_torture_content": False, "detention_centers": [], "victims": [], "perpetrators": [], "methods_mentioned": []},
                "disappearance_references": {"has_disappearance_content": False, "victims": [], "perpetrators": [], "locations": [], "dates_mentioned": []},
            },
            "original_text": "Text",
            "reviewed_text": "Reviewed",
            "confidence": {"overall": 0.9, "concerns": []},
        }
        (transcripts_dir / f"{doc_id}.json").write_text(json.dumps(data))

    # Create a sample PDF
    (pdf_dir / "00001.pdf").write_bytes(b"%PDF-1.4 fake pdf")

    # Create research questions (in a separate directory to avoid DocumentService picking it up)
    rq = misc_dir / "research_questions.json"
    rq.write_text(json.dumps({
        "version": "1.0.0",
        "description": "test",
        "questions": [{"id": "RQ-001", "question": "Test?", "date_asked": "2025-01-01",
                        "category": "OTHER", "status": "unanswered", "rag_results": "",
                        "relevance_score": 0, "related_docs": [], "notes": None,
                        "pdf_report": None, "html_report": None}]
    }))

    from app.api.main import create_app
    app = create_app(
        transcripts_dir=transcripts_dir,
        pdf_dir=pdf_dir,
        research_questions_path=rq,
        research_reports_dir=misc_dir,
        total_pdfs=100,
    )
    return TestClient(app)


class TestDocumentsAPI:
    def test_list_documents(self, api_client: TestClient):
        resp = api_client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_documents_with_filter(self, api_client: TestClient):
        resp = api_client.get("/api/documents?classification=SECRET")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_document(self, api_client: TestClient):
        resp = api_client.get("/api/documents/00001")
        assert resp.status_code == 200
        assert resp.json()["id"] == "00001"
        assert "reviewed_text" in resp.json()

    def test_get_document_not_found(self, api_client: TestClient):
        resp = api_client.get("/api/documents/99999")
        assert resp.status_code == 404


class TestEntitiesAPI:
    def test_list_entities(self, api_client: TestClient):
        resp = api_client.get("/api/entities")
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_filter_by_type(self, api_client: TestClient):
        resp = api_client.get("/api/entities?type=person")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["type"] == "person"


class TestStatsAPI:
    def test_get_stats(self, api_client: TestClient):
        resp = api_client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 2
        assert "classification_distribution" in data


class TestPdfAPI:
    def test_serve_pdf(self, api_client: TestClient):
        resp = api_client.get("/api/pdf/00001")
        assert resp.status_code == 200

    def test_pdf_not_found(self, api_client: TestClient):
        resp = api_client.get("/api/pdf/99999")
        assert resp.status_code == 404


class TestReportsAPI:
    def test_list_reports(self, api_client: TestClient):
        resp = api_client.get("/api/reports")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1
