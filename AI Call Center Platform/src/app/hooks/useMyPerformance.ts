import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { EmployeePerformance } from '../lib/types';

export const getMyPerformance = async (employeeId: number): Promise<EmployeePerformance> => {
  const response = await api.get<EmployeePerformance>('/api/analytics/my-performance', {
    params: { employee_id: employeeId },
  });
  return response.data;
};

export const useMyPerformance = (employeeId: number | null) => {
  return useQuery<EmployeePerformance>({
    queryKey: ['myPerformance', employeeId],
    queryFn: () => getMyPerformance(employeeId!),
    enabled: !!employeeId,
  });
};
