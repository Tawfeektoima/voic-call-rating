import { Bell, Search, Shield } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useSystemAlerts } from '../../hooks/useSystemHealth';
import { cn } from '../ui/utils';
import { ROLE_BADGE_COLORS, ROLE_LABELS } from '../../lib/roles';

export function Header({ title }: { title: string }) {
  const { userRole } = useApp();
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

      {/* Role Badge */}
      <div className={cn(
        'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold select-none',
        ROLE_BADGE_COLORS[userRole] ?? 'bg-secondary text-foreground border-border',
      )}>
        <Shield size={12} />
        <span>{ROLE_LABELS[userRole] ?? userRole}</span>
      </div>
    </header>
  );
}
