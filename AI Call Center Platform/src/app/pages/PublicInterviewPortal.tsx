import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { BriefcaseBusiness, CheckCircle2, Clock3, FileAudio, FileText, Loader2, RefreshCcw, Send, ShieldAlert, UserRoundPlus } from 'lucide-react';
import { toast } from 'sonner';

import {
  completeInterviewPortalSession,
  getApiErrorMessage,
  getInterviewPortalDashboard,
  getInterviewPortalMcq,
  getInterviewPortalJobs,
  getInterviewPortalQuestions,
  getInterviewPortalSession,
  registerInterviewPortalCandidate,
  startInterviewPortalQuestion,
  submitInterviewPortalMcq,
  submitInterviewPortalAnswer,
} from '../lib/api';
import { InterviewMcqPortalOut, InterviewPortalDashboardOut, InterviewPortalJob, InterviewPortalSessionOut, InterviewQuestionOut } from '../lib/types';

type AnswerDraft = {
  transcript: string;
  audioFile: File | null;
  status: 'idle' | 'starting' | 'started' | 'submitting' | 'submitted';
  startedAt?: string;
  timeLimitSeconds?: number;
};

export function PublicInterviewPortal() {
  const [searchParams] = useSearchParams();
  const tokenFromUrl = (searchParams.get('token') || '').trim();
  const jobIdFromUrl = (searchParams.get('job_id') || '').trim();
  const [registeredSessionToken, setRegisteredSessionToken] = useState('');
  const sessionToken = registeredSessionToken || tokenFromUrl;
  const [jobs, setJobs] = useState<InterviewPortalJob[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [registrationSubmitting, setRegistrationSubmitting] = useState(false);
  const [registrationForm, setRegistrationForm] = useState({
    job_id: '',
    full_name: '',
    contact_email: '',
    phone_number: '',
    national_id: '',
    date_of_birth: '',
    address: '',
    manual_experience: '',
    cv_file: null as File | null,
  });
  const [session, setSession] = useState<InterviewPortalSessionOut | null>(null);
  const [dashboard, setDashboard] = useState<InterviewPortalDashboardOut | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [questions, setQuestions] = useState<InterviewQuestionOut[]>([]);
  const [mcq, setMcq] = useState<InterviewMcqPortalOut | null>(null);
  const [mcqAnswers, setMcqAnswers] = useState<Record<string, number>>({});
  const [mcqSubmitting, setMcqSubmitting] = useState(false);
  const [mcqSubmitted, setMcqSubmitted] = useState(false);
  const [answerDrafts, setAnswerDrafts] = useState<Record<number, AnswerDraft>>({});
  const [portalStep, setPortalStep] = useState<'instructions' | 'interview'>('instructions');
  const [now, setNow] = useState(() => Date.now());
  const [loading, setLoading] = useState(Boolean(tokenFromUrl));
  const [submittingComplete, setSubmittingComplete] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const loadPortal = async () => {
      if (!sessionToken) {
        setErrorMessage(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      setErrorMessage(null);
      try {
        const [sessionData, questionData] = await Promise.all([
          getInterviewPortalSession(sessionToken),
          getInterviewPortalQuestions(sessionToken),
        ]);
        const mcqData = await getInterviewPortalMcq(sessionToken);
        setSession(sessionData);
        setQuestions(questionData);
        setMcq(mcqData);
        setMcqSubmitted(mcqData.mcq_completed);
        if (sessionData.status === 'completed') {
          setDashboardLoading(true);
          try {
            setDashboard(await getInterviewPortalDashboard(sessionToken));
          } finally {
            setDashboardLoading(false);
          }
        }
        setAnswerDrafts(
          Object.fromEntries(
            questionData.map((question) => [
              question.id,
              { transcript: '', audioFile: null, status: 'idle' as const },
            ]),
          ),
        );
        setPortalStep('instructions');
      } catch (error) {
        setErrorMessage(getApiErrorMessage(error, 'Could not load this interview session.'));
      } finally {
        setLoading(false);
      }
    };

    void loadPortal();
  }, [sessionToken]);

  useEffect(() => {
    if (portalStep !== 'interview') return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [portalStep]);

  useEffect(() => {
    const loadJobs = async () => {
      if (sessionToken) return;
      setJobsLoading(true);
      try {
        const jobData = await getInterviewPortalJobs();
        setJobs(jobData);
        setRegistrationForm((current) => ({
          ...current,
          job_id:
            current.job_id ||
            (jobIdFromUrl && jobData.some((job) => String(job.id) === jobIdFromUrl)
              ? jobIdFromUrl
              : (jobData[0] ? String(jobData[0].id) : '')),
        }));
      } catch (error) {
        toast.error(getApiErrorMessage(error, 'Could not load open interview jobs.'));
      } finally {
        setJobsLoading(false);
      }
    };

    void loadJobs();
  }, [sessionToken]);

  useEffect(() => {
    if (!jobIdFromUrl || sessionToken) return;
    setRegistrationForm((current) => ({
      ...current,
      job_id: current.job_id || jobIdFromUrl,
    }));
  }, [jobIdFromUrl, sessionToken]);

  const submittedCount = useMemo(
    () => Object.values(answerDrafts).filter((draft) => draft.status === 'submitted').length,
    [answerDrafts],
  );
  const allInterviewQuestionsSubmitted = questions.length > 0 && submittedCount === questions.length;
  const mcqAnsweredCount = useMemo(() => Object.keys(mcqAnswers).length, [mcqAnswers]);
  const mcqIsRequired = Boolean(mcq?.mcq_enabled);
  const mcqReadyToSubmit = Boolean(mcq && mcq.questions.length > 0 && mcqAnsweredCount === mcq.questions.length);
  const canCompleteInterview = allInterviewQuestionsSubmitted && (!mcqIsRequired || mcqSubmitted);

  const handleTranscriptChange = (questionId: number, transcript: string) => {
    setAnswerDrafts((current) => ({
      ...current,
      [questionId]: { ...(current[questionId] || { transcript: '', audioFile: null, status: 'idle' }), transcript },
    }));
  };

  const handleRegistrationSubmit = async () => {
    const effectiveJobId = registrationForm.job_id || jobIdFromUrl;
    if (!effectiveJobId || !registrationForm.full_name.trim() || !registrationForm.contact_email.trim()) {
      toast.error('Choose a job and add your name and email first.');
      return;
    }

    setRegistrationSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('job_id', effectiveJobId);
      formData.append('full_name', registrationForm.full_name.trim());
      formData.append('contact_email', registrationForm.contact_email.trim());
      if (registrationForm.phone_number.trim()) formData.append('phone_number', registrationForm.phone_number.trim());
      if (registrationForm.national_id.trim()) formData.append('national_id', registrationForm.national_id.trim());
      if (registrationForm.date_of_birth) formData.append('date_of_birth', registrationForm.date_of_birth);
      if (registrationForm.address.trim()) formData.append('address', registrationForm.address.trim());
      if (registrationForm.manual_experience.trim()) formData.append('manual_experience', registrationForm.manual_experience.trim());
      if (registrationForm.cv_file) formData.append('cv_file', registrationForm.cv_file);

      const response = await registerInterviewPortalCandidate(formData);
      setLoading(true);
      setRegisteredSessionToken(response.session_token);
      toast.success(response.duplicate_recent ? 'Existing application refreshed.' : 'Application registered successfully.');
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not register your application.'));
    } finally {
      setRegistrationSubmitting(false);
    }
  };

  const handleAudioChange = (questionId: number, audioFile: File | null) => {
    setAnswerDrafts((current) => ({
      ...current,
      [questionId]: { ...(current[questionId] || { transcript: '', audioFile: null, status: 'idle' }), audioFile },
    }));
  };

  const handleStartQuestion = async (questionId: number) => {
    if (!sessionToken) return;
    setAnswerDrafts((current) => ({
      ...current,
      [questionId]: { ...(current[questionId] || { transcript: '', audioFile: null, status: 'idle' }), status: 'starting' },
    }));
    try {
      const response = await startInterviewPortalQuestion(sessionToken, questionId);
      setAnswerDrafts((current) => ({
        ...current,
        [questionId]: {
          ...(current[questionId] || { transcript: '', audioFile: null, status: 'idle' }),
          status: 'started',
          startedAt: response.started_at,
          timeLimitSeconds: response.time_limit_seconds,
        },
      }));
      toast.success('Question timer started.');
    } catch (error) {
      setAnswerDrafts((current) => ({
        ...current,
        [questionId]: { ...(current[questionId] || { transcript: '', audioFile: null, status: 'idle' }), status: 'idle' },
      }));
      toast.error(getApiErrorMessage(error, 'Could not start this question.'));
    }
  };

  const handleSubmitAnswer = async (questionId: number) => {
    const draft = answerDrafts[questionId];
    if (!draft) return;
    if (!draft.startedAt) {
      toast.error('Start the question timer before submitting your answer.');
      return;
    }
    if (!draft.transcript.trim() && !draft.audioFile) {
      toast.error('Add a written answer or upload an audio response first.');
      return;
    }

    setAnswerDrafts((current) => ({
      ...current,
      [questionId]: { ...current[questionId], status: 'submitting' },
    }));

    try {
      const formData = new FormData();
      if (draft.transcript.trim()) {
        formData.append('transcript_text', draft.transcript.trim());
      }
      if (draft.audioFile) {
        formData.append('audio_file', draft.audioFile);
      }
      const response = await submitInterviewPortalAnswer(sessionToken, questionId, formData);
      setAnswerDrafts((current) => ({
        ...current,
        [questionId]: { ...current[questionId], status: 'submitted' },
      }));
      if (response.status === 'timeout') {
        toast.error('Answer submitted after the time limit and was marked as timed out.');
      } else {
        toast.success('Answer submitted successfully.');
      }
    } catch (error) {
      setAnswerDrafts((current) => ({
        ...current,
        [questionId]: { ...current[questionId], status: 'idle' },
      }));
      toast.error(getApiErrorMessage(error, 'Could not submit your answer.'));
    }
  };

  const handleCompleteSession = async () => {
    if (!sessionToken) return;
    if (!allInterviewQuestionsSubmitted) {
      toast.error('Submit all interview answers before finishing the interview.');
      return;
    }
    if (mcqIsRequired && !mcqSubmitted) {
      toast.error('Complete the written assessment before finishing the interview.');
      return;
    }
    setSubmittingComplete(true);
    try {
      const response = await completeInterviewPortalSession(sessionToken);
      setSession((current) => (current ? { ...current, status: response.status === 'completed' ? 'completed' : current.status } : current));
      setDashboard(await getInterviewPortalDashboard(sessionToken));
      toast.success('Interview session completed.');
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not complete the interview session.'));
    } finally {
      setSubmittingComplete(false);
    }
  };

  const refreshDashboard = async () => {
    if (!sessionToken) return;
    setDashboardLoading(true);
    try {
      setDashboard(await getInterviewPortalDashboard(sessionToken));
      toast.success('Candidate summary refreshed.');
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not refresh your interview summary.'));
    } finally {
      setDashboardLoading(false);
    }
  };

  const getRemainingSeconds = (draft: AnswerDraft) => {
    if (!draft.startedAt || draft.status === 'submitted') return null;
    const limit = draft.timeLimitSeconds ?? session?.question_time_limit_seconds ?? 180;
    const elapsed = Math.floor((now - new Date(draft.startedAt).getTime()) / 1000);
    return Math.max(limit - elapsed, 0);
  };

  const handleMcqSelect = (questionId: number, optionIndex: number) => {
    setMcqAnswers((current) => ({ ...current, [String(questionId)]: optionIndex }));
  };

  const handleSubmitMcq = async () => {
    if (!sessionToken || !mcqReadyToSubmit) return;
    setMcqSubmitting(true);
    try {
      await submitInterviewPortalMcq(sessionToken, mcqAnswers);
      setMcqSubmitted(true);
      toast.success('Written assessment submitted successfully.');
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not submit the written assessment.'));
    } finally {
      setMcqSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Loader2 className="size-5 animate-spin text-primary" />
          Preparing your interview workspace...
        </div>
      </div>
    );
  }

  if (!sessionToken) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
          <section className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
            <div className="flex items-start gap-3">
              <div className="size-10 rounded-xl border border-border bg-background inline-flex items-center justify-center">
                <UserRoundPlus className="size-5 text-primary" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-primary">Interview Portal</p>
                <h1 className="text-2xl font-semibold mt-2">Candidate Registration</h1>
                <p className="text-sm text-muted-foreground mt-2">
                  Apply to an open interview job and start your session after registration.
                </p>
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px] gap-4 items-start">
            <div className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="space-y-2 md:col-span-2">
                  <span className="text-xs font-medium text-muted-foreground">Open job</span>
                  <select
                    value={registrationForm.job_id}
                    disabled={jobsLoading}
                    onChange={(event) => setRegistrationForm((current) => ({ ...current, job_id: event.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                  >
                    {jobs.length === 0 ? (
                      <option value="">No open jobs available</option>
                    ) : (
                      jobs.map((job) => (
                        <option key={job.id} value={job.id}>
                          {job.title}
                        </option>
                      ))
                    )}
                  </select>
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Full name</span>
                  <input
                    value={registrationForm.full_name}
                    onChange={(event) => setRegistrationForm((current) => ({ ...current, full_name: event.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Email</span>
                  <input
                    value={registrationForm.contact_email}
                    onChange={(event) => setRegistrationForm((current) => ({ ...current, contact_email: event.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Phone number</span>
                  <input
                    value={registrationForm.phone_number}
                    onChange={(event) => setRegistrationForm((current) => ({ ...current, phone_number: event.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">National ID</span>
                  <input
                    value={registrationForm.national_id}
                    onChange={(event) => setRegistrationForm((current) => ({ ...current, national_id: event.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Date of birth</span>
                  <input
                    type="date"
                    value={registrationForm.date_of_birth}
                    onChange={(event) => setRegistrationForm((current) => ({ ...current, date_of_birth: event.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Address</span>
                  <input
                    value={registrationForm.address}
                    onChange={(event) => setRegistrationForm((current) => ({ ...current, address: event.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                  />
                </label>
              </div>

              <label className="space-y-2 block">
                <span className="text-xs font-medium text-muted-foreground">Manual experience</span>
                <textarea
                  value={registrationForm.manual_experience}
                  onChange={(event) => setRegistrationForm((current) => ({ ...current, manual_experience: event.target.value }))}
                  className="w-full min-h-[120px] rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground"
                />
              </label>

              <div className="flex flex-wrap items-center gap-3">
                <label className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-2 text-sm cursor-pointer">
                  <FileText className="size-4" />
                  Upload CV
                  <input
                    type="file"
                    accept=".pdf,.txt,.md,.docx"
                    onChange={(event) => setRegistrationForm((current) => ({ ...current, cv_file: event.target.files?.[0] || null }))}
                    className="hidden"
                  />
                </label>
                <p className="text-xs text-muted-foreground break-all">
                  {registrationForm.cv_file ? registrationForm.cv_file.name : 'PDF, DOCX, TXT, or MD'}
                </p>
              </div>

              <button
                onClick={() => void handleRegistrationSubmit()}
                disabled={registrationSubmitting || jobs.length === 0}
                className="h-11 px-5 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
              >
                {registrationSubmitting ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                Register and Start
              </button>
            </div>

            <aside className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
              <div className="flex items-center gap-2">
                <BriefcaseBusiness className="size-4 text-primary" />
                <h2 className="text-base font-semibold">Selected Job</h2>
              </div>
              {jobsLoading ? (
                <p className="text-sm text-muted-foreground">Loading open jobs...</p>
              ) : (
                (() => {
                  const selectedJob = jobs.find((job) => String(job.id) === registrationForm.job_id);
                  if (!selectedJob) {
                    return <p className="text-sm text-muted-foreground">No open job selected.</p>;
                  }
                  return (
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium text-foreground">{selectedJob.title}</h3>
                      <p className="text-sm text-muted-foreground leading-6">{selectedJob.description}</p>
                      <div className="rounded-xl border border-border bg-background px-3 py-2">
                        <p className="text-xs text-muted-foreground">Written assessment</p>
                        <p className="mt-1 text-sm text-foreground">{selectedJob.mcq_enabled ? 'Required' : 'Not required'}</p>
                      </div>
                    </div>
                  );
                })()
              )}
            </aside>
          </section>
        </div>
      </div>
    );
  }

  if (errorMessage || !session) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-6">
        <div className="w-full max-w-xl rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 space-y-3">
          <div className="flex items-center gap-3 text-rose-200">
            <ShieldAlert className="size-5" />
            <h1 className="text-lg font-semibold">Interview link unavailable</h1>
          </div>
          <p className="text-sm text-rose-100">{errorMessage || 'This interview session could not be loaded.'}</p>
        </div>
      </div>
    );
  }

  if (session.status === 'completed') {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
          <section className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-primary">Candidate Dashboard</p>
                <h1 className="text-2xl font-semibold mt-2">{dashboard?.job_title || session.job_title}</h1>
                <p className="text-sm text-muted-foreground mt-2">
                  Candidate: {dashboard?.candidate_name || session.candidate_name}
                </p>
              </div>
              <button
                type="button"
                onClick={() => void refreshDashboard()}
                disabled={dashboardLoading}
                className="h-10 px-4 rounded-xl border border-border bg-background text-sm text-foreground inline-flex items-center gap-2 disabled:opacity-50"
              >
                {dashboardLoading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCcw className="size-4" />}
                Refresh
              </button>
            </div>
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
              Your interview has been submitted successfully. Evaluation results may continue updating while the hiring team reviews your application.
            </div>
          </section>

          {dashboardLoading && !dashboard ? (
            <div className="rounded-2xl border border-border bg-card/80 p-6 text-sm text-muted-foreground inline-flex items-center gap-3">
              <Loader2 className="size-4 animate-spin text-primary" />
              Loading your interview summary...
            </div>
          ) : (
            <>
              <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
                <div className="rounded-xl border border-border bg-card/80 px-4 py-3">
                  <p className="text-xs text-muted-foreground">Session status</p>
                  <p className="mt-1 text-lg font-semibold capitalize">{dashboard?.session_status || session.status}</p>
                </div>
                <div className="rounded-xl border border-border bg-card/80 px-4 py-3">
                  <p className="text-xs text-muted-foreground">Answers submitted</p>
                  <p className="mt-1 text-lg font-semibold">
                    {dashboard ? `${dashboard.submitted_answers}/${dashboard.question_count}` : `${submittedCount}/${session.question_count}`}
                  </p>
                </div>
                <div className="rounded-xl border border-border bg-card/80 px-4 py-3">
                  <p className="text-xs text-muted-foreground">Evaluated answers</p>
                  <p className="mt-1 text-lg font-semibold">{dashboard?.evaluated_answers ?? 0}</p>
                </div>
                <div className="rounded-xl border border-border bg-card/80 px-4 py-3">
                  <p className="text-xs text-muted-foreground">Average score</p>
                  <p className="mt-1 text-lg font-semibold">
                    {dashboard?.average_score != null ? `${dashboard.average_score.toFixed(1)} / 100` : 'Pending'}
                  </p>
                </div>
              </section>

              <section className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px] gap-4 items-start">
                <div className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
                  <div>
                    <h2 className="text-lg font-semibold">Interview Answers</h2>
                    <p className="text-sm text-muted-foreground mt-1">Your submitted answers and current evaluation state.</p>
                  </div>
                  {!dashboard || dashboard.answers.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No submitted answers are available yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {dashboard.answers.map((answer, index) => (
                        <div key={answer.answer_id} className="rounded-xl border border-border bg-background px-4 py-4 space-y-3">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <p className="text-xs uppercase tracking-wide text-muted-foreground">Answer {index + 1}</p>
                              <h3 className="text-sm font-medium text-foreground mt-2 leading-6">{answer.question_text}</h3>
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-semibold text-foreground">
                                {answer.overall_score != null ? `${answer.overall_score.toFixed(1)} / 100` : 'Pending'}
                              </p>
                              <p className="text-xs uppercase text-muted-foreground mt-1">{answer.status}</p>
                            </div>
                          </div>
                          {answer.ai_summary ? (
                            <p className="text-sm text-muted-foreground leading-6">{answer.ai_summary}</p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <aside className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
                  <div>
                    <h2 className="text-lg font-semibold">Written Assessment</h2>
                    <p className="text-sm text-muted-foreground mt-1">Your MCQ submission summary.</p>
                  </div>
                  {!dashboard?.mcq_result.completed ? (
                    <p className="text-sm text-muted-foreground">No written assessment result is available.</p>
                  ) : (
                    <>
                      <div className="rounded-xl border border-border bg-background px-4 py-3">
                        <p className="text-xs text-muted-foreground">Score</p>
                        <p className="mt-1 text-lg font-semibold text-foreground">
                          {dashboard.mcq_result.score} / {dashboard.mcq_result.total_questions} ({dashboard.mcq_result.percentage}%)
                        </p>
                      </div>
                      <div className="rounded-xl border border-border bg-background px-4 py-3 space-y-2">
                        <p className="text-xs text-muted-foreground">Objective sections</p>
                        {Object.keys(dashboard.mcq_result.objective_breakdown).length === 0 ? (
                          <p className="text-sm text-muted-foreground">No objective breakdown recorded.</p>
                        ) : (
                          Object.entries(dashboard.mcq_result.objective_breakdown).map(([category, value]) => (
                            <div key={category} className="flex items-center justify-between gap-3 text-sm">
                              <span className="capitalize text-foreground">{category.replace('_', ' ')}</span>
                              <span className="text-muted-foreground">{value}</span>
                            </div>
                          ))
                        )}
                      </div>
                    </>
                  )}
                </aside>
              </section>
            </>
          )}
        </div>
      </div>
    );
  }

  if (portalStep === 'instructions') {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
          <section className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
            <p className="text-xs uppercase tracking-wide text-primary">Interview Instructions</p>
            <div>
              <h1 className="text-2xl font-semibold">{session.job_title}</h1>
              <p className="text-sm text-muted-foreground mt-2">Candidate: {session.candidate_name}</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="rounded-xl border border-border bg-background px-4 py-3">
                <p className="text-xs text-muted-foreground">Questions</p>
                <p className="mt-1 text-lg font-semibold">{session.question_count}</p>
              </div>
              <div className="rounded-xl border border-border bg-background px-4 py-3">
                <p className="text-xs text-muted-foreground">Time per question</p>
                <p className="mt-1 text-lg font-semibold">{Math.round(session.question_time_limit_seconds / 60)} min</p>
              </div>
              <div className="rounded-xl border border-border bg-background px-4 py-3">
                <p className="text-xs text-muted-foreground">Written assessment</p>
                <p className="mt-1 text-lg font-semibold">{session.mcq_enabled ? 'Required' : 'Optional'}</p>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
            <h2 className="text-lg font-semibold">Before you begin</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-muted-foreground">
              <div className="rounded-xl border border-border bg-background px-4 py-3">
                Start each question only when you are ready. The timer starts immediately.
              </div>
              <div className="rounded-xl border border-border bg-background px-4 py-3">
                Submit your answer before the timer reaches zero. Late answers are scored as timed out.
              </div>
              <div className="rounded-xl border border-border bg-background px-4 py-3">
                You can type an answer, upload audio, or send both together.
              </div>
              <div className="rounded-xl border border-border bg-background px-4 py-3">
                Complete all interview questions before the written assessment and final submission.
              </div>
            </div>
            <button
              type="button"
              onClick={() => setPortalStep('interview')}
              className="h-11 px-5 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2"
            >
              <CheckCircle2 className="size-4" />
              Begin Interview
            </button>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        <section className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-primary">Interview Portal</p>
              <h1 className="text-2xl font-semibold mt-2">{session.job_title}</h1>
              <p className="text-sm text-muted-foreground mt-2">Candidate: {session.candidate_name}</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm min-w-[260px]">
              <div className="rounded-xl border border-border bg-background px-4 py-3">
                <p className="text-xs text-muted-foreground">Status</p>
                <p className="mt-1 font-medium capitalize">{session.status}</p>
              </div>
              <div className="rounded-xl border border-border bg-background px-4 py-3">
                <p className="text-xs text-muted-foreground">Expires</p>
                <p className="mt-1 font-medium">{new Date(session.expires_at).toLocaleString()}</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl border border-border bg-background px-4 py-3">
              <p className="text-xs text-muted-foreground">Questions</p>
              <p className="mt-1 text-lg font-semibold">{session.question_count}</p>
            </div>
            <div className="rounded-xl border border-border bg-background px-4 py-3">
              <p className="text-xs text-muted-foreground">Submitted here</p>
              <p className="mt-1 text-lg font-semibold">{submittedCount}</p>
            </div>
            <div className="rounded-xl border border-border bg-background px-4 py-3">
              <p className="text-xs text-muted-foreground">Guidance</p>
              <p className="mt-1 text-sm">You can type your response, upload audio, or send both together.</p>
            </div>
          </div>
        </section>

        <section className="space-y-4">
          {questions.map((question, index) => {
            const draft = answerDrafts[question.id] || { transcript: '', audioFile: null, status: 'idle' as const };
            const isSubmitted = draft.status === 'submitted';
            const hasStarted = Boolean(draft.startedAt);
            const remainingSeconds = getRemainingSeconds(draft);
            const isExpired = remainingSeconds === 0 && hasStarted && !isSubmitted;
            return (
              <article key={question.id} className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Question {index + 1}</p>
                    <h2 className="text-lg font-medium mt-2 leading-7">{question.question_text}</h2>
                  </div>
                  <div className="rounded-full border px-3 py-1 text-xs font-medium capitalize">
                    {isSubmitted ? 'submitted' : question.source.replace('_', ' ')}
                  </div>
                </div>

                {!hasStarted && !isSubmitted ? (
                  <button
                    type="button"
                    onClick={() => void handleStartQuestion(question.id)}
                    disabled={draft.status === 'starting'}
                    className="h-10 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                  >
                    {draft.status === 'starting' ? <Loader2 className="size-4 animate-spin" /> : <Clock3 className="size-4" />}
                    Start Question
                  </button>
                ) : (
                  <>
                    <div className={`rounded-xl border px-4 py-3 text-sm ${
                      isExpired ? 'border-rose-500/30 bg-rose-500/10 text-rose-100' : 'border-border bg-background text-foreground'
                    }`}>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <span className="inline-flex items-center gap-2">
                          <Clock3 className="size-4" />
                          Time remaining
                        </span>
                        <span className="font-semibold">
                          {isSubmitted
                            ? 'Submitted'
                            : remainingSeconds == null
                              ? 'Not started'
                              : `${Math.floor(remainingSeconds / 60)}:${String(remainingSeconds % 60).padStart(2, '0')}`}
                        </span>
                      </div>
                    </div>

                    <label className="block space-y-2">
                      <span className="text-xs font-medium text-muted-foreground">Written response</span>
                      <textarea
                        value={draft.transcript}
                        onChange={(event) => handleTranscriptChange(question.id, event.target.value)}
                        disabled={isSubmitted}
                        className="w-full min-h-[140px] rounded-xl border border-border bg-background px-4 py-3 text-sm leading-6 disabled:opacity-70"
                        placeholder="Write your answer here..."
                      />
                    </label>

                    <div className="flex flex-wrap items-center gap-3">
                      <label className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-2 text-sm cursor-pointer">
                        <FileAudio className="size-4" />
                        Upload audio
                        <input
                          type="file"
                          accept="audio/*"
                          disabled={isSubmitted}
                          onChange={(event) => handleAudioChange(question.id, event.target.files?.[0] || null)}
                          className="hidden"
                        />
                      </label>
                      <p className="text-xs text-muted-foreground break-all">
                        {draft.audioFile ? draft.audioFile.name : 'Optional audio answer'}
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="text-xs text-muted-foreground flex items-center gap-2">
                        {isSubmitted ? <CheckCircle2 className="size-4 text-emerald-400" /> : <Clock3 className="size-4" />}
                        {isSubmitted
                          ? 'Answer received and queued for evaluation.'
                          : isExpired
                            ? 'This answer is past the time limit and may be scored as timed out.'
                            : 'Submit when this answer is ready.'}
                      </div>
                      <button
                        onClick={() => void handleSubmitAnswer(question.id)}
                        disabled={isSubmitted || draft.status === 'submitting'}
                        className="h-10 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                      >
                        {draft.status === 'submitting' ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                        {isSubmitted ? 'Submitted' : 'Submit Answer'}
                      </button>
                    </div>
                  </>
                )}
              </article>
            );
          })}
        </section>

        <section className="rounded-2xl border border-border bg-card/80 p-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">Finish Interview</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {mcqIsRequired
                ? 'Finish the interview answers, complete the written assessment, then submit the session.'
                : 'When you finish answering, submit the session so the hiring team can review it.'}
            </p>
          </div>
          <button
            onClick={() => void handleCompleteSession()}
            disabled={submittingComplete || !canCompleteInterview}
            className="h-11 px-5 rounded-xl bg-emerald-600 text-white text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
          >
            {submittingComplete ? <Loader2 className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />}
            Complete Interview
          </button>
        </section>

        {mcq?.mcq_enabled && (
          <section className="rounded-2xl border border-border bg-card/80 p-6 space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Written Soft-Skills Assessment</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  This step unlocks after the interview questions and is submitted once for the session.
                </p>
              </div>
              <div className="rounded-full border px-3 py-1 text-xs font-medium">
                {mcqSubmitted ? 'submitted' : `${mcqAnsweredCount}/${mcq.question_count} answered`}
              </div>
            </div>

            {!allInterviewQuestionsSubmitted ? (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                Submit all interview answers first to continue to the written assessment.
              </div>
            ) : (
              <div className="space-y-4">
                {mcq.questions.map((question, index) => (
                  <article key={question.id} className="rounded-2xl border border-border bg-background px-4 py-4 space-y-3">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">
                        {question.category.replace('_', ' ')}
                      </p>
                      <h3 className="text-base font-medium mt-2">{index + 1}. {question.question}</h3>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {question.options.map((option, optionIndex) => {
                        const selected = mcqAnswers[String(question.id)] === optionIndex;
                        return (
                          <button
                            key={optionIndex}
                            type="button"
                            disabled={mcqSubmitted}
                            onClick={() => handleMcqSelect(question.id, optionIndex)}
                            className={`w-full text-left rounded-xl border px-4 py-3 text-sm ${
                              selected ? 'border-primary bg-primary/10 text-foreground' : 'border-border bg-card text-muted-foreground'
                            } disabled:opacity-70`}
                          >
                            {option}
                          </button>
                        );
                      })}
                    </div>
                  </article>
                ))}

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs text-muted-foreground">
                    {mcqSubmitted
                      ? 'Written assessment received.'
                      : `Answer every written question to continue (${mcq.question_count - mcqAnsweredCount} remaining).`}
                  </p>
                  <button
                    type="button"
                    onClick={() => void handleSubmitMcq()}
                    disabled={mcqSubmitted || !mcqReadyToSubmit || mcqSubmitting}
                    className="h-10 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                  >
                    {mcqSubmitting ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                    {mcqSubmitted ? 'Assessment Submitted' : 'Submit Assessment'}
                  </button>
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
