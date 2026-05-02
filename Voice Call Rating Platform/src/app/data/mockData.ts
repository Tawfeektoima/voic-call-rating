export type CallStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface Agent {
  id: string;
  name: string;
  nameAr: string;
  email: string;
  initials: string;
  department: string;
  avgScore: number;
  totalCalls: number;
  passRate: number;
  color: string;
  trend: 'up' | 'down' | 'stable';
}

export interface RubricItem {
  id: string;
  category: string;
  categoryAr: string;
  maxScore: number;
  criteria: string[];
  weight: number;
}

export interface Campaign {
  id: string;
  name: string;
  description: string;
  rubricItems: RubricItem[];
  activeAgents: number;
  totalEvaluations: number;
  passThreshold: number;
  color: string;
  systemPrompt: string;
}

export interface TranscriptSegment {
  id: string;
  time: string;
  timeSeconds: number;
  speaker: 'Agent' | 'Customer';
  text: string;
  isHighlighted?: boolean;
  highlightType?: 'positive' | 'negative' | 'neutral';
}

export interface ScorecardItem {
  category: string;
  maxScore: number;
  aiScore: number;
  supervisorScore?: number;
  reasoning: string;
  criteria: { text: string; passed: boolean }[];
}

export interface Call {
  id: string;
  agentId: string;
  campaignId: string;
  date: string;
  duration: number;
  score: number | null;
  status: CallStatus;
  transcript: TranscriptSegment[];
  scorecard: ScorecardItem[];
  supervisorNote?: string;
  supervisorOverride?: number;
  supervisorReviewed?: boolean;
  filename: string;
  errorCategories: string[];
  phoneNumber: string;
}

export interface TrendDataPoint {
  date: string;
  score: number;
  calls: number;
}

export interface ErrorCategory {
  name: string;
  count: number;
  color: string;
}

export const agents: Agent[] = [
  { id: 'a1', name: 'Sarah Johnson', nameAr: 'سارة جونسون', email: 'sarah.j@company.com', initials: 'SJ', department: 'Sales', avgScore: 91.2, totalCalls: 142, passRate: 94, color: '#6366f1', trend: 'up' },
  { id: 'a2', name: 'Mohammed Al-Rashid', nameAr: 'محمد الرشيد', email: 'mo.rashid@company.com', initials: 'MA', department: 'Support', avgScore: 74.8, totalCalls: 98, passRate: 68, color: '#f59e0b', trend: 'down' },
  { id: 'a3', name: 'Emily Chen', nameAr: 'إيميلي تشن', email: 'emily.c@company.com', initials: 'EC', department: 'Retention', avgScore: 88.5, totalCalls: 115, passRate: 89, color: '#22c55e', trend: 'up' },
  { id: 'a4', name: 'Carlos Rivera', nameAr: 'كارلوس ريفيرا', email: 'carlos.r@company.com', initials: 'CR', department: 'Sales', avgScore: 82.3, totalCalls: 76, passRate: 82, color: '#3b82f6', trend: 'stable' },
  { id: 'a5', name: 'Aisha Balogun', nameAr: 'عائشة بالوجون', email: 'aisha.b@company.com', initials: 'AB', department: 'Support', avgScore: 96.1, totalCalls: 189, passRate: 97, color: '#ec4899', trend: 'up' },
  { id: 'a6', name: 'James Park', nameAr: 'جيمس بارك', email: 'james.p@company.com', initials: 'JP', department: 'Onboarding', avgScore: 67.4, totalCalls: 54, passRate: 61, color: '#f97316', trend: 'down' },
  { id: 'a7', name: 'Fatima Al-Zahra', nameAr: 'فاطمة الزهراء', email: 'fatima.z@company.com', initials: 'FZ', department: 'Retention', avgScore: 85.7, totalCalls: 103, passRate: 86, color: '#14b8a6', trend: 'up' },
  { id: 'a8', name: 'David Kim', nameAr: 'ديفيد كيم', email: 'david.k@company.com', initials: 'DK', department: 'Onboarding', avgScore: 78.9, totalCalls: 87, passRate: 77, color: '#a855f7', trend: 'stable' },
];

export const campaigns: Campaign[] = [
  {
    id: 'c1',
    name: 'Sales Excellence',
    description: 'Evaluate outbound sales calls for pitch quality, objection handling, and closing techniques.',
    color: '#6366f1',
    activeAgents: 12,
    totalEvaluations: 847,
    passThreshold: 75,
    systemPrompt: 'You are an expert sales call evaluator. Analyze the provided call transcript and evaluate the agent\'s performance based on the following criteria...',
    rubricItems: [
      { id: 'r1', category: 'Opening & Introduction', categoryAr: 'الافتتاح والتقديم', maxScore: 15, criteria: ['Proper greeting', 'Clear name & company intro', 'Permission to proceed'], weight: 15 },
      { id: 'r2', category: 'Needs Discovery', categoryAr: 'اكتشاف الاحتياجات', maxScore: 20, criteria: ['Open-ended questions', 'Active listening', 'Pain point identification', 'Budget inquiry'], weight: 20 },
      { id: 'r3', category: 'Product Presentation', categoryAr: 'عرض المنتج', maxScore: 25, criteria: ['Feature-benefit linkage', 'Relevant customization', 'Competitive differentiators'], weight: 25 },
      { id: 'r4', category: 'Objection Handling', categoryAr: 'معالجة الاعتراضات', maxScore: 20, criteria: ['Acknowledge objections', 'Provide evidence', 'Re-confirm value'], weight: 20 },
      { id: 'r5', category: 'Closing Technique', categoryAr: 'تقنية الإغلاق', maxScore: 20, criteria: ['Clear next steps', 'Commitment secured', 'Professional closing'], weight: 20 },
    ],
  },
  {
    id: 'c2',
    name: 'Customer Support QA',
    description: 'Measure support call quality including problem resolution, empathy, and technical accuracy.',
    color: '#22c55e',
    activeAgents: 18,
    totalEvaluations: 1243,
    passThreshold: 70,
    systemPrompt: 'You are an expert customer support quality analyst. Evaluate the following call transcript for resolution quality, empathy, and process adherence...',
    rubricItems: [
      { id: 'r6', category: 'Greeting & Verification', categoryAr: 'التحية والتحقق', maxScore: 10, criteria: ['Warm greeting', 'Account verification', 'Security questions'], weight: 10 },
      { id: 'r7', category: 'Problem Identification', categoryAr: 'تحديد المشكلة', maxScore: 25, criteria: ['Clear diagnosis', 'Probing questions', 'Empathy statement', 'Issue logging'], weight: 25 },
      { id: 'r8', category: 'Resolution Quality', categoryAr: 'جودة الحل', maxScore: 35, criteria: ['Accurate solution', 'Step-by-step guidance', 'Confirmation of resolution'], weight: 35 },
      { id: 'r9', category: 'Communication & Empathy', categoryAr: 'التواصل والتعاطف', maxScore: 20, criteria: ['Professional tone', 'Patience demonstrated', 'Clear language'], weight: 20 },
      { id: 'r10', category: 'Closing Protocol', categoryAr: 'بروتوكول الإغلاق', maxScore: 10, criteria: ['Recap solution', 'Additional help offer', 'Survey mention'], weight: 10 },
    ],
  },
  {
    id: 'c3',
    name: 'Customer Retention',
    description: 'Assess retention calls for cancellation prevention, value reinforcement, and negotiation skills.',
    color: '#f59e0b',
    activeAgents: 8,
    totalEvaluations: 412,
    passThreshold: 72,
    systemPrompt: 'Analyze this retention call to evaluate how effectively the agent prevented churn and reinforced customer value...',
    rubricItems: [
      { id: 'r11', category: 'Cancellation Reason Discovery', categoryAr: 'اكتشاف سبب الإلغاء', maxScore: 20, criteria: ['Root cause identified', 'Emotional acknowledgment'], weight: 20 },
      { id: 'r12', category: 'Value Reinforcement', categoryAr: 'تعزيز القيمة', maxScore: 30, criteria: ['Personalized benefits', 'Usage history referenced', 'ROI demonstrated'], weight: 30 },
      { id: 'r13', category: 'Offer & Negotiation', categoryAr: 'العرض والتفاوض', maxScore: 30, criteria: ['Appropriate incentive', 'Escalation if needed', 'Win-win framing'], weight: 30 },
      { id: 'r14', category: 'Outcome & Documentation', categoryAr: 'النتيجة والتوثيق', maxScore: 20, criteria: ['Clear commitment', 'Accurate CRM logging', 'Follow-up scheduled'], weight: 20 },
    ],
  },
  {
    id: 'c4',
    name: 'Onboarding Excellence',
    description: 'Evaluate new customer onboarding calls for clarity, completeness, and customer confidence building.',
    color: '#3b82f6',
    activeAgents: 6,
    totalEvaluations: 289,
    passThreshold: 78,
    systemPrompt: 'Evaluate this onboarding call for how effectively the agent set up the customer for success with the product...',
    rubricItems: [
      { id: 'r15', category: 'Welcome & Expectations', categoryAr: 'الترحيب والتوقعات', maxScore: 15, criteria: ['Warm welcome', 'Agenda setting', 'Timeline clarity'], weight: 15 },
      { id: 'r16', category: 'Account Setup Guidance', categoryAr: 'إرشادات إعداد الحساب', maxScore: 35, criteria: ['Step completeness', 'Terminology clarity', 'Technical accuracy'], weight: 35 },
      { id: 'r17', category: 'Feature Education', categoryAr: 'تثقيف الميزات', maxScore: 25, criteria: ['Key features covered', 'Use case examples', 'Resources shared'], weight: 25 },
      { id: 'r18', category: 'Customer Confidence', categoryAr: 'ثقة العميل', maxScore: 25, criteria: ['Questions answered', 'Comfort confirmed', 'Next steps clear'], weight: 25 },
    ],
  },
];

const sampleTranscript: TranscriptSegment[] = [
  { id: 't1', time: '0:00', timeSeconds: 0, speaker: 'Agent', text: 'Good afternoon, thank you for calling TechCorp Solutions. My name is Sarah Johnson from the Sales team. How can I help you today?', isHighlighted: true, highlightType: 'positive' },
  { id: 't2', time: '0:08', timeSeconds: 8, speaker: 'Customer', text: 'Hi Sarah, yes, I\'ve been looking at your enterprise software package and wanted to understand the pricing structure better.' },
  { id: 't3', time: '0:16', timeSeconds: 16, speaker: 'Agent', text: 'Absolutely, I\'d be happy to walk you through that. Before I do, could you tell me a bit about your company and what specific challenges you\'re trying to solve?' },
  { id: 't4', time: '0:27', timeSeconds: 27, speaker: 'Customer', text: 'Sure, we\'re a mid-size logistics firm, about 200 employees. We\'re struggling with our current reporting tools — they\'re too slow and don\'t integrate well with our ERP.' },
  { id: 't5', time: '0:45', timeSeconds: 45, speaker: 'Agent', text: 'That\'s a really common challenge in logistics. Our platform actually has native ERP integrations and real-time dashboard capabilities. What ERP system are you currently using?', isHighlighted: true, highlightType: 'positive' },
  { id: 't6', time: '0:58', timeSeconds: 58, speaker: 'Customer', text: 'We\'re on SAP. But honestly, I\'ve heard integrations are always a nightmare.' },
  { id: 't7', time: '1:04', timeSeconds: 64, speaker: 'Agent', text: 'I completely understand that concern. We actually have a certified SAP connector — it\'s a one-click setup, and we offer a 30-day integration guarantee. If it doesn\'t work seamlessly, you get a full refund.', isHighlighted: true, highlightType: 'positive' },
  { id: 't8', time: '1:22', timeSeconds: 82, speaker: 'Customer', text: 'That\'s interesting. What\'s the cost though? Your website doesn\'t show pricing.' },
  { id: 't9', time: '1:29', timeSeconds: 89, speaker: 'Agent', text: 'So pricing depends on the number of users and modules. For a 200-person company, you\'re typically looking at our Business tier, which starts at $4,500 per month.', isHighlighted: true, highlightType: 'neutral' },
  { id: 't10', time: '1:44', timeSeconds: 104, speaker: 'Customer', text: 'That seems quite high. We were expecting something closer to $2,000.' },
  { id: 't11', time: '1:51', timeSeconds: 111, speaker: 'Agent', text: 'I hear you. Let me ask — what\'s the cost of your current reporting issues in terms of staff hours or missed decisions? I want to make sure we\'re comparing apples to apples.', isHighlighted: true, highlightType: 'positive' },
  { id: 't12', time: '2:09', timeSeconds: 129, speaker: 'Customer', text: 'Honestly, probably 20 hours a week across the team. And we missed a major shipment delay last quarter because our reports were 3 days behind.' },
  { id: 't13', time: '2:22', timeSeconds: 142, speaker: 'Agent', text: 'So at an average rate of $40/hr, that\'s $800 per week, or over $3,000 monthly just in wasted labor — not counting the shipment incident. Our solution actually saves our average logistics client $6,000/month.', isHighlighted: false },
  { id: 't14', time: '2:45', timeSeconds: 165, speaker: 'Customer', text: 'OK, that\'s a compelling way to look at it. Can we schedule a demo?' },
  { id: 't15', time: '2:51', timeSeconds: 171, speaker: 'Agent', text: 'I would love to set that up. I have availability this Thursday at 2 PM or Friday morning. Which works better for you?', isHighlighted: true, highlightType: 'positive' },
  { id: 't16', time: '3:02', timeSeconds: 182, speaker: 'Customer', text: 'Thursday at 2 works.' },
  { id: 't17', time: '3:05', timeSeconds: 185, speaker: 'Agent', text: 'Perfect. I\'ll send a calendar invite with the meeting link to your email. Is there anything else I can help you with today?' },
  { id: 't18', time: '3:15', timeSeconds: 195, speaker: 'Customer', text: 'No, that\'s great. Thanks Sarah.' },
  { id: 't19', time: '3:18', timeSeconds: 198, speaker: 'Agent', text: 'Thank you for your time. I look forward to our demo on Thursday. Have a wonderful day!', isHighlighted: true, highlightType: 'positive' },
];

const sampleScorecard: ScorecardItem[] = [
  {
    category: 'Opening & Introduction',
    maxScore: 15,
    aiScore: 14,
    reasoning: 'Agent provided a clear and warm greeting, introduced herself with full name and department. Minor deduction for not explicitly asking for the customer\'s name at the start.',
    criteria: [
      { text: 'Proper greeting with time of day', passed: true },
      { text: 'Full name and company introduction', passed: true },
      { text: 'Department identification', passed: true },
      { text: 'Customer name acknowledgment', passed: false },
    ],
  },
  {
    category: 'Needs Discovery',
    maxScore: 20,
    aiScore: 18,
    reasoning: 'Excellent use of open-ended questions to understand company size, pain points, and technical environment. Agent identified the ERP integration issue and slow reporting as core pain points. Budget was addressed indirectly through ROI framing.',
    criteria: [
      { text: 'Open-ended discovery questions', passed: true },
      { text: 'Company size and context gathered', passed: true },
      { text: 'Pain points clearly identified', passed: true },
      { text: 'Budget/expectation discussion', passed: false },
    ],
  },
  {
    category: 'Product Presentation',
    maxScore: 25,
    aiScore: 22,
    reasoning: 'Strong feature-benefit linkage throughout. Agent connected SAP integration to the customer\'s specific ERP concern and referenced real-time dashboards as a solution to their reporting lag. ROI calculation was particularly effective.',
    criteria: [
      { text: 'Features linked to specific pain points', passed: true },
      { text: 'SAP integration highlighted', passed: true },
      { text: 'ROI/value quantification', passed: true },
      { text: 'Competitive differentiation', passed: false },
    ],
  },
  {
    category: 'Objection Handling',
    maxScore: 20,
    aiScore: 20,
    reasoning: 'Outstanding objection handling. Agent acknowledged the price concern, reframed it with ROI calculation, and provided specific data points. The 30-day integration guarantee effectively addressed the technical integration fear.',
    criteria: [
      { text: 'Acknowledged objections without dismissing', passed: true },
      { text: 'Provided concrete evidence/guarantee', passed: true },
      { text: 'Reframed objection positively', passed: true },
      { text: 'Confirmed customer satisfaction with response', passed: true },
    ],
  },
  {
    category: 'Closing Technique',
    maxScore: 20,
    aiScore: 17,
    reasoning: 'Good closing with an alternative choice question for scheduling. Follow-up actions were clear. Slight deduction for not confirming the customer\'s email address before sending the invite, and no summary of next steps beyond the demo.',
    criteria: [
      { text: 'Clear next steps established', passed: true },
      { text: 'Commitment secured (demo booked)', passed: true },
      { text: 'Contact confirmation', passed: false },
      { text: 'Professional and warm closing', passed: true },
    ],
  },
];

export const calls: Call[] = [
  {
    id: 'call001',
    agentId: 'a1',
    campaignId: 'c1',
    date: '2026-04-30T14:32:00',
    duration: 198,
    score: 91,
    status: 'COMPLETED',
    transcript: sampleTranscript,
    scorecard: sampleScorecard,
    supervisorReviewed: false,
    filename: 'CALL_20260430_143200_Sarah_Johnson.mp3',
    errorCategories: ['Contact confirmation'],
    phoneNumber: '+1 (415) 555-0192',
  },
  {
    id: 'call002',
    agentId: 'a2',
    campaignId: 'c2',
    date: '2026-04-30T13:15:00',
    duration: 456,
    score: 68,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: true,
    supervisorNote: 'Agent struggled with the technical escalation process and kept the customer on hold too long.',
    supervisorOverride: 65,
    filename: 'CALL_20260430_131500_Mohammed.mp3',
    errorCategories: ['Hold time excessive', 'Incomplete resolution', 'Missing empathy statement'],
    phoneNumber: '+44 20 7946 0321',
  },
  {
    id: 'call003',
    agentId: 'a3',
    campaignId: 'c3',
    date: '2026-04-30T11:44:00',
    duration: 312,
    score: 88,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260430_114400_Emily.mp3',
    errorCategories: [],
    phoneNumber: '+1 (213) 555-0845',
  },
  {
    id: 'call004',
    agentId: 'a5',
    campaignId: 'c2',
    date: '2026-04-30T10:20:00',
    duration: 287,
    score: 97,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: true,
    filename: 'CALL_20260430_102000_Aisha.mp3',
    errorCategories: [],
    phoneNumber: '+234 1 555 0214',
  },
  {
    id: 'call005',
    agentId: 'a6',
    campaignId: 'c4',
    date: '2026-04-30T09:05:00',
    duration: 423,
    score: 62,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260430_090500_James.mp3',
    errorCategories: ['Unclear instructions', 'Feature education incomplete', 'Customer confidence low'],
    phoneNumber: '+82 2 555 0177',
  },
  {
    id: 'call006',
    agentId: 'a4',
    campaignId: 'c1',
    date: '2026-04-30T08:30:00',
    duration: 534,
    score: 79,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260430_083000_Carlos.mp3',
    errorCategories: ['Weak closing', 'No competitive differentiation'],
    phoneNumber: '+52 55 5555 0344',
  },
  {
    id: 'call007',
    agentId: 'a7',
    campaignId: 'c3',
    date: '2026-04-29T16:45:00',
    duration: 267,
    score: 91,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260429_164500_Fatima.mp3',
    errorCategories: [],
    phoneNumber: '+971 4 555 0129',
  },
  {
    id: 'call008',
    agentId: 'a8',
    campaignId: 'c4',
    date: '2026-04-29T15:30:00',
    duration: 389,
    score: 75,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260429_153000_David.mp3',
    errorCategories: ['Account setup incomplete'],
    phoneNumber: '+1 (626) 555-0988',
  },
  {
    id: 'call009',
    agentId: 'a1',
    campaignId: 'c1',
    date: '2026-04-30T15:48:00',
    duration: 0,
    score: null,
    status: 'PROCESSING',
    transcript: [],
    scorecard: [],
    filename: 'CALL_20260430_154800_Sarah_Johnson.mp3',
    errorCategories: [],
    phoneNumber: '+1 (312) 555-0756',
  },
  {
    id: 'call010',
    agentId: 'a3',
    campaignId: 'c2',
    date: '2026-04-30T16:10:00',
    duration: 0,
    score: null,
    status: 'PENDING',
    transcript: [],
    scorecard: [],
    filename: 'CALL_20260430_161000_Emily.mp3',
    errorCategories: [],
    phoneNumber: '+1 (310) 555-0423',
  },
  {
    id: 'call011',
    agentId: 'a2',
    campaignId: 'c2',
    date: '2026-04-30T16:22:00',
    duration: 0,
    score: null,
    status: 'PENDING',
    transcript: [],
    scorecard: [],
    filename: 'CALL_20260430_162200_Mohammed.mp3',
    errorCategories: [],
    phoneNumber: '+44 20 7946 0567',
  },
  {
    id: 'call012',
    agentId: 'a6',
    campaignId: 'c4',
    date: '2026-04-29T11:20:00',
    duration: 201,
    score: 58,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260429_112000_James.mp3',
    errorCategories: ['Poor greeting', 'Unclear instructions', 'No follow-up scheduled'],
    phoneNumber: '+82 2 555 0214',
  },
  {
    id: 'call013',
    agentId: 'a5',
    campaignId: 'c2',
    date: '2026-04-29T14:05:00',
    duration: 334,
    score: 95,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260429_140500_Aisha.mp3',
    errorCategories: [],
    phoneNumber: '+234 1 555 0789',
  },
  {
    id: 'call014',
    agentId: 'a4',
    campaignId: 'c1',
    date: '2026-04-29T09:30:00',
    duration: 445,
    score: 84,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260429_093000_Carlos.mp3',
    errorCategories: ['Budget discovery missing'],
    phoneNumber: '+52 55 5555 0122',
  },
  {
    id: 'call015',
    agentId: 'a7',
    campaignId: 'c3',
    date: '2026-04-28T13:15:00',
    duration: 298,
    score: 87,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260428_131500_Fatima.mp3',
    errorCategories: ['Follow-up not confirmed'],
    phoneNumber: '+971 4 555 0458',
  },
  {
    id: 'call016',
    agentId: 'a2',
    campaignId: 'c2',
    date: '2026-04-28T10:40:00',
    duration: 521,
    score: null,
    status: 'FAILED',
    transcript: [],
    scorecard: [],
    filename: 'CALL_20260428_104000_Mohammed_CORRUPT.mp3',
    errorCategories: [],
    phoneNumber: '+44 20 7946 0892',
  },
  {
    id: 'call017',
    agentId: 'a8',
    campaignId: 'c4',
    date: '2026-04-28T15:55:00',
    duration: 367,
    score: 81,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260428_155500_David.mp3',
    errorCategories: ['Customer confidence not confirmed'],
    phoneNumber: '+1 (626) 555-0345',
  },
  {
    id: 'call018',
    agentId: 'a1',
    campaignId: 'c1',
    date: '2026-04-27T14:20:00',
    duration: 224,
    score: 93,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: true,
    filename: 'CALL_20260427_142000_Sarah_Johnson.mp3',
    errorCategories: [],
    phoneNumber: '+1 (628) 555-0921',
  },
  {
    id: 'call019',
    agentId: 'a5',
    campaignId: 'c2',
    date: '2026-04-27T11:10:00',
    duration: 278,
    score: 98,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: true,
    filename: 'CALL_20260427_111000_Aisha.mp3',
    errorCategories: [],
    phoneNumber: '+234 1 555 0341',
  },
  {
    id: 'call020',
    agentId: 'a3',
    campaignId: 'c3',
    date: '2026-04-27T16:00:00',
    duration: 389,
    score: 86,
    status: 'COMPLETED',
    transcript: [],
    scorecard: [],
    supervisorReviewed: false,
    filename: 'CALL_20260427_160000_Emily.mp3',
    errorCategories: ['Incentive too early'],
    phoneNumber: '+1 (213) 555-0512',
  },
];

export const weeklyTrend: TrendDataPoint[] = [
  { date: 'Apr 21', score: 81.2, calls: 28 },
  { date: 'Apr 22', score: 79.8, calls: 34 },
  { date: 'Apr 23', score: 83.4, calls: 41 },
  { date: 'Apr 24', score: 80.1, calls: 29 },
  { date: 'Apr 25', score: 82.7, calls: 38 },
  { date: 'Apr 26', score: 85.3, calls: 22 },
  { date: 'Apr 27', score: 88.1, calls: 31 },
  { date: 'Apr 28', score: 84.6, calls: 39 },
  { date: 'Apr 29', score: 86.2, calls: 44 },
  { date: 'Apr 30', score: 83.8, calls: 20 },
];

export const topErrorCategories: ErrorCategory[] = [
  { name: 'Incomplete Resolution', count: 47, color: '#ef4444' },
  { name: 'Missing Empathy', count: 38, color: '#f97316' },
  { name: 'Weak Closing', count: 31, color: '#f59e0b' },
  { name: 'No Follow-up', count: 28, color: '#eab308' },
  { name: 'Hold Time Excessive', count: 24, color: '#84cc16' },
  { name: 'Budget Not Discussed', count: 19, color: '#22c55e' },
  { name: 'Unclear Instructions', count: 17, color: '#14b8a6' },
];

export const agentTrends: Record<string, TrendDataPoint[]> = {
  a1: [
    { date: 'Apr 21', score: 88, calls: 6 }, { date: 'Apr 22', score: 91, calls: 7 },
    { date: 'Apr 23', score: 89, calls: 8 }, { date: 'Apr 24', score: 92, calls: 5 },
    { date: 'Apr 25', score: 94, calls: 9 }, { date: 'Apr 26', score: 90, calls: 4 },
    { date: 'Apr 27', score: 93, calls: 7 }, { date: 'Apr 28', score: 91, calls: 8 },
    { date: 'Apr 29', score: 95, calls: 6 }, { date: 'Apr 30', score: 91, calls: 4 },
  ],
  a2: [
    { date: 'Apr 21', score: 78, calls: 4 }, { date: 'Apr 22', score: 74, calls: 5 },
    { date: 'Apr 23', score: 71, calls: 6 }, { date: 'Apr 24', score: 69, calls: 3 },
    { date: 'Apr 25', score: 73, calls: 5 }, { date: 'Apr 26', score: 70, calls: 2 },
    { date: 'Apr 27', score: 68, calls: 4 }, { date: 'Apr 28', score: 72, calls: 5 },
    { date: 'Apr 29', score: 75, calls: 4 }, { date: 'Apr 30', score: 68, calls: 3 },
  ],
  a3: [
    { date: 'Apr 21', score: 84, calls: 5 }, { date: 'Apr 22', score: 86, calls: 6 },
    { date: 'Apr 23', score: 88, calls: 7 }, { date: 'Apr 24', score: 85, calls: 4 },
    { date: 'Apr 25', score: 89, calls: 8 }, { date: 'Apr 26', score: 87, calls: 3 },
    { date: 'Apr 27', score: 90, calls: 6 }, { date: 'Apr 28', score: 88, calls: 7 },
    { date: 'Apr 29', score: 91, calls: 5 }, { date: 'Apr 30', score: 88, calls: 3 },
  ],
  a5: [
    { date: 'Apr 21', score: 94, calls: 7 }, { date: 'Apr 22', score: 96, calls: 8 },
    { date: 'Apr 23', score: 95, calls: 9 }, { date: 'Apr 24', score: 97, calls: 6 },
    { date: 'Apr 25', score: 96, calls: 10 }, { date: 'Apr 26', score: 98, calls: 5 },
    { date: 'Apr 27', score: 97, calls: 8 }, { date: 'Apr 28', score: 96, calls: 9 },
    { date: 'Apr 29', score: 98, calls: 7 }, { date: 'Apr 30', score: 97, calls: 5 },
  ],
};

export const radarData = [
  { subject: 'Opening', a1: 93, a2: 72, a5: 97 },
  { subject: 'Discovery', a1: 90, a2: 68, a5: 96 },
  { subject: 'Presentation', a1: 88, a2: 74, a5: 95 },
  { subject: 'Objection', a1: 95, a2: 62, a5: 98 },
  { subject: 'Closing', a1: 87, a2: 75, a5: 94 },
  { subject: 'Empathy', a1: 91, a2: 70, a5: 99 },
];

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

export function getScoreColor(score: number): string {
  if (score >= 85) return '#22c55e';
  if (score >= 70) return '#f59e0b';
  return '#ef4444';
}

export function getScoreBg(score: number): string {
  if (score >= 85) return 'bg-green-500/10 text-green-400 border-green-500/20';
  if (score >= 70) return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  return 'bg-red-500/10 text-red-400 border-red-500/20';
}
