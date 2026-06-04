import { useNavigate } from 'react-router';
import {
  Phone, Users, TrendingUp, Clock, AlertTriangle, Shield, Zap, Target,
  ArrowUpRight, ArrowDownRight, Flame, Thermometer, Snowflake, Activity,
  ChevronRight, CheckCircle, XCircle
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { useApp } from '../context/AppContext';
import { useDashboard } from '../hooks/useDashboard';
import { useCalls } from '../hooks/useCalls';
import { useLeads } from '../hooks/useLeads';
import { useSystemMetrics } from '../hooks/useSystemHealth';
import { cn } from '../components/ui/utils';
import { Skeleton } from '../components/ui/skeleton';
import { EmptyState } from '../components/ui/states';
import { Call } from '../lib/types';

const kpiColors: Record<string, { bg: string; icon: string }> = {
  indigo: { bg: 'rgba(99,102,241,0.12)', icon: '#818cf8' },
  emerald: { bg: 'rgba(16,185,129,0.12)', icon: '#34d399' },
  cyan: { bg: 'rgba(6,182,212,0.12)', icon: '#22d3ee' },
  amber: { bg: 'rgba(245,158,11,0.12)', icon: '#fbbf24' },
  violet: { bg: 'rgba(139,92,246,0.12)', icon: '#a78bfa' },
  pink: { bg: 'rgba(236,72,153,0.12)', icon: '#f472b6' },
  red: { bg: 'rgba(239,68,68,0.12)', icon: '#f87171' },
  blue: { bg: 'rgba(56,189,248,0.12)', icon: '#38bdf8' },
};

const KPICard = ({ label, value, sub, icon: Icon, trend, color, onClick }: {
  label: string; value: string; sub?: string; icon: any; trend?: number; color: string; onClick?: () => void;
}) => (
  <div 
    onClick={onClick}
    className={cn(
      "bg-card border border-border rounded-xl p-4 flex flex-col gap-3 transition-all",
      onClick ? "cursor-pointer hover:border-border" : ""
    )}
  >
    <div className="flex items-start justify-between">
      <div className="size-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: kpiColors[color]?.bg }}>
        <Icon size={18} style={{ color: kpiColors[color]?.icon }} />
      </div>
      {trend !== undefined && (
        <div className={cn('flex items-center gap-1 text-xs', trend >= 0 ? 'text-emerald-400' : 'text-red-400')}>
          {trend >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
          {Math.abs(trend)}%
        </div>
      )}
    </div>
    <div className="flex items-end justify-between">
      <div>
        <p className="text-foreground text-xl font-semibold">{value}</p>
        <p className="text-muted-foreground text-xs mt-0.5">{label}</p>
        {sub && <p className="text-muted-foreground text-xs mt-0.5">{sub}</p>}
      </div>
      {onClick && <ChevronRight size={14} className="text-muted-foreground group-hover:text-primary" />}
    </div>
  </div>
);

const leadConfig = {
  hot: { icon: Flame, color: 'red', label: 'Hot Lead' },
  warm: { icon: Thermometer, color: 'amber', label: 'Warm Lead' },
  cold: { icon: Snowflake, color: 'blue', label: 'Cold Lead' },
};

const alertSeverityConfig = {
  critical: { color: 'red', dot: 'bg-red-500' },
  warning: { color: 'amber', dot: 'bg-amber-500' },
  info: { color: 'blue', dot: 'bg-blue-500' },
};

export function Dashboard() {
  const { userRole } = useApp();
  const navigate = useNavigate();
  const isAdmin = userRole === 'admin';
  const canSeeQueueDepth = userRole === 'admin' || userRole === 'hr_manager' || userRole === 'qa';

  const { data: dashboard, isLoading: kpisLoading, dataUpdatedAt } = useDashboard();
  const { data: recentCalls, isLoading: callsLoading } = useCalls({ limit: 5 } as any);
  const { data: leads } = useLeads();
  const { data: systemMetrics } = useSystemMetrics();

  // Fallback for safety
  const kpis = dashboard || {
    total_calls_today: 0,
    avg_qa_score: 0,
    queue_depth: 0,
    pass_rate: 0,
    weekly_trend: [],
    campaign_performance: []
  };

  const hotLeads = (leads || []).filter(l => l.lead_status === 'hot').slice(0, 3);

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      {/* Role banner */}
      {userRole === 'qa' && (
        <div className="flex items-center gap-3 px-4 py-3 bg-emerald-500/8 border border-emerald-500/20 rounded-xl">
          <Shield size={16} className="text-emerald-400" />
          <span className="text-emerald-300 text-sm">QA View Active — Business intelligence metrics are restricted per your access level.</span>
        </div>
      )}

      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpisLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl bg-secondary" />)
        ) : (
          <>
            <KPICard label="Calls Today" value={kpis.total_calls_today.toString()} sub="Total since midnight" icon={Phone} color="indigo" />
            <KPICard label="Avg QA Score" value={`${kpis.avg_qa_score}`} sub="Out of 100 pts" icon={Target} color="emerald" />
            <KPICard label="Pass Rate" value={`${kpis.pass_rate}%`} sub="Score >= 70" icon={CheckCircle} color="violet" />
            {canSeeQueueDepth ? (
              <KPICard 
                label="Queue Depth" 
                value={kpis.queue_depth.toString()} 
                sub="Pending/Processing" 
                icon={Clock} 
                color="amber" 
                onClick={isAdmin ? () => navigate('/system-health') : undefined}
              />
            ) : (
              <KPICard label="FCR Rate" value="--" sub="First call resolution" icon={TrendingUp} color="cyan" />
            )}
          </>
        )}
      </div>

      {/* Second row of KPIs (Simplified for now) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard label="PII Redactions" value="--" sub="Feature pending" icon={Shield} color="emerald" />
        <KPICard label="Escalation Rate" value="--" sub="Calls escalated" icon={TrendingUp} color="amber" />
        <KPICard label="Avg Handle Time" value="--" sub="Per call" icon={Clock} color="pink" />
        <KPICard 
          label="System Health" 
          value="Stable" 
          sub="API Online" 
          icon={Activity} 
          color="blue" 
          onClick={isAdmin ? () => navigate('/system-health') : undefined}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weekly trend chart */}
        <div className="lg:col-span-2 bg-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-foreground text-sm font-semibold">Weekly Call Volume & QA Score</h3>
            <span className="text-xs text-muted-foreground">Last 5 days</span>
          </div>
          {kpisLoading ? (
            <Skeleton className="w-full h-[200px] bg-secondary rounded-lg" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={kpis.weekly_trend} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis yAxisId="calls" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis yAxisId="score" orientation="right" domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }} />
                <Bar yAxisId="calls" dataKey="calls" fill="#6366f1" radius={[4, 4, 0, 0]} opacity={0.8} />
                <Line yAxisId="score" type="monotone" dataKey="score" stroke="#10b981" strokeWidth={2} dot={{ fill: '#10b981', r: 4 }} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Campaign performance */}
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="text-foreground text-sm font-semibold mb-4">Campaign Performance</h3>
          <div className="space-y-3">
            {kpisLoading ? (
              Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 w-full bg-secondary rounded-lg" />)
            ) : kpis.campaign_performance.length > 0 ? (
              kpis.campaign_performance.map((c, i) => (
                <div key={i}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-foreground">{c.name}</span>
                    <span className="text-xs text-muted-foreground">{c.score}/100</span>
                  </div>
                  <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${c.score}%`,
                        backgroundColor: c.score >= 80 ? '#10b981' : c.score >= 70 ? '#f59e0b' : '#ef4444'
                      }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{c.calls} calls</p>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground text-xs text-center py-4">No campaign data available</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent calls */}
        <div className="lg:col-span-2 bg-card border border-border rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <h3 className="text-foreground text-sm font-semibold">Recent Completed Calls</h3>
            <button onClick={() => navigate('/calls')} className="text-xs text-primary hover:text-indigo-300 flex items-center gap-1">
              View All <ChevronRight size={12} />
            </button>
          </div>
          <div className="divide-y divide-slate-800">
            {callsLoading ? (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-16 w-full bg-secondary" />)
            ) : recentCalls && recentCalls.length > 0 ? (
              recentCalls.map((call: Call) => {
                const score = call.overridden_score ?? call.evaluation_score ?? 0;
                return (
                  <div
                    key={call.id}
                    onClick={() => navigate(`/calls/${call.id}`)}
                    className="flex items-center gap-4 px-5 py-3 hover:bg-secondary/50 cursor-pointer transition-all"
                  >
                    <div className={cn(
                      'size-8 rounded-lg flex items-center justify-center flex-shrink-0',
                      score >= 85 ? 'bg-emerald-500/15' : score >= 70 ? 'bg-amber-500/15' : 'bg-red-500/15'
                    )}>
                      <Phone size={14} className={score >= 85 ? 'text-emerald-400' : score >= 70 ? 'text-amber-400' : 'text-red-400'} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-foreground font-medium truncate">ID: {call.id} · {call.call_summary || 'No summary'}</p>
                      <p className="text-xs text-muted-foreground">
                        {call.processed_at ? new Date(call.processed_at).toLocaleString() : 'Pending'} · {Math.floor((call.audio_duration || 0) / 60)}m {(call.audio_duration || 0) % 60}s
                      </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {isAdminOrManager && call.lead_status && (
                        <span className={cn(
                          'text-xs px-2 py-0.5 rounded-full capitalize',
                          call.lead_status === 'hot' ? 'bg-red-500/15 text-red-400' :
                          call.lead_status === 'warm' ? 'bg-amber-500/15 text-amber-400' : 'bg-blue-500/15 text-blue-400'
                        )}>
                          {call.lead_status}
                        </span>
                      )}
                      <span className={cn(
                        'text-xs font-semibold px-2 py-0.5 rounded-lg',
                        score >= 85 ? 'text-emerald-400 bg-emerald-500/10' :
                        score >= 70 ? 'text-amber-400 bg-amber-500/10' : 'text-red-400 bg-red-500/10'
                      )}>
                        {score || 'N/A'}
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <EmptyState
                icon={Phone}
                title="No recent calls"
                description="Processed calls will appear here once available."
                className="py-8"
              />
            )}
          </div>
        </div>

        {/* Right column: Leads (admin) + Alerts */}
        <div className="space-y-4">
          {/* Lead Status - Admin/Manager only */}
          {isAdminOrManager && (
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-foreground text-sm font-semibold">Hot Leads</h3>
                <button onClick={() => navigate('/intelligence')} className="text-xs text-primary">View All</button>
              </div>
              <div className="space-y-2">
                {hotLeads.length > 0 ? hotLeads.map(lead => {
                  const score = lead.overridden_score ?? lead.evaluation_score ?? 0;
                  const value = (score / 100) * 10000;
                  return (
                    <div key={lead.id} className="flex items-center gap-3 p-2.5 bg-red-500/5 border border-red-500/15 rounded-lg">
                      <Flame size={14} className="text-red-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-foreground font-medium truncate">Call #{lead.id}</p>
                        <p className="text-xs text-muted-foreground truncate">{(lead.call_summary || 'No summary available').slice(0, 35)}...</p>
                      </div>
                      <span className="text-xs text-emerald-400 font-semibold flex-shrink-0">${(value / 1000).toFixed(1)}K</span>
                    </div>
                  );
                }) : (
                  <p className="text-muted-foreground text-xs text-center py-2 italic">No hot leads detected</p>
                )}
              </div>
            </div>
          )}

          {/* Active Alerts (Placeholder for now) */}
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-foreground text-sm font-semibold">Active Alerts</h3>
              {isAdmin && <button onClick={() => navigate('/system-health')} className="text-xs text-primary">View All</button>}
            </div>
            <div className="space-y-2 text-center py-4">
              <p className="text-muted-foreground text-xs">All systems operational</p>
            </div>
          </div>

          {/* Inference Dashboard (Placeholder for now) */}
          {isAdmin && (
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-foreground text-sm font-semibold">Inference Status</h3>
                <button onClick={() => navigate('/system-health')} className="text-xs text-primary hover:text-indigo-300">View Details</button>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Latency',  value: systemMetrics ? `${Math.round(systemMetrics.inference_time)}ms` : '—' },
                  { label: 'GPU Load', value: systemMetrics ? `${Math.round(systemMetrics.gpu_load)}%`      : '—' },
                  { label: 'CPU Load', value: systemMetrics ? `${Math.round(systemMetrics.cpu_load)}%`      : '—' },
                  { label: 'Queue',    value: systemMetrics ? `${systemMetrics.queue_depth}`               : '—' },
                ].map(m => (
                  <div key={m.label} className="bg-secondary/50 rounded-lg p-2.5">
                    <p className="text-foreground text-sm font-semibold">{m.value}</p>
                    <p className="text-muted-foreground text-xs">{m.label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Footer / Status */}
      <div className="flex items-center justify-between pt-4 border-t border-border/50 mt-4">
        <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold">Enterprise Deep Tech v1.0.4</p>
        <div className="flex items-center gap-2">
          <span className="size-1.5 bg-emerald-500 rounded-full animate-pulse" />
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold">
            Live Sync Active · Last Updated: {new Date(dataUpdatedAt).toLocaleTimeString()}
          </p>
        </div>
      </div>
    </div>
  );
}
