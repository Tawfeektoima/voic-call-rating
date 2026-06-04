import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { 
  ShieldAlert, AlertTriangle, CheckCircle2, TrendingUp, Search,
  ChevronDown, ChevronRight, Activity, Clock, XCircle
} from "lucide-react";
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend
} from "recharts";
import { 
  useViolationStats, useViolationsSummary, useViolationTrends, useAgentViolations 
} from "../hooks/useViolations";
import { CallViolation } from "../lib/types";
import { useApp } from "../context/AppContext";

const PENALTY_COLOR: Record<string, string> = {
  "Warning":     "text-slate-400",
  "1 HR":        "text-yellow-400",
  "2 HR":        "text-amber-400",
  "3 HR":        "text-orange-400",
  "Half Day":    "text-red-400",
  "Full Day":    "text-red-500 font-bold",
  "No Show":     "text-red-600 font-bold",
  "Termination": "text-red-700 font-extrabold",
};

const SEVERITY_CONFIG: Record<string, { label: string, dot: string, badge: string }> = {
  high:   { label: "HIGH",   dot: "bg-red-500",    badge: "bg-red-500/10 text-red-400 border-red-500/20" },
  medium: { label: "MEDIUM", dot: "bg-amber-500",  badge: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  low:    { label: "LOW",    dot: "bg-yellow-500", badge: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20" },
};

function AgentViolationsInline({ employeeId }: { employeeId: number }) {
  const { data, isLoading } = useAgentViolations(employeeId);
  const navigate = useNavigate();

  if (isLoading) return <div className="p-4 text-center text-muted-foreground animate-pulse">Loading...</div>;
  if (!data || !data.violations || data.violations.length === 0) {
    return <div className="p-4 text-center text-muted-foreground">No violations found.</div>;
  }

  return (
    <div className="p-4 bg-secondary/20 rounded-b-xl border-x border-b border-border space-y-3">
      <div className="flex items-center justify-between text-xs text-muted-foreground px-2">
        <span className="font-semibold">{data.employee_name} — {data.total_violations} violations</span>
        <span className="text-red-400 font-semibold">-{data.total_deductions} pts total</span>
      </div>
      <div className="space-y-2">
        {data.violations.map((v) => {
          const sc = SEVERITY_CONFIG[v.severity] || SEVERITY_CONFIG.medium;
          return (
            <div key={v.id} className="bg-card border border-border rounded-lg p-3">
              <div className="flex items-center justify-between gap-4 mb-2">
                <div className="flex items-center gap-3">
                  <button 
                    onClick={() => navigate(`/calls/${v.call_id}`)}
                    className="text-indigo-400 hover:text-indigo-300 font-mono text-xs hover:underline"
                  >
                    Call #{v.call_id}
                  </button>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase ${sc.badge}`}>
                    <span className={`inline-block size-1.5 rounded-full ${sc.dot} mr-1`} />
                    {v.violation_id.replace(/_/g, " ")}
                  </span>
                  <span className="text-[10px] bg-secondary text-muted-foreground px-1.5 py-0.5 rounded">
                    {v.occurrence}{v.occurrence === 1 ? 'st' : v.occurrence === 2 ? 'nd' : v.occurrence === 3 ? 'rd' : 'th'} offense
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className={`font-bold ${PENALTY_COLOR[v.penalty_tier] || ""}`}>
                    {v.penalty_tier}
                  </span>
                  <span className="text-red-400 font-medium">
                    {v.score_deduction > 0 ? `-${v.score_deduction}pts` : "—"}
                  </span>
                </div>
              </div>
              {v.evidence && (
                <div className="text-[11px] text-muted-foreground leading-relaxed pl-2 border-l-2 border-secondary">
                  <span className="text-foreground/70 font-medium mr-1">Evidence:</span>
                  {v.timestamp_in_call && <span className="text-indigo-400/80 mr-1">[{v.timestamp_in_call}]</span>}
                  {v.evidence}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function HRDashboard() {
  const { userRole } = useApp();
  const navigate = useNavigate();
  
  if (userRole !== 'admin' && userRole !== 'hr_manager' && userRole !== 'qa') {
    return (
      <div className="p-10 flex flex-col items-center justify-center text-center">
        <ShieldAlert size={48} className="text-red-500 mb-4" />
        <h1 className="text-2xl font-bold text-foreground mb-2">Access Denied</h1>
        <p className="text-muted-foreground">You do not have permission to view the HR Dashboard.</p>
      </div>
    );
  }

  const { data: stats } = useViolationStats();
  const { data: summary } = useViolationsSummary();
  const { data: trends } = useViolationTrends(7);
  // Need to fetch pending manually via fetch or another hook, let's just make a fast one
  // Or just use the API directly with react-query
  const { data: pending } = useQuery({
    queryKey: ["violations-pending"],
    queryFn: async () => {
      const { default: api } = await import("../lib/api");
      const res = await api.get("/api/hr/violations/pending");
      return res.data;
    }
  });

  const { data: pendingAlarms } = useQuery({
    queryKey: ["qa-alarms-pending"],
    queryFn: async () => {
      const { default: api } = await import("../lib/api");
      const res = await api.get("/api/hr/alarms/pending");
      return res.data;
    }
  });

  const [search, setSearch] = useState("");
  const [expandedAgent, setExpandedAgent] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<"total"|"hr_flags"|"score_impact">("total");

  const filtered = summary
    ?.filter(row => row.employee_name.toLowerCase().includes(search.toLowerCase()))
    ?.sort((a, b) => {
      if (sortBy === "hr_flags") return b.hr_flagged_count - a.hr_flagged_count;
      if (sortBy === "score_impact") return b.total_deductions - a.total_deductions;
      return b.total_violations - a.total_violations;
    });

  const formatTrendDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { weekday: "short" });
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">HR Violations Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">Platform-wide compliance and penalty tracking</p>
        </div>
      </div>

      {/* Section 1: Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Total Violations (This Week)</p>
              <h3 className="text-2xl font-bold text-foreground mt-1">{stats?.total_violations_this_week || 0}</h3>
              <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                <TrendingUp size={12} /> {stats?.total_violations_today || 0} today
              </p>
            </div>
            <div className="p-2 bg-red-500/10 rounded-lg">
              <AlertTriangle size={18} className="text-red-400" />
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground">HR Flags Today</p>
              <h3 className="text-2xl font-bold text-foreground mt-1">{stats?.agents_with_hr_flags || 0}</h3>
              <p className="text-xs text-amber-400 mt-1">Pending review</p>
            </div>
            <div className="p-2 bg-amber-500/10 rounded-lg">
              <ShieldAlert size={18} className="text-amber-400" />
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Auto-Fails Today</p>
              <h3 className="text-2xl font-bold text-foreground mt-1">{stats?.auto_fails_today || 0}</h3>
              <p className="text-xs text-red-500 mt-1">Zero tolerance triggered</p>
            </div>
            <div className="p-2 bg-red-500/10 rounded-lg">
              <XCircle size={18} className="text-red-500" />
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Most Common</p>
              <h3 className="text-lg font-bold text-foreground mt-1 uppercase truncate" title={stats?.most_common_violation || "None"}>
                {(stats?.most_common_violation || "None").replace(/_/g, " ")}
              </h3>
              <p className="text-xs text-indigo-400 mt-1">{stats?.most_common_violation_count || 0} occurrences</p>
            </div>
            <div className="p-2 bg-indigo-500/10 rounded-lg">
              <Activity size={18} className="text-indigo-400" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Pending Flags & Chart */}
        <div className="lg:col-span-1 space-y-6">
          {/* Section: Pending QA Alarms */}
          <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden flex flex-col h-[280px]">
            <div className="p-4 border-b border-border bg-red-500/5 flex items-center justify-between">
              <h3 className="font-semibold text-foreground flex items-center gap-2">
                <ShieldAlert size={16} className="text-red-500 animate-pulse" /> 
                Pending QA Alarms
              </h3>
              <span className="text-xs font-bold bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full">
                {pendingAlarms?.length || 0}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {(!pendingAlarms || pendingAlarms.length === 0) ? (
                <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-lg p-4 text-center">
                  <div className="flex items-center justify-center gap-2 text-emerald-500 text-sm font-semibold">
                    <CheckCircle2 size={16} />
                    No pending QA alarms
                  </div>
                </div>
              ) : (
                pendingAlarms.map((a: any) => (
                  <div key={a.call_id} className="bg-secondary/30 border border-border rounded-lg p-3 relative group">
                    <div className="flex justify-between items-start mb-2">
                      <p className="text-xs font-bold text-foreground">{a.employee_name}</p>
                      <button 
                        onClick={() => navigate(`/calls/${a.call_id}`)}
                        className="text-[10px] text-indigo-400 hover:text-indigo-300 font-mono flex items-center gap-1 hover:underline"
                      >
                        Call #{a.call_id} <ChevronRight size={10} />
                      </button>
                    </div>
                    <div className="text-[10px] text-red-400 font-medium mb-1">
                      {a.qa_alarm_reason}
                    </div>
                    {a.qa_alarm_evidence && (
                      <div className="text-[9px] text-muted-foreground line-clamp-2 bg-black/20 p-1.5 rounded border border-border mt-1">
                        {a.qa_alarm_evidence}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Section 2: Pending HR Flags */}
          <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden flex flex-col h-[280px]">
            <div className="p-4 border-b border-border bg-amber-500/5 flex items-center justify-between">
              <h3 className="font-semibold text-foreground flex items-center gap-2">
                <ShieldAlert size={16} className="text-amber-500" /> 
                Pending HR Flags
              </h3>
              <span className="text-xs font-bold bg-amber-500/20 text-amber-500 px-2 py-0.5 rounded-full">
                {pending?.length || 0}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {(!pending || pending.length === 0) ? (
                <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-lg p-4 text-center">
                  <div className="flex items-center justify-center gap-2 text-emerald-500 text-sm font-semibold">
                    <CheckCircle2 size={16} />
                    No pending HR flags
                  </div>
                </div>
              ) : (
                pending.map((v: any) => (
                  <div key={v.violation_id} className="bg-secondary/30 border border-border rounded-lg p-3 relative group">
                    <div className="flex justify-between items-start mb-2">
                      <p className="text-xs font-bold text-foreground">{v.employee_name}</p>
                      <button 
                        onClick={() => navigate(`/calls/${v.call_id}`)}
                        className="text-[10px] text-indigo-400 hover:text-indigo-300 font-mono flex items-center gap-1 hover:underline"
                      >
                        Call #{v.call_id} <ChevronRight size={10} />
                      </button>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className="text-[10px] px-1.5 py-0.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded uppercase font-bold">
                        {v.severity}
                      </span>
                      <span className="text-[10px] text-muted-foreground truncate max-w-[120px]" title={v.violation_type.replace(/_/g, " ")}>
                        {v.violation_type.replace(/_/g, " ")}
                      </span>
                      <span className={`text-[10px] font-bold ${PENALTY_COLOR[v.penalty_tier] || ""}`}>
                        {v.penalty_tier}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Section 4: Violation Trends Chart */}
          <div className="bg-card border border-border rounded-xl shadow-sm p-4 h-[300px] flex flex-col">
            <h3 className="font-semibold text-foreground mb-4 text-sm">Violation Trends — Last 7 Days</h3>
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends || []} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorMedium" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorLow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#eab308" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#eab308" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={formatTrendDate} 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fontSize: 10, fill: '#94a3b8' }} 
                    dy={10}
                  />
                  <YAxis 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                  />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                    labelFormatter={(label) => new Date(label as string).toLocaleDateString()}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
                  <Area type="monotone" name="High" dataKey="high" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#colorHigh)" />
                  <Area type="monotone" name="Medium" dataKey="medium" stroke="#f59e0b" strokeWidth={2} fillOpacity={1} fill="url(#colorMedium)" />
                  <Area type="monotone" name="Low" dataKey="low" stroke="#eab308" strokeWidth={2} fillOpacity={1} fill="url(#colorLow)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Right Column: Agent Summary Table */}
        <div className="lg:col-span-2">
          <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden h-full flex flex-col">
            <div className="p-4 border-b border-border flex items-center justify-between gap-4 flex-wrap bg-secondary/10">
              <h3 className="font-semibold text-foreground whitespace-nowrap">Agent Violations Summary</h3>
              
              <div className="flex items-center gap-3 w-full sm:w-auto">
                <div className="relative flex-1 sm:w-64">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <input 
                    type="text" 
                    placeholder="Search agent..." 
                    className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </div>
                
                <select 
                  className="bg-background border border-border rounded-lg px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  value={sortBy}
                  onChange={(e: any) => setSortBy(e.target.value)}
                >
                  <option value="total">Sort: Total</option>
                  <option value="hr_flags">Sort: HR Flags</option>
                  <option value="score_impact">Sort: Impact</option>
                </select>
              </div>
            </div>
            
            <div className="flex-1 overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-secondary/30 text-muted-foreground uppercase tracking-wider text-[10px] sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-3 font-semibold w-8"></th>
                    <th className="px-4 py-3 font-semibold">Agent</th>
                    <th className="px-4 py-3 font-semibold text-center">Total</th>
                    <th className="px-4 py-3 font-semibold text-center"><div className="mx-auto size-2 rounded-full bg-red-500" title="High Severity"></div></th>
                    <th className="px-4 py-3 font-semibold text-center"><div className="mx-auto size-2 rounded-full bg-amber-500" title="Medium Severity"></div></th>
                    <th className="px-4 py-3 font-semibold text-center"><div className="mx-auto size-2 rounded-full bg-yellow-500" title="Low Severity"></div></th>
                    <th className="px-4 py-3 font-semibold text-center">HR Flags</th>
                    <th className="px-4 py-3 font-semibold text-right">Score Impact</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filtered?.map((row) => (
                    <React.Fragment key={row.employee_id}>
                      <tr 
                        onClick={() => setExpandedAgent(expandedAgent === row.employee_id ? null : row.employee_id)}
                        className={`hover:bg-secondary/20 transition-colors cursor-pointer ${expandedAgent === row.employee_id ? 'bg-secondary/10' : ''}`}
                      >
                        <td className="px-4 py-3 text-muted-foreground">
                          {expandedAgent === row.employee_id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </td>
                        <td className="px-4 py-3 font-medium text-foreground">
                          {row.employee_name}
                        </td>
                        <td className="px-4 py-3 text-center font-semibold text-foreground">
                          {row.total_violations}
                        </td>
                        <td className="px-4 py-3 text-center text-red-400">{row.high_count || 0}</td>
                        <td className="px-4 py-3 text-center text-amber-400">{row.medium_count || 0}</td>
                        <td className="px-4 py-3 text-center text-yellow-400">{row.low_count || 0}</td>
                        <td className="px-4 py-3 text-center">
                          {row.hr_flagged_count > 0 ? (
                            <span className="px-2 py-0.5 bg-amber-500/10 text-amber-500 border border-amber-500/20 rounded-full text-[10px] font-bold">
                              {row.hr_flagged_count}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className={`font-semibold ${
                            row.total_deductions === 0 ? 'text-muted-foreground' :
                            row.total_deductions <= 20 ? 'text-amber-400' :
                            row.total_deductions <= 40 ? 'text-orange-400' : 'text-red-400'
                          }`}>
                            {row.total_deductions > 0 ? `-${row.total_deductions.toFixed(1)} pts` : "0 pts"}
                          </span>
                        </td>
                      </tr>
                      {expandedAgent === row.employee_id && (
                        <tr>
                          <td colSpan={8} className="p-0 border-b border-border">
                            <AgentViolationsInline employeeId={row.employee_id} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                  {filtered?.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">
                        No agents found matching "{search}".
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
