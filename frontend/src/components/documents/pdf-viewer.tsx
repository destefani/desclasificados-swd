"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ExternalLink,
} from "lucide-react";

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfViewerProps {
  url: string;
}

export function PdfViewer({ url }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1);
  const [fitWidth, setFitWidth] = useState(true);
  const [containerWidth, setContainerWidth] = useState<number>(0);
  const [error, setError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const onDocumentLoadSuccess = useCallback(
    ({ numPages: total }: { numPages: number }) => {
      setNumPages(total);
      setError(false);
    },
    []
  );

  const onDocumentLoadError = useCallback(() => {
    setError(true);
  }, []);

  const goToPrev = () => setPageNumber((p) => Math.max(1, p - 1));
  const goToNext = () => setPageNumber((p) => Math.min(numPages, p + 1));
  const zoomIn = () => {
    setFitWidth(false);
    setScale((s) => Math.min(3, s + 0.25));
  };
  const zoomOut = () => {
    setFitWidth(false);
    setScale((s) => Math.max(0.25, s - 0.25));
  };
  const toggleFitWidth = () => {
    setFitWidth((f) => !f);
    if (!fitWidth) setScale(1);
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 border rounded bg-muted/50 gap-4">
        <p className="text-sm text-muted-foreground">Failed to load PDF</p>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
        >
          <ExternalLink className="h-4 w-4" />
          Open in new tab
        </a>
      </div>
    );
  }

  return (
    <div className="flex flex-col border rounded overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b bg-muted/50 flex-wrap">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={goToPrev}
            disabled={pageNumber <= 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm min-w-[80px] text-center tabular-nums">
            Page {pageNumber} of {numPages || "..."}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={goToNext}
            disabled={pageNumber >= numPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={zoomOut}
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-xs min-w-[40px] text-center tabular-nums">
            {fitWidth ? "Fit" : `${Math.round(scale * 100)}%`}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={zoomIn}
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleFitWidth}
            className={`h-8 w-8 ${fitWidth ? "bg-accent" : ""}`}
          >
            <Maximize2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* PDF content */}
      <div
        ref={containerRef}
        className="overflow-auto bg-neutral-100 dark:bg-neutral-900"
        style={{ height: "70vh" }}
      >
        <div className="flex justify-center py-4">
          <Document
            file={url}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="flex flex-col items-center gap-4 py-12">
                <Skeleton className="h-[600px] w-[450px]" />
              </div>
            }
          >
            <Page
              pageNumber={pageNumber}
              scale={fitWidth ? undefined : scale}
              width={fitWidth && containerWidth > 0 ? containerWidth - 48 : undefined}
              loading={<Skeleton className="h-[600px] w-[450px]" />}
            />
          </Document>
        </div>
      </div>
    </div>
  );
}
