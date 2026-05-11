// src/app/components/call/ViolationItem.tsx
import { ViolationItemOut } from "../../lib/types";

const severityColor = {
  low: "border-yellow-400 text-yellow-600",
  medium: "border-orange-400 text-orange-600",
  high: "border-red-500 text-red-600",
  critical: "border-red-700 text-red-800",
};

export const ViolationItem = ({ violation }: { violation: ViolationItemOut }) => (
  <div className={`border-l-4 pl-3 mb-4 ${severityColor[violation.severity as keyof typeof severityColor] || "border-gray-400 text-gray-600"}`}>
    <div className="font-semibold uppercase tracking-wide">
      {violation.violation_id.replace(/_/g, " ")}
    </div>
    <div className="text-sm text-muted-foreground">
      Severity:{" "}
      <span className="font-medium capitalize">{violation.severity}</span>
      {violation.timestamp && ` · At ${violation.timestamp}`}
    </div>
    {violation.evidence && (
      <div className="text-sm italic text-muted-foreground mt-1">
        "{violation.evidence}"
      </div>
    )}
  </div>
);
