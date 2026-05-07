import { SalesPenalty } from '../../lib/types';
import { ShieldAlert } from 'lucide-react';

interface PenaltiesTableProps {
  penalties: SalesPenalty[];
}

export function PenaltiesTable({ penalties }: PenaltiesTableProps) {
  if (penalties.length === 0) return null;

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <ShieldAlert size={14} className="text-amber-500" />
        <h3 className="text-foreground text-sm font-semibold">HR Penalty Summary</h3>
      </div>
      
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-left text-xs">
          <thead className="bg-secondary/50 text-muted-foreground uppercase tracking-wider text-[10px]">
            <tr>
              <th className="px-4 py-2 font-semibold">Violation</th>
              <th className="px-4 py-2 font-semibold text-center">Qty</th>
              <th className="px-4 py-2 font-semibold">Penalty Level</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {penalties.map((p, idx) => (
              <tr key={idx} className="hover:bg-secondary/20 transition-colors">
                <td className="px-4 py-2.5 font-medium text-foreground">{p.violation}</td>
                <td className="px-4 py-2.5 text-center text-muted-foreground">{p.occurrence}</td>
                <td className="px-4 py-2.5">
                  <span className="px-2 py-0.5 bg-amber-500/10 text-amber-500 rounded-full font-bold">
                    {p.penalty}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
