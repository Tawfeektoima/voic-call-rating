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

export interface Call {
  id: number;
  employee_id: number;
  campaign_id: number;
  original_filename: string | null;
  status: CallStatus | string;
  transcript: string | null;
  reasoning: string | null;
  evaluation_score: number | null;
  audio_duration: number | null;
  strengths: string[] | null;
  weaknesses: WeaknessItem[] | Record<string, any>[] | null;
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
  agent_talk_time: number | null;
  customer_talk_time: number | null;
  call_summary: string | null;
  outcome?: CallOutcome | null;
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
