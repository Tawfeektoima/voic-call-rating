import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSystemMetrics, getSystemAlerts, resolveAlert } from '../lib/api';
import { SystemMetrics, SystemAlert } from '../lib/types';

export const SYSTEM_METRICS_REFETCH_INTERVAL_MS = 30000;
export const SYSTEM_ALERTS_REFETCH_INTERVAL_MS = 120000;

export const useSystemMetrics = () => {
  return useQuery<SystemMetrics>({
    queryKey: ['systemMetrics'],
    queryFn: getSystemMetrics,
    refetchInterval: SYSTEM_METRICS_REFETCH_INTERVAL_MS,
    staleTime: SYSTEM_METRICS_REFETCH_INTERVAL_MS / 2,
    refetchOnWindowFocus: false,
  });
};

export const useSystemAlerts = () => {
  return useQuery<SystemAlert[]>({
    queryKey: ['systemAlerts'],
    queryFn: getSystemAlerts,
    refetchInterval: SYSTEM_ALERTS_REFETCH_INTERVAL_MS,
    staleTime: SYSTEM_ALERTS_REFETCH_INTERVAL_MS / 2,
    refetchOnWindowFocus: false,
  });
};

export const useResolveAlert = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => resolveAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['systemAlerts'] });
    },
  });
};
