import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { createNote, replyToNote } from '../../lib/api';
import {
  KpiCatalogItem,
  RoleNote,
  RoleNoteCreatePayload,
  RoleNotePriority,
  RoleNoteRecipient,
  RoleNoteType,
  RoleNoteVisibility,
} from '../../lib/types';
import { KPI_CATALOG, getKpiDefinition } from '../../lib/kpiCatalog';
import { Button } from '../ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Textarea } from '../ui/textarea';
import { NoteRecipientPicker } from './NoteRecipientPicker';
import { useApp } from '../../context/AppContext';

const CREATE_NOTE_TYPES: { value: RoleNoteType; label: string }[] = [
  { value: RoleNoteType.GENERAL, label: 'General' },
  { value: RoleNoteType.COACHING_NOTE, label: 'Coaching Note' },
  { value: RoleNoteType.COACHING_ESCALATION, label: 'Coaching Escalation' },
  { value: RoleNoteType.QA_REVIEW_REQUEST, label: 'QA Review Request' },
  { value: RoleNoteType.QA_DISPUTE, label: 'QA Dispute' },
  { value: RoleNoteType.OPS_ESCALATION, label: 'Ops Escalation' },
  { value: RoleNoteType.KPI_ALERT, label: 'KPI Alert' },
  { value: RoleNoteType.KPI_FOLLOW_UP, label: 'KPI Follow-up' },
  { value: RoleNoteType.TRANSFER_CONTEXT, label: 'Transfer Context' },
  { value: RoleNoteType.HR_COMPLIANCE, label: 'HR Compliance' },
  { value: RoleNoteType.SYSTEM_ISSUE, label: 'System Issue' },
];

const ROLE_NOTE_TYPES: Record<string, RoleNoteType[]> = {
  admin: [
    RoleNoteType.GENERAL,
    RoleNoteType.COACHING_NOTE,
    RoleNoteType.COACHING_ESCALATION,
    RoleNoteType.QA_REVIEW_REQUEST,
    RoleNoteType.QA_DISPUTE,
    RoleNoteType.OPS_ESCALATION,
    RoleNoteType.KPI_ALERT,
    RoleNoteType.KPI_FOLLOW_UP,
    RoleNoteType.TRANSFER_CONTEXT,
    RoleNoteType.HR_COMPLIANCE,
    RoleNoteType.SYSTEM_ISSUE,
  ],
  ops_manager: [RoleNoteType.GENERAL, RoleNoteType.OPS_ESCALATION, RoleNoteType.KPI_ALERT, RoleNoteType.QA_REVIEW_REQUEST, RoleNoteType.QA_DISPUTE],
  team_manager: [RoleNoteType.GENERAL, RoleNoteType.COACHING_ESCALATION, RoleNoteType.QA_REVIEW_REQUEST, RoleNoteType.QA_DISPUTE, RoleNoteType.KPI_FOLLOW_UP, RoleNoteType.TRANSFER_CONTEXT],
  team_leader: [RoleNoteType.GENERAL, RoleNoteType.COACHING_NOTE, RoleNoteType.QA_REVIEW_REQUEST, RoleNoteType.QA_DISPUTE, RoleNoteType.KPI_FOLLOW_UP],
  qa: [RoleNoteType.GENERAL, RoleNoteType.QA_REVIEW_REQUEST, RoleNoteType.QA_DISPUTE, RoleNoteType.HR_COMPLIANCE],
  hr_manager: [RoleNoteType.GENERAL, RoleNoteType.HR_COMPLIANCE, RoleNoteType.COACHING_NOTE],
  agent: [RoleNoteType.GENERAL, RoleNoteType.QA_DISPUTE],
};

const PRIORITY_OPTIONS = [
  { value: RoleNotePriority.LOW, label: 'Low' },
  { value: RoleNotePriority.NORMAL, label: 'Normal' },
  { value: RoleNotePriority.HIGH, label: 'High' },
  { value: RoleNotePriority.URGENT, label: 'Urgent' },
];

const VISIBILITY_OPTIONS = [
  { value: RoleNoteVisibility.INTERNAL, label: 'Internal' },
  { value: RoleNoteVisibility.RECIPIENT_VISIBLE, label: 'Recipient Visible' },
  { value: RoleNoteVisibility.AGENT_VISIBLE, label: 'Agent Visible' },
];

function parseOptionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : undefined;
}

interface NoteComposerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: (noteId: number) => void;
  initialValues?: Partial<RoleNoteCreatePayload>;
  replyToNoteId?: number;
  rootNote?: RoleNote;
}

export function NoteComposer({
  open,
  onOpenChange,
  onCreated,
  initialValues,
  replyToNoteId,
  rootNote,
}: NoteComposerProps) {
  const { userRole } = useApp();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [noteType, setNoteType] = useState<string>(RoleNoteType.GENERAL);
  const [priority, setPriority] = useState<string>(RoleNotePriority.NORMAL);
  const [visibility, setVisibility] = useState<string>(RoleNoteVisibility.INTERNAL);
  const [teamId, setTeamId] = useState('');
  const [campaignId, setCampaignId] = useState('');
  const [employeeId, setEmployeeId] = useState('');
  const [callId, setCallId] = useState('');
  const [selectedKpiKey, setSelectedKpiKey] = useState('');
  const [currentValue, setCurrentValue] = useState('');
  const [targetValue, setTargetValue] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [recipientId, setRecipientId] = useState<number | undefined>(undefined);
  const [availableRecipients, setAvailableRecipients] = useState<RoleNoteRecipient[]>([]);

  const isReplyMode = Boolean(replyToNoteId && rootNote);
  const isKpiNote = noteType === RoleNoteType.KPI_ALERT || noteType === RoleNoteType.KPI_FOLLOW_UP;
  const selectedKpiDefinition = getKpiDefinition(selectedKpiKey || initialValues?.kpi_key || rootNote?.kpi_key || undefined);
  const allowedNoteTypes = (ROLE_NOTE_TYPES[userRole] || ROLE_NOTE_TYPES.admin)
    .map((value) => CREATE_NOTE_TYPES.find((option) => option.value === value) || { value, label: value.replace(/_/g, ' ') });
  const lockedFields = {
    teamId: initialValues?.team_id !== undefined,
    campaignId: initialValues?.campaign_id !== undefined,
    employeeId: initialValues?.employee_id !== undefined,
    callId: initialValues?.call_id !== undefined,
    noteType: initialValues?.note_type !== undefined,
    kpiKey: initialValues?.kpi_key !== undefined,
  };

  const contextSummary = [
    teamId ? `Team #${teamId}` : null,
    campaignId ? `Campaign #${campaignId}` : null,
    employeeId ? `Employee #${employeeId}` : null,
    callId ? `Call #${callId}` : null,
  ].filter(Boolean).join(' - ');

  useEffect(() => {
    if (!open) return;

    const fallbackTitle = initialValues?.title || (isReplyMode && rootNote ? `Re: ${rootNote.title}` : '');
    setTitle(fallbackTitle);
    setBody(initialValues?.body || '');
    setNoteType(initialValues?.note_type || rootNote?.note_type || RoleNoteType.GENERAL);
    setPriority(initialValues?.priority || rootNote?.priority || RoleNotePriority.NORMAL);
    setVisibility(initialValues?.visibility || rootNote?.visibility || RoleNoteVisibility.INTERNAL);
    setTeamId(initialValues?.team_id ? String(initialValues.team_id) : rootNote?.team_id ? String(rootNote.team_id) : '');
    setCampaignId(initialValues?.campaign_id ? String(initialValues.campaign_id) : rootNote?.campaign_id ? String(rootNote.campaign_id) : '');
    setEmployeeId(initialValues?.employee_id ? String(initialValues.employee_id) : rootNote?.employee_id ? String(rootNote.employee_id) : '');
    setCallId(initialValues?.call_id ? String(initialValues.call_id) : rootNote?.call_id ? String(rootNote.call_id) : '');
    setSelectedKpiKey(initialValues?.kpi_key || rootNote?.kpi_key || '');
    setCurrentValue(initialValues?.current_value !== undefined ? String(initialValues.current_value) : rootNote?.current_value !== null && rootNote?.current_value !== undefined ? String(rootNote.current_value) : '');
    setTargetValue(initialValues?.target_value !== undefined ? String(initialValues.target_value) : rootNote?.target_value !== null && rootNote?.target_value !== undefined ? String(rootNote.target_value) : '');
    setPeriodStart(initialValues?.period_start ? initialValues.period_start.slice(0, 10) : rootNote?.period_start ? rootNote.period_start.slice(0, 10) : '');
    setPeriodEnd(initialValues?.period_end ? initialValues.period_end.slice(0, 10) : rootNote?.period_end ? rootNote.period_end.slice(0, 10) : '');
    setRecipientId(initialValues?.recipient_id);
    setAvailableRecipients([]);
  }, [initialValues, isReplyMode, open, rootNote]);

  useEffect(() => {
    if (!open || isReplyMode) return;
    if (!title.trim()) {
      const defaultTitles: Partial<Record<RoleNoteType, string>> = {
        [RoleNoteType.QA_REVIEW_REQUEST]: callId ? `QA review request for call #${callId}` : 'QA review request',
        [RoleNoteType.QA_DISPUTE]: callId ? `QA dispute for call #${callId}` : 'QA dispute',
        [RoleNoteType.COACHING_NOTE]: employeeId ? `Coaching note for employee #${employeeId}` : 'Coaching note',
        [RoleNoteType.COACHING_ESCALATION]: employeeId ? `Coaching escalation for employee #${employeeId}` : 'Coaching escalation',
        [RoleNoteType.KPI_ALERT]: selectedKpiDefinition ? `${selectedKpiDefinition.label} KPI alert` : 'KPI alert',
        [RoleNoteType.KPI_FOLLOW_UP]: selectedKpiDefinition ? `${selectedKpiDefinition.label} KPI follow-up` : 'KPI follow-up',
      };
      const suggested = defaultTitles[noteType as RoleNoteType];
      if (suggested) {
        setTitle(suggested);
      }
    }
  }, [callId, employeeId, isReplyMode, noteType, open, selectedKpiDefinition, title]);

  useEffect(() => {
    if (!isKpiNote || !selectedKpiKey) return;
    const definition = KPI_CATALOG.find((item) => item.key === selectedKpiKey);
    if (!definition) return;
  }, [isKpiNote, selectedKpiKey]);

  const notePayload = useMemo<RoleNoteCreatePayload>(() => ({
    title: title.trim(),
    body: body.trim(),
    note_type: noteType,
    priority,
    visibility,
    team_id: parseOptionalNumber(teamId),
    campaign_id: parseOptionalNumber(campaignId),
    employee_id: parseOptionalNumber(employeeId),
    call_id: parseOptionalNumber(callId),
    recipient_id: recipientId,
    kpi_key: isKpiNote ? selectedKpiKey || undefined : undefined,
    kpi_label: isKpiNote ? selectedKpiDefinition?.label : undefined,
    current_value: isKpiNote ? parseOptionalNumber(currentValue) : undefined,
    target_value: isKpiNote ? parseOptionalNumber(targetValue) : undefined,
    period_start: isKpiNote && periodStart ? new Date(periodStart).toISOString() : undefined,
    period_end: isKpiNote && periodEnd ? new Date(periodEnd).toISOString() : undefined,
  }), [body, callId, campaignId, currentValue, employeeId, isKpiNote, noteType, periodEnd, periodStart, priority, recipientId, selectedKpiDefinition?.label, selectedKpiKey, targetValue, teamId, title, visibility]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (isReplyMode && replyToNoteId) {
        return replyToNote(replyToNoteId, notePayload);
      }
      return createNote(notePayload);
    },
    onSuccess: async (note) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['notes'] }),
        queryClient.invalidateQueries({ queryKey: ['note-thread'] }),
      ]);
      toast.success(isReplyMode ? 'Reply posted.' : 'Workflow note created.');
      onOpenChange(false);
      onCreated?.(note.id);
    },
    onError: (error) => {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Unable to submit the note.');
    },
  });

  const canSubmit = Boolean(
    title.trim() &&
    body.trim() &&
    (isReplyMode || recipientId) &&
    (isReplyMode || availableRecipients.length > 0) &&
    (!isKpiNote || (
      selectedKpiKey &&
      currentValue.trim() &&
      targetValue.trim() &&
      periodStart &&
      periodEnd &&
      teamId.trim()
    ))
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{isReplyMode ? 'Reply to Workflow Note' : 'Create Workflow Note'}</DialogTitle>
          <DialogDescription>
            Structured notes stay linked to workflow context and recipient scope.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          {contextSummary && (
            <div className="rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
              <p className="text-[11px] uppercase tracking-wide text-primary/80">Linked Context</p>
              <p className="text-sm text-foreground mt-1">{contextSummary}</p>
              <p className="text-[11px] text-muted-foreground mt-2">This context was prefilled from the workflow page that launched the note.</p>
            </div>
          )}

          {!isReplyMode && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="note-type">Note Type</Label>
                <Select value={noteType} onValueChange={setNoteType} disabled={lockedFields.noteType}>
                  <SelectTrigger id="note-type">
                    <SelectValue placeholder="Select note type" />
                  </SelectTrigger>
                  <SelectContent>
                    {allowedNoteTypes.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="note-priority">Priority</Label>
                <Select value={priority} onValueChange={setPriority}>
                  <SelectTrigger id="note-priority">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORITY_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="note-visibility">Visibility</Label>
                <Select value={visibility} onValueChange={setVisibility}>
                  <SelectTrigger id="note-visibility">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {VISIBILITY_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="note-title">Title</Label>
              <Input id="note-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Short operational summary" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="note-recipient">Recipient</Label>
              {isReplyMode ? (
                <div className="h-9 rounded-md border border-border bg-secondary/20 px-3 flex items-center text-sm text-muted-foreground">
                  Reply recipient is resolved from the existing thread.
                </div>
              ) : (
                <NoteRecipientPicker
                  noteType={noteType}
                  teamId={parseOptionalNumber(teamId)}
                  campaignId={parseOptionalNumber(campaignId)}
                  employeeId={parseOptionalNumber(employeeId)}
                  callId={parseOptionalNumber(callId)}
                  value={recipientId}
                  onChange={setRecipientId}
                  onRecipientsChange={setAvailableRecipients}
                />
              )}
            </div>
          </div>

          {!isReplyMode && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="note-team-id">Team ID</Label>
                <Input id="note-team-id" inputMode="numeric" value={teamId} onChange={(event) => setTeamId(event.target.value)} placeholder="Optional" readOnly={lockedFields.teamId} />
                {lockedFields.teamId && <p className="text-[11px] text-muted-foreground">Locked from source context.</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="note-campaign-id">Campaign ID</Label>
                <Input id="note-campaign-id" inputMode="numeric" value={campaignId} onChange={(event) => setCampaignId(event.target.value)} placeholder="Optional" readOnly={lockedFields.campaignId} />
                {lockedFields.campaignId && <p className="text-[11px] text-muted-foreground">Locked from source context.</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="note-employee-id">Employee ID</Label>
                <Input id="note-employee-id" inputMode="numeric" value={employeeId} onChange={(event) => setEmployeeId(event.target.value)} placeholder="Optional" readOnly={lockedFields.employeeId} />
                {lockedFields.employeeId && <p className="text-[11px] text-muted-foreground">Locked from source context.</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="note-call-id">Call ID</Label>
                <Input id="note-call-id" inputMode="numeric" value={callId} onChange={(event) => setCallId(event.target.value)} placeholder="Optional" readOnly={lockedFields.callId} />
                {lockedFields.callId && <p className="text-[11px] text-muted-foreground">Locked from source context.</p>}
              </div>
            </div>
          )}

          {!isReplyMode && isKpiNote && (
            <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 px-4 py-4 space-y-4">
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">KPI workflow context</p>
                <p className="text-xs text-muted-foreground">KPI notes require a fixed KPI definition and measured period.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="kpi-catalog">KPI</Label>
                  <Select value={selectedKpiKey} onValueChange={setSelectedKpiKey} disabled={lockedFields.kpiKey}>
                    <SelectTrigger id="kpi-catalog">
                      <SelectValue placeholder="Select KPI" />
                    </SelectTrigger>
                    <SelectContent>
                      {KPI_CATALOG.map((item: KpiCatalogItem) => (
                        <SelectItem key={item.key} value={item.key}>{item.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {selectedKpiDefinition && <p className="text-[11px] text-muted-foreground">{selectedKpiDefinition.description}</p>}
                  {lockedFields.kpiKey && <p className="text-[11px] text-muted-foreground">Locked from source context.</p>}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="kpi-key-preview">Resolved KPI Key</Label>
                  <Input id="kpi-key-preview" value={selectedKpiDefinition?.key || ''} readOnly placeholder="Auto-filled from catalog" />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="kpi-current">Current Value</Label>
                  <Input id="kpi-current" value={currentValue} onChange={(event) => setCurrentValue(event.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="kpi-target">Target Value</Label>
                  <Input id="kpi-target" value={targetValue} onChange={(event) => setTargetValue(event.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="kpi-period-start">Period Start</Label>
                  <Input id="kpi-period-start" type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="kpi-period-end">Period End</Label>
                  <Input id="kpi-period-end" type="date" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} required />
                </div>
              </div>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="note-body">Body</Label>
            <Textarea
              id="note-body"
              value={body}
              onChange={(event) => setBody(event.target.value)}
              placeholder="Describe the issue, request, or action needed."
              className="min-h-32"
            />
          </div>
        </div>

        <DialogFooter>
          {!isReplyMode && availableRecipients.length === 0 && (
            <p className="text-xs text-amber-300 mr-auto">Submission is blocked until the backend resolves a valid recipient for this workflow context.</p>
          )}
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={() => mutation.mutate()} disabled={!canSubmit || mutation.isPending}>
            {mutation.isPending ? 'Submitting...' : isReplyMode ? 'Post Reply' : 'Create Note'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
