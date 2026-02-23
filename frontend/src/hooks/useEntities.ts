"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchEntities, type EntityFilters } from "@/lib/api";

export function useEntities(filters: EntityFilters) {
  return useQuery({
    queryKey: ["entities", filters],
    queryFn: () => fetchEntities(filters),
  });
}
