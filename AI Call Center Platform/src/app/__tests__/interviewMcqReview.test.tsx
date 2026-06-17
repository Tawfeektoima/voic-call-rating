/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes } from 'react-router';

import { InterviewMcqReview } from '../pages/InterviewMcqReview';

const mockGetInterviewCandidateMcqResults = vi.fn();

vi.mock('../lib/api', () => ({
  getInterviewCandidateMcqResults: (...args: unknown[]) => mockGetInterviewCandidateMcqResults(...args),
  getApiErrorMessage: () => 'Mock API error',
}));

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

describe('Interview MCQ review page', () => {
  beforeEach(() => {
    mockGetInterviewCandidateMcqResults.mockResolvedValue({
      status: 'success',
      candidate_id: 31,
      candidate_name: 'Candidate Maya',
      score: 12,
      total_questions: 15,
      percentage: 80,
      completed_at: '2026-06-15T10:00:00.000Z',
      iq: [
        {
          question_id: 1,
          question_text: 'What is the next number in the sequence?',
          options: ['36', '48', '60', '72'],
          user_answer: 1,
          correct_answer: 1,
          type: 'pattern',
          is_correct: true,
          trait_tags: [],
          chosen_trait: null,
        },
      ],
      computer: [
        {
          question_id: 6,
          question_text: 'Which component executes instructions?',
          options: ['RAM', 'GPU', 'CPU', 'Motherboard'],
          user_answer: 0,
          correct_answer: 2,
          type: 'hardware',
          is_correct: false,
          trait_tags: [],
          chosen_trait: null,
        },
      ],
      personality: [
        {
          question_id: 11,
          question_text: 'A team member is consistently late. How do you handle it?',
          options: ['Offer help', 'Wait silently', 'Criticize publicly', 'Escalate immediately'],
          user_answer: 0,
          correct_answer: 0,
          type: 'situational',
          is_correct: null,
          trait_tags: ['collaborative', 'passive', 'aggressive', 'impulsive'],
          chosen_trait: 'collaborative',
        },
      ],
      personality_breakdown: {
        collaborative: 1,
        passive: 0,
        aggressive: 0,
        impulsive: 0,
      },
    });
  });

  it('renders review sections and personality summary', async () => {
    const client = createClient();
    await client.prefetchQuery({
      queryKey: ['interview-candidate-mcq-results', '31'],
      queryFn: () => mockGetInterviewCandidateMcqResults(31),
    });

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/hr/interviews/candidates/31/mcq-review']}>
          <Routes>
            <Route path="/hr/interviews/candidates/:candidateId/mcq-review" element={<InterviewMcqReview />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('Candidate Maya');
    expect(html).toContain('IQ &amp; Logic');
    expect(html).toContain('Computer Knowledge');
    expect(html).toContain('Situational Judgment');
    expect(html).toContain('Personality Pattern Summary');
    expect(html).toContain('collaborative');
    expect(html).toContain('12 / 15');
  });
});
