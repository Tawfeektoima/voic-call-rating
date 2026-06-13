import { useState, useCallback, useEffect } from 'react';
import { 
  Upload, Download, CheckCircle2, AlertCircle, 
  Trash2, FileSpreadsheet, UserPlus, ArrowRight,
  ShieldCheck, HelpCircle, Loader2, Search
} from 'lucide-react';
import { cn } from '../components/ui/utils';
import api, { getApprovedRoles, getEmployeesPaginated, updateEmployee } from '../lib/api';
import { Agent, RoleDefinition } from '../lib/types';
import { useApp } from '../context/AppContext';

interface AgentPreview {
  index: number;
  name: string;
  email: string;
  otp_email?: string;
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

const FALLBACK_ROLE_OPTIONS: RoleDefinition[] = [
  { role: 'AGENT', label: 'Agent', description: '', permissions: [], assignable_by_hr: true },
  { role: 'TEAM_LEADER', label: 'Team Leader', description: '', permissions: [], assignable_by_hr: true },
  { role: 'TEAM_MANAGER', label: 'Team Manager', description: '', permissions: [], assignable_by_hr: true },
  { role: 'HR_MANAGER', label: 'HR Manager', description: '', permissions: [], assignable_by_hr: true },
  { role: 'QA', label: 'QA Analyst', description: '', permissions: [], assignable_by_hr: true },
  { role: 'OPS_MANAGER', label: 'Ops Manager', description: '', permissions: [], assignable_by_hr: true },
  { role: 'ADMIN', label: 'Administrator', description: '', permissions: [], assignable_by_hr: false },
];

export function HRManagement() {
  const { currentUser } = useApp();
  const [activeTab, setActiveTab] = useState<'directory' | 'onboard'>('directory');

  // Bulk Onboarding States
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<AgentPreview[] | null>(null);
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<{ message: string; success_count: number; failed_count: number } | null>(null);

  // User Directory States
  const [employees, setEmployees] = useState<Agent[]>([]);
  const [totalEmployees, setTotalEmployees] = useState(0);
  const [dirLoading, setDirLoading] = useState(false);
  const [dirSearch, setDirSearch] = useState('');
  const [dirRole, setDirRole] = useState<string>('all');
  const [dirStatus, setDirStatus] = useState<string>('all');
  const [dirPage, setDirPage] = useState(1);
  const [updatingEmployeeId, setUpdatingEmployeeId] = useState<number | null>(null);
  const [roleOptions, setRoleOptions] = useState<RoleDefinition[]>(FALLBACK_ROLE_OPTIONS);

  const LIMIT = 10;
  const canAssignAdmin = currentUser?.role === 'admin';
  const selectableRoles = roleOptions.filter((role) => canAssignAdmin || role.assignable_by_hr);

  const fetchDirectory = useCallback(async (page: number, search: string, role: string, status: string) => {
    setDirLoading(true);
    try {
      const skip = (page - 1) * LIMIT;
      const params: any = {
        skip,
        limit: LIMIT,
      };
      if (search) params.search = search;
      if (role !== 'all') params.role = role;
      if (status !== 'all') params.status = status;

      const data = await getEmployeesPaginated(params);
      setEmployees(data.items);
      setTotalEmployees(data.total);
    } catch (err) {
      console.error('Failed to load directory:', err);
    } finally {
      setDirLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'directory') {
      fetchDirectory(dirPage, dirSearch, dirRole, dirStatus);
    }
  }, [activeTab, dirPage, dirSearch, dirRole, dirStatus, fetchDirectory]);

  useEffect(() => {
    let cancelled = false;
    getApprovedRoles()
      .then((roles) => {
        if (!cancelled && roles.length > 0) setRoleOptions(roles);
      })
      .catch((err) => {
        console.error('Failed to load role catalog:', err);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleUpdateRole = async (employeeId: number, newRole: string) => {
    setUpdatingEmployeeId(employeeId);
    try {
      await updateEmployee(employeeId, { role: newRole });
      fetchDirectory(dirPage, dirSearch, dirRole, dirStatus);
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || 'Failed to update role');
    } finally {
      setUpdatingEmployeeId(null);
    }
  };

  const handleUpdateStatus = async (employeeId: number, newStatus: string) => {
    setUpdatingEmployeeId(employeeId);
    try {
      await updateEmployee(employeeId, { status: newStatus });
      fetchDirectory(dirPage, dirSearch, dirRole, dirStatus);
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || 'Failed to update status');
    } finally {
      setUpdatingEmployeeId(null);
    }
  };

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
            <ShieldCheck className="text-primary" />
            User & Access Management
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage user roles, account active states, and perform bulk onboarding.
          </p>
        </div>
        
        {activeTab === 'onboard' && (
          <button 
            onClick={downloadTemplate}
            className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 text-foreground rounded-xl transition-all border border-border"
          >
            <Download size={16} />
            <span>Download Excel Template</span>
          </button>
        )}
      </div>

      {/* Tab Buttons */}
      <div className="flex border-b border-border gap-4">
        <button
          onClick={() => setActiveTab('directory')}
          className={cn(
            "px-4 py-2.5 text-sm font-semibold border-b-2 transition-all flex items-center gap-2",
            activeTab === 'directory' 
              ? "border-primary text-primary" 
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <ShieldCheck size={16} />
          User Directory
        </button>
        <button
          onClick={() => setActiveTab('onboard')}
          className={cn(
            "px-4 py-2.5 text-sm font-semibold border-b-2 transition-all flex items-center gap-2",
            activeTab === 'onboard' 
              ? "border-primary text-primary" 
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <UserPlus size={16} />
          Bulk Onboard Agents
        </button>
      </div>

      {activeTab === 'directory' ? (
        <div className="space-y-6">
          {/* Filter controls */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 bg-card border border-border rounded-2xl">
            <div className="flex items-center gap-2 flex-1">
              <div className="relative w-full max-w-xs">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search code, name or email..."
                  className="w-full bg-background border border-border rounded-xl pl-9 pr-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-all"
                  value={dirSearch}
                  onChange={(e) => { setDirSearch(e.target.value); setDirPage(1); }}
                />
              </div>
            </div>
            
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground whitespace-nowrap">Filter Role:</span>
                <select
                  value={dirRole}
                  onChange={(e) => { setDirRole(e.target.value); setDirPage(1); }}
                  className="bg-secondary border border-border text-foreground text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-primary transition-all"
                >
                  <option value="all">All Roles</option>
                  {roleOptions.map((role) => (
                    <option key={role.role} value={role.role.toLowerCase()}>{role.label}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground whitespace-nowrap">Filter Status:</span>
                <select
                  value={dirStatus}
                  onChange={(e) => { setDirStatus(e.target.value); setDirPage(1); }}
                  className="bg-secondary border border-border text-foreground text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-primary transition-all"
                >
                  <option value="all">All Statuses</option>
                  <option value="active">Active</option>
                  <option value="disabled">Disabled</option>
                  <option value="suspended">Suspended</option>
                </select>
              </div>
            </div>
          </div>

          {/* Table of Employees */}
          <div className="bg-card border border-border rounded-2xl overflow-hidden flex flex-col h-[520px]">
            <div className="flex-1 overflow-auto">
              {dirLoading ? (
                <div className="h-full flex flex-col items-center justify-center text-center">
                  <Loader2 className="text-primary animate-spin mb-2" size={32} />
                  <p className="text-muted-foreground text-sm font-medium">Fetching User Directory...</p>
                </div>
              ) : employees.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground">
                  <HelpCircle className="opacity-20 mb-3" size={48} />
                  <p className="text-sm">No employees found matching the filters.</p>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead className="bg-secondary/50 sticky top-0 z-10 border-b border-border">
                    <tr>
                      <th className="px-5 py-3 text-xs font-bold text-muted-foreground uppercase">Agent</th>
                      <th className="px-5 py-3 text-xs font-bold text-muted-foreground uppercase">Code</th>
                      <th className="px-5 py-3 text-xs font-bold text-muted-foreground uppercase">Department</th>
                      <th className="px-5 py-3 text-xs font-bold text-muted-foreground uppercase">Role</th>
                      <th className="px-5 py-3 text-xs font-bold text-muted-foreground uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {employees.map((agent) => {
                      const agentRole = (agent.role || 'AGENT').toLowerCase();
                      const currentRoleOption = roleOptions.find((role) => role.role.toLowerCase() === agentRole);
                      const rowRoleOptions = selectableRoles.some((role) => role.role.toLowerCase() === agentRole)
                        ? selectableRoles
                        : [currentRoleOption, ...selectableRoles].filter(Boolean) as RoleDefinition[];
                      const isSelf = currentUser?.id === agent.id || currentUser?.email === agent.email;
                      return (
                        <tr key={agent.id} className={cn("hover:bg-secondary/20 transition-all", agent.status !== 'active' && "bg-red-500/5")}>
                          <td className="px-5 py-3">
                            <div className="flex items-center gap-3">
                              <div className="size-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs uppercase border border-primary/20">
                                {agent.name.substring(0, 2)}
                              </div>
                              <div>
                                <p className="text-xs font-bold text-foreground">{agent.name}</p>
                                <p className="text-[10px] text-muted-foreground">{agent.email}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-5 py-3 text-xs font-mono text-foreground">{agent.employee_code}</td>
                          <td className="px-5 py-3 text-xs text-muted-foreground">{agent.department || 'N/A'}</td>
                          <td className="px-5 py-3">
                            <select
                              value={agentRole}
                              disabled={isSelf || updatingEmployeeId === agent.id}
                              onChange={(e) => handleUpdateRole(agent.id, e.target.value)}
                              className="bg-secondary border border-border text-foreground text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {rowRoleOptions.map((role) => (
                                <option key={role.role} value={role.role.toLowerCase()}>{role.label}</option>
                              ))}
                            </select>
                          </td>
                          <td className="px-5 py-3">
                            <select
                              value={agent.status || 'active'}
                              disabled={isSelf || updatingEmployeeId === agent.id}
                              onChange={(e) => handleUpdateStatus(agent.id, e.target.value)}
                              className={cn(
                                "bg-secondary border border-border text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed font-medium",
                                (agent.status || 'active') === 'active' ? "text-emerald-400" : "text-red-400"
                              )}
                            >
                              <option value="active">Active</option>
                              <option value="disabled">Disabled</option>
                              <option value="suspended">Suspended</option>
                            </select>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            {/* Pagination controls */}
            {totalEmployees > LIMIT && (
              <div className="p-4 border-t border-border bg-secondary/20 flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  Showing <span className="font-semibold text-foreground">{Math.min(totalEmployees, (dirPage - 1) * LIMIT + 1)}</span> to{" "}
                  <span className="font-semibold text-foreground">{Math.min(totalEmployees, dirPage * LIMIT)}</span> of{" "}
                  <span className="font-semibold text-foreground">{totalEmployees}</span> agents
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setDirPage(prev => Math.max(1, prev - 1))}
                    disabled={dirPage === 1 || dirLoading}
                    className="px-3 py-1.5 bg-secondary text-foreground text-xs font-semibold rounded-lg border border-border hover:bg-secondary/80 disabled:opacity-50 transition-all"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setDirPage(prev => Math.min(Math.ceil(totalEmployees / LIMIT), prev + 1))}
                    disabled={dirPage === Math.ceil(totalEmployees / LIMIT) || dirLoading}
                    className="px-3 py-1.5 bg-secondary text-foreground text-xs font-semibold rounded-lg border border-border hover:bg-secondary/80 disabled:opacity-50 transition-all"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
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
      )}
    </div>
  );
}
