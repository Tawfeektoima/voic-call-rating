import { useState, useCallback } from 'react';
import { 
  Upload, Download, CheckCircle2, AlertCircle, 
  Trash2, FileSpreadsheet, UserPlus, ArrowRight,
  ShieldCheck, HelpCircle, Loader2
} from 'lucide-react';
import { cn } from '../components/ui/utils';
import api from '../lib/api';

interface AgentPreview {
  index: number;
  name: string;
  email: string;
  employee_code: string;
  campaign_name: string;
  phone_number: string;
  errors: string[];
  isValid: boolean;
}

interface ImportSummary {
  total: number;
  valid: number;
  invalid: number;
}

export function HRManagement() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<AgentPreview[] | null>(null);
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<{ message: string; success_count: number; failed_count: number } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (selectedFile: File) => {
    setFile(selectedFile);
    setLoading(true);
    setResult(null);
    
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await api.post('/api/hr/preview', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });
      
      const data = response.data;
      setPreview(data.data);
      setSummary(data.summary);
    } catch (err) {
      console.error(err);
      alert('Error reading file. Please ensure it follows the template format.');
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = async () => {
    try {
      const response = await api.get('/api/hr/template', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'agent_import_template.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error(err);
      alert('Failed to download template');
    }
  };

  const finalizeImport = async () => {
    if (!preview) return;
    
    setImporting(true);
    const validAgents = preview.filter(a => a.isValid);

    try {
      const response = await api.post('/api/hr/import', validAgents);
      const data = response.data;
      setResult(data);
      setPreview(null);
      setFile(null);
    } catch (err) {
      console.error(err);
      alert('Error during import process.');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <UserPlus className="text-primary" />
            Bulk Agent Onboarding
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Rapidly enroll new team members into the platform via Excel or CSV.
          </p>
        </div>
        
        <button 
          onClick={downloadTemplate}
          className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 text-foreground rounded-xl transition-all border border-border"
        >
          <Download size={16} />
          <span>Download Excel Template</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Zone */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-card border-2 border-dashed border-border rounded-2xl p-8 text-center flex flex-col items-center justify-center min-h-[300px] transition-all hover:border-primary/50 group">
            <div className="size-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <FileSpreadsheet className="text-primary" size={32} />
            </div>
            <h3 className="text-lg font-semibold text-slate-100 mb-2">Upload Agent List</h3>
            <p className="text-sm text-muted-foreground mb-6">
              Drag and drop your .xlsx or .csv file here to start the validation process.
            </p>
            
            <label className="cursor-pointer px-6 py-2.5 bg-primary text-white font-medium rounded-xl hover:bg-primary/90 transition-all shadow-lg shadow-primary/20">
              Browse Files
              <input type="file" className="hidden" accept=".xlsx, .xls, .csv" onChange={handleFileChange} />
            </label>
            
            {file && (
              <div className="mt-4 flex items-center gap-2 text-xs text-indigo-300 bg-primary/10 px-3 py-1.5 rounded-lg">
                <CheckCircle2 size={12} />
                <span>Selected: {file.name}</span>
              </div>
            )}
          </div>

          {/* Compliance & RBAC Info */}
          <div className="bg-fuchsia-500/5 border border-fuchsia-500/10 rounded-2xl p-5 space-y-4">
            <h4 className="text-fuchsia-400 text-sm font-semibold flex items-center gap-2">
              <ShieldCheck size={16} />
              HR Manager Permissions
            </h4>
            <ul className="space-y-2">
              {[
                "Automatic campaign assignment",
                "Bulk credential generation",
                "Email duplicate prevention",
                "Secure onboarding protocols"
              ].map(item => (
                <li key={item} className="flex items-center gap-2 text-xs text-muted-foreground">
                  <div className="size-1 rounded-full bg-fuchsia-400" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Results / Preview Zone */}
        <div className="lg:col-span-2">
          {loading ? (
            <div className="bg-card border border-border rounded-2xl p-20 flex flex-col items-center justify-center text-center">
              <Loader2 className="text-primary animate-spin mb-4" size={40} />
              <p className="text-slate-100 font-medium">Validating Data Schema...</p>
              <p className="text-muted-foreground text-sm mt-1">Checking for duplicates and format errors.</p>
            </div>
          ) : result ? (
            <div className="bg-card border border-border rounded-2xl p-8 text-center space-y-6">
              <div className="size-20 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-2">
                <CheckCircle2 className="text-emerald-400" size={40} />
              </div>
              <div>
                <h3 className="text-2xl font-bold text-slate-100">Onboarding Complete</h3>
                <p className="text-muted-foreground mt-2">{result.message}</p>
              </div>
              <div className="grid grid-cols-2 gap-4 max-w-sm mx-auto">
                <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-xl">
                  <p className="text-2xl font-bold text-emerald-400">{result.success_count}</p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Successful</p>
                </div>
                <div className="p-4 bg-red-500/5 border border-red-500/10 rounded-xl">
                  <p className="text-2xl font-bold text-red-400">{result.failed_count}</p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Failed</p>
                </div>
              </div>
              <button 
                onClick={() => setResult(null)}
                className="px-6 py-2 border border-border rounded-xl text-foreground hover:bg-secondary transition-all"
              >
                Onboard More Agents
              </button>
            </div>
          ) : preview ? (
            <div className="bg-card border border-border rounded-2xl flex flex-col h-[600px]">
              <div className="p-5 border-b border-border flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Validation Preview</h3>
                  <p className="text-xs text-muted-foreground">Review the detected entries before finalizing.</p>
                </div>
                <div className="flex items-center gap-3">
                   <div className="flex items-center gap-2 text-xs">
                     <span className="text-emerald-400 font-bold">{summary?.valid}</span>
                     <span className="text-muted-foreground">Ready</span>
                   </div>
                   <div className="flex items-center gap-2 text-xs">
                     <span className="text-red-400 font-bold">{summary?.invalid}</span>
                     <span className="text-muted-foreground">Errors</span>
                   </div>
                </div>
              </div>

               <div className="flex-1 overflow-auto">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-secondary/50 sticky top-0 z-10">
                    <tr>
                      <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase">Status</th>
                      <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase">Employee Code</th>
                      <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase">Name</th>
                      <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase">Email</th>
                      <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase">Campaign</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {preview.map((agent) => (
                      <tr key={agent.index} className={cn("hover:bg-secondary/30", !agent.isValid && "bg-red-500/5")}>
                        <td className="px-4 py-3">
                          {agent.isValid ? (
                            <CheckCircle2 size={16} className="text-emerald-400" />
                          ) : (
                            <div className="group relative">
                              <AlertCircle size={16} className="text-red-400 cursor-help" />
                              <div className="absolute left-full ml-2 top-0 w-48 p-2 bg-slate-900 border border-red-500/50 rounded-lg shadow-xl hidden group-hover:block z-20">
                                {agent.errors.map(err => (
                                  <p key={err} className="text-[10px] text-red-200 leading-tight mb-1">• {err}</p>
                                ))}
                              </div>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-foreground font-mono">{agent.employee_code}</td>
                        <td className="px-4 py-3 text-xs text-foreground">{agent.name}</td>
                        <td className="px-4 py-3 text-xs text-muted-foreground">{agent.email}</td>
                        <td className="px-4 py-3 text-xs text-muted-foreground">{agent.campaign_name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="p-4 border-t border-border bg-secondary/20 flex items-center justify-between">
                <button 
                  onClick={() => { setPreview(null); setFile(null); }}
                  className="flex items-center gap-2 text-xs text-muted-foreground hover:text-red-400 transition-all"
                >
                  <Trash2 size={14} /> Clear All
                </button>
                <button 
                  onClick={finalizeImport}
                  disabled={importing || !summary?.valid}
                  className="flex items-center gap-2 px-6 py-2 bg-primary text-white text-xs font-bold rounded-xl hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {importing ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                  Complete Import ({summary?.valid} Agents)
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-card border border-border rounded-2xl p-20 flex flex-col items-center justify-center text-center text-muted-foreground">
              <HelpCircle className="opacity-20 mb-4" size={60} />
              <p>Upload a file to see the validation preview.</p>
              <p className="text-xs mt-1">We support .csv, .xlsx, and .xls formats.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
