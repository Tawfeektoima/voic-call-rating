/** @vitest-environment node */
import { describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';

import { PublicInterviewPortal } from '../pages/PublicInterviewPortal';

vi.mock('../lib/api', () => ({
  getInterviewPortalJobs: vi.fn(),
  getInterviewPortalDashboard: vi.fn(),
  registerInterviewPortalCandidate: vi.fn(),
  getInterviewPortalSession: vi.fn(),
  getInterviewPortalQuestions: vi.fn(),
  getInterviewPortalMcq: vi.fn(),
  startInterviewPortalQuestion: vi.fn(),
  submitInterviewPortalAnswer: vi.fn(),
  submitInterviewPortalMcq: vi.fn(),
  completeInterviewPortalSession: vi.fn(),
  getApiErrorMessage: () => 'Mock API error',
}));

describe('Public interview portal', () => {
  it('renders candidate registration when no session token is present', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/interview-portal']}>
        <PublicInterviewPortal />
      </MemoryRouter>
    );

    expect(html).toContain('Candidate Registration');
    expect(html).toContain('Register and Start');
    expect(html).toContain('Upload CV');
  });
});
