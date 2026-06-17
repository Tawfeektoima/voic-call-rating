import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Brain, CheckCircle2, Cpu, Theater, XCircle } from 'lucide-react';
import { useNavigate, useParams } from 'react-router';

import { getApiErrorMessage, getInterviewCandidateMcqResults } from '../lib/api';
import { InterviewMcqReviewOut, InterviewMcqReviewQuestionOut } from '../lib/types';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { EmptyState, ErrorState, PageLoader } from '../components/ui/states';

function ObjectiveQuestionCard({
  question,
  index,
}: {
  question: InterviewMcqReviewQuestionOut;
  index: number;
}) {
  return (
    <div className="rounded-xl border border-border bg-background px-4 py-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Question {index + 1}</p>
          <h3 className="text-sm font-medium text-foreground mt-2 leading-6">{question.question_text}</h3>
        </div>
        <div
          className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${
            question.is_correct
              ? 'border border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
              : 'border border-rose-500/30 bg-rose-500/10 text-rose-200'
          }`}
        >
          {question.is_correct ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
          {question.is_correct ? 'Correct' : 'Incorrect'}
        </div>
      </div>

      <div className="space-y-2">
        {question.options.map((option, optionIndex) => {
          const isChosen = question.user_answer === optionIndex;
          const isCorrect = question.correct_answer === optionIndex;
          return (
            <div
              key={optionIndex}
              className={`rounded-lg border px-3 py-3 text-sm ${
                isCorrect
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-50'
                  : isChosen
                    ? 'border-amber-500/30 bg-amber-500/10 text-amber-50'
                    : 'border-border bg-card text-muted-foreground'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span>{option}</span>
                <span className="text-[11px] uppercase tracking-wide">
                  {isCorrect ? 'Correct answer' : isChosen ? 'Chosen answer' : `Option ${String.fromCharCode(65 + optionIndex)}`}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PersonalityQuestionCard({
  question,
  index,
}: {
  question: InterviewMcqReviewQuestionOut;
  index: number;
}) {
  return (
    <div className="rounded-xl border border-border bg-background px-4 py-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Scenario {index + 1}</p>
          <h3 className="text-sm font-medium text-foreground mt-2 leading-6">{question.question_text}</h3>
        </div>
        <div className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-medium text-sky-200 capitalize">
          {question.chosen_trait || 'No trait'}
        </div>
      </div>

      <div className="space-y-2">
        {question.options.map((option, optionIndex) => {
          const isChosen = question.user_answer === optionIndex;
          return (
            <div
              key={optionIndex}
              className={`rounded-lg border px-3 py-3 text-sm ${
                isChosen
                  ? 'border-primary bg-primary/10 text-foreground'
                  : 'border-border bg-card text-muted-foreground'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span>{option}</span>
                <span className="text-[11px] uppercase tracking-wide capitalize">
                  {question.trait_tags[optionIndex] || `Option ${String.fromCharCode(65 + optionIndex)}`}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ResultsSection({
  title,
  description,
  icon,
  questions,
  kind,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  questions: InterviewMcqReviewQuestionOut[];
  kind: 'objective' | 'personality';
}) {
  return (
    <Card className="border-border/70 bg-card/70">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          {icon}
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {questions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No questions recorded in this section.</p>
        ) : (
          questions.map((question, index) =>
            kind === 'objective' ? (
              <ObjectiveQuestionCard key={question.question_id} question={question} index={index} />
            ) : (
              <PersonalityQuestionCard key={question.question_id} question={question} index={index} />
            )
          )
        )}
      </CardContent>
    </Card>
  );
}

export function InterviewMcqReview() {
  const { candidateId } = useParams();
  const navigate = useNavigate();

  const query = useQuery({
    queryKey: ['interview-candidate-mcq-results', candidateId],
    enabled: Boolean(candidateId),
    queryFn: () => getInterviewCandidateMcqResults(Number(candidateId)),
  });

  if (query.isLoading) {
    return <PageLoader message="Loading written assessment review..." />;
  }

  if (query.isError) {
    return (
      <div className="p-6">
        <ErrorState
          message={getApiErrorMessage(query.error, 'Unable to load written assessment results.')}
          onRetry={() => query.refetch()}
        />
      </div>
    );
  }

  if (!query.data || query.data.status === 'no_results') {
    return (
      <div className="p-6 space-y-4 max-w-5xl mx-auto">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="icon" onClick={() => navigate('/hr/interviews')}>
            <ArrowLeft size={16} />
          </Button>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Interview Pipeline</p>
            <h1 className="text-2xl font-semibold text-foreground">Written Assessment Review</h1>
          </div>
        </div>
        <Card className="border-border/70 bg-card/70">
          <CardContent className="pt-6">
            <EmptyState
              title="No written assessment yet"
              description="This candidate has not submitted the post-interview MCQ assessment."
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  const data: InterviewMcqReviewOut = query.data;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button variant="outline" size="icon" onClick={() => navigate('/hr/interviews')}>
            <ArrowLeft size={16} />
          </Button>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Interview Pipeline</p>
            <h1 className="text-2xl font-semibold text-foreground mt-1">{data.candidate_name}</h1>
            <p className="text-sm text-muted-foreground mt-2">Written assessment review with section-by-section detail.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 min-w-[280px]">
          <div className="rounded-xl border border-border bg-card/70 px-4 py-3">
            <p className="text-xs text-muted-foreground">Total score</p>
            <p className="mt-1 text-lg font-semibold text-foreground">
              {data.score} / {data.total_questions}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card/70 px-4 py-3">
            <p className="text-xs text-muted-foreground">Percentage</p>
            <p className="mt-1 text-lg font-semibold text-foreground">{data.percentage}%</p>
          </div>
          <div className="rounded-xl border border-border bg-card/70 px-4 py-3">
            <p className="text-xs text-muted-foreground">Completed</p>
            <p className="mt-1 text-sm font-medium text-foreground">
              {data.completed_at ? new Date(data.completed_at).toLocaleString() : 'Not available'}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4 items-start">
        <div className="space-y-4">
          <ResultsSection
            title="IQ & Logic"
            description="Objective reasoning questions graded against the configured answer key."
            icon={<Brain size={16} className="text-primary" />}
            questions={data.iq}
            kind="objective"
          />
          <ResultsSection
            title="Computer Knowledge"
            description="Basic operational and workstation familiarity checks."
            icon={<Cpu size={16} className="text-primary" />}
            questions={data.computer}
            kind="objective"
          />
          <ResultsSection
            title="Situational Judgment"
            description="Behavioral scenarios showing the candidate's selected response style."
            icon={<Theater size={16} className="text-primary" />}
            questions={data.personality}
            kind="personality"
          />
        </div>

        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-base">Personality Pattern Summary</CardTitle>
            <CardDescription>Trait signals collected from situational choices in the written assessment.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.keys(data.personality_breakdown).length === 0 ? (
              <p className="text-sm text-muted-foreground">No situational trait signals were recorded.</p>
            ) : (
              Object.entries(data.personality_breakdown).map(([trait, count]) => {
                const ratio = data.personality.length > 0 ? (count / data.personality.length) * 100 : 0;
                return (
                  <div key={trait} className="space-y-2">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-foreground capitalize">{trait.replace('_', ' ')}</span>
                      <span className="text-xs text-muted-foreground">x {count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-secondary overflow-hidden">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${ratio}%` }} />
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
