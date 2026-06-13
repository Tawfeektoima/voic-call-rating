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
