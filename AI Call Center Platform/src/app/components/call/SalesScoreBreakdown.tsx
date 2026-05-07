import { SalesScoreBreakdown as BreakdownType } from '../../lib/types';

interface SalesScoreBreakdownProps {
  breakdown?: BreakdownType;
}

export function SalesScoreBreakdown({ breakdown }: SalesScoreBreakdownProps) {
  if (!breakdown) return null;

  const items = [
    { label: 'Opening', value: breakdown.opening, max: 10 },
    { label: 'Script Compliance', value: breakdown.script_compliance, max: 30 },
    { label: 'Customer Handling', value: breakdown.customer_handling, max: 20 },
    { label: 'Conduct', value: breakdown.conduct, max: 25 },
    { label: 'Closing', value: breakdown.closing, max: 15 },
  ];

  return (
    <div className="bg-card border border-border rounded-xl p-5 mb-5">
      <h3 className="text-foreground text-sm font-semibold mb-4">Sales Score Breakdown</h3>
      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.label} className="space-y-1.5">
            <div className="flex justify-between text-[11px]">
              <span className="text-muted-foreground uppercase tracking-wider">{item.label}</span>
              <span className="text-foreground font-medium">{item.value} / {item.max}</span>
            </div>
            <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary rounded-full transition-all duration-500"
                style={{ width: `${(item.value / item.max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
