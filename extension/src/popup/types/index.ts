export interface ModuleResult {
  score: number;
  max_score: number;
  status: "completed" | "skipped" | "error";
  details: string;
  sub_flags: string[];
}

export interface ModuleBreakdown {
  address_lookup: ModuleResult;
  price_anomaly: ModuleResult;
  nlp_analysis: ModuleResult;
  image_analysis: ModuleResult;
  video_presence: ModuleResult;
}

export interface Flag {
  severity: "high" | "moderate" | "low" | "info";
  category: string;
  message: string;
  evidence_text?: string;
}

export interface Evidence {
  source: string;
  label: string;
  value: string;
  url?: string;
}

export interface ExtractedData {
  rent: number | null;
  zip_code: string | null;
  address: string | null;
  neighborhood: string | null;
  bedrooms: number | null;
  bathrooms: number | null;
  contact_info: string[];
  suspicious_phrases: string[];
  payment_methods: string[];
}

export interface AnalysisResult {
  composite_score: number;
  risk_level: "low" | "moderate" | "high";
  risk_color: "green" | "yellow" | "red";
  modules: ModuleBreakdown;
  flags: Flag[];
  evidence: Evidence[];
  extracted_data: ExtractedData;
  disclaimer: string;
  processing_time_ms: number;
  api_errors: string[];
}
