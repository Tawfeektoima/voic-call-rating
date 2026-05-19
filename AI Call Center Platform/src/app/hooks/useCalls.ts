import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { searchCalls, uploadAudio, bulkUploadAudio } from '../lib/api';
import { Call } from '../lib/types';

export const useCalls = (
  params: {
    employee_code?: string;
    campaign_id?: number;
    date_from?: string;
    date_to?: string;
    limit?: number;
    min_id?: number;
  } = {},
  options?: Omit<Parameters<typeof useQuery<Call[]>>[0], 'queryKey' | 'queryFn'>
) => {
  return useQuery<Call[]>({
    queryKey: ['calls', params],
    queryFn: () => searchCalls(params),
    ...options,
  });
};

export const useUploadAudio = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => uploadAudio(formData),
    onSuccess: () => {
      // Invalidate all related queries to force refresh UI across the app
      queryClient.invalidateQueries({ queryKey: ['dashboardKPIs'] });
      queryClient.invalidateQueries({ queryKey: ['calls'] });
      queryClient.invalidateQueries({ queryKey: ['systemMetrics'] });
    },
  });
};

export const useBulkUploadAudio = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => bulkUploadAudio(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboardKPIs'] });
      queryClient.invalidateQueries({ queryKey: ['calls'] });
      queryClient.invalidateQueries({ queryKey: ['systemMetrics'] });
    },
  });
};
