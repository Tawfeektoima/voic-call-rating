import { useQuery } from '@tanstack/react-query';
import { getEmployees } from '../lib/api';
import { Agent } from '../lib/types';

export const useAgents = () => {
  return useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: getEmployees,
  });
};
