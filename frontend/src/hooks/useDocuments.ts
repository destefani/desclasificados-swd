"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchDocuments, fetchDocument, type DocumentFilters } from "@/lib/api";

export function useDocuments(filters: DocumentFilters) {
  return useQuery({
    queryKey: ["documents", filters],
    queryFn: () => fetchDocuments(filters),
  });
}

export function useDocument(id: string | null) {
  return useQuery({
    queryKey: ["document", id],
    queryFn: () => fetchDocument(id!),
    enabled: !!id,
  });
}
