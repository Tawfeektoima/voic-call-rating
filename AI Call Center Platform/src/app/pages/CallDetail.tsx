import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router';
import {
  Play, Pause, SkipBack, SkipForward, Volume2, Download,
  Star, Tag, ChevronLeft, User, Mic, Clock, Target,
  Flame, Thermometer, Snowflake, Loader2, ShieldAlert
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getCallDetails, getEmployees, getCampaigns } from '../lib/api';
import { Call, CallStatus, Agent, Campaign } from '../lib/types';
import { EmotionalWaveform } from '../components/call/EmotionalWaveform';
import { TalkListenGauge } from '../components/call/TalkListenGauge';
import { InteractiveTranscript } from '../components/call/InteractiveTranscript';
import { SalesScoreBreakdown } from '../components/call/SalesScoreBreakdown';
import { OfferFunnel } from '../components/call/OfferFunnel';
import { useApp } from '../context/AppContext';
import { cn } from '../components/ui/utils';
import { Skeleton } from '../components/ui/skeleton';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { ViolationItem } from '../components/call/ViolationItem';

const leadConfig = {
  hot: { icon: Flame, color: 'red', label: 'Hot Lead' },
  warm: { icon: Thermometer, color: 'amber', label: 'Warm Lead' },
  cold: { icon: Snowflake, color: 'blue', label: 'Cold Lead' },
};

const formatTime = (s: number) => {
  if (!s) return '0:00';
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
};

export function CallDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { userRole } = useApp();
  const canSeeLeadStatus = userRole === 'admin' || userRole === 'hr_manager' || userRole === 'qa';
  const isQAOrAdmin = userRole === 'admin' || userRole === 'qa';

  const [isEditingScore, setIsEditingScore] = useState(false);
  const [editScoreValue, setEditScoreValue] = useState("");
  const isSubmittingRef = useRef(false);

  const { data: call, isLoading: callLoading, refetch } = useQuery<Call>({
    queryKey: ['call', id],
    queryFn: () => getCallDetails(parseInt(id!)),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const status = data.status;
      // Stop polling if it's a legacy call stuck in a non-terminal state
      if (data.id <= 65 && (status === CallStatus.PENDING || status === CallStatus.PROCESSING)) return false;
      return (status === CallStatus.PENDING || status === CallStatus.PROCESSING) ? 2000 : false;
    }
  });

  const { data: agents } = useQuery({ queryKey: ['agents'], queryFn: getEmployees });
  const { data: campaigns } = useQuery({ queryKey: ['campaigns'], queryFn: getCampaigns });

  const agent = agents?.find(a => a.id === call?.employee_id);
  const campaign = campaigns?.find(c => c.id === call?.campaign_id);

  const handleScoreSubmit = async (newScoreStr: string) => {
    if (isSubmittingRef.current) return;
    const newScore = parseFloat(newScoreStr);
    if (isNaN(newScore) || newScore < 0 || newScore > 100) {
      alert("Please enter a valid score between 0 and 100.");
      setIsEditingScore(false);
      return;
    }
    const currentScore = call?.overridden_score ?? call?.evaluation_score ?? 0;
    if (newScore === currentScore) {
      setIsEditingScore(false);
      return;
    }
    
    isSubmittingRef.current = true;
    setIsEditingScore(false);

    const reason = window.prompt("Please enter a reason for overriding this score:");
    if (reason === null) {
      isSubmittingRef.current = false;
      return;
    }
    
    try {
      const { default: api } = await import("../lib/api");
      await api.patch(`/api/audio/${call?.id}/review`, {
        overridden_score: newScore,
        reason: reason || "Manual override"
      });
      refetch();
    } catch (err) {
      alert("Failed to save score override.");
    } finally {
      isSubmittingRef.current = false;
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleScoreSubmit(editScoreValue);
    } else if (e.key === 'Escape') {
      setIsEditingScore(false);
    }
  };

  const onBlur = () => {
    setTimeout(() => {
      if (!isSubmittingRef.current && isEditingScore) {
        handleScoreSubmit(editScoreValue);
      }
    }, 150);
  };

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(80);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isPlaying && call?.audio_duration) {
      timerRef.current = setInterval(() => {
        setCurrentTime(prev => {
          if (prev >= (call.audio_duration || 0)) {
            setIsPlaying(false);
            return 0;
          }
          return prev + 0.25;
        });
      }, 250);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isPlaying, call?.audio_duration]);

  const handleSeek = (t: number) => setCurrentTime(Math.min(t, call?.audio_duration || 0));
  
  if (callLoading) {
    return <div className="p-6 space-y-6"><Skeleton className="h-20 w-full bg-secondary" /><Skeleton className="h-96 w-full bg-secondary" /></div>;
  }

  if (!call) return <div className="p-6 text-muted-foreground">Call not found.</div>;

  const isProcessing = call.status === CallStatus.PENDING || call.status === CallStatus.PROCESSING;
  const leadC = call.lead_status ? (leadConfig as any)[call.lead_status] : null;
  const score = call.overridden_score ?? call.evaluation_score ?? 0;
  
  const agentTime = call.outcome?.agent_talk_time ?? call.agent_talk_time ?? 0;
  const customerTime = call.outcome?.customer_talk_time ?? call.customer_talk_time ?? 0;
  const silenceSeconds = (call.audio_duration || 0) - agentTime - customerTime;

  const isSalesCall = !!call?.sales_eval_data;
  const salesData = call?.sales_eval_data;

  return (
    <div className="p-6 space-y-5">
      {/* Back + Call Header */}
      <div className="flex items-start gap-4">
        <button onClick={() => navigate('/calls')} className="size-8 flex items-center justify-center rounded-lg bg-secondary text-muted-foreground hover:text-foreground transition-all flex-shrink-0">
          <ChevronLeft size={16} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="text-slate-100 text-base font-semibold">Call #{call.id}</h2>
            <span className={cn(
              'text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border',
              call.status === CallStatus.EVALUATED ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              call.status === CallStatus.FAILED ? 'bg-red-500/10 text-red-400 border-red-500/20' :
              'bg-amber-500/10 text-amber-400 border-amber-500/20'
            )}>
              {call.status}
            </span>
            {call.is_golden_moment && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 bg-amber-500/15 text-amber-400 border border-amber-500/20 rounded-full">
                <Star size={10} />Golden Moment
              </span>
            )}
            {canSeeLeadStatus && leadC && (
              <span className={cn(
                'flex items-center gap-1 text-xs px-2 py-0.5 rounded-full',
                call.lead_status === 'hot' ? 'bg-red-500/15 text-red-400 border border-red-500/20' :
                call.lead_status === 'warm' ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20' :
                'bg-blue-500/15 text-blue-400 border border-blue-500/20'
              )}>
                <leadC.icon size={10} />
                {leadC.label}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground flex-wrap">
            <span>{new Date(call.created_at).toLocaleString()}</span>
            <span>·</span>
            <span>{formatTime(call.audio_duration || 0)}</span>
            <span>·</span>
            <span>{agent?.name || `Agent #${call.employee_id}`}</span>
            <span>·</span>
            <span>{campaign?.name || `Campaign #${call.campaign_id}`}</span>
          </div>
        </div>

        <div className="flex items-center gap-4 flex-shrink-0">
          {/* Outcome Badge */}
          {!isProcessing && call.outcome && call.outcome.primary_outcome && (
            <div className="flex flex-col items-end px-4 py-3 rounded-xl border bg-secondary/50 border-border">
              <span className="text-sm font-semibold text-foreground">
                {call.outcome.primary_outcome}
              </span>
              {call.outcome.outcome_value != null && call.outcome.outcome_value > 0 && (
                <span className="text-xs text-emerald-400 font-bold mt-1">
                  ${call.outcome.outcome_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              )}
            </div>
          )}

          {/* QA Score Badge */}
          {!isProcessing && (
            <div 
              onDoubleClick={() => {
                if (isQAOrAdmin) {
                  setIsEditingScore(true);
                  setEditScoreValue(score.toString());
                }
              }}
              className={cn(
                'flex flex-col items-center px-4 py-3 rounded-xl border flex-shrink-0 select-none',
                score >= 85 ? 'bg-emerald-500/10 border-emerald-500/20' :
                score >= 70 ? 'bg-amber-500/10 border-amber-500/20' : 'bg-red-500/10 border-red-500/20',
                isQAOrAdmin && 'cursor-pointer hover:border-indigo-500/50',
                isEditingScore && 'ring-2 ring-indigo-500 border-transparent'
              )}
              title={isQAOrAdmin ? "Double click to edit score" : undefined}
            >
              {isEditingScore ? (
                <input
                  type="number"
                  min="0"
                  max="100"
                  className="w-16 text-center bg-background border border-border rounded text-lg font-bold text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  value={editScoreValue}
                  onChange={(e) => setEditScoreValue(e.target.value)}
                  onKeyDown={onKeyDown}
                  onBlur={onBlur}
                  autoFocus
                />
              ) : (
                <span className={cn(
                  'text-2xl font-bold',
                  score >= 85 ? 'text-emerald-400' : score >= 70 ? 'text-amber-400' : 'text-red-400'
                )}>{score}</span>
              )}
              <span className="text-muted-foreground text-xs">QA Score</span>
            </div>
          )}
        </div>
      </div>

      {/* Active QA Alarm Alert */}
      {call.qa_alarm && !call.overridden_score && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3">
          <ShieldAlert className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <h4 className="text-red-400 text-sm font-semibold">Active QA Alarm: Abuse Detected</h4>
            <p className="text-xs text-foreground/90 mt-1">
              {call.qa_alarm_reason || "Potential manipulative behavior or abuse has been flagged on this call."}
            </p>
            {call.qa_alarm_evidence && (
              <div className="text-[11px] text-muted-foreground bg-black/25 p-2 rounded border border-border mt-2 font-mono leading-relaxed">
                <span className="text-foreground/70 font-semibold block mb-1">Triggering Evidence:</span>
                {call.qa_alarm_evidence}
              </div>
            )}
            {isQAOrAdmin && (
              <p className="text-[10px] text-indigo-400 mt-2 font-semibold">
                💡 Double click the QA Score badge on the right to override the score and resolve this alarm.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Processing State Indicator */}
      {isProcessing && (
        <div className="bg-primary/10 border border-indigo-500/20 rounded-xl p-6 flex flex-col items-center justify-center text-center">
          <Loader2 size={40} className="text-primary animate-spin mb-4" />
          <h3 className="text-foreground font-semibold mb-1">AI Evaluation in Progress</h3>
          <p className="text-muted-foreground text-xs max-w-sm">
            We are currently transcribing the audio and running the QA analysis via Groq LPU. 
            This usually takes 15-30 seconds. This page will update automatically.
          </p>
        </div>
      )}

      {!isProcessing && (
        <>
          {/* Tags */}
          <div className="flex flex-wrap gap-2">
            {(call.tags || []).map(tag => (
              <span key={tag} className="flex items-center gap-1 text-xs px-2 py-0.5 bg-secondary text-muted-foreground border border-border rounded-full">
                <Tag size={9} />
                {tag}
              </span>
            ))}
          </div>

          {/* Emotional Waveform */}
          <div className="bg-card border border-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-foreground text-sm font-semibold">Emotional Heatmap Waveform</h3>
              <span className="text-xs text-muted-foreground">Click to seek · Colors by emotional energy</span>
            </div>
            {isProcessing ? <Skeleton className="h-24 w-full bg-secondary" /> : (
              <EmotionalWaveform
                emotionTimeline={call.emotion_timeline || []}
                duration={call.audio_duration || 0}
                currentTime={currentTime}
                onSeek={handleSeek}
                isPlaying={isPlaying}
              />
            )}

            {/* Playback Controls */}
            <div className="flex items-center gap-4 mt-4 pt-4 border-t border-border">
              <div className="flex items-center gap-2">
                <button onClick={() => handleSeek(Math.max(0, currentTime - 15))} className="size-8 flex items-center justify-center rounded-lg bg-secondary text-muted-foreground hover:text-foreground transition-all">
                  <SkipBack size={14} />
                </button>
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="size-10 flex items-center justify-center rounded-xl bg-primary hover:bg-indigo-400 text-white transition-all shadow-lg shadow-indigo-500/20"
                >
                  {isPlaying ? <Pause size={16} /> : <Play size={16} />}
                </button>
                <button onClick={() => handleSeek(Math.min(call.audio_duration || 0, currentTime + 15))} className="size-8 flex items-center justify-center rounded-lg bg-secondary text-muted-foreground hover:text-foreground transition-all">
                  <SkipForward size={14} />
                </button>
              </div>

              <span className="text-xs text-muted-foreground font-mono">{formatTime(currentTime)} / {formatTime(call.audio_duration || 0)}</span>

              <div className="flex-1" />

              <div className="flex items-center gap-2">
                <Volume2 size={14} className="text-muted-foreground" />
                <input
                  type="range" min={0} max={100} value={volume}
                  onChange={e => setVolume(Number(e.target.value))}
                  className="w-20 accent-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Main Analysis Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Left: Talk/Listen + Summary */}
            <div className="space-y-5">
              <TalkListenGauge
                agentSeconds={agentTime}
                customerSeconds={customerTime}
                silenceSeconds={Math.max(0, silenceSeconds)}
              />

                  {/* Campaign Specific Insights or Sales Dashboard */}
                  {!isProcessing && (
                    <>
                  {isSalesCall && salesData ? (
                    <>
                      <SalesScoreBreakdown breakdown={salesData.score_breakdown} />
                      <OfferFunnel 
                        presented={salesData.offers_presented}
                        skipped={salesData.offers_skipped_incorrectly}
                        details={salesData.offer_details}
                      />
                    </>
                  ) : (
                    call.outcome?.campaign_specific_data && Object.keys(call.outcome.campaign_specific_data).length > 0 && (
                      <div className="bg-card border border-border rounded-xl p-5 mb-5">
                        <div className="flex items-center gap-2 mb-3">
                          <Target size={14} className="text-primary" />
                          <span className="text-foreground text-sm font-semibold">Business Insights</span>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          {Object.entries(call.outcome.campaign_specific_data).map(([key, value]) => {
                            const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                            let displayValue = String(value);
                            if (typeof value === 'boolean') displayValue = value ? 'Yes' : 'No';
                            
                            return (
                              <div key={key} className="bg-secondary/30 rounded-lg p-2.5">
                                <p className="text-[10px] text-muted-foreground mb-1 uppercase tracking-wider">{displayKey}</p>
                                <p className="text-xs font-medium text-foreground">{displayValue}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )
                  )}
                </>
              )}

              {/* ── Card 1: AI Summary ── */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    📋 AI Analysis & Summary
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {call.ai_summary ?? "No analysis available for this call yet."}
                  </p>
                </CardContent>
              </Card>

              {/* ── Card 2: Performance Breakdown ── */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    📊 Performance Breakdown
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">

                  {/* Strengths */}
                  <div>
                    <h4 className="font-semibold text-green-600 mb-2">
                      ✅ Strengths & Achievements
                    </h4>
                    {call.strengths && call.strengths.length > 0 ? (
                      <ul className="list-disc list-inside text-sm space-y-1">
                        {call.strengths.map((s, i) => (
                          <li key={i} className="text-muted-foreground">
                            {typeof s === 'string' ? s : s.issue}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground italic">
                        No notable strengths identified in this call.
                      </p>
                    )}
                  </div>

                  <Separator />

                  {/* Deductions */}
                  <div>
                    <h4 className="font-semibold text-red-600 mb-2">
                      ❌ Deductions & Weaknesses
                    </h4>
                    {call.deductions && call.deductions.length > 0 ? (
                      <div className="space-y-2">
                        {call.deductions.map((d, i) => (
                          <div key={i} className="flex justify-between text-sm">
                            <span>{d.category}</span>
                            <span className="flex gap-4">
                              <span className="text-red-500 font-medium">{d.deduction}</span>
                              <span className="text-muted-foreground">
                                Score: {d.score}/{d.max}
                              </span>
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-green-600 italic">
                        🎉 Perfect performance! No weaknesses identified.
                      </p>
                    )}
                  </div>

                </CardContent>
              </Card>

              {/* ── Card 3: Compliance Violations ── */}
              <Card className={
                call.violations && call.violations.length > 0
                  ? "border-red-400 bg-red-50 dark:bg-red-950/20"
                  : "border-green-400 bg-green-50 dark:bg-green-950/20"
              }>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {call.violations && call.violations.length > 0 ? "🚨" : "✅"} Compliance Violations
                    {call.violations && call.violations.length > 0 && (
                      <Badge variant="destructive" className="ml-2">
                        {call.violations.length} Found
                      </Badge>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {call.violations && call.violations.length > 0 && (
                    call.violations.map((v, i) => (
                      <ViolationItem key={i} violation={v} />
                    ))
                  )}
                </CardContent>
              </Card>

              {/* ── Card 4: Score Override History ── */}
              {call.override_audits && call.override_audits.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      🕒 Score Override History
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="relative border-l-2 border-border pl-4 space-y-4">
                      {call.override_audits.map((audit) => (
                        <div key={audit.id} className="relative">
                          {/* Dot marker */}
                          <div className="absolute -left-[21px] top-1.5 size-2 rounded-full bg-indigo-500 border border-card animate-pulse" />
                          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                            <span className="font-semibold text-foreground">{audit.reviewer_name}</span>
                            <span>{new Date(audit.created_at).toLocaleString()}</span>
                          </div>
                          <div className="text-xs text-foreground bg-secondary/30 rounded p-2 border border-border">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-[10px] bg-secondary px-1.5 py-0.5 rounded text-muted-foreground">
                                Score Changed
                              </span>
                              <span className="font-bold text-red-400">
                                {audit.old_score ?? 'N/A'}
                              </span>
                              <span className="text-muted-foreground">→</span>
                              <span className="font-bold text-emerald-400">
                                {audit.new_score}
                              </span>
                            </div>
                            {audit.reason && (
                              <p className="text-[11px] text-slate-300 leading-relaxed italic">
                                "{audit.reason}"
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Right: Interactive Transcript */}
            <div className="lg:col-span-2" style={{ minHeight: '600px' }}>
              <InteractiveTranscript
                transcript={call.transcript || []}
                currentTime={currentTime}
                onSeek={handleSeek}
                agentName={agent?.name}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
