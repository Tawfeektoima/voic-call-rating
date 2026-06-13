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
} from './types';

// Create a centralized Axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getApiErrorMessage = (error: unknown, fallback: string): string => {
  if (!axios.isAxiosError(error)) return fallback;

  const detail = (error.response?.data as any)?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === 'string' && first.trim()) {
      return first;
    }
    if (first && typeof first === 'object' && typeof first.msg === 'string' && first.msg.trim()) {
      return first.msg;
    }
  }

  if (typeof (error.response?.data as any)?.message === 'string') {
    return (error.response?.data as any).message;
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

// Response interceptor for global error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const responseStatus = error.response?.status;
    const detail = (error.response?.data as any)?.detail;

    if (responseStatus === 401 || (responseStatus === 403 && typeof detail === 'string' && detail.toLowerCase().includes('account is'))) {
      console.warn('Unauthorized - Clearing session and redirecting to login');
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      
      // Force redirect to login
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Admin API Functions
 */

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

export const getTeamManagerDashboard = async (): Promise<TeamManagerDashboardOut> => {
  const response = await api.get<TeamManagerDashboardOut>('/api/team-manager/dashboard');
  return response.data;
};

export const getTeamManagerTeams = async (params?: { skip?: number; limit?: number }): Promise<TeamManagerTeamRowOut[]> => {
  const response = await api.get<TeamManagerTeamRowOut[]>('/api/team-manager/teams', { params });
  return response.data;
};

export const getTeamManagerAgents = async (params?: { team_id?: number; skip?: number; limit?: number }): Promise<TeamManagerAgentRowOut[]> => {
  const response = await api.get<TeamManagerAgentRowOut[]>('/api/team-manager/agents', { params });
  return response.data;
};

export const getTeamManagerSalesReport = async (): Promise<TeamManagerSalesReportOut> => {
  const response = await api.get<TeamManagerSalesReportOut>('/api/team-manager/reports/sales');
  return response.data;
};

export const getTeamManagerRevenueReport = async (): Promise<TeamManagerRevenueReportOut> => {
  const response = await api.get<TeamManagerRevenueReportOut>('/api/team-manager/reports/revenue');
  return response.data;
};

export const getTeamManagerConversionReport = async (): Promise<TeamManagerConversionReportOut> => {
  const response = await api.get<TeamManagerConversionReportOut>('/api/team-manager/reports/conversion');
  return response.data;
};

export const getTeamManagerAttendanceReport = async (): Promise<TeamManagerAttendanceReportOut> => {
  const response = await api.get<TeamManagerAttendanceReportOut>('/api/team-manager/reports/attendance');
  return response.data;
};

export const getTeamManagerKpis = async (params?: { month?: string }): Promise<TeamManagerKpisOut> => {
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

export default api;
