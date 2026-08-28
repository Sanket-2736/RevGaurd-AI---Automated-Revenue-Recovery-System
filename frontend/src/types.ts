export interface CategoryStat {
  case_count: number;
  recovered_count: number;
  total_at_risk: number;
  total_recovered: number;
  recovery_rate: number;
}

export interface MetricsResponse {
  total_at_risk: number;
  total_recovered: number;
  recovery_rate: number;
  by_category: Record<string, CategoryStat>;
  human_escalations: number;
  guardrail_blocks: number;
}

export interface RecoveryCase {
  id: number;
  case_type: string;
  status: string;
  amount_at_risk: number;
  root_cause?: string | null;
  recommended_action?: string | null;
  ai_confidence?: number | null;
  customer_name: string;
  customer_email: string;
  created_at?: string | null;
  resolved_at?: string | null;
}

export interface GuardrailEvent {
  id: number;
  case_id: number;
  rule_triggered: string;
  decision: string;
  reason: string;
  created_at?: string | null;
}

export interface SSEStreamEvent {
  case_id?: number;
  case_type?: string;
  action?: string;
  approved?: boolean;
  amount_recovered?: number;
  route?: string;
  root_cause?: string;
  reason?: string;
  confidence?: number;
  requires_human_approval?: boolean;
  batch_id?: string;
  is_finished?: boolean;
  progress_pct?: number;
  error?: string;
}

export interface BatchRunResponse {
  batch_id: string | null;
  total_enqueued: number;
  mode?: string;
  message: string;
}
