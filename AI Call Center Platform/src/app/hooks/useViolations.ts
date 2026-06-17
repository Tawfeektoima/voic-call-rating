import { useQuery } from "@tanstack/react-query";
import api from "../lib/api";
import { CallViolation, ViolationStats, ViolationSummaryRow } from "../lib/types";

export const useAgentViolations = (employeeId: number, teamId?: number) =>
  useQuery({
    queryKey: ["violations", employeeId, teamId ?? "all"],
    queryFn: async () => {
      const res = await api.get(`/api/hr/violations/${employeeId}`, {
        params: teamId ? { team_id: teamId } : undefined,
      });
      return res.data as {
        employee_name: string;
        total_violations: number;
        total_deductions: number;
        violations: CallViolation[];
      };
    },
    enabled: !!employeeId,
  });

export const useViolationsSummary = (teamId?: number) =>
  useQuery({
    queryKey: ["violations-summary", teamId ?? "all"],
    queryFn: async () => {
      const res = await api.get("/api/hr/violations/summary", {
        params: teamId ? { team_id: teamId } : undefined,
      });
      return res.data as ViolationSummaryRow[];
    },
  });

export const useViolationStats = (teamId?: number) =>
  useQuery({
    queryKey: ["violation-stats", teamId ?? "all"],
    queryFn: async () => {
      const res = await api.get("/api/hr/violations/stats", {
        params: teamId ? { team_id: teamId } : undefined,
      });
      return res.data as ViolationStats;
    },
  });

export const useViolationTrends = (days: number = 7, teamId?: number) =>
  useQuery({
    queryKey: ["violation-trends", days, teamId ?? "all"],
    queryFn: async () => {
      const res = await api.get("/api/hr/violations/trends", {
        params: {
          days,
          ...(teamId ? { team_id: teamId } : {}),
        },
      });
      return res.data as { date: string; high: number; medium: number; low: number }[];
    },
  });
