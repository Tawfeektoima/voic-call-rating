import { useState, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router';
import {
  Search, Filter, Download, Upload, ChevronUp, ChevronDown, ChevronLeft, ChevronRight,
  CheckCircle2, Loader2, Clock, XCircle, Phone, Eye, MoreHorizontal, AlertTriangle, X
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import api from '@/app/lib/api';
import { formatDuration, getScoreColor, type CallStatus, type Agent, type Campaign } from '../data/mockData';
import { useLang } from '../context/LangContext';

const StatusBadge = ({ status }: { status: string }) => {
  const { lang } = useLang();
  const isRtl = lang === 'ar';
  const configs: Record<string, { label: string; labelAr: string; class: string; icon: React.ReactNode }> = {
    EVALUATED: { label: 'Completed', labelAr: 'مكتمل', class: 'bg-green-500/10 text-green-400 border-green-500/20', icon: <CheckCircle2 size={11} /> },
    COMPLETED: { label: 'Completed', labelAr: 'مكتمل', class: 'bg-green-500/10 text-green-400 border-green-500/20', icon: <CheckCircle2 size={11} /> },
    PROCESSING: { label: 'Processing', labelAr: 'جاري المعالجة', class: 'bg-blue-500/10 text-blue-400 border-blue-500/20', icon: <Loader2 size={11} className="animate-spin" /> },
    TRANSCRIBED: { label: 'Analyzing', labelAr: 'جاري التحليل', class: 'bg-blue-500/10 text-blue-400 border-blue-500/20', icon: <Loader2 size={11} className="animate-spin" /> },
    PENDING: { label: 'Pending', labelAr: 'في الانتظار', class: 'bg-amber-500/10 text-amber-400 border-amber-500/20', icon: <Clock size={11} /> },
    FAILED: { label: 'Failed', labelAr: 'فشل', class: 'bg-red-500/10 text-red-400 border-red-500/20', icon: <XCircle size={11} /> },
  };
  const c = configs[status] || configs.PENDING;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${c.class}`}>
      {c.icon} {isRtl ? c.labelAr : c.label}
    </span>
  );
};

export function CallExplorer() {
  const navigate = useNavigate();
  const { lang } = useLang();
  const isRtl = lang === 'ar';
  const t = (en: string, ar: string) => isRtl ? ar : en;
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [agentFilter, setAgentFilter] = useState<string>('ALL');
  const [campaignFilter, setCampaignFilter] = useState<string>('ALL');
  const [scoreMin, setScoreMin] = useState('');
  const [scoreMax, setScoreMax] = useState('');
  const [sortField, setSortField] = useState<'date' | 'score' | 'duration' | 'agent' | 'campaign'>('date');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);
  const pageSize = 8;

  // Upload State
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadAgent, setUploadAgent] = useState('');
  const [uploadCampaign, setUploadCampaign] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });

  const handleUpload = async () => {
    if (uploadFiles.length === 0 || !uploadAgent || !uploadCampaign) {
      toast.error(t('Please fill all fields', 'يرجى ملء جميع الحقول'));
      return;
    }
    setIsUploading(true);
    setUploadProgress({ current: 0, total: uploadFiles.length });

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < uploadFiles.length; i++) {
      setUploadProgress(p => ({ ...p, current: i + 1 }));
      const file = uploadFiles[i];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('employee_id', uploadAgent);
      formData.append('campaign_id', uploadCampaign);

      try {
        await api.post('/audio/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        successCount++;
      } catch (err: any) {
        console.error(`Failed to upload ${file.name}:`, err);
        failCount++;
      }
    }

    if (successCount > 0) {
      toast.success(t(
        `Successfully uploaded ${successCount} files!`,
        `تم رفع ${successCount} ملفات بنجاح!`
      ));
    }
    if (failCount > 0) {
      toast.error(t(
        `Failed to upload ${failCount} files.`,
        `فشل رفع ${failCount} ملفات.`
      ));
    }

    setIsUploadOpen(false);
    setUploadFiles([]);
    setUploadAgent('');
    setUploadCampaign('');
    queryClient.invalidateQueries({ queryKey: ['calls'] });
    setIsUploading(false);
  };

  const { data: agents = [] } = useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: async () => {
      const res = await api.get('/admin/employees');
      return (res.data || []).map((a: any) => ({
        ...a,
        id: a.id.toString(),
        initials: a.name.split(' ').map((n: any) => n[0]).join('').toUpperCase(),
        color: '#6366f1',
      }));
    }
  });

  const { data: campaigns = [] } = useQuery<Campaign[]>({
    queryKey: ['campaigns'],
    queryFn: async () => {
      const res = await api.get('/admin/campaigns');
      return (res.data || []).map((c: any) => ({
        ...c,
        id: c.id.toString(),
        color: '#6366f1',
      }));
    }
  });

  const { data: calls = [] } = useQuery({
    queryKey: ['calls', search, statusFilter, agentFilter, campaignFilter, scoreMin, scoreMax],
    queryFn: async () => {
      const params: any = {};
      if (agentFilter !== 'ALL') {
        const agent = (agents || []).find(a => a.id === agentFilter);
        if (agent) params.employee_code = agent.employee_code;
      }
      if (campaignFilter !== 'ALL') params.campaign_id = campaignFilter;
      
      const res = await api.get('/analytics/search', { params });
      return (res.data || []).map((c: any) => ({
        ...c,
        date: c.created_at,
        filename: c.original_filename,
        duration: c.audio_duration ? `${Math.floor(c.audio_duration / 60)}:${(c.audio_duration % 60).toString().padStart(2, '0')}` : '0:00',
        score: c.overridden_score !== null ? c.overridden_score : (c.evaluation_score || 0),
        agent: (agents || []).find(a => a.id.toString() === c.employee_id?.toString())?.name || 'Unknown Agent',
        campaign: (campaigns || []).find(cam => cam.id.toString() === c.campaign_id?.toString())?.name || 'Unknown Campaign',
        status: c.status?.replace('CallStatus.', '').toUpperCase() || 'PENDING',
        errorCategories: c.weaknesses ? c.weaknesses.map((w: any) => w.issue) : []
      }));
    }
  });

  const filtered = useMemo(() => {
    const list = Array.isArray(calls) ? calls : [];
    return list.filter(call => {
      if (search) {
        const q = search.toLowerCase();
        if (
          !(call.agent || '').toLowerCase().includes(q) &&
          !(call.campaign || '').toLowerCase().includes(q) &&
          !(call.filename || '').toLowerCase().includes(q)
        ) return false;
      }
      if (statusFilter !== 'ALL' && call.status !== statusFilter) return false;
      if (agentFilter !== 'ALL' && call.employee_id?.toString() !== agentFilter) return false;
      if (campaignFilter !== 'ALL' && call.campaign_id?.toString() !== campaignFilter) return false;
      if (scoreMin && call.score < parseInt(scoreMin)) return false;
      if (scoreMax && call.score > parseInt(scoreMax)) return false;
      return true;
    });
  }, [calls, search, statusFilter, agentFilter, campaignFilter, scoreMin, scoreMax]);

  const totalPages = Math.ceil((filtered?.length || 0) / pageSize);
  const paginated = (filtered || []).slice((page - 1) * pageSize, page * pageSize);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) setPage(newPage);
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">{t('Call Explorer', 'مستكشف المكالمات')}</h1>
          <p className="text-sm text-slate-500 mt-0.5">{t(`${filtered?.length || 0} calls found`, `تم العثور على ${filtered?.length || 0} مكالمة`)}</p>
        </div>
        <button onClick={() => setIsUploadOpen(true)} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors">
          <Upload size={16} /> {t('Upload Recordings', 'رفع تسجيلات')}
        </button>
      </div>

      {isUploadOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => !isUploading && setIsUploadOpen(false)}>
          <div className="bg-[#111827] border border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold text-white">{t('Upload Recording', 'رفع تسجيل')}</h2>
              <button onClick={() => !isUploading && setIsUploadOpen(false)} className="text-slate-500 hover:text-white transition-colors"><X size={20} /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400 block mb-2">{t('Select Agent', 'اختر الوكيل')}</label>
                <select value={uploadAgent} onChange={e => setUploadAgent(e.target.value)} disabled={isUploading} className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500/50">
                  <option value="">{t('Select an agent...', 'اختر وكيلاً...')}</option>
                  {(agents || []).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-2">{t('Select Campaign', 'اختر الحملة')}</label>
                <select value={uploadCampaign} onChange={e => setUploadCampaign(e.target.value)} disabled={isUploading} className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500/50">
                  <option value="">{t('Select a campaign...', 'اختر حملة...')}</option>
                  {(campaigns || []).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-2">{t('Audio Files', 'الملفات الصوتية')}</label>
                <div className="relative group">
                  <input
                    type="file"
                    multiple
                    accept=".mp3,.wav,.m4a,.ogg,.flac,.webm"
                    onChange={e => setUploadFiles(Array.from(e.target.files || []))}
                    disabled={isUploading}
                    className="w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer"
                  />
                  {uploadFiles.length > 0 && (
                    <div className="mt-2 text-[11px] text-indigo-400 font-medium">
                      {t(`${uploadFiles.length} files selected`, `تم اختيار ${uploadFiles.length} ملفات`)}
                    </div>
                  )}
                </div>
              </div>
              <button
                onClick={handleUpload}
                disabled={isUploading || uploadFiles.length === 0 || !uploadAgent || !uploadCampaign}
                className="w-full mt-6 flex flex-col items-center justify-center gap-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
              >
                {isUploading ? (
                  <>
                    <div className="flex items-center gap-2">
                      <Loader2 size={18} className="animate-spin" />
                      {t(`Uploading ${uploadProgress.current}/${uploadProgress.total}...`, `جاري رفع ${uploadProgress.current}/${uploadProgress.total}...`)}
                    </div>
                    <div className="w-full max-w-[200px] h-1 bg-white/20 rounded-full mt-1 overflow-hidden">
                      <div
                        className="h-full bg-white transition-all duration-300"
                        style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
                      />
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-center gap-2">
                      <Upload size={18} />
                      {t('Start Batch Upload', 'بدء رفع المجموعة')}
                    </div>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col xl:flex-row gap-6">
        {/* Filter Sidebar */}
        <div className="xl:w-72 flex-shrink-0 space-y-5">
          <div className="bg-[#111827] border border-slate-800/60 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2"><Filter size={16} className="text-indigo-400" /> {t('Filters', 'الفلاتر')}</h3>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-500 mb-1.5 block">{t('Search', 'بحث')}</label>
                <div className="relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input type="text" placeholder={t('Search agents, campaigns...', 'البحث في الوكلاء والحملات...')} value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50" />
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1.5 block">{t('Status', 'الحالة')}</label>
                <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }} className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50">
                  <option value="ALL">{t('All Statuses', 'جميع الحالات')}</option>
                  <option value="COMPLETED">{t('Completed', 'مكتمل')}</option>
                  <option value="PROCESSING">{t('Processing', 'قيد المعالجة')}</option>
                  <option value="FAILED">{t('Failed', 'فشل')}</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1.5 block">{t('Agent', 'الوكيل')}</label>
                <select value={agentFilter} onChange={e => { setAgentFilter(e.target.value); setPage(1); }} className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50">
                  <option value="ALL">{t('All Agents', 'جميع الوكلاء')}</option>
                  {(agents || []).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1.5 block">{t('Campaign', 'الحملة')}</label>
                <select value={campaignFilter} onChange={e => { setCampaignFilter(e.target.value); setPage(1); }} className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50">
                  <option value="ALL">{t('All Campaigns', 'جميع الحملات')}</option>
                  {(campaigns || []).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Call Table */}
        <div className="flex-1 min-w-0">
          <div className="bg-[#111827] border border-slate-800/60 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-800/60 bg-slate-900/30">
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Date & File', 'التاريخ والملف')}</th>
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Agent', 'الوكيل')}</th>
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Campaign', 'الحملة')}</th>
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Status', 'الحالة')}</th>
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Score', 'النتيجة')}</th>
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('Errors', 'الأخطاء')}</th>
                    <th className="px-5 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40">
                  {paginated.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-5 py-10 text-center text-slate-500">
                        {t('No calls found. Upload your first recording', 'لم يتم العثور على مكالمات. قم برفع أول تسجيل لك')}
                      </td>
                    </tr>
                  ) : (
                    paginated.map((call, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/20 transition-colors group">
                        <td className="px-5 py-3">
                          <p className="text-sm text-slate-200 font-medium">{new Date(call.date).toLocaleString()}</p>
                          <p className="text-[11px] text-slate-500 mt-0.5 truncate max-w-[150px]" title={call.filename}>{call.filename}</p>
                        </td>
                        <td className="px-5 py-3"><p className="text-sm text-slate-300">{call.agent || t('Unknown', 'غير معروف')}</p></td>
                        <td className="px-5 py-3"><p className="text-sm text-slate-400">{call.campaign || t('Unknown', 'غير معروف')}</p></td>
                        <td className="px-5 py-3"><StatusBadge status={call.status} /></td>
                        <td className="px-5 py-3">
                          {(call.status === 'COMPLETED' || call.status === 'EVALUATED') && call.score !== undefined ? (
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold" style={{ color: getScoreColor(call.score) }}>{call.score}%</span>
                            </div>
                          ) : <span className="text-sm text-slate-600">-</span>}
                        </td>
                        <td className="px-5 py-3">
                          {call.status === 'FAILED' ? (
                            <span className="text-[11px] text-red-400">{t('Transcription unavailable', 'النسخ النصي غير متاح')}</span>
                          ) : (call.errorCategories?.length > 0 ? (
                            <div className="flex gap-1 flex-wrap max-w-[200px]">
                              {call.errorCategories.slice(0, 2).map((err: string, i: number) => (
                                <span key={i} className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700/50 truncate max-w-[80px]" title={err}>{err}</span>
                              ))}
                              {call.errorCategories.length > 2 && <span className="text-[10px] text-slate-500">+{call.errorCategories.length - 2}</span>}
                            </div>
                          ) : <span className="text-sm text-slate-600">-</span>)}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <button onClick={() => navigate(`/calls/${call.id}`)} className="opacity-0 group-hover:opacity-100 p-1.5 text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 rounded-lg transition-all" title={t('View Details', 'عرض التفاصيل')}>
                            <Eye size={16} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="px-5 py-3 border-t border-slate-800/60 flex items-center justify-between">
                <p className="text-xs text-slate-500">
                  {t(`Showing ${(page - 1) * pageSize + 1} to ${Math.min(page * pageSize, filtered.length)} of ${filtered.length} entries`, `عرض ${(page - 1) * pageSize + 1} إلى ${Math.min(page * pageSize, filtered.length)} من ${filtered.length} إدخال`)}
                </p>
                <div className="flex items-center gap-1">
                  <button onClick={() => handlePageChange(page - 1)} disabled={page === 1} className="p-1 rounded-lg text-slate-400 hover:bg-slate-800 disabled:opacity-50 disabled:hover:bg-transparent transition-colors"><ChevronLeft size={16} /></button>
                  <button onClick={() => handlePageChange(page + 1)} disabled={page === totalPages} className="p-1 rounded-lg text-slate-400 hover:bg-slate-800 disabled:opacity-50 disabled:hover:bg-transparent transition-colors"><ChevronRight size={16} /></button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}