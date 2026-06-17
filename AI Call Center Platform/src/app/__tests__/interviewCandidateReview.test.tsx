/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes } from 'react-router';

import { InterviewCandidateReview } from '../pages/InterviewCandidateReview';

const mockGetInterviewCandidateReview = vi.fn();

vi.mock('../lib/api', () => ({
  getInterviewCandidateReview: (...args: unknown[]) => mockGetInterviewCandidateReview(...args),
  getApiErrorMessage: () => 'Mock API error',
}));

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

describe('Interview candidate review page', () => {
  beforeEach(() => {
    mockGetInterviewCandidateReview.mockResolvedValue({
      status: 'success',
      candidate: {
        id: 31,
        job_id: 11,
        full_name: 'Candidate Maya',
        contact_email: 'maya@example.com',
        contact_email_normalized: 'maya@example.com',
        phone_number: '01099999999',
        phone_normalized: '01099999999',
        national_id_last4: '4567',
        status: 'interviewing',
        final_score: 82,
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
      interview_metrics: {
        evaluation_state: 'Ready',
        submitted_answers: 2,
        evaluated_answers: 2,
        average_answer_score: 82,
        strongest_answer_score: 86,
        weakest_answer_score: 78,
      },
      mcq_summary: {
        completed: true,
        score: 12,
        total_questions: 15,
        percentage: 80,
        completed_at: '2026-06-15T10:00:00.000Z',
        objective_breakdown: {
          iq: 4,
          computer: 3,
        },
        personality_breakdown: {
          collaborative: 3,
          passive: 1,
        },
      },
      recommendation: {
        label: 'Proceed',
        score: 81.4,
        rationale: 'The candidate is meeting the current bar with a balanced interview and assessment profile.',
        strengths: [
          'Interview responses show strong communication and answer quality.',
          'Written assessment performance is above target.',
        ],
        concerns: [],
      },
      answers: [
        {
          answer_id: 91,
          question_id: 71,
          question_text: 'Tell me about a difficult customer situation you handled.',
          overall_score: 86,
          status: 'evaluated',
          ai_summary: 'Strong structure and practical ownership.',
          transcribed_text: 'I stayed calm, clarified the issue, and confirmed the next action.',
          submitted_at: '2026-06-14T00:00:00.000Z',
          evaluated_at: '2026-06-14T00:02:00.000Z',
          error_message: null,
        },
      ],
    });
  });

  it('renders the unified review summary and answer details', async () => {
    const client = createClient();
    await client.prefetchQuery({
      queryKey: ['interview-candidate-review', '31'],
      queryFn: () => mockGetInterviewCandidateReview(31),
    });

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/hr/interviews/candidates/31/review']}>
          <Routes>
            <Route path="/hr/interviews/candidates/:candidateId/review" element={<InterviewCandidateReview />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('Candidate Maya');
    expect(html).toContain('Decision Summary');
    expect(html).toContain('Interview Answers');
    expect(html).toContain('Written Assessment Snapshot');
    expect(html).toContain('Proceed');
    expect(html).toContain('81.4 composite score');
    expect(html).toContain('Tell me about a difficult customer situation you handled.');
  });
});
