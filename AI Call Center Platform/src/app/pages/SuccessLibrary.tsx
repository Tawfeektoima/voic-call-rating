import { useState, useRef } from 'react';
import { Play, Pause, Star, Tag, Clock, BookOpen, TrendingUp, Zap, Target, Search, Filter } from 'lucide-react';
import { useGoldenMoments } from '../hooks/useGoldenMoments';
import { useCampaigns } from '../hooks/useCampaigns';
import { Call, Campaign } from '../lib/types';
import { useNavigate } from 'react-router';
import { cn } from '../components/ui/utils';
import { Skeleton } from '../components/ui/skeleton';

const typeConfig: Record<string, { color: string; icon: any; label: string }> = {
  sales: { color: '#6366f1', icon: TrendingUp, label: 'Sales' },
  customer_service: { color: '#06b6d4', icon: BookOpen, label: 'CS' },
  technical: { color: '#8b5cf6', icon: Zap, label: 'Tech' },
  collections: { color: '#f59e0b', icon: Target, label: 'Collections' },
};

const tagColors = [
  'bg-primary/10 text-primary border-indigo-500/20',
  'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  'bg-violet-500/10 text-violet-400 border-violet-500/20',
  'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  'bg-amber-500/10 text-amber-400 border-amber-500/20',
];

function WaveformPreview({ color }: { color: string }) {
  const bars = Array.from({ length: 32 }, (_, i) => ({
    h: Math.random() * 0.7 + 0.15,
  }));
  return (
    <div className="flex items-center gap-0.5 h-8">
      {bars.map((bar, i) => (
        <div
          key={i}
          className="w-0.5 rounded-full opacity-60"
          style={{ height: `${bar.h * 100}%`, backgroundColor: color }}
        />
      ))}
    </div>
  );
}

function MomentCard({ moment, campaign, isPlaying, onPlay }: {
  moment: Call;
  campaign?: Campaign;
  isPlaying: boolean;
  onPlay: () => void;
}) {
  const navigate = useNavigate();
  const tc = typeConfig[campaign?.type || 'customer_service'] || typeConfig.customer_service;
  const score = moment.overridden_score ?? moment.evaluation_score ?? 0;
  const scoreColor = score >= 90 ? '#10b981' : score >= 80 ? '#f59e0b' : '#ef4444';

  return (
    <div className={cn(
      'bg-card border rounded-2xl overflow-hidden transition-all duration-200 cursor-pointer group',
      isPlaying ? 'border-indigo-500/40 ring-1 ring-indigo-500/20' : 'border-border hover:border-border'
    )}
    onClick={() => navigate(`/calls/${moment.id}`)}
    >
      {/* Color header */}
      <div className="h-0.5" style={{ backgroundColor: tc.color }} />

      {/* Thumbnail / Waveform area */}
      <div
        className="relative h-24 flex items-center justify-center px-4"
        style={{ backgroundColor: tc.color + '08' }}
        onClick={onPlay}
      >
        <div className="absolute inset-0 flex items-center px-4">
          <WaveformPreview color={tc.color} />
        </div>

        {/* Play button overlay */}
        <div className={cn(
          'relative z-10 size-12 rounded-full flex items-center justify-center transition-all shadow-lg',
          isPlaying
            ? 'bg-primary shadow-indigo-500/30'
            : 'bg-card/90 backdrop-blur group-hover:bg-primary group-hover:shadow-indigo-500/30 border border-border group-hover:border-transparent'
        )}
        onClick={(e) => { e.stopPropagation(); onPlay(); }}
        >
          {isPlaying
            ? <Pause size={18} className="text-white" />
            : <Play size={18} className="text-foreground group-hover:text-white ml-0.5" />
          }
        </div>

        {/* Duration badge */}
        <div className="absolute bottom-2 right-3 flex items-center gap-1 bg-black/40 backdrop-blur rounded px-1.5 py-0.5">
          <Clock size={9} className="text-muted-foreground" />
          <span className="text-xs text-foreground">{Math.floor(moment.audio_duration || 0)}s</span>
        </div>

        {/* Type badge */}
        <div className="absolute top-2 left-3">
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full" style={{ backgroundColor: tc.color + '20' }}>
            <tc.icon size={10} style={{ color: tc.color }} />
            <span className="text-xs" style={{ color: tc.color }}>{tc.label}</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-slate-100 text-xs font-semibold leading-relaxed line-clamp-2">
            {moment.strengths?.[0] || `Exceptional ${tc.label} Interaction`}
          </h3>
          <div
            className="size-7 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0"
            style={{ backgroundColor: scoreColor + '15', color: scoreColor }}
          >
            {score}
          </div>
        </div>

        <p className="text-muted-foreground text-xs leading-relaxed mb-3 line-clamp-2">{moment.call_summary || 'No summary available'}</p>

        {/* Transcript preview */}
        <div className="bg-secondary/60 rounded-lg p-2.5 mb-3 border border-border">
          <p className="text-muted-foreground text-xs leading-relaxed italic line-clamp-3">
            {moment.transcript?.slice(0, 150) || 'Call recording available for review...'}...
          </p>
        </div>

        {/* Agent & date */}
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-muted-foreground">Agent #{moment.employee_id}</p>
          <p className="text-xs text-muted-foreground">{new Date(moment.created_at).toLocaleDateString()}</p>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5">
          {(moment.tags || []).slice(0, 3).map((tag, i) => (
            <span key={tag} className={cn('text-xs px-1.5 py-0.5 rounded-full border', tagColors[i % tagColors.length])}>
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function SuccessLibrary() {
  const [playingId, setPlayingId] = useState<number | null>(null);
  const [filterType, setFilterType] = useState<string | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: goldenMoments, isLoading: momentsLoading } = useGoldenMoments();
  const { data: campaigns } = useCampaigns();

  const campaignMap = (campaigns || []).reduce((acc, c) => {
    acc[c.id] = c;
    return acc;
  }, {} as Record<number, Campaign>);

  const filteredMoments = (goldenMoments || []).filter(m => {
    const campaign = campaignMap[m.campaign_id];
    const matchType = filterType === 'all' || campaign?.type === filterType;
    const matchSearch = !searchQuery || 
      (m.strengths?.[0] || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (m.call_summary || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchType && matchSearch;
  });

  const handlePlay = (id: number) => {
    setPlayingId(prev => prev === id ? null : id);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Star size={18} className="text-amber-400" />
            <p className="text-muted-foreground text-xs">{(goldenMoments || []).length} curated moments · Success Assets</p>
          </div>
          <p className="text-muted-foreground text-xs">Golden clips extracted by AI for agent coaching and onboarding</p>
        </div>
      </div>

      {/* Search + Filter Bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search moments, agents, tags..."
            className="w-full bg-secondary border border-border rounded-xl pl-9 pr-4 py-2 text-sm text-foreground placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>

        {/* Type filter */}
        <div className="flex items-center gap-2 bg-card border border-border rounded-xl p-1">
          {(['all', 'sales', 'customer_service', 'technical', 'collections'] as const).map(type => {
            const tc = type !== 'all' ? typeConfig[type] : null;
            return (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs transition-all capitalize',
                  filterType === type ? 'bg-primary/20 text-indigo-300' : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {type === 'all' ? 'All' : type === 'customer_service' ? 'CS' : type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            );
          })}
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-6 px-4 py-3 bg-card border border-border rounded-xl">
        {(['sales', 'customer_service', 'technical', 'collections'] as const).map(type => {
          const count = (goldenMoments || []).filter(m => campaignMap[m.campaign_id]?.type === type).length;
          const tc = typeConfig[type];
          return (
            <div key={type} className="flex items-center gap-2">
              <tc.icon size={13} style={{ color: tc.color }} />
              <span className="text-xs text-muted-foreground">{tc.label}</span>
              <span className="text-xs text-foreground font-semibold">{count}</span>
            </div>
          );
        })}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Showing</span>
          <span className="text-xs text-foreground font-semibold">{filteredMoments.length}</span>
          <span className="text-xs text-muted-foreground">clips</span>
        </div>
      </div>

      {/* Grid */}
      {momentsLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-96 rounded-2xl bg-secondary" />)}
        </div>
      ) : filteredMoments.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-3 gap-5">
          {filteredMoments.map(moment => (
            <MomentCard
              key={moment.id}
              moment={moment}
              campaign={campaignMap[moment.campaign_id]}
              isPlaying={playingId === moment.id}
              onPlay={() => handlePlay(moment.id)}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Star size={40} className="text-slate-700 mb-4" />
          <p className="text-muted-foreground text-sm font-medium">No moments found</p>
          <p className="text-muted-foreground text-xs mt-1">Try adjusting your search or filter</p>
        </div>
      )}
    </div>
  );
}
