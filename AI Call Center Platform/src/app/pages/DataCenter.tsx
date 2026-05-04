import { useState } from 'react';
import {
  Download, FileJson, FileSpreadsheet, Archive, Filter,
  Database, Cpu, BarChart3, Shield, CheckCircle, Loader2,
  Calendar, Tag, ChevronDown, Info
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useDashboard } from '../hooks/useDashboard';
import { useCampaigns } from '../hooks/useCampaigns';
import api from '../lib/api';
import { cn } from '../components/ui/utils';

type ExportFormat = 'json' | 'csv' | 'zip';
type ExportType = 'transcripts' | 'master_sheet' | 'golden_moments' | 'agent_metrics';

interface ExportConfig {
  type: ExportType;
  format: ExportFormat;
  campaigns: string[];
  dateRange: string;
  includePII: boolean;
}

const exportTypes = [
  {
    id: 'transcripts' as ExportType,
    icon: FileJson,
    color: 'indigo',
    label: 'Bulk Transcript Export',
    sub: 'Full call transcripts with emotion tags for LLM fine-tuning',
    formats: ['zip'] as ExportFormat[],
    size: 'Variable',
    records: 'Campaign-wide',
  },
  {
    id: 'master_sheet' as ExportType,
    icon: FileSpreadsheet,
    color: 'emerald',
    label: 'CSV Master Sheet',
    sub: 'Acoustic + semantic + business metadata for Power BI / Excel',
    formats: ['csv'] as ExportFormat[],
    size: 'Auto',
    records: 'All calls',
  },
];

const csvFields = [
  { category: 'Acoustic', fields: ['Call Duration (s)', 'Agent Talk Time', 'Customer Talk Time', 'Talk Ratio', 'Silence Ratio', 'Avg Decibel Level', 'Emotion Distribution'] },
  { category: 'Semantic', fields: ['QA Score', 'Objection Count', 'Sentiment Score', 'Key Topics', 'Compliance Flags', 'PII Segments Count'] },
  { category: 'Business', fields: ['Lead Status', 'Campaign Type', 'Primary Outcome', 'Outcome Value', 'Follow-up Required', 'Follow-up Date'] },
  { category: 'Metadata', fields: ['Call ID', 'Timestamp', 'Campaign ID', 'Agent ID', 'Is Golden Moment', 'Tags', 'Campaign Specific Data'] },
];

function ExportCard({ config, onExport, isExporting }: {
  config: typeof exportTypes[0];
  onExport: () => void;
  isExporting: boolean;
}) {
  const colorMap: Record<string, string> = { indigo: '#6366f1', emerald: '#10b981', amber: '#f59e0b', cyan: '#06b6d4' };
  const col = colorMap[config.color];

  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="h-0.5" style={{ backgroundColor: col }} />
      <div className="p-5">
        <div className="flex items-start gap-4">
          <div className="size-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: col + '15' }}>
            <config.icon size={20} style={{ color: col }} />
          </div>
          <div className="flex-1">
            <h3 className="text-slate-100 text-sm font-semibold">{config.label}</h3>
            <p className="text-muted-foreground text-xs mt-1 leading-relaxed">{config.sub}</p>
          </div>
        </div>

        <div className="flex items-center gap-4 mt-4 text-xs text-muted-foreground">
          <span><span className="text-foreground font-medium">{config.records}</span> records</span>
          <span><span className="text-foreground font-medium">{config.size}</span> estimated</span>
          <span>Formats: {config.formats.map(f => <code key={f} className="ml-1 px-1 bg-secondary rounded text-muted-foreground">.{f}</code>)}</span>
        </div>

        <button
          onClick={onExport}
          disabled={isExporting}
          className={cn(
            'w-full mt-4 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all',
            isExporting
              ? 'bg-secondary text-muted-foreground cursor-not-allowed'
              : 'text-white hover:opacity-90'
          )}
          style={!isExporting ? { backgroundColor: col + 'cc' } : {}}
        >
          {isExporting ? (
            <><Loader2 size={14} className="animate-spin" />Preparing Export...</>
          ) : (
            <><Download size={14} />Export {config.formats[0].toUpperCase()}</>
          )}
        </button>
      </div>
    </div>
  );
}

export function DataCenter() {
  const { userRole } = useApp();
  const isAdmin = userRole === 'admin';
  const [exportingId, setExportingId] = useState<string | null>(null);
  const [completedExports, setCompletedExports] = useState<string[]>([]);
  const [showCSVSchema, setShowCSVSchema] = useState(false);
  const [filterCampaign, setFilterCampaign] = useState<number | 'all'>('all');

  const { data: dashboard } = useDashboard();
  const { data: campaigns } = useCampaigns();

  const handleExport = async (id: string) => {
    setExportingId(id);
    try {
      if (id === 'master_sheet') {
        const response = await api.get('/api/export/csv', {
          params: { campaign_id: filterCampaign === 'all' ? undefined : filterCampaign },
          responseType: 'blob'
        });
        const url = URL.createObjectURL(new Blob([response.data]));
        const a = document.createElement('a');
        a.href = url;
        a.download = `voiceqa_master_sheet_${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } else if (id === 'transcripts') {
        if (filterCampaign === 'all') {
          alert('Please select a specific campaign for transcript ZIP export.');
          setExportingId(null);
          return;
        }
        const response = await api.get('/api/export/transcripts', {
          params: { campaign_id: filterCampaign },
          responseType: 'blob'
        });
        const url = URL.createObjectURL(new Blob([response.data]));
        const a = document.createElement('a');
        a.href = url;
        a.download = `campaign_${filterCampaign}_transcripts.zip`;
        a.click();
        URL.revokeObjectURL(url);
      }
      setCompletedExports(prev => [...prev, id]);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExportingId(null);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-muted-foreground text-xs">LLM fine-tuning exports, BI integrations, and data science operations</p>
        {isAdmin && (
          <div className="flex items-center gap-2">
            <Shield size={14} className="text-emerald-400" />
            <span className="text-xs text-emerald-400">PII Compliance Active</span>
          </div>
        )}
      </div>

      {/* Data Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Calls', value: dashboard?.total_calls?.toString() || '0', icon: Database, iconColor: '#818cf8', bgColor: 'rgba(99,102,241,0.12)' },
          { label: 'Avg QA Score', value: dashboard?.avg_qa_score?.toString() || '0', icon: FileJson, iconColor: '#22d3ee', bgColor: 'rgba(6,182,212,0.12)' },
          { label: 'Queue Depth', value: dashboard?.queue_depth?.toString() || '0', icon: Archive, iconColor: '#fbbf24', bgColor: 'rgba(245,158,11,0.12)' },
          { label: 'Pass Rate', value: `${dashboard?.pass_rate || 0}%`, icon: Shield, iconColor: '#34d399', bgColor: 'rgba(16,185,129,0.12)' },
        ].map(stat => (
          <div key={stat.label} className="bg-card border border-border rounded-xl p-4">
            <div className="size-8 rounded-lg flex items-center justify-center mb-3" style={{ backgroundColor: stat.bgColor }}>
              <stat.icon size={16} style={{ color: stat.iconColor }} />
            </div>
            <p className="text-foreground text-lg font-semibold">{stat.value}</p>
            <p className="text-muted-foreground text-xs">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 p-4 bg-card border border-border rounded-xl">
        <Filter size={14} className="text-muted-foreground" />
        <span className="text-xs text-muted-foreground">Export Filters:</span>

        <select
          value={filterCampaign}
          onChange={e => setFilterCampaign(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
          className="bg-secondary border border-border text-foreground text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500"
        >
          <option value="all">All Campaigns</option>
          {campaigns?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>

        {!isAdmin && (
          <div className="flex items-center gap-2 ml-auto px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <Shield size={12} className="text-amber-400" />
            <span className="text-xs text-amber-400">PII fields excluded from your exports</span>
          </div>
        )}
      </div>

      {/* Export Cards */}
      <div>
        <h3 className="text-foreground text-sm font-semibold mb-4">Strategic Export Hub</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {exportTypes.map(et => (
            <div key={et.id} className="relative">
              <ExportCard
                config={et}
                onExport={() => handleExport(et.id)}
                isExporting={exportingId === et.id}
              />
              {completedExports.includes(et.id) && (
                <div className="absolute top-4 right-4 flex items-center gap-1 text-xs text-emerald-400">
                  <CheckCircle size={12} />
                  Exported
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* CSV Schema Reference */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <button
          onClick={() => setShowCSVSchema(!showCSVSchema)}
          className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-secondary/50 transition-all"
        >
          <div className="flex items-center gap-3">
            <Info size={16} className="text-muted-foreground" />
            <h3 className="text-foreground text-sm font-semibold">CSV Master Sheet Schema Reference</h3>
            <span className="text-xs px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full">Power BI Ready</span>
          </div>
          <ChevronDown size={14} className={cn('text-muted-foreground transition-transform', showCSVSchema && 'rotate-180')} />
        </button>

        {showCSVSchema && (
          <div className="px-5 pb-5 border-t border-border">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {csvFields.map(cat => (
                <div key={cat.category} className="bg-secondary/50 rounded-xl p-4">
                  <h4 className="text-foreground text-xs font-semibold mb-3 uppercase tracking-wider">{cat.category}</h4>
                  <ul className="space-y-1.5">
                    {cat.fields.map(f => (
                      <li key={f} className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="size-1 rounded-full bg-slate-600 flex-shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              Compatible with Microsoft Power BI, Tableau, Excel, and any LLM fine-tuning pipeline (OpenAI, Hugging Face, etc.)
            </p>
          </div>
        )}
      </div>
    </div>
  );
}