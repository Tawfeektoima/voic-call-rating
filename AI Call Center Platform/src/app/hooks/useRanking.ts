import { useQuery } from '@tanstack/react-query';
import { getRanking } from '../lib/api';
import { EmployeeRanking } from '../lib/types';

export const useRanking = (params?: { top?: number; bottom?: number }) => {
  return useQuery<EmployeeRanking[]>({
    queryKey: ['ranking', params],
    queryFn: () => getRanking(params),
  });
};
