export type CampaignType = 'sales' | 'customer_service' | 'technical' | 'collections';
export type UserRole = 'admin' | 'manager' | 'qa' | 'agent';
export type LeadStatus = 'hot' | 'warm' | 'cold';
export type EmotionState = 'calm' | 'stress' | 'agitation';

export interface Campaign {
  id: string;
  name: string;
  type: CampaignType;
  description: string;
  totalCalls: number;
  avgScore: number;
  status: 'active' | 'paused' | 'completed';
  startDate: string;
  endDate?: string;
  kpis: string[];
  groqPromptFocus: string;
  color: string;
  accentClass: string;
  agentCount: number;
}

export interface TranscriptSegment {
  id: string;
  speaker: 'agent' | 'customer';
  text: string;
  redactedText: string;
  startTime: number;
  endTime: number;
  emotion: EmotionState;
  hasPII: boolean;
}

export interface EmotionPoint {
  time: number;
  emotion: EmotionState;
  intensity: number;
}

export interface Call {
  id: string;
  campaignId: string;
  agentId: string;
  date: string;
  duration: number;
  agentTalkTime: number;
  customerTalkTime: number;
  qaScore: number;
  transcript: TranscriptSegment[];
  tags: string[];
  leadStatus: LeadStatus;
  outcome: string;
  isGoldenMoment: boolean;
  emotionTimeline: EmotionPoint[];
  callSummary: string;
}

export interface SkillProfile {
  empathy: number;
  resolution: number;
  communication: number;
  productKnowledge: number;
  compliance: number;
  callControl: number;
}

export interface Agent {
  id: string;
  name: string;
  email: string;
  campaignId: string;
  callsHandled: number;
  avgScore: number;
  skills: SkillProfile;
  emotionConsistency: { week: string; score: number }[];
  recentCalls: string[];
  avatar: string;
  tier: 'bronze' | 'silver' | 'gold' | 'platinum';
}

export interface Alert {
  id: string;
  type: 'shouting' | 'processing_failure' | 'low_score' | 'system' | 'pii_leak';
  message: string;
  timestamp: string;
  severity: 'critical' | 'warning' | 'info';
  callId?: string;
  agentId?: string;
  resolved: boolean;
}

export interface GoldenMoment {
  id: string;
  callId: string;
  agentId: string;
  agentName: string;
  campaignType: CampaignType;
  title: string;
  description: string;
  duration: number;
  score: number;
  tags: string[];
  transcript: string;
  date: string;
}

export interface InferenceHistoryPoint {
  time: string;
  value: number;
}

export interface SystemMetrics {
  inferenceTime: number;
  gpuLoad: number;
  cpuLoad: number;
  callsProcessing: number;
  queueDepth: number;
  uptime: number;
  inferenceHistory: InferenceHistoryPoint[];
  gpuHistory: InferenceHistoryPoint[];
}

export interface Lead {
  id: string;
  callId: string;
  agentId: string;
  agentName: string;
  customerName: string;
  status: LeadStatus;
  score: number;
  lastContact: string;
  notes: string;
  campaignId: string;
  phone: string;
  value: number;
}

// ─────────────────────────────────────────────────────
// CAMPAIGNS
// ─────────────────────────────────────────────────────
export const campaigns: Campaign[] = [
  {
    id: 'c1',
    name: 'Q4 Enterprise Sales Blitz',
    type: 'sales',
    description: 'High-value enterprise outreach targeting Fortune 500 procurement leads.',
    totalCalls: 1284,
    avgScore: 78.4,
    status: 'active',
    startDate: '2026-10-01',
    kpis: ['Objection Rate', 'Conversion Rate', 'Follow-up Booked', 'Value Proposed'],
    groqPromptFocus: 'Extract objections, buying signals, competitor mentions, and next-step commitments.',
    color: '#6366f1',
    accentClass: 'indigo',
    agentCount: 24,
  },
  {
    id: 'c2',
    name: 'Premium Support Queue',
    type: 'customer_service',
    description: 'Tier-1 support for premium subscribers across product lines.',
    totalCalls: 3421,
    avgScore: 84.1,
    status: 'active',
    startDate: '2026-09-01',
    kpis: ['First Call Resolution', 'CSAT Score', 'Handle Time', 'Escalation Rate'],
    groqPromptFocus: 'Identify issue root cause, resolution steps taken, and customer satisfaction indicators.',
    color: '#06b6d4',
    accentClass: 'cyan',
    agentCount: 38,
  },
  {
    id: 'c3',
    name: 'Tech Support L2 Escalations',
    type: 'technical',
    description: 'Level-2 technical resolution for complex infrastructure issues.',
    totalCalls: 892,
    avgScore: 81.7,
    status: 'active',
    startDate: '2026-08-15',
    kpis: ['Resolution Rate', 'Time-to-Resolution', 'Ticket Deflection', 'Documentation Quality'],
    groqPromptFocus: 'Extract technical steps, error codes, resolution paths, and escalation triggers.',
    color: '#8b5cf6',
    accentClass: 'violet',
    agentCount: 16,
  },
  {
    id: 'c4',
    name: 'AR Recovery — 90-Day Past Due',
    type: 'collections',
    description: 'Debt recovery outreach for accounts 90+ days past due.',
    totalCalls: 647,
    avgScore: 69.3,
    status: 'paused',
    startDate: '2026-07-01',
    endDate: '2026-11-30',
    kpis: ['Promise-to-Pay Rate', 'Settlement Rate', 'Compliance Score', 'Recovery Amount'],
    groqPromptFocus: 'Track payment commitments, hardship disclosures, compliance language, and dispute flags.',
    color: '#f59e0b',
    accentClass: 'amber',
    agentCount: 12,
  },
];

// ─────────────────────────────────────────────────────
// AGENTS
// ─────────────────────────────────────────────────────
export const agents: Agent[] = [
  {
    id: 'a1',
    name: 'Marcus Webb',
    email: 'marcus.webb@voiceqa.ai',
    campaignId: 'c1',
    callsHandled: 312,
    avgScore: 88.2,
    avatar: 'MW',
    tier: 'gold',
    skills: { empathy: 82, resolution: 90, communication: 94, productKnowledge: 88, compliance: 95, callControl: 79 },
    emotionConsistency: [
      { week: 'W1', score: 72 }, { week: 'W2', score: 75 }, { week: 'W3', score: 80 },
      { week: 'W4', score: 78 }, { week: 'W5', score: 83 }, { week: 'W6', score: 88 },
      { week: 'W7', score: 85 }, { week: 'W8', score: 91 },
    ],
    recentCalls: ['call1', 'call2', 'call3'],
  },
  {
    id: 'a2',
    name: 'Priya Nair',
    email: 'priya.nair@voiceqa.ai',
    campaignId: 'c2',
    callsHandled: 487,
    avgScore: 91.5,
    avatar: 'PN',
    tier: 'platinum',
    skills: { empathy: 96, resolution: 93, communication: 92, productKnowledge: 85, compliance: 98, callControl: 91 },
    emotionConsistency: [
      { week: 'W1', score: 85 }, { week: 'W2', score: 87 }, { week: 'W3', score: 89 },
      { week: 'W4', score: 88 }, { week: 'W5', score: 92 }, { week: 'W6', score: 93 },
      { week: 'W7', score: 91 }, { week: 'W8', score: 94 },
    ],
    recentCalls: ['call4', 'call5'],
  },
  {
    id: 'a3',
    name: 'Devon Cross',
    email: 'devon.cross@voiceqa.ai',
    campaignId: 'c1',
    callsHandled: 198,
    avgScore: 72.8,
    avatar: 'DC',
    tier: 'silver',
    skills: { empathy: 65, resolution: 74, communication: 78, productKnowledge: 72, compliance: 88, callControl: 68 },
    emotionConsistency: [
      { week: 'W1', score: 60 }, { week: 'W2', score: 63 }, { week: 'W3', score: 58 },
      { week: 'W4', score: 67 }, { week: 'W5', score: 70 }, { week: 'W6', score: 65 },
      { week: 'W7', score: 72 }, { week: 'W8', score: 74 },
    ],
    recentCalls: ['call6'],
  },
  {
    id: 'a4',
    name: 'Sofia Vasquez',
    email: 'sofia.vasquez@voiceqa.ai',
    campaignId: 'c3',
    callsHandled: 256,
    avgScore: 85.6,
    avatar: 'SV',
    tier: 'gold',
    skills: { empathy: 80, resolution: 92, communication: 88, productKnowledge: 94, compliance: 91, callControl: 85 },
    emotionConsistency: [
      { week: 'W1', score: 77 }, { week: 'W2', score: 80 }, { week: 'W3', score: 82 },
      { week: 'W4', score: 85 }, { week: 'W5', score: 83 }, { week: 'W6', score: 87 },
      { week: 'W7', score: 86 }, { week: 'W8', score: 89 },
    ],
    recentCalls: ['call7', 'call8'],
  },
  {
    id: 'a5',
    name: 'Tariq Johnson',
    email: 'tariq.j@voiceqa.ai',
    campaignId: 'c4',
    callsHandled: 143,
    avgScore: 66.4,
    avatar: 'TJ',
    tier: 'bronze',
    skills: { empathy: 58, resolution: 65, communication: 70, productKnowledge: 62, compliance: 82, callControl: 60 },
    emotionConsistency: [
      { week: 'W1', score: 50 }, { week: 'W2', score: 55 }, { week: 'W3', score: 52 },
      { week: 'W4', score: 60 }, { week: 'W5', score: 58 }, { week: 'W6', score: 63 },
      { week: 'W7', score: 62 }, { week: 'W8', score: 67 },
    ],
    recentCalls: ['call9'],
  },
];

// ─────────────────────────────────────────────────────
// TRANSCRIPT SEGMENTS
// ─────────────────────────────────────────────────────
const sampleTranscript: TranscriptSegment[] = [
  {
    id: 't1', speaker: 'agent', startTime: 0, endTime: 8,
    text: 'Thank you for calling VoiceQA Enterprise Solutions, my name is Marcus. How can I assist you today?',
    redactedText: 'Thank you for calling VoiceQA Enterprise Solutions, my name is Marcus. How can I assist you today?',
    emotion: 'calm', hasPII: false,
  },
  {
    id: 't2', speaker: 'customer', startTime: 8, endTime: 22,
    text: "Hi Marcus, I'm calling about the proposal you sent to our procurement team. My name is Jennifer Caldwell and my direct line is 555-294-8821. I had some questions about the pricing tier.",
    redactedText: "Hi Marcus, I'm calling about the proposal you sent to our procurement team. My name is [REDACTED] and my direct line is [REDACTED]. I had some questions about the pricing tier.",
    emotion: 'calm', hasPII: true,
  },
  {
    id: 't3', speaker: 'agent', startTime: 22, endTime: 34,
    text: "Absolutely, I'd be happy to walk you through the pricing. We have three tiers designed for different enterprise scales. The Enterprise tier would likely be the best fit given your team size of around 500.",
    redactedText: "Absolutely, I'd be happy to walk you through the pricing. We have three tiers designed for different enterprise scales. The Enterprise tier would likely be the best fit given your team size of around 500.",
    emotion: 'calm', hasPII: false,
  },
  {
    id: 't4', speaker: 'customer', startTime: 34, endTime: 52,
    text: "Well, our competitor just offered us a 40% discount on a similar package. I honestly don't see why we should pay more for features we're not even sure we'll use. This seems like a lot of money for something unproven.",
    redactedText: "Well, our competitor just offered us a 40% discount on a similar package. I honestly don't see why we should pay more for features we're not even sure we'll use. This seems like a lot of money for something unproven.",
    emotion: 'stress', hasPII: false,
  },
  {
    id: 't5', speaker: 'agent', startTime: 52, endTime: 68,
    text: "I completely understand your concern — ROI is everything at the enterprise level. What our platform provides that differs from competitors is our multimodal AI, which averages 34% improvement in agent performance within 60 days. Can I share a case study from a similar company?",
    redactedText: "I completely understand your concern — ROI is everything at the enterprise level. What our platform provides that differs from competitors is our multimodal AI, which averages 34% improvement in agent performance within 60 days. Can I share a case study from a similar company?",
    emotion: 'calm', hasPII: false,
  },
  {
    id: 't6', speaker: 'customer', startTime: 68, endTime: 85,
    text: "I've seen case studies before and they always cherry-pick the best results. What happens when it doesn't work? Who's accountable? My account number is ACC-77-449821 and I need assurances in writing.",
    redactedText: "I've seen case studies before and they always cherry-pick the best results. What happens when it doesn't work? Who's accountable? My account number is [REDACTED] and I need assurances in writing.",
    emotion: 'agitation', hasPII: true,
  },
  {
    id: 't7', speaker: 'agent', startTime: 85, endTime: 102,
    text: "That's a completely fair point and I respect you for asking it. We offer a 90-day performance guarantee — if your QA scores don't improve by at least 20%, you receive a full credit. That's how confident we are. I'd love to schedule a demo with your team. Would Thursday at 2pm work?",
    redactedText: "That's a completely fair point and I respect you for asking it. We offer a 90-day performance guarantee — if your QA scores don't improve by at least 20%, you receive a full credit. That's how confident we are. I'd love to schedule a demo with your team. Would Thursday at 2pm work?",
    emotion: 'calm', hasPII: false,
  },
  {
    id: 't8', speaker: 'customer', startTime: 102, endTime: 115,
    text: "Hmm, that does sound more reasonable. Thursday could work. Let me check with my team. Can you send the guarantee terms to jennifer.caldwell@acmecorp.com before then?",
    redactedText: "Hmm, that does sound more reasonable. Thursday could work. Let me check with my team. Can you send the guarantee terms to [REDACTED] before then?",
    emotion: 'calm', hasPII: true,
  },
  {
    id: 't9', speaker: 'agent', startTime: 115, endTime: 128,
    text: "Absolutely, I'll have that over within the hour. I'll also include a personalized ROI projection based on your team size. Looking forward to Thursday — you're going to love what you see. Is there anything else I can help you with today?",
    redactedText: "Absolutely, I'll have that over within the hour. I'll also include a personalized ROI projection based on your team size. Looking forward to Thursday — you're going to love what you see. Is there anything else I can help you with today?",
    emotion: 'calm', hasPII: false,
  },
  {
    id: 't10', speaker: 'customer', startTime: 128, endTime: 135,
    text: "No, that should do it. Thanks Marcus.",
    redactedText: "No, that should do it. Thanks Marcus.",
    emotion: 'calm', hasPII: false,
  },
];

function buildEmotionTimeline(transcript: TranscriptSegment[]): EmotionPoint[] {
  const points: EmotionPoint[] = [];
  const totalDuration = transcript[transcript.length - 1].endTime;
  for (let t = 0; t <= totalDuration; t += 2) {
    const seg = transcript.find(s => t >= s.startTime && t < s.endTime);
    const emotion = seg ? seg.emotion : 'calm';
    const base = emotion === 'agitation' ? 0.8 : emotion === 'stress' ? 0.5 : 0.3;
    const noise = (Math.random() - 0.5) * 0.2;
    points.push({ time: t, emotion, intensity: Math.min(1, Math.max(0, base + noise)) });
  }
  return points;
}

// ─────────────────────────────────────────────────────
// CALLS
// ─────────────────────────────────────────────────────
export const calls: Call[] = [
  {
    id: 'call1',
    campaignId: 'c1',
    agentId: 'a1',
    date: '2026-05-01 14:23',
    duration: 135,
    agentTalkTime: 72,
    customerTalkTime: 55,
    qaScore: 88,
    transcript: sampleTranscript,
    tags: ['Objection Handled', 'Demo Booked', 'Competitor Mention'],
    leadStatus: 'hot',
    outcome: 'Demo scheduled for Thursday; guarantee terms requested.',
    isGoldenMoment: true,
    emotionTimeline: buildEmotionTimeline(sampleTranscript),
    callSummary: 'Agent handled pricing objection effectively using the guarantee offer and booked a follow-up demo. Strong product knowledge demonstrated. Customer showed clear buying signals by the end of the call.',
  },
  {
    id: 'call2',
    campaignId: 'c1',
    agentId: 'a1',
    date: '2026-05-01 11:04',
    duration: 94,
    agentTalkTime: 60,
    customerTalkTime: 28,
    qaScore: 74,
    transcript: sampleTranscript.slice(0, 5),
    tags: ['Short Call', 'Pricing Query'],
    leadStatus: 'warm',
    outcome: 'Customer requested callback next week.',
    isGoldenMoment: false,
    emotionTimeline: buildEmotionTimeline(sampleTranscript.slice(0, 5)),
    callSummary: 'Call ended without a firm next step. Agent dominated talk time but failed to surface key pain points.',
  },
  {
    id: 'call3',
    campaignId: 'c1',
    agentId: 'a3',
    date: '2026-04-30 16:45',
    duration: 212,
    agentTalkTime: 145,
    customerTalkTime: 58,
    qaScore: 61,
    transcript: sampleTranscript,
    tags: ['Long Call', 'Escalation Risk', 'Agitation Detected'],
    leadStatus: 'cold',
    outcome: 'Customer declined to proceed. No future contact scheduled.',
    isGoldenMoment: false,
    emotionTimeline: buildEmotionTimeline(sampleTranscript),
    callSummary: 'Agent struggled with objection handling. Customer expressed frustration multiple times. High agent talk ratio with poor active listening.',
  },
  {
    id: 'call4',
    campaignId: 'c2',
    agentId: 'a2',
    date: '2026-05-01 09:12',
    duration: 178,
    agentTalkTime: 85,
    customerTalkTime: 88,
    qaScore: 95,
    transcript: sampleTranscript,
    tags: ['FCR', 'High CSAT', 'Golden Moment'],
    leadStatus: 'warm',
    outcome: 'Issue resolved on first contact. CSAT survey sent.',
    isGoldenMoment: true,
    emotionTimeline: buildEmotionTimeline(sampleTranscript),
    callSummary: 'Exemplary customer service call. Priya demonstrated exceptional empathy and resolved a complex billing dispute without escalation.',
  },
  {
    id: 'call5',
    campaignId: 'c2',
    agentId: 'a2',
    date: '2026-04-30 15:33',
    duration: 143,
    agentTalkTime: 70,
    customerTalkTime: 68,
    qaScore: 90,
    transcript: sampleTranscript.slice(0, 7),
    tags: ['FCR', 'Escalation Avoided'],
    leadStatus: 'cold',
    outcome: 'Technical issue escalated to Tier-2 but full context documented.',
    isGoldenMoment: false,
    emotionTimeline: buildEmotionTimeline(sampleTranscript.slice(0, 7)),
    callSummary: 'Well-managed call with balanced conversation. Agent accurately diagnosed the technical issue and set appropriate escalation expectations.',
  },
];

// ─────────────────────────────────────────────────────
// LEADS
// ─────────────────────────────────────────────────────
export const leads: Lead[] = [
  { id: 'l1', callId: 'call1', agentId: 'a1', agentName: 'Marcus Webb', customerName: 'Jennifer Caldwell', status: 'hot', score: 94, lastContact: '2 hours ago', notes: 'Demo scheduled Thursday. Guarantee terms requested. Decision maker.', campaignId: 'c1', phone: '(555) ***-8821', value: 128000 },
  { id: 'l2', callId: 'call4', agentId: 'a1', agentName: 'Marcus Webb', customerName: 'Robert Huang', status: 'hot', score: 87, lastContact: '5 hours ago', notes: 'Requested enterprise proposal. Budget confirmed Q4.', campaignId: 'c1', phone: '(555) ***-4412', value: 84000 },
  { id: 'l3', callId: 'call5', agentId: 'a2', agentName: 'Priya Nair', customerName: 'Lisa Moreno', status: 'warm', score: 68, lastContact: '1 day ago', notes: 'Interested but needs internal approval. Follow-up in 5 days.', campaignId: 'c1', phone: '(555) ***-7723', value: 42000 },
  { id: 'l4', callId: 'call2', agentId: 'a4', agentName: 'Sofia Vasquez', customerName: 'Daniel Okafor', status: 'warm', score: 55, lastContact: '2 days ago', notes: 'Price-sensitive. Requested comparison sheet.', campaignId: 'c1', phone: '(555) ***-3301', value: 31000 },
  { id: 'l5', callId: 'call3', agentId: 'a3', agentName: 'Devon Cross', customerName: 'Sarah Ito', status: 'cold', score: 22, lastContact: '4 days ago', notes: 'Declined demo. Not interested at this time.', campaignId: 'c1', phone: '(555) ***-9988', value: 0 },
  { id: 'l6', callId: 'call1', agentId: 'a5', agentName: 'Tariq Johnson', customerName: 'Michael Torres', status: 'cold', score: 18, lastContact: '1 week ago', notes: 'Currently under contract with competitor. Revisit Q2 2027.', campaignId: 'c1', phone: '(555) ***-6601', value: 0 },
];

// ─────────────────────────────────────────────────────
// GOLDEN MOMENTS
// ─────────────────────────────────────────────────────
export const goldenMoments: GoldenMoment[] = [
  {
    id: 'gm1', callId: 'call1', agentId: 'a1', agentName: 'Marcus Webb',
    campaignType: 'sales', title: 'The Guarantee Close', duration: 30, score: 96,
    tags: ['Objection Handled', 'Guarantee', 'Empathy'],
    description: 'Textbook objection handling using the 90-day guarantee to neutralize risk perception.',
    transcript: '"That\'s a completely fair point... we offer a 90-day performance guarantee — if your QA scores don\'t improve by at least 20%, you receive a full credit. That\'s how confident we are."',
    date: '2026-05-01',
  },
  {
    id: 'gm2', callId: 'call4', agentId: 'a2', agentName: 'Priya Nair',
    campaignType: 'customer_service', title: 'De-escalation Masterclass', duration: 28, score: 98,
    tags: ['Empathy', 'De-escalation', 'FCR'],
    description: 'Rapid emotional recognition and calm-focused language turned an angry caller into a satisfied one.',
    transcript: '"I completely hear you, and I\'d feel the same way in your position. Let me personally take ownership of this right now and make sure we resolve it before this call ends."',
    date: '2026-05-01',
  },
  {
    id: 'gm3', callId: 'call5', agentId: 'a4', agentName: 'Sofia Vasquez',
    campaignType: 'technical', title: 'Technical Clarity Under Pressure', duration: 25, score: 91,
    tags: ['Technical', 'Clarity', 'Documentation'],
    description: 'Clear, jargon-free explanation of a complex network issue with step-by-step verification.',
    transcript: '"Think of it like a traffic light — when the packet loss exceeds 15%, it\'s like the light gets stuck on red. Here\'s what we\'ll do in three steps to fix it permanently..."',
    date: '2026-04-30',
  },
  {
    id: 'gm4', callId: 'call1', agentId: 'a1', agentName: 'Marcus Webb',
    campaignType: 'sales', title: 'Competitor Pivot Technique', duration: 22, score: 88,
    tags: ['Competitor', 'Value Positioning', 'Confidence'],
    description: 'Reframed competitor pricing as a quality signal rather than getting defensive.',
    transcript: '"Our platform investment reflects the engineering depth behind it — 34% performance improvement in 60 days is a proven outcome, not a promise."',
    date: '2026-04-30',
  },
  {
    id: 'gm5', callId: 'call4', agentId: 'a2', agentName: 'Priya Nair',
    campaignType: 'customer_service', title: 'Proactive Empathy Opening', duration: 18, score: 93,
    tags: ['Empathy', 'Opening', 'Customer-First'],
    description: 'Set a collaborative tone within the first 10 seconds using personalized acknowledgment.',
    transcript: '"Before we dive in, I want you to know — I\'ve already pulled up your account history and I can see you\'ve been with us for 4 years. Your time matters to me today."',
    date: '2026-04-29',
  },
  {
    id: 'gm6', callId: 'call5', agentId: 'a2', agentName: 'Priya Nair',
    campaignType: 'customer_service', title: 'Perfect Wrap-up Sequence', duration: 20, score: 90,
    tags: ['Closing', 'Summary', 'Confirmation'],
    description: 'Complete call wrap-up with 3-step confirmation, timeline, and ownership statement.',
    transcript: '"So to confirm: your refund of $147 will process in 3-5 days, you\'ll get an email confirmation, and if anything feels off I\'m giving you my direct extension right now."',
    date: '2026-04-28',
  },
];

// ─────────────────────────────────────────────────────
// ALERTS
// ─────────────────────────────────────────────────────
export const alerts: Alert[] = [
  { id: 'al1', type: 'shouting', message: 'Sustained vocal agitation detected in call #call3 (Devon Cross) — 45-second shouting threshold exceeded.', timestamp: '2026-05-02 09:14', severity: 'critical', callId: 'call3', agentId: 'a3', resolved: false },
  { id: 'al2', type: 'processing_failure', message: 'Groq inference timeout on Campaign "AR Recovery" — 3 calls queued for re-processing.', timestamp: '2026-05-02 08:47', severity: 'critical', resolved: false },
  { id: 'al3', type: 'low_score', message: 'Agent Tariq Johnson average QA score dropped below 65 threshold (currently 62.1).', timestamp: '2026-05-02 08:30', severity: 'warning', agentId: 'a5', resolved: false },
  { id: 'al4', type: 'pii_leak', message: 'PII detected in unredacted export attempt by user "devon.cross" — export blocked.', timestamp: '2026-05-01 17:22', severity: 'critical', resolved: true },
  { id: 'al5', type: 'system', message: 'GPU utilization sustained above 90% for 15 minutes — inference latency may increase.', timestamp: '2026-05-01 16:55', severity: 'warning', resolved: true },
  { id: 'al6', type: 'low_score', message: 'Campaign "AR Recovery" average score fell below 70 — consider coaching intervention.', timestamp: '2026-05-01 14:10', severity: 'warning', resolved: false },
  { id: 'al7', type: 'system', message: 'Celery worker pool scaled to 8 instances due to queue depth of 127 pending calls.', timestamp: '2026-05-01 11:30', severity: 'info', resolved: true },
  { id: 'al8', type: 'processing_failure', message: 'Redis connection briefly lost (2.3 seconds) — all jobs recovered successfully.', timestamp: '2026-05-01 09:05', severity: 'info', resolved: true },
];

// ─────────────────────────────────────────────────────
// SYSTEM METRICS
// ─────────────────────────────────────────────────────
function genHistory(base: number, variance: number, count: number, labels: string[]): InferenceHistoryPoint[] {
  return labels.map((time, i) => ({
    time,
    value: Math.round((base + (Math.sin(i * 0.8) * variance) + (Math.random() - 0.5) * variance * 0.5) * 10) / 10,
  }));
}

const timeLabels = ['08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30'];

export const systemMetrics: SystemMetrics = {
  inferenceTime: 847,
  gpuLoad: 73,
  cpuLoad: 58,
  callsProcessing: 14,
  queueDepth: 32,
  uptime: 2184,
  inferenceHistory: genHistory(850, 120, 12, timeLabels),
  gpuHistory: genHistory(70, 15, 12, timeLabels),
};

// ─────────────────────────────────────────────────────
// DASHBOARD KPIs
// ─────────────────────────────────────────────────────
export const dashboardKPIs = {
  totalCallsToday: 284,
  avgQAScore: 79.8,
  fcrRate: 73.4,
  activeAgents: 47,
  callsInQueue: 32,
  avgHandleTime: 186,
  escalationRate: 8.2,
  piiRedactionsToday: 1243,
  weeklyTrend: [
    { day: 'Mon', calls: 312, score: 77 },
    { day: 'Tue', calls: 278, score: 80 },
    { day: 'Wed', calls: 341, score: 82 },
    { day: 'Thu', calls: 295, score: 78 },
    { day: 'Fri', calls: 284, score: 80 },
  ],
  campaignPerformance: [
    { name: 'Sales Blitz', score: 78, calls: 124 },
    { name: 'Support Queue', score: 84, calls: 98 },
    { name: 'Tech L2', score: 82, calls: 41 },
    { name: 'AR Recovery', score: 69, calls: 21 },
  ],
};

export const getUserByRole = (role: UserRole) => {
  const users = {
    admin: { id: 100, name: 'Alex Rivera', email: 'alex.rivera@voiceqa.ai', role: 'admin' as UserRole, avatar: 'AR' },
    manager: { id: 101, name: 'Sam Chen', email: 'sam.chen@voiceqa.ai', role: 'manager' as UserRole, avatar: 'SC' },
    qa: { id: 102, name: 'Jordan Lee', email: 'jordan.lee@voiceqa.ai', role: 'qa' as UserRole, avatar: 'JL' },
    agent: { id: 1, name: 'Marcus Webb', email: 'marcus.webb@voiceqa.ai', role: 'agent' as UserRole, avatar: 'MW' },
  };
  return users[role];
};
