export type SeverityLevel = "CRITICAL" | "ERROR" | "WARNING" | "INFO" | "UNKNOWN";
export type SLAStatus = "ON_TRACK" | "AT_RISK" | "BREACHED" | "UNKNOWN";
export type PipelineStatus = "HEALTHY" | "RUNNING" | "WARNING" | "FAILED" | "BLOCKED" | "COMPLETED_WITH_VIOLATIONS";
export type IncidentStatus = "OPEN" | "ACKNOWLEDGED" | "INVESTIGATING" | "RESOLVED";

export interface PipelineStage {
  stage: string;
  status: PipelineStatus;
  run_count?: number;
  error?: string;
}

export interface PipelineRun {
  run_id: string;
  hospital_id: string;
  batch_id: string;
  status: PipelineStatus;
  current_stage: string;
  duration_sec: number;
  records_in: number;
  records_out: number;
  dq_violations: number;
  errors: number;
  sla_status: SLAStatus;
  started_at: string;
  updated_at: string;
}

export interface AnomalyEvent {
  anomaly_id: string;
  domain: "VOLUME" | "OPERATIONAL" | "DISTRIBUTION";
  model: string;
  feature: string;
  observed: number;
  expected: number;
  anomaly_score: number;
  severity: SeverityLevel;
  hospital_id: string;
  batch_id: string;
  run_id: string;
  detected_at: string;
}

export interface BusinessRuleViolation {
  rule_id: string;
  category: string;
  severity: SeverityLevel;
  claim_id: string;
  hospital_id: string;
  run_id: string;
  batch_id: string;
  message: string;
  timestamp: string;
  field_values: Record<string, any>;
}

export interface AlertEvent {
  alert_id: string;
  incident_id: string;
  severity: SeverityLevel;
  status: IncidentStatus;
  summary: string;
  alert_type: string;
  hospital_id: string;
  batch_id: string;
  run_id: string;
  stage: string;
  sla_status: SLAStatus;
  detected_at: string;
  age_minutes: number;
  eta?: string;
  deadline?: string;
}

export interface RCAFinding {
  description: string;
  type: "FACT" | "CONFIRMED" | "CORRELATED" | "LIKELY";
  evidence_ids: string[];
}

export interface RCAResponse {
  incident_id: string;
  summary: string;
  findings: RCAFinding[];
  recommended_investigation: string;
  insufficient_evidence: boolean;
}

export interface SLAObservation {
  observation_id: string;
  run_id: string;
  stage: string;
  status: SLAStatus;
  throughput: number;
  eta: string;
  deadline: string;
  margin_minutes: number;
}

export type RagProviderStatus = "READY" | "NOT_CONFIGURED" | "UNAVAILABLE" | "HISTORICAL_ONLY";

export interface RagEvidence {
  type: string;
  source: string;
  value: string;
  timestamp?: string;
  context?: string;
}

export interface RagResponse {
  grounded_explanation: string;
  recommended_action: string;
  sources: string;
  retrieval_method: string;
  response_type: string;
}

export interface RagAnalysis {
  anomaly_id: string;
  user_query: string;
  grounded_explanation: string;
  recommended_action: string;
  sources: string;
  retrieval_method: string;
  response_type: string;
  
  // Context from anomaly metadata
  window_date?: string;
  dataset?: string;
  anomaly_type?: string;
  severity?: string;
}

export interface RagAnalysisSummary {
  anomaly_id: string;
  dataset: string;
  anomaly_type: string;
  severity: string;
  window_date: string;
}
