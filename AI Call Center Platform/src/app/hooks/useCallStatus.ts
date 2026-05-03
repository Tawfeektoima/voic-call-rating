import { useQuery } from '@tanstack/react-query';
import { getCallDetails } from '../lib/api';
import { Call, CallStatus } from '../lib/types';

export const useCallStatus = (callId: number | null) => {
  return useQuery<Call>({
    queryKey: ['callStatus', callId],
    queryFn: () => getCallDetails(callId!),
    enabled: !!callId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === CallStatus.PENDING || status === CallStatus.PROCESSING) {
        return 3000; // Poll every 3 seconds
      }
      return false; // Stop polling
    },
  });
};
