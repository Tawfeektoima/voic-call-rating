import { useState, useRef, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router';
import {
  ArrowLeft, Play, Pause, SkipBack, SkipForward, Volume2, Phone, Clock,
  CheckCircle2, XCircle, AlertTriangle, Edit3, Save, ChevronDown, ChevronUp,
  User, Headphones, Star, RotateCcw, Shield, MessageSquare, Download, Share2,
  Loader2, AlertCircle, Sparkles
} from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import WaveSurfer from 'wavesurfer.js';
import api from '@/app/lib/api';
import { formatDuration, getScoreColor } from '../data/mockData';
import { useLang } from '../context/LangContext';

interface CallDetailProps {
  lang: 'en' | 'ar';
}

const parseTranscript = (text: string | null) => {
  if (!text) return [];
  const lines = text.split('\n');
  return lines.map((line, idx) => {
    const match = line.match(/\[([\d.]+) - ([\d.]+)\] (.*?): (.*)/);
    if (match) {
      return {
        id: `t${idx}`,
        timeSeconds: parseFloat(match[1]),
        endTimeSeconds: parseFloat(match[2]),
        speaker: match[3].includes('00') ? 'Agent' : 'Customer',
        speakerRaw: match[3],
        text: match[4],
        timeLabel: `${Math.floor(parseFloat(match[1]) / 60)}:${(Math.floor(parseFloat(match[1]) % 60)).toString().padStart(2, '0')}`
      };
    }
    return null;
  }).filter(Boolean);
};

export function CallDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { lang } = useLang();
  const isRtl = lang === 'ar';
  const t = (en: string, ar: string) => isRtl ? ar : en;
  const queryClient = useQueryClient();

  const waveformRef = useRef<HTMLDivElement>(null);
  const wavesurfer = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [volume, setVolume] = useState(0.8);
  const [activeSegment, setActiveSegment] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>('scorecard');
  const transcriptRef = useRef<HTMLDivElement>(null);

  // --- API Query ---
  const { data: call, isLoading, isError } = useQuery({
    queryKey: ['call', id],
    queryFn: async () => {
      const res = await api.get(`/audio/${id}`);
      return res.data;
    },
    enabled: !!id,
    refetchInterval: (data) => (data?.state?.data?.status === 'pending' || data?.state?.data?.status === 'processing' ? 5000 : false)
  });

  const { data: agent } = useQuery({
    queryKey: ['agent', call?.employee_id],
    queryFn: async () => {
      const res = await api.get('/admin/employees');
      const found = res.data.find((a: any) => a.id === call?.employee_id);
      if (found) {
        return {
          ...found,
          initials: found.name.split(' ').map((n: any) => n[0]).join('').toUpperCase(),
          color: '#6366f1'
        };
      }
      return null;
    },
    enabled: !!call?.employee_id
  });

  const { data: campaign } = useQuery({
    queryKey: ['campaign', call?.campaign_id],
    queryFn: async () => {
      const res = await api.get('/admin/campaigns');
      return res.data.find((c: any) => c.id === call?.campaign_id);
    },
    enabled: !!call?.campaign_id
  });

  const transcript = useMemo(() => parseTranscript(call?.transcript), [call?.transcript]);

  // --- WaveSurfer Init ---
  useEffect(() => {
    if (!waveformRef.current || !call?.id || call.status === 'pending') return;

    wavesurfer.current = WaveSurfer.create({
      container: waveformRef.current,
      waveColor: '#1e293b',
      progressColor: '#6366f1',
      cursorColor: '#818cf8',
      barWidth: 2,
      barRadius: 3,
      responsive: true,
      height: 60,
      url: `/api/audio/${call.id}/file`,
    });

    wavesurfer.current.on('play', () => setIsPlaying(true));
    wavesurfer.current.on('pause', () => setIsPlaying(false));
    wavesurfer.current.on('timeupdate', (time) => {
      setCurrentTime(time);
      const seg = transcript.findLast(s => (s?.timeSeconds || 0) <= time);
      if (seg) setActiveSegment(seg.id);
    });

    return () => {
      wavesurfer.current?.destroy();
    };
  }, [call?.id, call?.status, transcript]);

  const handlePlayPause = () => {
    wavesurfer.current?.playPause();
  };

  const handleSeek = (time: number) => {
    wavesurfer.current?.setTime(time);
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    wavesurfer.current?.setPlaybackRate(speed);
  };

  const handleVolumeChange = (v: number) => {
    setVolume(v);
    wavesurfer.current?.setVolume(v);
  };

  const [overrideMode, setOverrideMode] = useState(false);
  const [overrideScore, setOverrideScore] = useState('');
  const [overrideNote, setOverrideNote] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (call) {
      setOverrideScore(call.overridden_score?.toString() || call.evaluation_score?.toString() || '');
      setOverrideNote(call.reviewer_notes || '');
    }
  }, [call]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <Loader2 size={40} className="text-indigo-500 animate-spin" />
        <p className="text-slate-500">{t('Loading call analysis...', 'جاري تحميل تحليل المكالمة...')}</p>
      </div>
    );
  }

  if (isError || !call) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <AlertCircle size={40} className="text-red-500" />
        <p className="text-slate-500">{t('Call not found or error loading', 'المكالمة غير موجودة أو حدث خطأ في التحميل')}</p>
        <button onClick={() => navigate('/calls')} className="text-indigo-400 underline">{t('Back to Explorer', 'العودة للمستكشف')}</button>
      </div>
    );
  }

  const displayScore = call.overridden_score !== null && call.overridden_score !== undefined 
    ? call.overridden_score 
    : (call.evaluation_score || 0);

  const handleSaveOverride = async () => {
    try {
      const score = overrideScore === '' ? null : parseFloat(overrideScore);
      await api.patch(`/audio/${id}/review`, {
        overridden_score: score,
        reviewer_notes: overrideNote
      });
      
      queryClient.invalidateQueries({ queryKey: ['call', id] });
      setSaveSuccess(true);
      setOverrideMode(false);
      toast.success(t('Review saved successfully', 'تم حفظ المراجعة بنجاح'));
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      toast.error(t('Failed to save review', 'فشل في حفظ المراجعة'));
    }
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate('/calls')}
          className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft size={16} />
          <span className="text-sm">{t('Back to Calls', 'العودة للمكالمات')}</span>
        </button>
        <div className="w-px h-4 bg-slate-700" />
        <div className="flex-1">
          <h1 className="text-lg font-semibold text-white">
            {t('Call Analysis', 'تحليل المكالمة')}: {call.original_filename}
          </h1>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-xs text-slate-500">{agent?.name}</span>
            <span className="text-slate-700">•</span>
            <span className="text-xs text-slate-500">{campaign?.name}</span>
            <span className="text-slate-700">•</span>
            <span className="text-xs text-slate-500">{new Date(call.created_at).toLocaleString()}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {saveSuccess && (
            <div className="flex items-center gap-1.5 text-xs text-green-400 bg-green-500/10 border border-green-500/20 px-3 py-1.5 rounded-lg">
              <CheckCircle2 size={13} /> {t('Override saved', 'تم حفظ التعديل')}
            </div>
          )}
          <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-sm text-slate-400 hover:text-slate-200 transition-colors">
            <Download size={14} />
          </button>
          <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-sm text-slate-400 hover:text-slate-200 transition-colors">
            <Share2 size={14} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Left: Audio + Transcript */}
        <div className="xl:col-span-3 space-y-5">
          {/* Audio Player */}
          <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-5">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0"
                style={{ backgroundColor: agent?.color + '22', color: agent?.color, border: `1px solid ${agent?.color}44` }}
              >
                {agent?.initials || '??'}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-white">{agent?.name || 'Unknown Agent'}</p>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <span className="flex items-center gap-1"><Phone size={10} /> {call.original_filename}</span>
                  <span className="flex items-center gap-1"><Clock size={10} /> {formatDuration(call.audio_duration || 0)}</span>
                </div>
              </div>
              <div
                className="text-2xl font-bold"
                style={{ color: getScoreColor(displayScore) }}
              >
                {call.status === 'evaluated' ? `${displayScore}%` : call.status.toUpperCase()}
              </div>
            </div>

            {/* Waveform Container */}
            <div className="relative">
              {call.status === 'pending' || call.status === 'processing' ? (
                <div className="h-16 flex items-center justify-center bg-slate-900/50 rounded-lg border border-slate-800 border-dashed">
                  <div className="flex items-center gap-3">
                    <Loader2 size={16} className="text-indigo-500 animate-spin" />
                    <span className="text-xs text-slate-500">{t('Audio being processed...', 'جاري معالجة الصوت...')}</span>
                  </div>
                </div>
              ) : (
                <div ref={waveformRef} className="h-16" />
              )}
            </div>

            {/* Time */}
            <div className="flex justify-between text-[11px] text-slate-600 mt-1 mb-4">
              <span>{formatDuration(Math.floor(currentTime))}</span>
              <span>{formatDuration(call.audio_duration || 0)}</span>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <select
                  value={playbackSpeed}
                  onChange={e => handleSpeedChange(Number(e.target.value))}
                  className="bg-slate-800 border border-slate-700/50 rounded-lg px-2 py-1 text-xs text-slate-400 focus:outline-none"
                >
                  {[0.5, 0.75, 1, 1.25, 1.5, 2].map(s => (
                    <option key={s} value={s}>{s}x</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => handleSeek(Math.max(0, currentTime - 10))}
                  className="p-2 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <SkipBack size={18} />
                </button>
                <button
                  onClick={handlePlayPause}
                  disabled={call.status !== 'evaluated' && call.status !== 'transcribed'}
                  className="w-11 h-11 rounded-full bg-indigo-600 hover:bg-indigo-500 flex items-center justify-center text-white transition-colors shadow-lg shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isPlaying ? <Pause size={18} /> : <Play size={18} className="translate-x-0.5" />}
                </button>
                <button
                  onClick={() => handleSeek(Math.min(call.audio_duration || 0, currentTime + 10))}
                  className="p-2 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <SkipForward size={18} />
                </button>
              </div>

              <div className="flex items-center gap-2">
                <Volume2 size={14} className="text-slate-500" />
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={volume}
                  onChange={e => handleVolumeChange(Number(e.target.value))}
                  className="w-16 accent-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Transcript */}
          <div className="bg-[#111827] border border-slate-800/60 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800/60">
              <div className="flex items-center gap-2">
                <MessageSquare size={15} className="text-slate-400" />
                <h3 className="text-sm font-semibold text-white">{t('Interactive Transcript', 'النص التفاعلي')}</h3>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1"><User size={11} className="text-blue-400" /> {t('Agent', 'الوكيل')}</span>
                <span className="flex items-center gap-1"><Headphones size={11} className="text-slate-400" /> {t('Customer', 'العميل')}</span>
              </div>
            </div>
            <div ref={transcriptRef} className="p-5 space-y-4 max-h-[500px] overflow-y-auto">
              {transcript.length === 0 ? (
                <div className="py-10 text-center">
                  <p className="text-sm text-slate-600">{t('Transcript will appear once processing is complete.', 'سيظهر النص بمجرد اكتمال المعالجة.')}</p>
                </div>
              ) : transcript.map((seg: any) => {
                const isActive = activeSegment === seg.id;
                const isAgent = seg.speaker === 'Agent';
                return (
                  <div
                    key={seg.id}
                    onClick={() => { handleSeek(seg.timeSeconds); setActiveSegment(seg.id); }}
                    className={`flex gap-3 cursor-pointer transition-all rounded-lg p-2 -mx-2 ${isActive ? 'bg-indigo-500/10' : 'hover:bg-slate-800/30'}`}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      <div
                        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold
                          ${isAgent
                            ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                            : 'bg-slate-700/60 text-slate-400 border border-slate-600/30'
                          }`}
                      >
                        {isAgent ? 'A' : 'C'}
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium ${isAgent ? 'text-blue-400' : 'text-slate-500'}`}>
                          {isAgent ? t('Agent', 'الوكيل') : `${t('Customer', 'العميل')} (${seg.speakerRaw})`}
                        </span>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleSeek(seg.timeSeconds); wavesurfer.current?.play(); }}
                          className="text-[10px] text-slate-600 hover:text-indigo-400 transition-colors font-mono"
                        >
                          {seg.timeLabel}
                        </button>
                      </div>
                      <p className={`text-sm leading-relaxed ${isActive ? 'text-white' : 'text-slate-400'}`}>
                        {seg.text}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Scorecard + AI Analysis */}
        <div className="xl:col-span-2 space-y-5">
          {/* Score Overview */}
          <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-4">
              <div
                className="w-16 h-16 rounded-full flex items-center justify-center border-4"
                style={{ borderColor: getScoreColor(displayScore), backgroundColor: getScoreColor(displayScore) + '15' }}
              >
                <span className="text-xl font-bold" style={{ color: getScoreColor(displayScore) }}>{displayScore}</span>
              </div>
              <div>
                <p className="text-sm font-semibold text-white">{t('AI Evaluation Score', 'نقاط تقييم الذكاء الاصطناعي')}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {t('Based on campaign rules', 'بناءً على قواعد الحملة')}
                </p>
              </div>
              <div className="ml-auto text-right">
                <div className="flex items-center gap-1 text-xs">
                  {displayScore >= (campaign?.passThreshold || 75) ? (
                    <span className="flex items-center gap-1 text-green-400 bg-green-500/10 border border-green-500/20 px-2 py-1 rounded-lg">
                      <CheckCircle2 size={12} /> {t('PASS', 'نجاح')}
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-1 rounded-lg">
                      <XCircle size={12} /> {t('FAIL', 'فشل')}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-600 mt-1">{t('Threshold:', 'الحد الأدنى:')} {campaign?.passThreshold || 75}%</p>
              </div>
            </div>

            {/* AI Reasoning */}
            <div className="mt-4 pt-4 border-t border-slate-800/60">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles size={14} className="text-indigo-400" />
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('AI Reasoning', 'تفسير الذكاء الاصطناعي')}</h4>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed bg-slate-900/50 rounded-lg p-3 border border-slate-800/40">
                {call.reasoning || t('Reasoning will be available after evaluation.', 'سيكون التفسير متاحاً بعد التقييم.')}
              </p>
            </div>
          </div>

          {/* Strengths & Weaknesses */}
          <div className="bg-[#111827] border border-slate-800/60 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800/60">
              <div className="flex items-center gap-2">
                <Star size={15} className="text-amber-400" />
                <h3 className="text-sm font-semibold text-white">{t('Strengths & Weaknesses', 'نقاط القوة والضعف')}</h3>
              </div>
            </div>

            <div className="p-5 space-y-6">
              {/* Strengths */}
              <div>
                <p className="text-[10px] text-green-400 uppercase tracking-wider mb-3 font-semibold">{t('Key Strengths', 'نقاط القوة الرئيسية')}</p>
                <div className="space-y-2">
                  {call.strengths?.length ? call.strengths.map((s: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-slate-300">
                      <CheckCircle2 size={14} className="text-green-500 mt-0.5 flex-shrink-0" />
                      <span>{s}</span>
                    </div>
                  )) : <p className="text-xs text-slate-600">{t('No strengths noted.', 'لا توجد نقاط قوة مسجلة.')}</p>}
                </div>
              </div>

              {/* Weaknesses */}
              <div>
                <p className="text-[10px] text-red-400 uppercase tracking-wider mb-3 font-semibold">{t('Areas for Improvement', 'مجالات التحسين')}</p>
                <div className="space-y-3">
                  {call.weaknesses?.length ? call.weaknesses.map((w: any, i: number) => (
                    <div key={i} className="bg-red-500/5 border border-red-500/10 rounded-lg p-3">
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-xs font-bold text-red-400">{w.issue}</span>
                        <span className="text-[10px] bg-red-500/20 text-red-300 px-1.5 py-0.5 rounded">-{w.deduction} pts</span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed">{w.detail}</p>
                    </div>
                  )) : <p className="text-xs text-slate-600">{t('No critical weaknesses found.', 'لم يتم العثور على نقاط ضعف حرجة.')}</p>}
                </div>
              </div>
            </div>
          </div>

          {/* Supervisor Review */}
          <div className="bg-[#111827] border border-slate-800/60 rounded-xl overflow-hidden">
            <button
              onClick={() => setExpandedSection(expandedSection === 'review' ? null : 'review')}
              className="w-full flex items-center justify-between px-5 py-4 border-b border-slate-800/60 hover:bg-slate-800/20 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Shield size={15} className="text-purple-400" />
                <h3 className="text-sm font-semibold text-white">{t('Supervisor Review', 'مراجعة المشرف')}</h3>
                {call.reviewed_at && (
                  <span className="text-[10px] text-green-400 bg-green-500/10 border border-green-500/20 px-1.5 py-0.5 rounded-full">
                    {t('Reviewed', 'تمت المراجعة')}
                  </span>
                )}
              </div>
              {expandedSection === 'review' ? <ChevronUp size={15} className="text-slate-500" /> : <ChevronDown size={15} className="text-slate-500" />}
            </button>

            {expandedSection === 'review' && (
              <div className="p-5">
                {!overrideMode ? (
                  <div className="space-y-4">
                    {call.reviewer_notes ? (
                      <div>
                        <p className="text-xs text-slate-500 mb-1">{t('Supervisor Note:', 'ملاحظة المشرف:')}</p>
                        <p className="text-sm text-slate-300 bg-slate-800/30 border border-slate-700/30 rounded-lg p-3 leading-relaxed">
                          {call.reviewer_notes}
                        </p>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-600 text-center py-2">{t('No review submitted yet', 'لم يتم تقديم مراجعة بعد')}</p>
                    )}

                    {call.overridden_score !== null && (
                      <div className="flex items-center gap-3 p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                        <Shield size={14} className="text-purple-400" />
                        <div>
                          <p className="text-xs text-purple-400">{t('Score overridden:', 'تم تعديل النقاط:')}</p>
                          <p className="text-sm text-white">{call.evaluation_score}% → <span className="text-purple-400 font-bold">{call.overridden_score}%</span></p>
                        </div>
                      </div>
                    )}

                    <button
                      onClick={() => setOverrideMode(true)}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-purple-500/30 text-purple-400 hover:bg-purple-500/10 text-sm transition-colors"
                    >
                      <Edit3 size={14} />
                      {call.reviewed_at ? t('Edit Review', 'تعديل المراجعة') : t('Submit Review', 'تقديم مراجعة')}
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <label className="text-xs text-slate-500 mb-1.5 block">{t('Override Score (leave empty to keep AI score)', 'النقاط المعدلة (اتركه فارغاً للاحتفاظ بنقاط الذكاء الاصطناعي)')}</label>
                      <div className="flex items-center gap-3">
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={overrideScore}
                          onChange={e => setOverrideScore(e.target.value)}
                          placeholder={call.evaluation_score?.toString()}
                          className="w-24 bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-purple-500/50 transition-colors"
                        />
                        <span className="text-slate-600 text-sm">{t('/ 100', '/ 100')}</span>
                        <button
                          onClick={() => setOverrideScore(call.evaluation_score?.toString() || '')}
                          className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1"
                        >
                          <RotateCcw size={12} /> {t('Reset', 'إعادة تعيين')}
                        </button>
                      </div>
                    </div>

                    <div>
                      <label className="text-xs text-slate-500 mb-1.5 block">{t('Review Notes', 'ملاحظات المراجعة')}</label>
                      <textarea
                        value={overrideNote}
                        onChange={e => setOverrideNote(e.target.value)}
                        rows={4}
                        placeholder={t('Add your observations, coaching points, or override justification...', 'أضف ملاحظاتك ونقاط التدريب أو مبرر التعديل...')}
                        className="w-full bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-purple-500/50 resize-none transition-colors"
                      />
                    </div>

                    <div className="flex gap-3">
                      <button
                        onClick={() => setOverrideMode(false)}
                        className="flex-1 px-4 py-2 rounded-lg border border-slate-700/50 text-slate-400 hover:text-slate-200 text-sm transition-colors"
                      >
                        {t('Cancel', 'إلغاء')}
                      </button>
                      <button
                        onClick={handleSaveOverride}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium transition-colors"
                      >
                        <Save size={14} />
                        {t('Save Review', 'حفظ المراجعة')}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}