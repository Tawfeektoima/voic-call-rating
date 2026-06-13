/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { KpiNoteCard } from '../components/notes/KpiNoteCard';
import { NotesInbox } from '../pages/NotesInbox';
import { NoteRecipientPicker } from '../components/notes/NoteRecipientPicker';
import { UserRole } from '../lib/types';

const mockUseApp = vi.fn();
const mockGetNotesInbox = vi.fn();
const mockGetSentNotes = vi.fn();
const mockMarkNoteRead = vi.fn();
const mockResolveNote = vi.fn();
const mockGetNoteRecipients = vi.fn();
const mockCreateNote = vi.fn();
const mockReplyToNote = vi.fn();

vi.mock('../context/AppContext', () => ({
  useApp: () => mockUseApp(),
}));

vi.mock('../lib/api', () => ({
  getNotesInbox: (...args: unknown[]) => mockGetNotesInbox(...args),
  getSentNotes: (...args: unknown[]) => mockGetSentNotes(...args),
  markNoteRead: (...args: unknown[]) => mockMarkNoteRead(...args),
  resolveNote: (...args: unknown[]) => mockResolveNote(...args),
  getNoteRecipients: (...args: unknown[]) => mockGetNoteRecipients(...args),
  createNote: (...args: unknown[]) => mockCreateNote(...args),
  replyToNote: (...args: unknown[]) => mockReplyToNote(...args),
}));

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

describe('KPI notes UI', () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.TEAM_MANAGER,
      currentUser: { id: 11, name: 'Team Manager', email: 'tm@example.com', role: UserRole.TEAM_MANAGER, avatar: 'TM' },
      sidebarCollapsed: false,
      setSidebarCollapsed: vi.fn(),
      piiMaskingEnabled: true,
      setPiiMaskingEnabled: vi.fn(),
      setCurrentUser: vi.fn(),
      setUserRole: vi.fn(),
    });
    mockGetNotesInbox.mockResolvedValue([]);
    mockGetSentNotes.mockResolvedValue([]);
    mockMarkNoteRead.mockResolvedValue({});
    mockResolveNote.mockResolvedValue({});
    mockGetNoteRecipients.mockResolvedValue([]);
    mockCreateNote.mockResolvedValue({ id: 1 });
    mockReplyToNote.mockResolvedValue({ id: 2 });
  });

  it('formats KPI note values for percentage units', () => {
    const html = renderToStaticMarkup(
      <KpiNoteCard
        note={{
          id: 1,
          sender_id: 1,
          sender_name: 'Ops',
          recipient_id: 2,
          recipient_name: 'TM',
          recipient_role: 'TEAM_MANAGER',
          visibility: 'INTERNAL',
          team_id: 10,
          team_name_snapshot: 'Team 10',
          campaign_id: null,
          campaign_name_snapshot: null,
          employee_id: null,
          agent_name_snapshot: null,
          call_id: null,
          parent_note_id: null,
          title: 'Conversion KPI',
          body: 'Watch this KPI.',
          note_type: 'KPI_ALERT',
          priority: 'HIGH',
          status: 'OPEN',
          kpi_key: 'conversion_rate',
          kpi_label: 'Conversion Rate',
          current_value: 18.5,
          target_value: 25,
          period_start: '2026-06-01T00:00:00.000Z',
          period_end: '2026-06-30T00:00:00.000Z',
          created_at: '2026-06-10T00:00:00.000Z',
          updated_at: '2026-06-10T00:00:00.000Z',
          read_at: null,
          resolved_at: null,
          resolved_by_id: null,
          resolved_by_name: null,
          deleted_at: null,
          deleted_by_id: null,
          delete_reason: null,
        }}
      />
    );

    expect(html).toContain('18.5%');
    expect(html).toContain('25.0%');
    expect(html).toContain('6.5%');
  });

  it('shows KPI quick action launchers for team managers', async () => {
    const client = createClient();
    await client.prefetchQuery({
      queryKey: ['notes', 'inbox', { status: undefined, note_type: undefined, limit: 100 }],
      queryFn: () => [],
    });

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <NotesInbox />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('Create KPI Follow-up');
    expect(html).toContain('Request QA Review');
  });

  it('shows KPI follow-up quick action for team leaders', async () => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.TEAM_LEADER,
      currentUser: { id: 14, name: 'Team Leader', email: 'tl@example.com', role: UserRole.TEAM_LEADER, avatar: 'TL' },
      sidebarCollapsed: false,
      setSidebarCollapsed: vi.fn(),
      piiMaskingEnabled: true,
      setPiiMaskingEnabled: vi.fn(),
      setCurrentUser: vi.fn(),
      setUserRole: vi.fn(),
    });

    const client = createClient();
    await client.prefetchQuery({
      queryKey: ['notes', 'inbox', { status: undefined, note_type: undefined, limit: 100 }],
      queryFn: () => [],
    });

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <NotesInbox />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('Create KPI Follow-up');
    expect(html).toContain('Coaching Note');
  });

  it('blocks submission when no recipient is resolved for a KPI workflow context', async () => {
    const client = createClient();
    await client.prefetchQuery({
      queryKey: ['note-recipients', 'KPI_FOLLOW_UP', 9, undefined, undefined, undefined],
      queryFn: () => [],
    });

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <NoteRecipientPicker
            noteType="KPI_FOLLOW_UP"
            teamId={9}
            onChange={() => undefined}
          />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('No valid recipient for this context.');
    expect(html).toContain('Resolved from team #9 using backend hierarchy rules.');
  });
});
