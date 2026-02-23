"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface DocumentTextPanelProps {
  reviewedText: string;
  originalText: string;
}

export function DocumentTextPanel({
  reviewedText,
  originalText,
}: DocumentTextPanelProps) {
  if (!reviewedText && !originalText) return null;

  const defaultTab = reviewedText ? "reviewed" : "original";

  return (
    <Tabs defaultValue={defaultTab}>
      <TabsList>
        {reviewedText && <TabsTrigger value="reviewed">Reviewed Text</TabsTrigger>}
        {originalText && <TabsTrigger value="original">Original Text</TabsTrigger>}
      </TabsList>
      {reviewedText && (
        <TabsContent value="reviewed">
          <pre className="whitespace-pre-wrap text-xs bg-muted p-4 rounded max-h-96 overflow-y-auto mt-2">
            {reviewedText}
          </pre>
        </TabsContent>
      )}
      {originalText && (
        <TabsContent value="original">
          <pre className="whitespace-pre-wrap text-xs bg-muted p-4 rounded max-h-96 overflow-y-auto mt-2">
            {originalText}
          </pre>
        </TabsContent>
      )}
    </Tabs>
  );
}
