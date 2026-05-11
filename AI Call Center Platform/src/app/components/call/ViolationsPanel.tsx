import { AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";
import { CallViolation } from "../../../lib/types";

interface ViolationsPanelProps {
  violations?: CallViolation[];
}

const SEVERITY_CONFIG = {
  high:   { label: "HIGH",   dot: "bg-red-500",    badge: "bg-red-500/10 text-red-400 border-red-500/20" },
  medium: { label: "MEDIUM", dot: "bg-amber-500",  badge: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  low:    { label: "LOW",    dot: "bg-yellow-500", badge: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20" },
};

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

export function ViolationsPanel({ violations }: ViolationsPanelProps) {
  // Clean call — show green banner
  if (!violations || violations.length === 0) {
    return (
      <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-5 mb-5">
        <div className="flex items-center gap-2 text-emerald-500 text-xs font-semibold">
          <CheckCircle2 size={14} />
          No Compliance Violations Detected
        </div>
      </div>
    );
  }

  const hasHRFlag = violations.some(v => v.hr_flagged);
  const hasAutoFail = violations.some(v => v.auto_fail);
  const totalDeduction = violations.reduce((sum, v) => sum + v.score_deduction, 0);

  return (
    <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-5 mb-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-red-400">
          <AlertTriangle size={16} />
          <h3 className="text-sm font-semibold">
            Flagged Violations ({violations.length})
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {hasAutoFail && (
            <span className="text-xs px-2 py-0.5 bg-red-500/20 text-red-400
                             border border-red-500/30 rounded-full font-bold">
              AUTO-FAIL
            </span>
          )}
          {hasHRFlag && (
            <span className="flex items-center gap-1 text-xs px-2 py-0.5
                             bg-amber-500/10 text-amber-400 border
                             border-amber-500/20 rounded-full">
              <ShieldAlert size={10} /> HR Flagged
            </span>
          )}
          <span className="text-xs text-red-400 font-semibold">
            -{totalDeduction.toFixed(0)} pts total
          </span>
        </div>
      </div>

      {/* Violations list */}
      <div className="space-y-3">
        {violations.map((v) => {
          const sc = SEVERITY_CONFIG[v.severity];
          return (
            <div key={v.id}
                 className="bg-card border border-border rounded-xl p-4 space-y-2">
              {/* Top row */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Severity badge */}
                  <span className={`text-9px font-bold px-2 py-0.5 rounded-md
                                   border uppercase ${sc?.badge || ""}`}>
                    <span className={`inline-block size-1.5 rounded-full
                                     ${sc?.dot || ""} mr-1`} />
                    {sc?.label || v.severity}
                  </span>
                  {/* Violation name */}
                  <span className="text-xs font-semibold text-foreground">
                    {v.violation_id.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
                  </span>
                  {/* Occurrence badge */}
                  <span className="text-9px px-1.5 py-0.5 bg-secondary
                                   text-muted-foreground rounded-md">
                    {v.occurrence === 1 ? "1st offense"
                     : v.occurrence === 2 ? "2nd offense"
                     : "3rd+ offense"}
                  </span>
                </div>
                {/* Penalty + deduction */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-xs font-bold ${PENALTY_COLOR[v.penalty_tier] || ""}`}>
                    {v.penalty_tier}
                  </span>
                  {v.score_deduction > 0 && (
                    <span className="text-xs text-red-400">
                      -{v.score_deduction}pts
                    </span>
                  )}
                </div>
              </div>

              {/* Evidence */}
              {v.evidence && (
                <p className="text-xs text-muted-foreground pl-1 leading-relaxed">
                  <span className="text-red-400/80 font-medium mr-1">Evidence:</span>
                  {v.timestamp_in_call && (
                    <span className="text-primary mr-1">[{v.timestamp_in_call}]</span>
                  )}
                  {v.evidence}
                </p>
              )}

              {/* HR / Auto-fail flags */}
              <div className="flex gap-2">
                {v.hr_flagged && (
                  <span className="text-9px px-1.5 py-0.5 bg-amber-500/10
                                   text-amber-400 rounded-md border
                                   border-amber-500/20">
                    HR Notified
                  </span>
                )}
                {v.auto_fail && (
                  <span className="text-9px px-1.5 py-0.5 bg-red-500/20
                                   text-red-400 rounded-md border
                                   border-red-500/20">
                    Auto-Fail
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
