"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ClassificationBadge } from "./classification-badge";
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

function MetadataSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </h4>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function SensitiveFlags({
  violence,
  torture,
  disappearance,
  financial,
}: {
  violence: boolean;
  torture: boolean;
  disappearance: boolean;
  financial: boolean;
}) {
  const flags = [
    violence && "Violence",
    torture && "Torture",
    disappearance && "Disappearances",
    financial && "Financial",
  ].filter(Boolean) as string[];

  if (flags.length === 0) return null;

  return (
    <MetadataSection label="Sensitive Content">
      <div className="flex flex-wrap gap-1">
        {flags.map((f) => (
          <Badge key={f} variant="destructive" className="text-xs">
            {f}
          </Badge>
        ))}
      </div>
    </MetadataSection>
  );
}

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
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isLoading || !doc ? "Loading..." : doc.title || `Document ${doc.id}`}
          </DialogTitle>
        </DialogHeader>

        {isLoading || !doc ? (
          <div className="space-y-4">
            <div className="flex gap-2">
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-5 w-24" />
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <div className="grid grid-cols-3 gap-4">
              <Skeleton className="h-64 col-span-2" />
              <Skeleton className="h-64" />
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Badge row */}
            <div className="flex flex-wrap items-center gap-2">
              <ClassificationBadge level={doc.classification} />
              {doc.type && <Badge variant="outline">{doc.type}</Badge>}
              {doc.date && <Badge variant="secondary">{doc.date}</Badge>}
              <Badge variant="secondary">{doc.pages} page{doc.pages !== 1 ? "s" : ""}</Badge>
              {doc.language && <Badge variant="secondary">{doc.language}</Badge>}
              <ConfidenceDot value={doc.confidence} />
            </div>

            {/* Summary */}
            {doc.summary && (
              <p className="text-sm text-muted-foreground">{doc.summary}</p>
            )}

            <Separator />

            {/* Two-column layout: content + metadata sidebar */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Left: PDF or reviewed text */}
              <div className="md:col-span-2">
                {doc.has_pdf && doc.source_file ? (
                  <iframe
                    src={pdfUrl(doc.source_file)}
                    className="w-full h-[600px] border rounded"
                    title={`PDF: ${doc.id}`}
                  />
                ) : doc.reviewed_text ? (
                  <div>
                    <h3 className="font-medium mb-2 text-sm">Reviewed Text</h3>
                    <pre className="whitespace-pre-wrap text-xs bg-muted p-4 rounded max-h-[600px] overflow-y-auto">
                      {doc.reviewed_text}
                    </pre>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-48 border rounded bg-muted/50 text-sm text-muted-foreground">
                    PDF unavailable
                  </div>
                )}
              </div>

              {/* Right: Metadata sidebar */}
              <div className="space-y-4">
                {doc.author && (
                  <MetadataSection label="Author">
                    {doc.author}
                  </MetadataSection>
                )}

                {doc.recipients?.length > 0 && (
                  <MetadataSection label="Recipients">
                    {doc.recipients.join(", ")}
                  </MetadataSection>
                )}

                {doc.keywords?.length > 0 && (
                  <MetadataSection label="Keywords">
                    <div className="flex flex-wrap gap-1">
                      {doc.keywords.map((k) => (
                        <Badge key={k} variant="outline" className="text-xs">
                          {k}
                        </Badge>
                      ))}
                    </div>
                  </MetadataSection>
                )}

                {doc.people_mentioned?.length > 0 && (
                  <MetadataSection label="People">
                    {doc.people_mentioned.join(", ")}
                  </MetadataSection>
                )}

                {doc.organizations_mentioned?.length > 0 && (
                  <MetadataSection label="Organizations">
                    {doc.organizations_mentioned.join(", ")}
                  </MetadataSection>
                )}

                {(doc.countries_mentioned?.length > 0 || doc.cities_mentioned?.length > 0) && (
                  <MetadataSection label="Locations">
                    <div>
                      {doc.countries_mentioned?.length > 0 && (
                        <div>{doc.countries_mentioned.join(", ")}</div>
                      )}
                      {doc.cities_mentioned?.length > 0 && (
                        <div className="text-muted-foreground">
                          {doc.cities_mentioned.join(", ")}
                        </div>
                      )}
                    </div>
                  </MetadataSection>
                )}

                <SensitiveFlags
                  violence={doc.has_violence_content}
                  torture={doc.has_torture_content}
                  disappearance={doc.has_disappearance_content}
                  financial={doc.has_financial_content}
                />

                {doc.concerns?.length > 0 && (
                  <MetadataSection label="Concerns">
                    <div className="flex flex-wrap gap-1">
                      {doc.concerns.map((c, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          {c}
                        </Badge>
                      ))}
                    </div>
                  </MetadataSection>
                )}
              </div>
            </div>

            {/* Tabs for text content (only if PDF is shown and text exists) */}
            {doc.has_pdf && doc.source_file && (doc.reviewed_text || doc.original_text) && (
              <>
                <Separator />
                <Tabs defaultValue="reviewed">
                  <TabsList>
                    {doc.reviewed_text && (
                      <TabsTrigger value="reviewed">Reviewed Text</TabsTrigger>
                    )}
                    {doc.original_text && (
                      <TabsTrigger value="original">Original Text</TabsTrigger>
                    )}
                  </TabsList>
                  {doc.reviewed_text && (
                    <TabsContent value="reviewed">
                      <pre className="whitespace-pre-wrap text-xs bg-muted p-4 rounded max-h-96 overflow-y-auto mt-2">
                        {doc.reviewed_text}
                      </pre>
                    </TabsContent>
                  )}
                  {doc.original_text && (
                    <TabsContent value="original">
                      <pre className="whitespace-pre-wrap text-xs bg-muted p-4 rounded max-h-96 overflow-y-auto mt-2">
                        {doc.original_text}
                      </pre>
                    </TabsContent>
                  )}
                </Tabs>
              </>
            )}

            {/* If no PDF, show original text tab below */}
            {(!doc.has_pdf || !doc.source_file) && doc.original_text && doc.reviewed_text && (
              <>
                <Separator />
                <Tabs defaultValue="original">
                  <TabsList>
                    <TabsTrigger value="original">Original Text</TabsTrigger>
                  </TabsList>
                  <TabsContent value="original">
                    <pre className="whitespace-pre-wrap text-xs bg-muted p-4 rounded max-h-96 overflow-y-auto mt-2">
                      {doc.original_text}
                    </pre>
                  </TabsContent>
                </Tabs>
              </>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
