/**
 * TypeScript interfaces mirroring the backend Pydantic schemas.
 * Path: app/schemas.py
 */

export enum UserRole {
  ADMIN = "admin",
  MANAGER = "manager",
  QA = "qa",
  AGENT = "agent",
  HR_MANAGER = "hr_manager",
}

export enum CallStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  TRANSCRIBED = "transcribed",
  EVALUATED = "evaluated",
  FAILED = "failed",
}

export type EmotionState = 'calm' | 'stress' | 'agitation';

export interface AgentMastery {
  rapport_building: number;
  emotional_sync: number;
  ownership_trust: number;
  process_clarity: number;
  updated_at: string;
}

export interface EmotionPoint {
  time: number;
  emotion: EmotionState;
  intensity: number;
}

export interface TranscriptSegment {
  id: string;
  speaker: 'agent' | 'customer' | string;
  text: string;
  redactedText?: string;
  start: number;
  end: number;
  emotion: EmotionState;
  hasPII?: boolean;
  needs_review?: boolean;
}

export interface Agent {
  id: number;
  name: string;
  department: string | null;
  employee_code: string;
  avatar?: string;
  tier?: string;
  skills?: Record<string, number>;
  emotion_history?: number[];
  mastery_stats?: AgentMastery;
  created_at: string; // ISO format string
}

export interface Campaign {
  id: number;
  name: string;
  description: string | null;
  type: string;
  status: string;
  kpis: string[] | null;
  color: string;
  evaluation_prompt: string;
  created_at: string;

  // Computed stats
  total_calls: number;
  agent_count: number;
  avg_score: number;
}

export interface WeaknessItem {
  issue: string;
  detail: string;
  deduction: number;
  score?: number;
  max?: number;
}

export interface CallOutcome {
  id: number;
  call_id: number;
  campaign_type: string;
  primary_outcome: string | null;
  outcome_value: number | null;
  follow_up_required: boolean;
  follow_up_date: string | null;
  agent_talk_time: number | null;
  customer_talk_time: number | null;
  talk_ratio: number | null;
  campaign_specific_data: Record<string, any> | null;
  created_at: string;
}

export interface SalesScoreBreakdown {
  opening: number;
  script_compliance: number;
  customer_handling: number;
  conduct: number;
  closing: number;
}

export type ViolationSeverity = "high" | "medium" | "low";
export type PenaltyTier =
  | "Warning" | "1 HR" | "2 HR" | "3 HR"
  | "Half Day" | "Full Day" | "No Show" | "Termination";

export interface CallViolation {
  id: number;
  call_id: number;
  violation_id: string;
  severity: ViolationSeverity;
  occurrence: number;
  penalty_tier: PenaltyTier;
  score_deduction: number;
  hr_flagged: boolean;
  auto_fail: boolean;
  evidence: string | null;
  timestamp_in_call: string | null;
  created_at: string;
}

export interface ViolationSummaryRow {
  employee_id: number;
  employee_name: string;
  total_violations: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  hr_flagged_count: number;
  total_deductions: number;
  last_violation_at: string | null;
}

export interface SalesPenalty {
  violation: string;
  occurrence: number;
  penalty: string;
}

export interface OfferDetail {
  offer_name: string;
  presented: boolean;
  qualifying_questions_asked: boolean;
  branch_followed_correctly: boolean;
  walked_through_enrollment: boolean;
  skip_reason: string;
}

export interface SalesEvalData {
  score: number;
  summary: string;
  reasoning: string;
  strengths: string[];
  areas_for_improvement: string[];
  opening: Record<string, any>;
  qualifying_questions: Record<string, any>;
  offers_presented: string[];
  offers_skipped_incorrectly: string[];
  offer_details: OfferDetail[];
  closing: Record<string, any>;
  penalties: SalesPenalty[];
  score_breakdown?: SalesScoreBreakdown;
}

export interface DeductionItem {
  category: string;
  deduction: number;
  score: number;
  max: number;
}

export interface ViolationItemOut {
  violation_id: string;
  severity: "low" | "medium" | "high" | "critical";
  timestamp?: string;
  evidence?: string;
}

export interface Call {
  id: number;
  employee_id: number;
  campaign_id: number;
  original_filename: string | null;
  status: CallStatus | string;
  transcript: TranscriptSegment[] | null;
  reasoning: string | null;
  evaluation_score: number | null;
  audio_duration: number | null;
  strengths: (string | StrengthItem)[] | null;
  weaknesses: WeaknessItem[] | null;
  error_message: string | null;

  // Review fields
  overridden_score: number | null;
  reviewer_notes: string | null;
  reviewed_at: string | null; // ISO format string

  created_at: string; // ISO format string
  processed_at: string | null; // ISO format string

  emotion_timeline: EmotionPoint[] | null;
  lead_status: string | null;
  is_golden_moment: boolean;
  needs_review?: boolean;
  agent_talk_time: number | null;
  customer_talk_time: number | null;
  call_summary: string | null;
  ai_summary?: string | null;
  deductions?: DeductionItem[] | null;
  outcome?: CallOutcome | null;
  sales_eval_data?: SalesEvalData | null;
  violations?: ViolationItemOut[];
  qa_alarm?: boolean;
  qa_alarm_reason?: string | null;
  qa_alarm_evidence?: string | null;
  override_audits?: ScoreOverrideAudit[] | null;
}

export interface ScoreOverrideAudit {
  id: number;
  call_id: number;
  reviewer_id: number;
  reviewer_name: string;
  old_score: number | null;
  new_score: number;
  reason: string | null;
  created_at: string;
}

export interface EmployeeRanking {
  employee_id: number;
  employee_name: string;
  employee_code: string;
  department: string | null;
  avg_score: number;
  total_calls: number;
}

export interface CommonError {
  category: string;
  occurrence_count: number;
  affected_employees: number;
  avg_deduction: number;
  example_details: string[];
}

export interface ScoreOverview {
  average_score: number;
  total_calls: number;
  pass_rate: number;
}

export interface CallUploadResponse {
  call_id: number;
  status: string;
  message: string;
}

export interface EmployeePerformance {
  avg_score: number;
  total_calls: number;
  rank: string;
  skills_matrix: Record<string, number> | null;
  cumulative_stats?: AgentMastery;
  recent_evaluations: Call[];
}

export interface DashboardKPIs {
  total_calls_today: number;
  avg_qa_score: number;
  queue_depth: number;
  pass_rate: number;
  weekly_trend: { day: string; calls: number; score: number }[];
  campaign_performance: { name: string; score: number; calls: number }[];
}

export interface SystemMetrics {
  gpu_load: number;
  cpu_load: number;
  inference_time: number;
  calls_processing: number;
  queue_depth: number;
  uptime: number;
  gpu_history: { time: string; value: number }[];
  inference_history: { time: string; value: number }[];
}

export interface SystemAlert {
  id: number;
  call_id?: number;
  error_type: string;
  error_message: string;
  severity: "critical" | "warning" | "info";
  resolved: boolean;
  created_at: string;
}
