import { useState } from 'react';
import { useNavigate } from 'react-router';
import { 
  Upload, Search, Filter, Phone, Clock, CheckCircle, 
  XCircle, AlertCircle, ChevronRight, Loader2, Plus,
  Database, User, Radio
} from 'lucide-react';
import { useCalls, useUploadAudio } from '../hooks/useCalls';
import { useCampaigns } from '../hooks/useCampaigns';
import { getEmployees } from '../lib/api';
import { useQuery } from '@tanstack/react-query';
import { Call, CallStatus } from '../lib/types';
import { cn } from '../components/ui/utils';
import { Skeleton } from '../components/ui/skeleton';

export function CallExplorer() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  
  // Upload form state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [selectedCampaign, setSelectedCampaign] = useState<string>('');

  const { data: calls, isLoading: callsLoading } = useCalls({ limit: 100, min_id: 66 } as any);
  const { data: campaigns } = useCampaigns();
  const { data: agents } = useQuery({ queryKey: ['agents'], queryFn: getEmployees });
  const uploadMutation = useUploadAudio();

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !selectedAgent || !selectedCampaign) return;

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('employee_id', selectedAgent);
    formData.append('campaign_id', selectedCampaign);

    uploadMutation.mutate(formData, {
      onSuccess: (data) => {
        navigate(`/calls/${data.call_id}`);
      },
      onError: (err) => {
        console.error('Upload failed:', err);
        alert('Failed to upload audio. Please try again.');
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
                    <button className="text-muted-foreground group-hover:text-primary transition-all">
                      <ChevronRight size={18} />
                    </button>
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
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setShowUploadModal(false)} />
          <form 
            onSubmit={handleUpload}
            className="relative bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden"
          >
            <div className="px-6 py-4 border-b border-border">
              <h2 className="text-slate-100 text-sm font-semibold">Upload Audio File</h2>
              <p className="text-muted-foreground text-xs mt-1">Select an MP3/WAV file and assign it to an agent and campaign.</p>
            </div>
            
            <div className="p-6 space-y-4">
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
                    className="w-full bg-secondary border border-border rounded-lg pl-9 pr-4 py-2 text-xs text-foreground focus:outline-none focus:border-indigo-500"
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
                    className="w-full bg-secondary border border-border rounded-lg pl-9 pr-4 py-2 text-xs text-foreground focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">Select Campaign...</option>
                    {campaigns?.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="px-6 py-4 bg-secondary/50 border-t border-border flex gap-3">
              <button 
                type="button"
                onClick={() => setShowUploadModal(false)}
                className="flex-1 py-2 bg-secondary hover:bg-slate-700 text-foreground rounded-xl text-sm transition-all"
              >
                Cancel
              </button>
              <button 
                type="submit"
                disabled={uploadMutation.isPending || !selectedFile || !selectedAgent || !selectedCampaign}
                className="flex-1 flex items-center justify-center gap-2 py-2 bg-primary hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-indigo-500/20"
              >
                {uploadMutation.isPending ? <><Loader2 size={14} className="animate-spin" /> Uploading...</> : 'Start Evaluation'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
