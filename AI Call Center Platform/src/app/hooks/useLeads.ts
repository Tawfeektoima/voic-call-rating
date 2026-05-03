import { useQuery } from '@tanstack/react-query';
import { getLeads } from '../lib/api';
import { Call } from '../lib/types';

export const useLeads = () => {
  return useQuery<Call[]>({
    queryKey: ['leads'],
    queryFn: getLeads,
    refetchInterval: 60000, // Refresh every minute
  });
};
