import axios, { AxiosError } from 'axios';
import { 
  Agent, 
  Campaign, 
  Call, 
  CallUploadResponse, 
  EmployeeRanking, 
  CommonError,
  CurrentUser,
  SystemMetrics,
  SystemAlert,
  RoleNote,
  RoleNoteCreatePayload,
  RoleNoteFilters,
  RoleNoteRecipient,
  RoleNoteRecipientParams,
  RoleNoteStatusUpdatePayload,
  RoleNoteThread,
  RoleDefinition,
  ViolationStats,
  PendingViolation,
  TeamDirectoryOut,
  TeamLeaderAgentRowOut,
  TeamLeaderCallRowOut,
  TeamLeaderDashboardOut,
  TeamLeaderKpisOut,
  TeamLeaderTeamRowOut,
  AgentTransferRequestCreate,
  AgentTransferRequestOut,
  TeamManagerAgentRowOut,
  TeamManagerAttendanceReportOut,
  TeamManagerConversionReportOut,
  TeamManagerDashboardOut,
  TeamManagerKpisOut,
  TeamManagerRevenueReportOut,
  TeamManagerSalesReportOut,
  TeamManagerTeamRowOut,
  InterviewAnswer,
  InterviewAnswerSubmitOut,
  InterviewCandidate,
  InterviewCandidateBulkActionOut,
  InterviewCandidateReviewOut,
  InterviewCandidateConversionOut,
  InterviewCandidateDocument,
  InterviewCandidateInviteOut,
  InterviewCandidateOnboardingReadiness,
  InterviewCandidateTimelineEvent,
  InterviewJob,
  InterviewMcqPortalOut,
  InterviewMcqReviewOut,
  InterviewMcqQuestionOut,
  InterviewMcqSubmissionOut,
  InterviewPortalDashboardOut,
  InterviewPortalJob,
  InterviewPortalRegistrationOut,
  InterviewPortalSessionOut,
  InterviewQuestionStartOut,
  InterviewQuestionOut,
  InterviewRetentionPurgeOut,
} from './types';
import { getApiBaseUrl } from './network';

// Create a centralized Axios instance
const api = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

export function isSafeDisplayMessage(message: string): boolean {
  if (typeof message !== 'string') return false;

  // Check for forbidden keywords/sensitive keys using token/key-aware regexes with lookarounds
  const unsafeRegex = /(?<![a-zA-Z])(sid|jti|device_id_hash|device_id|device hash|bearer)(?![a-zA-Z])/i;
  if (unsafeRegex.test(message)) {
    return false;
  }

  // Check for JWT-like strings: three dot-separated base64url segments
  const jwtRegex = /[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/;
  if (jwtRegex.test(message)) {
    return false;
  }

  // Check for long hex strings (32+ hex chars)
  const longHexRegex = /[a-fA-F0-9]{32,}/;
  if (longHexRegex.test(message)) {
    return false;
  }

  return true;
}

export function getSafeSecurityLogoutReason(error: unknown): string {
  const fallback = 'Your access is no longer valid. Please sign in again.';
  return getApiErrorMessage(error, fallback);
}

export const getApiErrorMessage = (error: unknown, fallback: string): string => {
  if (!axios.isAxiosError(error)) return fallback;

  const detail = (error.response?.data as any)?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return isSafeDisplayMessage(detail) ? detail : fallback;
  }

  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    if (typeof detail.message === 'string' && detail.message.trim()) {
      return isSafeDisplayMessage(detail.message) ? detail.message : fallback;
    }
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === 'string' && first.trim()) {
      return isSafeDisplayMessage(first) ? first : fallback;
    }
    if (first && typeof first === 'object' && typeof first.msg === 'string' && first.msg.trim()) {
      return isSafeDisplayMessage(first.msg) ? first.msg : fallback;
    }
  }

  if (typeof (error.response?.data as any)?.message === 'string') {
    const msg = (error.response?.data as any).message;
    return isSafeDisplayMessage(msg) ? msg : fallback;
  }

  return fallback;
};

// Request interceptor to add Authorization header
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export function isSecurityAuthError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false;
  const status = error.response?.status;
  if (status !== 401 && status !== 403) return false;

  // Do not treat login or password reset failures as forced logout errors.
  const url = error.config?.url || '';
  if (url.includes('/api/auth/login') || url.includes('/api/auth/password-reset')) {
    return false;
  }

  if (status === 401) {
    return true;
  }

  if (status === 403) {
    const detail = (error.response?.data as any)?.detail;
    let detailText = '';

    if (typeof detail === 'string') {
      detailText = detail;
    } else if (detail && typeof detail === 'object') {
      if (typeof detail.message === 'string') {
        detailText = detail.message;
      } else if (typeof detail.code === 'string') {
        detailText = detail.code;
      }
    }

    if (detailText) {
      const lowercaseDetail = detailText.toLowerCase();

      // Ignore administrative/role permission failures (e.g., managing shifts or admin actions)
      if (
        lowercaseDetail.includes('manage shifts') ||
        lowercaseDetail.includes('only admins') ||
        lowercaseDetail.includes('permission to view this') ||
        lowercaseDetail.includes('permission to access this')
      ) {
        return false;
      }

      const securityPhrases = [
        'session',
        'revoked',
        'expired',
        'device',
        'trusted',
        'shift',
        'access is no longer valid',
        'outside allowed working hours'
      ];
      return securityPhrases.some(phrase => lowercaseDetail.includes(phrase));
    }
    return false;
  }

  return false;
}

let securityErrorCallback: ((reason: string) => void) | null = null;

export function registerSecurityErrorCallback(cb: (reason: string) => void) {
  securityErrorCallback = cb;
}

// Response interceptor for global error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const detail = (error.response?.data as any)?.detail;
    const hasInterviewPortalToken = Boolean((error.config?.headers as any)?.['X-Interview-Session-Token']);
    const isPublicInterviewPortal = typeof window !== 'undefined' && window.location.pathname === '/interview-portal';

    if (!hasInterviewPortalToken && !isPublicInterviewPortal && isSecurityAuthError(error)) {
      console.warn('Security auth error - triggering forced logout');
      const reason = getSafeSecurityLogoutReason(error);
      
      if (securityErrorCallback) {
        securityErrorCallback(reason);
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export const getEmployees = async (): Promise<Agent[]> => {
  const response = await api.get<Agent[]>('/api/admin/employees');
  return response.data;
};

export const getEmployeesPaginated = async (params: {
  skip?: number;
  limit?: number;
  role?: string;
  status?: string;
  search?: string;
}): Promise<{ items: Agent[]; total: number }> => {
  const response = await api.get<Agent[]>('/api/admin/employees', { params });
  const total = parseInt(response.headers['x-total-count'] || '0', 10);
  return { items: response.data, total };
};

export const updateEmployee = async (id: number, data: { role?: string; status?: string }): Promise<Agent> => {
  const response = await api.put<Agent>(`/api/admin/employees/${id}`, data);
  return response.data;
};

export const getTeamsDirectory = async (params?: { active_only?: boolean }): Promise<TeamDirectoryOut[]> => {
  const response = await api.get<TeamDirectoryOut[]>('/api/admin/teams', { params });
  return response.data;
};

export const assignTeamLeader = async (teamId: number, leaderId?: number | null): Promise<TeamDirectoryOut> => {
  const response = await api.put<TeamDirectoryOut>(`/api/admin/teams/${teamId}/leader`, { leader_id: leaderId ?? null });
  return response.data;
};

export const assignQaScope = async (employeeId: number, payload: { team_id?: number | null; campaign_id?: number | null }): Promise<Agent> => {
  const response = await api.put<Agent>(`/api/admin/employees/${employeeId}/qa-scope`, payload);
  return response.data;
};

export const getInterviewJobs = async (params?: { status?: string; team_id?: number; campaign_id?: number }): Promise<InterviewJob[]> => {
  const response = await api.get<InterviewJob[]>('/api/hr/interviews/jobs', { params });
  return response.data;
};

export const createInterviewJob = async (payload: {
  title: string;
  description: string;
  department?: string;
  team_id?: number | null;
  campaign_id?: number | null;
  status?: string;
  base_questions?: string[];
}): Promise<InterviewJob> => {
  const response = await api.post<InterviewJob>('/api/hr/interviews/jobs', payload);
  return response.data;
};

export const updateInterviewJob = async (
  jobId: number,
  payload: Partial<{
    title: string;
    description: string;
    department: string;
    team_id: number | null;
    campaign_id: number | null;
    status: string;
    base_questions: string[];
  }>
): Promise<InterviewJob> => {
  const response = await api.put<InterviewJob>(`/api/hr/interviews/jobs/${jobId}`, payload);
  return response.data;
};

export const getInterviewCandidates = async (params?: { job_id?: number; status?: string }): Promise<InterviewCandidate[]> => {
  const response = await api.get<InterviewCandidate[]>('/api/hr/interviews/candidates', { params });
  return response.data;
};

export const createInterviewCandidate = async (payload: {
  job_id: number;
  full_name: string;
  contact_email: string;
  phone_number?: string;
  national_id?: string;
}): Promise<InterviewCandidate> => {
  const response = await api.post<InterviewCandidate>('/api/hr/interviews/candidates', payload);
  return response.data;
};

export const inviteInterviewCandidate = async (
  candidateId: number,
  payload?: { expires_in_hours?: number; questions?: string[] }
): Promise<InterviewCandidateInviteOut> => {
  const response = await api.post<InterviewCandidateInviteOut>(`/api/hr/interviews/candidates/${candidateId}/invite`, payload ?? {});
  return response.data;
};

export const rejectInterviewCandidate = async (candidateId: number, note?: string, sendEmail?: boolean): Promise<InterviewCandidate> => {
  const response = await api.post<InterviewCandidate>(`/api/hr/interviews/candidates/${candidateId}/reject`, {
    note: note ?? null,
    send_email: sendEmail ?? false,
  });
  return response.data;
};

export const archiveInterviewCandidate = async (candidateId: number, note?: string, sendEmail?: boolean): Promise<InterviewCandidate> => {
  const response = await api.post<InterviewCandidate>(`/api/hr/interviews/candidates/${candidateId}/archive`, {
    note: note ?? null,
    send_email: sendEmail ?? false,
  });
  return response.data;
};

export const shortlistInterviewCandidate = async (
  candidateId: number,
  note?: string,
  sendEmail?: boolean
): Promise<InterviewCandidate> => {
  const response = await api.post<InterviewCandidate>(`/api/hr/interviews/candidates/${candidateId}/shortlist`, {
    note: note ?? null,
    send_email: sendEmail ?? false,
  });
  return response.data;
};

export const acceptInterviewCandidate = async (
  candidateId: number,
  note?: string,
  sendEmail?: boolean
): Promise<InterviewCandidate> => {
  const response = await api.post<InterviewCandidate>(`/api/hr/interviews/candidates/${candidateId}/accept`, {
    note: note ?? null,
    send_email: sendEmail ?? false,
  });
  return response.data;
};

export const restoreInterviewCandidate = async (
  candidateId: number,
  note?: string
): Promise<InterviewCandidate> => {
  const response = await api.post<InterviewCandidate>(`/api/hr/interviews/candidates/${candidateId}/restore`, {
    note: note ?? null,
  });
  return response.data;
};

export const getInterviewCandidateOnboardingReadiness = async (
  candidateId: number,
): Promise<InterviewCandidateOnboardingReadiness> => {
  const response = await api.get<InterviewCandidateOnboardingReadiness>(`/api/hr/interviews/candidates/${candidateId}/onboarding-readiness`);
  return response.data;
};

export const bulkArchiveInterviewCandidates = async (
  candidateIds: number[],
  note?: string,
): Promise<InterviewCandidateBulkActionOut> => {
  const response = await api.post<InterviewCandidateBulkActionOut>('/api/hr/interviews/candidates/bulk-archive', {
    candidate_ids: candidateIds,
    note: note ?? null,
  });
  return response.data;
};

export const convertInterviewCandidate = async (
  candidateId: number,
  payload: {
    employee_code: string;
    role?: string;
    department?: string;
    otp_email?: string;
    password?: string;
    phone_number?: string;
  }
): Promise<InterviewCandidateConversionOut> => {
  const response = await api.post<InterviewCandidateConversionOut>(`/api/hr/interviews/candidates/${candidateId}/convert`, payload);
  return response.data;
};

export const uploadInterviewCandidateDocument = async (
  candidateId: number,
  formData: FormData
): Promise<InterviewCandidateDocument> => {
  const response = await api.post<InterviewCandidateDocument>(`/api/hr/interviews/candidates/${candidateId}/documents`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getInterviewCandidateDocuments = async (candidateId: number): Promise<InterviewCandidateDocument[]> => {
  const response = await api.get<InterviewCandidateDocument[]>(`/api/hr/interviews/candidates/${candidateId}/documents`);
  return response.data;
};

export const getInterviewCandidateAnswers = async (candidateId: number): Promise<InterviewAnswer[]> => {
  const response = await api.get<InterviewAnswer[]>(`/api/hr/interviews/candidates/${candidateId}/answers`);
  return response.data;
};

export const getInterviewCandidateReview = async (candidateId: number): Promise<InterviewCandidateReviewOut> => {
  const response = await api.get<InterviewCandidateReviewOut>(`/api/hr/interviews/candidates/${candidateId}/review`);
  return response.data;
};

export const getInterviewCandidateTimeline = async (candidateId: number): Promise<InterviewCandidateTimelineEvent[]> => {
  const response = await api.get<InterviewCandidateTimelineEvent[]>(`/api/hr/interviews/candidates/${candidateId}/timeline`);
  return response.data;
};

export const exportInterviewCandidatesCsv = async (params?: {
  job_id?: number;
  status?: string;
  include_pii?: boolean;
}): Promise<Blob> => {
  const response = await api.get('/api/hr/interviews/export/candidates.csv', {
    params,
    responseType: 'blob',
  });
  return response.data;
};

export const purgeArchivedInterviewCandidates = async (payload: {
  older_than_days: number;
  dry_run: boolean;
}): Promise<InterviewRetentionPurgeOut> => {
  const response = await api.post<InterviewRetentionPurgeOut>('/api/hr/interviews/retention/purge-archived', payload);
  return response.data;
};

export const getInterviewPortalSession = async (sessionToken: string): Promise<InterviewPortalSessionOut> => {
  const response = await api.get<InterviewPortalSessionOut>('/api/interview-portal/session', {
    headers: { 'X-Interview-Session-Token': sessionToken },
  });
  return response.data;
};

export const getInterviewPortalDashboard = async (sessionToken: string): Promise<InterviewPortalDashboardOut> => {
  const response = await api.get<InterviewPortalDashboardOut>('/api/interview-portal/dashboard', {
    headers: { 'X-Interview-Session-Token': sessionToken },
  });
  return response.data;
};

export const getInterviewPortalJobs = async (): Promise<InterviewPortalJob[]> => {
  const response = await api.get<InterviewPortalJob[]>('/api/interview-portal/jobs');
  return response.data;
};

export const registerInterviewPortalCandidate = async (formData: FormData): Promise<InterviewPortalRegistrationOut> => {
  const response = await api.post<InterviewPortalRegistrationOut>('/api/interview-portal/register', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getInterviewPortalQuestions = async (sessionToken: string): Promise<InterviewQuestionOut[]> => {
  const response = await api.get<InterviewQuestionOut[]>('/api/interview-portal/questions', {
    headers: { 'X-Interview-Session-Token': sessionToken },
  });
  return response.data;
};

export const startInterviewPortalQuestion = async (
  sessionToken: string,
  questionId: number,
): Promise<InterviewQuestionStartOut> => {
  const response = await api.post<InterviewQuestionStartOut>(
    `/api/interview-portal/questions/${questionId}/start`,
    {},
    { headers: { 'X-Interview-Session-Token': sessionToken } },
  );
  return response.data;
};

export const getInterviewPortalMcq = async (sessionToken: string): Promise<InterviewMcqPortalOut> => {
  const response = await api.get<InterviewMcqPortalOut>('/api/interview-portal/mcq', {
    headers: { 'X-Interview-Session-Token': sessionToken },
  });
  return response.data;
};

export const submitInterviewPortalAnswer = async (
  sessionToken: string,
  questionId: number,
  formData: FormData,
): Promise<InterviewAnswerSubmitOut> => {
  const response = await api.post<InterviewAnswerSubmitOut>(
    `/api/interview-portal/questions/${questionId}/answer`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
        'X-Interview-Session-Token': sessionToken,
      },
    },
  );
  return response.data;
};

export const submitInterviewPortalMcq = async (
  sessionToken: string,
  answers: Record<string, number>,
): Promise<InterviewMcqSubmissionOut> => {
  const response = await api.post<InterviewMcqSubmissionOut>(
    '/api/interview-portal/mcq',
    { answers },
    { headers: { 'X-Interview-Session-Token': sessionToken } },
  );
  return response.data;
};

export const completeInterviewPortalSession = async (
  sessionToken: string,
): Promise<{ status: string; session_id: number; candidate_status?: string }> => {
  const response = await api.post(
    '/api/interview-portal/complete',
    {},
    { headers: { 'X-Interview-Session-Token': sessionToken } },
  );
  return response.data;
};

export const getDefaultInterviewMcqBank = async (): Promise<InterviewMcqQuestionOut[]> => {
  const response = await api.get<InterviewMcqQuestionOut[]>('/api/hr/interviews/mcq-bank/default');
  return response.data;
};

export const getInterviewCandidateMcqSubmission = async (
  candidateId: number,
): Promise<InterviewMcqSubmissionOut | null> => {
  const response = await api.get<InterviewMcqSubmissionOut | null>(`/api/hr/interviews/candidates/${candidateId}/mcq`);
  return response.data;
};

export const getInterviewCandidateMcqResults = async (
  candidateId: number,
): Promise<InterviewMcqReviewOut> => {
  const response = await api.get<InterviewMcqReviewOut>(`/api/hr/interviews/candidates/${candidateId}/mcq-results`);
  return response.data;
};

export const approveHrViolation = async (violationId: number, note?: string): Promise<void> => {
  await api.patch(`/api/hr/violations/${violationId}/approve`, { note: note ?? null });
};

export const approveQaViolation = async (violationId: number, note?: string): Promise<void> => {
  await api.patch(`/api/hr/violations/${violationId}/qa-approve`, { note: note ?? null });
};


export const getCampaigns = async (): Promise<Campaign[]> => {
  const response = await api.get<Campaign[]>('/api/admin/campaigns');
  return response.data;
};

export const createCampaign = async (data: any): Promise<Campaign> => {
  const response = await api.post<Campaign>('/api/admin/campaigns', data);
  return response.data;
};

export const updateCampaign = async (id: number, data: any): Promise<Campaign> => {
  const response = await api.put<Campaign>(`/api/admin/campaigns/${id}`, data);
  return response.data;
};

export const deleteCampaign = async (id: number): Promise<void> => {
  await api.delete(`/api/admin/campaigns/${id}`);
};

/**
 * Audio / Call API Functions
 */

export const getCallDetails = async (id: number): Promise<Call> => {
  const response = await api.get<Call>(`/api/audio/${id}`);
  return response.data;
};

export const uploadAudio = async (formData: FormData): Promise<CallUploadResponse> => {
  const response = await api.post<CallUploadResponse>('/api/audio/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export interface BulkCallItemResult {
  filename: string;
  success: boolean;
  call_id?: number;
  error?: string;
}

export interface BulkCallUploadResponse {
  results: BulkCallItemResult[];
  success_count: number;
  failed_count: number;
  message: string;
}

export const bulkUploadAudio = async (formData: FormData): Promise<BulkCallUploadResponse> => {
  const response = await api.post<BulkCallUploadResponse>('/api/audio/bulk-upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Analytics API Functions
 */

export const searchCalls = async (params: {
  employee_code?: string;
  campaign_id?: number;
  date_from?: string;
  date_to?: string;
}): Promise<Call[]> => {
  const response = await api.get<Call[]>('/api/analytics/search', { params });
  return response.data;
};

export const getRanking = async (params?: { top?: number; bottom?: number }): Promise<EmployeeRanking[]> => {
  const response = await api.get<EmployeeRanking[]>('/api/analytics/ranking', { params });
  return response.data;
};

export const getCommonErrors = async (limit: number = 10): Promise<CommonError[]> => {
  const response = await api.get<CommonError[]>('/api/analytics/common-errors', { params: { limit } });
  return response.data;
};

export const getAgentDetails = async (id: number): Promise<Agent> => {
  const response = await api.get<Agent>(`/api/analytics/agents/${id}`);
  return response.data;
};

export const getLeads = async (): Promise<Call[]> => {
  const response = await api.get<Call[]>('/api/analytics/leads');
  return response.data;
};

export const updateLeadStatus = async (callId: number, status: string): Promise<Call> => {
  const response = await api.patch<Call>(`/api/audio/${callId}/lead-status`, null, {
    params: { status }
  });
  return response.data;
};

export const getGoldenMoments = async (): Promise<Call[]> => {
  const response = await api.get<Call[]>('/api/analytics/golden-moments');
  return response.data;
};

export const getSystemMetrics = async (): Promise<SystemMetrics> => {
  const response = await api.get<SystemMetrics>('/api/system/metrics');
  return response.data;
};

export const getViolationStats = async (params?: { team_id?: number }): Promise<ViolationStats> => {
  const response = await api.get<ViolationStats>('/api/hr/violations/stats', { params });
  return response.data;
};

export const getPendingHrViolations = async (params?: { team_id?: number }): Promise<PendingViolation[]> => {
  const response = await api.get<PendingViolation[]>('/api/hr/violations/pending', { params });
  return response.data;
};

export const getPendingQaViolations = async (params?: { team_id?: number }): Promise<PendingViolation[]> => {
  const response = await api.get<PendingViolation[]>('/api/hr/violations/qa-pending', { params });
  return response.data;
};

export const getSystemAlerts = async (): Promise<SystemAlert[]> => {
  const response = await api.get<SystemAlert[]>('/api/system/alerts');
  return response.data;
};

export const resolveAlert = async (id: number): Promise<SystemAlert> => {
  const response = await api.patch<SystemAlert>(`/api/system/alerts/${id}/resolve`);
  return response.data;
};

export const getCurrentUser = async (): Promise<CurrentUser> => {
  const response = await api.get<CurrentUser>('/api/auth/me');
  return response.data;
};

export const getApprovedRoles = async (): Promise<RoleDefinition[]> => {
  const response = await api.get<RoleDefinition[]>('/api/auth/roles');
  return response.data;
};

export const getNotesInbox = async (params?: RoleNoteFilters): Promise<RoleNote[]> => {
  const response = await api.get<RoleNote[]>('/api/notes/inbox', { params });
  return response.data;
};

export const getSentNotes = async (params?: RoleNoteFilters): Promise<RoleNote[]> => {
  const response = await api.get<RoleNote[]>('/api/notes/sent', { params });
  return response.data;
};

export const getNoteThread = async (noteId: number): Promise<RoleNoteThread> => {
  const response = await api.get<RoleNoteThread>(`/api/notes/${noteId}`);
  return response.data;
};

export const getNoteRecipients = async (params: RoleNoteRecipientParams): Promise<RoleNoteRecipient[]> => {
  const response = await api.get<RoleNoteRecipient[]>('/api/notes/recipients', { params });
  return response.data;
};

export const createNote = async (payload: RoleNoteCreatePayload): Promise<RoleNote> => {
  const response = await api.post<RoleNote>('/api/notes', payload);
  return response.data;
};

export const replyToNote = async (noteId: number, payload: RoleNoteCreatePayload): Promise<RoleNote> => {
  const response = await api.post<RoleNote>(`/api/notes/${noteId}/reply`, payload);
  return response.data;
};

export const markNoteRead = async (noteId: number): Promise<RoleNote> => {
  const response = await api.patch<RoleNote>(`/api/notes/${noteId}/read`);
  return response.data;
};

export const updateNoteStatus = async (noteId: number, payload: RoleNoteStatusUpdatePayload): Promise<RoleNote> => {
  const response = await api.patch<RoleNote>(`/api/notes/${noteId}/status`, payload);
  return response.data;
};

export const resolveNote = async (noteId: number): Promise<RoleNote> => {
  const response = await api.patch<RoleNote>(`/api/notes/${noteId}/resolve`);
  return response.data;
};

export const archiveNote = async (noteId: number): Promise<RoleNote> => {
  const response = await api.patch<RoleNote>(`/api/notes/${noteId}/archive`);
  return response.data;
};

export const deleteNote = async (noteId: number, reason: string): Promise<RoleNote> => {
  const response = await api.delete<RoleNote>(`/api/notes/${noteId}`, { params: { reason } });
  return response.data;
};

export const getTeamLeaderDashboard = async (): Promise<TeamLeaderDashboardOut> => {
  const response = await api.get<TeamLeaderDashboardOut>('/api/team-leader/dashboard');
  return response.data;
};

export const getTeamLeaderTeams = async (): Promise<TeamLeaderTeamRowOut[]> => {
  const response = await api.get<TeamLeaderTeamRowOut[]>('/api/team-leader/teams');
  return response.data;
};

export const getTeamLeaderAgents = async (params?: { team_id?: number }): Promise<TeamLeaderAgentRowOut[]> => {
  const response = await api.get<TeamLeaderAgentRowOut[]>('/api/team-leader/agents', { params });
  return response.data;
};

export const getTeamLeaderAgent = async (agentId: number): Promise<TeamLeaderAgentRowOut> => {
  const response = await api.get<TeamLeaderAgentRowOut>(`/api/team-leader/agents/${agentId}`);
  return response.data;
};

export const getTeamLeaderCalls = async (params?: { skip?: number; limit?: number }): Promise<{ items: TeamLeaderCallRowOut[]; total: number }> => {
  const response = await api.get<TeamLeaderCallRowOut[]>('/api/team-leader/calls', { params });
  const total = parseInt(response.headers['x-total-count'] || String(response.data.length), 10);
  return { items: response.data, total };
};

export const getTeamLeaderCall = async (callId: number): Promise<TeamLeaderCallRowOut> => {
  const response = await api.get<TeamLeaderCallRowOut>(`/api/team-leader/calls/${callId}`);
  return response.data;
};

export const getTeamLeaderKpis = async (params?: { month?: string }): Promise<TeamLeaderKpisOut> => {
  const response = await api.get<TeamLeaderKpisOut>('/api/team-leader/kpis', { params });
  return response.data;
};

export interface TeamManagerDateRangeParams {
  start_date?: string;
  end_date?: string;
}

export const getTeamManagerDashboard = async (params?: TeamManagerDateRangeParams): Promise<TeamManagerDashboardOut> => {
  const response = await api.get<TeamManagerDashboardOut>('/api/team-manager/dashboard', { params });
  return response.data;
};

export const getTeamManagerTeams = async (params?: { skip?: number; limit?: number; start_date?: string; end_date?: string }): Promise<TeamManagerTeamRowOut[]> => {
  const response = await api.get<TeamManagerTeamRowOut[]>('/api/team-manager/teams', { params });
  return response.data;
};

export const getTeamManagerAgents = async (params?: { team_id?: number; skip?: number; limit?: number; start_date?: string; end_date?: string }): Promise<TeamManagerAgentRowOut[]> => {
  const response = await api.get<TeamManagerAgentRowOut[]>('/api/team-manager/agents', { params });
  return response.data;
};

export const getTeamManagerSalesReport = async (params?: TeamManagerDateRangeParams): Promise<TeamManagerSalesReportOut> => {
  const response = await api.get<TeamManagerSalesReportOut>('/api/team-manager/reports/sales', { params });
  return response.data;
};

export const getTeamManagerRevenueReport = async (params?: TeamManagerDateRangeParams): Promise<TeamManagerRevenueReportOut> => {
  const response = await api.get<TeamManagerRevenueReportOut>('/api/team-manager/reports/revenue', { params });
  return response.data;
};

export const getTeamManagerConversionReport = async (params?: TeamManagerDateRangeParams): Promise<TeamManagerConversionReportOut> => {
  const response = await api.get<TeamManagerConversionReportOut>('/api/team-manager/reports/conversion', { params });
  return response.data;
};

export const getTeamManagerAttendanceReport = async (params?: TeamManagerDateRangeParams): Promise<TeamManagerAttendanceReportOut> => {
  const response = await api.get<TeamManagerAttendanceReportOut>('/api/team-manager/reports/attendance', { params });
  return response.data;
};

export const getTeamManagerKpis = async (params?: { month?: string; start_date?: string; end_date?: string }): Promise<TeamManagerKpisOut> => {
  const response = await api.get<TeamManagerKpisOut>('/api/team-manager/kpis', { params });
  return response.data;
};

export const getTeamManagerTransferRequests = async (): Promise<AgentTransferRequestOut[]> => {
  const response = await api.get<AgentTransferRequestOut[]>('/api/team-manager/transfer-requests');
  return response.data;
};

export const createTeamManagerTransferRequest = async (payload: AgentTransferRequestCreate): Promise<AgentTransferRequestOut> => {
  const response = await api.post<AgentTransferRequestOut>('/api/team-manager/transfer-requests', payload);
  return response.data;
};

export const cancelTeamManagerTransferRequest = async (requestId: number): Promise<AgentTransferRequestOut> => {
  const response = await api.patch<AgentTransferRequestOut>(`/api/team-manager/transfer-requests/${requestId}/cancel`);
  return response.data;
};

export interface InterviewCandidateNotifyResponse {
  success: boolean;
  candidate_id: number;
  template: string;
  message: string;
}

export interface InterviewCandidateBulkNotifyResponse {
  success_count: number;
  failed_count: number;
  total: number;
  results: Array<{
    candidate_id: number;
    success: boolean;
    error?: string;
  }>;
}

export const notifyInterviewCandidate = async (
  candidateId: number,
  template: string,
  context?: Record<string, any>
): Promise<InterviewCandidateNotifyResponse> => {
  const response = await api.post<InterviewCandidateNotifyResponse>(
    `/api/hr/interviews/candidates/${candidateId}/notify`,
    { template, context }
  );
  return response.data;
};

export const bulkNotifyInterviewCandidates = async (
  candidateIds: number[],
  template: string,
  context?: Record<string, any>
): Promise<InterviewCandidateBulkNotifyResponse> => {
  const response = await api.post<InterviewCandidateBulkNotifyResponse>(
    '/api/hr/interviews/candidates/bulk-notify',
    { candidate_ids: candidateIds, template, context }
  );
  return response.data;
};

export default api;
