import { useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Plus, Radio, Pause, CheckCircle, Users, Phone, Target,
  Trash2, Settings, ChevronRight, TrendingUp, Zap, BookOpen
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useCampaigns, useCreateCampaign, useDeleteCampaign } from '../hooks/useCampaigns';
import { Campaign } from '../lib/types';
import { cn } from '../components/ui/utils';
import { Skeleton } from '../components/ui/skeleton';

const typeConfig: Record<string, { icon: any; label: string; color: string; kpiHighlight: string }> = {
  sales: { icon: TrendingUp, label: 'Sales', color: 'indigo', kpiHighlight: 'Conversion Rate' },
  customer_service: { icon: BookOpen, label: 'Customer Service', color: 'cyan', kpiHighlight: 'First Call Resolution' },
  technical: { icon: Zap, label: 'Technical', color: 'violet', kpiHighlight: 'Resolution Rate' },
  collections: { icon: Target, label: 'Collections', color: 'amber', kpiHighlight: 'Promise-to-Pay Rate' },
};

const statusConfig = {
  active: { icon: Radio, label: 'Active', colorClass: 'text-emerald-400' },
  paused: { icon: Pause, label: 'Paused', colorClass: 'text-amber-400' },
  completed: { icon: CheckCircle, label: 'Completed', colorClass: 'text-blue-400' },
};

const groqPrompts: Record<CampaignType, { name: string; focus: string[] }> = {
  sales: {
    name: 'Sales Intelligence Prompt',
    focus: ['Objection detection & categorization', 'Buying signal identification', 'Competitor mention extraction', 'Next-step commitment tracking', 'Value proposition delivery scoring'],
  },
  customer_service: {
    name: 'Support Resolution Prompt',
    focus: ['Root cause identification', 'Resolution step verification', 'Empathy language scoring', 'Escalation trigger detection', 'CSAT prediction signals'],
  },
  technical: {
    name: 'Technical Diagnostic Prompt',
    focus: ['Error code extraction', 'Resolution path documentation', 'Escalation trigger detection', 'Technical accuracy scoring', 'Documentation quality assessment'],
  },
  collections: {
    name: 'Collections Compliance Prompt',
    focus: ['Payment commitment extraction', 'Hardship disclosure tracking', 'FDCPA compliance verification', 'Dispute flag detection', 'Settlement offer tracking'],
  },
};

const defaultPrompt = `Evaluate the call for empathy, professionalism, and problem resolution. 
Provide a score from 0-100.
List specific strengths and weaknesses with point deductions.`;

function CampaignCard({ campaign, onDelete }: { campaign: Campaign; onDelete: (c: Campaign) => void }) {
  const navigate = useNavigate();
  const { userRole } = useApp();
  const isAdmin = userRole === 'admin';
  const typeC = typeConfig[campaign.type] || typeConfig.customer_service;
  const statusC = (statusConfig as any)[campaign.status] || statusConfig.active;
  const groq = groqPrompts[campaign.type] || groqPrompts.customer_service;

  const scoreColor = campaign.avg_score >= 80 ? '#10b981' : campaign.avg_score >= 70 ? '#f59e0b' : '#ef4444';

  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden hover:border-border transition-all group">
      {/* Color bar */}
      <div className="h-1" style={{ backgroundColor: campaign.color }} />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start gap-3 mb-4">
          <div className="size-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: campaign.color + '20' }}>
            <typeC.icon size={20} style={{ color: campaign.color }} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-slate-100 text-sm font-semibold truncate">{campaign.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-muted-foreground capitalize">{typeC.label}</span>
              <span className="text-slate-700">·</span>
              <span className={cn('flex items-center gap-1 text-xs', statusC.colorClass)}>
                <statusC.icon size={10} />
                {statusC.label}
              </span>
            </div>
          </div>
          <div
            className="size-10 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0"
            style={{ backgroundColor: scoreColor + '15', color: scoreColor }}
          >
            {campaign.avgScore.toFixed(0)}
          </div>
        </div>

        <p className="text-xs text-muted-foreground mb-4 leading-relaxed">{campaign.description}</p>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="bg-secondary/50 rounded-lg p-2.5 text-center">
            <p className="text-foreground text-sm font-semibold">{campaign.total_calls.toLocaleString()}</p>
            <p className="text-muted-foreground text-xs">Calls</p>
          </div>
          <div className="bg-secondary/50 rounded-lg p-2.5 text-center">
            <p className="text-foreground text-sm font-semibold">{campaign.agent_count}</p>
            <p className="text-muted-foreground text-xs">Agents</p>
          </div>
          <div className="bg-secondary/50 rounded-lg p-2.5 text-center">
            <p className="text-sm font-semibold" style={{ color: scoreColor }}>{campaign.avg_score.toFixed(1)}</p>
            <p className="text-muted-foreground text-xs">Avg Score</p>
          </div>
        </div>

        {/* KPIs */}
        <div className="mb-4">
          <p className="text-xs text-muted-foreground mb-2">Tracked KPIs</p>
          <div className="flex flex-wrap gap-1.5">
            {campaign.kpis && campaign.kpis.length > 0 ? (
              campaign.kpis.map(kpi => (
                <span key={kpi} className="text-xs px-2 py-0.5 bg-secondary text-muted-foreground rounded-full border border-border">
                  {kpi}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-700">Default evaluation</span>
            )}
          </div>
        </div>

        {/* Groq prompt */}
        <div className="bg-secondary/40 rounded-xl p-3 mb-4 border border-border">
          <div className="flex items-center gap-2 mb-2">
            <div className="size-4 rounded bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center">
              <Zap size={9} className="text-white" />
            </div>
            <span className="text-xs text-primary font-medium">{groq.name}</span>
          </div>
          <ul className="space-y-1">
            {groq.focus.slice(0, 3).map(f => (
              <li key={f} className="text-xs text-muted-foreground flex items-start gap-1.5">
                <span className="text-primary mt-0.5">›</span>
                {f}
              </li>
            ))}
          </ul>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/calls/call1')}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-primary/10 hover:bg-primary/20 text-primary border border-indigo-500/20 rounded-xl text-xs transition-all"
          >
            View Calls <ChevronRight size={12} />
          </button>
          {isAdmin && (
            <button
              className="size-8 flex items-center justify-center bg-secondary hover:bg-slate-700 text-muted-foreground rounded-xl transition-all"
            >
              <Settings size={14} />
            </button>
          )}
          {isAdmin && (
            <button
              onClick={() => onDelete(campaign)}
              className="size-8 flex items-center justify-center bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-xl transition-all"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const templateTypes = [
  { type: 'sales', icon: TrendingUp, color: '#6366f1', label: 'Sales Campaign', sub: 'Outbound conversion & objection handling' },
  { type: 'customer_service', icon: BookOpen, color: '#06b6d4', label: 'Customer Service', sub: 'Support quality & FCR tracking' },
  { type: 'technical', icon: Zap, color: '#8b5cf6', label: 'Technical Support', sub: 'L1–L3 resolution & documentation' },
  { type: 'collections', icon: Target, color: '#f59e0b', label: 'Collections', sub: 'AR recovery with compliance scoring' },
];

export function Campaigns() {
  const { data: campaigns, isLoading } = useCampaigns();
  const createMutation = useCreateCampaign();
  const deleteMutation = useDeleteCampaign();
  
  const [deleteTarget, setDeleteTarget] = useState<Campaign | null>(null);
  const [showNewCampaign, setShowNewCampaign] = useState(false);
  const { userRole } = useApp();
  const isAdmin = userRole === 'admin';

  const handleCreate = async (template: typeof templateTypes[0]) => {
    createMutation.mutate({
      name: `${template.label} - ${new Date().toLocaleDateString()}`,
      description: template.sub,
      type: template.type as any,
      status: 'active',
      color: template.color,
      kpis: groqPrompts[template.type as any]?.focus || [],
      evaluation_prompt: defaultPrompt
    }, {
      onSuccess: () => {
        setShowNewCampaign(false);
      }
    });
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    deleteMutation.mutate(deleteTarget.id, {
      onSuccess: () => {
        setDeleteTarget(null);
      }
    });
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-muted-foreground text-xs">Manage and monitor your AI-powered campaign workflows</p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowNewCampaign(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary/15 hover:bg-primary/25 text-indigo-300 border border-indigo-500/30 rounded-xl text-sm transition-all"
          >
            <Plus size={16} />
            New Campaign
          </button>
        )}
      </div>

      {/* Campaign Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-5">
        {isLoading ? (
          Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-96 rounded-2xl bg-secondary" />)
        ) : campaigns && campaigns.length > 0 ? (
          campaigns.map(c => (
            <CampaignCard key={c.id} campaign={c} onDelete={setDeleteTarget} />
          ))
        ) : (
          <div className="col-span-full py-20 text-center border border-dashed border-border rounded-2xl">
            <p className="text-muted-foreground text-sm">No campaigns found. Create your first one to start evaluating calls.</p>
          </div>
        )}
      </div>

      {/* New Campaign Templates Modal */}
      {showNewCampaign && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setShowNewCampaign(false)} />
          <div className="relative bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="px-6 py-4 border-b border-border">
              <h2 className="text-slate-100 text-sm font-semibold">Create New Campaign</h2>
              <p className="text-muted-foreground text-xs mt-1">Select a campaign template with pre-configured Groq system prompts and KPI tracking.</p>
            </div>
            <div className="p-5 grid grid-cols-2 gap-3">
              {templateTypes.map(t => (
                <button
                  key={t.type}
                  onClick={() => handleCreate(t)}
                  className="flex flex-col gap-3 p-4 bg-secondary/50 hover:bg-secondary border border-border hover:border-slate-600 rounded-xl text-left transition-all"
                >
                  <div className="size-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: t.color + '20' }}>
                    <t.icon size={18} style={{ color: t.color }} />
                  </div>
                  <div>
                    <p className="text-foreground text-xs font-medium">{t.label}</p>
                    <p className="text-muted-foreground text-xs mt-0.5">{t.sub}</p>
                  </div>
                </button>
              ))}
            </div>
            <div className="px-6 py-4 border-t border-border">
              <button onClick={() => setShowNewCampaign(false)} className="w-full py-2 bg-secondary hover:bg-slate-700 text-foreground rounded-xl text-sm transition-all">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Guardrail Delete Modal */}
      {deleteTarget && (
        <GuardrailModal
          campaign={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onConfirmDelete={handleDelete}
        />
      )}
    </div>
  );
}