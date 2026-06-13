/**
 * Shared role display constants.
 * Single source of truth consumed by Header, Sidebar, and any future role-aware components.
 * Covers the supported UserRole values including HR_MANAGER.
 */
import { UserRole } from './types';

/** Tailwind classes for the header role badge (bg + text + border). */
export const ROLE_BADGE_COLORS: Record<UserRole, string> = {
  [UserRole.ADMIN]:      'bg-violet-500/15 text-violet-300 border-violet-500/30',
  [UserRole.QA]:         'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  [UserRole.AGENT]:      'bg-amber-500/15 text-amber-300 border-amber-500/30',
  [UserRole.HR_MANAGER]: 'bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/30',
  [UserRole.OPS_MANAGER]: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  [UserRole.TEAM_MANAGER]: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  [UserRole.TEAM_LEADER]: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
};

/** Tailwind gradient classes used for avatar backgrounds in the sidebar. */
export const ROLE_GRADIENT_COLORS: Record<UserRole, string> = {
  [UserRole.ADMIN]:      'from-violet-500 to-indigo-500',
  [UserRole.QA]:         'from-emerald-500 to-teal-500',
  [UserRole.AGENT]:      'from-amber-500 to-orange-500',
  [UserRole.HR_MANAGER]: 'from-fuchsia-500 to-pink-500',
  [UserRole.OPS_MANAGER]: 'from-cyan-500 to-sky-500',
  [UserRole.TEAM_MANAGER]: 'from-blue-500 to-indigo-500',
  [UserRole.TEAM_LEADER]: 'from-rose-500 to-pink-500',
};

/** Human-readable label for each role. */
export const ROLE_LABELS: Record<UserRole, string> = {
  [UserRole.ADMIN]:      'Administrator',
  [UserRole.QA]:         'QA Analyst',
  [UserRole.AGENT]:      'Agent',
  [UserRole.HR_MANAGER]: 'HR Manager',
  [UserRole.OPS_MANAGER]: 'Ops Manager',
  [UserRole.TEAM_MANAGER]: 'Team Manager',
  [UserRole.TEAM_LEADER]: 'Team Leader',
};

export const PERMISSIONS = {
  VIEW_OWN_DASHBOARD: 'dashboard.view_own',
  VIEW_GLOBAL_DASHBOARD: 'dashboard.view_global',
  VIEW_OWN_PROFILE: 'profile.view_own',
  VIEW_AGENT_PROFILES: 'profiles.view_agents',
  VIEW_OWN_CALLS: 'calls.view_own',
  VIEW_RAW_CALLS: 'calls.view_raw',
  UPLOAD_OWN_CALLS: 'calls.upload_own',
  REVIEW_CALLS: 'calls.review',
  UPDATE_LEADS: 'calls.update_leads',
  VIEW_CAMPAIGNS: 'campaigns.view',
  MANAGE_CAMPAIGNS: 'campaigns.manage',
  VIEW_SUCCESS_LIBRARY: 'success_library.view',
  VIEW_BI: 'business_intelligence.view',
  VIEW_DATA_CENTER: 'data_center.view',
  VIEW_HR_DASHBOARD: 'hr.dashboard.view',
  MANAGE_HR_ONBOARDING: 'hr.onboarding.manage',
  VIEW_EMPLOYEES: 'employees.view',
  MANAGE_EMPLOYEES: 'employees.manage',
  CHANGE_EMPLOYEE_ROLE: 'employees.change_role',
  CHANGE_EMPLOYEE_STATUS: 'employees.change_status',
  VIEW_AUDIT_LOGS: 'audit.view',
  EXPORT_DATA: 'exports.run',
  VIEW_SYSTEM_HEALTH: 'system.health.view',
  RESOLVE_SYSTEM_ALERTS: 'system.alerts.resolve',
  VIEW_OPS_REPORTS: 'ops.reports.view',
  VIEW_TEAM_MANAGER_WORKSPACE: 'team_manager.workspace.view',
  VIEW_TEAM_LEADER_WORKSPACE: 'team_leader.workspace.view',
  VIEW_NOTES: 'notes.view',
  MANAGE_KPI_THRESHOLDS: 'kpi_thresholds.manage',
} as const;

export type Permission = typeof PERMISSIONS[keyof typeof PERMISSIONS];

export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  [UserRole.AGENT]: [
    PERMISSIONS.VIEW_OWN_DASHBOARD,
    PERMISSIONS.VIEW_OWN_PROFILE,
    PERMISSIONS.VIEW_OWN_CALLS,
    PERMISSIONS.UPLOAD_OWN_CALLS,
    PERMISSIONS.VIEW_SUCCESS_LIBRARY,
    PERMISSIONS.VIEW_NOTES,
  ],
  [UserRole.TEAM_LEADER]: [
    PERMISSIONS.VIEW_TEAM_LEADER_WORKSPACE,
    PERMISSIONS.VIEW_AGENT_PROFILES,
    PERMISSIONS.VIEW_SUCCESS_LIBRARY,
    PERMISSIONS.VIEW_NOTES,
  ],
  [UserRole.TEAM_MANAGER]: [
    PERMISSIONS.VIEW_TEAM_MANAGER_WORKSPACE,
    PERMISSIONS.VIEW_AGENT_PROFILES,
    PERMISSIONS.VIEW_NOTES,
  ],
  [UserRole.HR_MANAGER]: [
    PERMISSIONS.VIEW_HR_DASHBOARD,
    PERMISSIONS.MANAGE_HR_ONBOARDING,
    PERMISSIONS.VIEW_EMPLOYEES,
    PERMISSIONS.MANAGE_EMPLOYEES,
    PERMISSIONS.CHANGE_EMPLOYEE_ROLE,
    PERMISSIONS.CHANGE_EMPLOYEE_STATUS,
    PERMISSIONS.VIEW_NOTES,
  ],
  [UserRole.QA]: [
    PERMISSIONS.VIEW_GLOBAL_DASHBOARD,
    PERMISSIONS.VIEW_RAW_CALLS,
    PERMISSIONS.REVIEW_CALLS,
    PERMISSIONS.UPDATE_LEADS,
    PERMISSIONS.VIEW_CAMPAIGNS,
    PERMISSIONS.VIEW_SUCCESS_LIBRARY,
    PERMISSIONS.VIEW_AGENT_PROFILES,
    PERMISSIONS.EXPORT_DATA,
    PERMISSIONS.VIEW_NOTES,
  ],
  [UserRole.OPS_MANAGER]: [
    PERMISSIONS.VIEW_OPS_REPORTS,
    PERMISSIONS.VIEW_NOTES,
  ],
  [UserRole.ADMIN]: Object.values(PERMISSIONS) as Permission[],
};

export const getPermissionsForRole = (role: UserRole): Permission[] => ROLE_PERMISSIONS[role] ?? ROLE_PERMISSIONS[UserRole.AGENT];

export const hasPermission = (role: UserRole, permission: Permission, userPermissions?: string[]): boolean => {
  if (userPermissions && userPermissions.length > 0) {
    return userPermissions.includes(permission);
  }
  return getPermissionsForRole(role).includes(permission);
};
