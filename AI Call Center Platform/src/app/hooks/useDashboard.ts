import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { DashboardKPIs } from '../lib/types';

export const getDashboardKPIs = async (): Promise<DashboardKPIs> => {
  const response = await api.get<DashboardKPIs>('/api/analytics/dashboard');
  return response.data;
};

export const useDashboard = () => {
  return useQuery<DashboardKPIs>({
    queryKey: ['dashboardKPIs'],
    queryFn: getDashboardKPIs,
    refetchInterval: 10000, // Refresh every 10 seconds
  });
};
