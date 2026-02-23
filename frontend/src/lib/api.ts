import type {
  DocumentListItem,
  DocumentDetail,
  Entity,
  PaginatedResponse,
  StatsResponse,
  ResearchQuestion,
} from "./types";

const BASE = "/api";

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface DocumentFilters {
  page?: number;
  page_size?: number;
  q?: string;
  date_from?: string;
  date_to?: string;
  classification?: string[];
  type?: string[];
  keywords?: string[];
  sort?: string;
}

export function fetchDocuments(filters: DocumentFilters = {}) {
  const params = new URLSearchParams();
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  if (filters.q) params.set("q", filters.q);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.classification?.length) params.set("classification", filters.classification.join(","));
  if (filters.type?.length) params.set("type", filters.type.join(","));
  if (filters.keywords?.length) params.set("keywords", filters.keywords.join(","));
  if (filters.sort) params.set("sort", filters.sort);
  return fetchJSON<PaginatedResponse<DocumentListItem>>(`${BASE}/documents?${params}`);
}

export function fetchDocument(id: string) {
  return fetchJSON<DocumentDetail>(`${BASE}/documents/${id}`);
}

export interface EntityFilters {
  type?: string;
  q?: string;
  min_docs?: number;
  sort?: string;
  page?: number;
  page_size?: number;
}

export function fetchEntities(filters: EntityFilters = {}) {
  const params = new URLSearchParams();
  if (filters.type) params.set("type", filters.type);
  if (filters.q) params.set("q", filters.q);
  if (filters.min_docs) params.set("min_docs", String(filters.min_docs));
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  return fetchJSON<PaginatedResponse<Entity>>(`${BASE}/entities?${params}`);
}

export function fetchStats() {
  return fetchJSON<StatsResponse>(`${BASE}/stats`);
}

export function fetchReports() {
  return fetchJSON<{ items: ResearchQuestion[] }>(`${BASE}/reports`);
}

export function fetchReport(id: string) {
  return fetchJSON<Record<string, unknown>>(`${BASE}/reports/${id}`);
}

export function pdfUrl(sourceFile: string) {
  return `${BASE}/pdf/${sourceFile}`;
}
