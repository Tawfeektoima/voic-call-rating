import { useQuery } from '@tanstack/react-query';
import { getAgentDetails } from '../lib/api';
import { Agent } from '../lib/types';

export const useAgentDetails = (id: number | null) => {
  return useQuery<Agent>({
    queryKey: ['agentDetails', id],
    queryFn: () => getAgentDetails(id!),
    enabled: !!id,
  });
};
