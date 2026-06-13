import { Badge } from '../ui/badge';
import { Card, CardContent } from '../ui/card';
import { RoleNote } from '../../lib/types';
import { KpiNoteCard } from './KpiNoteCard';

const PRIORITY_STYLES: Record<string, string> = {
  LOW: 'bg-slate-500/10 text-slate-300 border-slate-500/20',
  NORMAL: 'bg-blue-500/10 text-blue-300 border-blue-500/20',
  HIGH: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
  URGENT: 'bg-red-500/10 text-red-300 border-red-500/20',
};

const STATUS_STYLES: Record<string, string> = {
  OPEN: 'bg-violet-500/10 text-violet-300 border-violet-500/20',
  READ: 'bg-sky-500/10 text-sky-300 border-sky-500/20',
  IN_PROGRESS: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20',
  WAITING_REPLY: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
  RESOLVED: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
  ARCHIVED: 'bg-slate-500/10 text-slate-300 border-slate-500/20',
  DELETED: 'bg-red-500/10 text-red-300 border-red-500/20',
};

const VISIBILITY_STYLES: Record<string, string> = {
  INTERNAL: 'bg-slate-500/10 text-slate-300 border-slate-500/20',
  RECIPIENT_VISIBLE: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20',
  AGENT_VISIBLE: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
};

const TYPE_LABELS: Record<string, string> = {
  GENERAL: 'General',
  COACHING_NOTE: 'Coaching Note',
  COACHING_ESCALATION: 'Coaching Escalation',
  QA_REVIEW_REQUEST: 'QA Review Request',
  QA_DISPUTE: 'QA Dispute',
  OPS_ESCALATION: 'Ops Escalation',
  KPI_ALERT: 'KPI Alert',
  KPI_FOLLOW_UP: 'KPI Follow-up',
  TRANSFER_CONTEXT: 'Transfer Context',
  HR_COMPLIANCE: 'HR Compliance',
  CANDIDATE_REVIEW: 'Candidate Review',
  AI_DETECTION_REVIEW: 'AI Detection Review',
  SYSTEM_ISSUE: 'System Issue',
};

function formatToken(token: string | null | undefined) {
  if (!token) return '';
  return TYPE_LABELS[token] || token.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
}

export function NoteContextCard({ note, compact = false }: { note: RoleNote; compact?: boolean }) {
  const hasContext = Boolean(
    note.team_id ||
    note.campaign_id ||
    note.employee_id ||
    note.call_id ||
    note.kpi_key ||
    note.kpi_label,
  );

  return (
    <Card className="border-border/70 bg-secondary/20">
      <CardContent className={compact ? 'px-4 py-4 space-y-3' : 'px-5 py-5 space-y-4'}>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">{formatToken(note.note_type)}</Badge>
          <Badge className={PRIORITY_STYLES[note.priority] || PRIORITY_STYLES.NORMAL}>{formatToken(note.priority)}</Badge>
          <Badge className={STATUS_STYLES[note.status] || STATUS_STYLES.OPEN}>{formatToken(note.status)}</Badge>
          {note.visibility && (
            <Badge className={VISIBILITY_STYLES[note.visibility] || VISIBILITY_STYLES.INTERNAL}>
              {formatToken(note.visibility)}
            </Badge>
          )}
        </div>

        {hasContext ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {note.team_id && (
              <div className="rounded-lg border border-border/60 bg-background/40 px-3 py-2">
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Team</p>
                <p className="text-sm text-foreground font-medium">{note.team_name_snapshot || `Team #${note.team_id}`}</p>
              </div>
            )}
            {note.campaign_id && (
              <div className="rounded-lg border border-border/60 bg-background/40 px-3 py-2">
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Campaign</p>
                <p className="text-sm text-foreground font-medium">{note.campaign_name_snapshot || `Campaign #${note.campaign_id}`}</p>
              </div>
            )}
            {note.employee_id && (
              <div className="rounded-lg border border-border/60 bg-background/40 px-3 py-2">
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Employee</p>
                <p className="text-sm text-foreground font-medium">{note.agent_name_snapshot || `Employee #${note.employee_id}`}</p>
              </div>
            )}
            {note.call_id && (
              <div className="rounded-lg border border-border/60 bg-background/40 px-3 py-2">
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Call</p>
                <p className="text-sm text-foreground font-medium">Call #{note.call_id}</p>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">General workflow note with no linked business context.</p>
        )}

        {(note.kpi_key || note.kpi_label) && <KpiNoteCard note={note} />}
      </CardContent>
    </Card>
  );
}
