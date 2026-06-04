import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { DashboardKPIs } from '../lib/types';

export const DASHBOARD_REFETCH_INTERVAL_MS = 30000;

export const getDashboardKPIs = async (): Promise<DashboardKPIs> => {
  const response = await api.get<DashboardKPIs>('/api/analytics/dashboard');
  return response.data;
};

export const useDashboard = () => {
  return useQuery<DashboardKPIs>({
    queryKey: ['dashboardKPIs'],
    queryFn: getDashboardKPIs,
    refetchInterval: DASHBOARD_REFETCH_INTERVAL_MS,
    staleTime: DASHBOARD_REFETCH_INTERVAL_MS / 2,
    refetchOnWindowFocus: false,
  });
};
