"""
PDF viewer modal using PDF.js.

Generates an embedded PDF viewer that opens in a modal when clicking
on PDF links in the report. Requires serving the report via HTTP
(not file://) for PDF.js to load the documents.
"""

# PDF.js CDN URLs
PDFJS_CDN = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"
PDFJS_WORKER_CDN = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js"


def generate_pdf_viewer_modal() -> str:
    """
    Generate HTML/CSS/JS for the PDF viewer modal.

    The modal includes:
    - PDF.js canvas rendering
    - Page navigation (prev/next, page input)
    - Zoom controls
    - Close button (and ESC key)
    - Loading spinner

    Returns:
        HTML string with embedded CSS and JavaScript
    """
    html = f'''
<!-- PDF Viewer Modal -->
<div id="pdf-viewer-modal" class="pdf-modal" style="display: none;">
    <div class="pdf-modal-backdrop" onclick="closePdfViewer()"></div>
    <div class="pdf-modal-content">
        <div class="pdf-modal-header">
            <div class="pdf-modal-title">
                <span id="pdf-viewer-filename">Document</span>
            </div>
            <div class="pdf-modal-controls">
                <button onclick="pdfZoomOut()" class="pdf-btn" title="Zoom Out">−</button>
                <span id="pdf-zoom-level">100%</span>
                <button onclick="pdfZoomIn()" class="pdf-btn" title="Zoom In">+</button>
                <button onclick="pdfFitWidth()" class="pdf-btn" title="Fit Width">↔</button>
                <span class="pdf-control-divider"></span>
                <button onclick="pdfPrevPage()" class="pdf-btn" title="Previous Page">◀</button>
                <span class="pdf-page-info">
                    <input type="number" id="pdf-page-input" min="1" value="1" onchange="pdfGoToPage(this.value)">
                    / <span id="pdf-total-pages">1</span>
                </span>
                <button onclick="pdfNextPage()" class="pdf-btn" title="Next Page">▶</button>
                <span class="pdf-control-divider"></span>
                <button onclick="closePdfViewer()" class="pdf-btn pdf-btn-close" title="Close (ESC)">✕</button>
            </div>
        </div>
        <div class="pdf-modal-body">
            <div id="pdf-loading" class="pdf-loading">
                <div class="pdf-spinner"></div>
                <p>Loading PDF...</p>
            </div>
            <div id="pdf-error" class="pdf-error" style="display: none;">
                <p>Failed to load PDF. <a href="#" id="pdf-download-link" target="_blank">Download instead</a></p>
            </div>
            <div id="pdf-canvas-container">
                <canvas id="pdf-canvas"></canvas>
            </div>
        </div>
    </div>
</div>

<style>
/* PDF Modal Styles */
.pdf-modal {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
}}

.pdf-modal-backdrop {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
}}

.pdf-modal-content {{
    position: relative;
    width: 95%;
    max-width: 1200px;
    height: 95%;
    max-height: 95vh;
    background: #1f2937;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
}}

.pdf-modal-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: #111827;
    border-bottom: 1px solid #374151;
    flex-shrink: 0;
}}

.pdf-modal-title {{
    color: #f3f4f6;
    font-weight: 500;
    font-size: 14px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 300px;
}}

.pdf-modal-controls {{
    display: flex;
    align-items: center;
    gap: 8px;
}}

.pdf-btn {{
    background: #374151;
    color: #f3f4f6;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background 0.2s;
}}

.pdf-btn:hover {{
    background: #4b5563;
}}

.pdf-btn-close {{
    background: #dc2626;
}}

.pdf-btn-close:hover {{
    background: #ef4444;
}}

.pdf-control-divider {{
    width: 1px;
    height: 20px;
    background: #374151;
    margin: 0 4px;
}}

.pdf-page-info {{
    color: #f3f4f6;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 4px;
}}

#pdf-page-input {{
    width: 50px;
    padding: 4px 8px;
    border: 1px solid #374151;
    border-radius: 4px;
    background: #1f2937;
    color: #f3f4f6;
    text-align: center;
    font-size: 14px;
}}

#pdf-page-input:focus {{
    outline: none;
    border-color: #3b82f6;
}}

#pdf-zoom-level {{
    color: #9ca3af;
    font-size: 12px;
    min-width: 45px;
    text-align: center;
}}

.pdf-modal-body {{
    flex: 1;
    overflow: auto;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 20px;
    background: #374151;
}}

#pdf-canvas-container {{
    display: flex;
    justify-content: center;
}}

#pdf-canvas {{
    max-width: 100%;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}}

.pdf-loading {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #f3f4f6;
    padding: 40px;
}}

.pdf-spinner {{
    width: 40px;
    height: 40px;
    border: 3px solid #374151;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: pdf-spin 1s linear infinite;
}}

@keyframes pdf-spin {{
    to {{ transform: rotate(360deg); }}
}}

.pdf-error {{
    color: #fca5a5;
    text-align: center;
    padding: 40px;
}}

.pdf-error a {{
    color: #60a5fa;
}}

/* Responsive adjustments */
@media (max-width: 768px) {{
    .pdf-modal-content {{
        width: 100%;
        height: 100%;
        max-height: 100%;
        border-radius: 0;
    }}

    .pdf-modal-header {{
        flex-wrap: wrap;
        gap: 10px;
    }}

    .pdf-modal-title {{
        width: 100%;
        max-width: none;
    }}
}}
</style>

<script src="{PDFJS_CDN}"></script>
<script>
(function() {{
    // Set PDF.js worker
    pdfjsLib.GlobalWorkerOptions.workerSrc = '{PDFJS_WORKER_CDN}';

    // State
    let currentPdf = null;
    let currentPage = 1;
    let totalPages = 0;
    let currentScale = 1.0;
    let currentPdfUrl = '';

    // DOM elements
    const modal = document.getElementById('pdf-viewer-modal');
    const canvas = document.getElementById('pdf-canvas');
    const ctx = canvas.getContext('2d');
    const loading = document.getElementById('pdf-loading');
    const error = document.getElementById('pdf-error');
    const canvasContainer = document.getElementById('pdf-canvas-container');
    const filenameEl = document.getElementById('pdf-viewer-filename');
    const pageInput = document.getElementById('pdf-page-input');
    const totalPagesEl = document.getElementById('pdf-total-pages');
    const zoomLevelEl = document.getElementById('pdf-zoom-level');
    const downloadLink = document.getElementById('pdf-download-link');

    // Open PDF viewer
    window.openPdfViewer = async function(url, filename) {{
        currentPdfUrl = url;
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Show loading, hide error and canvas
        loading.style.display = 'flex';
        error.style.display = 'none';
        canvas.style.display = 'none';

        // Set filename
        filenameEl.textContent = filename || url.split('/').pop();
        downloadLink.href = url;

        try {{
            // Load PDF
            currentPdf = await pdfjsLib.getDocument(url).promise;
            totalPages = currentPdf.numPages;
            currentPage = 1;
            currentScale = 1.0;

            // Update UI
            totalPagesEl.textContent = totalPages;
            pageInput.max = totalPages;
            pageInput.value = 1;
            updateZoomDisplay();

            // Render first page
            await renderPage(currentPage);

            // Hide loading, show canvas
            loading.style.display = 'none';
            canvas.style.display = 'block';
        }} catch (err) {{
            console.error('Error loading PDF:', err);
            loading.style.display = 'none';
            error.style.display = 'block';
        }}
    }};

    // Close PDF viewer
    window.closePdfViewer = function() {{
        modal.style.display = 'none';
        document.body.style.overflow = '';
        currentPdf = null;
    }};

    // Render a page
    async function renderPage(pageNum) {{
        if (!currentPdf) return;

        const page = await currentPdf.getPage(pageNum);
        const viewport = page.getViewport({{ scale: currentScale }});

        canvas.height = viewport.height;
        canvas.width = viewport.width;

        await page.render({{
            canvasContext: ctx,
            viewport: viewport
        }}).promise;

        pageInput.value = pageNum;
    }}

    // Navigation
    window.pdfPrevPage = function() {{
        if (currentPage > 1) {{
            currentPage--;
            renderPage(currentPage);
        }}
    }};

    window.pdfNextPage = function() {{
        if (currentPage < totalPages) {{
            currentPage++;
            renderPage(currentPage);
        }}
    }};

    window.pdfGoToPage = function(pageNum) {{
        const page = parseInt(pageNum, 10);
        if (page >= 1 && page <= totalPages) {{
            currentPage = page;
            renderPage(currentPage);
        }} else {{
            pageInput.value = currentPage;
        }}
    }};

    // Zoom
    function updateZoomDisplay() {{
        zoomLevelEl.textContent = Math.round(currentScale * 100) + '%';
    }}

    window.pdfZoomIn = function() {{
        currentScale = Math.min(currentScale + 0.25, 4.0);
        updateZoomDisplay();
        renderPage(currentPage);
    }};

    window.pdfZoomOut = function() {{
        currentScale = Math.max(currentScale - 0.25, 0.25);
        updateZoomDisplay();
        renderPage(currentPage);
    }};

    window.pdfFitWidth = function() {{
        if (!currentPdf) return;

        currentPdf.getPage(currentPage).then(page => {{
            const containerWidth = canvasContainer.clientWidth - 40;
            const viewport = page.getViewport({{ scale: 1.0 }});
            currentScale = containerWidth / viewport.width;
            updateZoomDisplay();
            renderPage(currentPage);
        }});
    }};

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {{
        if (modal.style.display !== 'flex') return;

        switch(e.key) {{
            case 'Escape':
                closePdfViewer();
                break;
            case 'ArrowLeft':
                pdfPrevPage();
                break;
            case 'ArrowRight':
                pdfNextPage();
                break;
            case '+':
            case '=':
                if (e.ctrlKey || e.metaKey) {{
                    e.preventDefault();
                    pdfZoomIn();
                }}
                break;
            case '-':
                if (e.ctrlKey || e.metaKey) {{
                    e.preventDefault();
                    pdfZoomOut();
                }}
                break;
        }}
    }});
}})();
</script>
'''
    return html


def generate_pdf_link_interceptor() -> str:
    """
    Generate JavaScript that intercepts clicks on PDF links
    and opens them in the PDF viewer modal instead.

    Returns:
        JavaScript code as a string
    """
    js = '''
<script>
(function() {
    // Intercept clicks on PDF links
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a[href$=".pdf"]');
        if (link && link.href.startsWith(window.location.origin)) {
            e.preventDefault();
            const filename = link.href.split('/').pop();
            openPdfViewer(link.href, decodeURIComponent(filename));
        }
    });
})();
</script>
'''
    return js


def generate_external_viewer_modal() -> str:
    """
    Generate HTML/CSS/JS for an iframe-based external PDF viewer modal.

    This modal embeds the external viewer (e.g., declasseuucl.vercel.app)
    in an iframe, allowing users to view PDFs without leaving the page.

    Returns:
        HTML string with embedded CSS and JavaScript
    """
    html = '''
<!-- External PDF Viewer Modal -->
<div id="external-viewer-modal" class="external-modal" style="display: none;">
    <div class="external-modal-backdrop" onclick="closeExternalViewer()"></div>
    <div class="external-modal-content">
        <div class="external-modal-header">
            <div class="external-modal-title">
                <span id="external-viewer-title">Document Viewer</span>
            </div>
            <div class="external-modal-controls">
                <a id="external-viewer-newwindow" href="#" target="_blank" class="external-btn" title="Open in new window">↗ New Window</a>
                <button onclick="closeExternalViewer()" class="external-btn external-btn-close" title="Close (ESC)">✕ Close</button>
            </div>
        </div>
        <div class="external-modal-body">
            <div id="external-loading" class="external-loading">
                <div class="external-spinner"></div>
                <p>Loading viewer...</p>
            </div>
            <iframe id="external-viewer-iframe" src="" frameborder="0" allowfullscreen></iframe>
        </div>
    </div>
</div>

<style>
/* External Viewer Modal Styles */
.external-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
}

.external-modal-backdrop {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
}

.external-modal-content {
    position: relative;
    width: 95%;
    max-width: 1400px;
    height: 95%;
    max-height: 95vh;
    background: #1f2937;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.external-modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: #111827;
    border-bottom: 1px solid #374151;
    flex-shrink: 0;
}

.external-modal-title {
    color: #f3f4f6;
    font-weight: 500;
    font-size: 14px;
}

.external-modal-controls {
    display: flex;
    gap: 12px;
    align-items: center;
}

.external-btn {
    background: #374151;
    color: #f3f4f6;
    border: none;
    padding: 8px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    text-decoration: none;
    transition: background 0.2s;
}

.external-btn:hover {
    background: #4b5563;
}

.external-btn-close {
    background: #dc2626;
}

.external-btn-close:hover {
    background: #b91c1c;
}

.external-modal-body {
    flex: 1;
    position: relative;
    overflow: hidden;
}

#external-viewer-iframe {
    width: 100%;
    height: 100%;
    border: none;
    background: #fff;
}

.external-loading {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: #9ca3af;
}

.external-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #374151;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: external-spin 1s linear infinite;
    margin: 0 auto 12px;
}

@keyframes external-spin {
    to { transform: rotate(360deg); }
}
</style>

<script>
(function() {
    const modal = document.getElementById('external-viewer-modal');
    const iframe = document.getElementById('external-viewer-iframe');
    const loading = document.getElementById('external-loading');
    const titleEl = document.getElementById('external-viewer-title');
    const newWindowLink = document.getElementById('external-viewer-newwindow');

    // Open external viewer in modal
    window.openExternalViewer = function(url, title) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        loading.style.display = 'block';
        iframe.style.opacity = '0';

        titleEl.textContent = title || 'Document Viewer';
        newWindowLink.href = url;
        iframe.src = url;

        iframe.onload = function() {
            loading.style.display = 'none';
            iframe.style.opacity = '1';
        };
    };

    // Close the modal
    window.closeExternalViewer = function() {
        modal.style.display = 'none';
        document.body.style.overflow = '';
        iframe.src = '';
    };

    // ESC key to close
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            closeExternalViewer();
        }
    });
})();
</script>
'''
    return html


def generate_external_link_interceptor() -> str:
    """
    Generate JavaScript that intercepts clicks on external PDF links
    and opens them in the iframe modal instead of a new tab.

    Returns:
        JavaScript code as a string
    """
    js = '''
<script>
(function() {
    // Intercept clicks on external PDF links
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a.pdf-link.external');
        if (link) {
            e.preventDefault();
            // Extract document ID from URL for title
            const url = new URL(link.href);
            const docId = url.searchParams.get('documentId') || 'Document';
            openExternalViewer(link.href, 'Document ' + docId);
        }
    });
})();
</script>
'''
    return js
