import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router';
import { AxiosError } from 'axios';
import { Archive, ArrowLeft, CheckCheck, MessageSquareReply, ShieldAlert, Trash2 } from 'lucide-react';
import { archiveNote, deleteNote, getNoteThread, markNoteRead, resolveNote, updateNoteStatus } from '../lib/api';
import { RoleNote, RoleNoteStatus } from '../lib/types';
import { NoteComposer } from '../components/notes/NoteComposer';
import { NoteContextCard } from '../components/notes/NoteContextCard';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { EmptyState, ErrorState, PageLoader } from '../components/ui/states';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { useApp } from '../context/AppContext';

const STATUS_OPTIONS = [
  RoleNoteStatus.READ,
  RoleNoteStatus.IN_PROGRESS,
  RoleNoteStatus.WAITING_REPLY,
];

function formatStatusLabel(status: string) {
  return status.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
}

function getStatusGuidance(rootNote: RoleNote, currentUserId?: number) {
  if (rootNote.status === RoleNoteStatus.WAITING_REPLY) {
    return rootNote.recipient_id === currentUserId
      ? 'The thread is waiting for your reply.'
      : 'The thread is waiting for the recipient to reply.';
  }

  if (rootNote.status === RoleNoteStatus.IN_PROGRESS) {
    return 'Someone is actively working this note.';
  }

  if (rootNote.status === RoleNoteStatus.RESOLVED) {
    return 'This workflow thread has been resolved.';
  }

  if (rootNote.status === RoleNoteStatus.READ) {
    return 'The note has been read and is ready for follow-up.';
  }

  return 'This note is open and waiting for action.';
}

export function NoteThread() {
  const { noteId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { currentUser, userRole } = useApp();
  const [replyOpen, setReplyOpen] = useState(false);

  const query = useQuery({
    queryKey: ['note-thread', noteId],
    enabled: Boolean(noteId),
    queryFn: () => getNoteThread(Number(noteId)),
  });

  const rootNote = query.data?.note;
  const replies = query.data?.replies || [];

  const markReadMutation = useMutation({
    mutationFn: () => markNoteRead(Number(noteId)),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['note-thread', noteId] }),
        queryClient.invalidateQueries({ queryKey: ['notes'] }),
      ]);
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) => updateNoteStatus(Number(noteId), { status }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['note-thread', noteId] }),
        queryClient.invalidateQueries({ queryKey: ['notes'] }),
      ]);
    },
  });

  const resolveMutation = useMutation({
    mutationFn: () => resolveNote(Number(noteId)),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['note-thread', noteId] }),
        queryClient.invalidateQueries({ queryKey: ['notes'] }),
      ]);
    },
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveNote(Number(noteId)),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['note-thread', noteId] }),
        queryClient.invalidateQueries({ queryKey: ['notes'] }),
      ]);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const reason = window.prompt('Delete reason:');
      if (!reason) {
        throw new Error('Delete cancelled');
      }
      return deleteNote(Number(noteId), reason);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['notes'] });
      navigate('/notes');
    },
  });

  useEffect(() => {
    if (!rootNote || !currentUser) return;
    if (rootNote.recipient_id === currentUser.id && !rootNote.read_at && rootNote.status === RoleNoteStatus.OPEN) {
      markReadMutation.mutate();
    }
  }, [currentUser, markReadMutation, rootNote]);

  const canResolve = useMemo(() => {
    if (!rootNote) return false;
    return ![RoleNoteStatus.RESOLVED, RoleNoteStatus.ARCHIVED, RoleNoteStatus.DELETED].includes(rootNote.status as RoleNoteStatus);
  }, [rootNote]);

  const error = query.error as AxiosError<{ detail?: string }> | null;
  const isForbidden = error?.response?.status === 403;

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="icon" onClick={() => navigate('/notes')}>
            <ArrowLeft size={16} />
          </Button>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground font-semibold">Workflow Thread</p>
            <h1 className="text-2xl font-semibold text-foreground">{rootNote?.title || 'Note thread'}</h1>
          </div>
        </div>

        {rootNote && (
          <div className="flex items-center gap-2 flex-wrap">
            {!rootNote.read_at && rootNote.recipient_id === currentUser?.id && (
              <Button variant="outline" onClick={() => markReadMutation.mutate()}>
                Mark Read
              </Button>
            )}
            {canResolve && (
              <Button variant="outline" onClick={() => resolveMutation.mutate()}>
                <CheckCheck size={14} />
                Resolve
              </Button>
            )}
            <Button onClick={() => setReplyOpen(true)}>
              <MessageSquareReply size={14} />
              Reply
            </Button>
            {userRole === 'admin' && rootNote.status === RoleNoteStatus.RESOLVED && (
              <Button variant="outline" onClick={() => archiveMutation.mutate()}>
                <Archive size={14} />
                Archive
              </Button>
            )}
            {userRole === 'admin' && (
              <Button variant="destructive" onClick={() => deleteMutation.mutate()}>
                <Trash2 size={14} />
                Delete
              </Button>
            )}
          </div>
        )}
      </div>

      {query.isLoading ? (
        <PageLoader message="Loading note thread..." />
      ) : isForbidden ? (
        <ErrorState message="You do not have access to this workflow thread." />
      ) : query.isError ? (
        <ErrorState message={error?.response?.data?.detail || 'Unable to load this note thread.'} onRetry={() => query.refetch()} />
      ) : !rootNote ? (
        <EmptyState icon={ShieldAlert} title="Note not found" description="The requested workflow note could not be loaded." />
      ) : (
        <>
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="rounded-lg border border-border/70 bg-secondary/15 px-4 py-4">
                  <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Current Status</p>
                  <p className="text-sm font-semibold text-foreground mt-1">{formatStatusLabel(rootNote.status)}</p>
                  <p className="text-xs text-muted-foreground mt-2">{getStatusGuidance(rootNote, currentUser?.id)}</p>
                </div>
                <div className="rounded-lg border border-border/70 bg-secondary/15 px-4 py-4">
                  <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Participants</p>
                  <p className="text-sm font-semibold text-foreground mt-1">
                    {rootNote.sender_name || `User #${rootNote.sender_id}`} to {rootNote.recipient_name || rootNote.recipient_role || 'Resolved recipient'}
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">The backend keeps recipient scope locked to the workflow hierarchy.</p>
                </div>
                <div className="rounded-lg border border-border/70 bg-secondary/15 px-4 py-4">
                  <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Activity</p>
                  <p className="text-sm font-semibold text-foreground mt-1">{replies.length} {replies.length === 1 ? 'reply' : 'replies'}</p>
                  <p className="text-xs text-muted-foreground mt-2">
                    {rootNote.read_at ? 'The root note has already been read.' : 'The root note has not been marked as read yet.'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 border-b border-border/80">
              <div className="space-y-1">
                <CardTitle className="text-lg font-semibold">{rootNote.title}</CardTitle>
                <p className="text-xs text-muted-foreground">
                  From {rootNote.sender_name || `User #${rootNote.sender_id}`} to {rootNote.recipient_name || rootNote.recipient_role || 'Resolved recipient'}
                  {' - '}{new Date(rootNote.created_at).toLocaleString()}
                </p>
              </div>

              {canResolve && (
                <div className="w-full lg:w-52">
                  <Select value={rootNote.status} onValueChange={(nextStatus) => statusMutation.mutate(nextStatus)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STATUS_OPTIONS.map((status) => (
                        <SelectItem key={status} value={status}>{formatStatusLabel(status)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </CardHeader>
            <CardContent className="pt-6 space-y-5">
              <p className="text-sm leading-7 text-foreground/90 whitespace-pre-wrap">{rootNote.body}</p>
              <NoteContextCard note={rootNote} />
            </CardContent>
          </Card>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Replies</h2>
              <p className="text-xs text-muted-foreground">{replies.length} message{replies.length === 1 ? '' : 's'}</p>
            </div>

            {replies.length === 0 ? (
              <EmptyState
                icon={MessageSquareReply}
                title="No replies yet"
                description="Use the reply action to continue this workflow thread."
              />
            ) : (
              replies.map((reply) => <ReplyCard key={reply.id} note={reply} currentUserId={currentUser?.id} />)
            )}
          </div>
        </>
      )}

      {rootNote && (
        <NoteComposer
          open={replyOpen}
          onOpenChange={setReplyOpen}
          replyToNoteId={rootNote.id}
          rootNote={rootNote}
          onCreated={async () => {
            await Promise.all([
              queryClient.invalidateQueries({ queryKey: ['note-thread', noteId] }),
              queryClient.invalidateQueries({ queryKey: ['notes'] }),
            ]);
            setReplyOpen(false);
          }}
        />
      )}
    </div>
  );
}

function ReplyCard({ note, currentUserId }: { note: RoleNote; currentUserId?: number }) {
  const isCurrentUser = currentUserId === note.sender_id;

  return (
    <Card className={isCurrentUser ? 'border-primary/25 bg-primary/5' : undefined}>
      <CardContent className="pt-6 space-y-3">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-foreground">{note.sender_name || `User #${note.sender_id}`}</p>
            <p className="text-xs text-muted-foreground">{new Date(note.created_at).toLocaleString()}</p>
          </div>
          {isCurrentUser && (
            <span className="text-[11px] uppercase tracking-wide text-primary font-semibold">You</span>
          )}
        </div>
        <p className="text-sm text-foreground/90 leading-7 whitespace-pre-wrap">{note.body}</p>
      </CardContent>
    </Card>
  );
}
