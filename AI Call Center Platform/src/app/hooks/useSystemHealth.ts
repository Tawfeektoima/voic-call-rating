import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSystemMetrics, getSystemAlerts, resolveAlert } from '../lib/api';
import { SystemMetrics, SystemAlert } from '../lib/types';

export const useSystemMetrics = () => {
  return useQuery<SystemMetrics>({
    queryKey: ['systemMetrics'],
    queryFn: getSystemMetrics,
    refetchInterval: 5000, // Refresh every 5 seconds
  });
};

export const useSystemAlerts = () => {
  return useQuery<SystemAlert[]>({
    queryKey: ['systemAlerts'],
    queryFn: getSystemAlerts,
    refetchInterval: 60000,
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
