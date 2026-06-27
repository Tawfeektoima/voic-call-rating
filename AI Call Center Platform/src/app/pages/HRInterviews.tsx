import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import {
  Archive,
  Bell,
  BriefcaseBusiness,
  Copy,
  Download,
  ExternalLink,
  FileText,
  FileUp,
  FolderArchive,
  Loader2,
  Mail,
  Plus,
  RefreshCcw,
  Send,
  ShieldCheck,
  UserCheck,
  CheckCircle,
  UserRoundPlus,
  UserX,
  History,
} from 'lucide-react';
import { toast } from 'sonner';

import {
  archiveInterviewCandidate,
  bulkArchiveInterviewCandidates,
  getInterviewCandidateOnboardingReadiness,
  convertInterviewCandidate,
  createInterviewCandidate,
  createInterviewJob,
  exportInterviewCandidatesCsv,
  getApiErrorMessage,
  getCampaigns,
  getDefaultInterviewMcqBank,
  getInterviewCandidateAnswers,
  getInterviewCandidateDocuments,
  getInterviewCandidateMcqSubmission,
  getInterviewCandidateTimeline,
  getInterviewCandidates,
  getInterviewJobs,
  getTeamsDirectory,
  inviteInterviewCandidate,
  notifyInterviewCandidate,
  bulkNotifyInterviewCandidates,
  purgeArchivedInterviewCandidates,
  rejectInterviewCandidate,
  shortlistInterviewCandidate,
  acceptInterviewCandidate,
  restoreInterviewCandidate,
  updateInterviewJob,
  uploadInterviewCandidateDocument,
} from '../lib/api';
import {
  Campaign,
  InterviewAnswer,
  InterviewCandidate,
  InterviewCandidateDocument,
  InterviewCandidateTimelineEvent,
  InterviewMcqQuestionOut,
  InterviewMcqSubmissionOut,
  InterviewRetentionPurgeOut,
  TeamDirectoryOut,
  UserRole,
} from '../lib/types';
import { useApp } from '../context/AppContext';
import { PERMISSIONS, hasPermission } from '../lib/roles';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { cn } from '../components/ui/utils';

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-slate-500/10 text-slate-300 border-slate-500/20',
  open: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
  paused: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
  closed: 'bg-rose-500/10 text-rose-300 border-rose-500/20',
  applied: 'bg-sky-500/10 text-sky-300 border-sky-500/20',
  screening: 'bg-blue-500/10 text-blue-300 border-blue-500/20',
  interviewing: 'bg-violet-500/10 text-violet-300 border-violet-500/20',
  evaluated: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
  shortlisted: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20',
  rejected: 'bg-rose-500/10 text-rose-300 border-rose-500/20',
  archived: 'bg-slate-500/10 text-slate-300 border-slate-500/20',
  accepted: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
};

type CandidateMcqFilter = 'all' | 'completed' | 'pending';
type CandidateStatusFilter = 'all' | 'applied' | 'screening' | 'interviewing' | 'evaluated' | 'shortlisted' | 'accepted' | 'rejected' | 'archived';
type CandidateSortMode = 'recent' | 'mcq_high' | 'mcq_low' | 'name' | 'score_high' | 'score_low';

type ConvertDraft = {
  employee_code: string;
  role: string;
  department: string;
  otp_email: string;
  password: string;
};

const defaultConvertDraft: ConvertDraft = {
  employee_code: '',
  role: 'AGENT',
  department: '',
  otp_email: '',
  password: '',
};

const WHISPER_DEFAULT_SOFT_SKILLS_BANK: InterviewMcqQuestionOut[] = [
  {
    id: 1,
    category: 'iq',
    question: 'What is the next number in the sequence: 3, 6, 12, 24, ...?',
    options: ['36', '48', '60', '72'],
    correct: 1,
    type: 'pattern',
  },
  {
    id: 2,
    category: 'iq',
    question: 'Which shape comes next in the pattern: Triangle, Square, Pentagon, Hexagon, ...?',
    options: ['Heptagon', 'Octagon', 'Nonagon', 'Circle'],
    correct: 0,
    type: 'pattern',
  },
  {
    id: 3,
    category: 'iq',
    question: 'If all Bloops are Razzies and all Razzies are Lurgas, which of the following MUST be true?',
    options: ['All Bloops are Lurgas', 'All Lurgas are Bloops', 'Some Razzies are not Lurgas', 'None of the above'],
    correct: 0,
    type: 'logic',
  },
  {
    id: 4,
    category: 'iq',
    question: 'Which word does not belong with the others?',
    options: ['Leaf', 'Root', 'Branch', 'Dirt'],
    correct: 3,
    type: 'logic',
  },
  {
    id: 5,
    category: 'iq',
    question: 'Book is to Reading as Fork is to:',
    options: ['Drawing', 'Writing', 'Eating', 'Stirring'],
    correct: 2,
    type: 'logic',
  },
  {
    id: 6,
    category: 'computer',
    question: 'Which component is responsible for performing calculations and executing instructions in a computer?',
    options: ['RAM', 'GPU', 'CPU', 'Motherboard'],
    correct: 2,
    type: 'hardware',
  },
  {
    id: 7,
    category: 'computer',
    question: 'What keyboard shortcut is commonly used to permanently delete a file without moving it to the Recycle Bin?',
    options: ['Delete', 'Ctrl + Delete', 'Shift + Delete', 'Alt + Delete'],
    correct: 2,
    type: 'shortcut',
  },
  {
    id: 8,
    category: 'computer',
    question: 'What does SSD stand for in the context of computer storage?',
    options: ['Super Speed Drive', 'Solid State Drive', 'System Storage Device', 'Secure Static Drive'],
    correct: 1,
    type: 'hardware',
  },
  {
    id: 9,
    category: 'computer',
    question: 'Which shortcut key combination opens the Windows Task Manager directly?',
    options: ['Ctrl + Alt + Delete', 'Ctrl + Shift + Esc', 'Win + R', 'Alt + F4'],
    correct: 1,
    type: 'shortcut',
  },
  {
    id: 10,
    category: 'computer',
    question: 'Which port is most commonly used to connect a modern mouse, keyboard, or flash drive?',
    options: ['VGA', 'HDMI', 'USB', 'Ethernet'],
    correct: 2,
    type: 'hardware',
  },
  {
    id: 11,
    category: 'soft_skills',
    question: 'A team member is consistently late with their deliverables, affecting your progress. How do you handle it?',
    options: [
      'Offer to help them and discuss how to improve the workflow together.',
      'Wait silently and hope they catch up eventually.',
      'Publicly criticize their performance in the next team meeting.',
      'Report them to the manager immediately without talking to them.',
    ],
    correct: 0,
    type: 'situational',
    trait_tags: ['collaborative', 'passive', 'aggressive', 'impulsive'],
  },
  {
    id: 12,
    category: 'soft_skills',
    question: 'You realize you made a significant mistake in a report that was already sent to a client. What is your first action?',
    options: [
      'Inform your manager and the team immediately to coordinate a correction.',
      'Say nothing and hope no one notices the error.',
      'Blame the person who provided the initial data for the report.',
      'Send a second, conflicting report without explaining the first one.',
    ],
    correct: 0,
    type: 'situational',
    trait_tags: ['collaborative', 'passive', 'aggressive', 'impulsive'],
  },
  {
    id: 13,
    category: 'soft_skills',
    question: 'During a brainstorming session, a colleague proposes an idea you think will not work. How do you respond?',
    options: [
      'Acknowledge their idea and suggest exploring both the pros and cons together.',
      'Stay quiet and let others decide even if you disagree.',
      "Tell them their idea is stupid and won't work.",
      'Interrupt them immediately to propose your own better idea.',
    ],
    correct: 0,
    type: 'situational',
    trait_tags: ['collaborative', 'passive', 'aggressive', 'impulsive'],
  },
  {
    id: 14,
    category: 'soft_skills',
    question: 'You are assigned a task that you have never done before and feel overwhelmed. What do you do?',
    options: [
      'Consult with a more experienced colleague for guidance and resources.',
      'Try to do it slowly and hope it works out without asking anyone.',
      'Complain loudly to your peers about the unfair workload.',
      'Quit the task and start something else that is easier.',
    ],
    correct: 0,
    type: 'situational',
    trait_tags: ['collaborative', 'passive', 'aggressive', 'impulsive'],
  },
  {
    id: 15,
    category: 'soft_skills',
    question: 'A client is upset with you over the phone about a delay. How do you respond?',
    options: [
      'Listen calmly, empathize, and work with them to find a solution.',
      'Listen to the complaint and apologize without offering solutions.',
      'Raise your voice to defend yourself and your team.',
      'End the conversation immediately without resolving the issue.',
    ],
    correct: 0,
    type: 'situational',
    trait_tags: ['collaborative', 'passive', 'aggressive', 'impulsive'],
  },
];

export function HRInterviews() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { currentUser, userRole } = useApp();
  const canManageJobs = hasPermission(userRole, PERMISSIONS.MANAGE_INTERVIEW_JOBS, currentUser?.permissions);
  const canViewCandidates = hasPermission(userRole, PERMISSIONS.VIEW_INTERVIEW_CANDIDATES, currentUser?.permissions);
  const canManageCandidates = hasPermission(userRole, PERMISSIONS.MANAGE_INTERVIEW_CANDIDATES, currentUser?.permissions);
  const canConvertCandidates = hasPermission(userRole, PERMISSIONS.CONVERT_INTERVIEW_CANDIDATES, currentUser?.permissions);
  const canExportInterviewData = hasPermission(userRole, PERMISSIONS.EXPORT_INTERVIEW_DATA, currentUser?.permissions);
  const canExportFullPii = currentUser?.role === UserRole.ADMIN;

  const [activeTab, setActiveTab] = useState<'jobs' | 'candidates'>('jobs');
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [applicationUrl, setApplicationUrl] = useState<string | null>(null);
  const [candidateNote, setCandidateNote] = useState('');
  const [autoNotify, setAutoNotify] = useState(false);
  const [bulkNotifyTemplate, setBulkNotifyTemplate] = useState<string>('interview_invite');
  const [jobForm, setJobForm] = useState({
    title: '',
    description: '',
    department: '',
    team_id: '',
    campaign_id: '',
    status: 'open',
    base_questions: 'Introduce yourself\nWhy do you want this role?',
    mcq_enabled: false,
    mcq_questions: [] as InterviewMcqQuestionOut[],
  });
  const [candidateForm, setCandidateForm] = useState({
    full_name: '',
    contact_email: '',
    phone_number: '',
    national_id: '',
  });
  const [convertDraft, setConvertDraft] = useState<ConvertDraft>(defaultConvertDraft);
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [retentionDays, setRetentionDays] = useState('90');
  const [retentionSummary, setRetentionSummary] = useState<InterviewRetentionPurgeOut | null>(null);
  const [candidateMcqFilter, setCandidateMcqFilter] = useState<CandidateMcqFilter>('all');
  const [candidateStatusFilter, setCandidateStatusFilter] = useState<CandidateStatusFilter>('all');
  const [candidateSortMode, setCandidateSortMode] = useState<CandidateSortMode>('recent');
  const [candidateSearchQuery, setCandidateSearchQuery] = useState('');
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<number[]>([]);

  const jobsQuery = useQuery({
    queryKey: ['interview-jobs'],
    queryFn: () => getInterviewJobs(),
    enabled: canManageJobs,
  });

  const activeJobId = selectedJobId || (jobsQuery.data && jobsQuery.data.length > 0 ? jobsQuery.data[0].id : null);

  const candidatesQuery = useQuery({
    queryKey: ['interview-candidates', activeJobId],
    queryFn: () => getInterviewCandidates(activeJobId ? { job_id: activeJobId } : undefined),
    enabled: canViewCandidates,
  });
  const teamsQuery = useQuery({
    queryKey: ['interview-teams'],
    queryFn: () => getTeamsDirectory({ active_only: true }),
    enabled: canManageJobs,
  });
  const campaignsQuery = useQuery({
    queryKey: ['interview-campaigns'],
    queryFn: () => getCampaigns(),
    enabled: canManageJobs,
  });
  const defaultMcqBankQuery = useQuery({
    queryKey: ['interview-mcq-default-bank'],
    queryFn: () => getDefaultInterviewMcqBank(),
    enabled: canManageJobs,
  });
  const activeCandidateId = selectedCandidateId || (candidatesQuery.data && candidatesQuery.data.length > 0 ? candidatesQuery.data[0].id : null);

  const documentsQuery = useQuery({
    queryKey: ['interview-documents', activeCandidateId],
    queryFn: () => getInterviewCandidateDocuments(activeCandidateId as number),
    enabled: Boolean(activeCandidateId && canViewCandidates),
  });
  const answersQuery = useQuery({
    queryKey: ['interview-answers', activeCandidateId],
    queryFn: () => getInterviewCandidateAnswers(activeCandidateId as number),
    enabled: Boolean(activeCandidateId && canViewCandidates),
  });
  const mcqSubmissionQuery = useQuery({
    queryKey: ['interview-candidate-mcq', activeCandidateId],
    queryFn: () => getInterviewCandidateMcqSubmission(activeCandidateId as number),
    enabled: Boolean(activeCandidateId && canViewCandidates),
  });
  const onboardingReadinessQuery = useQuery({
    queryKey: ['interview-candidate-onboarding-readiness', activeCandidateId],
    queryFn: () => getInterviewCandidateOnboardingReadiness(activeCandidateId as number),
    enabled: Boolean(
      activeCandidateId &&
      canViewCandidates &&
      candidatesQuery.data?.find((candidate) => candidate.id === activeCandidateId)?.status === 'accepted'
    ),
  });

  const timelineQuery = useQuery({
    queryKey: ['interview-candidate-timeline', activeCandidateId],
    queryFn: () => getInterviewCandidateTimeline(activeCandidateId as number),
    enabled: Boolean(activeCandidateId && canViewCandidates),
  });

  useEffect(() => {
    if (!selectedJobId && jobsQuery.data && jobsQuery.data.length > 0) {
      setSelectedJobId(jobsQuery.data[0].id);
    }
  }, [jobsQuery.data, selectedJobId]);

  useEffect(() => {
    if (!selectedCandidateId && candidatesQuery.data && candidatesQuery.data.length > 0) {
      setSelectedCandidateId(candidatesQuery.data[0].id);
    }
  }, [candidatesQuery.data, selectedCandidateId]);

  const selectedJob = useMemo(
    () => jobsQuery.data?.find((job) => job.id === activeJobId) ?? null,
    [jobsQuery.data, activeJobId]
  );
  const selectedCandidate = useMemo(
    () => candidatesQuery.data?.find((candidate) => candidate.id === activeCandidateId) ?? null,
    [candidatesQuery.data, activeCandidateId]
  );

  const candidateJob = useMemo(
    () => jobsQuery.data?.find((job) => job.id === selectedCandidate?.job_id) ?? null,
    [jobsQuery.data, selectedCandidate?.job_id]
  );

  useEffect(() => {
    if (selectedJob) {
      setJobForm({
        title: selectedJob.title,
        description: selectedJob.description,
        department: selectedJob.department || '',
        team_id: selectedJob.team_id ? String(selectedJob.team_id) : '',
        campaign_id: selectedJob.campaign_id ? String(selectedJob.campaign_id) : '',
        status: selectedJob.status,
        base_questions: (selectedJob.base_questions || []).join('\n'),
        mcq_enabled: selectedJob.mcq_enabled,
        mcq_questions: ((selectedJob.mcq_questions || []) as InterviewMcqQuestionOut[]),
      });
    }
  }, [selectedJob]);

  useEffect(() => {
    if (selectedCandidate) {
      setConvertDraft({
        employee_code: '',
        role: 'AGENT',
        department: selectedJob?.department || '',
        otp_email: selectedCandidate.contact_email_normalized,
        password: '',
      });
    }
  }, [selectedCandidate, selectedJob?.department]);

  useEffect(() => {
    if (selectedCandidate?.status !== 'accepted' || !onboardingReadinessQuery.data) {
      return;
    }
    setConvertDraft((current) => ({
      ...current,
      employee_code: current.employee_code || onboardingReadinessQuery.data.suggested_employee_code || '',
      department: current.department || selectedJob?.department || '',
      otp_email: current.otp_email || selectedCandidate.contact_email_normalized,
    }));
  }, [onboardingReadinessQuery.data, selectedCandidate?.status, selectedCandidate?.contact_email_normalized, selectedJob?.department]);

  useEffect(() => {
    setInviteToken(null);
    setInviteUrl(null);
  }, [selectedCandidateId]);

  useEffect(() => {
    if (!selectedJobId) {
      setApplicationUrl(null);
      return;
    }
    setApplicationUrl(`${window.location.origin}/interview-portal?job_id=${selectedJobId}`);
  }, [selectedJobId]);

  const refreshAll = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['interview-jobs'] }),
      queryClient.invalidateQueries({ queryKey: ['interview-candidates'] }),
      queryClient.invalidateQueries({ queryKey: ['interview-documents'] }),
      queryClient.invalidateQueries({ queryKey: ['interview-answers'] }),
      queryClient.invalidateQueries({ queryKey: ['interview-candidate-mcq'] }),
      queryClient.invalidateQueries({ queryKey: ['interview-candidate-onboarding-readiness'] }),
      queryClient.invalidateQueries({ queryKey: ['interview-candidate-timeline'] }),
    ]);
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const createJobMutation = useMutation({
    mutationFn: async () => createInterviewJob({
      title: jobForm.title,
      description: jobForm.description,
      department: jobForm.department || undefined,
      team_id: jobForm.team_id ? Number(jobForm.team_id) : undefined,
      campaign_id: jobForm.campaign_id ? Number(jobForm.campaign_id) : undefined,
      status: jobForm.status,
      base_questions: jobForm.base_questions.split('\n').map((line) => line.trim()).filter(Boolean),
      mcq_enabled: jobForm.mcq_enabled,
      mcq_questions: jobForm.mcq_questions,
    }),
    onSuccess: async (job) => {
      toast.success('Interview job created');
      setSelectedJobId(job.id);
      setApplicationUrl(`${window.location.origin}/interview-portal?job_id=${job.id}`);
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to create interview job.')),
  });

  const updateJobMutation = useMutation({
    mutationFn: async () => {
      if (!selectedJobId) throw new Error('No interview job selected.');
      return updateInterviewJob(selectedJobId, {
        title: jobForm.title,
        description: jobForm.description,
        department: jobForm.department || undefined,
        team_id: jobForm.team_id ? Number(jobForm.team_id) : null,
        campaign_id: jobForm.campaign_id ? Number(jobForm.campaign_id) : null,
        status: jobForm.status,
        base_questions: jobForm.base_questions.split('\n').map((line) => line.trim()).filter(Boolean),
        mcq_enabled: jobForm.mcq_enabled,
        mcq_questions: jobForm.mcq_questions,
      });
    },
    onSuccess: async () => {
      toast.success('Interview job updated');
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to update interview job.')),
  });

  const createCandidateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedJobId) throw new Error('Select an interview job first.');
      return createInterviewCandidate({
        job_id: selectedJobId,
        full_name: candidateForm.full_name,
        contact_email: candidateForm.contact_email,
        phone_number: candidateForm.phone_number || undefined,
        national_id: candidateForm.national_id || undefined,
      });
    },
    onSuccess: async (candidate) => {
      toast.success('Interview candidate created');
      setCandidateForm({ full_name: '', contact_email: '', phone_number: '', national_id: '' });
      setSelectedCandidateId(candidate.id);
      setActiveTab('candidates');
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to create interview candidate.')),
  });

  const inviteMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCandidateId) throw new Error('Select a candidate first.');
      return inviteInterviewCandidate(selectedCandidateId);
    },
    onSuccess: async (data) => {
      setInviteToken(data.session_token);
      setInviteUrl(data.invite_url || null);
      toast.success('Interview session created');
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to invite candidate.')),
  });

  const rejectMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCandidateId) throw new Error('Select a candidate first.');
      return rejectInterviewCandidate(selectedCandidateId, candidateNote, autoNotify);
    },
    onSuccess: async () => {
      toast.success('Candidate rejected');
      setCandidateNote('');
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to reject candidate.')),
  });

  const archiveMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCandidateId) throw new Error('Select a candidate first.');
      return archiveInterviewCandidate(selectedCandidateId, candidateNote, autoNotify);
    },
    onSuccess: async () => {
      toast.success('Candidate archived');
      setCandidateNote('');
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to archive candidate.')),
  });

  const shortlistMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCandidateId) throw new Error('Select a candidate first.');
      return shortlistInterviewCandidate(selectedCandidateId, candidateNote, autoNotify);
    },
    onSuccess: async () => {
      toast.success('Candidate shortlisted');
      setCandidateNote('');
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to shortlist candidate.')),
  });

  const acceptMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCandidateId) throw new Error('Select a candidate first.');
      return acceptInterviewCandidate(selectedCandidateId, candidateNote, autoNotify);
    },
    onSuccess: async () => {
      toast.success('Candidate accepted');
      setCandidateNote('');
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to accept candidate.')),
  });

  const restoreMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCandidateId) throw new Error('Select a candidate first.');
      return restoreInterviewCandidate(selectedCandidateId, candidateNote);
    },
    onSuccess: async () => {
      toast.success('Candidate restored from archive');
      setCandidateNote('');
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to restore candidate.')),
  });

  const bulkArchiveMutation = useMutation({
    mutationFn: async () => bulkArchiveInterviewCandidates(selectedCandidateIds, candidateNote || 'Bulk archive from HR interview workspace'),
    onSuccess: async (summary) => {
      toast.success(`Archived ${summary.updated} candidate${summary.updated === 1 ? '' : 's'}.`);
      setSelectedCandidateIds([]);
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to bulk archive selected candidates.')),
  });

  const convertMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCandidateId) throw new Error('Select a candidate first.');
      return convertInterviewCandidate(selectedCandidateId, {
        employee_code: convertDraft.employee_code,
        role: convertDraft.role,
        department: convertDraft.department || undefined,
        otp_email: convertDraft.otp_email || undefined,
        password: convertDraft.password || undefined,
        phone_number: selectedCandidate?.phone_number || undefined,
      });
    },
    onSuccess: async (data) => {
      toast.success(`Converted to employee ${data.employee_code}`);
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to convert candidate.')),
  });

  const uploadDocumentMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCandidateId || !documentFile) throw new Error('Select a candidate and file first.');
      const formData = new FormData();
      formData.append('document_type', 'cv');
      formData.append('file', documentFile);
      return uploadInterviewCandidateDocument(selectedCandidateId, formData);
    },
    onSuccess: async () => {
      toast.success('Candidate document uploaded');
      setDocumentFile(null);
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to upload candidate document.')),
  });

  const exportCandidatesMutation = useMutation({
    mutationFn: async ({ includePii }: { includePii: boolean }) => exportInterviewCandidatesCsv({
      job_id: selectedJobId || undefined,
      include_pii: includePii,
    }),
    onSuccess: (blob, variables) => {
      const suffix = variables.includePii ? 'full' : 'redacted';
      const scope = selectedJobId ? `job-${selectedJobId}` : 'all';
      downloadBlob(blob, `interview-candidates-${scope}-${suffix}.csv`);
      toast.success(variables.includePii ? 'Full candidate export downloaded' : 'Redacted candidate export downloaded');
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to export interview candidates.')),
  });

  const notifyCandidateMutation = useMutation({
    mutationFn: async ({ template, context }: { template: string; context?: Record<string, any> }) => {
      if (!selectedCandidateId) throw new Error('Select a candidate first.');
      return notifyInterviewCandidate(selectedCandidateId, template, context);
    },
    onSuccess: async (data) => {
      if (data.success) {
        toast.success(data.message || 'Notification sent successfully');
      } else {
        toast.error(data.message || 'Notification failed to send');
      }
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to send notification.')),
  });

  const bulkNotifyMutation = useMutation({
    mutationFn: async ({ template, context }: { template: string; context?: Record<string, any> }) => {
      return bulkNotifyInterviewCandidates(selectedCandidateIds, template, context);
    },
    onSuccess: async (data) => {
      toast.success(`Bulk notifications processed: ${data.success_count} succeeded, ${data.failed_count} failed.`);
      setSelectedCandidateIds([]);
      await refreshAll();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to send bulk notifications.')),
  });

  const retentionMutation = useMutation({
    mutationFn: async ({ dryRun }: { dryRun: boolean }) => purgeArchivedInterviewCandidates({
      older_than_days: Number(retentionDays || '90'),
      dry_run: dryRun,
    }),
    onSuccess: async (summary) => {
      setRetentionSummary(summary);
      toast.success(summary.dry_run ? 'Retention preview ready' : 'Archived candidate cleanup completed');
      if (!summary.dry_run) {
        await refreshAll();
      }
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to run interview retention cleanup.')),
  });

  const teams = teamsQuery.data || [];
  const campaigns = campaignsQuery.data || [];
  const jobs = jobsQuery.data || [];
  const candidates = candidatesQuery.data || [];
  const documents = documentsQuery.data || [];
  const answers = answersQuery.data || [];
  const mcqSubmission = (mcqSubmissionQuery.data || null) as InterviewMcqSubmissionOut | null;
  const mcqTraitBreakdown = (mcqSubmission?.breakdown?.traits || {}) as Record<string, number>;
  const mcqObjectiveBreakdown = (mcqSubmission?.breakdown?.objective || {}) as Record<string, number>;

  useEffect(() => {
    const candidateIds = new Set(candidates.map((candidate) => candidate.id));
    setSelectedCandidateIds((current) => current.filter((candidateId) => candidateIds.has(candidateId)));
  }, [candidates]);

  const visibleCandidates = useMemo(() => {
    const normalizedSearchQuery = candidateSearchQuery.trim().toLowerCase();
    const filtered = candidates.filter((candidate) => {
      if (candidateStatusFilter !== 'all' && candidate.status !== candidateStatusFilter) {
        return false;
      }
      if (candidateMcqFilter === 'completed') {
        if (!candidate.mcq_completed_at) {
          return false;
        }
      }
      if (candidateMcqFilter === 'pending' && candidate.mcq_completed_at) {
        return false;
      }

      if (!normalizedSearchQuery) {
        return true;
      }

      const searchableValues = [
        candidate.full_name,
        candidate.contact_email_normalized,
        candidate.phone_number,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return searchableValues.includes(normalizedSearchQuery);
    });

    return [...filtered].sort((left, right) => {
      if (candidateSortMode === 'name') {
        return left.full_name.localeCompare(right.full_name);
      }

      if (candidateSortMode === 'mcq_high') {
        const leftScore = left.mcq_percentage ?? -1;
        const rightScore = right.mcq_percentage ?? -1;
        if (rightScore !== leftScore) {
          return rightScore - leftScore;
        }
      }

      if (candidateSortMode === 'mcq_low') {
        const leftScore = left.mcq_percentage ?? Number.MAX_SAFE_INTEGER;
        const rightScore = right.mcq_percentage ?? Number.MAX_SAFE_INTEGER;
        if (leftScore !== rightScore) {
          return leftScore - rightScore;
        }
      }

      if (candidateSortMode === 'score_high') {
        const leftScore = left.final_score ?? -1;
        const rightScore = right.final_score ?? -1;
        if (rightScore !== leftScore) {
          return rightScore - leftScore;
        }
      }

      if (candidateSortMode === 'score_low') {
        const leftScore = left.final_score ?? Number.MAX_SAFE_INTEGER;
        const rightScore = right.final_score ?? Number.MAX_SAFE_INTEGER;
        if (leftScore !== rightScore) {
          return leftScore - rightScore;
        }
      }

      const leftAppliedAt = new Date(left.applied_at).getTime();
      const rightAppliedAt = new Date(right.applied_at).getTime();
      return rightAppliedAt - leftAppliedAt;
    });
  }, [candidateMcqFilter, candidateSearchQuery, candidateSortMode, candidateStatusFilter, candidates]);
  const completedVisibleCandidates = visibleCandidates.filter((candidate) => candidate.mcq_completed_at).length;
  const selectedVisibleCandidates = visibleCandidates.filter((candidate) => selectedCandidateIds.includes(candidate.id));
  const selectedCandidateEmails = selectedVisibleCandidates
    .map((candidate) => candidate.contact_email_normalized || candidate.contact_email)
    .filter(Boolean);
  const candidateKpis = useMemo(() => {
    const completedCandidates = candidates.filter((candidate) => candidate.mcq_completed_at);
    const pendingCandidates = candidates.length - completedCandidates.length;
    const averageMcqPercentage = completedCandidates.length > 0
      ? Math.round(
        completedCandidates.reduce((total, candidate) => total + (candidate.mcq_percentage ?? 0), 0) / completedCandidates.length
      )
      : null;

    return {
      total: candidates.length,
      visible: visibleCandidates.length,
      completed: completedCandidates.length,
      pending: pendingCandidates,
      averageMcqPercentage,
    };
  }, [candidates, visibleCandidates.length]);

  const loadDefaultMcqBank = async () => {
    try {
      const bank = await getDefaultInterviewMcqBank();
      const resolvedBank = bank.length > 0 ? bank : WHISPER_DEFAULT_SOFT_SKILLS_BANK;
      setJobForm((current) => ({
        ...current,
        mcq_enabled: true,
        mcq_questions: [...resolvedBank],
      }));
      toast.success(bank.length > 0 ? 'Default soft-skills bank loaded.' : 'Loaded Whisper soft-skills bank fallback.');
    } catch (error) {
      setJobForm((current) => ({
        ...current,
        mcq_enabled: true,
        mcq_questions: [...WHISPER_DEFAULT_SOFT_SKILLS_BANK],
      }));
      toast.error(getApiErrorMessage(error, 'Could not load from server, so Whisper soft-skills bank was loaded instead.'));
    }
  };

  const addBlankMcqQuestion = () => {
    setJobForm((current) => ({
      ...current,
      mcq_enabled: true,
      mcq_questions: [
        ...current.mcq_questions,
        {
          id: Date.now(),
          category: 'soft_skills',
          question: '',
          options: ['', ''],
          type: 'manual',
        },
      ],
    }));
  };

  const updateMcqQuestion = (index: number, patch: Partial<InterviewMcqQuestionOut>) => {
    setJobForm((current) => ({
      ...current,
      mcq_questions: current.mcq_questions.map((question, questionIndex) =>
        questionIndex === index ? { ...question, ...patch } : question,
      ),
    }));
  };

  const updateMcqOption = (questionIndex: number, optionIndex: number, value: string) => {
    const question = jobForm.mcq_questions[questionIndex];
    const options = [...(question?.options || [])];
    options[optionIndex] = value;
    updateMcqQuestion(questionIndex, { options });
  };

  const addMcqOption = (questionIndex: number) => {
    const question = jobForm.mcq_questions[questionIndex];
    const options = [...(question?.options || []), ''];
    updateMcqQuestion(questionIndex, { options });
  };

  const removeMcqQuestion = (questionIndex: number) => {
    setJobForm((current) => ({
      ...current,
      mcq_questions: current.mcq_questions.filter((_, index) => index !== questionIndex),
    }));
  };

  const openSelectedCandidateMcqReview = () => {
    if (!selectedCandidateId) return;
    navigate(`/hr/interviews/candidates/${selectedCandidateId}/mcq-review`);
  };

  const openSelectedCandidateReview = () => {
    if (!selectedCandidateId) return;
    navigate(`/hr/interviews/candidates/${selectedCandidateId}/review`);
  };

  const openCandidateMcqReview = (candidateId: number) => {
    setSelectedCandidateId(candidateId);
    navigate(`/hr/interviews/candidates/${candidateId}/mcq-review`);
  };

  const openCandidateReview = (candidateId: number) => {
    setSelectedCandidateId(candidateId);
    navigate(`/hr/interviews/candidates/${candidateId}/review`);
  };

  const toggleCandidateSelection = (candidateId: number) => {
    setSelectedCandidateIds((current) =>
      current.includes(candidateId)
        ? current.filter((id) => id !== candidateId)
        : [...current, candidateId]
    );
  };

  const selectAllVisibleCandidates = () => {
    setSelectedCandidateIds(visibleCandidates.map((candidate) => candidate.id));
  };

  const clearCandidateSelection = () => {
    setSelectedCandidateIds([]);
  };

  const openBulkEmailCompose = () => {
    if (selectedCandidateEmails.length === 0) {
      toast.error('Select at least one candidate with an email address.');
      return;
    }
    const subject = selectedJob ? `Update regarding ${selectedJob.title}` : 'Interview update';
    const body = 'Hello,\n\nWe are following up regarding your interview application.\n\nBest regards,';
    const url = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(selectedCandidateEmails.join(','))}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  useEffect(() => {
    if (visibleCandidates.length === 0) {
      if (selectedCandidateId != null) {
        setSelectedCandidateId(null);
      }
      return;
    }

    if (!selectedCandidateId || !visibleCandidates.some((candidate) => candidate.id === selectedCandidateId)) {
      setSelectedCandidateId(visibleCandidates[0].id);
    }
  }, [selectedCandidateId, visibleCandidates]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Interview Pipeline</h1>
          <p className="text-sm text-slate-400 mt-1">
            Jobs, candidates, interview invites, document intake, and employee conversion inside the HR workspace.
          </p>
        </div>
        <button
          onClick={() => void refreshAll()}
          className="h-10 px-4 rounded-xl border border-border bg-card hover:bg-secondary text-sm text-foreground inline-flex items-center gap-2"
        >
          <RefreshCcw size={15} />
          Refresh
        </button>
      </div>

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'jobs' | 'candidates')} className="space-y-4">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="jobs">Interview Jobs</TabsTrigger>
          <TabsTrigger value="candidates">Candidates</TabsTrigger>
        </TabsList>

        <TabsContent value="jobs" className="space-y-4" forceMount>
          <div className="grid grid-cols-1 xl:grid-cols-[320px_minmax(0,1fr)] gap-4">
            <Card className="border-border/70 bg-card/70">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <BriefcaseBusiness size={16} className="text-primary" />
                  Job Queue
                </CardTitle>
                <CardDescription>HR-owned interview jobs available for candidate intake.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {applicationUrl && (
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-emerald-300">Application link</p>
                        <p className="text-xs text-emerald-100/80">Share this link with candidates for the selected job.</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => {
                            void navigator.clipboard.writeText(applicationUrl);
                            toast.success('Application link copied');
                          }}
                          className="h-8 px-3 rounded-lg border border-emerald-400/30 bg-emerald-500/10 text-emerald-100 text-xs inline-flex items-center gap-2"
                        >
                          <Copy size={13} />
                          Copy link
                        </button>
                        <a
                          href={applicationUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="h-8 px-3 rounded-lg border border-emerald-400/30 bg-emerald-500/10 text-emerald-100 text-xs inline-flex items-center gap-2"
                        >
                          <ExternalLink size={13} />
                          Open
                        </a>
                      </div>
                    </div>
                    <p className="font-mono text-xs text-emerald-100 break-all">{applicationUrl}</p>
                  </div>
                )}
                {jobsQuery.isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading jobs...</p>
                ) : jobs.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No interview jobs created yet.</p>
                ) : jobs.map((job) => (
                  <button
                    key={job.id}
                    onClick={() => setSelectedJobId(job.id)}
                    className={cn(
                      'w-full text-left rounded-xl border p-3 transition-colors',
                      selectedJobId === job.id ? 'border-primary bg-primary/10' : 'border-border hover:bg-secondary/50'
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-foreground">{job.title}</p>
                        <p className="text-xs text-muted-foreground mt-1">{job.department || 'No department'}</p>
                      </div>
                      <span className={cn('text-[10px] uppercase font-semibold px-2 py-1 rounded-full border', STATUS_STYLES[job.status] || STATUS_STYLES.draft)}>
                        {job.status}
                      </span>
                    </div>
                  </button>
                ))}
              </CardContent>
            </Card>

            <Card className="border-border/70 bg-card/70">
              <CardHeader>
                <CardTitle className="text-base">Job Editor</CardTitle>
                <CardDescription>Create a new interview job or update the selected one.</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="space-y-2 md:col-span-2">
                  <span className="text-xs font-medium text-muted-foreground">Job title</span>
                  <input
                    value={jobForm.title}
                    onChange={(e) => setJobForm((current) => ({ ...current, title: e.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                    placeholder="Outbound Sales Agent"
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Department</span>
                  <input
                    value={jobForm.department}
                    onChange={(e) => setJobForm((current) => ({ ...current, department: e.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                    placeholder="Sales"
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Status</span>
                  <select
                    value={jobForm.status}
                    onChange={(e) => setJobForm((current) => ({ ...current, status: e.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                  >
                    <option value="draft">Draft</option>
                    <option value="open">Open</option>
                    <option value="paused">Paused</option>
                    <option value="closed">Closed</option>
                  </select>
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Team</span>
                  <select
                    value={jobForm.team_id}
                    onChange={(e) => setJobForm((current) => ({ ...current, team_id: e.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                  >
                    <option value="">No team scope</option>
                    {teams.map((team: TeamDirectoryOut) => (
                      <option key={team.id} value={String(team.id)}>{team.name}</option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Campaign</span>
                  <select
                    value={jobForm.campaign_id}
                    onChange={(e) => setJobForm((current) => ({ ...current, campaign_id: e.target.value }))}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                  >
                    <option value="">No campaign scope</option>
                    {campaigns.map((campaign: Campaign) => (
                      <option key={campaign.id} value={String(campaign.id)}>{campaign.name}</option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2 md:col-span-2">
                  <span className="text-xs font-medium text-muted-foreground">Description</span>
                  <textarea
                    value={jobForm.description}
                    onChange={(e) => setJobForm((current) => ({ ...current, description: e.target.value }))}
                    className="w-full min-h-[110px] rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground"
                    placeholder="Describe the role, screening priorities, and evaluation context."
                  />
                </label>
                <label className="space-y-2 md:col-span-2">
                  <span className="text-xs font-medium text-muted-foreground">Base questions</span>
                  <textarea
                    value={jobForm.base_questions}
                    onChange={(e) => setJobForm((current) => ({ ...current, base_questions: e.target.value }))}
                    className="w-full min-h-[130px] rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground"
                    placeholder="One question per line"
                  />
                </label>
                <div className="md:col-span-2 rounded-2xl border border-border bg-background/60 p-4 space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">Post-interview soft-skills assessment</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Optional written MCQ step after the candidate finishes the main interview questions.
                      </p>
                    </div>
                    <label className="inline-flex items-center gap-2 text-sm text-foreground">
                      <input
                        type="checkbox"
                        checked={jobForm.mcq_enabled}
                        onChange={(e) => setJobForm((current) => ({ ...current, mcq_enabled: e.target.checked }))}
                      />
                      Enable
                    </label>
                  </div>

                  {jobForm.mcq_enabled && (
                    <div className="space-y-4">
                      <div className="flex flex-wrap gap-3">
                        <button
                          type="button"
                          onClick={() => void loadDefaultMcqBank()}
                          disabled={defaultMcqBankQuery.isLoading || defaultMcqBankQuery.isFetching}
                          className="h-10 px-4 rounded-xl border border-border bg-card text-sm text-foreground inline-flex items-center gap-2 disabled:opacity-50"
                        >
                          <ShieldCheck size={15} />
                          Load Default Soft-Skills Bank
                        </button>
                        <button
                          type="button"
                          onClick={addBlankMcqQuestion}
                          className="h-10 px-4 rounded-xl border border-border bg-card text-sm text-foreground inline-flex items-center gap-2"
                        >
                          <Plus size={15} />
                          Add MCQ Question
                        </button>
                      </div>

                      <div className="space-y-3">
                        {jobForm.mcq_questions.length === 0 ? (
                          <div className="rounded-xl border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
                            No written assessment questions configured yet.
                          </div>
                        ) : (
                          jobForm.mcq_questions.map((question, questionIndex) => (
                            <div key={`${question.id}-${questionIndex}`} className="rounded-xl border border-border bg-card/70 p-4 space-y-3">
                              <div className="flex flex-wrap items-start justify-between gap-3">
                                <p className="text-sm font-medium text-foreground">Question {questionIndex + 1}</p>
                                <button
                                  type="button"
                                  onClick={() => removeMcqQuestion(questionIndex)}
                                  className="text-xs text-rose-300 hover:text-rose-200"
                                >
                                  Remove
                                </button>
                              </div>
                              <input
                                value={question.question}
                                onChange={(e) => updateMcqQuestion(questionIndex, { question: e.target.value })}
                                className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                                placeholder="Enter the question text"
                              />
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {question.options.map((option, optionIndex) => (
                                  <input
                                    key={optionIndex}
                                    value={option}
                                    onChange={(e) => updateMcqOption(questionIndex, optionIndex, e.target.value)}
                                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                                    placeholder={`Option ${optionIndex + 1}`}
                                  />
                                ))}
                              </div>
                              <div className="flex flex-wrap items-center gap-3">
                                <select
                                  value={question.category}
                                  onChange={(e) => updateMcqQuestion(questionIndex, { category: e.target.value })}
                                  className="h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                                >
                                  <option value="soft_skills">Soft Skills</option>
                                  <option value="situational">Situational</option>
                                  <option value="iq">IQ</option>
                                  <option value="computer">Computer</option>
                                </select>
                                <select
                                  value={question.type}
                                  onChange={(e) => updateMcqQuestion(questionIndex, { type: e.target.value })}
                                  className="h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                                >
                                  <option value="situational">Situational</option>
                                  <option value="manual">Manual</option>
                                  <option value="logic">Logic</option>
                                  <option value="knowledge">Knowledge</option>
                                </select>
                                <button
                                  type="button"
                                  onClick={() => addMcqOption(questionIndex)}
                                  className="h-11 px-4 rounded-xl border border-border bg-card text-sm text-foreground"
                                >
                                  Add Option
                                </button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>
                <div className="md:col-span-2 flex flex-wrap gap-3">
                  <button
                    disabled={!canManageJobs || createJobMutation.isPending}
                    onClick={() => createJobMutation.mutate()}
                    className="h-11 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                  >
                    <Plus size={15} />
                    Create Job
                  </button>
                  <button
                    disabled={!canManageJobs || !selectedJobId || updateJobMutation.isPending}
                    onClick={() => updateJobMutation.mutate()}
                    className="h-11 px-4 rounded-xl border border-border bg-card text-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                  >
                    <RefreshCcw size={15} />
                    Update Selected Job
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-4">
            <Card className="border-border/70 bg-card/70">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Download size={16} className="text-primary" />
                  Candidate Export
                </CardTitle>
                <CardDescription>Controlled export for the current interview scope with redacted defaults.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-xl border border-border bg-background px-4 py-3 text-sm text-muted-foreground">
                  {selectedJob ? `Current scope: ${selectedJob.title}` : 'Current scope: all interview jobs'}
                </div>
                <div className="flex flex-wrap gap-3">
                  <button
                    disabled={!canExportInterviewData || exportCandidatesMutation.isPending}
                    onClick={() => exportCandidatesMutation.mutate({ includePii: false })}
                    className="h-10 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                  >
                    <Download size={15} />
                    Download Redacted CSV
                  </button>
                  {canExportFullPii && (
                    <button
                      disabled={!canExportInterviewData || exportCandidatesMutation.isPending}
                      onClick={() => exportCandidatesMutation.mutate({ includePii: true })}
                      className="h-10 px-4 rounded-xl border border-border bg-card text-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                    >
                      <ShieldCheck size={15} />
                      Download Full PII CSV
                    </button>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/70 bg-card/70">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <FolderArchive size={16} className="text-primary" />
                  Retention Controls
                </CardTitle>
                <CardDescription>Preview or purge archived interview records after the retention window.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <label className="space-y-2 block">
                  <span className="text-xs font-medium text-muted-foreground">Retention window (days)</span>
                  <input
                    value={retentionDays}
                    onChange={(e) => setRetentionDays(e.target.value)}
                    className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                    inputMode="numeric"
                  />
                </label>
                <div className="flex flex-wrap gap-3">
                  <button
                    disabled={!canManageCandidates || retentionMutation.isPending}
                    onClick={() => retentionMutation.mutate({ dryRun: true })}
                    className="h-10 px-4 rounded-xl border border-border bg-card text-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                  >
                    <RefreshCcw size={15} />
                    Preview Cleanup
                  </button>
                  <button
                    disabled={!canManageCandidates || retentionMutation.isPending}
                    onClick={() => retentionMutation.mutate({ dryRun: false })}
                    className="h-10 px-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                  >
                    <Archive size={15} />
                    Purge Archived
                  </button>
                </div>
                {retentionSummary && (
                  <div className="rounded-xl border border-border bg-background px-4 py-3 space-y-2 text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-muted-foreground">Mode</span>
                      <span className="text-foreground">{retentionSummary.dry_run ? 'Preview only' : 'Deletion executed'}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-muted-foreground">Archived matches</span>
                      <span className="text-foreground">{retentionSummary.archived_candidates_matched}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-muted-foreground">Candidates deleted</span>
                      <span className="text-foreground">{retentionSummary.candidates_deleted}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-muted-foreground">Document rows</span>
                      <span className="text-foreground">{retentionSummary.document_rows_deleted}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-muted-foreground">Document files</span>
                      <span className="text-foreground">{retentionSummary.document_files_deleted}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-muted-foreground">Answer audio files</span>
                      <span className="text-foreground">{retentionSummary.answer_audio_files_deleted}</span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="candidates" className="space-y-4" forceMount>
          <div className="grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-4">
            <Card className="border-border/70 bg-card/70">
              <CardHeader>
                <CardTitle className="text-base">Candidate Intake</CardTitle>
                <CardDescription>Add candidates into the selected interview job.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-xl border border-border bg-background px-3 py-2">
                  <p className="text-xs text-muted-foreground">Selected job</p>
                  <p className="text-sm text-foreground">{selectedJob?.title || 'Choose an interview job first'}</p>
                </div>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Full name</span>
                  <input value={candidateForm.full_name} onChange={(e) => setCandidateForm((current) => ({ ...current, full_name: e.target.value }))} className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground" />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Email</span>
                  <input value={candidateForm.contact_email} onChange={(e) => setCandidateForm((current) => ({ ...current, contact_email: e.target.value }))} className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground" />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Phone number</span>
                  <input value={candidateForm.phone_number} onChange={(e) => setCandidateForm((current) => ({ ...current, phone_number: e.target.value }))} className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground" />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">National ID</span>
                  <input value={candidateForm.national_id} onChange={(e) => setCandidateForm((current) => ({ ...current, national_id: e.target.value }))} className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground" />
                </label>
                <button
                  disabled={!canManageCandidates || !selectedJobId || createCandidateMutation.isPending}
                  onClick={() => createCandidateMutation.mutate()}
                  className="w-full h-11 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <UserRoundPlus size={15} />
                  Add Candidate
                </button>
              </CardContent>
            </Card>

            <div className="space-y-4">
              <Card className="border-border/70 bg-card/70">
                <CardHeader>
                  <CardTitle className="text-base">Candidates</CardTitle>
                  <CardDescription>Manage invitations, decisioning, and conversion for the selected job.</CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4">
                  <div className="space-y-3">
                    <div className="rounded-xl border border-border bg-background/70 p-3 space-y-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-medium text-muted-foreground">Pipeline Snapshot</p>
                        <span className="text-[11px] text-muted-foreground">
                          {candidateKpis.visible}/{candidateKpis.total} shown
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="rounded-lg border border-border bg-card px-3 py-2">
                          <p className="text-[11px] text-muted-foreground">Total</p>
                          <p className="mt-1 text-base font-semibold text-foreground">{candidateKpis.total}</p>
                        </div>
                        <div className="rounded-lg border border-border bg-card px-3 py-2">
                          <p className="text-[11px] text-muted-foreground">Completed</p>
                          <p className="mt-1 text-base font-semibold text-foreground">{candidateKpis.completed}</p>
                        </div>
                        <div className="rounded-lg border border-border bg-card px-3 py-2">
                          <p className="text-[11px] text-muted-foreground">Pending</p>
                          <p className="mt-1 text-base font-semibold text-foreground">{candidateKpis.pending}</p>
                        </div>
                        <div className="rounded-lg border border-border bg-card px-3 py-2">
                          <p className="text-[11px] text-muted-foreground">Avg. MCQ</p>
                          <p className="mt-1 text-base font-semibold text-foreground">
                            {candidateKpis.averageMcqPercentage != null ? `${candidateKpis.averageMcqPercentage}%` : '—'}
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="rounded-xl border border-border bg-background/70 p-3 space-y-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-medium text-muted-foreground">Assessment View</p>
                        <span className="text-[11px] text-muted-foreground">
                          {completedVisibleCandidates}/{visibleCandidates.length} completed
                        </span>
                      </div>
                      <div className="grid grid-cols-1 gap-3">
                        <label className="space-y-2">
                          <span className="text-[11px] font-medium text-muted-foreground">Search</span>
                          <input
                            value={candidateSearchQuery}
                            onChange={(event) => setCandidateSearchQuery(event.target.value)}
                            placeholder="Name, email, or phone"
                            className="w-full h-10 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                          />
                        </label>
                        <label className="space-y-2">
                          <span className="text-[11px] font-medium text-muted-foreground">MCQ filter</span>
                          <select
                            value={candidateMcqFilter}
                            onChange={(event) => setCandidateMcqFilter(event.target.value as CandidateMcqFilter)}
                            className="w-full h-10 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                          >
                            <option value="all">All candidates</option>
                            <option value="completed">MCQ completed</option>
                            <option value="pending">MCQ pending</option>
                          </select>
                        </label>
                        <label className="space-y-2">
                          <span className="text-[11px] font-medium text-muted-foreground">Status filter</span>
                          <select
                            value={candidateStatusFilter}
                            onChange={(event) => setCandidateStatusFilter(event.target.value as CandidateStatusFilter)}
                            className="w-full h-10 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                          >
                            <option value="all">All statuses</option>
                            <option value="applied">Applied</option>
                            <option value="screening">Screening</option>
                            <option value="interviewing">Interviewing</option>
                            <option value="evaluated">Evaluated</option>
                            <option value="shortlisted">Shortlisted</option>
                            <option value="accepted">Accepted</option>
                            <option value="rejected">Rejected</option>
                            <option value="archived">Archived</option>
                          </select>
                        </label>
                        <label className="space-y-2">
                          <span className="text-[11px] font-medium text-muted-foreground">Sort by</span>
                          <select
                            value={candidateSortMode}
                            onChange={(event) => setCandidateSortMode(event.target.value as CandidateSortMode)}
                            className="w-full h-10 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                          >
                            <option value="recent">Most recent application</option>
                            <option value="mcq_high">Highest MCQ score</option>
                            <option value="mcq_low">Lowest MCQ score</option>
                            <option value="score_high">Highest evaluation score</option>
                            <option value="score_low">Lowest evaluation score</option>
                            <option value="name">Candidate name</option>
                          </select>
                        </label>
                      </div>
                    </div>
                    <div className="rounded-xl border border-border bg-background/70 p-3 space-y-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-medium text-muted-foreground">Bulk Actions</p>
                        <span className="text-[11px] text-muted-foreground">{selectedCandidateIds.length} selected</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          type="button"
                          disabled={visibleCandidates.length === 0}
                          onClick={selectAllVisibleCandidates}
                          className="h-9 rounded-lg border border-border bg-card text-foreground text-[11px] font-medium disabled:opacity-50"
                        >
                          Select shown
                        </button>
                        <button
                          type="button"
                          disabled={selectedCandidateIds.length === 0}
                          onClick={clearCandidateSelection}
                          className="h-9 rounded-lg border border-border bg-card text-foreground text-[11px] font-medium disabled:opacity-50"
                        >
                          Clear
                        </button>
                        <button
                          type="button"
                          disabled={selectedCandidateEmails.length === 0}
                          onClick={openBulkEmailCompose}
                          className="h-9 rounded-lg border border-border bg-card text-foreground text-[11px] font-medium inline-flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                          <Mail size={13} />
                          Email
                        </button>
                         <button
                          type="button"
                          disabled={!canManageCandidates || selectedCandidateIds.length === 0 || bulkArchiveMutation.isPending}
                          onClick={() => bulkArchiveMutation.mutate()}
                          className="h-9 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 text-[11px] font-medium inline-flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                          <Archive size={13} />
                          Archive
                        </button>
                      </div>

                      {/* Bulk Notification Section */}
                      <div className="border-t border-border pt-2.5 space-y-2">
                        <select
                          id="bulk-notification-template-select"
                          disabled={selectedCandidateIds.length === 0 || bulkNotifyMutation.isPending}
                          value={bulkNotifyTemplate}
                          onChange={(e) => setBulkNotifyTemplate(e.target.value)}
                          className="w-full h-9 rounded-lg border border-border bg-card px-2.5 text-xs text-foreground disabled:opacity-50"
                        >
                          <option value="interview_invite">Send invite</option>
                          <option value="missing_mcq_reminder">Send reminder</option>
                          <option value="accepted">Send acceptance</option>
                          <option value="rejected">Send rejection</option>
                        </select>
                        <button
                          id="btn-send-bulk-notification"
                          type="button"
                          disabled={!canManageCandidates || selectedCandidateIds.length === 0 || bulkNotifyMutation.isPending}
                          onClick={() => bulkNotifyMutation.mutate({ template: bulkNotifyTemplate })}
                          className="w-full h-9 rounded-lg bg-primary text-primary-foreground text-[11px] font-medium inline-flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                          {bulkNotifyMutation.isPending ? (
                            <Loader2 className="animate-spin" size={13} />
                          ) : (
                            <Send size={13} />
                          )}
                          Send Notification
                        </button>
                      </div>
                    </div>
                    {candidatesQuery.isLoading ? (
                      <p className="text-sm text-muted-foreground">Loading candidates...</p>
                    ) : candidates.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No candidates yet for this interview job.</p>
                    ) : visibleCandidates.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No candidates match the current search and MCQ filters.</p>
                    ) : visibleCandidates.map((candidate: InterviewCandidate) => (
                      <div
                        key={candidate.id}
                        className={cn(
                          'w-full rounded-xl border p-3 transition-colors',
                          selectedCandidateId === candidate.id ? 'border-primary bg-primary/10' : 'border-border hover:bg-secondary/50'
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <input
                            type="checkbox"
                            checked={selectedCandidateIds.includes(candidate.id)}
                            onChange={() => toggleCandidateSelection(candidate.id)}
                            onClick={(event) => event.stopPropagation()}
                            className="mt-1 size-4 rounded border-border bg-background"
                            aria-label={`Select ${candidate.full_name}`}
                          />
                          <button
                            type="button"
                            onClick={() => setSelectedCandidateId(candidate.id)}
                            className="flex-1 text-left"
                          >
                            <p className="text-sm font-medium text-foreground">{candidate.full_name}</p>
                            <p className="text-xs text-muted-foreground mt-1">{candidate.contact_email_normalized}</p>
                            <div className="mt-2 flex flex-wrap items-center gap-2">
                              <span
                                className={cn(
                                  'text-[10px] uppercase font-semibold px-2 py-1 rounded-full border',
                                  candidate.mcq_completed_at
                                    ? 'border-sky-500/30 bg-sky-500/10 text-sky-200'
                                    : 'border-border bg-card text-muted-foreground'
                                )}
                              >
                                {candidate.mcq_completed_at
                                  ? `MCQ ${candidate.mcq_score ?? 0}/${candidate.mcq_total_questions ?? 0}`
                                  : 'MCQ Pending'}
                              </span>
                              {candidate.mcq_completed_at && candidate.mcq_percentage != null && (
                                <span className="text-[10px] text-muted-foreground">{candidate.mcq_percentage}%</span>
                              )}
                            </div>
                          </button>
                          <div className="flex flex-col items-end gap-2">
                            <span className={cn('text-[10px] uppercase font-semibold px-2 py-1 rounded-full border', STATUS_STYLES[candidate.status] || STATUS_STYLES.applied)}>
                              {candidate.status}
                            </span>
                            <button
                              type="button"
                              onClick={() => openCandidateReview(candidate.id)}
                              className="h-8 px-3 rounded-lg border border-border bg-card text-foreground text-[11px] font-medium inline-flex items-center gap-2"
                            >
                              <FileText size={13} />
                              Review
                            </button>
                            {candidate.mcq_completed_at && (
                              <button
                                type="button"
                                onClick={() => openCandidateMcqReview(candidate.id)}
                                className="h-8 px-3 rounded-lg border border-border bg-card text-foreground text-[11px] font-medium inline-flex items-center gap-2"
                              >
                                <ExternalLink size={13} />
                                View MCQ
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="space-y-4">
                    {selectedCandidate ? (
                      <>
                        <div className="rounded-2xl border border-border bg-background p-4 space-y-3">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <h3 className="text-lg font-semibold text-foreground">{selectedCandidate.full_name}</h3>
                              <p className="text-sm text-muted-foreground">{selectedCandidate.contact_email_normalized}</p>
                            </div>
                            <span className={cn('text-[11px] uppercase font-semibold px-2.5 py-1 rounded-full border', STATUS_STYLES[selectedCandidate.status] || STATUS_STYLES.applied)}>
                              {selectedCandidate.status}
                            </span>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                            <div className="rounded-xl bg-card border border-border px-3 py-2">
                              <p className="text-xs text-muted-foreground">Phone</p>
                              <p className="text-foreground">{selectedCandidate.phone_number || 'Not provided'}</p>
                            </div>
                            <div className="rounded-xl bg-card border border-border px-3 py-2">
                              <p className="text-xs text-muted-foreground">National ID</p>
                              <p className="text-foreground">{selectedCandidate.national_id_last4 ? `•••• ${selectedCandidate.national_id_last4}` : 'Not provided'}</p>
                            </div>
                            <div className="rounded-xl bg-card border border-border px-3 py-2">
                              <p className="text-xs text-muted-foreground">Converted employee</p>
                              <p className="text-foreground">{selectedCandidate.converted_employee_id || 'Not converted'}</p>
                            </div>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                            <div className="rounded-xl bg-card border border-border px-3 py-2">
                              <p className="text-xs text-muted-foreground">Final score</p>
                              <p className="text-foreground">{selectedCandidate.final_score != null ? selectedCandidate.final_score.toFixed(1) : 'Pending evaluation'}</p>
                            </div>
                            <div className="rounded-xl bg-card border border-border px-3 py-2">
                              <p className="text-xs text-muted-foreground">Submitted answers</p>
                              <p className="text-foreground">{answers.length}</p>
                            </div>
                            <div className="rounded-xl bg-card border border-border px-3 py-2">
                              <p className="text-xs text-muted-foreground">Evaluation state</p>
                              <p className="text-foreground">
                                {answers.some((answer) => answer.status === 'failed')
                                  ? 'Needs review'
                                  : answers.some((answer) => answer.status === 'pending' || answer.status === 'processing')
                                    ? 'Running'
                                    : answers.length > 0
                                      ? 'Ready'
                                      : 'Not started'}
                              </p>
                            </div>
                          </div>

                          <div className="flex flex-wrap gap-3">
                            <button
                              onClick={openSelectedCandidateReview}
                              className="h-10 px-4 rounded-xl border border-border bg-card text-foreground text-sm font-medium inline-flex items-center gap-2"
                            >
                              <FileText size={15} />
                              Open Review
                            </button>
                            {['applied', 'screening', 'interviewing'].includes(selectedCandidate.status) && (
                              <button
                                disabled={!canManageCandidates || inviteMutation.isPending}
                                onClick={() => inviteMutation.mutate()}
                                className="h-10 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                              >
                                <Send size={15} />
                                Create Invite
                              </button>
                            )}
                            {['evaluated', 'rejected'].includes(selectedCandidate.status) && (
                              <button
                                disabled={!canManageCandidates || shortlistMutation.isPending}
                                onClick={() => shortlistMutation.mutate()}
                                className="h-10 px-4 rounded-xl border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                              >
                                <CheckCircle size={15} />
                                Shortlist
                              </button>
                            )}
                            {['evaluated', 'shortlisted', 'rejected'].includes(selectedCandidate.status) && (
                              <button
                                disabled={!canManageCandidates || acceptMutation.isPending}
                                onClick={() => acceptMutation.mutate()}
                                className="h-10 px-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                              >
                                <UserCheck size={15} />
                                Accept
                              </button>
                            )}
                            {!['rejected', 'archived'].includes(selectedCandidate.status) && (
                              <button
                                disabled={!canManageCandidates || rejectMutation.isPending}
                                onClick={() => rejectMutation.mutate()}
                                className="h-10 px-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                              >
                                <UserX size={15} />
                                Reject
                              </button>
                            )}
                            {selectedCandidate.status !== 'archived' && (
                              <button
                                disabled={!canManageCandidates || archiveMutation.isPending}
                                onClick={() => archiveMutation.mutate()}
                                className="h-10 px-4 rounded-xl border border-border bg-card text-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                              >
                                <Archive size={15} />
                                Archive
                              </button>
                            )}
                            {selectedCandidate.status === 'archived' && (
                              <button
                                disabled={!canManageCandidates || restoreMutation.isPending}
                                onClick={() => restoreMutation.mutate()}
                                className="h-10 px-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                              >
                                <RefreshCcw size={15} />
                                Restore
                              </button>
                            )}
                          </div>

                          {/* Candidate Notifications Section */}
                          <div className="border-t border-border pt-3 space-y-2">
                            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Notifications</p>
                            <div className="flex flex-wrap gap-3">
                              {/* Send Invite */}
                              {['applied', 'interviewing'].includes(selectedCandidate.status) && (
                                <button
                                  id="btn-send-invite-email"
                                  disabled={!canManageCandidates || notifyCandidateMutation.isPending}
                                  onClick={() => notifyCandidateMutation.mutate({ template: 'interview_invite' })}
                                  className="h-9 px-3 rounded-xl bg-primary/10 border border-primary/20 hover:bg-primary/20 text-primary text-xs font-medium inline-flex items-center gap-1.5 disabled:opacity-50"
                                >
                                  {notifyCandidateMutation.isPending ? (
                                    <Loader2 className="animate-spin" size={14} />
                                  ) : (
                                    <Mail size={14} />
                                  )}
                                  Send Invite
                                </button>
                              )}

                              {/* Send Reminder */}
                              {candidateJob?.mcq_enabled && !selectedCandidate.mcq_completed_at && (
                                <button
                                  id="btn-send-reminder-email"
                                  disabled={!canManageCandidates || notifyCandidateMutation.isPending}
                                  onClick={() => notifyCandidateMutation.mutate({ template: 'missing_mcq_reminder' })}
                                  className="h-9 px-3 rounded-xl bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 text-amber-300 text-xs font-medium inline-flex items-center gap-1.5 disabled:opacity-50"
                                >
                                  {notifyCandidateMutation.isPending ? (
                                    <Loader2 className="animate-spin" size={14} />
                                  ) : (
                                    <Bell size={14} />
                                  )}
                                  Send Reminder
                                </button>
                              )}

                              {/* Send Acceptance */}
                              {selectedCandidate.status === 'evaluated' && (
                                <button
                                  id="btn-send-acceptance-email"
                                  disabled={!canManageCandidates || notifyCandidateMutation.isPending}
                                  onClick={() => notifyCandidateMutation.mutate({ template: 'accepted' })}
                                  className="h-9 px-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 text-emerald-300 text-xs font-medium inline-flex items-center gap-1.5 disabled:opacity-50"
                                >
                                  {notifyCandidateMutation.isPending ? (
                                    <Loader2 className="animate-spin" size={14} />
                                  ) : (
                                    <Mail size={14} />
                                  )}
                                  Send Acceptance
                                </button>
                              )}

                              {/* Send Rejection */}
                              {selectedCandidate.status === 'rejected' && (
                                <button
                                  id="btn-send-rejection-email"
                                  disabled={!canManageCandidates || notifyCandidateMutation.isPending}
                                  onClick={() => notifyCandidateMutation.mutate({ template: 'rejected' })}
                                  className="h-9 px-3 rounded-xl bg-rose-500/10 border border-rose-500/20 hover:bg-rose-500/20 text-rose-300 text-xs font-medium inline-flex items-center gap-1.5 disabled:opacity-50"
                                >
                                  {notifyCandidateMutation.isPending ? (
                                    <Loader2 className="animate-spin" size={14} />
                                  ) : (
                                    <Mail size={14} />
                                  )}
                                  Send Rejection
                                </button>
                              )}
                            </div>
                          </div>

                          <label className="block space-y-2">
                            <span className="text-xs font-medium text-muted-foreground">Decision note</span>
                            <textarea
                              value={candidateNote}
                              onChange={(e) => setCandidateNote(e.target.value)}
                              className="w-full min-h-[90px] rounded-xl border border-border bg-card px-3 py-3 text-sm text-foreground"
                              placeholder="Internal note for candidate status transition decisions"
                            />
                          </label>

                          <div className="flex items-center gap-2 py-1">
                            <input
                              type="checkbox"
                              id="auto-notify-checkbox"
                              checked={autoNotify}
                              onChange={(e) => setAutoNotify(e.target.checked)}
                              className="rounded border-border bg-card text-primary focus:ring-primary h-4 w-4"
                            />
                            <label htmlFor="auto-notify-checkbox" className="text-xs font-medium text-muted-foreground cursor-pointer select-none">
                              Auto-notify Candidate via Email on Status Change
                            </label>
                          </div>

                          {inviteToken && (
                            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 space-y-3">
                              {inviteUrl && (
                                <div className="space-y-2">
                                  <div className="flex flex-wrap items-center justify-between gap-2">
                                    <p className="text-xs uppercase tracking-wide text-emerald-300">Public invite link</p>
                                    <div className="flex flex-wrap gap-2">
                                      <button
                                        onClick={() => {
                                          void navigator.clipboard.writeText(inviteUrl);
                                          toast.success('Invite link copied');
                                        }}
                                        className="h-8 px-3 rounded-lg border border-emerald-400/30 bg-emerald-500/10 text-emerald-100 text-xs inline-flex items-center gap-2"
                                      >
                                        <Copy size={13} />
                                        Copy link
                                      </button>
                                      <a
                                        href={inviteUrl}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="h-8 px-3 rounded-lg border border-emerald-400/30 bg-emerald-500/10 text-emerald-100 text-xs inline-flex items-center gap-2"
                                      >
                                        <ExternalLink size={13} />
                                        Open
                                      </a>
                                    </div>
                                  </div>
                                  <p className="font-mono text-xs text-emerald-100 break-all">{inviteUrl}</p>
                                </div>
                              )}
                              <div>
                                <p className="text-xs uppercase tracking-wide text-emerald-300">Session token</p>
                                <p className="mt-1 font-mono text-xs text-emerald-100 break-all">{inviteToken}</p>
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px] gap-4">
                          <Card className="border-border/70 bg-card/70 xl:col-span-2">
                            <CardHeader>
                              <CardTitle className="text-base">Interview Evaluation</CardTitle>
                              <CardDescription>Answer-by-answer scoring and AI summaries for the selected candidate.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                              {answersQuery.isLoading ? (
                                <p className="text-sm text-muted-foreground">Loading evaluation results...</p>
                              ) : answers.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No submitted answers yet.</p>
                              ) : answers.map((answer: InterviewAnswer, index) => (
                                <div key={answer.id} className="rounded-xl border border-border bg-background px-4 py-4 space-y-3">
                                  <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div>
                                      <p className="text-sm font-medium text-foreground">Answer {index + 1}</p>
                                      <p className="text-xs text-muted-foreground mt-1">Question #{answer.question_id}</p>
                                    </div>
                                    <div className="text-right">
                                      <p className="text-sm font-semibold text-foreground">
                                        {answer.overall_score != null ? `${answer.overall_score.toFixed(1)} / 100` : 'Pending'}
                                      </p>
                                      <p className="text-xs uppercase text-muted-foreground mt-1">{answer.status}</p>
                                    </div>
                                  </div>
                                  {answer.ai_summary && (
                                    <p className="text-sm text-foreground leading-6">{answer.ai_summary}</p>
                                  )}
                                  {answer.transcribed_text && (
                                    <div className="rounded-lg border border-border bg-card px-3 py-3">
                                      <p className="text-xs text-muted-foreground mb-2">Transcript</p>
                                      <p className="text-sm text-foreground leading-6 whitespace-pre-wrap">{answer.transcribed_text}</p>
                                    </div>
                                  )}
                                  {answer.error_message && (
                                    <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-3">
                                      <p className="text-xs text-rose-200">{answer.error_message}</p>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </CardContent>
                          </Card>

                          <Card className="border-border/70 bg-card/70">
                          <CardHeader>
                            <CardTitle className="text-base">Soft-Skills Assessment</CardTitle>
                            <CardDescription>Written post-interview MCQ results for the selected candidate.</CardDescription>
                          </CardHeader>
                          <CardContent className="space-y-3">
                              {mcqSubmissionQuery.isLoading ? (
                                <p className="text-sm text-muted-foreground">Loading written assessment...</p>
                              ) : !mcqSubmission ? (
                                <p className="text-sm text-muted-foreground">No written assessment submitted yet.</p>
                              ) : (
                                <>
                                  <div className="rounded-xl border border-border bg-background px-4 py-3">
                                    <p className="text-xs text-muted-foreground">Score</p>
                                    <p className="mt-1 text-lg font-semibold text-foreground">
                                      {mcqSubmission.score} / {mcqSubmission.total_questions} ({mcqSubmission.percentage}%)
                                    </p>
                                  </div>
                                  <div className="rounded-xl border border-border bg-background px-4 py-3 space-y-2">
                                    <p className="text-xs text-muted-foreground">Trait breakdown</p>
                                    {Object.keys(mcqTraitBreakdown).length === 0 ? (
                                      <p className="text-sm text-muted-foreground">No trait signals recorded.</p>
                                    ) : (
                                      Object.entries(mcqTraitBreakdown).map(([trait, value]) => (
                                        <div key={trait} className="flex items-center justify-between gap-3 text-sm">
                                          <span className="capitalize text-foreground">{trait.replace('_', ' ')}</span>
                                          <span className="text-muted-foreground">{value}</span>
                                        </div>
                                      ))
                                    )}
                                  </div>
                                  {Object.keys(mcqObjectiveBreakdown).length > 0 && (
                                    <div className="rounded-xl border border-border bg-background px-4 py-3 space-y-2">
                                      <p className="text-xs text-muted-foreground">Objective sections</p>
                                      {Object.entries(mcqObjectiveBreakdown).map(([category, value]) => (
                                        <div key={category} className="flex items-center justify-between gap-3 text-sm">
                                          <span className="capitalize text-foreground">{category.replace('_', ' ')}</span>
                                          <span className="text-muted-foreground">{value}</span>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                  <button
                                    onClick={openSelectedCandidateMcqReview}
                                    className="w-full h-10 rounded-xl border border-border bg-card text-foreground text-sm font-medium inline-flex items-center justify-center gap-2"
                                  >
                                    <ExternalLink size={15} />
                                    Open Full MCQ Review
                                  </button>
                                </>
                              )}
                            </CardContent>
                          </Card>

                          <Card className="border-border/70 bg-card/70">
                            <CardHeader>
                              <CardTitle className="text-base flex items-center gap-2">
                                <FileUp size={16} className="text-primary" />
                                Documents
                              </CardTitle>
                              <CardDescription>Attach CVs or supporting files to the candidate record.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              <div className="flex flex-wrap items-center gap-3">
                                <input
                                  type="file"
                                  onChange={(event) => setDocumentFile(event.target.files?.[0] || null)}
                                  className="max-w-sm text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-secondary file:px-3 file:py-2 file:text-sm file:text-foreground"
                                />
                                <button
                                  disabled={!canManageCandidates || !documentFile || uploadDocumentMutation.isPending}
                                  onClick={() => uploadDocumentMutation.mutate()}
                                  className="h-10 px-4 rounded-xl border border-border bg-card text-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-50"
                                >
                                  <FileUp size={15} />
                                  Upload CV
                                </button>
                              </div>
                              <div className="space-y-2">
                                {documentsQuery.isLoading ? (
                                  <p className="text-sm text-muted-foreground">Loading documents...</p>
                                ) : documents.length === 0 ? (
                                  <p className="text-sm text-muted-foreground">No documents uploaded yet.</p>
                                ) : documents.map((document: InterviewCandidateDocument) => (
                                  <div key={document.id} className="rounded-xl border border-border bg-background px-4 py-3">
                                    <div className="flex items-center justify-between gap-3">
                                      <div>
                                        <p className="text-sm text-foreground">{document.original_filename}</p>
                                        <p className="text-xs text-muted-foreground mt-1">
                                          {document.document_type.toUpperCase()} · {document.extraction_status}
                                        </p>
                                      </div>
                                      <span className="text-xs text-muted-foreground">
                                        {new Date(document.uploaded_at).toLocaleString()}
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </CardContent>
                          </Card>

                          <Card className="border-border/70 bg-card/70">
                            <CardHeader>
                              <CardTitle className="text-base flex items-center gap-2">
                                <ShieldCheck size={16} className="text-primary" />
                                Convert To Employee
                              </CardTitle>
                              <CardDescription>Create the employee record using the existing company identity rules.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                              {selectedCandidate.status === 'accepted' && (
                                <div className="rounded-xl border border-border bg-background px-3 py-3 space-y-3">
                                  <div className="flex flex-wrap items-start justify-between gap-2">
                                    <div>
                                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Onboarding Readiness</p>
                                      <p className="text-sm font-medium text-foreground mt-1">
                                        {onboardingReadinessQuery.isLoading
                                          ? 'Checking readiness...'
                                          : onboardingReadinessQuery.data?.is_ready
                                            ? 'Ready to convert'
                                            : 'Needs attention before convert'}
                                      </p>
                                    </div>
                                    {onboardingReadinessQuery.data?.suggested_company_email && (
                                      <span className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 text-emerald-300">
                                        {onboardingReadinessQuery.data.suggested_company_email}
                                      </span>
                                    )}
                                  </div>
                                  {onboardingReadinessQuery.isError ? (
                                    <p className="text-xs text-rose-300">Unable to load onboarding readiness.</p>
                                  ) : onboardingReadinessQuery.data ? (
                                    <div className="space-y-2">
                                      {onboardingReadinessQuery.data.blocking_reasons.length > 0 ? (
                                        <ul className="space-y-1">
                                          {onboardingReadinessQuery.data.blocking_reasons.map((reason, index) => {
                                            const category = onboardingReadinessQuery.data.blocking_categories?.[index];
                                            const categoryLabel = category
                                              ? category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
                                              : null;
                                            return (
                                              <li key={reason} className="text-xs text-muted-foreground flex items-start gap-2">
                                                <span className="mt-1 size-1.5 rounded-full bg-amber-400 shrink-0" />
                                                <span>
                                                  {reason}
                                                  {categoryLabel && (
                                                    <span className="ml-1 text-[10px] uppercase tracking-wide text-amber-200/80">({categoryLabel})</span>
                                                  )}
                                                </span>
                                              </li>
                                            );
                                          })}
                                        </ul>
                                      ) : (
                                        <p className="text-xs text-emerald-300">No blockers found.</p>
                                      )}
                                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                                        <div className="rounded-lg border border-border bg-card px-3 py-2">
                                          <p className="text-muted-foreground">Suggested employee code</p>
                                          <p className="mt-1 text-foreground font-medium">{onboardingReadinessQuery.data.suggested_employee_code || 'N/A'}</p>
                                        </div>
                                        <div className="rounded-lg border border-border bg-card px-3 py-2">
                                          <p className="text-muted-foreground">Suggested company email</p>
                                          <p className="mt-1 text-foreground font-medium break-all">{onboardingReadinessQuery.data.suggested_company_email || 'N/A'}</p>
                                        </div>
                                      </div>
                                      {onboardingReadinessQuery.data.existing_employee_match && (
                                        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                                          Existing employee match: #{onboardingReadinessQuery.data.existing_employee_match.employee_id} ·{' '}
                                          {onboardingReadinessQuery.data.existing_employee_match.employee_code}
                                        </div>
                                      )}
                                    </div>
                                  ) : null}
                                </div>
                              )}
                              {selectedCandidate.converted_employee_id ? (
                                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 space-y-2">
                                  <p className="text-xs uppercase tracking-wide text-emerald-300">Already Converted</p>
                                  <p className="text-sm text-foreground font-medium">
                                    Employee #{selectedCandidate.converted_employee_id}
                                  </p>
                                  <p className="text-xs text-muted-foreground">
                                    This candidate has already been converted. Identity fields are locked.
                                  </p>
                                </div>
                              ) : null}
                              <label className="space-y-2 block">
                                <span className="text-xs font-medium text-muted-foreground">Employee code</span>
                                <input
                                  value={convertDraft.employee_code}
                                  onChange={(e) => setConvertDraft((current) => ({ ...current, employee_code: e.target.value }))}
                                  className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground disabled:opacity-60"
                                  placeholder="950"
                                  disabled={Boolean(selectedCandidate.converted_employee_id)}
                                />
                              </label>
                              <label className="space-y-2 block">
                                <span className="text-xs font-medium text-muted-foreground">Role</span>
                                <select
                                  value={convertDraft.role}
                                  onChange={(e) => setConvertDraft((current) => ({ ...current, role: e.target.value }))}
                                  className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground disabled:opacity-60"
                                  disabled={Boolean(selectedCandidate.converted_employee_id)}
                                >
                                  <option value="AGENT">Agent</option>
                                  <option value="QA">QA</option>
                                  <option value="HR_MANAGER">HR Manager</option>
                                  <option value="TEAM_LEADER">Team Leader</option>
                                  <option value="TEAM_MANAGER">Team Manager</option>
                                  <option value="OPS_MANAGER">Ops Manager</option>
                                </select>
                              </label>
                              <label className="space-y-2 block">
                                <span className="text-xs font-medium text-muted-foreground">Department</span>
                                <input
                                  value={convertDraft.department}
                                  onChange={(e) => setConvertDraft((current) => ({ ...current, department: e.target.value }))}
                                  className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground disabled:opacity-60"
                                  disabled={Boolean(selectedCandidate.converted_employee_id)}
                                />
                              </label>
                              <label className="space-y-2 block">
                                <span className="text-xs font-medium text-muted-foreground">OTP email</span>
                                <input
                                  value={convertDraft.otp_email}
                                  onChange={(e) => setConvertDraft((current) => ({ ...current, otp_email: e.target.value }))}
                                  className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground disabled:opacity-60"
                                  disabled={Boolean(selectedCandidate.converted_employee_id)}
                                />
                              </label>
                              <label className="space-y-2 block">
                                <span className="text-xs font-medium text-muted-foreground">Initial password optional</span>
                                <input
                                  type="password"
                                  value={convertDraft.password}
                                  onChange={(e) => setConvertDraft((current) => ({ ...current, password: e.target.value }))}
                                  className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"
                                  placeholder="Leave blank to use the backend default"
                                />
                                <p className="text-[11px] text-muted-foreground">
                                  Do not enter shared credentials here. Leave blank unless HR assigns a one-time credential.
                                </p>
                              </label>
                              <div className="rounded-xl border border-border bg-background px-3 py-2">
                                <p className="text-xs text-muted-foreground flex items-center gap-2">
                                  <Mail size={13} />
                                  Generated company email
                                </p>
                                <p className="text-sm text-foreground mt-1">
                                  {convertDraft.employee_code ? `emp-${convertDraft.employee_code.trim().toLowerCase()}@eiacs.com` : 'Enter employee code'}
                                </p>
                              </div>
                              <button
                                disabled={
                                  !canConvertCandidates ||
                                  selectedCandidate.status !== 'accepted' ||
                                  onboardingReadinessQuery.isLoading ||
                                  !onboardingReadinessQuery.data?.is_ready ||
                                  !convertDraft.employee_code ||
                                  convertMutation.isPending
                                }
                                onClick={() => convertMutation.mutate()}
                                className="w-full h-11 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center justify-center gap-2 disabled:opacity-50"
                              >
                                <ShieldCheck size={15} />
                                Convert Candidate
                              </button>
                            </CardContent>
                          </Card>

                          <Card className="border-border/70 bg-card/70">
                            <CardHeader>
                              <CardTitle className="text-base flex items-center gap-2">
                                <History size={16} className="text-primary" />
                                Candidate Timeline
                              </CardTitle>
                              <CardDescription>Workflow and status transition logs for this candidate.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              {timelineQuery.isLoading ? (
                                <p className="text-sm text-muted-foreground">Loading timeline...</p>
                              ) : timelineQuery.isError ? (
                                <p className="text-sm text-rose-300">Error loading timeline</p>
                              ) : !timelineQuery.data || timelineQuery.data.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No timeline events logged yet.</p>
                              ) : (
                                <div className="relative border-l border-border ml-2 pl-4 space-y-4">
                                  {timelineQuery.data.map((event: InterviewCandidateTimelineEvent) => (
                                    <div key={event.id} className="relative space-y-1">
                                      <div className="absolute -left-[21px] mt-1.5 size-2 rounded-full border border-primary bg-background" />
                                      <div className="flex flex-wrap items-center justify-between gap-x-2">
                                        <p className="text-xs font-semibold text-foreground capitalize">
                                          {event.event_type.replace(/_/g, ' ').toLowerCase()}
                                        </p>
                                        <span className="text-[10px] text-muted-foreground">
                                          {new Date(event.created_at).toLocaleString()}
                                        </span>
                                      </div>
                                      {event.from_status && event.to_status && (
                                        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                                          <span className="font-medium">{event.from_status}</span>
                                          <span>→</span>
                                          <span className="font-medium text-foreground">{event.to_status}</span>
                                        </div>
                                      )}
                                      {event.note && (
                                        <p className="text-[11px] text-muted-foreground italic bg-secondary/30 px-2 py-1 rounded">
                                          {event.note}
                                        </p>
                                      )}
                                      {event.actor_name && (
                                        <p className="text-[10px] text-muted-foreground flex items-center gap-1">
                                          <span>By:</span>
                                          <span className="font-medium">{event.actor_name}</span>
                                        </p>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </CardContent>
                          </Card>
                        </div>
                      </>
                    ) : (
                      <div className="rounded-2xl border border-dashed border-border p-8 text-center text-muted-foreground">
                        Select a candidate to manage invitations, documents, and conversion.
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
