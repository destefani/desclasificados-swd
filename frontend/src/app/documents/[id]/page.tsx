"use client";

import { use } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { ClassificationBadge } from "@/components/documents/classification-badge";
import { PdfViewer } from "@/components/documents/pdf-viewer";
import { DocumentMetadataPanel } from "@/components/documents/document-metadata-panel";
import { DocumentTextPanel } from "@/components/documents/document-text-panel";
import { useDocument } from "@/hooks/useDocuments";
import { pdfUrl } from "@/lib/api";

function ConfidenceDot({ value }: { value: number }) {
  const color =
    value >= 0.8
      ? "bg-green-500"
      : value >= 0.5
        ? "bg-yellow-500"
        : "bg-red-500";
  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <span className={`inline-block h-2 w-2 rounded-full ${color}`} />
      {Math.round(value * 100)}%
    </span>
  );
}

export default function DocumentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: doc, isLoading } = useDocument(id);

  if (isLoading) {
    return (
      <div className="container py-8 space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-24" />
        </div>
        <Skeleton className="h-4 w-full" />
        <div className="flex gap-4">
          <Skeleton className="h-[70vh] flex-1" />
          <Skeleton className="h-[70vh] w-80" />
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="container py-8">
        <Link href="/explorer">
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Explorer
          </Button>
        </Link>
        <p className="text-muted-foreground">Document not found.</p>
      </div>
    );
  }

  return (
    <div className="container py-6 space-y-4">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link href="/explorer">
          <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0 mt-1">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold truncate">
            {doc.title || `Document ${doc.id}`}
          </h1>
          <div className="flex flex-wrap items-center gap-2 mt-1">
            <ClassificationBadge level={doc.classification} />
            {doc.type && <Badge variant="outline">{doc.type}</Badge>}
            {doc.date && <Badge variant="secondary">{doc.date}</Badge>}
            <Badge variant="secondary">
              {doc.pages} page{doc.pages !== 1 ? "s" : ""}
            </Badge>
            {doc.language && <Badge variant="secondary">{doc.language}</Badge>}
            <ConfidenceDot value={doc.confidence} />
          </div>
        </div>
      </div>

      {/* Summary */}
      {doc.summary && (
        <p className="text-sm text-muted-foreground">{doc.summary}</p>
      )}

      <Separator />

      {/* Main content: PDF + metadata sidebar */}
      <div className="flex gap-4">
        {/* PDF viewer */}
        <div className="flex-1 min-w-0">
          {doc.has_pdf && doc.source_file ? (
            <PdfViewer url={pdfUrl(doc.source_file)} />
          ) : (
            <div className="flex flex-col items-center justify-center h-96 border rounded bg-muted/50 gap-2">
              <p className="text-sm text-muted-foreground">PDF unavailable</p>
              {doc.source_file && (
                <a
                  href={pdfUrl(doc.source_file)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                >
                  <ExternalLink className="h-4 w-4" />
                  Try opening directly
                </a>
              )}
            </div>
          )}
        </div>

        {/* Metadata sidebar */}
        <div className="hidden lg:block">
          <DocumentMetadataPanel doc={doc} />
        </div>
      </div>

      {/* Mobile metadata (below PDF) */}
      <div className="lg:hidden">
        <DocumentMetadataPanel doc={doc} />
      </div>

      {/* Text content */}
      {(doc.reviewed_text || doc.original_text) && (
        <>
          <Separator />
          <DocumentTextPanel
            reviewedText={doc.reviewed_text}
            originalText={doc.original_text}
          />
        </>
      )}
    </div>
  );
}
