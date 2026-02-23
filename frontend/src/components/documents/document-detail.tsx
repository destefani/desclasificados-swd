"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ClassificationBadge } from "./classification-badge";
import { useDocument } from "@/hooks/useDocuments";
import { pdfUrl } from "@/lib/api";

export function DocumentDetail({
  docId,
  onClose,
}: {
  docId: string | null;
  onClose: () => void;
}) {
  const { data: doc, isLoading } = useDocument(docId);

  return (
    <Dialog open={!!docId} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        {isLoading || !doc ? (
          <div className="space-y-4">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>{doc.title || `Document ${doc.id}`}</DialogTitle>
            </DialogHeader>

            <div className="flex flex-wrap gap-2 mb-4">
              <ClassificationBadge level={doc.classification} />
              <Badge variant="outline">{doc.type}</Badge>
              <Badge variant="secondary">{doc.date}</Badge>
              <Badge variant="secondary">{doc.pages} pages</Badge>
              <Badge variant="secondary">{doc.language}</Badge>
            </div>

            {doc.summary && (
              <p className="text-sm text-muted-foreground mb-4">{doc.summary}</p>
            )}

            <Separator />

            {/* Metadata grid */}
            <div className="grid grid-cols-2 gap-4 text-sm my-4">
              {doc.author && <div><span className="font-medium">Author:</span> {doc.author}</div>}
              {doc.recipients?.length > 0 && (
                <div><span className="font-medium">Recipients:</span> {doc.recipients.join(", ")}</div>
              )}
              {doc.keywords?.length > 0 && (
                <div className="col-span-2">
                  <span className="font-medium">Keywords:</span>{" "}
                  {doc.keywords.map((k) => <Badge key={k} variant="outline" className="mr-1 mb-1">{k}</Badge>)}
                </div>
              )}
              {doc.people_mentioned?.length > 0 && (
                <div className="col-span-2">
                  <span className="font-medium">People:</span> {doc.people_mentioned.join(", ")}
                </div>
              )}
            </div>

            <Separator />

            {/* PDF embed */}
            {doc.has_pdf && (
              <div className="my-4">
                <h3 className="font-medium mb-2">Document PDF</h3>
                <iframe
                  src={pdfUrl(doc.id)}
                  className="w-full h-[600px] border rounded"
                  title={`PDF: ${doc.id}`}
                />
              </div>
            )}

            {/* Text content */}
            {doc.reviewed_text && (
              <div className="my-4">
                <h3 className="font-medium mb-2">Reviewed Text</h3>
                <pre className="whitespace-pre-wrap text-xs bg-muted p-4 rounded max-h-96 overflow-y-auto">
                  {doc.reviewed_text}
                </pre>
              </div>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
