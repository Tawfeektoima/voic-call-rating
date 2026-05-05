import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCallDetails } from '../lib/api';
import { Call } from '../lib/types';

export const useCallStatus = (callId: number | null) => {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!callId) return;

    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const wsBaseUrl = apiBaseUrl.replace(/^http/, 'ws');
    const wsUrl = `${wsBaseUrl}/ws/calls/${callId}`;
    const socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.call_id === callId) {
        queryClient.invalidateQueries({ queryKey: ['callStatus', callId] });
      }
    };

    return () => {
      socket.close();
    };
  }, [callId, queryClient]);

  return useQuery<Call>({
    queryKey: ['callStatus', callId],
    queryFn: () => getCallDetails(callId!),
    enabled: !!callId,
  });
};
