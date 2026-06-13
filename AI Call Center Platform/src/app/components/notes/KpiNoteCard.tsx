import { TrendingDown, TrendingUp } from 'lucide-react';
import { RoleNote } from '../../lib/types';
import { formatKpiValue, getKpiDefinition } from '../../lib/kpiCatalog';

export function KpiNoteCard({ note }: { note: RoleNote }) {
  const definition = getKpiDefinition(note.kpi_key || undefined);
  const unit = definition?.unit || 'count';
  const current = note.current_value;
  const target = note.target_value;
  const delta = current !== null && current !== undefined && target !== null && target !== undefined ? current - target : null;
  const isPositive = definition?.direction === 'lower_is_better' ? (delta ?? 0) <= 0 : (delta ?? 0) >= 0;
  const DeltaIcon = isPositive ? TrendingUp : TrendingDown;

  return (
    <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 px-4 py-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-indigo-300/80">KPI Context</p>
          <p className="text-sm text-foreground font-medium">{note.kpi_label || definition?.label || note.kpi_key}</p>
          {definition?.description && <p className="text-xs text-muted-foreground mt-1">{definition.description}</p>}
        </div>
        {note.kpi_key && <span className="text-[11px] text-muted-foreground font-mono">{note.kpi_key}</span>}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <MetricBlock label="Current" value={formatKpiValue(current, unit)} />
        <MetricBlock label="Target" value={formatKpiValue(target, unit)} />
        <div className="rounded-lg border border-border/60 bg-background/40 px-3 py-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Gap</p>
          <div className={`text-sm font-medium flex items-center gap-1 ${isPositive ? 'text-emerald-300' : 'text-red-300'}`}>
            <DeltaIcon size={14} />
            {delta === null ? '--' : formatKpiValue(Math.abs(delta), unit)}
          </div>
        </div>
      </div>

      {(note.period_start || note.period_end) && (
        <p className="text-xs text-muted-foreground">
          Period: {note.period_start ? new Date(note.period_start).toLocaleDateString() : '--'} to{' '}
          {note.period_end ? new Date(note.period_end).toLocaleDateString() : '--'}
        </p>
      )}
    </div>
  );
}

function MetricBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/60 bg-background/40 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-sm text-foreground font-medium">{value}</p>
    </div>
  );
}
