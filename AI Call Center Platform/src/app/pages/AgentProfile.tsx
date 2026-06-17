import { useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import {
  ChevronLeft, Phone, Target, TrendingUp, Star, Award,
  ChevronRight, Mail, Users, MessageSquarePlus
} from 'lucide-react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, AreaChart, Area, BarChart, Bar
} from 'recharts';
import { useApp } from '../context/AppContext';
import { useMyPerformance } from '../hooks/useMyPerformance';
import { useAgentDetails } from '../hooks/useAgentDetails';
import { useAgents } from '../hooks/useAgents';
import { useCalls } from '../hooks/useCalls';
import { cn } from '../components/ui/utils';
import { Agent, Call } from '../lib/types';
import { Skeleton } from '../components/ui/skeleton';
import { buildNotesComposeUrl } from '../lib/noteNavigation';

const tierConfig = {
  platinum: { color: '#e2e8f0', bg: 'bg-slate-300/10 border-slate-300/20', label: 'Platinum', stars: 4 },
  gold: { color: '#fbbf24', bg: 'bg-amber-500/10 border-amber-500/20', label: 'Gold', stars: 3 },
  silver: { color: '#94a3b8', bg: 'bg-slate-400/10 border-slate-400/20', label: 'Silver', stars: 2 },
  bronze: { color: '#cd7f32', bg: 'bg-orange-700/10 border-orange-700/20', label: 'Bronze', stars: 1 },
};

export function AgentProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { userRole, currentUser } = useApp();
  const canCreateCoachingNote = ['admin', 'qa', 'hr_manager', 'team_leader'].includes(userRole);
  const canCreateCoachingEscalation = ['admin', 'qa', 'hr_manager', 'team_manager'].includes(userRole);
  
  // For agents, always show their own profile. For others, allow switching via ID.
  const employeeId = (userRole === 'agent' || id === 'me') ? currentUser?.id : (id ? parseInt(id) : currentUser?.id);
  
  const { data: performance, isLoading: perfLoading } = useMyPerformance(employeeId);
  const { data: agent, isLoading: agentLoading } = useAgentDetails(employeeId);
  const { data: allAgents } = useAgents();
  const { data: recentCalls, isLoading: callsLoading } = useCalls(
    { employee_code: agent?.employee_code },
    { enabled: !!agent?.employee_code }
  );

  if (agentLoading || perfLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-10 w-48 bg-secondary rounded-lg" />
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <Skeleton className="h-[500px] bg-card rounded-2xl" />
          <div className="lg:col-span-3 space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <Skeleton className="h-[300px] bg-card rounded-2xl" />
              <Skeleton className="h-[300px] bg-card rounded-2xl" />
            </div>
            <Skeleton className="h-[300px] bg-card rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  if (!agent) {
    return <div className="p-10 text-center text-muted-foreground">Agent not found</div>;
  }

  const avgScore = performance?.avg_score ?? 0;
  const totalCallsCount = performance?.total_calls ?? 0;
  const rank = performance?.rank ?? "N/A";
  const skills = (performance?.skills_matrix ?? agent.skills) || {};
  const backPath = userRole === 'agent' ? '/' : '/intelligence';

  const tc = (tierConfig as any)[agent.tier?.toLowerCase()] || tierConfig.bronze;
  const scoreColor = avgScore >= 85 ? '#10b981' : avgScore >= 70 ? '#f59e0b' : '#ef4444';

  const mastery = performance?.cumulative_stats;
  const openAgentNote = (noteType: string, title: string) => {
    navigate(buildNotesComposeUrl({
      noteType,
      employeeId: String(agent.id),
      title,
    }));
  };
  
  const radarData = [
    { skill: 'Rapport Building', A: mastery?.rapport_building ?? 80, fullMark: 100 },
    { skill: 'Emotional Sync', A: mastery?.emotional_sync ?? 85, fullMark: 100 },
    { skill: 'Ownership & Trust', A: mastery?.ownership_trust ?? 75, fullMark: 100 },
    { skill: 'Process Clarity', A: mastery?.process_clarity ?? 90, fullMark: 100 },
  ];

  const skillEntries = Object.entries(skills) as [string, number][];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(backPath)} className="size-8 flex items-center justify-center rounded-lg bg-secondary text-muted-foreground hover:text-foreground transition-all">
          <ChevronLeft size={16} />
        </button>
        {(canCreateCoachingNote || canCreateCoachingEscalation) && (
          <div className="flex items-center gap-2 ml-auto">
            {canCreateCoachingNote && (
              <button
                onClick={() => openAgentNote('COACHING_NOTE', `Coaching note for ${agent.name}`)}
                className="h-9 px-3 rounded-lg border border-border bg-card text-sm text-foreground hover:bg-secondary/30 transition-colors"
              >
                Coaching Note
              </button>
            )}
            {canCreateCoachingEscalation && (
              <button
                onClick={() => openAgentNote('COACHING_ESCALATION', `Coaching escalation for ${agent.name}`)}
                className="h-9 px-3 rounded-lg bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors inline-flex items-center gap-2"
              >
                <MessageSquarePlus size={14} />
                Escalate
              </button>
            )}
          </div>
        )}

        {/* Agent Switcher (Hidden for Agents) */}
        {userRole !== 'agent' && allAgents && (
          <div className="flex items-center gap-2 bg-card border border-border rounded-xl p-1 overflow-x-auto max-w-md">
            {allAgents.map(a => (
              <button
                key={a.id}
                onClick={() => navigate(`/agents/${a.id}`)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs whitespace-nowrap transition-all',
                  employeeId === a.id ? 'bg-primary/20 text-indigo-300' : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {a.name.split(' ')[0]}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Agent Card */}
        <div className="lg:col-span-1 space-y-4">
          <div className={cn('bg-card border rounded-2xl p-5', tc.bg)}>
            <div className="flex flex-col items-center text-center">
              <div
                className="size-16 rounded-2xl flex items-center justify-center text-white text-xl font-bold mb-3"
                style={{ backgroundColor: tc.color + '20', color: tc.color }}
              >
                {agent.avatar || agent.name.split(' ').map(n => n[0]).join('')}
              </div>
              <h2 className="text-slate-100 text-sm font-semibold">{agent.name}</h2>
              <p className="text-muted-foreground text-xs mt-0.5">{agent.email}</p>

              <div className="flex items-center gap-1 mt-2">
                {Array.from({ length: tc.stars }).map((_, i) => (
                  <Star key={i} size={12} className="fill-current" style={{ color: tc.color }} />
                ))}
                <span className="text-xs ml-1" style={{ color: tc.color }}>{tc.label}</span>
              </div>

              <div className="w-full mt-4 p-3 bg-secondary/50 rounded-xl">
                <p className="text-2xl font-bold" style={{ color: scoreColor }}>{avgScore}</p>
                <p className="text-muted-foreground text-xs">Average QA Score</p>
              </div>
            </div>

            <div className="mt-4 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Ranking</span>
                <span className="text-primary font-semibold">{rank}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Calls Handled</span>
                <span className="text-foreground">{totalCallsCount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Department</span>
                <span className="text-foreground">{agent.department || 'N/A'}</span>
              </div>
            </div>
          </div>

          {/* Skill bars */}
          <div className="bg-card border border-border rounded-2xl p-4">
            <h3 className="text-foreground text-xs font-semibold mb-3">Skill Breakdown</h3>
            <div className="space-y-2.5">
              {skillEntries.map(([skill, val]) => {
                const sColor = val >= 85 ? '#10b981' : val >= 70 ? '#f59e0b' : '#ef4444';
                return (
                  <div key={skill}>
                    <div className="flex justify-between mb-1">
                      <span className="text-xs text-muted-foreground capitalize">{skill.replace(/([A-Z])/g, ' $1').trim()}</span>
                      <span className="text-xs font-semibold" style={{ color: sColor }}>{val}</span>
                    </div>
                    <div className="h-1 bg-secondary rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${val}%`, backgroundColor: sColor }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-card border border-border rounded-2xl p-4">
            <h3 className="text-foreground text-xs font-semibold mb-3">Personal Details</h3>
            <div className="space-y-3">
              <ProfileDetail icon={Mail} label="Company Email" value={agent.email || 'N/A'} />
              <ProfileDetail icon={Mail} label="Personal Email" value={agent.otp_email || 'N/A'} />
              <ProfileDetail icon={Phone} label="Phone Number" value={agent.phone_number || 'N/A'} />
              <ProfileDetail icon={Users} label="Employee Code" value={agent.employee_code || 'N/A'} />
              <ProfileDetail icon={Target} label="Department" value={agent.department || 'N/A'} />
              <ProfileDetail icon={Award} label="Role" value={(agent.role || 'AGENT').replaceAll('_', ' ')} />
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="lg:col-span-3 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Radar Chart */}
            <div className="bg-card border border-border rounded-2xl p-5">
              <h3 className="text-foreground text-sm font-semibold mb-2">Skill Mastery Radar</h3>
              <p className="text-muted-foreground text-xs mb-4">Multidimensional performance profile</p>
              <ResponsiveContainer width="100%" height={240}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#1e293b" />
                  <PolarAngleAxis dataKey="skill" tick={{ fill: '#64748b', fontSize: 10 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#475569', fontSize: 9 }} />
                  <Radar
                    name={agent.name}
                    dataKey="A"
                    stroke="#6366f1"
                    fill="#6366f1"
                    fillOpacity={0.2}
                    strokeWidth={2}
                    dot={{ fill: '#6366f1', r: 3 }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Emotion Consistency */}
            <div className="bg-card border border-border rounded-2xl p-5">
              <h3 className="text-foreground text-sm font-semibold mb-2">Emotional Consistency</h3>
              <p className="text-muted-foreground text-xs mb-4">Historical composure trend</p>
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={(agent.emotion_history || []).map((score, i) => ({ week: `W${i+1}`, score }))}>
                  <defs>
                    <linearGradient id="emotionGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="week" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }} />
                  <Area type="monotone" dataKey="score" stroke="#10b981" strokeWidth={2} fill="url(#emotionGrad)" dot={{ fill: '#10b981', r: 4 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Recent Calls */}
          <div className="bg-card border border-border rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h3 className="text-foreground text-sm font-semibold">Recent Calls</h3>
              <span className="text-xs text-muted-foreground">{recentCalls?.length || 0} calls</span>
            </div>
            {recentCalls && recentCalls.length > 0 ? (
              <div className="divide-y divide-slate-800">
                {recentCalls.map((call: Call) => (
                  <div
                    key={call.id}
                    onClick={() => navigate(`/calls/${call.id}`)}
                    className="flex items-center gap-4 px-5 py-3 hover:bg-secondary/50 cursor-pointer transition-all"
                  >
                    <div className={cn(
                      'size-8 rounded-lg flex items-center justify-center',
                      (call.overridden_score ?? call.evaluation_score ?? 0) >= 85 ? 'bg-emerald-500/15' : (call.overridden_score ?? call.evaluation_score ?? 0) >= 70 ? 'bg-amber-500/15' : 'bg-red-500/15'
                    )}>
                      <Phone size={13} className={(call.overridden_score ?? call.evaluation_score ?? 0) >= 85 ? 'text-emerald-400' : (call.overridden_score ?? call.evaluation_score ?? 0) >= 70 ? 'text-amber-400' : 'text-red-400'} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-foreground font-medium truncate">{call.call_summary || 'No summary available'}</p>
                      <p className="text-xs text-muted-foreground">
                        {call.processed_at ? new Date(call.processed_at).toLocaleString() : 'Pending'} · {Math.floor((call.audio_duration || 0) / 60)}m {(call.audio_duration || 0) % 60}s
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {call.is_golden_moment && <Star size={12} className="text-amber-400 fill-amber-400" />}
                      <span className={cn(
                        'text-xs font-bold px-2 py-0.5 rounded-lg',
                        (call.overridden_score ?? call.evaluation_score ?? 0) >= 85 ? 'text-emerald-400 bg-emerald-500/10' :
                        (call.overridden_score ?? call.evaluation_score ?? 0) >= 70 ? 'text-amber-400 bg-amber-500/10' : 'text-red-400 bg-red-500/10'
                      )}>
                        {call.overridden_score ?? call.evaluation_score ?? 'N/A'}
                      </span>
                      <ChevronRight size={12} className="text-muted-foreground" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="px-5 py-8 text-center">
                <p className="text-muted-foreground text-sm">No recent calls found</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileDetail({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-xl bg-secondary/40 px-3 py-3">
      <div className="mt-0.5 text-primary">
        <Icon size={14} />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] text-muted-foreground">{label}</p>
        <p className="text-xs text-foreground break-words">{value}</p>
      </div>
    </div>
  );
}
