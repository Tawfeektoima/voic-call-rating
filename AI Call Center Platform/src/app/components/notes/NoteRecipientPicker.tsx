import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getNoteRecipients } from '../../lib/api';
import { RoleNoteRecipient } from '../../lib/types';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';

interface NoteRecipientPickerProps {
  noteType: string;
  teamId?: number;
  campaignId?: number;
  employeeId?: number;
  callId?: number;
  value?: number;
  onChange: (recipientId?: number) => void;
  onRecipientsChange?: (recipients: RoleNoteRecipient[]) => void;
  disabled?: boolean;
}

function buildContextHint({
  teamId,
  campaignId,
  employeeId,
  callId,
}: {
  teamId?: number;
  campaignId?: number;
  employeeId?: number;
  callId?: number;
}) {
  const labels = [
    teamId ? `team #${teamId}` : null,
    campaignId ? `campaign #${campaignId}` : null,
    employeeId ? `employee #${employeeId}` : null,
    callId ? `call #${callId}` : null,
  ].filter(Boolean);

  if (labels.length === 0) {
    return 'Add workflow context to let the backend resolve an allowed recipient.';
  }

  return `Resolved from ${labels.join(', ')} using backend hierarchy rules.`;
}

export function NoteRecipientPicker({
  noteType,
  teamId,
  campaignId,
  employeeId,
  callId,
  value,
  onChange,
  onRecipientsChange,
  disabled,
}: NoteRecipientPickerProps) {
  const shouldLoad = Boolean(noteType);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['note-recipients', noteType, teamId, campaignId, employeeId, callId],
    enabled: shouldLoad,
    queryFn: () => getNoteRecipients({
      note_type: noteType,
      team_id: teamId,
      campaign_id: campaignId,
      employee_id: employeeId,
      call_id: callId,
    }),
  });

  const recipients = data || [];

  useEffect(() => {
    onRecipientsChange?.(recipients);
  }, [onRecipientsChange, recipients]);

  useEffect(() => {
    if (!value && recipients.length === 1) {
      onChange(recipients[0].id);
    }
  }, [onChange, recipients, value]);

  useEffect(() => {
    if (value && recipients.length > 0 && !recipients.some((recipient) => recipient.id === value)) {
      onChange(undefined);
    }
  }, [onChange, recipients, value]);

  if (!shouldLoad) {
    return <p className="text-xs text-muted-foreground">Choose a note type to resolve the allowed recipient list.</p>;
  }

  if (isError) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    return (
      <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-3 space-y-1">
        <p className="text-xs font-medium text-red-300">{typeof detail === 'string' ? detail : 'Failed to load recipients for this context.'}</p>
        <p className="text-[11px] text-red-200/80">{buildContextHint({ teamId, campaignId, employeeId, callId })}</p>
      </div>
    );
  }

  if (!isLoading && recipients.length === 0) {
    return (
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-3 space-y-1">
        <p className="text-xs font-medium text-amber-300">No valid recipient for this context.</p>
        <p className="text-[11px] text-amber-200/80">{buildContextHint({ teamId, campaignId, employeeId, callId })}</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Select
        value={value ? String(value) : undefined}
        onValueChange={(nextValue) => onChange(nextValue ? Number(nextValue) : undefined)}
        disabled={disabled || isLoading || recipients.length === 0}
      >
        <SelectTrigger>
          <SelectValue placeholder={isLoading ? 'Resolving recipients...' : 'Select recipient'} />
        </SelectTrigger>
        <SelectContent>
          {recipients.map((recipient) => (
            <SelectItem key={recipient.id} value={String(recipient.id)}>
              {recipient.name} ({recipient.role.replace(/_/g, ' ')})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p className="text-[11px] text-muted-foreground">
        {value
          ? recipients.find((recipient) => recipient.id === value)?.reason || 'Recipients are resolved by backend hierarchy and scope rules.'
          : buildContextHint({ teamId, campaignId, employeeId, callId })}
      </p>
    </div>
  );
}
