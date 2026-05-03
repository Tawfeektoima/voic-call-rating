import { useState, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router';
import {
  Plus, Radio, Pause, CheckCircle, Users, Phone, Target,
  Trash2, Settings, ChevronRight, TrendingUp, Zap, BookOpen,
  Search, Sliders, Save, X, Layout, FileText, Palette, Info,
  ChevronDown, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';
import { useApp } from '../context/AppContext';
import { useCampaigns, useCreateCampaign, useUpdateCampaign, useDeleteCampaign } from '../hooks/useCampaigns';
import { Campaign, CampaignType } from '../lib/types';
import { cn } from '../components/ui/utils';
import { Skeleton } from '../components/ui/skeleton';
import { GuardrailModal } from '../components/campaigns/GuardrailModal';

const typeConfig: Record<string, { icon: any; label: string; color: string; kpiHighlight: string }> = {
  sales: { icon: TrendingUp, label: 'Sales', color: '#6366f1', kpiHighlight: 'Conversion Rate' },
  customer_service: { icon: BookOpen, label: 'Customer Service', color: '#06b6d4', kpiHighlight: 'First Call Resolution' },
  technical: { icon: Zap, label: 'Technical', color: '#8b5cf6', kpiHighlight: 'Resolution Rate' },
  collections: { icon: Target, label: 'Collections', color: '#f59e0b', kpiHighlight: 'Promise-to-Pay Rate' },
};

const groqPrompts: Record<string, { name: string; focus: string[] }> = {
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

const templateTypes = [
  { type: 'sales', icon: TrendingUp, color: '#6366f1', label: 'Sales Campaign', sub: 'Outbound conversion & objection handling' },
  { type: 'customer_service', icon: BookOpen, color: '#06b6d4', label: 'Customer Service', sub: 'Support quality & FCR tracking' },
  { type: 'technical', icon: Zap, color: '#8b5cf6', label: 'Technical Support', sub: 'L1–L3 resolution & documentation' },
  { type: 'collections', icon: Target, color: '#f59e0b', label: 'Collections', sub: 'AR recovery with compliance scoring' },
];

const defaultPrompt = `Evaluate the call for empathy, professionalism, and problem resolution. 
Provide a score from 0-100.
List specific strengths and weaknesses with point deductions.`;

export function CampaignManager() {
  const navigate = useNavigate();
  const { userRole } = useApp();
  const isAdmin = userRole === 'admin';
  const editorRef = useRef<HTMLDivElement>(null);

  const { data: campaigns, isLoading } = useCampaigns();
  const createMutation = useCreateCampaign();
  const updateMutation = useUpdateCampaign();
  const deleteMutation = useDeleteCampaign();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Campaign | null>(null);
  const [showTemplateModal, setShowTemplateModal] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    type: 'customer_service' as CampaignType,
    color: '#06b6d4',
    evaluation_prompt: defaultPrompt,
    kpis: [] as string[]
  });

  const filteredCampaigns = useMemo(() => {
    if (!campaigns) return [];
    return campaigns.filter(c => 
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.description?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [campaigns, searchQuery]);

  const handleNewCampaign = () => {
    setSelectedCampaign(null);
    setIsCreating(true);
    setEditMode(true);
    setFormData({
      name: '',
      description: '',
      type: 'customer_service',
      color: '#6366f1',
      evaluation_prompt: defaultPrompt,
      kpis: groqPrompts.customer_service.focus
    });
    toast.success('Drafting new campaign...');
    
    // Mobile scroll
    if (window.innerWidth < 1024) {
      setTimeout(() => {
        editorRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  };

  const handleSelectTemplate = (template: typeof templateTypes[0]) => {
    setFormData({
      name: `${template.label} - ${new Date().toLocaleDateString()}`,
      description: template.sub,
      type: template.type as any,
      color: template.color,
      evaluation_prompt: defaultPrompt,
      kpis: groqPrompts[template.type]?.focus || []
    });
    setShowTemplateModal(false);
    setIsCreating(true);
    setEditMode(true);
    setSelectedCampaign(null);
    toast.info(`Template "${template.label}" applied`);
    
    if (window.innerWidth < 1024) {
      setTimeout(() => {
        editorRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  };

  const handleSave = () => {
    if (!formData.name || !formData.evaluation_prompt) return;

    if (isCreating) {
      createMutation.mutate({
        ...formData,
        status: 'active'
      }, {
        onSuccess: () => {
          setIsCreating(false);
          setEditMode(false);
          toast.success('Campaign created successfully');
        }
      });
    } else if (selectedCampaign && editMode) {
      updateMutation.mutate({
        id: selectedCampaign.id,
        data: {
          ...formData,
          status: selectedCampaign.status
        }
      }, {
        onSuccess: () => {
          setEditMode(false);
          toast.success('Campaign updated successfully');
        }
      });
    }
  };

  const isSaveDisabled = !formData.name || !formData.evaluation_prompt || createMutation.isPending || updateMutation.isPending;

  return (
    <div className="flex h-full overflow-hidden bg-background">
      {/* Left Column: List */}
      <div className="w-full lg:w-96 border-r border-border flex flex-col bg-card/50">
        <div className="p-4 border-b border-border space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-slate-100 font-semibold flex items-center gap-2">
              <Layout size={18} className="text-primary" />
              Campaigns
            </h2>
            {isAdmin && (
              <button 
                onClick={handleNewCampaign}
                className="size-8 flex items-center justify-center bg-primary hover:bg-indigo-400 text-white rounded-lg transition-colors"
              >
                <Plus size={18} />
              </button>
            )}
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={14} />
            <input 
              type="text"
              placeholder="Search campaigns..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-secondary border border-border rounded-xl pl-9 pr-4 py-2 text-sm text-foreground focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl bg-secondary" />)
          ) : filteredCampaigns.length > 0 ? (
            filteredCampaigns.map(c => {
              const typeC = typeConfig[c.type] || typeConfig.customer_service;
              const isActive = selectedCampaign?.id === c.id;
              return (
                <button
                  key={c.id}
                  onClick={() => {
                    setSelectedCampaign(c);
                    setIsCreating(false);
                    setEditMode(false);
                    setFormData({
                      name: c.name,
                      description: c.description || '',
                      type: c.type,
                      color: c.color,
                      evaluation_prompt: c.evaluation_prompt,
                      kpis: c.kpis || []
                    });
                  }}
                  className={cn(
                    "w-full p-3 rounded-xl border text-left transition-all group",
                    isActive 
                      ? "bg-primary/10 border-indigo-500/50" 
                      : "bg-card border-border hover:border-border"
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className="size-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ backgroundColor: c.color + '20' }}>
                      {(() => {
                        const Icon = typeC.icon;
                        return <Icon size={16} style={{ color: c.color }} />;
                      })()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h4 className={cn("text-sm font-medium truncate", isActive ? "text-indigo-300" : "text-foreground")}>{c.name}</h4>
                        <span className="text-[10px] text-muted-foreground">{c.total_calls} calls</span>
                      </div>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">{c.description || 'No description'}</p>
                    </div>
                  </div>
                </button>
              );
            })
          ) : (
            <div className="py-10 text-center">
              <p className="text-muted-foreground text-sm">No campaigns found</p>
            </div>
          )}
        </div>
      </div>

      {/* Right Column: Editor / Detail */}
      <div className="flex-1 overflow-y-auto bg-background" ref={editorRef}>
        {isCreating || (selectedCampaign && editMode) ? (
          <div className="max-w-3xl mx-auto p-6 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-300">
            {/* Form Header */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100">{isCreating ? 'Create New Campaign' : 'Edit Campaign'}</h2>
                <p className="text-muted-foreground text-sm mt-1">Configure your AI evaluation logic and metadata</p>
              </div>
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => { setIsCreating(false); setEditMode(false); }}
                  className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleSave}
                  disabled={isSaveDisabled}
                  className="flex items-center gap-2 px-6 py-2 bg-primary disabled:bg-secondary disabled:text-muted-foreground text-white rounded-xl text-sm font-semibold hover:bg-indigo-400 transition-all shadow-lg shadow-indigo-500/20"
                >
                  {createMutation.isPending ? 'Saving...' : <><Save size={16} /> Save Campaign</>}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Basic Info */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Campaign Name</label>
                  <input 
                    type="text"
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Q2 Outbound Sales"
                    className="w-full bg-card border border-border rounded-xl px-4 py-2.5 text-foreground focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Description</label>
                  <textarea 
                    value={formData.description}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Describe the purpose of this campaign..."
                    className="w-full bg-card border border-border rounded-xl px-4 py-2.5 text-foreground h-24 resize-none focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {/* Categorization */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Industry Type</label>
                  <div className="grid grid-cols-2 gap-2">
                    {templateTypes.map(t => (
                      <button
                        key={t.type}
                        onClick={() => setFormData({ ...formData, type: t.type as any, color: t.color })}
                        className={cn(
                          "flex items-center gap-2 p-3 rounded-xl border transition-all text-left",
                          formData.type === t.type 
                            ? "bg-secondary border-slate-600 ring-2 ring-indigo-500/20" 
                            : "bg-card border-border hover:border-border"
                        )}
                      >
                        {(() => {
                          const Icon = t.icon;
                          return <Icon size={14} style={{ color: t.color }} />;
                        })()}
                        <span className="text-xs font-medium text-foreground">{t.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Theme Color</label>
                  <div className="flex items-center gap-3 p-3 bg-card border border-border rounded-xl">
                    <input 
                      type="color"
                      value={formData.color}
                      onChange={e => setFormData({ ...formData, color: e.target.value })}
                      className="size-8 rounded cursor-pointer bg-transparent border-none"
                    />
                    <span className="text-xs text-muted-foreground font-mono">{formData.color}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Prompt Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Zap size={14} className="text-primary" />
                  Groq System Evaluation Prompt
                </label>
                <button 
                  onClick={() => setShowTemplateModal(true)}
                  className="text-xs text-primary hover:text-indigo-300 font-medium"
                >
                  Use Template
                </button>
              </div>
              <div className="relative group">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500/20 to-violet-500/20 rounded-2xl blur opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200"></div>
                <textarea 
                  value={formData.evaluation_prompt}
                  onChange={e => setFormData({ ...formData, evaluation_prompt: e.target.value })}
                  className="relative w-full bg-card border border-border rounded-2xl px-5 py-4 text-foreground h-64 font-mono text-sm leading-relaxed focus:outline-none focus:border-indigo-500/50 transition-colors"
                />
              </div>
              <div className="flex items-start gap-2 p-3 bg-primary/5 border border-indigo-500/10 rounded-xl">
                <Info size={14} className="text-primary mt-0.5" />
                <p className="text-[11px] text-muted-foreground leading-normal">
                  This prompt defines how the AI evaluates calls. You can use variables like <span className="text-indigo-300">{"{transcript}"}</span> to customize the analysis context.
                </p>
              </div>
            </div>
          </div>
        ) : selectedCampaign ? (
          <div className="max-w-4xl mx-auto p-8 space-y-8 animate-in fade-in duration-300">
            {/* Detail View Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className="size-16 rounded-2xl flex items-center justify-center text-3xl" style={{ backgroundColor: selectedCampaign.color + '15' }}>
                  {(() => {
                    const DetailIcon = typeConfig[selectedCampaign.type]?.icon;
                    return DetailIcon ? <DetailIcon size={32} style={{ color: selectedCampaign.color }} /> : null;
                  })()}
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-slate-100">{selectedCampaign.name}</h1>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-muted-foreground uppercase tracking-widest">{selectedCampaign.type}</span>
                    <span className="text-slate-800">|</span>
                    <span className="text-xs text-emerald-400 flex items-center gap-1">
                      <div className="size-1.5 bg-emerald-400 rounded-full animate-pulse" />
                      Active Campaign
                    </span>
                  </div>
                </div>
              </div>
              {isAdmin && (
                <div className="flex items-center gap-2">
                  <button 
                    onClick={() => setEditMode(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-slate-700 text-foreground rounded-xl text-sm transition-all"
                  >
                    <Settings size={16} /> Edit
                  </button>
                  <button 
                    onClick={() => setDeleteTarget(selectedCampaign)}
                    className="size-10 flex items-center justify-center bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-xl transition-all"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              )}
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[
                { label: 'Total Calls', value: selectedCampaign.total_calls, icon: Phone, color: 'indigo' },
                { label: 'Avg Score', value: `${selectedCampaign.avg_score.toFixed(1)}%`, icon: Target, color: 'emerald' },
                { label: 'Agent Count', value: selectedCampaign.agent_count, icon: Users, color: 'cyan' },
                { label: 'QA Progress', value: '88%', icon: TrendingUp, color: 'violet' },
              ].map(stat => (
                <div key={stat.label} className="bg-card border border-border rounded-2xl p-4">
                  <p className="text-muted-foreground text-[10px] font-semibold uppercase tracking-wider mb-1">{stat.label}</p>
                  <div className="flex items-end justify-between">
                    <p className="text-xl font-bold text-slate-100">{stat.value}</p>
                    <stat.icon size={18} className="text-slate-700" />
                  </div>
                </div>
              ))}
            </div>

            {/* Content Sections */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2 space-y-6">
                <div className="bg-card border border-border rounded-2xl overflow-hidden">
                  <div className="px-5 py-3 border-b border-border flex items-center gap-2">
                    <FileText size={14} className="text-primary" />
                    <h3 className="text-foreground text-sm font-semibold">System Prompt</h3>
                  </div>
                  <div className="p-5">
                    <pre className="text-xs text-muted-foreground leading-relaxed font-mono whitespace-pre-wrap">
                      {selectedCampaign.evaluation_prompt}
                    </pre>
                  </div>
                </div>
              </div>
              <div className="space-y-6">
                <div className="bg-card border border-border rounded-2xl p-5">
                  <h3 className="text-foreground text-sm font-semibold mb-4">Tracked KPIs</h3>
                  <div className="space-y-3">
                    {selectedCampaign.kpis?.map(kpi => (
                      <div key={kpi} className="flex items-center gap-3">
                        <div className="size-1.5 bg-primary rounded-full" />
                        <span className="text-xs text-muted-foreground">{kpi}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <button 
                  onClick={() => navigate('/calls', { state: { campaignId: selectedCampaign.id } })}
                  className="w-full flex items-center justify-center gap-2 py-3 bg-primary hover:bg-indigo-400 text-white rounded-2xl text-sm font-semibold transition-all shadow-lg shadow-indigo-500/20"
                >
                  Analyze Calls <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4">
            <div className="size-20 bg-card rounded-full flex items-center justify-center text-slate-700">
              <Layout size={40} />
            </div>
            <div>
              <h3 className="text-foreground font-semibold">Select a Campaign</h3>
              <p className="text-muted-foreground text-sm max-w-xs mt-1">Choose a campaign from the list or create a new one to manage evaluation prompts.</p>
            </div>
            {isAdmin && (
              <button 
                onClick={handleNewCampaign}
                className="px-6 py-2 bg-primary/15 hover:bg-primary/25 text-primary border border-indigo-500/30 rounded-xl text-sm font-medium transition-all"
              >
                Start New Campaign
              </button>
            )}
          </div>
        )}
      </div>

      {/* Template Selection Modal */}
      {showTemplateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setShowTemplateModal(false)} />
          <div className="relative bg-card border border-border rounded-3xl w-full max-w-2xl shadow-2xl overflow-hidden">
            <div className="px-8 py-6 border-b border-border">
              <h2 className="text-xl font-bold text-slate-100">Select Campaign Template</h2>
              <p className="text-muted-foreground text-sm mt-1">Starting from a template auto-configures the Groq evaluation logic.</p>
            </div>
            <div className="p-8 grid grid-cols-2 gap-4">
              {templateTypes.map(t => (
                <button
                  key={t.type}
                  onClick={() => handleSelectTemplate(t)}
                  className="flex flex-col gap-4 p-5 bg-secondary/30 hover:bg-secondary/60 border border-border hover:border-border rounded-2xl text-left transition-all group"
                >
                  <div className="size-12 rounded-xl flex items-center justify-center" style={{ backgroundColor: t.color + '15' }}>
                    {(() => {
                      const Icon = t.icon;
                      return <Icon size={24} style={{ color: t.color }} />;
                    })()}
                  </div>
                  <div>
                    <p className="text-foreground font-semibold group-hover:text-indigo-300 transition-colors">{t.label}</p>
                    <p className="text-muted-foreground text-xs mt-1 leading-relaxed">{t.sub}</p>
                  </div>
                </button>
              ))}
            </div>
            <div className="px-8 py-4 bg-secondary/50 border-t border-border flex justify-end">
              <button onClick={() => setShowTemplateModal(false)} className="px-6 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <GuardrailModal
          campaign={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onConfirmDelete={async () => {
            await deleteMutation.mutateAsync(deleteTarget.id);
            setDeleteTarget(null);
            setSelectedCampaign(null);
            toast.error('Campaign deleted permanently');
          }}
        />
      )}
    </div>
  );
}
