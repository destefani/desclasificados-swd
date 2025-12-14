#!/usr/bin/env python3
"""
Local web server for serving the HTML report with PDF viewer.

This server enables the embedded PDF viewer by serving both the HTML report
and the source PDFs over HTTP, bypassing browser security restrictions that
prevent loading file:// PDFs in JavaScript.

Usage:
    uv run python -m app.serve_report [OPTIONS]

Options:
    --report PATH     Path to the HTML report file (default: reports/report_full.html)
    --pdf-dir PATH    Directory containing source PDFs (default: data/original_pdfs)
    --port PORT       Port to serve on (default: 8000)
    --no-open         Don't auto-open browser
"""

import argparse
import os
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles


def create_app(report_path: str, pdf_dir: str) -> FastAPI:
    """
    Create the FastAPI application.

    Args:
        report_path: Path to the HTML report file
        pdf_dir: Directory containing source PDFs

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Declassified Documents Report Server",
        description="Local server for viewing the HTML report with embedded PDF viewer",
    )

    # Validate paths
    report_file = Path(report_path)
    pdf_directory = Path(pdf_dir)

    if not report_file.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")

    if not pdf_directory.exists():
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")

    @app.get("/", response_class=HTMLResponse)
    async def serve_report():
        """Serve the HTML report."""
        content = report_file.read_text(encoding="utf-8")
        return HTMLResponse(content=content)

    @app.get("/pdf/{filename:path}")
    async def serve_pdf(filename: str):
        """Serve a PDF file from the PDF directory."""
        # Security: prevent path traversal
        if ".." in filename or filename.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid filename")

        pdf_path = pdf_directory / filename

        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF not found: {filename}")

        if not pdf_path.suffix.lower() == ".pdf":
            raise HTTPException(status_code=400, detail="Only PDF files allowed")

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=filename,
        )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "ok",
            "report": str(report_file),
            "pdf_dir": str(pdf_directory),
        }

    return app


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Serve the HTML report with embedded PDF viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Serve with defaults
    uv run python -m app.serve_report

    # Specify custom paths
    uv run python -m app.serve_report --report reports/my_report.html --pdf-dir /path/to/pdfs

    # Use a different port
    uv run python -m app.serve_report --port 3000
        """,
    )
    parser.add_argument(
        "--report",
        default="reports/report_full.html",
        help="Path to the HTML report file (default: reports/report_full.html)",
    )
    parser.add_argument(
        "--pdf-dir",
        default="data/original_pdfs",
        help="Directory containing source PDFs (default: data/original_pdfs)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to serve on (default: 8000)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't auto-open browser",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )

    args = parser.parse_args()

    # Validate paths before starting
    if not os.path.exists(args.report):
        print(f"Error: Report file not found: {args.report}")
        print("Run 'make analyze-full' first to generate the report.")
        return 1

    if not os.path.exists(args.pdf_dir):
        print(f"Error: PDF directory not found: {args.pdf_dir}")
        return 1

    # Create the app
    app = create_app(args.report, args.pdf_dir)

    # Open browser
    url = f"http://{args.host}:{args.port}"
    if not args.no_open:
        print(f"Opening browser at {url}")
        webbrowser.open(url)

    print(f"\nServing report: {args.report}")
    print(f"PDF directory: {args.pdf_dir}")
    print(f"\nServer running at {url}")
    print("Press Ctrl+C to stop\n")

    # Run the server
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
