import pytest
import json
from pathlib import Path


@pytest.fixture
def sample_transcripts(tmp_path: Path) -> Path:
    """Create a temp directory with 3 sample JSON transcript files."""
    for i, (doc_id, date, classification, doc_type) in enumerate([
        ("00001", "1973-09-11", "TOP SECRET", "MEMORANDUM"),
        ("00002", "1976-09-21", "SECRET", "CABLE"),
        ("00003", "1970-11-03", "CONFIDENTIAL", "REPORT"),
    ]):
        data = {
            "metadata": {
                "document_id": doc_id,
                "case_number": f"C00{i}",
                "document_date": date,
                "classification_level": classification,
                "document_type": doc_type,
                "document_title": f"Test Document {doc_id}",
                "document_summary": f"Summary for document {doc_id}",
                "author": "SMITH, JOHN",
                "recipients": ["DOE, JANE"],
                "people_mentioned": ["PINOCHET, AUGUSTO"],
                "organizations_mentioned": [
                    {"name": "CIA", "type": "INTELLIGENCE_AGENCY", "country": "UNITED STATES"}
                ],
                "keywords": ["COUP 1973", "CIA"],
                "country": ["CHILE"],
                "city": ["SANTIAGO"],
                "other_place": [],
                "language": "ENGLISH",
                "page_count": i + 1,
                "financial_references": {"has_financial_content": False, "amounts": [], "financial_actors": [], "purposes": []},
                "violence_references": {"has_violence_content": False, "incident_types": [], "victims": [], "perpetrators": []},
                "torture_references": {"has_torture_content": False, "detention_centers": [], "victims": [], "perpetrators": [], "methods_mentioned": []},
                "disappearance_references": {"has_disappearance_content": False, "victims": [], "perpetrators": [], "locations": [], "dates_mentioned": []},
            },
            "original_text": f"Original text for {doc_id}",
            "reviewed_text": f"Reviewed text for {doc_id}",
            "confidence": {"overall": 0.9, "concerns": []},
        }
        (tmp_path / f"{doc_id}.json").write_text(json.dumps(data))
    return tmp_path


class TestDocumentService:
    def test_load_documents(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        assert svc.total_documents == 3

    def test_list_documents_default(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(page=1, page_size=25)
        assert result["total"] == 3
        assert len(result["items"]) == 3
        # Default sort is date_desc
        assert result["items"][0]["id"] == "00002"  # 1976 first

    def test_list_documents_pagination(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(page=1, page_size=2)
        assert len(result["items"]) == 2
        assert result["total_pages"] == 2
        result2 = svc.list_documents(page=2, page_size=2)
        assert len(result2["items"]) == 1

    def test_filter_by_classification(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(classification=["SECRET"])
        assert result["total"] == 1
        assert result["items"][0]["id"] == "00002"

    def test_filter_by_date_range(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(date_from="1973-01-01", date_to="1976-12-31")
        assert result["total"] == 2

    def test_search_by_query(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(q="00002")
        assert result["total"] == 1

    def test_get_document_by_id(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        doc = svc.get_document("00001")
        assert doc is not None
        assert doc["id"] == "00001"
        assert "original_text" in doc
        assert "reviewed_text" in doc
        assert doc["source_file"] == "00001"
        # New metadata fields
        assert doc["other_places"] == []
        assert doc["declassification_date"] == ""
        assert doc["document_description"] == ""
        assert doc["archive_location"] == ""
        assert doc["observations"] == ""
        assert doc["date_range"] is None
        assert isinstance(doc["organizations_detail"], list)
        assert len(doc["organizations_detail"]) == 1
        assert doc["organizations_detail"][0]["name"] == "CIA"
        assert doc["organizations_detail"][0]["type"] == "INTELLIGENCE_AGENCY"
        assert doc["organizations_detail"][0]["country"] == "UNITED STATES"

    def test_get_document_has_pdf_with_dir(self, sample_transcripts: Path, tmp_path: Path):
        from app.api.services.document_service import DocumentService
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "00001.pdf").write_bytes(b"%PDF")
        svc = DocumentService(sample_transcripts, pdf_dir=pdf_dir)
        doc = svc.get_document("00001")
        assert doc is not None
        assert doc["has_pdf"] is True
        doc2 = svc.get_document("00002")
        assert doc2 is not None
        assert doc2["has_pdf"] is False

    def test_get_document_not_found(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        doc = svc.get_document("99999")
        assert doc is None

    def test_sort_date_asc(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(sort="date_asc")
        assert result["items"][0]["id"] == "00003"  # 1970 first

    def test_filter_by_type(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(doc_type=["CABLE"])
        assert result["total"] == 1
