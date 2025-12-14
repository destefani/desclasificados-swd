"""Tests for the serve_report module."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.serve_report import create_app


@pytest.fixture
def temp_report_setup():
    """Create temporary report and PDF directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test report file
        report_path = os.path.join(tmpdir, "test_report.html")
        with open(report_path, "w") as f:
            f.write("<html><body><h1>Test Report</h1></body></html>")

        # Create a PDF directory with test PDFs
        pdf_dir = os.path.join(tmpdir, "pdfs")
        os.makedirs(pdf_dir)

        # Create a minimal PDF file (just enough to test serving)
        test_pdf_path = os.path.join(pdf_dir, "test_doc.pdf")
        with open(test_pdf_path, "wb") as f:
            # Minimal PDF header
            f.write(b"%PDF-1.4\n%test\n")

        yield {
            "tmpdir": tmpdir,
            "report_path": report_path,
            "pdf_dir": pdf_dir,
            "test_pdf_path": test_pdf_path,
        }


class TestCreateApp:
    """Tests for create_app function."""

    def test_creates_fastapi_app(self, temp_report_setup):
        """Test that create_app returns a FastAPI application."""
        app = create_app(
            temp_report_setup["report_path"],
            temp_report_setup["pdf_dir"]
        )
        assert app is not None
        assert hasattr(app, "routes")

    def test_raises_error_for_missing_report(self, temp_report_setup):
        """Test that create_app raises error for missing report file."""
        with pytest.raises(FileNotFoundError):
            create_app(
                "/nonexistent/report.html",
                temp_report_setup["pdf_dir"]
            )

    def test_raises_error_for_missing_pdf_dir(self, temp_report_setup):
        """Test that create_app raises error for missing PDF directory."""
        with pytest.raises(FileNotFoundError):
            create_app(
                temp_report_setup["report_path"],
                "/nonexistent/pdf_dir"
            )


class TestReportEndpoint:
    """Tests for the report serving endpoint."""

    def test_serves_report_at_root(self, temp_report_setup):
        """Test that GET / returns the HTML report."""
        app = create_app(
            temp_report_setup["report_path"],
            temp_report_setup["pdf_dir"]
        )
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Test Report" in response.text


class TestPdfEndpoint:
    """Tests for the PDF serving endpoint."""

    def test_serves_pdf_file(self, temp_report_setup):
        """Test that GET /pdf/filename.pdf returns the PDF."""
        app = create_app(
            temp_report_setup["report_path"],
            temp_report_setup["pdf_dir"]
        )
        client = TestClient(app)

        response = client.get("/pdf/test_doc.pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")

    def test_returns_404_for_missing_pdf(self, temp_report_setup):
        """Test that GET /pdf/nonexistent.pdf returns 404."""
        app = create_app(
            temp_report_setup["report_path"],
            temp_report_setup["pdf_dir"]
        )
        client = TestClient(app)

        response = client.get("/pdf/nonexistent.pdf")
        assert response.status_code == 404

    def test_rejects_path_traversal(self, temp_report_setup):
        """Test that path traversal attempts are rejected or not found."""
        app = create_app(
            temp_report_setup["report_path"],
            temp_report_setup["pdf_dir"]
        )
        client = TestClient(app)

        # Try path traversal - may return 400 (rejected) or 404 (normalized away)
        # Both are secure as the file won't be served
        response = client.get("/pdf/../../../etc/passwd")
        assert response.status_code in (400, 404)

        # Also test with encoded dots
        response = client.get("/pdf/..%2F..%2F..%2Fetc%2Fpasswd")
        assert response.status_code in (400, 404)

    def test_rejects_absolute_paths(self, temp_report_setup):
        """Test that absolute paths are rejected."""
        app = create_app(
            temp_report_setup["report_path"],
            temp_report_setup["pdf_dir"]
        )
        client = TestClient(app)

        response = client.get("/pdf//etc/passwd")
        assert response.status_code == 400

    def test_rejects_non_pdf_files(self, temp_report_setup):
        """Test that non-PDF files are rejected."""
        # Create a non-PDF file
        txt_path = os.path.join(temp_report_setup["pdf_dir"], "test.txt")
        with open(txt_path, "w") as f:
            f.write("not a pdf")

        app = create_app(
            temp_report_setup["report_path"],
            temp_report_setup["pdf_dir"]
        )
        client = TestClient(app)

        response = client.get("/pdf/test.txt")
        assert response.status_code == 400


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check_returns_ok(self, temp_report_setup):
        """Test that GET /health returns status ok."""
        app = create_app(
            temp_report_setup["report_path"],
            temp_report_setup["pdf_dir"]
        )
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "report" in data
        assert "pdf_dir" in data
