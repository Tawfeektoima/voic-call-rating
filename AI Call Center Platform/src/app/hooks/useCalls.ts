import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { searchCalls, uploadAudio } from '../lib/api';
import { Call } from '../lib/types';

export const useCalls = (params: {
  employee_code?: string;
  campaign_id?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
  min_id?: number;
} = {}) => {
  return useQuery<Call[]>({
    queryKey: ['calls', params],
    queryFn: () => searchCalls(params),
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
