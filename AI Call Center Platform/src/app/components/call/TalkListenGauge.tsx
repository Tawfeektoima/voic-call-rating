import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Mic, User } from 'lucide-react';

interface Props {
  agentSeconds: number;
  customerSeconds: number;
  silenceSeconds?: number;
}

const formatTime = (s: number) => {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, '0')}`;
};

export function TalkListenGauge({ agentSeconds, customerSeconds, silenceSeconds = 0 }: Props) {
  const total = agentSeconds + customerSeconds + silenceSeconds;
  const ratio = customerSeconds / agentSeconds;
  const agentPct = Math.round((agentSeconds / total) * 100);
  const customerPct = Math.round((customerSeconds / total) * 100);
  const silencePct = 100 - agentPct - customerPct;

  const ratioLabel = ratio > 1.2 ? 'Customer Dominant' : ratio < 0.7 ? 'Agent Dominant' : 'Balanced';
  const ratioColor = ratio >= 0.8 && ratio <= 1.3 ? '#10b981' : ratio < 0.6 || ratio > 1.6 ? '#ef4444' : '#f59e0b';

  const data = [
    { name: 'Agent', value: agentSeconds, color: 'var(--primary)' },
    { name: 'Customer', value: customerSeconds, color: '#06b6d4' },
    ...(silenceSeconds > 0 ? [{ name: 'Silence', value: silenceSeconds, color: 'var(--muted)' }] : []),
  ];

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h3 className="text-foreground text-sm font-semibold mb-4">Talk-to-Listen Ratio</h3>

      <div className="flex items-center gap-6">
        {/* Donut */}
        <div className="relative h-28 w-28 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={36}
                outerRadius={52}
                paddingAngle={2}
                dataKey="value"
                startAngle={90}
                endAngle={-270}
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }}
                formatter={(v: number) => [formatTime(v), '']}
              />
            </PieChart>
          </ResponsiveContainer>
          {/* Center label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-foreground text-sm font-bold">{ratio.toFixed(2)}</span>
            <span className="text-muted-foreground text-xs">ratio</span>
          </div>
        </div>

        {/* Stats */}
        <div className="flex-1 space-y-3">
          {/* Agent */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5">
                <Mic size={12} className="text-primary" />
                <span className="text-xs text-foreground">Agent</span>
              </div>
              <span className="text-xs text-muted-foreground">{formatTime(agentSeconds)} · {agentPct}%</span>
            </div>
            <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
              <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${agentPct}%` }} />
            </div>
          </div>

          {/* Customer */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5">
                <User size={12} className="text-cyan-400" />
                <span className="text-xs text-foreground">Customer</span>
              </div>
              <span className="text-xs text-muted-foreground">{formatTime(customerSeconds)} · {customerPct}%</span>
            </div>
            <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
              <div className="h-full bg-cyan-500 rounded-full transition-all" style={{ width: `${customerPct}%` }} />
            </div>
          </div>

          {silenceSeconds > 0 && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">Silence</span>
                <span className="text-xs text-muted-foreground">{formatTime(silenceSeconds)} · {silencePct}%</span>
              </div>
              <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                <div className="h-full bg-muted-foreground/30 rounded-full" style={{ width: `${silencePct}%` }} />
              </div>
            </div>
          )}

          {/* Ratio badge */}
          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-muted-foreground">Balance</span>
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: ratioColor + '20', color: ratioColor }}>
              {ratioLabel}
            </span>
          </div>
        </div>
      </div>

      {/* Formula note */}
      <div className="mt-3 px-3 py-2 bg-secondary/50 rounded-lg">
        <p className="text-xs text-muted-foreground font-mono">Ratio = Customer(s) ÷ Agent(s) = {customerSeconds} ÷ {agentSeconds} = <span className="text-foreground">{ratio.toFixed(2)}</span></p>
      </div>
    </div>
  );
}
