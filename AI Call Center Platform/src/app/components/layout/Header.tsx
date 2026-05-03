import { Bell, Search, ChevronDown, Shield } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useSystemAlerts } from '../../hooks/useSystemHealth';
import { useState } from 'react';
import { cn } from '../ui/utils';
import { UserRole } from '../../lib/types';

const roleColors = {
  [UserRole.ADMIN]: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
  [UserRole.MANAGER]: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  [UserRole.QA]: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  [UserRole.AGENT]: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
};

const roleLabels = {
  [UserRole.ADMIN]: 'Administrator',
  [UserRole.MANAGER]: 'Manager',
  [UserRole.QA]: 'QA Analyst',
  [UserRole.AGENT]: 'Agent',
};

export function Header({ title }: { title: string }) {
  const { userRole, setUserRole } = useApp();
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const { data: alerts } = useSystemAlerts();
  
  const unresolvedAlerts = (alerts || []).filter(a => !a.resolved && a.severity === 'critical').length;

  return (
    <header className="h-14 bg-background/80 backdrop-blur border-b border-border flex items-center px-6 gap-4 flex-shrink-0">
      <h1 className="text-slate-100 text-base font-semibold flex-1">{title}</h1>

      {/* Search */}
      <div className="relative hidden md:block">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <input
          placeholder="Search calls, agents..."
          className="bg-secondary border border-border rounded-lg pl-9 pr-4 py-1.5 text-sm text-foreground placeholder-slate-500 focus:outline-none focus:border-primary w-48"
        />
      </div>

      {/* Alerts bell */}
      <button className="relative size-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-all">
        <Bell size={16} />
        {unresolvedAlerts > 0 && (
          <span className="absolute top-1 right-1 size-2 bg-red-500 rounded-full" />
        )}
      </button>

      {/* Role Switcher (demo) */}
      <div className="relative">
        <button
          onClick={() => setRoleMenuOpen(!roleMenuOpen)}
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition-all',
            roleColors[userRole]
          )}
        >
          <Shield size={12} />
          <span>{roleLabels[userRole]}</span>
          <ChevronDown size={12} />
        </button>

        {roleMenuOpen && (
          <div className="absolute right-0 top-full mt-1 w-44 bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden">
            <p className="px-3 py-2 text-xs text-muted-foreground border-b border-border">Switch Demo Role</p>
            {Object.values(UserRole).map(role => (
              <button
                key={role}
                onClick={() => { setUserRole(role as UserRole); setRoleMenuOpen(false); }}
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2 text-sm transition-all',
                  role === userRole ? 'bg-primary/15 text-primary' : 'text-foreground hover:bg-secondary'
                )}
              >
                <div className={cn('size-1.5 rounded-full', 
                  role === UserRole.ADMIN ? 'bg-violet-400' : 
                  role === UserRole.MANAGER ? 'bg-cyan-400' : 
                  role === UserRole.QA ? 'bg-emerald-400' : 'bg-amber-400'
                )} />
                {roleLabels[role as UserRole]}
              </button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
