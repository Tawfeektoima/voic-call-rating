/** @vitest-environment node */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes } from 'react-router';
import { Sidebar } from '../components/layout/Sidebar';
import { RoleGuard } from '../components/auth/RoleGuard';
import { NoteThread } from '../pages/NoteThread';
import { NotesInbox } from '../pages/NotesInbox';
import { UserRole } from '../lib/types';

const mockUseApp = vi.fn();

vi.mock('../context/AppContext', () => ({
  useApp: () => mockUseApp(),
}));

const mockGetNotesInbox = vi.fn();
const mockGetSentNotes = vi.fn();
const mockGetNoteThread = vi.fn();
const mockMarkNoteRead = vi.fn();
const mockResolveNote = vi.fn();
const mockUpdateNoteStatus = vi.fn();
const mockArchiveNote = vi.fn();
const mockDeleteNote = vi.fn();
const mockCreateNote = vi.fn();
const mockReplyToNote = vi.fn();
const mockGetNoteRecipients = vi.fn();

vi.mock('../lib/api', () => ({
  getNotesInbox: (...args: unknown[]) => mockGetNotesInbox(...args),
  getSentNotes: (...args: unknown[]) => mockGetSentNotes(...args),
  getNoteThread: (...args: unknown[]) => mockGetNoteThread(...args),
  markNoteRead: (...args: unknown[]) => mockMarkNoteRead(...args),
  resolveNote: (...args: unknown[]) => mockResolveNote(...args),
  updateNoteStatus: (...args: unknown[]) => mockUpdateNoteStatus(...args),
  archiveNote: (...args: unknown[]) => mockArchiveNote(...args),
  deleteNote: (...args: unknown[]) => mockDeleteNote(...args),
  createNote: (...args: unknown[]) => mockCreateNote(...args),
  replyToNote: (...args: unknown[]) => mockReplyToNote(...args),
  getNoteRecipients: (...args: unknown[]) => mockGetNoteRecipients(...args),
}));

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

describe('Notes foundation', () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.ADMIN,
      currentUser: { id: 1, name: 'Admin User', email: 'admin@example.com', role: UserRole.ADMIN, avatar: 'AU' },
      sidebarCollapsed: false,
      setSidebarCollapsed: vi.fn(),
      piiMaskingEnabled: true,
      setPiiMaskingEnabled: vi.fn(),
      setCurrentUser: vi.fn(),
      setUserRole: vi.fn(),
    });

    mockGetNotesInbox.mockResolvedValue([]);
    mockGetSentNotes.mockResolvedValue([]);
    mockGetNoteThread.mockResolvedValue({ note: null, replies: [] });
    mockMarkNoteRead.mockResolvedValue({});
    mockResolveNote.mockResolvedValue({});
    mockUpdateNoteStatus.mockResolvedValue({});
    mockArchiveNote.mockResolvedValue({});
    mockDeleteNote.mockResolvedValue({});
    mockCreateNote.mockResolvedValue({ id: 501 });
    mockReplyToNote.mockResolvedValue({ id: 601 });
    mockGetNoteRecipients.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('redirects unauthorized users away from protected notes routes', () => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.AGENT,
      currentUser: { id: 20, name: 'Agent User', email: 'agent@example.com', role: UserRole.AGENT, avatar: 'AG' },
    });

    const result = RoleGuard({
      allowedRoles: [UserRole.ADMIN],
      children: <div>Secure Notes</div>,
    }) as unknown as { props?: { to?: string } };

    expect(result?.props?.to).toBe('/');
  });

  it('shows Workflow Notes in the sidebar for team leaders', () => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.TEAM_LEADER,
      currentUser: { id: 31, name: 'Team Leader', email: 'tl@example.com', role: UserRole.TEAM_LEADER, avatar: 'TL' },
      sidebarCollapsed: false,
      setSidebarCollapsed: vi.fn(),
      piiMaskingEnabled: true,
      setPiiMaskingEnabled: vi.fn(),
    });

    const html = renderToStaticMarkup(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(html).toContain('Workflow Notes');
    expect(html).not.toContain('Dashboard');
  });

  it('renders the notes inbox list for operational roles from prefetched data', async () => {
    const sampleNotes = [
      {
        id: 101,
        sender_id: 7,
        sender_name: 'Ops Manager',
        recipient_id: 8,
        recipient_name: 'Team Manager',
        recipient_role: 'TEAM_MANAGER',
        visibility: 'INTERNAL',
        team_id: 14,
        team_name_snapshot: 'Team Cairo',
        campaign_id: null,
        campaign_name_snapshot: null,
        employee_id: null,
        agent_name_snapshot: null,
        call_id: 222,
        parent_note_id: null,
        title: 'Review call spike',
        body: 'Please inspect the sudden spike in escalated calls.',
        note_type: 'OPS_ESCALATION',
        priority: 'HIGH',
        status: 'OPEN',
        kpi_key: null,
        kpi_label: null,
        current_value: null,
        target_value: null,
        period_start: null,
        period_end: null,
        created_at: '2026-06-10T00:00:00Z',
        updated_at: '2026-06-10T00:00:00Z',
        read_at: null,
        resolved_at: null,
        resolved_by_id: null,
        resolved_by_name: null,
        deleted_at: null,
        deleted_by_id: null,
        delete_reason: null,
      },
    ];

    mockGetNotesInbox.mockResolvedValue(sampleNotes);

    const client = createClient();
    await client.prefetchQuery({
      queryKey: ['notes', 'inbox', { status: undefined, note_type: undefined, limit: 100 }],
      queryFn: () => sampleNotes,
    });

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <NotesInbox />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('Operational Notes');
    expect(html).toContain('Review call spike');
    expect(html).toContain('Team Cairo');
    expect(html).toContain('Create Note');
  });

  it('renders a workflow thread with replies from prefetched data', async () => {
    const thread = {
      note: {
        id: 500,
        sender_id: 1,
        sender_name: 'Admin User',
        recipient_id: 40,
        recipient_name: 'QA User',
        recipient_role: 'QA',
        visibility: 'RECIPIENT_VISIBLE',
        team_id: null,
        team_name_snapshot: null,
        campaign_id: null,
        campaign_name_snapshot: null,
        employee_id: 91,
        agent_name_snapshot: 'Agent One',
        call_id: 450,
        parent_note_id: null,
        title: 'QA review needed',
        body: 'Please review the flagged call and confirm the scoring logic.',
        note_type: 'QA_REVIEW_REQUEST',
        priority: 'NORMAL',
        status: 'IN_PROGRESS',
        kpi_key: null,
        kpi_label: null,
        current_value: null,
        target_value: null,
        period_start: null,
        period_end: null,
        created_at: '2026-06-10T00:00:00Z',
        updated_at: '2026-06-10T00:00:00Z',
        read_at: '2026-06-10T00:05:00Z',
        resolved_at: null,
        resolved_by_id: null,
        resolved_by_name: null,
        deleted_at: null,
        deleted_by_id: null,
        delete_reason: null,
      },
      replies: [
        {
          id: 501,
          sender_id: 40,
          sender_name: 'QA User',
          recipient_id: 1,
          recipient_name: 'Admin User',
          recipient_role: 'ADMIN',
          visibility: 'RECIPIENT_VISIBLE',
          team_id: null,
          team_name_snapshot: null,
          campaign_id: null,
          campaign_name_snapshot: null,
          employee_id: 91,
          agent_name_snapshot: 'Agent One',
          call_id: 450,
          parent_note_id: 500,
          title: 'Re: QA review needed',
          body: 'I am reviewing the transcript now.',
          note_type: 'QA_REVIEW_REQUEST',
          priority: 'NORMAL',
          status: 'OPEN',
          kpi_key: null,
          kpi_label: null,
          current_value: null,
          target_value: null,
          period_start: null,
          period_end: null,
          created_at: '2026-06-10T00:10:00Z',
          updated_at: '2026-06-10T00:10:00Z',
          read_at: null,
          resolved_at: null,
          resolved_by_id: null,
          resolved_by_name: null,
          deleted_at: null,
          deleted_by_id: null,
          delete_reason: null,
        },
      ],
    };

    const client = createClient();
    await client.prefetchQuery({
      queryKey: ['note-thread', '500'],
      queryFn: () => thread,
    });

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/notes/500']}>
          <Routes>
            <Route path="/notes/:noteId" element={<NoteThread />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('QA review needed');
    expect(html).toContain('I am reviewing the transcript now.');
    expect(html).toContain('Reply');
    expect(html).toContain('Current Status');
    expect(html).toContain('Participants');
    expect(html).toContain('1 reply');
  });

});
