/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';

import { Sidebar } from '../components/layout/Sidebar';
import { HRInterviews } from '../pages/HRInterviews';
import { UserRole } from '../lib/types';

const mockUseApp = vi.fn();
const mockGetInterviewJobs = vi.fn();
const mockCreateInterviewJob = vi.fn();
const mockUpdateInterviewJob = vi.fn();
const mockGetInterviewCandidates = vi.fn();
const mockGetInterviewCandidateAnswers = vi.fn();
const mockGetDefaultInterviewMcqBank = vi.fn();
const mockGetInterviewCandidateMcqSubmission = vi.fn();
const mockGetInterviewCandidateOnboardingReadiness = vi.fn();
const mockCreateInterviewCandidate = vi.fn();
const mockInviteInterviewCandidate = vi.fn();
const mockRejectInterviewCandidate = vi.fn();
const mockArchiveInterviewCandidate = vi.fn();
const mockShortlistInterviewCandidate = vi.fn();
const mockAcceptInterviewCandidate = vi.fn();
const mockRestoreInterviewCandidate = vi.fn();
const mockBulkArchiveInterviewCandidates = vi.fn();
const mockConvertInterviewCandidate = vi.fn();
const mockExportInterviewCandidatesCsv = vi.fn();
const mockPurgeArchivedInterviewCandidates = vi.fn();
const mockUploadInterviewCandidateDocument = vi.fn();
const mockGetInterviewCandidateDocuments = vi.fn();
const mockGetTeamsDirectory = vi.fn();
const mockGetCampaigns = vi.fn();
const mockGetInterviewCandidateTimeline = vi.fn();

vi.mock('../context/AppContext', () => ({
  useApp: () => mockUseApp(),
}));

vi.mock('../lib/api', () => ({
  getInterviewJobs: () => mockGetInterviewJobs(),
  createInterviewJob: (...args: unknown[]) => mockCreateInterviewJob(...args),
  updateInterviewJob: (...args: unknown[]) => mockUpdateInterviewJob(...args),
  getInterviewCandidates: (...args: unknown[]) => mockGetInterviewCandidates(...args),
  getInterviewCandidateAnswers: (...args: unknown[]) => mockGetInterviewCandidateAnswers(...args),
  getDefaultInterviewMcqBank: (...args: unknown[]) => mockGetDefaultInterviewMcqBank(...args),
  getInterviewCandidateMcqSubmission: (...args: unknown[]) => mockGetInterviewCandidateMcqSubmission(...args),
  getInterviewCandidateOnboardingReadiness: (...args: unknown[]) => mockGetInterviewCandidateOnboardingReadiness(...args),
  createInterviewCandidate: (...args: unknown[]) => mockCreateInterviewCandidate(...args),
  inviteInterviewCandidate: (...args: unknown[]) => mockInviteInterviewCandidate(...args),
  rejectInterviewCandidate: (...args: unknown[]) => mockRejectInterviewCandidate(...args),
  archiveInterviewCandidate: (...args: unknown[]) => mockArchiveInterviewCandidate(...args),
  shortlistInterviewCandidate: (...args: unknown[]) => mockShortlistInterviewCandidate(...args),
  acceptInterviewCandidate: (...args: unknown[]) => mockAcceptInterviewCandidate(...args),
  restoreInterviewCandidate: (...args: unknown[]) => mockRestoreInterviewCandidate(...args),
  bulkArchiveInterviewCandidates: (...args: unknown[]) => mockBulkArchiveInterviewCandidates(...args),
  convertInterviewCandidate: (...args: unknown[]) => mockConvertInterviewCandidate(...args),
  exportInterviewCandidatesCsv: (...args: unknown[]) => mockExportInterviewCandidatesCsv(...args),
  purgeArchivedInterviewCandidates: (...args: unknown[]) => mockPurgeArchivedInterviewCandidates(...args),
  uploadInterviewCandidateDocument: (...args: unknown[]) => mockUploadInterviewCandidateDocument(...args),
  getInterviewCandidateDocuments: (...args: unknown[]) => mockGetInterviewCandidateDocuments(...args),
  getTeamsDirectory: (...args: unknown[]) => mockGetTeamsDirectory(...args),
  getCampaigns: (...args: unknown[]) => mockGetCampaigns(...args),
  getInterviewCandidateTimeline: (...args: unknown[]) => mockGetInterviewCandidateTimeline(...args),
  getApiErrorMessage: () => 'Mock API error',
}));

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

describe('HR interview workspace', () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.HR_MANAGER,
      currentUser: {
        id: 77,
        name: 'HR Manager',
        email: 'hr@example.com',
        role: UserRole.HR_MANAGER,
        permissions: [
          'hr.dashboard.view',
          'hr.interviews.jobs.manage',
          'hr.interviews.candidates.view',
          'hr.interviews.candidates.manage',
          'hr.interviews.candidates.convert',
          'hr.interviews.export',
        ],
        avatar: 'HR',
      },
      sidebarCollapsed: false,
      setSidebarCollapsed: vi.fn(),
      piiMaskingEnabled: true,
      setPiiMaskingEnabled: vi.fn(),
      setCurrentUser: vi.fn(),
      setUserRole: vi.fn(),
    });

    mockGetInterviewJobs.mockResolvedValue([
      {
        id: 11,
        title: 'Outbound Sales Agent',
        description: 'Voice-first interview screening.',
        department: 'Sales',
        team_id: null,
        campaign_id: null,
        status: 'open',
        base_questions: ['Introduce yourself', 'Why do you want this role?'],
        mcq_enabled: false,
        mcq_questions: [],
        created_by_id: 77,
        updated_by_id: 77,
        created_at: '2026-06-14T00:00:00.000Z',
        updated_at: '2026-06-14T00:00:00.000Z',
      },
    ]);
    mockGetInterviewCandidates.mockResolvedValue([
      {
        id: 31,
        job_id: 11,
        full_name: 'Candidate Maya',
        contact_email: 'maya@example.com',
        contact_email_normalized: 'maya@example.com',
        phone_number: '01099999999',
        phone_normalized: '01099999999',
        national_id_last4: '4567',
        status: 'interviewing',
        final_score: null,
        global_percentile: null,
        applied_at: '2026-06-14T00:00:00.000Z',
        completed_at: null,
        archived_at: null,
        converted_employee_id: null,
        created_by_id: 77,
        mcq_score: 12,
        mcq_total_questions: 15,
        mcq_percentage: 80,
        mcq_completed_at: '2026-06-15T10:00:00.000Z',
      },
    ]);
    mockGetInterviewCandidateAnswers.mockResolvedValue([
      {
        id: 51,
        session_id: 61,
        candidate_id: 31,
        question_id: 71,
        transcribed_text: 'I improved retention by calming frustrated customers and confirming next steps.',
        overall_score: 84,
        ai_summary: 'Strong answer with practical ownership and clear communication.',
        status: 'evaluated',
        submitted_at: '2026-06-14T00:00:00.000Z',
        evaluated_at: '2026-06-14T00:02:00.000Z',
      },
    ]);
    mockGetDefaultInterviewMcqBank.mockResolvedValue([]);
    mockGetInterviewCandidateMcqSubmission.mockResolvedValue(null);
    mockGetInterviewCandidateOnboardingReadiness.mockResolvedValue({
      candidate_id: 31,
      status: 'accepted',
      is_ready: true,
      blocking_reasons: [],
      blocking_categories: [],
      suggested_employee_code: '31',
      suggested_company_email: 'emp-31@eiacs.com',
      candidate_identity_summary: {
        candidate_id: 31,
        full_name: 'Candidate Maya',
        job_id: 11,
        job_title: 'Outbound Sales Agent',
        department: 'Sales',
        status: 'accepted',
        phone_last4: '9999',
        national_id_last4: '4567',
        contact_email_masked: 'ma**@example.com',
        converted_employee_id: null,
      },
      existing_employee_match: null,
    });
    mockGetInterviewCandidateDocuments.mockResolvedValue([
      {
        id: 41,
        candidate_id: 31,
        document_type: 'cv',
        original_filename: 'maya-cv.pdf',
        storage_path: '/uploads/maya-cv.pdf',
        extraction_status: 'pending',
        extraction_error: null,
        uploaded_at: '2026-06-14T00:00:00.000Z',
      },
    ]);
    mockExportInterviewCandidatesCsv.mockResolvedValue(new Blob(['csv-content'], { type: 'text/csv' }));
    mockPurgeArchivedInterviewCandidates.mockResolvedValue({
      archived_candidates_matched: 0,
      candidates_deleted: 0,
      document_rows_deleted: 0,
      answer_audio_files_deleted: 0,
      document_files_deleted: 0,
      dry_run: true,
    });
    mockGetTeamsDirectory.mockResolvedValue([]);
    mockGetCampaigns.mockResolvedValue([]);
    mockGetInterviewCandidateTimeline.mockResolvedValue([
      {
        id: 99,
        candidate_id: 31,
        actor_id: 77,
        actor_name: 'HR Manager',
        event_type: 'CANDIDATE_INVITED',
        from_status: 'applied',
        to_status: 'interviewing',
        note: 'Interview session created',
        event_payload: null,
        created_at: '2026-06-15T12:00:00.000Z',
      },
    ]);
  });

  it('shows interview pipeline navigation for HR users', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(html).toContain('Interview Pipeline');
    expect(html).toContain('HR Dashboard');
  });

  it('renders interview jobs, candidates, and conversion workspace', async () => {
    const client = createClient();
    await Promise.all([
      client.prefetchQuery({ queryKey: ['interview-jobs'], queryFn: () => mockGetInterviewJobs() }),
      client.prefetchQuery({ queryKey: ['interview-candidates', 11], queryFn: () => mockGetInterviewCandidates() }),
      client.prefetchQuery({ queryKey: ['interview-answers', 31], queryFn: () => mockGetInterviewCandidateAnswers() }),
      client.prefetchQuery({ queryKey: ['interview-documents', 31], queryFn: () => mockGetInterviewCandidateDocuments() }),
      client.prefetchQuery({ queryKey: ['interview-teams'], queryFn: () => mockGetTeamsDirectory() }),
      client.prefetchQuery({ queryKey: ['interview-campaigns'], queryFn: () => mockGetCampaigns() }),
    ]);

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <HRInterviews />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('Interview Pipeline');
    expect(html).toContain('Outbound Sales Agent');
    expect(html).toContain('Job Queue');
    expect(html).toContain('Job Editor');
    expect(html).toContain('Interview Jobs');
    expect(html).toContain('Candidate Export');
    expect(html).toContain('Retention Controls');
  });

  it('renders candidate status filter dropdown and bulk action controls', async () => {
    const client = createClient();
    await Promise.all([
      client.prefetchQuery({ queryKey: ['interview-jobs'], queryFn: () => mockGetInterviewJobs() }),
      client.prefetchQuery({ queryKey: ['interview-candidates', 11], queryFn: () => mockGetInterviewCandidates() }),
      client.prefetchQuery({ queryKey: ['interview-answers', 31], queryFn: () => mockGetInterviewCandidateAnswers() }),
      client.prefetchQuery({ queryKey: ['interview-documents', 31], queryFn: () => mockGetInterviewCandidateDocuments() }),
      client.prefetchQuery({ queryKey: ['interview-teams'], queryFn: () => mockGetTeamsDirectory() }),
      client.prefetchQuery({ queryKey: ['interview-campaigns'], queryFn: () => mockGetCampaigns() }),
    ]);

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <HRInterviews />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('Status filter');
    expect(html).toContain('All statuses');
    expect(html).toContain('Bulk Actions');
    expect(html).toContain('Select shown');
    expect(html).toContain('Clear');
    expect(html).toContain('Email');
    expect(html).toContain('Archive');
  });

  it('renders decision buttons based on candidate status', async () => {
    // 1. Test with an 'evaluated' candidate - should show Shortlist, Accept, Reject, Archive
    mockGetInterviewCandidates.mockResolvedValue([
      {
        id: 31,
        job_id: 11,
        full_name: 'Evaluated Candidate',
        contact_email: 'eval@example.com',
        status: 'evaluated',
        applied_at: '2026-06-14T00:00:00.000Z',
      },
    ]);

    const client1 = createClient();
    await Promise.all([
      client1.prefetchQuery({ queryKey: ['interview-jobs'], queryFn: () => mockGetInterviewJobs() }),
      client1.prefetchQuery({ queryKey: ['interview-candidates', 11], queryFn: () => mockGetInterviewCandidates() }),
      client1.prefetchQuery({ queryKey: ['interview-answers', 31], queryFn: () => mockGetInterviewCandidateAnswers() }),
      client1.prefetchQuery({ queryKey: ['interview-documents', 31], queryFn: () => mockGetInterviewCandidateDocuments() }),
      client1.prefetchQuery({ queryKey: ['interview-teams'], queryFn: () => mockGetTeamsDirectory() }),
      client1.prefetchQuery({ queryKey: ['interview-campaigns'], queryFn: () => mockGetCampaigns() }),
    ]);

    const html1 = renderToStaticMarkup(
      <QueryClientProvider client={client1}>
        <MemoryRouter>
          <HRInterviews />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Verify button classes are rendered
    expect(/Shortlist\s*<\/button>/.test(html1)).toBe(true);
    expect(/Accept\s*<\/button>/.test(html1)).toBe(true);
    expect(/Reject\s*<\/button>/.test(html1)).toBe(true);
    expect(/Restore\s*<\/button>/.test(html1)).toBe(false);

    // Assert inputs rendering
    expect(html1).toContain('placeholder="Internal note for candidate status transition decisions"');
    expect(html1).toContain('id="auto-notify-checkbox"');

    // 2. Test with an 'archived' candidate - should show Restore, but not Shortlist, Accept, Reject
    mockGetInterviewCandidates.mockResolvedValue([
      {
        id: 31,
        job_id: 11,
        full_name: 'Archived Candidate',
        contact_email: 'archive@example.com',
        status: 'archived',
        applied_at: '2026-06-14T00:00:00.000Z',
      },
    ]);

    const client2 = createClient();
    await Promise.all([
      client2.prefetchQuery({ queryKey: ['interview-jobs'], queryFn: () => mockGetInterviewJobs() }),
      client2.prefetchQuery({ queryKey: ['interview-candidates', 11], queryFn: () => mockGetInterviewCandidates() }),
      client2.prefetchQuery({ queryKey: ['interview-answers', 31], queryFn: () => mockGetInterviewCandidateAnswers() }),
      client2.prefetchQuery({ queryKey: ['interview-documents', 31], queryFn: () => mockGetInterviewCandidateDocuments() }),
      client2.prefetchQuery({ queryKey: ['interview-teams'], queryFn: () => mockGetTeamsDirectory() }),
      client2.prefetchQuery({ queryKey: ['interview-campaigns'], queryFn: () => mockGetCampaigns() }),
    ]);

    const html2 = renderToStaticMarkup(
      <QueryClientProvider client={client2}>
        <MemoryRouter>
          <HRInterviews />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(/Restore\s*<\/button>/.test(html2)).toBe(true);
    expect(/Shortlist\s*<\/button>/.test(html2)).toBe(false);
    expect(/Accept\s*<\/button>/.test(html2)).toBe(false);
    expect(/Reject\s*<\/button>/.test(html2)).toBe(false);

    // 3. Test with a 'shortlisted' candidate - should show Accept, Reject, hide Shortlist, Restore
    mockGetInterviewCandidates.mockResolvedValue([
      {
        id: 31,
        job_id: 11,
        full_name: 'Shortlisted Candidate',
        contact_email: 'shortlist@example.com',
        status: 'shortlisted',
        applied_at: '2026-06-14T00:00:00.000Z',
      },
    ]);

    const client3 = createClient();
    await Promise.all([
      client3.prefetchQuery({ queryKey: ['interview-jobs'], queryFn: () => mockGetInterviewJobs() }),
      client3.prefetchQuery({ queryKey: ['interview-candidates', 11], queryFn: () => mockGetInterviewCandidates() }),
      client3.prefetchQuery({ queryKey: ['interview-answers', 31], queryFn: () => mockGetInterviewCandidateAnswers() }),
      client3.prefetchQuery({ queryKey: ['interview-documents', 31], queryFn: () => mockGetInterviewCandidateDocuments() }),
      client3.prefetchQuery({ queryKey: ['interview-teams'], queryFn: () => mockGetTeamsDirectory() }),
      client3.prefetchQuery({ queryKey: ['interview-campaigns'], queryFn: () => mockGetCampaigns() }),
    ]);

    const html3 = renderToStaticMarkup(
      <QueryClientProvider client={client3}>
        <MemoryRouter>
          <HRInterviews />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(/Accept\s*<\/button>/.test(html3)).toBe(true);
    expect(/Reject\s*<\/button>/.test(html3)).toBe(true);
    expect(/Shortlist\s*<\/button>/.test(html3)).toBe(false);
    expect(/Restore\s*<\/button>/.test(html3)).toBe(false);

    // 4. Test with a 'rejected' candidate - should show Shortlist, Accept, hide Reject, Restore
    mockGetInterviewCandidates.mockResolvedValue([
      {
        id: 31,
        job_id: 11,
        full_name: 'Rejected Candidate',
        contact_email: 'rejected@example.com',
        status: 'rejected',
        applied_at: '2026-06-14T00:00:00.000Z',
      },
    ]);

    const client4 = createClient();
    await Promise.all([
      client4.prefetchQuery({ queryKey: ['interview-jobs'], queryFn: () => mockGetInterviewJobs() }),
      client4.prefetchQuery({ queryKey: ['interview-candidates', 11], queryFn: () => mockGetInterviewCandidates() }),
      client4.prefetchQuery({ queryKey: ['interview-answers', 31], queryFn: () => mockGetInterviewCandidateAnswers() }),
      client4.prefetchQuery({ queryKey: ['interview-documents', 31], queryFn: () => mockGetInterviewCandidateDocuments() }),
      client4.prefetchQuery({ queryKey: ['interview-teams'], queryFn: () => mockGetTeamsDirectory() }),
      client4.prefetchQuery({ queryKey: ['interview-campaigns'], queryFn: () => mockGetCampaigns() }),
    ]);

    const html4 = renderToStaticMarkup(
      <QueryClientProvider client={client4}>
        <MemoryRouter>
          <HRInterviews />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(/Shortlist\s*<\/button>/.test(html4)).toBe(true);
    expect(/Accept\s*<\/button>/.test(html4)).toBe(true);
    expect(/Reject\s*<\/button>/.test(html4)).toBe(false);
    expect(/Restore\s*<\/button>/.test(html4)).toBe(false);
  });

  it('renders onboarding readiness panel for accepted candidates', async () => {
    mockGetInterviewCandidates.mockResolvedValue([
      {
        id: 31,
        job_id: 11,
        full_name: 'Accepted Candidate',
        contact_email: 'accepted@example.com',
        contact_email_normalized: 'accepted@example.com',
        status: 'accepted',
        applied_at: '2026-06-14T00:00:00.000Z',
      },
    ]);
    mockGetInterviewCandidateOnboardingReadiness.mockResolvedValue({
      candidate_id: 31,
      status: 'accepted',
      is_ready: false,
      blocking_reasons: ['Employee code already registered.'],
      blocking_categories: ['employee_code'],
      suggested_employee_code: '31',
      suggested_company_email: 'emp-31@eiacs.com',
      candidate_identity_summary: {
        candidate_id: 31,
        full_name: 'Accepted Candidate',
        job_id: 11,
        job_title: 'Outbound Sales Agent',
        department: 'Sales',
        status: 'accepted',
        phone_last4: null,
        national_id_last4: null,
        contact_email_masked: 'ac******@example.com',
        converted_employee_id: null,
      },
      existing_employee_match: {
        employee_id: 901,
        employee_code: '31',
        employee_email: 'emp-31@eiacs.com',
        role: 'AGENT',
        status: 'active',
      },
    });

    const client = createClient();
    await Promise.all([
      client.prefetchQuery({ queryKey: ['interview-jobs'], queryFn: () => mockGetInterviewJobs() }),
      client.prefetchQuery({ queryKey: ['interview-candidates', 11], queryFn: () => mockGetInterviewCandidates() }),
      client.prefetchQuery({ queryKey: ['interview-answers', 31], queryFn: () => mockGetInterviewCandidateAnswers() }),
      client.prefetchQuery({ queryKey: ['interview-documents', 31], queryFn: () => mockGetInterviewCandidateDocuments() }),
      client.prefetchQuery({ queryKey: ['interview-teams'], queryFn: () => mockGetTeamsDirectory() }),
      client.prefetchQuery({ queryKey: ['interview-campaigns'], queryFn: () => mockGetCampaigns() }),
      client.prefetchQuery({
        queryKey: ['interview-candidate-onboarding-readiness', 31],
        queryFn: () => mockGetInterviewCandidateOnboardingReadiness(),
      }),
    ]);

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <HRInterviews />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('Onboarding Readiness');
    expect(html).toContain('Needs attention before convert');
    expect(html).toContain('Employee code already registered.');
    expect(html).toContain('Suggested employee code');
    expect(html).toContain('Suggested company email');
    expect(html).toContain('emp-31@eiacs.com');
  });

  it('renders candidate timeline panel with events, loading, and empty states', async () => {
    // 1. Test case: With events
    mockGetInterviewCandidateTimeline.mockResolvedValue([
      {
        id: 99,
        candidate_id: 31,
        actor_id: 77,
        actor_name: 'HR Manager',
        event_type: 'CANDIDATE_INVITED',
        from_status: 'applied',
        to_status: 'interviewing',
        note: 'Interview session created',
        event_payload: null,
        created_at: '2026-06-15T12:00:00.000Z',
      },
    ]);

    const client1 = createClient();
    await Promise.all([
      client1.prefetchQuery({ queryKey: ['interview-jobs'], queryFn: () => mockGetInterviewJobs() }),
      client1.prefetchQuery({ queryKey: ['interview-candidates', 11], queryFn: () => mockGetInterviewCandidates() }),
      client1.prefetchQuery({ queryKey: ['interview-answers', 31], queryFn: () => mockGetInterviewCandidateAnswers() }),
      client1.prefetchQuery({ queryKey: ['interview-documents', 31], queryFn: () => mockGetInterviewCandidateDocuments() }),
      client1.prefetchQuery({ queryKey: ['interview-teams'], queryFn: () => mockGetTeamsDirectory() }),
      client1.prefetchQuery({ queryKey: ['interview-campaigns'], queryFn: () => mockGetCampaigns() }),
      client1.prefetchQuery({ queryKey: ['interview-candidate-timeline', 31], queryFn: () => mockGetInterviewCandidateTimeline() }),
    ]);

    const html1 = renderToStaticMarkup(
      <QueryClientProvider client={client1}>
        <MemoryRouter>
          <HRInterviews />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html1).toContain('Candidate Timeline');
    expect(html1).toContain('candidate invited');
    expect(html1).toContain('applied');
    expect(html1).toContain('interviewing');
    expect(html1).toContain('Interview session created');
    expect(html1).toContain('HR Manager');

    // 2. Test case: Empty timeline state
    mockGetInterviewCandidateTimeline.mockResolvedValue([]);

    const client2 = createClient();
    await Promise.all([
      client2.prefetchQuery({ queryKey: ['interview-jobs'], queryFn: () => mockGetInterviewJobs() }),
      client2.prefetchQuery({ queryKey: ['interview-candidates', 11], queryFn: () => mockGetInterviewCandidates() }),
      client2.prefetchQuery({ queryKey: ['interview-answers', 31], queryFn: () => mockGetInterviewCandidateAnswers() }),
      client2.prefetchQuery({ queryKey: ['interview-documents', 31], queryFn: () => mockGetInterviewCandidateDocuments() }),
      client2.prefetchQuery({ queryKey: ['interview-teams'], queryFn: () => mockGetTeamsDirectory() }),
      client2.prefetchQuery({ queryKey: ['interview-campaigns'], queryFn: () => mockGetCampaigns() }),
      client2.prefetchQuery({ queryKey: ['interview-candidate-timeline', 31], queryFn: () => mockGetInterviewCandidateTimeline() }),
    ]);

    const html2 = renderToStaticMarkup(
      <QueryClientProvider client={client2}>
        <MemoryRouter>
          <HRInterviews />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html2).toContain('No timeline events logged yet.');

    // 3. Test case: Loading state (timeline query not prefetched)
    const client3 = createClient();
    await Promise.all([
      client3.prefetchQuery({ queryKey: ['interview-jobs'], queryFn: () => mockGetInterviewJobs() }),
      client3.prefetchQuery({ queryKey: ['interview-candidates', 11], queryFn: () => mockGetInterviewCandidates() }),
      client3.prefetchQuery({ queryKey: ['interview-answers', 31], queryFn: () => mockGetInterviewCandidateAnswers() }),
      client3.prefetchQuery({ queryKey: ['interview-documents', 31], queryFn: () => mockGetInterviewCandidateDocuments() }),
      client3.prefetchQuery({ queryKey: ['interview-teams'], queryFn: () => mockGetTeamsDirectory() }),
      client3.prefetchQuery({ queryKey: ['interview-campaigns'], queryFn: () => mockGetCampaigns() }),
    ]);

    const html3 = renderToStaticMarkup(
      <QueryClientProvider client={client3}>
        <MemoryRouter>
          <HRInterviews />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html3).toContain('Loading timeline...');
  });
});
