export interface DocumentListItem {
  id: string;
  doc_id: string;
  date: string;
  classification: "TOP SECRET" | "SECRET" | "CONFIDENTIAL" | "UNCLASSIFIED";
  type: string;
  title: string;
  summary: string;
  pages: number;
  confidence: number;
  keywords: string[];
  people_mentioned: string[];
  organizations_mentioned: string[];
  countries_mentioned: string[];
}

export interface DocumentDetail extends DocumentListItem {
  author: string;
  recipients: string[];
  language: string;
  original_text: string;
  reviewed_text: string;
  has_pdf: boolean;
  financial_references: Record<string, unknown>;
  violence_references: Record<string, unknown>;
  torture_references: Record<string, unknown>;
  disappearance_references: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Entity {
  name: string;
  type: "person" | "organization" | "keyword" | "place";
  doc_count: number;
  sample_doc_ids: string[];
}

export interface StatsResponse {
  total_documents: number;
  total_pages: number;
  avg_confidence: number;
  transcription_progress: { completed: number; total: number };
  classification_distribution: Record<string, number>;
  type_distribution: Record<string, number>;
  timeline: Record<string, number>;
  sensitive_content: {
    violence: number;
    torture: number;
    disappearances: number;
    financial: number;
  };
  top_people: { name: string; count: number }[];
  top_organizations: { name: string; count: number }[];
  top_keywords: { name: string; count: number }[];
}

export interface ResearchQuestion {
  id: string;
  question: string;
  date_asked: string;
  category: string;
  status: "unanswered" | "partially_answered" | "answered" | "needs_more_data";
  rag_results: string;
  relevance_score: number;
  related_docs: string[];
}
