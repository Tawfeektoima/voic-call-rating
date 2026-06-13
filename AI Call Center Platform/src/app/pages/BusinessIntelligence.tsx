import { useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Flame, Thermometer, Snowflake, DollarSign, Phone, TrendingUp,
  ChevronRight, BarChart3, Users, Trophy, ArrowUpRight, Target
} from 'lucide-react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, Cell
} from 'recharts';
import { useApp } from '../context/AppContext';
import { useLeads } from '../hooks/useLeads';
import { useRanking } from '../hooks/useRanking';
import { useCommonErrors } from '../hooks/useCommonErrors';
import { useAgents } from '../hooks/useAgents';
import { updateLeadStatus } from '../lib/api';
import { Agent, Call } from '../lib/types';
import { cn } from '../components/ui/utils';
import { Skeleton } from '../components/ui/skeleton';
import { buildNotesComposeUrl } from '../lib/noteNavigation';

const leadConfig = {
  hot: { icon: Flame, color: '#ef4444', bg: 'bg-red-500/10', border: 'border-red-500/20', text: 'text-red-400', label: 'Hot' },
  warm: { icon: Thermometer, color: '#f59e0b', bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-400', label: 'Warm' },
  cold: { icon: Snowflake, color: '#3b82f6', bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-400', label: 'Cold' },
};

const tierColors = { platinum: '#e2e8f0', gold: '#fbbf24', silver: '#94a3b8', bronze: '#cd7f32' };
const tierBg = { platinum: 'bg-slate-300/10', gold: 'bg-amber-500/10', silver: 'bg-slate-400/10', bronze: 'bg-orange-700/10' };

function AgentRadar({ agent }: { agent: Agent }) {
  const navigate = useNavigate();
  const skills = agent.skills || {};
  const data = [
    { skill: 'Empathy', value: skills.empathy || 0 },
    { skill: 'Resolution', value: skills.resolution || 0 },
    { skill: 'Comm.', value: skills.communication || 0 },
    { skill: 'Product', value: skills.productKnowledge || 0 },
    { skill: 'Compliance', value: skills.compliance || 0 },
    { skill: 'Control', value: skills.callControl || 0 },
  ];
  const avgScore = agent.avg_score || 0;
  const scoreColor = avgScore >= 85 ? '#10b981' : avgScore >= 70 ? '#f59e0b' : '#ef4444';
  const tier = (agent.tier?.toLowerCase() || 'bronze') as keyof typeof tierColors;

  return (
    <div
      onClick={() => navigate(`/agents/${agent.id}`)}
      className="bg-card border border-border hover:border-border rounded-xl p-4 cursor-pointer transition-all group"
    >
      {/* Agent header */}
      <div className="flex items-center gap-3 mb-4">
        <div className={cn('size-9 rounded-full flex items-center justify-center text-white text-xs font-bold', tierBg[tier])}>
          <span style={{ color: tierColors[tier] }}>{agent.avatar || agent.name[0]}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-foreground text-xs font-semibold truncate">{agent.name}</p>
          <p className="text-muted-foreground text-xs">{agent.total_calls || 0} calls · <span className="capitalize">{tier}</span></p>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-sm font-bold" style={{ color: scoreColor }}>{avgScore}</span>
          <ChevronRight size={12} className="text-muted-foreground group-hover:text-primary transition-colors" />
        </div>
      </div>

      {/* Radar */}
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data}>
            <PolarGrid stroke="#1e293b" />
            <PolarAngleAxis dataKey="skill" tick={{ fill: '#64748b', fontSize: 10 }} />
            <Radar dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.15} strokeWidth={2} dot={{ fill: '#6366f1', r: 2 }} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Mini emotion trend */}
      <div className="h-12 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={(agent.emotion_history || []).map((s, i) => ({ week: i, score: s }))}>
            <Line type="monotone" dataKey="score" stroke="#10b981" strokeWidth={1.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-center text-xs text-muted-foreground mt-1">Emotion consistency trend</p>
    </div>
  );
}

export function BusinessIntelligence() {
  const { userRole } = useApp();
  const navigate = useNavigate();
  const isAdmin = userRole === 'admin';
  const [activeLeadFilter, setActiveLeadFilter] = useState<'all' | 'hot' | 'warm' | 'cold'>('all');
  const openNoteLauncher = (params: Record<string, string | number | undefined>) => {
    navigate(buildNotesComposeUrl(params));
  };

  const { data: leads, isLoading: leadsLoading, refetch: refetchLeads } = useLeads();
  const { data: ranking, isLoading: rankingLoading } = useRanking();
  const { data: commonErrors, isLoading: errorsLoading } = useCommonErrors(5);
  const { data: agents, isLoading: agentsLoading } = useAgents();

  const filteredLeads = !leads ? [] : activeLeadFilter === 'all' ? leads : leads.filter(l => l.lead_status === activeLeadFilter);
  
  // --- Dynamic KPIs ---
  // Sales Conversion Rate
  const salesCalls = leads?.filter(l => l.outcome?.campaign_type === 'sales') || [];
  const salesClosedCount = salesCalls.filter(l => l.outcome?.primary_outcome === 'Sale Closed').length;
  const salesConversionRate = salesCalls.length > 0 ? (salesClosedCount / salesCalls.length) * 100 : 0;

  // Collections PTP Rate
  const collectionsCalls = leads?.filter(l => l.outcome?.campaign_type === 'collections') || [];
  const ptpCount = collectionsCalls.filter(l => l.outcome?.primary_outcome === 'Promise to Pay').length;
  const ptpRate = collectionsCalls.length > 0 ? (ptpCount / collectionsCalls.length) * 100 : 0;

  // Revenue Tracking
  const totalValueGenerated = leads?.reduce((s, l) => s + (l.outcome?.outcome_value || 0), 0) || 0;

  // Talk Ratio Leaderboard
  // Target talk ratio is 40% (0.4) for Sales
  const talkRatioData = agents?.map(a => {
    const agentCalls = leads?.filter(l => l.employee_id === a.id && l.outcome?.talk_ratio != null) || [];
    if (agentCalls.length === 0) return null;
    const avgRatio = agentCalls.reduce((s, l) => s + (l.outcome!.talk_ratio || 0), 0) / agentCalls.length;
    const distanceToTarget = Math.abs(0.4 - avgRatio);
    return { name: a.name.split(' ')[0], ratio: avgRatio * 100, distance: distanceToTarget };
  }).filter(Boolean).sort((a, b) => a!.distance - b!.distance) || [];

  // Used for Lead Status Tracker values (fallback if no outcome value)
  const calculateValue = (l: Call) => l.outcome?.outcome_value || 0;

  const performanceData = (ranking || []).map(r => ({
    name: r.employee_name.split(' ')[0],
    score: r.avg_score,
    calls: r.total_calls,
  }));

  const handleStatusUpdate = async (callId: number, status: string) => {
    try {
      await updateLeadStatus(callId, status);
      refetchLeads();
    } catch (err) {
      console.error('Failed to update lead status:', err);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <p className="text-muted-foreground text-xs">Business performance metrics and agent intelligence</p>

      {/* BI Summary KPIs - Admin only note for financials */}
      <div className={cn("grid gap-4", isAdmin ? "grid-cols-2 md:grid-cols-5" : "grid-cols-2 md:grid-cols-4")}>
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Users size={16} className="text-primary" />
            <span className="text-xs text-muted-foreground">Total Agents</span>
          </div>
          {agentsLoading ? <Skeleton className="h-6 w-12 bg-secondary" /> : <p className="text-foreground text-xl font-semibold">{agents?.length || 0}</p>}
          <p className="text-xs text-muted-foreground mt-1">Active staff</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Trophy size={16} className="text-amber-400" />
            <span className="text-xs text-muted-foreground">Top Performer</span>
          </div>
          {rankingLoading ? <Skeleton className="h-6 w-24 bg-secondary" /> : (
            <>
              <p className="text-foreground text-sm font-semibold">{performanceData[0]?.name || 'N/A'}</p>
              <p className="text-xs text-amber-400 mt-1">{performanceData[0]?.score || 0} avg score</p>
            </>
          )}
        </div>

        {/* Admin-only: financials */}
        {isAdmin ? (
          <>
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign size={16} className="text-emerald-400" />
                <span className="text-xs text-muted-foreground">Total Value Generated</span>
              </div>
              <p className="text-foreground text-xl font-semibold">${totalValueGenerated.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground mt-1">From resolved outcomes</p>
              <button
                onClick={() => openNoteLauncher({ noteType: 'KPI_ALERT', kpiKey: 'total_revenue', kpiLabel: 'Total Revenue', currentValue: totalValueGenerated, title: 'Total Revenue KPI alert' })}
                className="mt-3 text-xs text-primary hover:text-indigo-300 inline-flex items-center gap-1"
              >
                Send KPI alert <ArrowUpRight size={12} />
              </button>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Target size={16} className="text-indigo-400" />
                <span className="text-xs text-muted-foreground">Sales Conversion</span>
              </div>
              <p className="text-foreground text-xl font-semibold">{salesConversionRate.toFixed(1)}%</p>
              <p className="text-xs text-muted-foreground mt-1">{salesClosedCount} / {salesCalls.length} Sales</p>
              <button
                onClick={() => openNoteLauncher({ noteType: 'KPI_ALERT', kpiKey: 'conversion_rate', kpiLabel: 'Conversion Rate', currentValue: Number(salesConversionRate.toFixed(1)), title: 'Conversion Rate KPI alert' })}
                className="mt-3 text-xs text-primary hover:text-indigo-300 inline-flex items-center gap-1"
              >
                Send KPI alert <ArrowUpRight size={12} />
              </button>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Phone size={16} className="text-amber-400" />
                <span className="text-xs text-muted-foreground">PTP Rate</span>
              </div>
              <p className="text-foreground text-xl font-semibold">{ptpRate.toFixed(1)}%</p>
              <p className="text-xs text-muted-foreground mt-1">{ptpCount} / {collectionsCalls.length} Collections</p>
            </div>
          </>
        ) : (
          <>
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp size={16} className="text-cyan-400" />
                <span className="text-xs text-muted-foreground">Avg Team Score</span>
              </div>
              <p className="text-foreground text-xl font-semibold">80.9</p>
              <p className="text-xs text-emerald-400 mt-1">↑ +2.3 this week</p>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Phone size={16} className="text-violet-400" />
                <span className="text-xs text-muted-foreground">Total Calls</span>
              </div>
              <p className="text-foreground text-xl font-semibold">1,396</p>
              <p className="text-xs text-muted-foreground mt-1">This month</p>
            </div>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lead Status Tracker - Admin/Manager only */}
        {isAdmin && (
          <div className="lg:col-span-1 bg-card border border-border rounded-xl overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h3 className="text-foreground text-sm font-semibold">Lead Status Tracker</h3>
              <div className="flex items-center gap-1">
                {(['all', 'hot', 'warm', 'cold'] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => setActiveLeadFilter(f)}
                    className={cn(
                      'px-2 py-0.5 rounded text-xs transition-all capitalize',
                      activeLeadFilter === f ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-foreground'
                    )}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
            <div className="divide-y divide-slate-800 overflow-y-auto max-h-[400px]">
              {leadsLoading ? (
                Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 w-full bg-secondary" />)
              ) : filteredLeads.length > 0 ? (
                filteredLeads.map(lead => {
                  const status = (lead.lead_status || 'cold') as keyof typeof leadConfig;
                  const lc = leadConfig[status];
                  const score = lead.overridden_score ?? lead.evaluation_score ?? 0;
                  const value = calculateValue(lead);
                  return (
                    <div key={lead.id} className={cn('p-4 hover:bg-secondary/40 transition-all', lc.bg)}>
                      <div className="flex items-start gap-3">
                        <lc.icon size={16} style={{ color: lc.color }} className="flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <p className="text-xs text-foreground font-medium">Call #{lead.id}</p>
                            {value > 0 && (
                              <span className="text-xs text-emerald-400 font-semibold">${(value / 1000).toFixed(1)}K</span>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5">{new Date(lead.created_at).toLocaleDateString()}</p>
                          <p className="text-xs text-muted-foreground mt-1 leading-relaxed line-clamp-2">{lead.call_summary || 'No summary available'}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mt-2 ml-7">
                        <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${score}%`, backgroundColor: lc.color }} />
                        </div>
                        <span className="text-xs font-semibold" style={{ color: lc.color }}>{score}</span>
                      </div>
                      <div className="flex items-center gap-1.5 mt-3 ml-7">
                        {(['hot', 'warm', 'cold'] as const).map(s => (
                          <button
                            key={s}
                            onClick={() => handleStatusUpdate(lead.id, s)}
                            className={cn(
                              'text-[10px] px-2 py-0.5 rounded border capitalize transition-all',
                              lead.lead_status === s 
                                ? 'bg-secondary border-border text-foreground' 
                                : 'border-transparent text-muted-foreground hover:text-muted-foreground'
                            )}
                          >
                            {s}
                          </button>
                        ))}
                        <button 
                          onClick={() => navigate(`/calls/${lead.id}`)}
                          className="ml-auto text-[10px] text-primary flex items-center gap-0.5"
                        >
                          Details <ChevronRight size={10} />
                        </button>
                        <button
                          onClick={() => openNoteLauncher({
                            noteType: 'GENERAL',
                            callId: lead.id,
                            employeeId: lead.employee_id,
                            title: `Lead follow-up for call #${lead.id}`,
                          })}
                          className="text-[10px] text-primary flex items-center gap-0.5"
                        >
                          Note <ArrowUpRight size={10} />
                        </button>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-10 text-center text-muted-foreground text-xs">No leads found for this filter</div>
              )}
            </div>
          </div>
        )}

        {/* Agent Performance Bar Chart */}
        <div className={cn('bg-card border border-border rounded-xl p-5', isAdmin ? 'lg:col-span-1' : 'lg:col-span-2')}>
          <h3 className="text-foreground text-sm font-semibold mb-4">Agent Performance Leaderboard</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={performanceData} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} width={60} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }} />
              <Bar dataKey="score" radius={[0, 6, 6, 0]}>
                {performanceData.map((entry, i) => (
                  <Cell key={i} fill={entry.score >= 85 ? '#10b981' : entry.score >= 70 ? '#f59e0b' : '#ef4444'} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Talk Ratio Leaderboard */}
        <div className="bg-card border border-border rounded-xl p-5 lg:col-span-1">
          <h3 className="text-foreground text-sm font-semibold mb-4">Talk Ratio (Target 40%)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={talkRatioData} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} width={60} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }} />
              <Bar dataKey="ratio" radius={[0, 6, 6, 0]}>
                {talkRatioData.map((entry, i) => {
                  const diff = Math.abs(40 - entry.ratio!);
                  const color = diff <= 5 ? '#10b981' : diff <= 15 ? '#f59e0b' : '#ef4444';
                  return <Cell key={i} fill={color} fillOpacity={0.85} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Agent Radar Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-foreground text-sm font-semibold">Agent Momentum Profiles</h3>
          <button onClick={() => navigate('/agents/1')} className="text-xs text-primary hover:text-indigo-300 flex items-center gap-1">
            Full Profiles <ChevronRight size={12} />
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
          {agentsLoading ? (
            Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-64 rounded-xl bg-secondary" />)
          ) : agents && agents.length > 0 ? (
            agents.map(agent => (
              <AgentRadar key={agent.id} agent={agent} />
            ))
          ) : (
            <div className="col-span-full py-10 text-center text-muted-foreground text-xs">No agents found</div>
          )}
        </div>
      </div>
    </div>
  );
}
