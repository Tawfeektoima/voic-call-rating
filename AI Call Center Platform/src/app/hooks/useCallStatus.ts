import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCallDetails } from '../lib/api';
import { getWebSocketBaseUrl } from '../lib/network';
import { Call } from '../lib/types';

export const useCallStatus = (callId: number | null) => {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!callId) return;

    const wsBaseUrl = getWebSocketBaseUrl();
    const token = localStorage.getItem('access_token');
    if (!token) return;
    const wsUrl = `${wsBaseUrl}/ws/calls/${callId}?auth_token=${encodeURIComponent(token)}`;
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
