import { NavLink } from 'react-router';
import {
  LayoutDashboard, Radio, Phone, BarChart3, Star, UserCircle,
  Database, Activity, ChevronLeft, ChevronRight, Shield, Zap,
  Users, LogOut, EyeOff, ShieldAlert, Inbox, BriefcaseBusiness
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { UserRole } from '../../lib/types';
import { Permission, PERMISSIONS, ROLE_GRADIENT_COLORS, ROLE_LABELS, hasPermission } from '../../lib/roles';
import { cn } from '../ui/utils';

interface NavItemConfig {
  path: string;
  label: string;
  agentLabel?: string;
  icon: React.ElementType;
  permission?: Permission;
  anyPermissions?: Permission[];
  roles?: UserRole[];
  /** Use NavLink `end` so the root '/' doesn't match all child routes. */
  end?: boolean;
}

const navItems: NavItemConfig[] = [
  { path: '/',               label: 'Dashboard',      agentLabel: 'My Dashboard', icon: LayoutDashboard, anyPermissions: [PERMISSIONS.VIEW_OWN_DASHBOARD, PERMISSIONS.VIEW_GLOBAL_DASHBOARD], end: true },
  { path: '/campaigns',      label: 'Campaigns',                                  icon: Radio,            permission: PERMISSIONS.VIEW_CAMPAIGNS },
  { path: '/calls',          label: 'Call Explorer',  agentLabel: 'My Calls',     icon: Phone,            anyPermissions: [PERMISSIONS.VIEW_OWN_CALLS, PERMISSIONS.VIEW_RAW_CALLS] },
  { path: '/intelligence',   label: 'BI Hub',                                     icon: BarChart3,         permission: PERMISSIONS.VIEW_BI },
  { path: '/success-library',label: 'Success Library',                            icon: Star,             permission: PERMISSIONS.VIEW_SUCCESS_LIBRARY },
  { path: '/agents/me',      label: 'Agent Profiles', agentLabel: 'My Profile',   icon: Users,            anyPermissions: [PERMISSIONS.VIEW_OWN_PROFILE, PERMISSIONS.VIEW_AGENT_PROFILES], roles: [UserRole.AGENT, UserRole.ADMIN, UserRole.QA] },
  { path: '/data-center',    label: 'Data Center',                                icon: Database,          permission: PERMISSIONS.VIEW_DATA_CENTER },
  { path: '/hr',             label: 'HR Dashboard',                               icon: ShieldAlert,       permission: PERMISSIONS.VIEW_HR_DASHBOARD },
  { path: '/hr/agents',      label: 'Agent Directory',                            icon: UserCircle,        permission: PERMISSIONS.VIEW_EMPLOYEES },
  { path: '/hr/interviews',  label: 'Interview Pipeline',                         icon: BriefcaseBusiness, anyPermissions: [PERMISSIONS.MANAGE_INTERVIEW_JOBS, PERMISSIONS.VIEW_INTERVIEW_CANDIDATES] },
  { path: '/team-leader',    label: 'Team Overview',                              icon: LayoutDashboard,   permission: PERMISSIONS.VIEW_TEAM_LEADER_WORKSPACE },
  { path: '/team-leader/agents', label: 'Team Agents',                            icon: Users,             permission: PERMISSIONS.VIEW_TEAM_LEADER_WORKSPACE },
  { path: '/team-leader/calls', label: 'Team Calls',                              icon: Phone,             permission: PERMISSIONS.VIEW_TEAM_LEADER_WORKSPACE },
  { path: '/team-leader/kpis',  label: 'Team KPIs',                               icon: BarChart3,         permission: PERMISSIONS.VIEW_TEAM_LEADER_WORKSPACE },
  { path: '/team-manager',   label: 'Manager Workspace',                          icon: Users,             permission: PERMISSIONS.VIEW_TEAM_MANAGER_WORKSPACE },
  { path: '/notes',          label: 'Workflow Notes',  agentLabel: 'My Notes',    icon: Inbox,             permission: PERMISSIONS.VIEW_NOTES },
  { path: '/system-health',  label: 'System Health',                              icon: Activity,          permission: PERMISSIONS.VIEW_SYSTEM_HEALTH },
];

export function Sidebar() {
  const { userRole, currentUser, sidebarCollapsed, setSidebarCollapsed, piiMaskingEnabled, setPiiMaskingEnabled } = useApp();

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  };

  const visibleItems = navItems.filter((item) => {
    if (item.roles && !item.roles.includes(userRole)) {
      return false;
    }
    if (item.permission) {
      return hasPermission(userRole, item.permission, currentUser?.permissions);
    }
    if (item.anyPermissions) {
      return item.anyPermissions.some((permission) => hasPermission(userRole, permission, currentUser?.permissions));
    }
    return false;
  });
  const gradientClass = ROLE_GRADIENT_COLORS[userRole] ?? 'from-slate-500 to-slate-700';

  return (
    <aside
      className={cn(
        'flex flex-col h-full bg-sidebar border-r border-border transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-60'
      )}
    >
      {/* Logo */}
      <div className={cn('flex items-center gap-3 px-4 py-5 border-b border-border', sidebarCollapsed && 'justify-center px-2')}>
        <div className="size-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center flex-shrink-0">
          <Zap size={16} className="text-white" />
        </div>
        {!sidebarCollapsed && (
          <div>
            <p className="text-slate-100 text-sm font-semibold leading-none">VoiceQA</p>
            <p className="text-muted-foreground text-xs mt-0.5">Enterprise AI</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-0.5 overflow-y-auto">
        {visibleItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.end}
            className={({ isActive }) => cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group',
              sidebarCollapsed && 'justify-center px-0',
              isActive
                ? 'bg-primary/15 text-primary border border-primary/20'
                : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
            )}
          >
            {({ isActive }) => (
              <>
                <item.icon
                  size={18}
                  className={cn(
                    'flex-shrink-0',
                    isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
                  )}
                />
                {!sidebarCollapsed && (
                  <span className="text-sm">
                    {userRole === UserRole.AGENT && item.agentLabel ? item.agentLabel : item.label}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}

        {/* Admin-only section divider */}
        {!sidebarCollapsed && userRole === UserRole.ADMIN && (
          <div className="pt-3 pb-1">
            <p className="px-3 text-xs text-muted-foreground uppercase tracking-wider">Admin Only</p>
          </div>
        )}
      </nav>

      {/* PII Toggle */}
      <div className={cn('px-3 py-3 border-t border-border', sidebarCollapsed && 'flex justify-center')}>
        {!sidebarCollapsed ? (
          <button
            onClick={() => setPiiMaskingEnabled(!piiMaskingEnabled)}
            className={cn(
              'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all',
              piiMaskingEnabled
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-red-500/10 text-red-400 border border-red-500/20'
            )}
          >
            {piiMaskingEnabled ? <Shield size={14} /> : <EyeOff size={14} />}
            <span>PII {piiMaskingEnabled ? 'Masked' : 'Visible'}</span>
          </button>
        ) : (
          <button
            onClick={() => setPiiMaskingEnabled(!piiMaskingEnabled)}
            className={cn(
              'size-8 flex items-center justify-center rounded-lg transition-all',
              piiMaskingEnabled ? 'text-emerald-400' : 'text-red-400'
            )}
          >
            {piiMaskingEnabled ? <Shield size={16} /> : <EyeOff size={16} />}
          </button>
        )}
      </div>

      {/* User Profile */}
      <div className={cn('px-3 py-3 border-t border-border', sidebarCollapsed && 'flex flex-col items-center gap-2')}>
        {!sidebarCollapsed ? (
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3 min-w-0">
              <div className={cn('size-8 rounded-full bg-gradient-to-br flex items-center justify-center text-white text-xs font-semibold flex-shrink-0', gradientClass)}>
                {currentUser?.avatar || (currentUser?.name ? currentUser.name.substring(0, 2).toUpperCase() : '')}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-foreground text-xs font-medium truncate">{currentUser?.name}</p>
                <p className="text-muted-foreground text-xs truncate">{ROLE_LABELS[userRole]}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Log Out"
              className="text-muted-foreground hover:text-red-400 p-1.5 rounded-lg hover:bg-secondary transition-all flex-shrink-0"
            >
              <LogOut size={14} />
            </button>
          </div>
        ) : (
          <button
            onClick={handleLogout}
            title="Log Out"
            className={cn('size-8 rounded-full bg-gradient-to-br flex items-center justify-center text-white text-xs font-semibold group relative', gradientClass)}
          >
            <span className="group-hover:hidden">{currentUser?.avatar || (currentUser?.name ? currentUser.name.substring(0, 2).toUpperCase() : '')}</span>
            <LogOut size={14} className="hidden group-hover:block text-white absolute" />
          </button>
        )}

        {/* Collapse toggle */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className={cn(
            'mt-2 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-all',
            sidebarCollapsed ? 'size-8' : 'w-full h-7'
          )}
        >
          {sidebarCollapsed ? <ChevronRight size={14} /> : (
            <span className="flex items-center gap-1 text-xs"><ChevronLeft size={14} /> Collapse</span>
          )}
        </button>
      </div>
    </aside>
  );
}
