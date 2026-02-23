"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { useEntities } from "@/hooks/useEntities";
import type { EntityFilters } from "@/lib/api";

const ENTITY_TYPES = [
  { value: "", label: "All" },
  { value: "person", label: "People" },
  { value: "organization", label: "Organizations" },
  { value: "keyword", label: "Keywords" },
  { value: "place", label: "Places" },
];

const TYPE_COLORS: Record<string, string> = {
  person: "bg-purple-100 text-purple-800",
  organization: "bg-cyan-100 text-cyan-800",
  keyword: "bg-orange-100 text-orange-800",
  place: "bg-green-100 text-green-800",
};

function EntitiesContent() {
  const searchParams = useSearchParams();
  const initialType = searchParams.get("type") ?? "";

  const [filters, setFilters] = useState<EntityFilters>({
    type: initialType || undefined,
    sort: "doc_count_desc",
    page: 1,
    page_size: 50,
  });
  const [search, setSearch] = useState("");
  const { data, isLoading } = useEntities({ ...filters, q: search || undefined });

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-bold mb-6">Entity Explorer</h1>

      {/* Tabs + Search */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <Tabs
          value={filters.type ?? ""}
          onValueChange={(v) => setFilters({ ...filters, type: v || undefined, page: 1 })}
        >
          <TabsList>
            {ENTITY_TYPES.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <Input
          placeholder="Search entities..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
      </div>

      {/* Results count */}
      <p className="text-sm text-muted-foreground mb-4">
        {data ? `${data.total.toLocaleString()} entities` : "Loading..."}
      </p>

      {/* Entity grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.items.map((entity) => (
            <Card key={`${entity.type}-${entity.name}`}>
              <CardContent className="p-4 flex items-center justify-between">
                <div className="min-w-0">
                  <Badge className={TYPE_COLORS[entity.type] ?? ""} variant="secondary">
                    {entity.type}
                  </Badge>
                  <p className="font-medium text-sm mt-1 truncate">{entity.name}</p>
                </div>
                <div className="text-right shrink-0 ml-4">
                  <p className="text-2xl font-bold">{entity.doc_count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">docs</p>
                </div>
              </CardContent>
            </Card>
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
  );
}

export default function EntitiesPage() {
  return (
    <Suspense
      fallback={
        <div className="container py-8 space-y-4">
          <Skeleton className="h-8 w-48" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 9 }).map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        </div>
      }
    >
      <EntitiesContent />
    </Suspense>
  );
}
