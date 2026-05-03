import { NavLink, useLocation } from 'react-router';
import {
  LayoutDashboard, Radio, Phone, BarChart3, Star, UserCircle,
  Database, Activity, ChevronLeft, ChevronRight, Shield, Zap,
  Users, Settings, LogOut, Eye, EyeOff
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { cn } from '../ui/utils';

const navItems = [
  { path: '/', label: 'Dashboard', agentLabel: 'My Dashboard', icon: LayoutDashboard, roles: ['admin', 'manager', 'qa', 'agent'] },
  { path: '/campaigns', label: 'Campaigns', icon: Radio, roles: ['admin', 'manager', 'qa'] },
  { path: '/calls', label: 'Call Explorer', agentLabel: 'My Calls', icon: Phone, roles: ['admin', 'manager', 'qa', 'agent'] },
  { path: '/intelligence', label: 'BI Hub', icon: BarChart3, roles: ['admin', 'manager'] },
  { path: '/success-library', label: 'Success Library', icon: Star, roles: ['admin', 'manager', 'qa', 'agent'] },
  { path: '/agents/a1', label: 'Agent Profiles', agentLabel: 'My Profile', icon: Users, roles: ['admin', 'manager', 'qa', 'agent'] },
  { path: '/data-center', label: 'Data Center', icon: Database, roles: ['admin', 'manager'] },
  { path: '/system-health', label: 'System Health', icon: Activity, roles: ['admin'] },
];

const roleColors = {
  admin: 'from-violet-500 to-indigo-500',
  manager: 'from-cyan-500 to-blue-500',
  qa: 'from-emerald-500 to-teal-500',
  agent: 'from-amber-500 to-orange-500',
};

const roleLabels = {
  admin: 'Administrator',
  manager: 'Manager',
  qa: 'QA Analyst',
  agent: 'Agent',
};

export function Sidebar() {
  const { userRole, currentUser, sidebarCollapsed, setSidebarCollapsed, piiMaskingEnabled, setPiiMaskingEnabled } = useApp();
  const location = useLocation();

  const visibleItems = navItems.filter(item => item.roles.includes(userRole));

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
        {visibleItems.map((item) => {
          const isActive = location.pathname === item.path ||
            (item.path !== '/' && location.pathname.startsWith(item.path.split('/')[1] ? `/${item.path.split('/')[1]}` : item.path));
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group',
                sidebarCollapsed && 'justify-center px-0',
                isActive
                  ? 'bg-primary/15 text-primary border border-primary/20'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
              )}
            >
              <item.icon size={18} className={cn('flex-shrink-0', isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground')} />
              {!sidebarCollapsed && (
                <span className="text-sm">
                  {userRole === 'agent' && (item as any).agentLabel ? (item as any).agentLabel : item.label}
                </span>
              )}
            </NavLink>
          );
        })}

        {/* Admin-only section divider */}
        {!sidebarCollapsed && userRole === 'admin' && (
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
          <div className="flex items-center gap-3">
            <div className={cn('size-8 rounded-full bg-gradient-to-br flex items-center justify-center text-white text-xs font-semibold flex-shrink-0', roleColors[userRole])}>
              {currentUser.avatar}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-foreground text-xs font-medium truncate">{currentUser.name}</p>
              <p className="text-muted-foreground text-xs truncate">{roleLabels[userRole]}</p>
            </div>
          </div>
        ) : (
          <div className={cn('size-8 rounded-full bg-gradient-to-br flex items-center justify-center text-white text-xs font-semibold', roleColors[userRole])}>
            {currentUser.avatar}
          </div>
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
