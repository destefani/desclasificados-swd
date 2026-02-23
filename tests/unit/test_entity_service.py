from pathlib import Path
from tests.unit.test_document_service import sample_transcripts  # reuse fixture


class TestEntityService:
    def test_build_entities(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        assert ent_svc.total_entities > 0

    def test_list_entities_by_type(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        result = ent_svc.list_entities(entity_type="person")
        assert result["total"] > 0
        for item in result["items"]:
            assert item["type"] == "person"

    def test_list_entities_search(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        result = ent_svc.list_entities(q="pinochet")
        assert result["total"] >= 1

    def test_list_entities_min_docs(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        result = ent_svc.list_entities(min_docs=100)
        assert result["total"] == 0

    def test_entity_documents(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        result = ent_svc.entity_documents("PINOCHET, AUGUSTO", "person")
        assert result["total"] == 3  # all 3 docs mention PINOCHET

    def test_sort_by_doc_count(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        result = ent_svc.list_entities(sort="doc_count_desc")
        counts = [item["doc_count"] for item in result["items"]]
        assert counts == sorted(counts, reverse=True)
