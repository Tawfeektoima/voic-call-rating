import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router';
import {
  Play, Pause, SkipBack, SkipForward, Volume2, Download,
  Star, Tag, ChevronLeft, User, Mic, Clock, Target,
  TrendingUp, Flame, Thermometer, Snowflake, Zap, Loader2
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getCallDetails, getEmployees, getCampaigns } from '../lib/api';
import { Call, CallStatus, Agent, Campaign } from '../lib/types';
import { EmotionalWaveform } from '../components/call/EmotionalWaveform';
import { TalkListenGauge } from '../components/call/TalkListenGauge';
import { InteractiveTranscript } from '../components/call/InteractiveTranscript';
import { CallAnalysis } from '../components/call/CallAnalysis';
import { useApp } from '../context/AppContext';
import { cn } from '../components/ui/utils';
import { Skeleton } from '../components/ui/skeleton';

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
  const isAdminOrManager = userRole === 'admin' || userRole === 'manager';

  const { data: call, isLoading: callLoading, refetch } = useQuery<Call>({
    queryKey: ['call', id],
    queryFn: () => getCallDetails(parseInt(id!)),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return (status === CallStatus.PENDING || status === CallStatus.PROCESSING) ? 3000 : false;
    }
  });

  const { data: agents } = useQuery({ queryKey: ['agents'], queryFn: getEmployees });
  const { data: campaigns } = useQuery({ queryKey: ['campaigns'], queryFn: getCampaigns });

  const agent = agents?.find(a => a.id === call?.employee_id);
  const campaign = campaigns?.find(c => c.id === call?.campaign_id);

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
            {isAdminOrManager && leadC && (
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
            <div className={cn(
              'flex flex-col items-center px-4 py-3 rounded-xl border flex-shrink-0',
              score >= 85 ? 'bg-emerald-500/10 border-emerald-500/20' :
              score >= 70 ? 'bg-amber-500/10 border-amber-500/20' : 'bg-red-500/10 border-red-500/20'
            )}>
              <span className={cn(
                'text-2xl font-bold',
                score >= 85 ? 'text-emerald-400' : score >= 70 ? 'text-amber-400' : 'text-red-400'
              )}>{score}</span>
              <span className="text-muted-foreground text-xs">QA Score</span>
            </div>
          )}
        </div>
      </div>

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

              {/* Campaign Specific Insights */}
              {!isProcessing && call.outcome?.campaign_specific_data && Object.keys(call.outcome.campaign_specific_data).length > 0 && (
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
              )}

              {/* AI Summary */}
              <div className="bg-card border border-border rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <div className="size-5 rounded bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center">
                    <Zap size={10} className="text-white" />
                  </div>
                  <span className="text-foreground text-sm font-semibold">AI Analysis & Summary</span>
                </div>
                <div className="space-y-3">
                  {call.call_summary && (
                    <p className="text-xs text-foreground leading-relaxed font-medium">
                      {call.call_summary}
                    </p>
                  )}
                  {call.reasoning && (
                    <div className={cn("pt-3 border-t border-border", !call.call_summary && "border-t-0 pt-0")}>
                      <p className="text-[11px] text-muted-foreground leading-relaxed italic">
                        <span className="font-bold not-italic text-indigo-400 mr-1">Reasoning:</span>
                        {call.reasoning}
                      </p>
                    </div>
                  )}
                  {!call.call_summary && !call.reasoning && (
                    <p className="text-xs text-muted-foreground italic">No analysis available for this call yet.</p>
                  )}
                </div>
              </div>
              
              {/* Balanced Analysis (Strengths & Weaknesses) */}
              <CallAnalysis
                strengths={call.strengths || []}
                weaknesses={call.weaknesses || []}
              />
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
