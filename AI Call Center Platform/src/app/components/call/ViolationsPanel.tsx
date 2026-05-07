import { AlertTriangle } from 'lucide-react';
import { SalesViolations } from '../../lib/types';

interface ViolationsPanelProps {
  violations?: SalesViolations;
}

export function ViolationsPanel({ violations }: ViolationsPanelProps) {
  if (!violations) return null;

  const flagged = Object.entries(violations).filter(([_, v]) => v.flagged);

  if (flagged.length === 0) {
    return (
      <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-5 mb-5">
        <div className="flex items-center gap-2 text-emerald-500 text-xs font-semibold">
          <CheckCircle2 size={14} />
          No Compliance Violations Detected
        </div>
      </div>
    );
  }

  return (
    <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-5 mb-5">
      <div className="flex items-center gap-2 mb-4 text-red-500">
        <AlertTriangle size={16} />
        <h3 className="text-sm font-semibold">Flagged Compliance Violations</h3>
      </div>
      
      <div className="space-y-4">
        {flagged.map(([key, data]) => (
          <div key={key} className="space-y-1.5">
            <span className="text-[10px] font-bold uppercase px-2 py-0.5 bg-red-500/20 text-red-400 rounded-md">
              {key.replace(/_/g, ' ')}
            </span>
            <p className="text-xs text-muted-foreground leading-relaxed pl-1">
              <span className="text-red-400/80 font-medium mr-1">Evidence:</span>
              {data.evidence}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

import { CheckCircle2 } from 'lucide-react';
