import { CheckCircle, AlertCircle, TrendingUp, Award } from 'lucide-react';
import { cn } from '../ui/utils';

interface Weakness {
  issue: string;
  detail: string;
  deduction: number;
}

interface Props {
  strengths: string[];
  weaknesses: Weakness[];
}

export function CallAnalysis({ strengths, weaknesses }: Props) {
  const hasStrengths = strengths && strengths.length > 0;
  const hasWeaknesses = weaknesses && weaknesses.length > 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {/* Strengths Section */}
      <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <div className="size-6 rounded-lg bg-emerald-500/15 flex items-center justify-center">
            <Award size={14} className="text-emerald-400" />
          </div>
          <h3 className="text-foreground text-sm font-semibold">Strengths & Achievements</h3>
        </div>
        
        <div className="space-y-3">
          {hasStrengths ? (
            strengths.map((s, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-lg group hover:bg-emerald-500/8 transition-all">
                <CheckCircle size={14} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-foreground font-medium leading-tight">{s}</p>
              </div>
            ))
          ) : (
            <p className="text-xs text-muted-foreground italic px-2">No notable strengths identified in this call.</p>
          )}
        </div>
      </div>

      {/* Weaknesses Section */}
      <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <div className="size-6 rounded-lg bg-red-500/15 flex items-center justify-center">
            <TrendingUp size={14} className="text-red-400 rotate-180" />
          </div>
          <h3 className="text-foreground text-sm font-semibold">Deductions & Weaknesses</h3>
        </div>

        <div className="space-y-3">
          {hasWeaknesses ? (
            weaknesses.map((w, i) => (
              <div key={i} className="p-3 bg-red-500/5 border border-red-500/10 rounded-lg group hover:bg-red-500/8 transition-all">
                <div className="flex justify-between items-start gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <AlertCircle size={12} className="text-red-400" />
                    <span className="text-xs font-semibold text-red-400">{w.issue}</span>
                  </div>
                  <span className="text-xs font-bold text-red-400">-{w.deduction}</span>
                </div>
                <p className="text-[10px] text-muted-foreground leading-relaxed pl-5">{w.detail}</p>
              </div>
            ))
          ) : (
            <p className="text-xs text-muted-foreground italic px-2">Perfect performance! No weaknesses identified.</p>
          )}
        </div>
      </div>
    </div>
  );
}
