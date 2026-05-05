import { useState, useRef, useEffect } from 'react';
import { Search, Shield, Mic, User, ChevronRight } from 'lucide-react';
import { TranscriptSegment } from '../../lib/types';
import { useApp } from '../../context/AppContext';
import { cn } from '../ui/utils';

interface Props {
  transcript: TranscriptSegment[];
  currentTime: number;
  onSeek: (time: number) => void;
  agentName?: string;
}

const emotionColors = {
  calm: { bg: 'bg-emerald-500/8', border: 'border-emerald-500/20', text: 'text-emerald-400' },
  stress: { bg: 'bg-amber-500/8', border: 'border-amber-500/20', text: 'text-amber-400' },
  agitation: { bg: 'bg-red-500/8', border: 'border-red-500/20', text: 'text-red-400' },
};

const isAgentSpeaker = (speaker: string): boolean => {
  const s = speaker?.toLowerCase() ?? ""
  return s === "agent" || s === "speaker_00"
}

function highlightText(text: string, query: string) {
  if (!query.trim()) return [{ text, highlight: false }];
  const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
  return parts.map(p => ({ text: p, highlight: p.toLowerCase() === query.toLowerCase() }));
}

const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

export function InteractiveTranscript({ transcript, currentTime, onSeek, agentName }: Props) {
  const { piiMaskingEnabled } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeId, setActiveId] = useState<string | null>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  const segments: TranscriptSegment[] = Array.isArray(transcript) 
    ? transcript 
    : (() => {
        if (typeof transcript === 'string') {
          try {
            const parsed = JSON.parse(transcript);
            return Array.isArray(parsed) ? parsed : [];
          } catch {
            return [];
          }
        }
        return [];
      })();

  useEffect(() => {
    const current = segments.find(s => currentTime >= s.start && currentTime < s.end);
    if (current && current.id !== activeId) {
      setActiveId(current.id);
    }
  }, [currentTime, segments, activeId]);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [activeId]);

  const filteredSegments = searchQuery
    ? segments.filter(s => {
        const text = (piiMaskingEnabled && s.redactedText) ? s.redactedText : s.text;
        return text.toLowerCase().includes(searchQuery.toLowerCase());
      })
    : segments;

  const searchResultCount = filteredSegments.length;

  return (
    <div className="bg-card border border-border rounded-xl flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
        <span className="text-foreground text-sm font-semibold flex-1">Interactive Transcript</span>

        {/* PII indicator */}
        <div className={cn(
          'flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs',
          piiMaskingEnabled ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
        )}>
          <Shield size={11} />
          {piiMaskingEnabled ? 'PII Masked' : 'PII Visible'}
        </div>

        <span className="text-xs text-muted-foreground">{segments.length} segments</span>
      </div>

      {/* Search */}
      <div className="px-4 py-2 border-b border-border">
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Semantic search within transcript..."
            className="w-full bg-secondary border border-border rounded-lg pl-8 pr-4 py-1.5 text-xs text-foreground placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          {searchQuery && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
              {searchResultCount} results
            </span>
          )}
        </div>
      </div>

      {/* Segments */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {filteredSegments.length === 0 ? (
           <div className="h-full flex items-center justify-center text-muted-foreground text-xs italic">
             No segments match your search
           </div>
        ) : filteredSegments.map(segment => {
          const isActive = segment.id === activeId;
          const text = (piiMaskingEnabled && segment.redactedText) ? segment.redactedText : segment.text;
          const parts = highlightText(text, searchQuery);
          const ec = (emotionColors as any)[segment.emotion] || emotionColors.calm;

          const isAgent = isAgentSpeaker(segment.speaker);

          return (
            <div
              key={segment.id}
              ref={isActive ? activeRef : undefined}
              onClick={() => onSeek(segment.start)}
              className={cn(
                'flex gap-3 p-3 rounded-xl border cursor-pointer transition-all duration-200 group',
                isActive
                  ? `${ec.bg} ${ec.border} ring-1 ring-inset ${ec.border}`
                  : 'bg-secondary/40 border-border hover:bg-secondary/70 hover:border-border'
              )}
            >
              {/* Speaker icon */}
              <div className="flex-shrink-0 flex flex-col items-center gap-1 pt-0.5">
                <div className={cn(
                  'size-6 rounded-full flex items-center justify-center',
                  isAgent ? 'bg-primary/20' : 'bg-cyan-500/20'
                )}>
                  {isAgent
                    ? <Mic size={11} className="text-primary" />
                    : <User size={11} className="text-cyan-400" />
                  }
                </div>
                <ChevronRight size={10} className={cn('opacity-0 group-hover:opacity-100 transition-opacity', ec.text)} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn('text-xs font-medium', isAgent ? 'text-primary' : 'text-cyan-400')}>
                    {isAgent ? (agentName || 'Agent') : 'Customer'}
                  </span>
                  <span className="text-xs text-muted-foreground">{formatTime(segment.start)} – {formatTime(segment.end)}</span>
                  <span className={cn('text-xs px-1.5 py-0.5 rounded-full capitalize ml-auto', ec.bg, ec.text)}>
                    {segment.emotion}
                  </span>
                  {segment.hasPII && (
                    <span className={cn(
                      'text-xs px-1.5 py-0.5 rounded-full flex items-center gap-1',
                      piiMaskingEnabled ? 'bg-muted text-muted-foreground' : 'bg-orange-500/15 text-orange-400'
                    )}>
                      <Shield size={9} />
                      {piiMaskingEnabled ? 'Redacted' : 'PII'}
                    </span>
                  )}
                </div>

                <p className="text-sm text-foreground leading-relaxed">
                  {parts.map((part, i) =>
                    part.highlight ? (
                      <mark key={i} className="bg-primary/30 text-indigo-300 rounded px-0.5">{part.text}</mark>
                    ) : (
                      <span key={i}>{part.text}</span>
                    )
                  )}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
