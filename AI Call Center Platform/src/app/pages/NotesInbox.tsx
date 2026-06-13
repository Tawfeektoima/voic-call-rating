import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router';
import { AxiosError } from 'axios';
import { MessageSquarePlus, Inbox, Send, CheckCheck, Eye, Target, ShieldAlert, Users, ArrowUpRight } from 'lucide-react';
import { getNotesInbox, getSentNotes, markNoteRead, resolveNote } from '../lib/api';
import { RoleNote, RoleNoteStatus, RoleNoteType } from '../lib/types';
import { NoteComposer } from '../components/notes/NoteComposer';
import { NoteContextCard } from '../components/notes/NoteContextCard';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { EmptyState, ErrorState, PageLoader } from '../components/ui/states';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useApp } from '../context/AppContext';
import { buildNotesComposeUrl } from '../lib/noteNavigation';
const NOTE_TYPE_FILTERS = [
  'ALL',
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
];

const STATUS_FILTERS = [
  'ALL',
  RoleNoteStatus.OPEN,
  RoleNoteStatus.READ,
  RoleNoteStatus.IN_PROGRESS,
  RoleNoteStatus.WAITING_REPLY,
  RoleNoteStatus.RESOLVED,
  RoleNoteStatus.ARCHIVED,
];

function normalizeLabel(value: string) {
  return value.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
}

function parseNumberParam(value: string | null) {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function NotesInbox() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { currentUser } = useApp();
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<'inbox' | 'sent'>('inbox');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [composerOpen, setComposerOpen] = useState(searchParams.get('compose') === '1');

  const filters = useMemo(() => ({
    status: statusFilter === 'ALL' ? undefined : statusFilter,
    note_type: typeFilter === 'ALL' ? undefined : typeFilter,
    limit: 100,
  }), [statusFilter, typeFilter]);

  const query = useQuery({
    queryKey: ['notes', activeTab, filters],
    queryFn: () => activeTab === 'inbox' ? getNotesInbox(filters) : getSentNotes(filters),
  });

  const readMutation = useMutation({
    mutationFn: (noteId: number) => markNoteRead(noteId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['notes'] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: (noteId: number) => resolveNote(noteId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['notes'] });
    },
  });

  const notes = query.data || [];
  const pendingCount = notes.filter((note) => [RoleNoteStatus.OPEN, RoleNoteStatus.IN_PROGRESS, RoleNoteStatus.WAITING_REPLY].includes(note.status as RoleNoteStatus)).length;
  const resolvedCount = notes.filter((note) => note.status === RoleNoteStatus.RESOLVED).length;

  const initialValues = useMemo(() => ({
    note_type: searchParams.get('noteType') || undefined,
    team_id: parseNumberParam(searchParams.get('teamId')),
    campaign_id: parseNumberParam(searchParams.get('campaignId')),
    employee_id: parseNumberParam(searchParams.get('employeeId')),
    call_id: parseNumberParam(searchParams.get('callId')),
    title: searchParams.get('title') || undefined,
    kpi_key: searchParams.get('kpiKey') || undefined,
    kpi_label: searchParams.get('kpiLabel') || undefined,
    current_value: parseNumberParam(searchParams.get('currentValue')),
    target_value: parseNumberParam(searchParams.get('targetValue')),
    period_start: searchParams.get('periodStart') || undefined,
    period_end: searchParams.get('periodEnd') || undefined,
  }), [searchParams]);

  const error = query.error as AxiosError<{ detail?: string }> | null;
  const isForbidden = error?.response?.status === 403;

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground font-semibold">Workflow Communication</p>
          <h1 className="text-2xl font-semibold text-foreground">Operational Notes</h1>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Structured notes stay attached to calls, people, teams, and workflow context. Visibility and recipients are enforced by the backend.
          </p>
        </div>
        <Button onClick={() => setComposerOpen(true)}>
          <MessageSquarePlus size={16} />
          Create Note
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Queue</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-foreground">{pendingCount}</p>
            <p className="text-xs text-muted-foreground mt-1">Open, in progress, or waiting for reply.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Resolved</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-foreground">{resolvedCount}</p>
            <p className="text-xs text-muted-foreground mt-1">Closed conversations still remain searchable.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Session Role</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-foreground">{currentUser?.role.replace(/_/g, ' ')}</p>
            <p className="text-xs text-muted-foreground mt-1">This view is filtered by backend scope rules.</p>
          </CardContent>
        </Card>
      </div>

      <QuickActions
        role={currentUser?.role}
        onLaunch={(url) => {
          navigate(url);
          setComposerOpen(true);
        }}
      />

      <Card>
        <CardContent className="pt-6 space-y-5">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <Tabs value={activeTab} onValueChange={(nextValue) => setActiveTab(nextValue as 'inbox' | 'sent')} className="gap-4">
              <TabsList>
                <TabsTrigger value="inbox"><Inbox size={14} /> Inbox</TabsTrigger>
                <TabsTrigger value="sent"><Send size={14} /> Sent</TabsTrigger>
              </TabsList>
              <TabsContent value={activeTab} />
            </Tabs>

            <div className="flex flex-col sm:flex-row gap-3">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-44">
                  <SelectValue placeholder="Filter status" />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_FILTERS.map((status) => (
                    <SelectItem key={status} value={status}>{normalizeLabel(status)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-full sm:w-52">
                  <SelectValue placeholder="Filter type" />
                </SelectTrigger>
                <SelectContent>
                  {NOTE_TYPE_FILTERS.map((type) => (
                    <SelectItem key={type} value={type}>{normalizeLabel(type)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {query.isLoading ? (
            <PageLoader message="Loading workflow notes..." />
          ) : isForbidden ? (
            <ErrorState message="You do not have access to the notes workspace for this session." />
          ) : query.isError ? (
            <ErrorState message={error?.response?.data?.detail || 'Unable to load workflow notes right now.'} onRetry={() => query.refetch()} />
          ) : notes.length === 0 ? (
            <EmptyState
              icon={activeTab === 'inbox' ? Inbox : Send}
              title={activeTab === 'inbox' ? 'No inbox notes' : 'No sent notes'}
              description="Notes will appear here once a workflow conversation is created for your current scope."
              action={<Button variant="outline" onClick={() => setComposerOpen(true)}>Create Note</Button>}
            />
          ) : (
            <div className="space-y-4">
              {notes.map((note) => (
                <NoteListItem
                  key={note.id}
                  note={note}
                  activeTab={activeTab}
                  onOpen={() => navigate(`/notes/${note.id}`)}
                  onMarkRead={() => readMutation.mutate(note.id)}
                  onResolve={() => resolveMutation.mutate(note.id)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <NoteComposer
        open={composerOpen}
        onOpenChange={setComposerOpen}
        initialValues={initialValues}
        onCreated={async (noteId) => {
          await queryClient.invalidateQueries({ queryKey: ['notes'] });
          navigate(`/notes/${noteId}`);
        }}
      />
    </div>
  );
}

function QuickActions({
  role,
  onLaunch,
}: {
  role?: string;
  onLaunch: (url: string) => void;
}) {
  if (!role) return null;

  const actionsByRole: Record<string, { label: string; description: string; icon: React.ElementType; url: string }[]> = {
    ops_manager: [
      {
        label: 'Send KPI Alert',
        description: 'Open a KPI alert with team context and threshold fields.',
        icon: Target,
        url: buildNotesComposeUrl({ noteType: RoleNoteType.KPI_ALERT, title: 'KPI alert' }),
      },
      {
        label: 'Escalate Ops Issue',
        description: 'Raise an operational escalation note.',
        icon: ShieldAlert,
        url: buildNotesComposeUrl({ noteType: RoleNoteType.OPS_ESCALATION, title: 'Operational escalation' }),
      },
    ],
    team_manager: [
      {
        label: 'Create KPI Follow-up',
        description: 'Create a KPI follow-up for a team leader.',
        icon: Target,
        url: buildNotesComposeUrl({ noteType: RoleNoteType.KPI_FOLLOW_UP, title: 'KPI follow-up' }),
      },
      {
        label: 'Request QA Review',
        description: 'Open a QA review request with call context.',
        icon: ShieldAlert,
        url: buildNotesComposeUrl({ noteType: RoleNoteType.QA_REVIEW_REQUEST, title: 'QA review request' }),
      },
    ],
    team_leader: [
      {
        label: 'Create KPI Follow-up',
        description: 'Open a KPI follow-up note with the fixed KPI catalog.',
        icon: Target,
        url: buildNotesComposeUrl({ noteType: RoleNoteType.KPI_FOLLOW_UP, title: 'KPI follow-up' }),
      },
      {
        label: 'Coaching Note',
        description: 'Start a coaching note for your current team workflow.',
        icon: Users,
        url: buildNotesComposeUrl({ noteType: RoleNoteType.COACHING_NOTE, title: 'Coaching note' }),
      },
      {
        label: 'Dispute QA Score',
        description: 'Start a QA dispute with structured context.',
        icon: ShieldAlert,
        url: buildNotesComposeUrl({ noteType: RoleNoteType.QA_DISPUTE, title: 'QA score dispute' }),
      },
    ],
  };

  const actions = actionsByRole[role] || [];
  if (actions.length === 0) return null;

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm font-medium text-foreground">Quick actions</p>
            <p className="text-xs text-muted-foreground">Launch note flows with the right type preselected.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {actions.map((action) => (
            <button
              key={action.label}
              type="button"
              onClick={() => onLaunch(action.url)}
              className="text-left rounded-xl border border-border bg-secondary/15 hover:bg-secondary/25 transition-colors px-4 py-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">{action.label}</p>
                  <p className="text-xs text-muted-foreground">{action.description}</p>
                </div>
                <action.icon size={16} className="text-primary shrink-0" />
              </div>
              <div className="mt-4 flex items-center gap-1 text-xs text-primary font-medium">
                Launch <ArrowUpRight size={12} />
              </div>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function NoteListItem({
  note,
  activeTab,
  onOpen,
  onMarkRead,
  onResolve,
}: {
  note: RoleNote;
  activeTab: 'inbox' | 'sent';
  onOpen: () => void;
  onMarkRead: () => void;
  onResolve: () => void;
}) {
  const isUnread = !note.read_at && note.status === RoleNoteStatus.OPEN;
  const canResolve = ![RoleNoteStatus.RESOLVED, RoleNoteStatus.ARCHIVED, RoleNoteStatus.DELETED].includes(note.status as RoleNoteStatus);

  return (
    <button
      type="button"
      onClick={onOpen}
      className="w-full text-left rounded-xl border border-border bg-card hover:bg-secondary/20 transition-colors"
    >
      <div className="px-5 py-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-semibold text-foreground truncate">{note.title}</p>
              {isUnread && <span className="size-2 rounded-full bg-primary shrink-0" />}
            </div>
            <p className="text-xs text-muted-foreground">
              {activeTab === 'inbox'
                ? `From ${note.sender_name || `User #${note.sender_id}`}`
                : `To ${note.recipient_name || note.recipient_role || 'Resolved recipient'}`}
              {' '}· {new Date(note.created_at).toLocaleString()}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {isUnread && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={(event) => {
                  event.stopPropagation();
                  onMarkRead();
                }}
              >
                <Eye size={14} />
                Read
              </Button>
            )}
            {canResolve && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={(event) => {
                  event.stopPropagation();
                  onResolve();
                }}
              >
                <CheckCheck size={14} />
                Resolve
              </Button>
            )}
          </div>
        </div>

        <p className="text-sm text-muted-foreground line-clamp-2">{note.body}</p>

        <NoteContextCard note={note} compact />
      </div>
    </button>
  );
}
