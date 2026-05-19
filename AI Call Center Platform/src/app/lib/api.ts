import axios, { AxiosError } from 'axios';
import { 
  Agent, 
  Campaign, 
  Call, 
  CallUploadResponse, 
  EmployeeRanking, 
  CommonError 
} from './types';

// Create a centralized Axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

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
    if (error.response?.status === 401) {
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

export default api;
