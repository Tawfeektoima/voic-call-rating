/**
 * TypeScript interfaces mirroring the backend Pydantic schemas.
 * Path: app/schemas.py
 */

export enum UserRole {
  ADMIN = "admin",
  QA = "qa",
  AGENT = "agent",
  HR_MANAGER = "hr_manager",
  OPS_MANAGER = "ops_manager",
  TEAM_MANAGER = "team_manager",
  TEAM_LEADER = "team_leader",
}

export interface CurrentUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  permissions?: string[];
  avatar: string;
  qa_scope_team_id?: number | null;
  qa_scope_team_name?: string | null;
  qa_scope_campaign_id?: number | null;
  qa_scope_campaign_name?: string | null;
  account_status?: string;
}

export interface RoleDefinition {
  role: string;
  label: string;
  description: string;
  permissions: string[];
  assignable_by_hr: boolean;
}

export interface TeamDirectoryOut {
  id: number;
  name: string;
  campaign_id?: number | null;
  campaign_name?: string | null;
  manager_id?: number | null;
  manager_name?: string | null;
  leader_id?: number | null;
  leader_name?: string | null;
  is_active: boolean;
}

export interface InterviewJob {
  id: number;
  title: string;
  description: string;
  department?: string | null;
  team_id?: number | null;
  campaign_id?: number | null;
  status: string;
  base_questions?: string[] | null;
  scoring_weights?: Record<string, number> | null;
  mcq_enabled: boolean;
  mcq_questions?: Array<Record<string, unknown>> | null;
  created_by_id: number;
  updated_by_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface InterviewCandidate {
  id: number;
  job_id: number;
  full_name: string;
  contact_email: string;
  contact_email_normalized: string;
  phone_number?: string | null;
  phone_normalized?: string | null;
  national_id_last4?: string | null;
  status: string;
  final_score?: number | null;
  global_percentile?: number | null;
  applied_at: string;
  completed_at?: string | null;
  archived_at?: string | null;
  converted_employee_id?: number | null;
  created_by_id?: number | null;
  mcq_score?: number | null;
  mcq_total_questions?: number | null;
  mcq_percentage?: number | null;
  mcq_completed_at?: string | null;
}

export interface InterviewCandidateDocument {
  id: number;
  candidate_id: number;
  document_type: string;
  original_filename: string;
  content_type?: string | null;
  file_size_bytes?: number | null;
  extraction_status: string;
  extraction_error?: string | null;
  uploaded_at: string;
}

export interface InterviewCandidateTimelineEvent {
  id: number;
  candidate_id: number;
  actor_id?: number | null;
  actor_name?: string | null;
  event_type: string;
  from_status?: string | null;
  to_status?: string | null;
  note?: string | null;
  event_payload?: Record<string, any> | null;
  created_at: string;
}

export interface InterviewPortalJob {
  id: number;
  title: string;
  description: string;
  department?: string | null;
  mcq_enabled: boolean;
}

export interface InterviewPortalRegistrationOut {
  status: string;
  candidate_id: number;
  candidate_name: string;
  job_id: number;
  job_title: string;
  session_id: number;
  session_token: string;
  invite_url?: string | null;
  expires_at: string;
  question_count: number;
  duplicate_recent: boolean;
  document_id?: number | null;
  document_extraction_status?: string | null;
}

export interface InterviewAnswer {
  id: number;
  session_id: number;
  candidate_id: number;
  question_id: number;
  transcribed_text?: string | null;
  relevance_score?: number | null;
  fluency_score?: number | null;
  grammar_score?: number | null;
  overall_score?: number | null;
  ai_summary?: string | null;
  status: string;
  started_at?: string | null;
  submitted_at?: string | null;
  evaluated_at?: string | null;
  error_message?: string | null;
}

export interface InterviewCandidateInviteOut {
  candidate_id: number;
  session_id: number;
  session_token: string;
  invite_url?: string | null;
  expires_at: string;
  question_count: number;
}

export interface InterviewPortalSessionOut {
  candidate_id: number;
  candidate_name: string;
  job_id: number;
  job_title: string;
  session_id: number;
  status: string;
  expires_at: string;
  question_count: number;
  mcq_enabled: boolean;
  mcq_completed: boolean;
  mcq_question_count: number;
  question_time_limit_seconds: number;
}

export interface InterviewMcqQuestionOut {
  id: number;
  category: string;
  question: string;
  options: string[];
  type: string;
  correct?: number | null;
  trait_tags?: string[];
}

export interface InterviewMcqPortalOut {
  mcq_enabled: boolean;
  mcq_completed: boolean;
  question_count: number;
  questions: InterviewMcqQuestionOut[];
}

export interface InterviewMcqSubmissionOut {
  id: number;
  session_id: number;
  candidate_id: number;
  job_id: number;
  answers: Record<string, number>;
  question_bank_snapshot: Array<Record<string, unknown>>;
  breakdown?: Record<string, unknown> | null;
  score: number;
  total_questions: number;
  percentage: number;
  completed_at: string;
  created_at: string;
}

export interface InterviewMcqReviewQuestionOut {
  question_id: number;
  question_text: string;
  options: string[];
  user_answer?: number | null;
  correct_answer?: number | null;
  type?: string | null;
  is_correct?: boolean | null;
  trait_tags: string[];
  chosen_trait?: string | null;
}

export interface InterviewMcqReviewOut {
  status: string;
  candidate_id: number;
  candidate_name: string;
  score: number;
  total_questions: number;
  percentage: number;
  completed_at?: string | null;
  iq: InterviewMcqReviewQuestionOut[];
  computer: InterviewMcqReviewQuestionOut[];
  personality: InterviewMcqReviewQuestionOut[];
  personality_breakdown: Record<string, number>;
}

export interface InterviewCandidateReviewAnswer {
  answer_id: number;
  question_id: number;
  question_text: string;
  overall_score?: number | null;
  status: string;
  ai_summary?: string | null;
  transcribed_text?: string | null;
  submitted_at?: string | null;
  evaluated_at?: string | null;
  error_message?: string | null;
}

export interface InterviewCandidateReviewMetrics {
  evaluation_state: string;
  submitted_answers: number;
  evaluated_answers: number;
  average_answer_score?: number | null;
  strongest_answer_score?: number | null;
  weakest_answer_score?: number | null;
}

export interface InterviewCandidateReviewMcqSummary {
  completed: boolean;
  score?: number | null;
  total_questions?: number | null;
  percentage?: number | null;
  completed_at?: string | null;
  objective_breakdown: Record<string, number>;
  personality_breakdown: Record<string, number>;
}

export interface InterviewCandidateRecommendation {
  label: string;
  score?: number | null;
  rationale: string;
  strengths: string[];
  concerns: string[];
}

export interface InterviewCandidateReviewOut {
  status: string;
  candidate: InterviewCandidate;
  interview_metrics: InterviewCandidateReviewMetrics;
  mcq_summary: InterviewCandidateReviewMcqSummary;
  recommendation: InterviewCandidateRecommendation;
  answers: InterviewCandidateReviewAnswer[];
}

export interface InterviewQuestionOut {
  id: number;
  job_id: number;
  session_id?: number | null;
  candidate_id?: number | null;
  question_text: string;
  expected_skills_tags?: Record<string, unknown> | unknown[] | null;
  source: string;
  display_order: number;
  created_at: string;
}

export interface InterviewAnswerSubmitOut {
  answer_id: number;
  session_id: number;
  question_id: number;
  status: string;
  transcribed_text?: string | null;
}

export interface InterviewQuestionStartOut {
  answer_id: number;
  session_id: number;
  question_id: number;
  status: string;
  started_at: string;
  time_limit_seconds: number;
}

export interface InterviewPortalAnswerHistory {
  answer_id: number;
  question_id: number;
  question_text: string;
  status: string;
  overall_score?: number | null;
  ai_summary?: string | null;
  submitted_at?: string | null;
  evaluated_at?: string | null;
}

export interface InterviewPortalMcqResult {
  completed: boolean;
  score?: number | null;
  total_questions?: number | null;
  percentage?: number | null;
  completed_at?: string | null;
  objective_breakdown: Record<string, number>;
  personality_breakdown: Record<string, number>;
}

export interface InterviewPortalDashboardOut {
  candidate_id: number;
  candidate_name: string;
  job_id: number;
  job_title: string;
  session_id: number;
  session_status: string;
  completed_at?: string | null;
  question_count: number;
  submitted_answers: number;
  evaluated_answers: number;
  average_score?: number | null;
  answers: InterviewPortalAnswerHistory[];
  mcq_result: InterviewPortalMcqResult;
}

export interface InterviewCandidateConversionOut {
  candidate_id: number;
  employee_id: number;
  employee_code: string;
  employee_email: string;
  role: string;
}

export interface InterviewCandidateIdentitySummary {
  candidate_id: number;
  full_name: string;
  job_id: number;
  job_title?: string | null;
  department?: string | null;
  status: string;
  phone_last4?: string | null;
  national_id_last4?: string | null;
  contact_email_masked?: string | null;
  converted_employee_id?: number | null;
}

export interface InterviewEmployeeMatch {
  employee_id: number;
  employee_code: string;
  employee_email: string;
  role: string;
  status: string;
}

export interface InterviewCandidateOnboardingReadiness {
  candidate_id: number;
  status: string;
  is_ready: boolean;
  blocking_reasons: string[];
  blocking_categories: string[];
  suggested_employee_code?: string | null;
  suggested_company_email?: string | null;
  candidate_identity_summary: InterviewCandidateIdentitySummary;
  existing_employee_match?: InterviewEmployeeMatch | null;
}

export interface InterviewCandidateBulkActionOut {
  requested: number;
  updated: number;
  skipped: number;
  candidate_ids: number[];
}

export interface InterviewRetentionPurgeOut {
  archived_candidates_matched: number;
  candidates_deleted: number;
  document_rows_deleted: number;
  answer_audio_files_deleted: number;
  document_files_deleted: number;
  dry_run: boolean;
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
  email?: string;
  otp_email?: string;
  role?: string;
  department: string | null;
  employee_code: string;
  avatar?: string;
  tier?: string;
  skills?: Record<string, number>;
  emotion_history?: number[];
  qa_scope_team_id?: number | null;
  qa_scope_team_name?: string | null;
  qa_scope_campaign_id?: number | null;
  qa_scope_campaign_name?: string | null;
  mastery_stats?: AgentMastery;
  created_at: string; // ISO format string
  status?: string;
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

/** Payload for creating a new campaign. */
export interface CampaignCreate {
  name: string;
  description?: string;
  type: string;
  status?: string;
  kpis?: string[];
  color?: string;
  evaluation_prompt: string;
}

/** Payload for updating an existing campaign (all fields optional). */
export type CampaignUpdate = Partial<CampaignCreate>;

export interface WeaknessItem {
  issue: string;
  detail: string;
  deduction: number;
  score?: number;
  max?: number;
}

/** A single strength item returned from the evaluation engine. */
export interface StrengthItem {
  text: string;
  score?: number;
  category?: string;
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

export type ViolationSeverity = "critical" | "high" | "medium" | "low";
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
  qa_approved: boolean;
  qa_approved_by_id: number | null;
  qa_approved_at: string | null;
  qa_approval_note: string | null;
  hr_approved: boolean;
  hr_approved_by_id: number | null;
  hr_approved_at: string | null;
  hr_approval_note: string | null;
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

export interface PendingViolation {
  violation_id: number;
  employee_id: number;
  employee_name: string;
  team_id: number | null;
  team_name: string | null;
  call_id: number;
  violation_type: string;
  severity: ViolationSeverity;
  occurrence: number;
  penalty_tier: PenaltyTier;
  evidence: string | null;
  created_at: string;
}

export interface ViolationStats {
  total_violations_today: number;
  total_violations_this_week: number;
  most_common_violation: string | null;
  most_common_violation_count: number;
  agents_with_hr_flags: number;
  auto_fails_today: number;
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
  severity: ViolationSeverity;
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
  pipeline_latency: number;
  services: { name: string; status: 'operational' | 'degraded' | 'offline'; latency: string }[];
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

export enum RoleNoteVisibility {
  INTERNAL = "INTERNAL",
  RECIPIENT_VISIBLE = "RECIPIENT_VISIBLE",
  AGENT_VISIBLE = "AGENT_VISIBLE",
}

export enum RoleNoteStatus {
  OPEN = "OPEN",
  READ = "READ",
  IN_PROGRESS = "IN_PROGRESS",
  WAITING_REPLY = "WAITING_REPLY",
  RESOLVED = "RESOLVED",
  ARCHIVED = "ARCHIVED",
  DELETED = "DELETED",
}

export enum RoleNoteType {
  GENERAL = "GENERAL",
  COACHING_NOTE = "COACHING_NOTE",
  COACHING_ESCALATION = "COACHING_ESCALATION",
  QA_REVIEW_REQUEST = "QA_REVIEW_REQUEST",
  QA_DISPUTE = "QA_DISPUTE",
  OPS_ESCALATION = "OPS_ESCALATION",
  KPI_ALERT = "KPI_ALERT",
  KPI_FOLLOW_UP = "KPI_FOLLOW_UP",
  TRANSFER_CONTEXT = "TRANSFER_CONTEXT",
  HR_COMPLIANCE = "HR_COMPLIANCE",
  CANDIDATE_REVIEW = "CANDIDATE_REVIEW",
  AI_DETECTION_REVIEW = "AI_DETECTION_REVIEW",
  SYSTEM_ISSUE = "SYSTEM_ISSUE",
}

export enum RoleNotePriority {
  LOW = "LOW",
  NORMAL = "NORMAL",
  HIGH = "HIGH",
  URGENT = "URGENT",
}

export interface RoleNoteRecipient {
  id: number;
  name: string;
  role: string;
  reason?: string | null;
}

export interface KpiCatalogItem {
  key: string;
  label: string;
  unit: "percentage" | "currency" | "count" | "score" | "ratio" | "duration";
  direction: "higher_is_better" | "lower_is_better";
  description: string;
}

export interface RoleNote {
  id: number;
  sender_id: number;
  sender_name: string | null;
  recipient_id: number | null;
  recipient_name: string | null;
  recipient_role: string | null;
  visibility: string | null;
  team_id: number | null;
  team_name_snapshot: string | null;
  campaign_id: number | null;
  campaign_name_snapshot: string | null;
  employee_id: number | null;
  agent_name_snapshot: string | null;
  call_id: number | null;
  parent_note_id: number | null;
  title: string;
  body: string;
  note_type: string;
  priority: string;
  status: string;
  kpi_key: string | null;
  kpi_label: string | null;
  current_value: number | null;
  target_value: number | null;
  period_start: string | null;
  period_end: string | null;
  created_at: string;
  updated_at: string;
  read_at: string | null;
  resolved_at: string | null;
  resolved_by_id: number | null;
  resolved_by_name: string | null;
  deleted_at: string | null;
  deleted_by_id: number | null;
  delete_reason: string | null;
}

export interface RoleNoteThread {
  note: RoleNote;
  replies: RoleNote[];
}

export interface RoleNoteCreatePayload {
  recipient_id?: number;
  recipient_role?: string;
  visibility?: RoleNoteVisibility | string;
  team_id?: number;
  campaign_id?: number;
  employee_id?: number;
  call_id?: number;
  parent_note_id?: number;
  title: string;
  body: string;
  note_type?: RoleNoteType | string;
  priority?: RoleNotePriority | string;
  kpi_key?: string;
  kpi_label?: string;
  current_value?: number;
  target_value?: number;
  period_start?: string;
  period_end?: string;
}

export interface RoleNoteStatusUpdatePayload {
  status: RoleNoteStatus | string;
}

export interface RoleNoteFilters {
  skip?: number;
  limit?: number;
  status?: string;
  note_type?: string;
  priority?: string;
  visibility?: string;
}

export interface RoleNoteRecipientParams {
  note_type: string;
  team_id?: number;
  campaign_id?: number;
  employee_id?: number;
  call_id?: number;
}

export interface TeamLeaderDashboardOut {
  team_count: number;
  agent_count: number;
  average_qa_score: number;
  attendance_rate: number;
  sales: number;
  revenue: number;
  conversion_rate: number;
  pending_notes_count: number;
  pending_transfer_requests_count: number;
}

export interface TeamLeaderTeamRowOut {
  team_id: number;
  team_name: string;
  campaign_id?: number | null;
  campaign_name?: string | null;
  leader_id?: number | null;
  leader_name?: string | null;
  agent_count: number;
  sales: number;
  revenue: number;
  conversion_rate: number;
  average_qa_score: number;
  attendance_rate: number;
}

export interface TeamLeaderAgentRowOut {
  agent_id: number;
  agent_name: string;
  email: string;
  team_id: number;
  team_name: string;
  campaign_id?: number | null;
  campaign_name?: string | null;
  sales: number;
  revenue: number;
  conversion_rate: number;
  qa_score?: number | null;
  attendance_rate?: number | null;
  status: string;
}

export interface TeamLeaderCallRowOut {
  id: number;
  employee_id: number;
  employee_name?: string | null;
  campaign_id: number;
  campaign_name?: string | null;
  status: string;
  evaluation_score?: number | null;
  overridden_score?: number | null;
  audio_duration?: number | null;
  created_at: string;
}

export interface TeamLeaderKpisOut {
  month: string;
  total_sales: number;
  total_revenue: number;
  average_qa_score: number;
  average_conversion_rate: number;
  attendance_rate: number;
}

export interface TeamManagerAlertOut {
  type: string;
  message: string;
  severity: string;
  team_id?: number | null;
  agent_id?: number | null;
}

export interface TeamManagerTeamRowOut {
  team_id: number;
  team_name: string;
  campaign_id?: number | null;
  campaign_name?: string | null;
  leader_id?: number | null;
  leader_name?: string | null;
  agent_count: number;
  sales: number;
  revenue: number;
  conversion_rate: number;
  average_qa_score: number;
  attendance_rate: number;
}

export interface TeamManagerDashboardOut {
  total_teams: number;
  total_agents: number;
  total_sales: number;
  total_revenue: number;
  average_conversion_rate: number;
  average_qa_score: number;
  attendance_rate: number;
  teams: TeamManagerTeamRowOut[];
  alerts: TeamManagerAlertOut[];
}

export interface TeamManagerAgentRowOut {
  agent_id: number;
  agent_name: string;
  email: string;
  team_id: number;
  team_name: string;
  campaign_id?: number | null;
  campaign_name?: string | null;
  sales: number;
  revenue: number;
  conversion_rate: number;
  qa_score?: number | null;
  attendance_rate?: number | null;
  status: string;
}

export interface TeamManagerSalesRow {
  team_id: number;
  team_name: string;
  sales: number;
  total_calls: number;
}

export interface TeamManagerSalesReportOut {
  teams: TeamManagerSalesRow[];
  total_sales: number;
}

export interface TeamManagerRevenueRow {
  team_id: number;
  team_name: string;
  revenue: number;
}

export interface TeamManagerRevenueReportOut {
  teams: TeamManagerRevenueRow[];
  total_revenue: number;
}

export interface TeamManagerConversionRow {
  team_id: number;
  team_name: string;
  sales: number;
  total_calls: number;
  conversion_rate: number;
}

export interface TeamManagerConversionReportOut {
  teams: TeamManagerConversionRow[];
  average_conversion_rate: number;
}

export interface TeamManagerAttendanceRow {
  agent_id: number;
  agent_name: string;
  attendance_date: string;
  status: string;
  scheduled_minutes?: number | null;
  worked_minutes?: number | null;
  late_minutes?: number | null;
}

export interface TeamManagerAttendanceReportOut {
  records: TeamManagerAttendanceRow[];
  attendance_rate: number;
}

export interface TeamManagerKpisOut {
  month: string;
  period_start?: string | null;
  period_end?: string | null;
  period_label?: string | null;
  total_sales: number;
  total_revenue: number;
  average_qa_score: number;
  average_conversion_rate: number;
  attendance_rate: number;
}

export interface AgentTransferRequestOut {
  id: number;
  agent_id: number;
  agent_name?: string | null;
  from_team_id: number;
  from_team_name?: string | null;
  to_team_id?: number | null;
  to_team_name?: string | null;
  requested_by_id: number;
  requested_by_name?: string | null;
  reviewed_by_id?: number | null;
  reviewed_by_name?: string | null;
  status: string;
  reason: string;
  review_note?: string | null;
  created_at: string;
  reviewed_at?: string | null;
}

export interface AgentTransferRequestCreate {
  agent_id: number;
  from_team_id: number;
  to_team_id?: number | null;
  reason: string;
}
