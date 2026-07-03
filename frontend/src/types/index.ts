export type Confidence = "high" | "medium" | "low";

export type QuestionType =
  | "interpretation"
  | "recommendation"
  | "methodology"
  | "hypothetical"
  | "comparison"
  | "uncertainty"
  | "clarification";

export interface Citation {
  source_type: "mmm_output" | "knowledge_base";
  reference: string;
  snippet?: string | null;
}

export interface ChannelAnalysis {
  channel_name: string;
  interpretation: string;
  confidence: Confidence;
  confidence_reasoning: string;
  citations: Citation[];
}

export interface Risk {
  title: string;
  description: string;
  severity: Confidence;
  citations: Citation[];
}

export interface Recommendation {
  action: string;
  priority: Confidence;
  rationale: string;
  confidence: Confidence;
  dependencies: string[];
  citations: Citation[];
}

export interface ValidationStep {
  step: string;
  rationale: string;
}

export interface AnalysisReport {
  session_id: string;
  overview: string;
  per_channel: ChannelAnalysis[];
  structural_risks: Risk[];
  recommendations: Recommendation[];
  validation_suggestions: ValidationStep[];
  metadata: { agent_model: string; prompt_version: string; generated_at: string };
}

export interface SampleInfo {
  id: string;
  name: string;
  model_type: string | null;
  n_channels: number;
  data_span_weeks: number | null;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  questionType?: QuestionType;
}
