import { useQuery } from '@tanstack/react-query';
import { getCommonErrors } from '../lib/api';
import { CommonError } from '../lib/types';

export const useCommonErrors = (limit: number = 10) => {
  return useQuery<CommonError[]>({
    queryKey: ['commonErrors', limit],
    queryFn: () => getCommonErrors(limit),
  });
};
