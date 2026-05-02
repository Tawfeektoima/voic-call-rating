import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import {
  Phone, TrendingUp, TrendingDown, Clock, CheckCircle2, AlertTriangle,
  Loader2, XCircle, ArrowRight, Users, Target, Activity, RefreshCw
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import api from '@/app/lib/api';
import { useLang } from '../context/LangContext';
import { formatDuration, getScoreColor, weeklyTrend, topErrorCategories } from '../data/mockData';

const StatusBadge = ({ status }: { status: string }) => {
  const { lang } = useLang();
  const isRtl = lang === 'ar';
  const configs: Record<string, { label: string; labelAr: string; class: string; icon: React.ReactNode }> = {
    EVALUATED: { label: 'Completed', labelAr: 'مكتمل', class: 'bg-green-500/10 text-green-400 border-green-500/20', icon: <CheckCircle2 size={11} /> },
    COMPLETED: { label: 'Completed', labelAr: 'مكتمل', class: 'bg-green-500/10 text-green-400 border-green-500/20', icon: <CheckCircle2 size={11} /> },
    PROCESSING: { label: 'Processing', labelAr: 'جاري المعالجة', class: 'bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse', icon: <Loader2 size={11} className="animate-spin" /> },
    TRANSCRIBED: { label: 'Analyzing', labelAr: 'جاري التحليل', class: 'bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse', icon: <Loader2 size={11} className="animate-spin" /> },
    PENDING: { label: 'Pending', labelAr: 'في الانتظار', class: 'bg-amber-500/10 text-amber-400 border-amber-500/20', icon: <Clock size={11} /> },
    FAILED: { label: 'Failed', labelAr: 'فشل', class: 'bg-red-500/10 text-red-400 border-red-500/20', icon: <XCircle size={11} /> },
  };
  const c = configs[status] || configs.PENDING;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${c.class}`}>
      {c.icon} {isRtl ? c.labelAr : c.label}
    </span>
  );
};

export function Dashboard() {
  const navigate = useNavigate();
  const { lang } = useLang();
  const isRtl = lang === 'ar';
  const t = (en: string, ar: string) => isRtl ? ar : en;

  // --- API Queries ---
  const { data: agents = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const res = await api.get('/admin/employees');
      return res.data;
    }
  });

  const { data: campaigns = [] } = useQuery({
    queryKey: ['campaigns'],
    queryFn: async () => {
      const res = await api.get('/admin/campaigns');
      return res.data;
    }
  });

  const { data: calls = [] } = useQuery({
    queryKey: ['calls'],
    queryFn: async () => {
      const res = await api.get('/analytics/search');
      return res.data.map((c: any) => ({
        ...c,
        date: c.created_at,
        score: c.overridden_score !== null ? c.overridden_score : (c.evaluation_score || 0),
        status: c.status.replace('CallStatus.', '').toUpperCase()
      }));
    }
  });

  const [pulseKey, setPulseKey] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPulseKey(k => k + 1);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const completedCalls = (calls || []).filter((c: any) => c.status === 'COMPLETED' || c.status === 'EVALUATED');
  const avgScore = completedCalls.length > 0 
    ? Math.round(completedCalls.reduce((s, c) => s + (c.score || 0), 0) / completedCalls.length)
    : 0;
  const passRate = completedCalls.length > 0
    ? Math.round(completedCalls.filter(c => (c.score || 0) >= 75).length / completedCalls.length * 100)
    : 0;
  const pendingCount = (calls || []).filter((c: any) => c.status === 'PENDING' || c.status === 'PROCESSING' || c.status === 'TRANSCRIBED').length;
  const failedCount = (calls || []).filter((c: any) => c.status === 'FAILED').length;

  const scoreDistribution = [
    { range: '0-59', count: completedCalls.filter(c => (c.score || 0) < 60).length, color: '#ef4444' },
    { range: '60-69', count: completedCalls.filter(c => (c.score || 0) >= 60 && (c.score || 0) < 70).length, color: '#f97316' },
    { range: '70-79', count: completedCalls.filter(c => (c.score || 0) >= 70 && (c.score || 0) < 80).length, color: '#f59e0b' },
    { range: '80-89', count: completedCalls.filter(c => (c.score || 0) >= 80 && (c.score || 0) < 90).length, color: '#22c55e' },
    { range: '90-100', count: completedCalls.filter(c => (c.score || 0) >= 90).length, color: '#6366f1' },
  ];

  const liveQueue = (calls || []).filter((c: any) => c.status === 'PROCESSING' || c.status === 'PENDING' || c.status === 'TRANSCRIBED').slice(0, 5);
  const recentCalls = completedCalls.slice(0, 6);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload?.length) {
      return (
        <div className="bg-[#1a2235] border border-slate-700/60 rounded-lg px-3 py-2 shadow-xl">
          <p className="text-xs text-slate-400 mb-1">{label}</p>
          {payload.map((p: any, i: number) => (
            <p key={i} className="text-sm font-medium text-white">{p.name}: <span style={{ color: p.color }}>{p.value}{p.name === 'score' ? '' : ''}</span></p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">{t('Quality Assurance Dashboard', 'لوحة تحكم ضمان الجودة')}</h1>
          <p className="text-sm text-slate-500 mt-0.5">{t('Today — Friday, May 1, 2026', 'اليوم — الجمعة، 1 مايو 2026')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors">
            <RefreshCw size={14} />
            {t('Refresh', 'تحديث')}
          </button>
          <button
            onClick={() => navigate('/calls')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
          >
            {t('View All Calls', 'عرض جميع المكالمات')}
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: t('Total Calls Today', 'إجمالي مكالمات اليوم'),
            value: '47',
            icon: Phone,
            color: 'text-indigo-400',
            bg: 'bg-indigo-500/10',
            border: 'border-indigo-500/20',
            change: '+12%',
            up: true,
          },
          {
            label: t('Avg. Quality Score', 'متوسط درجة الجودة'),
            value: `${avgScore}%`,
            icon: Target,
            color: 'text-green-400',
            bg: 'bg-green-500/10',
            border: 'border-green-500/20',
            change: '+3.2%',
            up: true,
          },
          {
            label: t('Queue (Pending + Processing)', 'قائمة الانتظار'),
            value: pendingCount.toString(),
            icon: Activity,
            color: 'text-amber-400',
            bg: 'bg-amber-500/10',
            border: 'border-amber-500/20',
            change: '3 processing',
            up: null,
          },
          {
            label: t('Pass Rate (≥75%)', 'معدل النجاح (≥75%)'),
            value: `${passRate}%`,
            icon: Users,
            color: 'text-blue-400',
            bg: 'bg-blue-500/10',
            border: 'border-blue-500/20',
            change: '+5%',
            up: true,
          },
        ].map((kpi, i) => (
          <div key={i} className={`bg-[#111827] border border-slate-800/60 rounded-xl p-5 hover:border-slate-700/60 transition-colors`}>
            <div className="flex items-start justify-between mb-4">
              <div className={`${kpi.bg} ${kpi.border} border p-2.5 rounded-lg`}>
                <kpi.icon size={18} className={kpi.color} />
              </div>
              {kpi.up !== null && (
                <span className={`text-xs flex items-center gap-1 ${kpi.up ? 'text-green-400' : 'text-red-400'}`}>
                  {kpi.up ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                  {kpi.change}
                </span>
              )}
              {kpi.up === null && (
                <span className="text-xs text-slate-500">{kpi.change}</span>
              )}
            </div>
            <p className="text-2xl font-bold text-white">{kpi.value}</p>
            <p className="text-xs text-slate-500 mt-1">{kpi.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Score Trend Chart */}
        <div className="xl:col-span-2 bg-[#111827] border border-slate-800/60 rounded-xl p-5">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-sm font-semibold text-white">{t('Score Trend (Last 10 Days)', 'اتجاه النقاط (آخر 10 أيام)')}</h3>
              <p className="text-xs text-slate-500 mt-0.5">{t('Average daily quality score', 'متوسط درجة الجودة اليومية')}</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={weeklyTrend} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis domain={[70, 95]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="score" name="score" stroke="#6366f1" strokeWidth={2} fill="url(#scoreGrad)" dot={{ fill: '#6366f1', r: 3 }} activeDot={{ r: 5, fill: '#818cf8' }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Score Distribution */}
        <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-5">
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-white">{t('Score Distribution', 'توزيع النقاط')}</h3>
            <p className="text-xs text-slate-500 mt-0.5">{t('All completed calls', 'جميع المكالمات المكتملة')}</p>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={scoreDistribution} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="range" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" name="calls" radius={[4, 4, 0, 0]}>
                {scoreDistribution.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Live Queue */}
        <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <h3 className="text-sm font-semibold text-white">{t('Live Processing Queue', 'قائمة المعالجة المباشرة')}</h3>
            </div>
            <span className="text-[11px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">{liveQueue.length} {t('in queue', 'في الانتظار')}</span>
          </div>
          <div className="space-y-3">
            {liveQueue.map((call) => {
              const agent = agents.find(a => a.id === call.agentId);
              const campaign = campaigns.find(c => c.id === call.campaignId);
              return (
                <div key={call.id} className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/30 border border-slate-700/30 hover:border-slate-700/60 transition-colors">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white flex-shrink-0"
                    style={{ backgroundColor: agent?.color + '33', border: `1px solid ${agent?.color}44`, color: agent?.color }}
                  >
                    {agent?.initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-300 truncate font-medium">{agent?.name}</p>
                    <p className="text-[11px] text-slate-600 truncate">{campaign?.name}</p>
                  </div>
                  <StatusBadge status={call.status} />
                </div>
              );
            })}
            {liveQueue.length === 0 && (
              <div className="text-center py-6 text-slate-600 text-sm">
                {t('No calls in queue', 'لا توجد مكالمات في قائمة الانتظار')}
              </div>
            )}
          </div>

          {/* Processing stats */}
          <div className="mt-4 pt-4 border-t border-slate-800/60 grid grid-cols-2 gap-3">
            {[
              { label: t('Processing', 'جاري المعالجة'), value: calls.filter(c => c.status === 'PROCESSING').length, color: 'text-blue-400' },
              { label: t('Pending', 'في الانتظار'), value: calls.filter(c => c.status === 'PENDING').length, color: 'text-amber-400' },
            ].map((s, i) => (
              <div key={i} className="text-center p-2 rounded-lg bg-slate-800/30">
                <p className={`text-lg font-bold ${s.color}`}>{s.value}</p>
                <p className="text-[10px] text-slate-600">{s.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Top Error Categories */}
        <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-5">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-white">{t('Top Error Categories', 'فئات الأخطاء الأعلى')}</h3>
            <p className="text-xs text-slate-500 mt-0.5">{t('Most frequent issues this week', 'المشاكل الأكثر تكراراً هذا الأسبوع')}</p>
          </div>
          <div className="space-y-3">
            {topErrorCategories.map((err, i) => (
              <div key={i}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-400 truncate">{err.name}</span>
                  <span className="text-xs font-medium text-slate-300 ml-2 flex-shrink-0">{err.count}</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full transition-all duration-700"
                    style={{ 
                      width: `${topErrorCategories[0]?.count ? (err.count / topErrorCategories[0].count) * 100 : 0}%`, 
                      backgroundColor: err.color 
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Agent Leaderboard */}
        <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">{t('Agent Leaderboard', 'لوحة المتصدرين')}</h3>
            <button onClick={() => navigate('/agents')} className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
              {t('View all', 'عرض الكل')} <ArrowRight size={11} />
            </button>
          </div>
          <div className="space-y-2">
            {[...agents].sort((a, b) => b.avgScore - a.avgScore).slice(0, 5).map((agent, i) => (
              <div
                key={agent.id}
                onClick={() => navigate(`/agents/${agent.id}`)}
                className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-800/40 cursor-pointer transition-colors group"
              >
                <span className={`text-xs font-bold w-5 text-center ${i === 0 ? 'text-yellow-400' : i === 1 ? 'text-slate-400' : i === 2 ? 'text-amber-600' : 'text-slate-600'}`}>
                  {i + 1}
                </span>
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-semibold flex-shrink-0"
                  style={{ backgroundColor: agent.color + '22', color: agent.color, border: `1px solid ${agent.color}40` }}
                >
                  {agent.initials}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-300 truncate group-hover:text-white">{agent.name}</p>
                  <p className="text-[10px] text-slate-600">{agent.department}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold" style={{ color: getScoreColor(agent.avgScore) }}>{agent.avgScore}</p>
                  <div className="flex items-center justify-end">
                    {agent.trend === 'up' ? <TrendingUp size={10} className="text-green-500" /> : agent.trend === 'down' ? <TrendingDown size={10} className="text-red-500" /> : <span className="text-[10px] text-slate-600">—</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Calls */}
      <div className="bg-[#111827] border border-slate-800/60 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800/60">
          <h3 className="text-sm font-semibold text-white">{t('Recent Completed Calls', 'المكالمات المكتملة الأخيرة')}</h3>
          <button onClick={() => navigate('/calls')} className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
            {t('View all', 'عرض الكل')} <ArrowRight size={11} />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800/60">
                {[t('Agent', 'الوكيل'), t('Campaign', 'الحملة'), t('Date & Time', 'التاريخ والوقت'), t('Duration', 'المدة'), t('Score', 'النقاط'), t('Status', 'الحالة'), ''].map((h, i) => (
                  <th key={i} className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {recentCalls.map(call => {
                const agent = agents.find(a => a.id === call.agentId);
                const campaign = campaigns.find(c => c.id === call.campaignId);
                return (
                  <tr key={call.id} className="hover:bg-slate-800/20 transition-colors group">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-semibold flex-shrink-0"
                          style={{ backgroundColor: agent?.color + '22', color: agent?.color }}
                        >
                          {agent?.initials}
                        </div>
                        <span className="text-sm text-slate-300">{agent?.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-slate-400 px-2 py-1 rounded-md bg-slate-800/50">{campaign?.name}</span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {new Date(call.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} {new Date(call.date).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">{formatDuration(call.duration)}</td>
                    <td className="px-4 py-3">
                      {call.score !== null ? (
                        <span
                          className="text-sm font-bold px-2 py-0.5 rounded"
                          style={{ color: getScoreColor(call.score), backgroundColor: getScoreColor(call.score) + '15' }}
                        >
                          {call.score}%
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={call.status} /></td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => navigate(`/calls/${call.id}`)}
                        className="opacity-0 group-hover:opacity-100 text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-opacity"
                      >
                        {t('Review', 'مراجعة')} <ArrowRight size={11} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Campaign Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {campaigns.map(camp => (
          <div
            key={camp.id}
            onClick={() => navigate('/campaigns')}
            className="bg-[#111827] border border-slate-800/60 rounded-xl p-4 hover:border-slate-700/60 cursor-pointer transition-all group"
          >
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: camp.color }} />
              <span className="text-xs text-slate-400 truncate">{camp.name}</span>
            </div>
            <p className="text-2xl font-bold text-white">{camp.totalEvaluations}</p>
            <p className="text-[11px] text-slate-600 mt-0.5">{t('evaluations', 'تقييم')}</p>
            <div className="mt-3 flex items-center justify-between">
              <span className="text-[11px] text-slate-500">{camp.activeAgents} {t('agents', 'وكيل')}</span>
              <span className="text-[11px]" style={{ color: camp.color }}>{t('≥', '≥')}{camp.passThreshold}% {t('pass', 'نجاح')}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}