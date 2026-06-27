import { useState } from 'react';
import { useNavigate } from 'react-router';
import { 
  Upload, Search, Filter, Phone, CheckCircle, 
  AlertCircle, ChevronRight, Loader2, Radio, Trash2
} from 'lucide-react';
import { useCalls, useUploadAudio, useBulkUploadAudio } from '../hooks/useCalls';
import { useCampaigns } from '../hooks/useCampaigns';
import { getApiErrorMessage, getEmployees } from '../lib/api';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Call, CallStatus } from '../lib/types';
import { cn } from '../components/ui/utils';
import { Skeleton } from '../components/ui/skeleton';
import { buildNotesComposeUrl } from '../lib/noteNavigation';

export function CallExplorer() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  
  // Tab control
  const [activeTab, setActiveTab] = useState<'single' | 'bulk'>('single');

  // Single upload form state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [selectedCampaign, setSelectedCampaign] = useState<string>('');

  // Bulk upload form state
  interface BulkFileItem {
    id: string;
    file: File;
    employeeId: string;
    campaignId: string;
  }
  const [bulkFiles, setBulkFiles] = useState<BulkFileItem[]>([]);
  const [globalAgent, setGlobalAgent] = useState<string>('');
  const [globalCampaign, setGlobalCampaign] = useState<string>('');
  const [bulkResult, setBulkResult] = useState<any>(null);

  const { data: calls, isLoading: callsLoading } = useCalls({ limit: 100, min_id: 66 } as any);
  const { data: campaigns } = useCampaigns();
  const { data: agents } = useQuery({ queryKey: ['agents'], queryFn: getEmployees });
  const uploadMutation = useUploadAudio();
  const bulkUploadMutation = useBulkUploadAudio();
  const openCallNote = (call: Call) => {
    navigate(buildNotesComposeUrl({
      noteType: 'GENERAL',
      callId: call.id,
      employeeId: call.employee_id,
      campaignId: call.campaign_id,
      title: `Workflow note for call #${call.id}`,
    }));
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !selectedAgent || !selectedCampaign) return;

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('employee_id', selectedAgent);
    formData.append('campaign_id', selectedCampaign);

    uploadMutation.mutate(formData, {
      onSuccess: (data) => {
        toast.success('Upload complete. AI processing has started.');
        navigate(`/calls/${data.call_id}`);
      },
      onError: (err) => {
        console.error('Upload failed:', err);
        toast.error(getApiErrorMessage(err, 'Audio upload failed. Please try again.'));
      }
    });
  };

  const handleBulkFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newItems = Array.from(e.target.files).map(file => ({
        id: `${file.name}-${Date.now()}-${Math.random()}`,
        file,
        employeeId: globalAgent || '',
        campaignId: globalCampaign || ''
      }));
      setBulkFiles(prev => [...prev, ...newItems]);
    }
  };

  const applyGlobalAgent = (agentId: string) => {
    setGlobalAgent(agentId);
    setBulkFiles(prev => prev.map(item => ({ ...item, employeeId: agentId })));
  };

  const applyGlobalCampaign = (campaignId: string) => {
    setGlobalCampaign(campaignId);
    setBulkFiles(prev => prev.map(item => ({ ...item, campaignId: campaignId })));
  };

  const removeBulkFile = (id: string) => {
    setBulkFiles(prev => prev.filter(item => item.id !== id));
  };

  const handleBulkUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (bulkFiles.length === 0) return;

    const formData = new FormData();
    const metadata = [];

    for (const item of bulkFiles) {
      formData.append('files', item.file);
      metadata.push({
        filename: item.file.name,
        employee_id: item.employeeId ? parseInt(item.employeeId) : null,
        campaign_id: item.campaignId ? parseInt(item.campaignId) : null
      });
    }

    formData.append('metadata', JSON.stringify(metadata));

    bulkUploadMutation.mutate(formData, {
      onSuccess: (data) => {
        setBulkResult(data);
        setBulkFiles([]);
      },
      onError: (err) => {
        console.error('Bulk upload failed:', err);
        toast.error(getApiErrorMessage(err, 'Bulk upload failed. Please try again.'));
      }
    });
  };

  const filteredCalls = (calls || []).filter(call => 
    call.id.toString().includes(searchQuery) || 
    (call.call_summary || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-slate-100 text-lg font-semibold">Call Explorer</h1>
          <p className="text-muted-foreground text-xs mt-1">Browse all recorded calls and upload new files for AI evaluation</p>
        </div>
        <button 
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-indigo-400 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-indigo-500/20"
        >
          <Upload size={16} />
          Upload New Call
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 p-4 bg-card border border-border rounded-xl">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={14} />
          <input 
            type="text"
            placeholder="Search by ID or summary..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full bg-secondary border border-border rounded-lg pl-9 pr-4 py-2 text-xs text-foreground focus:outline-none focus:border-indigo-500"
          />
        </div>
        <button className="flex items-center gap-2 px-3 py-2 bg-secondary text-muted-foreground rounded-lg text-xs hover:text-foreground border border-border transition-all">
          <Filter size={14} />
          More Filters
        </button>
      </div>

      {/* Calls List */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-6 py-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Call ID</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Agent</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Campaign</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Score</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Created</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {callsLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={7} className="px-6 py-4"><Skeleton className="h-10 w-full bg-secondary" /></td>
                  </tr>
                ))
              ) : filteredCalls.map((call: Call) => (
                <tr 
                  key={call.id} 
                  className="hover:bg-secondary/50 cursor-pointer transition-all group"
                  onClick={() => navigate(`/calls/${call.id}`)}
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        'size-8 rounded-lg flex items-center justify-center',
                        call.status === CallStatus.EVALUATED ? 'bg-emerald-500/10 text-emerald-400' : 
                        call.status === CallStatus.FAILED ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'
                      )}>
                        <Phone size={14} />
                      </div>
                      <span className="text-sm text-foreground font-medium">#{call.id}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-xs text-muted-foreground">Agent #{call.employee_id}</td>
                  <td className="px-6 py-4 text-xs text-muted-foreground">Campaign #{call.campaign_id}</td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      'text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border',
                      call.status === CallStatus.EVALUATED ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                      call.status === CallStatus.FAILED ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                      'bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse'
                    )}>
                      {call.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      'text-sm font-bold',
                      (call.overridden_score ?? call.evaluation_score ?? 0) >= 80 ? 'text-emerald-400' :
                      (call.overridden_score ?? call.evaluation_score ?? 0) >= 70 ? 'text-amber-400' : 'text-red-400'
                    )}>
                      {call.overridden_score ?? call.evaluation_score ?? '--'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-xs text-muted-foreground">
                    {new Date(call.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          openCallNote(call);
                        }}
                        className="text-xs text-primary hover:text-indigo-300 transition-colors"
                        title={`Create a workflow note for call #${call.id}`}
                      >
                        Add Note
                      </button>
                      <button className="text-muted-foreground group-hover:text-primary transition-all">
                        <ChevronRight size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/75 backdrop-blur-sm" onClick={() => {
            setShowUploadModal(false);
            setBulkResult(null);
            setBulkFiles([]);
          }} />
          
          {bulkResult ? (
            <div className="relative bg-card border border-border rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
              <div className="px-6 py-5 border-b border-border bg-slate-900/50">
                <h2 className="text-slate-100 text-lg font-bold flex items-center gap-2">
                  📊 Bulk Evaluation Results
                </h2>
                <p className="text-muted-foreground text-xs mt-1">Summary of the bulk ingestion run.</p>
              </div>

              <div className="p-6 overflow-y-auto space-y-6 flex-1">
                {/* Summary statistics */}
                <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
                  <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl text-center">
                    <p className="text-3xl font-extrabold text-emerald-400">{bulkResult.success_count}</p>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold mt-1">Successfully Imported</p>
                  </div>
                  <div className="p-4 bg-red-500/5 border border-red-500/10 rounded-2xl text-center">
                    <p className="text-3xl font-extrabold text-red-400">{bulkResult.failed_count}</p>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold mt-1">Failed</p>
                  </div>
                </div>

                {/* Per-item list */}
                <div className="space-y-3 bg-secondary/20 border border-border rounded-xl p-4">
                  <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-2">Detailed Report</h3>
                  <div className="space-y-2 max-h-[300px] overflow-y-auto divide-y divide-border/40 pr-2">
                    {bulkResult.results?.map((item: any, idx: number) => (
                      <div key={idx} className="flex items-start justify-between py-2.5 gap-4">
                        <div className="flex items-start gap-3 min-w-0">
                          {item.success ? (
                            <CheckCircle size={16} className="text-emerald-400 mt-0.5 shrink-0" />
                          ) : (
                            <AlertCircle size={16} className="text-red-400 mt-0.5 shrink-0" />
                          )}
                          <div className="min-w-0">
                            <p className="text-xs font-medium text-slate-100 truncate">{item.filename}</p>
                            {!item.success && (
                              <p className="text-[10px] text-red-300 mt-0.5 font-medium">{item.error}</p>
                            )}
                          </div>
                        </div>
                        {item.success && (
                          <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20 shrink-0">
                            ID #{item.call_id}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="px-6 py-4 bg-secondary/50 border-t border-border flex justify-end">
                <button 
                  onClick={() => {
                    setBulkResult(null);
                    setBulkFiles([]);
                    setShowUploadModal(false);
                  }}
                  className="px-6 py-2 bg-primary hover:bg-indigo-400 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-indigo-500/20"
                >
                  Close Results
                </button>
              </div>
            </div>
          ) : (
            <div className={cn(
              "relative bg-card border border-border rounded-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[85vh] transition-all",
              activeTab === 'bulk' ? 'max-w-4xl' : 'max-w-md'
            )}>
              <div className="px-6 py-4 border-b border-border bg-slate-900/50">
                <h2 className="text-slate-100 text-sm font-semibold">Upload Audio Calls</h2>
                <p className="text-muted-foreground text-xs mt-1">Select call recordings and assign them for automated rating.</p>
              </div>

              {/* Tabs header */}
              <div className="flex border-b border-border bg-secondary/30">
                <button 
                  onClick={() => setActiveTab('single')}
                  className={cn(
                    "flex-1 py-3 text-xs font-bold transition-all border-b-2",
                    activeTab === 'single' ? "border-primary text-primary bg-primary/5" : "border-transparent text-muted-foreground hover:text-slate-200"
                  )}
                >
                  Single Upload
                </button>
                <button 
                  onClick={() => setActiveTab('bulk')}
                  className={cn(
                    "flex-1 py-3 text-xs font-bold transition-all border-b-2",
                    activeTab === 'bulk' ? "border-primary text-primary bg-primary/5" : "border-transparent text-muted-foreground hover:text-slate-200"
                  )}
                >
                  Bulk Upload ({bulkFiles.length} Selected)
                </button>
              </div>

              <div className="p-6 overflow-y-auto flex-1">
                {activeTab === 'single' ? (
                  <form onSubmit={handleUpload} className="space-y-4">
                    {/* File Input */}
                    <div className="space-y-2">
                      <label className="text-xs text-muted-foreground">Audio File</label>
                      <div 
                        className={cn(
                          'border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center gap-2 cursor-pointer transition-all',
                          selectedFile ? 'border-indigo-500 bg-primary/5' : 'border-border hover:border-border'
                        )}
                        onClick={() => document.getElementById('fileInput')?.click()}
                      >
                        <Upload size={24} className={selectedFile ? 'text-primary' : 'text-muted-foreground'} />
                        <p className="text-xs text-foreground font-medium">{selectedFile ? selectedFile.name : 'Select or drop file'}</p>
                        <p className="text-[10px] text-muted-foreground">MP3, WAV up to 50MB</p>
                        <input 
                          id="fileInput"
                          type="file" 
                          accept="audio/*"
                          onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                          className="hidden" 
                        />
                      </div>
                    </div>

                    {/* Agent Selection */}
                    <div className="space-y-2">
                      <label className="text-xs text-muted-foreground">Assign to Agent</label>
                      <div className="relative">
                        <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                        <select 
                          value={selectedAgent}
                          onChange={e => setSelectedAgent(e.target.value)}
                          required
                          className="w-full bg-secondary border border-border rounded-lg pl-9 pr-4 py-2 text-xs text-foreground focus:outline-none focus:border-indigo-500 font-medium"
                        >
                          <option value="">Select Agent...</option>
                          {agents?.map(a => (
                            <option key={a.id} value={a.id}>{a.name} ({a.employee_code})</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {/* Campaign Selection */}
                    <div className="space-y-2">
                      <label className="text-xs text-muted-foreground">Assign to Campaign</label>
                      <div className="relative">
                        <Radio size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                        <select 
                          value={selectedCampaign}
                          onChange={e => setSelectedCampaign(e.target.value)}
                          required
                          className="w-full bg-secondary border border-border rounded-lg pl-9 pr-4 py-2 text-xs text-foreground focus:outline-none focus:border-indigo-500 font-medium"
                        >
                          <option value="">Select Campaign...</option>
                          {campaigns?.map(c => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="pt-4 flex gap-3">
                      <button 
                        type="button"
                        onClick={() => setShowUploadModal(false)}
                        className="flex-1 py-2 bg-secondary hover:bg-slate-700 text-foreground rounded-xl text-xs font-bold transition-all border border-border"
                      >
                        Cancel
                      </button>
                      <button 
                        type="submit"
                        disabled={uploadMutation.isPending || !selectedFile || !selectedAgent || !selectedCampaign}
                        className="flex-1 flex items-center justify-center gap-2 py-2 bg-primary hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-indigo-500/20"
                      >
                        {uploadMutation.isPending ? <><Loader2 size={14} className="animate-spin" /> Uploading...</> : 'Start Evaluation'}
                      </button>
                    </div>
                  </form>
                ) : (
                  <form onSubmit={handleBulkUpload} className="space-y-6">
                    {/* Bulk File Selection Box */}
                    <div className="space-y-2">
                      <label className="text-xs text-muted-foreground">Select Call Audio Files (Multiple Allowed)</label>
                      <div 
                        className={cn(
                          'border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center gap-2 cursor-pointer transition-all border-border hover:border-primary/50 bg-secondary/10'
                        )}
                        onClick={() => document.getElementById('bulkFileInput')?.click()}
                      >
                        <Upload size={32} className="text-primary hover:scale-110 transition-transform" />
                        <p className="text-xs text-foreground font-semibold">Click to select files</p>
                        <p className="text-[10px] text-muted-foreground">Supports MP3 and WAV. Max size 50MB per file.</p>
                        <input 
                          id="bulkFileInput"
                          type="file" 
                          accept="audio/*"
                          multiple
                          onChange={handleBulkFileChange}
                          className="hidden" 
                        />
                      </div>
                    </div>

                    {bulkFiles.length > 0 && (
                      <div className="space-y-4">
                        {/* Global assignments bar */}
                        <div className="p-4 bg-primary/5 border border-primary/20 rounded-xl space-y-3">
                          <h4 className="text-[11px] font-bold text-primary uppercase tracking-wider">⚡ Batch Configuration (Apply to all)</h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="relative">
                              <User size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                              <select 
                                value={globalAgent}
                                onChange={e => applyGlobalAgent(e.target.value)}
                                className="w-full bg-secondary border border-border rounded-lg pl-9 pr-4 py-2 text-xs text-foreground focus:outline-none focus:border-indigo-500"
                              >
                                <option value="">Global Agent...</option>
                                {agents?.map(a => (
                                  <option key={a.id} value={a.id}>{a.name} ({a.employee_code})</option>
                                ))}
                              </select>
                            </div>
                            <div className="relative">
                              <Radio size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                              <select 
                                value={globalCampaign}
                                onChange={e => applyGlobalCampaign(e.target.value)}
                                className="w-full bg-secondary border border-border rounded-lg pl-9 pr-4 py-2 text-xs text-foreground focus:outline-none focus:border-indigo-500"
                              >
                                <option value="">Global Campaign...</option>
                                {campaigns?.map(c => (
                                  <option key={c.id} value={c.id}>{c.name}</option>
                                ))}
                              </select>
                            </div>
                          </div>
                        </div>

                        {/* File list table */}
                        <div className="border border-border rounded-xl overflow-hidden max-h-[300px] overflow-y-auto bg-slate-950/40">
                          <table className="w-full text-left border-collapse">
                            <thead className="bg-secondary/40 sticky top-0 z-10 border-b border-border">
                              <tr>
                                <th className="px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase">File Name</th>
                                <th className="px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase">Assign Agent</th>
                                <th className="px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase">Assign Campaign</th>
                                <th className="px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase text-center w-12">Action</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border/60">
                              {bulkFiles.map((item, idx) => (
                                <tr key={item.id} className="hover:bg-secondary/20">
                                  <td className="px-4 py-2.5 text-xs text-slate-100 max-w-[200px] truncate font-medium">
                                    {item.file.name}
                                    <span className="text-[10px] text-muted-foreground block mt-0.5">
                                      ({(item.file.size / (1024 * 1024)).toFixed(2)} MB)
                                    </span>
                                  </td>
                                  <td className="px-4 py-2.5">
                                    <select 
                                      value={item.employeeId}
                                      onChange={e => {
                                        const val = e.target.value;
                                        setBulkFiles(prev => prev.map(x => x.id === item.id ? { ...x, employeeId: val } : x));
                                      }}
                                      className="bg-secondary/80 border border-border/80 rounded-lg px-2 py-1 text-xs text-foreground focus:outline-none focus:border-indigo-500 w-full"
                                    >
                                      <option value="">Select Agent...</option>
                                      {agents?.map(a => (
                                        <option key={a.id} value={a.id}>{a.name}</option>
                                      ))}
                                    </select>
                                  </td>
                                  <td className="px-4 py-2.5">
                                    <select 
                                      value={item.campaignId}
                                      onChange={e => {
                                        const val = e.target.value;
                                        setBulkFiles(prev => prev.map(x => x.id === item.id ? { ...x, campaignId: val } : x));
                                      }}
                                      className="bg-secondary/80 border border-border/80 rounded-lg px-2 py-1 text-xs text-foreground focus:outline-none focus:border-indigo-500 w-full"
                                    >
                                      <option value="">Select Campaign...</option>
                                      {campaigns?.map(c => (
                                        <option key={c.id} value={c.id}>{c.name}</option>
                                      ))}
                                    </select>
                                  </td>
                                  <td className="px-4 py-2.5 text-center">
                                    <button 
                                      type="button"
                                      onClick={() => removeBulkFile(item.id)}
                                      className="text-muted-foreground hover:text-red-400 p-1.5 hover:bg-red-500/10 rounded-lg transition-all"
                                    >
                                      <Trash2 size={14} />
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    <div className="pt-4 flex gap-3 border-t border-border/40">
                      <button 
                        type="button"
                        onClick={() => {
                          setBulkFiles([]);
                          setShowUploadModal(false);
                        }}
                        className="flex-1 py-2 bg-secondary hover:bg-slate-700 text-foreground rounded-xl text-xs font-bold transition-all border border-border"
                      >
                        Cancel
                      </button>
                      <button 
                        type="submit"
                        disabled={
                          bulkUploadMutation.isPending || 
                          bulkFiles.length === 0 || 
                          bulkFiles.some(item => !item.employeeId || !item.campaignId)
                        }
                        className="flex-1 flex items-center justify-center gap-2 py-2 bg-primary hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-indigo-500/20"
                      >
                        {bulkUploadMutation.isPending ? (
                          <><Loader2 size={14} className="animate-spin" /> Uploading Batch...</>
                        ) : (
                          `Start Evaluation (${bulkFiles.length} Calls)`
                        )}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
