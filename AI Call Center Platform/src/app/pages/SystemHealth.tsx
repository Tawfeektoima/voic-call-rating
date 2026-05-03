import { useState } from 'react';
import {
  Activity, AlertTriangle, CheckCircle, Clock, Cpu, Zap,
  Server, Database, RefreshCw, X, Volume2, AlertOctagon, Info
} from 'lucide-react';
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts';
import { useSystemMetrics, useSystemAlerts, useResolveAlert } from '../hooks/useSystemHealth';
import { SystemAlert, SystemMetrics } from '../lib/types';
import { cn } from '../components/ui/utils';
import { Skeleton } from '../components/ui/skeleton';

const alertTypeConfig = {
  shouting: { icon: Volume2, label: 'Vocal Agitation', color: 'red' },
  processing_failure: { icon: AlertOctagon, label: 'Processing Failure', color: 'red' },
  low_score: { icon: AlertTriangle, label: 'Low QA Score', color: 'amber' },
  system: { icon: Server, label: 'System Event', color: 'blue' },
  pii_leak: { icon: AlertTriangle, label: 'PII Security', color: 'red' },
};

const severityConfig = {
  critical: { color: 'red', bg: 'bg-red-500/8', border: 'border-red-500/25', dot: 'bg-red-500', label: 'Critical', iconBg: 'bg-red-500/15', iconText: 'text-red-400', badgeBg: 'bg-red-500/15', badgeText: 'text-red-400' },
  warning: { color: 'amber', bg: 'bg-amber-500/8', border: 'border-amber-500/25', dot: 'bg-amber-500', label: 'Warning', iconBg: 'bg-amber-500/15', iconText: 'text-amber-400', badgeBg: 'bg-amber-500/15', badgeText: 'text-amber-400' },
  info: { color: 'blue', bg: 'bg-blue-500/8', border: 'border-blue-500/25', dot: 'bg-blue-500', label: 'Info', iconBg: 'bg-blue-500/15', iconText: 'text-blue-400', badgeBg: 'bg-blue-500/15', badgeText: 'text-blue-400' },
};

function AlertItem({ alert, onResolve }: { alert: SystemAlert; onResolve: () => void }) {
  const atc = (alertTypeConfig as any)[alert.error_type] || alertTypeConfig.system;
  const sc = (severityConfig as any)[alert.severity] || severityConfig.info;

  return (
    <div className={cn(
      'flex items-start gap-3 p-4 rounded-xl border transition-all',
      alert.resolved ? 'opacity-40 bg-card/30 border-border' : `${sc.bg} ${sc.border}`
    )}>
      <div className={cn(
        'size-8 rounded-lg flex items-center justify-center flex-shrink-0',
        alert.resolved ? 'bg-slate-700' : sc.iconBg
      )}>
        {alert.resolved
          ? <CheckCircle size={15} className="text-muted-foreground" />
          : <atc.icon size={15} className={sc.iconText} />
        }
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={cn(
            'text-xs px-2 py-0.5 rounded-full',
            alert.resolved ? 'bg-slate-700 text-muted-foreground' : `${sc.badgeBg} ${sc.badgeText}`
          )}>
            {alert.resolved ? 'Resolved' : sc.label}
          </span>
          <span className="text-xs text-muted-foreground">{atc.label}</span>
          {!alert.resolved && <span className={cn('size-1.5 rounded-full ml-auto animate-pulse', sc.dot)} />}
        </div>
        <p className="text-xs text-foreground leading-relaxed">{alert.error_message}</p>
        <p className="text-xs text-muted-foreground mt-1">{new Date(alert.created_at).toLocaleString()}</p>
      </div>
      {!alert.resolved && (
        <button
          onClick={onResolve}
          className="size-7 flex items-center justify-center rounded-lg bg-slate-700 hover:bg-slate-600 text-muted-foreground hover:text-foreground transition-all flex-shrink-0"
        >
          <X size={12} />
        </button>
      )}
    </div>
  );
}

function GaugeRing({ value, max = 100, label, color, size = 80 }: {
  value: number; max?: number; label: string; color: string; size?: number;
}) {
  const pct = (value / max) * 100;
  const r = (size / 2) - 8;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const displayColor = pct > 85 ? '#ef4444' : pct > 65 ? '#f59e0b' : color;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} stroke="#1e293b" strokeWidth={8} fill="none" />
          <circle
            cx={size / 2} cy={size / 2} r={r}
            stroke={displayColor} strokeWidth={8} fill="none"
            strokeDasharray={`${dash} ${circ - dash}`}
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 4px ${displayColor}60)` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-foreground text-sm font-bold">{value}{typeof max === 'number' && max !== 100 ? '' : '%'}</span>
        </div>
      </div>
      <p className="text-xs text-muted-foreground text-center">{label}</p>
    </div>
  );
}

export function SystemHealth() {
  const [showResolved, setShowResolved] = useState(false);

  const { data: metrics, isLoading: metricsLoading, refetch: refetchMetrics, isFetching: isFetchingMetrics } = useSystemMetrics();
  const { data: alerts, isLoading: alertsLoading, refetch: refetchAlerts, isFetching: isFetchingAlerts } = useSystemAlerts();
  const { mutate: resolve } = useResolveAlert();

  const isRefreshing = isFetchingMetrics || isFetchingAlerts;

  const activeAlerts = (alerts || []).filter(a => !a.resolved);
  const resolvedAlerts = (alerts || []).filter(a => a.resolved);
  const criticalCount = activeAlerts.filter(a => a.severity === 'critical').length;

  const handleResolve = (id: number) => {
    resolve(id);
  };

  const handleRefresh = async () => {
    refetchMetrics();
    refetchAlerts();
  };

  const displayAlerts = showResolved ? alerts || [] : activeAlerts;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <p className="text-muted-foreground text-xs">Real-time system monitoring and anomaly detection</p>
          {criticalCount > 0 && (
            <span className="flex items-center gap-1.5 px-3 py-1 bg-red-500/15 border border-red-500/25 rounded-full text-xs text-red-400 animate-pulse">
              <span className="size-1.5 bg-red-400 rounded-full" />
              {criticalCount} Critical Active
            </span>
          )}
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-2 px-3 py-1.5 bg-secondary hover:bg-slate-700 text-muted-foreground hover:text-foreground rounded-xl text-xs transition-all"
        >
          <RefreshCw size={12} className={cn(isRefreshing && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* System Gauges */}
      <div className="bg-card border border-border rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-foreground text-sm font-semibold">Inference Dashboard</h3>
          <span className="flex items-center gap-1.5 text-xs text-emerald-400">
            <span className="size-1.5 bg-emerald-400 rounded-full animate-pulse" />
            System Online · {metrics?.uptime || 0}h uptime
          </span>
        </div>

        {metricsLoading ? (
          <div className="flex justify-around py-10">
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="size-20 rounded-full bg-secondary" />)}
          </div>
        ) : metrics && (
          <div className="flex items-center justify-around flex-wrap gap-6 mb-6">
            <GaugeRing value={metrics.gpu_load} label="GPU Load" color="#6366f1" size={90} />
            <GaugeRing value={metrics.cpu_load} label="CPU Load" color="#06b6d4" size={90} />
            <div className="flex flex-col items-center gap-2">
              <div className="size-[90px] rounded-full border-4 border-indigo-500/30 flex flex-col items-center justify-center" style={{ boxShadow: '0 0 20px rgba(99,102,241,0.15)' }}>
                <span className="text-foreground text-base font-bold">{metrics.inference_time}</span>
                <span className="text-muted-foreground text-xs">ms</span>
              </div>
              <p className="text-xs text-muted-foreground text-center">T_inference</p>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="size-[90px] rounded-full border-4 border-cyan-500/30 flex flex-col items-center justify-center">
                <span className="text-foreground text-base font-bold">{metrics.calls_processing}</span>
                <span className="text-muted-foreground text-xs">calls</span>
              </div>
              <p className="text-xs text-muted-foreground text-center">Processing</p>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="size-[90px] rounded-full border-4 border-amber-500/30 flex flex-col items-center justify-center">
                <span className="text-foreground text-base font-bold">{metrics.queue_depth}</span>
                <span className="text-muted-foreground text-xs">queued</span>
              </div>
              <p className="text-xs text-muted-foreground text-center">Queue Depth</p>
            </div>
          </div>
        )}

        {/* Inference Time Chart */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground mb-2">Inference Latency (ms) — Today</p>
            <ResponsiveContainer width="100%" height={100}>
              <AreaChart data={metrics?.inference_history || []}>
                <defs>
                  <linearGradient id="infGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis domain={['auto', 'auto']} tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '11px' }} />
                <Area type="monotone" dataKey="value" stroke="#6366f1" fill="url(#infGrad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-2">GPU Load (%) — Today</p>
            <ResponsiveContainer width="100%" height={100}>
              <AreaChart data={metrics?.gpu_history || []}>
                <defs>
                  <linearGradient id="gpuGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '11px' }} />
                <Area type="monotone" dataKey="value" stroke="#06b6d4" fill="url(#gpuGrad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Alerts Panel */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 className="text-foreground text-sm font-semibold">System Health Alerts</h3>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5"><span className="size-2 bg-red-500 rounded-full" />{activeAlerts.filter(a => a.severity === 'critical').length} critical</span>
              <span className="flex items-center gap-1.5"><span className="size-2 bg-amber-500 rounded-full" />{activeAlerts.filter(a => a.severity === 'warning').length} warning</span>
            </div>
            <button
              onClick={() => setShowResolved(!showResolved)}
              className={cn(
                'px-3 py-1 rounded-lg text-xs transition-all',
                showResolved ? 'bg-slate-700 text-foreground' : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {showResolved ? 'Hide Resolved' : 'Show Resolved'}
            </button>
          </div>
        </div>

        <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
          {alertsLoading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full bg-secondary" />)
          ) : displayAlerts.length > 0 ? displayAlerts.map(alert => (
            <AlertItem key={alert.id} alert={alert} onResolve={() => handleResolve(alert.id)} />
          )) : (
            <div className="flex flex-col items-center py-12 text-center">
              <CheckCircle size={36} className="text-emerald-500 mb-3" />
              <p className="text-foreground text-sm font-medium">All Systems Normal</p>
              <p className="text-muted-foreground text-xs mt-1">No active alerts</p>
            </div>
          )}
        </div>
      </div>

      {/* Service Status */}
      <div className="bg-card border border-border rounded-2xl p-5">
        <h3 className="text-foreground text-sm font-semibold mb-4">Service Status</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { name: 'FastAPI Backend', status: 'operational', latency: '12ms' },
            { name: 'Groq Inference', status: 'operational', latency: `${metrics?.inference_time || 0}ms` },
            { name: 'PostgreSQL', status: 'operational', latency: '4ms' },
            { name: 'Redis Queue', status: 'operational', latency: '2ms' },
            { name: 'Celery Workers', status: 'operational', latency: '—' },
            { name: 'PII Redaction', status: 'operational', latency: '8ms' },
            { name: 'Export Pipeline', status: 'operational', latency: '120ms' },
            { name: 'WebSocket Stream', status: 'operational', latency: '18ms' },
          ].map(svc => (
            <div key={svc.name} className="flex items-center gap-3 p-3 bg-secondary/50 rounded-xl">
              <span className={cn(
                'size-2 rounded-full flex-shrink-0',
                svc.status === 'operational' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'
              )} />
              <div className="min-w-0">
                <p className="text-xs text-foreground truncate">{svc.name}</p>
                <p className="text-xs text-muted-foreground">{svc.latency}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}