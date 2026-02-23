"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DocumentCard } from "@/components/documents/document-card";
import { FilterSidebar } from "@/components/documents/filter-sidebar";
import { DocumentDetail } from "@/components/documents/document-detail";
import { Skeleton } from "@/components/ui/skeleton";
import { useDocuments } from "@/hooks/useDocuments";
import type { DocumentFilters } from "@/lib/api";

export default function ExplorerPage() {
  const [filters, setFilters] = useState<DocumentFilters>({
    page: 1,
    page_size: 25,
    sort: "date_desc",
  });
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const { data, isLoading } = useDocuments(filters);

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-bold mb-6">Document Explorer</h1>

      <div className="flex gap-8">
        <FilterSidebar filters={filters} onChange={setFilters} />

        <div className="flex-1">
          {/* Results header */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">
              {data ? `${data.total.toLocaleString()} documents found` : "Loading..."}
            </p>
            <select
              className="text-sm border rounded px-2 py-1"
              value={filters.sort ?? "date_desc"}
              onChange={(e) => setFilters({ ...filters, sort: e.target.value, page: 1 })}
            >
              <option value="date_desc">Newest first</option>
              <option value="date_asc">Oldest first</option>
              <option value="confidence">Highest confidence</option>
              <option value="pages">Most pages</option>
            </select>
          </div>

          {/* Document grid */}
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-36" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data?.items.map((doc, idx) => (
                <DocumentCard
                  key={doc.id || `doc-${idx}`}
                  doc={doc}
                  onClick={() => setSelectedDoc(doc.id)}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <Button
                variant="outline"
                size="sm"
                disabled={data.page <= 1}
                onClick={() => setFilters({ ...filters, page: data.page - 1 })}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {data.page} of {data.total_pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={data.page >= data.total_pages}
                onClick={() => setFilters({ ...filters, page: data.page + 1 })}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      </div>

      <DocumentDetail docId={selectedDoc} onClose={() => setSelectedDoc(null)} />
    </div>
  );
}
