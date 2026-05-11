import { ShieldAlert } from "lucide-react";
import { CallViolation } from "../../lib/types";

interface PenaltiesTableProps {
  violations?: CallViolation[];
  penalties?: any[]; // For backwards compatibility during transition if needed
}

export function PenaltiesTable({ violations, penalties }: PenaltiesTableProps) {
  // Use either violations (new) or penalties (old)
  const displayViolations = violations || [];
  
  if (displayViolations.length === 0) return null;

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
              <th className="px-4 py-2 font-semibold text-center">Offense #</th>
              <th className="px-4 py-2 font-semibold">Penalty</th>
              <th className="px-4 py-2 font-semibold text-center">Deduction</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {displayViolations.map((v) => (
              <tr key={v.id} className="hover:bg-secondary/20 transition-colors">
                <td className="px-4 py-2.5 font-medium text-foreground capitalize">
                  {v.violation_id.replace(/_/g, " ")}
                </td>
                <td className="px-4 py-2.5 text-center text-muted-foreground">
                  {v.occurrence}
                </td>
                <td className="px-4 py-2.5">
                  <span className="px-2 py-0.5 bg-amber-500/10 text-amber-500 rounded-full font-bold">
                    {v.penalty_tier}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-center text-red-400 font-semibold">
                  {v.score_deduction > 0 ? `-${v.score_deduction}` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
