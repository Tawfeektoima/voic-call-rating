import { useQuery } from "@tanstack/react-query";
import api from "../lib/api";
import { CallViolation, ViolationSummaryRow } from "../lib/types";

export const useAgentViolations = (employeeId: number) =>
  useQuery({
    queryKey: ["violations", employeeId],
    queryFn: async () => {
      const res = await api.get(`/api/hr/violations/${employeeId}`);
      return res.data as {
        employee_name: string;
        total_violations: number;
        total_deductions: number;
        violations: CallViolation[];
      };
    },
    enabled: !!employeeId,
  });

export const useViolationsSummary = () =>
  useQuery({
    queryKey: ["violations-summary"],
    queryFn: async () => {
      const res = await api.get("/api/hr/violations/summary");
      return res.data as ViolationSummaryRow[];
    },
  });

export const useViolationStats = () =>
  useQuery({
    queryKey: ["violation-stats"],
    queryFn: async () => {
      const res = await api.get("/api/hr/violations/stats");
      return res.data;
    },
  });

export const useViolationTrends = (days: number = 7) =>
  useQuery({
    queryKey: ["violation-trends", days],
    queryFn: async () => {
      const res = await api.get(`/api/hr/violations/trends?days=${days}`);
      return res.data as { date: string; high: number; medium: number; low: number }[];
    },
  });
