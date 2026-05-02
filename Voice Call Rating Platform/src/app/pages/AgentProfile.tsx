import { useParams, useNavigate } from 'react-router';
import {
  ArrowLeft, Phone, TrendingUp, TrendingDown, Minus, Eye, Award,
  AlertTriangle, Star, Target, CheckCircle2, BarChart3
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, Cell
} from 'recharts';
import { agents, calls, campaigns, agentTrends, radarData, formatDuration, getScoreColor } from '../data/mockData';
import { useLang } from '../context/LangContext';

interface AgentProfileProps {
  lang: 'en' | 'ar';
}

export function AgentProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { lang } = useLang();
  const isRtl = lang === 'ar';
  const t = (en: string, ar: string) => isRtl ? ar : en;

  const agent = agents.find(a => a.id === id) || agents[0];
  const agentCalls = calls.filter(c => c.agentId === agent.id && c.status === 'COMPLETED');
  const campaign = campaigns.find(c => c.id === agentCalls[0]?.campaignId);
  const trendData = agentTrends[agent.id] || agentTrends['a1'];

  const agentRadar = radarData.map(d => ({
    subject: d.subject,
    score: d[agent.id as keyof typeof d] as number || 80,
  }));

  const scoreByCategory = [
    { name: t('Opening', 'الافتتاح'), score: agentRadar[0]?.score || 0 },
    { name: t('Discovery', 'الاكتشاف'), score: agentRadar[1]?.score || 0 },
    { name: t('Presentation', 'العرض'), score: agentRadar[2]?.score || 0 },
    { name: t('Objection', 'الاعتراض'), score: agentRadar[3]?.score || 0 },
    { name: t('Closing', 'الإغلاق'), score: agentRadar[4]?.score || 0 },
    { name: t('Empathy', 'التعاطف'), score: agentRadar[5]?.score || 0 },
  ];

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload?.length) {
      return (
        <div className="bg-[#1a2235] border border-slate-700/60 rounded-lg px-3 py-2 shadow-xl">
          <p className="text-xs text-slate-400 mb-1">{label}</p>
          <p className="text-sm font-bold" style={{ color: agent.color }}>{payload[0]?.value}%</p>
          {payload[1] && <p className="text-xs text-slate-500">{payload[1].value} {t('calls', 'مكالمة')}</p>}
        </div>
      );
    }
    return null;
  };

  const passedCalls = agentCalls.filter(c => (c.score || 0) >= 75).length;
  const passRate = agentCalls.length > 0 ? Math.round(passedCalls / agentCalls.length * 100) : 0;

  const rankIndex = [...agents].sort((a, b) => b.avgScore - a.avgScore).findIndex(a => a.id === agent.id);

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/agents')}
          className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft size={16} />
          <span className="text-sm">{t('Back to Agents', 'العودة للوكلاء')}</span>
        </button>
      </div>

      {/* Agent Header Card */}
      <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center text-lg font-bold flex-shrink-0"
            style={{ backgroundColor: agent.color + '22', color: agent.color, border: `2px solid ${agent.color}44` }}
          >
            {agent.initials}
          </div>

          <div className="flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-semibold text-white">{agent.name}</h1>
              {rankIndex === 0 && <span className="text-xs text-yellow-400 bg-yellow-400/10 border border-yellow-400/20 px-2 py-0.5 rounded-full">🏆 {t('Top Performer', 'أفضل أداء')}</span>}
              {agent.avgScore < 75 && <span className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 px-2 py-0.5 rounded-full">⚠ {t('At Risk', 'في خطر')}</span>}
            </div>
            <p className="text-sm text-slate-500 mt-0.5">{agent.email}</p>
            <div className="flex items-center gap-4 mt-2 flex-wrap">
              <span className="text-xs text-slate-400 bg-slate-800/50 px-2 py-1 rounded-lg">{agent.department}</span>
              <span className="text-xs text-slate-500">{t('Rank', 'الترتيب')} #{rankIndex + 1} {t('of', 'من')} {agents.length}</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 text-center">
            {[
              { label: t('Avg Score', 'متوسط النقاط'), value: `${agent.avgScore}%`, color: getScoreColor(agent.avgScore) },
              { label: t('Total Calls', 'إجمالي المكالمات'), value: agent.totalCalls, color: '#94a3b8' },
              { label: t('Pass Rate', 'معدل النجاح'), value: `${agent.passRate}%`, color: agent.passRate >= 75 ? '#22c55e' : '#ef4444' },
            ].map((stat, i) => (
              <div key={i} className="px-4">
                <p className="text-2xl font-bold" style={{ color: stat.color }}>{stat.value}</p>
                <p className="text-xs text-slate-600 mt-0.5">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Score Trend */}
        <div className="xl:col-span-2 bg-[#111827] border border-slate-800/60 rounded-xl p-5">
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-white">{t('Score Trend (Last 10 Days)', 'اتجاه النقاط (آخر 10 أيام)')}</h3>
            <div className="flex items-center gap-2 mt-1">
              {agent.trend === 'up' ? (
                <span className="flex items-center gap-1 text-xs text-green-400"><TrendingUp size={12} /> {t('Improving', 'تحسن')}</span>
              ) : agent.trend === 'down' ? (
                <span className="flex items-center gap-1 text-xs text-red-400"><TrendingDown size={12} /> {t('Declining', 'تراجع')}</span>
              ) : (
                <span className="flex items-center gap-1 text-xs text-slate-500"><Minus size={12} /> {t('Stable', 'مستقر')}</span>
              )}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trendData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis domain={[50, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="score"
                stroke={agent.color}
                strokeWidth={2.5}
                dot={{ fill: agent.color, r: 4, strokeWidth: 0 }}
                activeDot={{ r: 6, fill: agent.color }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Radar Chart */}
        <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-5">
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-white">{t('Competency Radar', 'رادار الكفاءات')}</h3>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={agentRadar}>
              <PolarGrid stroke="#1e293b" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10 }} />
              <PolarRadiusAxis domain={[0, 100]} tick={{ fill: '#475569', fontSize: 9 }} />
              <Radar
                name={agent.name}
                dataKey="score"
                stroke={agent.color}
                fill={agent.color}
                fillOpacity={0.15}
                strokeWidth={2}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-5">
        <div className="mb-5">
          <h3 className="text-sm font-semibold text-white">{t('Performance by Category', 'الأداء حسب الفئة')}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{t('Average scores across all rubric categories', 'متوسط النقاط عبر جميع فئات المعايير')}</p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {scoreByCategory.map((cat, i) => (
            <div key={i} className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-3 text-center">
              <div
                className="w-10 h-10 rounded-full mx-auto flex items-center justify-center mb-2 text-sm font-bold"
                style={{ backgroundColor: getScoreColor(cat.score) + '15', color: getScoreColor(cat.score) }}
              >
                {cat.score}
              </div>
              <p className="text-[11px] text-slate-400">{cat.name}</p>
              <div className="w-full bg-slate-800 rounded-full h-1 mt-1.5">
                <div
                  className="h-1 rounded-full"
                  style={{ width: `${cat.score}%`, backgroundColor: getScoreColor(cat.score) }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Calls */}
      <div className="bg-[#111827] border border-slate-800/60 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-800/60">
          <h3 className="text-sm font-semibold text-white">{t('Recent Calls', 'المكالمات الأخيرة')}</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800/60 bg-slate-900/30">
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Date', 'التاريخ')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Campaign', 'الحملة')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Duration', 'المدة')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Score', 'النقاط')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Issues', 'المشاكل')}</th>
                <th className="px-4 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Reviewed', 'تمت المراجعة')}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {calls.filter(c => c.agentId === agent.id).map(call => {
                const camp = campaigns.find(c => c.id === call.campaignId);
                return (
                  <tr key={call.id} className="hover:bg-slate-800/20 transition-colors group">
                    <td className="px-4 py-3.5">
                      <p className="text-xs text-slate-300">{new Date(call.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</p>
                      <p className="text-[11px] text-slate-600">{new Date(call.date).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</p>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: camp?.color }} />
                        <span className="text-xs text-slate-400">{camp?.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400">
                      {call.duration > 0 ? formatDuration(call.duration) : '—'}
                    </td>
                    <td className="px-4 py-3.5">
                      {call.score !== null ? (
                        <span className="text-sm font-bold" style={{ color: getScoreColor(call.score) }}>{call.score}%</span>
                      ) : (
                        <span className={`text-[11px] px-2 py-0.5 rounded-full border ${
                          call.status === 'PROCESSING' ? 'text-blue-400 bg-blue-500/10 border-blue-500/20' :
                          call.status === 'PENDING' ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' :
                          'text-red-400 bg-red-500/10 border-red-500/20'
                        }`}>{call.status}</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      {call.errorCategories.length > 0 ? (
                        <span className="text-xs text-amber-500">{call.errorCategories.length} {t('issue(s)', 'مشكلة')}</span>
                      ) : call.status === 'COMPLETED' ? (
                        <span className="text-xs text-green-500/60">✓</span>
                      ) : <span className="text-slate-700">—</span>}
                    </td>
                    <td className="px-4 py-3.5">
                      {call.supervisorReviewed ? (
                        <CheckCircle2 size={14} className="text-green-500" />
                      ) : (
                        <span className="text-slate-700 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      {call.status === 'COMPLETED' && (
                        <button
                          onClick={() => navigate(`/calls/${call.id}`)}
                          className="opacity-0 group-hover:opacity-100 flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-all"
                        >
                          <Eye size={12} /> {t('Review', 'مراجعة')}
                        </button>
                      )}
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