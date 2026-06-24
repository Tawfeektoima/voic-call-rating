import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCallDetails } from '../lib/api';
import { getWebSocketBaseUrl } from '../lib/network';
import { Call } from '../lib/types';
import { useApp } from '../context/AppContext';
import { toast } from 'sonner';

export const useCallStatus = (callId: number | null) => {
  const queryClient = useQueryClient();
  const { forceLogout } = useApp();

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

    socket.onclose = (event) => {
      if (event.code === 4401) {
        forceLogout("Your session is no longer valid. Please sign in again.");
      } else if (event.code === 4403) {
        forceLogout("Your access is no longer allowed from this device or shift.");
      } else if (event.code === 1011) {
        toast.error("The connection ended unexpectedly. Please try again.");
      }
    };

    return () => {
      socket.close();
    };
  }, [callId, queryClient, forceLogout]);

  return useQuery<Call>({
    queryKey: ['callStatus', callId],
    queryFn: () => getCallDetails(callId!),
    enabled: !!callId,
  });
};
