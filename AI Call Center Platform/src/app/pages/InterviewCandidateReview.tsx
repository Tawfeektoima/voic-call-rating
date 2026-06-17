import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  ClipboardList,
  ExternalLink,
  Gauge,
  MessageSquareText,
} from 'lucide-react';
import { useNavigate, useParams } from 'react-router';

import { getApiErrorMessage, getInterviewCandidateReview } from '../lib/api';
import { InterviewCandidateReviewAnswer, InterviewCandidateReviewOut } from '../lib/types';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { EmptyState, ErrorState, PageLoader } from '../components/ui/states';

const recommendationStyles: Record<string, string> = {
  'Strong Hire': 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
  Proceed: 'border-sky-500/30 bg-sky-500/10 text-sky-200',
  Hold: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  'Do Not Proceed': 'border-rose-500/30 bg-rose-500/10 text-rose-200',
  'Provisional Review': 'border-violet-500/30 bg-violet-500/10 text-violet-200',
  'Pending Review': 'border-border bg-card text-muted-foreground',
};

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card/70 px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold text-foreground">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

function AnswerCard({ answer, index }: { answer: InterviewCandidateReviewAnswer; index: number }) {
  return (
    <div className="rounded-xl border border-border bg-background px-4 py-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Answer {index + 1}</p>
          <h3 className="mt-2 text-sm font-medium text-foreground leading-6">{answer.question_text}</h3>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-foreground">
            {answer.overall_score != null ? `${answer.overall_score.toFixed(1)} / 100` : 'Pending'}
          </p>
          <p className="mt-1 text-xs uppercase text-muted-foreground">{answer.status}</p>
        </div>
      </div>

      {answer.ai_summary ? (
        <div className="rounded-lg border border-border bg-card px-3 py-3">
          <p className="text-xs text-muted-foreground mb-2">AI summary</p>
          <p className="text-sm text-foreground leading-6">{answer.ai_summary}</p>
        </div>
      ) : null}

      {answer.transcribed_text ? (
        <div className="rounded-lg border border-border bg-card px-3 py-3">
          <p className="text-xs text-muted-foreground mb-2">Transcript</p>
          <p className="text-sm text-foreground leading-6 whitespace-pre-wrap">{answer.transcribed_text}</p>
        </div>
      ) : null}

      {answer.error_message ? (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-3">
          <p className="text-xs text-rose-200">{answer.error_message}</p>
        </div>
      ) : null}
    </div>
  );
}

export function InterviewCandidateReview() {
  const { candidateId } = useParams();
  const navigate = useNavigate();

  const query = useQuery({
    queryKey: ['interview-candidate-review', candidateId],
    enabled: Boolean(candidateId),
    queryFn: () => getInterviewCandidateReview(Number(candidateId)),
  });

  if (query.isLoading) {
    return <PageLoader message="Loading final candidate review..." />;
  }

  if (query.isError) {
    return (
      <div className="p-6">
        <ErrorState
          message={getApiErrorMessage(query.error, 'Unable to load the candidate review.')}
          onRetry={() => query.refetch()}
        />
      </div>
    );
  }

  if (!query.data) {
    return (
      <div className="p-6 max-w-5xl mx-auto">
        <Card className="border-border/70 bg-card/70">
          <CardContent className="pt-6">
            <EmptyState
              title="Candidate review unavailable"
              description="The requested candidate review could not be found."
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  const data: InterviewCandidateReviewOut = query.data;
  const { candidate, interview_metrics, mcq_summary, recommendation, answers } = data;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button variant="outline" size="icon" onClick={() => navigate('/hr/interviews')}>
            <ArrowLeft size={16} />
          </Button>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Interview Pipeline</p>
            <h1 className="text-2xl font-semibold text-foreground mt-1">{candidate.full_name}</h1>
            <p className="text-sm text-muted-foreground mt-2">
              Final review combining interview scoring, written assessment, and decision support.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          {mcq_summary.completed ? (
            <Button variant="outline" onClick={() => navigate(`/hr/interviews/candidates/${candidate.id}/mcq-review`)}>
              <ExternalLink size={15} />
              Open MCQ Detail
            </Button>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        <div className={`rounded-xl border px-4 py-3 ${recommendationStyles[recommendation.label] || recommendationStyles['Pending Review']}`}>
          <p className="text-xs">Recommendation</p>
          <p className="mt-1 text-lg font-semibold">{recommendation.label}</p>
          <p className="mt-1 text-xs">
            {recommendation.score != null ? `${recommendation.score.toFixed(1)} composite score` : 'Awaiting enough scored signals'}
          </p>
        </div>
        <StatCard label="Candidate status" value={candidate.status} />
        <StatCard label="Evaluation state" value={interview_metrics.evaluation_state} />
        <StatCard
          label="Written assessment"
          value={mcq_summary.completed && mcq_summary.percentage != null ? `${mcq_summary.percentage}%` : 'Not submitted'}
          hint={mcq_summary.completed_at ? new Date(mcq_summary.completed_at).toLocaleString() : undefined}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px] gap-4 items-start">
        <div className="space-y-4">
          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <BadgeCheck size={16} className="text-primary" />
                Decision Summary
              </CardTitle>
              <CardDescription>Recommendation logic distilled from the currently available interview signals.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-xl border border-border bg-background px-4 py-4">
                <p className="text-sm text-foreground leading-6">{recommendation.rationale}</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="rounded-xl border border-border bg-background px-4 py-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <BadgeCheck size={15} className="text-emerald-300" />
                    <p className="text-sm font-medium text-foreground">Strengths</p>
                  </div>
                  {recommendation.strengths.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No strong positive signals have been recorded yet.</p>
                  ) : (
                    recommendation.strengths.map((item) => (
                      <p key={item} className="text-sm text-foreground leading-6">
                        {item}
                      </p>
                    ))
                  )}
                </div>
                <div className="rounded-xl border border-border bg-background px-4 py-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={15} className="text-amber-300" />
                    <p className="text-sm font-medium text-foreground">Concerns</p>
                  </div>
                  {recommendation.concerns.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No major concerns are currently flagged.</p>
                  ) : (
                    recommendation.concerns.map((item) => (
                      <p key={item} className="text-sm text-foreground leading-6">
                        {item}
                      </p>
                    ))
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <MessageSquareText size={16} className="text-primary" />
                Interview Answers
              </CardTitle>
              <CardDescription>Question-by-question summaries, transcripts, and scoring details.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {answers.length === 0 ? (
                <p className="text-sm text-muted-foreground">No submitted answers yet.</p>
              ) : (
                answers.map((answer, index) => <AnswerCard key={answer.answer_id} answer={answer} index={index} />)
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Gauge size={16} className="text-primary" />
                Interview Signal
              </CardTitle>
              <CardDescription>Quick read on scoring depth and current answer quality.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <StatCard label="Submitted answers" value={String(interview_metrics.submitted_answers)} />
              <StatCard label="Evaluated answers" value={String(interview_metrics.evaluated_answers)} />
              <StatCard
                label="Average score"
                value={interview_metrics.average_answer_score != null ? `${interview_metrics.average_answer_score.toFixed(1)} / 100` : 'Pending'}
              />
              <StatCard
                label="Range"
                value={
                  interview_metrics.strongest_answer_score != null && interview_metrics.weakest_answer_score != null
                    ? `${interview_metrics.weakest_answer_score.toFixed(1)} - ${interview_metrics.strongest_answer_score.toFixed(1)}`
                    : 'Pending'
                }
              />
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <ClipboardList size={16} className="text-primary" />
                Written Assessment Snapshot
              </CardTitle>
              <CardDescription>Objective sections and personality tendencies from the post-interview MCQ.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!mcq_summary.completed ? (
                <p className="text-sm text-muted-foreground">The written assessment has not been submitted yet.</p>
              ) : (
                <>
                  <div className="rounded-xl border border-border bg-background px-4 py-3">
                    <p className="text-xs text-muted-foreground">Score</p>
                    <p className="mt-1 text-lg font-semibold text-foreground">
                      {mcq_summary.score} / {mcq_summary.total_questions} ({mcq_summary.percentage}%)
                    </p>
                  </div>

                  <div className="rounded-xl border border-border bg-background px-4 py-3 space-y-2">
                    <p className="text-xs text-muted-foreground">Objective sections</p>
                    {Object.keys(mcq_summary.objective_breakdown).length === 0 ? (
                      <p className="text-sm text-muted-foreground">No objective section data recorded.</p>
                    ) : (
                      Object.entries(mcq_summary.objective_breakdown).map(([category, value]) => (
                        <div key={category} className="flex items-center justify-between gap-3 text-sm">
                          <span className="capitalize text-foreground">{category.replace('_', ' ')}</span>
                          <span className="text-muted-foreground">{value}</span>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="rounded-xl border border-border bg-background px-4 py-3 space-y-2">
                    <p className="text-xs text-muted-foreground">Personality pattern</p>
                    {Object.keys(mcq_summary.personality_breakdown).length === 0 ? (
                      <p className="text-sm text-muted-foreground">No personality signals recorded.</p>
                    ) : (
                      Object.entries(mcq_summary.personality_breakdown).map(([trait, value]) => (
                        <div key={trait} className="flex items-center justify-between gap-3 text-sm">
                          <span className="capitalize text-foreground">{trait.replace('_', ' ')}</span>
                          <span className="text-muted-foreground">{value}</span>
                        </div>
                      ))
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
