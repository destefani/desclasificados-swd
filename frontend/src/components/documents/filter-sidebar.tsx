"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { DocumentFilters } from "@/lib/api";

const CLASSIFICATIONS = ["TOP SECRET", "SECRET", "CONFIDENTIAL", "UNCLASSIFIED"];
const DOC_TYPES = ["MEMORANDUM", "LETTER", "TELEGRAM", "INTELLIGENCE BRIEF", "REPORT", "CABLE"];

export function FilterSidebar({
  filters,
  onChange,
}: {
  filters: DocumentFilters;
  onChange: (filters: DocumentFilters) => void;
}) {
  return (
    <div className="space-y-6 w-64 shrink-0">
      <div>
        <label className="text-sm font-medium mb-2 block">Search</label>
        <Input
          placeholder="Search documents..."
          value={filters.q ?? ""}
          onChange={(e) => onChange({ ...filters, q: e.target.value || undefined, page: 1 })}
        />
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">Date Range</label>
        <div className="flex gap-2">
          <Input
            type="date"
            value={filters.date_from ?? ""}
            onChange={(e) => onChange({ ...filters, date_from: e.target.value || undefined, page: 1 })}
          />
          <Input
            type="date"
            value={filters.date_to ?? ""}
            onChange={(e) => onChange({ ...filters, date_to: e.target.value || undefined, page: 1 })}
          />
        </div>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">Classification</label>
        <div className="space-y-1">
          {CLASSIFICATIONS.map((c) => (
            <label key={c} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={filters.classification?.includes(c) ?? false}
                onChange={(e) => {
                  const current = filters.classification ?? [];
                  const next = e.target.checked
                    ? [...current, c]
                    : current.filter((x) => x !== c);
                  onChange({ ...filters, classification: next.length ? next : undefined, page: 1 });
                }}
              />
              {c}
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">Document Type</label>
        <div className="space-y-1">
          {DOC_TYPES.map((t) => (
            <label key={t} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={filters.type?.includes(t) ?? false}
                onChange={(e) => {
                  const current = filters.type ?? [];
                  const next = e.target.checked
                    ? [...current, t]
                    : current.filter((x) => x !== t);
                  onChange({ ...filters, type: next.length ? next : undefined, page: 1 });
                }}
              />
              {t}
            </label>
          ))}
        </div>
      </div>

      <Button
        variant="outline"
        className="w-full"
        onClick={() => onChange({ page: 1, page_size: 25, sort: "date_desc" })}
      >
        Clear Filters
      </Button>
    </div>
  );
}
