"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchReport } from "@/lib/api";

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: report, isLoading } = useQuery({
    queryKey: ["report", id],
    queryFn: () => fetchReport(id),
  });

  if (isLoading) {
    return (
      <div className="container max-w-3xl py-8 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!report) return <div className="container py-8">Report not found.</div>;

  const title = report.title as string | undefined;
  const subtitle = report.subtitle as string | undefined;
  const category = report.category as string | undefined;
  const introduction = report.introduction as string | undefined;
  const ragResults = report.rag_results as string | undefined;

  // Rich report (has sections)
  const sections = (report.sections ?? []) as Array<{
    title: string;
    content: Array<{ type: string; text?: string; items?: string[]; doc_id?: string }>;
  }>;
  const hasRichContent = sections.length > 0;

  return (
    <div className="container max-w-3xl py-8">
      <h1 className="text-2xl font-bold mb-2">{title ?? `Report ${id}`}</h1>
      {subtitle && (
        <p className="text-lg text-muted-foreground mb-4">{subtitle}</p>
      )}

      <div className="flex gap-2 mb-6">
        <Badge variant="outline">{id}</Badge>
        {category && <Badge variant="secondary">{category}</Badge>}
      </div>

      {introduction && (
        <p className="text-sm mb-6">{introduction}</p>
      )}

      <Separator className="my-6" />

      {hasRichContent ? (
        sections.map((section, i) => (
          <div key={i} className="mb-8">
            <h2 className="text-xl font-semibold mb-4">{section.title}</h2>
            {section.content.map((block, j) => {
              if (block.type === "paragraph")
                return (
                  <p key={j} className="text-sm mb-3">
                    {block.text}
                  </p>
                );
              if (block.type === "quote")
                return (
                  <blockquote
                    key={j}
                    className="border-l-4 border-blue-500 pl-4 italic text-sm mb-3"
                  >
                    {block.text}
                  </blockquote>
                );
              if (block.type === "list")
                return (
                  <ul key={j} className="list-disc pl-6 text-sm mb-3 space-y-1">
                    {block.items?.map((item, k) => (
                      <li key={k}>{item}</li>
                    ))}
                  </ul>
                );
              if (block.type === "document_reference")
                return (
                  <Card key={j} className="mb-3">
                    <CardContent className="p-3 text-xs">
                      <span className="font-mono font-medium">Doc {block.doc_id}</span>
                      {block.text && (
                        <span className="ml-2 text-muted-foreground">{block.text}</span>
                      )}
                    </CardContent>
                  </Card>
                );
              return (
                <p key={j} className="text-sm mb-3">
                  {block.text}
                </p>
              );
            })}
          </div>
        ))
      ) : (
        // Basic report (from tracker)
        ragResults && (
          <div className="bg-muted p-4 rounded text-sm">{ragResults}</div>
        )
      )}
    </div>
  );
}
