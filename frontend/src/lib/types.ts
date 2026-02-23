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

export interface FinancialReferences {
  has_financial_content: boolean;
  amounts: { value: string; normalized_usd: number | null; context: string }[];
  financial_actors: string[];
  purposes: string[];
}

export interface ViolenceReferences {
  has_violence_content: boolean;
  incident_types: string[];
  victims: string[];
  perpetrators: string[];
}

export interface TortureReferences {
  has_torture_content: boolean;
  detention_centers: string[];
  victims: string[];
  perpetrators: string[];
  methods_mentioned: string[];
}

export interface DisappearanceReferences {
  has_disappearance_content: boolean;
  victims: string[];
  perpetrators: string[];
  locations: string[];
  dates_mentioned: string[];
}

export interface OrganizationDetail {
  name: string;
  type: string;
  country: string;
}

export interface DocumentDetail extends DocumentListItem {
  source_file: string;
  author: string;
  recipients: string[];
  language: string;
  original_text: string;
  reviewed_text: string;
  has_pdf: boolean;
  concerns: string[];
  cities_mentioned: string[];
  has_financial_content: boolean;
  has_violence_content: boolean;
  has_torture_content: boolean;
  has_disappearance_content: boolean;
  financial_references: FinancialReferences;
  violence_references: ViolenceReferences;
  torture_references: TortureReferences;
  disappearance_references: DisappearanceReferences;
  date_range: { start_date: string; end_date: string; is_approximate: boolean } | null;
  declassification_date: string;
  document_description: string;
  archive_location: string;
  observations: string;
  other_places: string[];
  organizations_detail: OrganizationDetail[];
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
