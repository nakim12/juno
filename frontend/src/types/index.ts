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

export interface KnowledgeSource {
  chunk_id: string;
  title?: string | null;
  topic?: string | null;
  source?: string | null;
  snippet?: string | null;
}

export interface AnalysisReport {
  session_id: string;
  overview: string;
  per_channel: ChannelAnalysis[];
  structural_risks: Risk[];
  recommendations: Recommendation[];
  validation_suggestions: ValidationStep[];
  knowledge_sources: KnowledgeSource[];
  metadata: { agent_model: string; prompt_version: string; generated_at: string };
}

export interface SampleInfo {
  id: string;
  name: string;
  model_type: string | null;
  n_channels: number;
  data_span_weeks: number | null;
}

export interface EvalRun {
  n_cases: number;
  agent_model: string;
  judge_model: string | null;
  prompt_version: string;
  created_at: string;
  used_judge: number;
  accuracy: number;
  calibration_ece: number;
  // Judged dimensions are null when a run was executed without the LLM judge.
  groundedness: number | null;
  actionability: number | null;
  failure_mode_recall: number;
  hallucination_rate: number | null;
  weighted_total: number | null;
  scenario_breakdown: {
    accuracy_by_channel_count?: Record<string, number>;
    recall_by_failure_mode?: Record<string, number>;
  };
}

export interface EvalDimensionMeta {
  label: string;
  target: string;
  direction: "higher" | "lower";
}

export interface JudgeValidation {
  n_cases: number;
  k_repetitions: number;
  overall_test_retest_kappa: number;
  per_dimension: Record<string, { test_retest_kappa: number; all_identical_rate: number }>;
}

export interface EvaluationSummary {
  available: boolean;
  run?: EvalRun;
  failures?: { total: number; by_category: Record<string, number> };
  judge_validation?: JudgeValidation;
  targets: Record<string, EvalDimensionMeta>;
  note?: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  questionType?: QuestionType;
  sources?: KnowledgeSource[];
}
