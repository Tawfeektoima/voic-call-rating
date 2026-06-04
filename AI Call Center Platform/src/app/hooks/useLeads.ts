import { useQuery } from '@tanstack/react-query';
import { getLeads } from '../lib/api';
import { Call } from '../lib/types';

export const LEADS_REFETCH_INTERVAL_MS = 120000;

export const useLeads = () => {
  return useQuery<Call[]>({
    queryKey: ['leads'],
    queryFn: getLeads,
    refetchInterval: LEADS_REFETCH_INTERVAL_MS,
    staleTime: LEADS_REFETCH_INTERVAL_MS / 2,
    refetchOnWindowFocus: false,
  });
};
