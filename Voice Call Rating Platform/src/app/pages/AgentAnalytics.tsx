import { useState } from 'react';
import { useNavigate } from 'react-router';
import {
  TrendingUp, TrendingDown, Minus, ArrowRight, Award, AlertTriangle,
  Search, SlidersHorizontal, Star, Users
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { agents, calls, getScoreColor } from '../data/mockData';
import { useLang } from '../context/LangContext';

interface AgentAnalyticsProps {
  lang: 'en' | 'ar';
}

export function AgentAnalytics() {
  const navigate = useNavigate();
  const { lang } = useLang();
  const isRtl = lang === 'ar';
  const t = (en: string, ar: string) => isRtl ? ar : en;

  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState<'score' | 'calls' | 'passRate'>('score');
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');

  const departments = Array.from(new Set((agents || []).map(a => a.department)));

  const filteredAgents = (agents || []).filter(a => {
    if (search && !a.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (deptFilter !== 'ALL' && a.department !== deptFilter) return false;
    return true;
  }).sort((a, b) => {
    if (sortBy === 'score') return (b.avgScore || 0) - (a.avgScore || 0);
    if (sortBy === 'calls') return (b.totalCalls || 0) - (a.totalCalls || 0);
    return (b.passRate || 0) - (a.passRate || 0);
  });

  const topAgent = [...(agents || [])].sort((a, b) => (b.avgScore || 0) - (a.avgScore || 0))[0] || { name: 'None', avgScore: 0 };
  const atRiskAgents = (agents || []).filter(a => (a.avgScore || 0) < 75);
  const overallAvg = (agents || []).length > 0 
    ? Math.round((agents || []).reduce((s, a) => s + (a.avgScore || 0), 0) / agents.length)
    : 0;

  const barData = (agents || []).map(a => ({
    name: (a.name || 'Agent').split(' ')[0],
    score: a.avgScore || 0,
    color: a.color || '#6366f1',
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload?.length) {
      return (
        <div className="bg-[#1a2235] border border-slate-700/60 rounded-lg px-3 py-2 shadow-xl">
          <p className="text-xs text-slate-400 mb-1">{label}</p>
          <p className="text-sm font-bold" style={{ color: payload[0]?.payload?.color }}>{payload[0]?.value}%</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">{t('Agent Analytics', 'تحليلات الوكلاء')}</h1>
          <p className="text-sm text-slate-500 mt-0.5">{t('Performance overview and individual agent metrics', 'نظرة عامة على الأداء ومقاييس الوكلاء الفردية')}</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: t('Total Agents', 'إجمالي الوكلاء'), value: agents.length, icon: Users, color: 'text-indigo-400', bg: 'bg-indigo-500/10', border: 'border-indigo-500/20' },
          { label: t('Team Avg Score', 'متوسط درجة الفريق'), value: `${overallAvg}%`, icon: Star, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20' },
          { label: t('Top Performer', 'أفضل أداء'), value: topAgent.name.split(' ')[0], icon: Award, color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20' },
          { label: t('At-Risk Agents', 'الوكلاء في خطر'), value: atRiskAgents.length, icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' },
        ].map((card, i) => (
          <div key={i} className={`bg-[#111827] border border-slate-800/60 rounded-xl p-5`}>
            <div className={`${card.bg} ${card.border} border w-10 h-10 rounded-lg flex items-center justify-center mb-4`}>
              <card.icon size={18} className={card.color} />
            </div>
            <p className="text-2xl font-bold text-white">{card.value}</p>
            <p className="text-xs text-slate-500 mt-1">{card.label}</p>
          </div>
        ))}
      </div>

      {/* Score Comparison Chart */}
      <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-5">
        <div className="mb-5">
          <h3 className="text-sm font-semibold text-white">{t('Agent Score Comparison', 'مقارنة درجات الوكلاء')}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{t('Average quality score by agent (all time)', 'متوسط درجة الجودة لكل وكيل (طوال الوقت)')}</p>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={barData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis domain={[50, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
            <Bar dataKey="score" radius={[4, 4, 0, 0]}>
              {barData.map((entry, index) => (
                <Cell key={index} fill={entry.color} opacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Pass threshold line indicator */}
        <div className="mt-2 flex items-center gap-2">
          <div className="w-4 h-px bg-amber-500 border-dashed border-t border-amber-500" />
          <span className="text-[11px] text-amber-500/70">{t('75% pass threshold', 'حد النجاح 75%')}</span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder={t('Search agents...', 'البحث عن الوكلاء...')}
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 transition-colors"
          />
        </div>

        <select
          value={deptFilter}
          onChange={e => setDeptFilter(e.target.value)}
          className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
        >
          <option value="ALL">{t('All Departments', 'جميع الأقسام')}</option>
          {departments.map(d => <option key={d} value={d}>{d}</option>)}
        </select>

        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value as any)}
          className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
        >
          <option value="score">{t('Sort by Score', 'ترتيب حسب النقاط')}</option>
          <option value="calls">{t('Sort by Calls', 'ترتيب حسب المكالمات')}</option>
          <option value="passRate">{t('Sort by Pass Rate', 'ترتيب حسب معدل النجاح')}</option>
        </select>
      </div>

      {/* Wall of Fame/Shame */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top Performers */}
        <div className="bg-[#111827] border border-green-500/20 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Award size={16} className="text-green-400" />
            <h3 className="text-sm font-semibold text-green-400">{t('Wall of Fame', 'لوحة الشرف')}</h3>
            <span className="text-[11px] text-slate-600">{t('Score ≥ 85%', 'النقاط ≥ 85%')}</span>
          </div>
          <div className="space-y-2">
            {[...agents].filter(a => a.avgScore >= 85).sort((a, b) => b.avgScore - a.avgScore).map((agent, i) => (
              <div
                key={agent.id}
                onClick={() => navigate(`/agents/${agent.id}`)}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-green-500/5 cursor-pointer transition-colors group"
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${i === 0 ? 'bg-yellow-400/20 text-yellow-400' : 'bg-green-500/10 text-green-400'}`}>
                  {i === 0 ? '🏆' : i + 1}
                </div>
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-semibold flex-shrink-0"
                  style={{ backgroundColor: agent.color + '22', color: agent.color, border: `1px solid ${agent.color}44` }}
                >
                  {agent.initials}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 group-hover:text-white">{agent.name}</p>
                  <p className="text-[11px] text-slate-600">{agent.department} · {agent.totalCalls} {t('calls', 'مكالمة')}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-green-400">{agent.avgScore}%</p>
                  <p className="text-[10px] text-green-600">{agent.passRate}% {t('pass', 'نجاح')}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Needs Improvement */}
        <div className="bg-[#111827] border border-red-500/20 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={16} className="text-red-400" />
            <h3 className="text-sm font-semibold text-red-400">{t('Needs Coaching', 'يحتاج تدريباً')}</h3>
            <span className="text-[11px] text-slate-600">{t('Score < 80%', 'النقاط < 80%')}</span>
          </div>
          <div className="space-y-2">
            {[...agents].filter(a => a.avgScore < 80).sort((a, b) => a.avgScore - b.avgScore).map((agent, i) => (
              <div
                key={agent.id}
                onClick={() => navigate(`/agents/${agent.id}`)}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-red-500/5 cursor-pointer transition-colors group"
              >
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-semibold flex-shrink-0"
                  style={{ backgroundColor: agent.color + '22', color: agent.color, border: `1px solid ${agent.color}44` }}
                >
                  {agent.initials}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 group-hover:text-white">{agent.name}</p>
                  <p className="text-[11px] text-slate-600">{agent.department} · {agent.totalCalls} {t('calls', 'مكالمة')}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold" style={{ color: getScoreColor(agent.avgScore) }}>{agent.avgScore}%</p>
                  <div className="flex items-center justify-end gap-1">
                    <TrendingDown size={10} className="text-red-500" />
                    <span className="text-[10px] text-red-500">{agent.passRate}% {t('pass', 'نجاح')}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Full Agent Table */}
      <div className="bg-[#111827] border border-slate-800/60 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-800/60">
          <h3 className="text-sm font-semibold text-white">{t('All Agents', 'جميع الوكلاء')} ({filteredAgents.length})</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800/60 bg-slate-900/30">
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Rank', 'الترتيب')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Agent', 'الوكيل')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Department', 'القسم')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Avg Score', 'متوسط النقاط')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Total Calls', 'إجمالي المكالمات')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Pass Rate', 'معدل النجاح')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Trend', 'الاتجاه')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Status', 'الحالة')}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {filteredAgents.map((agent, idx) => {
                const rank = [...agents].sort((a, b) => b.avgScore - a.avgScore).findIndex(a => a.id === agent.id) + 1;
                const agentCalls = calls.filter(c => c.agentId === agent.id && c.status === 'COMPLETED');
                return (
                  <tr key={agent.id} className="hover:bg-slate-800/20 transition-colors group">
                    <td className="px-4 py-4">
                      <span className={`text-sm font-bold ${rank === 1 ? 'text-yellow-400' : rank === 2 ? 'text-slate-400' : rank === 3 ? 'text-amber-600' : 'text-slate-600'}`}>
                        {rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0"
                          style={{ backgroundColor: agent.color + '22', color: agent.color, border: `1px solid ${agent.color}44` }}
                        >
                          {agent.initials}
                        </div>
                        <div>
                          <p className="text-sm text-slate-200">{agent.name}</p>
                          <p className="text-[11px] text-slate-600">{agent.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className="text-xs text-slate-400 px-2 py-1 bg-slate-800/50 rounded-lg">{agent.department}</span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-800 rounded-full h-1.5">
                          <div className="h-1.5 rounded-full" style={{ width: `${agent.avgScore}%`, backgroundColor: getScoreColor(agent.avgScore) }} />
                        </div>
                        <span className="text-sm font-semibold" style={{ color: getScoreColor(agent.avgScore) }}>{agent.avgScore}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-400">{agent.totalCalls}</td>
                    <td className="px-4 py-4">
                      <span className="text-sm text-slate-400">{agent.passRate}%</span>
                    </td>
                    <td className="px-4 py-4">
                      {agent.trend === 'up' ? (
                        <div className="flex items-center gap-1 text-green-400 text-xs"><TrendingUp size={13} /> {t('Improving', 'تحسن')}</div>
                      ) : agent.trend === 'down' ? (
                        <div className="flex items-center gap-1 text-red-400 text-xs"><TrendingDown size={13} /> {t('Declining', 'تراجع')}</div>
                      ) : (
                        <div className="flex items-center gap-1 text-slate-500 text-xs"><Minus size={13} /> {t('Stable', 'مستقر')}</div>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <span className={`text-[11px] px-2 py-1 rounded-full border ${agent.avgScore >= 75 ? 'text-green-400 bg-green-500/10 border-green-500/20' : 'text-red-400 bg-red-500/10 border-red-500/20'}`}>
                        {agent.avgScore >= 75 ? t('Passing', 'ناجح') : t('At Risk', 'في خطر')}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <button
                        onClick={() => navigate(`/agents/${agent.id}`)}
                        className="opacity-0 group-hover:opacity-100 flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-all"
                      >
                        {t('Profile', 'الملف')} <ArrowRight size={11} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}