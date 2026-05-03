import { useQuery } from '@tanstack/react-query';
import { getGoldenMoments } from '../lib/api';
import { Call } from '../lib/types';

export const useGoldenMoments = () => {
  return useQuery<Call[]>({
    queryKey: ['goldenMoments'],
    queryFn: getGoldenMoments,
  });
};
