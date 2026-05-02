import { useState, useMemo } from 'react';
import {
  BookOpen, Plus, Edit2, Trash2, ChevronDown, ChevronUp, Save, X,
  Target, Users, CheckCircle, BarChart3, Copy, Eye, Sparkles, GripVertical,
  Loader2, AlertCircle
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import api from '@/app/lib/api';
import { type Campaign, type RubricItem } from '../data/mockData';
import { useLang } from '../context/LangContext';

interface CampaignManagerProps {
  lang: 'en' | 'ar';
}

export function CampaignManager() {
  const { lang } = useLang();
  const isRtl = lang === 'ar';
  const t = (en: string, ar: string) => isRtl ? ar : en;
  const queryClient = useQueryClient();

  // --- API Queries ---
  const { 
    data: campaigns = [], 
    isLoading, 
    isError, 
    refetch 
  } = useQuery<Campaign[]>({
    queryKey: ['campaigns'],
    queryFn: async () => {
      const res = await api.get('/admin/campaigns');
      return (res.data || []).map((c: any) => ({
        ...c,
        id: c.id.toString(),
        systemPrompt: c.evaluation_prompt || '',
        color: c.color || '#6366f1',
        passThreshold: c.passThreshold || 75,
        rubricItems: c.rubricItems || [],
        activeAgents: 0,
        totalEvaluations: 0,
      }));
    },
  });

  // --- Mutations ---
  const createMutation = useMutation({
    mutationFn: (newCamp: any) => api.post('/admin/campaigns', newCamp),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success(t('Campaign created successfully', 'تم إنشاء الحملة بنجاح'));
      setIsCreating(false);
      setEditMode(false);
      // Select the newly created campaign
      const created = {
        ...res.data,
        id: res.data.id.toString(),
        systemPrompt: res.data.evaluation_prompt,
        color: '#6366f1',
        passThreshold: 75,
        rubricItems: [],
        activeAgents: 0,
        totalEvaluations: 0,
      };
      setSelectedCampaign(created);
    },
    onError: (error: any) => {
      const msg = error.response?.data?.detail || 'Failed to create campaign';
      toast.error(t(msg, 'فشل في إنشاء الحملة'));
    }
  });

  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [promptExpanded, setPromptExpanded] = useState(true);

  const [form, setForm] = useState<Partial<Campaign>>({
    name: '',
    description: '',
    passThreshold: 75,
    systemPrompt: '',
    rubricItems: [],
    color: '#6366f1',
  });

  const colorOptions = ['#6366f1', '#22c55e', '#f59e0b', '#3b82f6', '#ec4899', '#14b8a6', '#f97316', '#a855f7'];

  const handleSelectCampaign = (camp: Campaign) => {
    setSelectedCampaign(camp);
    setForm({ ...camp });
    setEditMode(false);
    setIsCreating(false);
  };

  const handleCreate = () => {
    setSelectedCampaign(null);
    setForm({
      name: '',
      description: '',
      passThreshold: 75,
      systemPrompt: '',
      rubricItems: [],
      color: '#6366f1',
    });
    setIsCreating(true);
    setEditMode(true);
  };

  const handleSave = () => {
    if (isCreating) {
      // Map frontend fields to backend schema
      const payload = {
        name: form.name,
        description: form.description,
        evaluation_prompt: form.systemPrompt
      };
      createMutation.mutate(payload);
    } else if (selectedCampaign) {
      // Update logic would go here if API supported it
      toast.info(t('Update functionality coming soon', 'خاصية التعديل ستتوفر قريباً'));
      setEditMode(false);
    }
  };

  const addRubricItem = () => {
    const newItem: RubricItem = {
      id: `r${Date.now()}`,
      category: '',
      categoryAr: '',
      maxScore: 20,
      criteria: [''],
      weight: 20,
    };
    setForm(prev => ({ ...prev, rubricItems: [...(prev.rubricItems || []), newItem] }));
  };

  const updateRubricItem = (idx: number, updates: Partial<RubricItem>) => {
    setForm(prev => ({
      ...prev,
      rubricItems: (prev.rubricItems || []).map((item, i) => i === idx ? { ...item, ...updates } : item),
    }));
  };

  const removeRubricItem = (idx: number) => {
    setForm(prev => ({
      ...prev,
      rubricItems: (prev.rubricItems || []).filter((_, i) => i !== idx),
    }));
  };

  const addCriteria = (rubricIdx: number) => {
    updateRubricItem(rubricIdx, {
      criteria: [...(form.rubricItems?.[rubricIdx]?.criteria || []), ''],
    });
  };

  const updateCriteria = (rubricIdx: number, critIdx: number, value: string) => {
    const criteria = [...(form.rubricItems?.[rubricIdx]?.criteria || [])];
    criteria[critIdx] = value;
    updateRubricItem(rubricIdx, { criteria });
  };

  const removeCriteria = (rubricIdx: number, critIdx: number) => {
    const criteria = (form.rubricItems?.[rubricIdx]?.criteria || []).filter((_, i) => i !== critIdx);
    updateRubricItem(rubricIdx, { criteria });
  };

  const totalWeight = (form?.rubricItems || []).reduce((s, i) => s + (i.maxScore || 0), 0);

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-white">{t('Campaign Manager', 'مدير الحملات')}</h1>
          <p className="text-sm text-slate-500 mt-0.5">{t('Create and manage evaluation rubrics for different call types', 'إنشاء وإدارة معايير التقييم لأنواع المكالمات المختلفة')}</p>
        </div>
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          {t('New Campaign', 'حملة جديدة')}
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Campaign List */}
        <div className="xl:col-span-1 space-y-3">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">{t('Campaigns', 'الحملات')} ({campaigns.length})</p>
            {isLoading && <Loader2 size={12} className="text-slate-500 animate-spin" />}
          </div>

          {isLoading && campaigns.length === 0 && (
            <div className="py-20 flex flex-col items-center justify-center text-center">
              <Loader2 size={30} className="text-indigo-500 animate-spin mb-4" />
              <p className="text-sm text-slate-500">{t('Loading campaigns...', 'جاري تحميل الحملات...')}</p>
            </div>
          )}

          {isError && (
            <div className="p-6 border border-red-500/20 bg-red-500/5 rounded-xl text-center">
              <AlertCircle size={24} className="text-red-400 mx-auto mb-2" />
              <p className="text-sm text-red-400 mb-3">{t('Failed to load campaigns', 'فشل تحميل الحملات')}</p>
              <button 
                onClick={() => refetch()}
                className="text-xs text-red-400 underline hover:text-red-300"
              >
                {t('Try Again', 'إعادة المحاولة')}
              </button>
            </div>
          )}

          {!isLoading && campaigns.length === 0 && !isError && (
            <div className="py-20 border border-dashed border-slate-800 rounded-xl flex flex-col items-center justify-center text-center px-4">
              <BookOpen size={30} className="text-slate-700 mb-3" />
              <p className="text-sm text-slate-600">{t('No campaigns found', 'لا توجد حملات')}</p>
            </div>
          )}

          {campaigns.map(camp => (
            <div
              key={camp.id}
              onClick={() => handleSelectCampaign(camp)}
              className={`bg-[#111827] border rounded-xl p-4 cursor-pointer transition-all hover:border-slate-700/60
                ${selectedCampaign?.id === camp.id ? 'border-indigo-500/40 bg-indigo-500/5' : 'border-slate-800/60'}`}
            >
              <div className="flex items-start gap-3">
                <div className="w-3 h-3 rounded-full mt-1 flex-shrink-0" style={{ backgroundColor: camp.color }} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">{camp.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{camp.description}</p>
                </div>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                <div>
                  <p className="text-sm font-semibold text-white">{camp.totalEvaluations}</p>
                  <p className="text-[10px] text-slate-600">{t('Evals', 'تقييم')}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{camp.activeAgents}</p>
                  <p className="text-[10px] text-slate-600">{t('Agents', 'وكلاء')}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold" style={{ color: camp.color }}>{camp.passThreshold}%</p>
                  <p className="text-[10px] text-slate-600">{t('Pass', 'نجاح')}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Campaign Editor */}
        <div className="xl:col-span-2">
          {(selectedCampaign || isCreating) ? (
            <div className="bg-[#111827] border border-slate-800/60 rounded-xl overflow-hidden">
              {/* Editor header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800/60">
                <div className="flex items-center gap-3">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: editMode ? form.color : selectedCampaign?.color }}
                  />
                  <h2 className="text-sm font-semibold text-white">
                    {isCreating ? t('New Campaign', 'حملة جديدة') : editMode ? t('Editing:', 'تعديل:') : ''} {!isCreating && (editMode ? form.name : selectedCampaign?.name)}
                  </h2>
                </div>
                <div className="flex items-center gap-2">
                  {!editMode ? (
                    <>
                      <button className="p-2 text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 rounded-lg transition-colors">
                        <Copy size={14} />
                      </button>
                      <button
                        onClick={() => setEditMode(true)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                      >
                        <Edit2 size={13} /> {t('Edit', 'تعديل')}
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => { setEditMode(false); setIsCreating(false); if (!selectedCampaign) setSelectedCampaign(null); }}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-700/50 text-sm text-slate-400 hover:text-slate-200 transition-colors"
                      >
                        <X size={13} /> {t('Cancel', 'إلغاء')}
                      </button>
                      <button
                        onClick={handleSave}
                        className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
                      >
                        <Save size={13} /> {t('Save', 'حفظ')}
                      </button>
                    </>
                  )}
                </div>
              </div>

              <div className="p-5 space-y-6 max-h-[calc(100vh-250px)] overflow-y-auto">
                {/* Basic Info */}
                <div className="space-y-4">
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('Basic Information', 'المعلومات الأساسية')}</h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-slate-500 mb-1.5 block">{t('Campaign Name', 'اسم الحملة')} *</label>
                      {editMode ? (
                        <input
                          type="text"
                          value={form.name || ''}
                          onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                          className="w-full bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
                          placeholder={t('e.g. Sales Excellence Q2', 'مثال: تميز المبيعات الربع الثاني')}
                        />
                      ) : (
                        <p className="text-sm text-slate-300 py-2">{selectedCampaign?.name}</p>
                      )}
                    </div>

                    <div>
                      <label className="text-xs text-slate-500 mb-1.5 block">{t('Pass Threshold (%)', 'حد النجاح (%)')}</label>
                      {editMode ? (
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={form.passThreshold || 75}
                          onChange={e => setForm(p => ({ ...p, passThreshold: parseInt(e.target.value) }))}
                          className="w-full bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
                        />
                      ) : (
                        <p className="text-sm text-slate-300 py-2">{selectedCampaign?.passThreshold}%</p>
                      )}
                    </div>
                  </div>

                  <div>
                    <label className="text-xs text-slate-500 mb-1.5 block">{t('Description', 'الوصف')}</label>
                    {editMode ? (
                      <textarea
                        rows={2}
                        value={form.description || ''}
                        onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                        className="w-full bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 resize-none transition-colors"
                        placeholder={t('What type of calls does this campaign evaluate?', 'ما نوع المكالمات التي تقيمها هذه الحملة؟')}
                      />
                    ) : (
                      <p className="text-sm text-slate-400 leading-relaxed">{selectedCampaign?.description}</p>
                    )}
                  </div>

                  {editMode && (
                    <div>
                      <label className="text-xs text-slate-500 mb-2 block">{t('Campaign Color', 'لون الحملة')}</label>
                      <div className="flex items-center gap-2">
                        {colorOptions.map(color => (
                          <button
                            key={color}
                            onClick={() => setForm(p => ({ ...p, color }))}
                            className={`w-7 h-7 rounded-full transition-all ${form.color === color ? 'ring-2 ring-offset-2 ring-offset-[#111827] ring-white scale-110' : 'hover:scale-105'}`}
                            style={{ backgroundColor: color }}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* System Prompt */}
                <div>
                  <button
                    onClick={() => setPromptExpanded(!promptExpanded)}
                    className="w-full flex items-center justify-between mb-3"
                  >
                    <div className="flex items-center gap-2">
                      <Sparkles size={14} className="text-indigo-400" />
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('AI System Prompt', 'نظام مطالبة الذكاء الاصطناعي')}</h3>
                    </div>
                    {promptExpanded ? <ChevronUp size={14} className="text-slate-600" /> : <ChevronDown size={14} className="text-slate-600" />}
                  </button>

                  {promptExpanded && (
                    editMode ? (
                      <textarea
                        rows={6}
                        value={form.systemPrompt || ''}
                        onChange={e => setForm(p => ({ ...p, systemPrompt: e.target.value }))}
                        className="w-full bg-slate-900 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 font-mono focus:outline-none focus:border-indigo-500/50 resize-none transition-colors"
                        placeholder={t('You are an expert call quality evaluator. Analyze the transcript and...', 'أنت محلل جودة مكالمات خبير. حلل النص و...')}
                      />
                    ) : (
                      <div className="bg-slate-900/50 border border-slate-700/30 rounded-lg p-4">
                        <p className="text-xs text-slate-400 font-mono leading-relaxed">{selectedCampaign?.systemPrompt}</p>
                      </div>
                    )
                  )}
                </div>

                {/* Rubric Items */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Target size={14} className="text-amber-400" />
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('Evaluation Rubric', 'معايير التقييم')}</h3>
                      <span className="text-xs text-slate-600">({t('Total:', 'الإجمالي:')} {totalWeight} {t('pts', 'نقطة')})</span>
                    </div>
                    {editMode && (
                      <button
                        onClick={addRubricItem}
                        className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1.5 rounded-lg transition-colors"
                      >
                        <Plus size={12} /> {t('Add Category', 'إضافة فئة')}
                      </button>
                    )}
                  </div>

                  <div className="space-y-3">
                    {(editMode ? form.rubricItems : selectedCampaign?.rubricItems)?.map((item, idx) => (
                      <div
                        key={item.id}
                        className={`border rounded-xl transition-colors ${expandedId === item.id ? 'border-indigo-500/30 bg-indigo-500/5' : 'border-slate-700/30 bg-slate-800/20'}`}
                      >
                        <div
                          className="flex items-center gap-3 p-4 cursor-pointer"
                          onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                        >
                          {editMode && <GripVertical size={14} className="text-slate-700 flex-shrink-0" />}
                          <div className="flex-1 min-w-0">
                            {editMode ? (
                              <input
                                type="text"
                                value={item.category}
                                onChange={e => { e.stopPropagation(); updateRubricItem(idx, { category: e.target.value }); }}
                                onClick={e => e.stopPropagation()}
                                className="bg-transparent border-b border-slate-700/50 text-sm text-white focus:outline-none focus:border-indigo-500 pb-0.5 w-full"
                                placeholder={t('Category name...', 'اسم الفئة...')}
                              />
                            ) : (
                              <p className="text-sm text-white font-medium">{item.category}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-3 flex-shrink-0">
                            {editMode ? (
                              <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                                <input
                                  type="number"
                                  value={item.maxScore}
                                  onChange={e => updateRubricItem(idx, { maxScore: parseInt(e.target.value) || 0 })}
                                  className="w-14 bg-slate-800 border border-slate-700/50 rounded-lg px-2 py-1 text-sm text-slate-300 text-center focus:outline-none"
                                />
                                <span className="text-xs text-slate-600">{t('pts', 'نقطة')}</span>
                                <button
                                  onClick={e => { e.stopPropagation(); removeRubricItem(idx); }}
                                  className="text-red-500/60 hover:text-red-400 transition-colors"
                                >
                                  <Trash2 size={13} />
                                </button>
                              </div>
                            ) : (
                              <span className="text-xs font-semibold text-amber-400">{item.maxScore} {t('pts', 'نقطة')}</span>
                            )}
                            {expandedId === item.id ? <ChevronUp size={13} className="text-slate-600" /> : <ChevronDown size={13} className="text-slate-600" />}
                          </div>
                        </div>

                        {expandedId === item.id && (
                          <div className="px-4 pb-4">
                            <div className="border-t border-slate-700/30 pt-3">
                              <p className="text-[11px] text-slate-600 uppercase tracking-wider mb-2">{t('Evaluation Criteria', 'معايير التقييم')}</p>
                              <div className="space-y-1.5">
                                {item.criteria.map((crit, critIdx) => (
                                  <div key={critIdx} className="flex items-center gap-2">
                                    <CheckCircle size={12} className="text-slate-700 flex-shrink-0" />
                                    {editMode ? (
                                      <>
                                        <input
                                          type="text"
                                          value={crit}
                                          onChange={e => updateCriteria(idx, critIdx, e.target.value)}
                                          className="flex-1 bg-slate-800/50 border border-slate-700/40 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
                                          placeholder={t('Criterion description...', 'وصف المعيار...')}
                                        />
                                        <button
                                          onClick={() => removeCriteria(idx, critIdx)}
                                          className="text-slate-700 hover:text-red-400 transition-colors"
                                        >
                                          <X size={12} />
                                        </button>
                                      </>
                                    ) : (
                                      <span className="text-xs text-slate-400">{crit}</span>
                                    )}
                                  </div>
                                ))}
                                {editMode && (
                                  <button
                                    onClick={() => addCriteria(idx)}
                                    className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-400 transition-colors ml-5"
                                  >
                                    <Plus size={11} /> {t('Add criterion', 'إضافة معيار')}
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Stats (view mode) */}
                {!editMode && selectedCampaign && (
                  <div>
                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">{t('Campaign Statistics', 'إحصائيات الحملة')}</h3>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { icon: BarChart3, label: t('Total Evaluations', 'إجمالي التقييمات'), value: selectedCampaign.totalEvaluations, color: 'text-indigo-400' },
                        { icon: Users, label: t('Active Agents', 'الوكلاء النشطون'), value: selectedCampaign.activeAgents, color: 'text-green-400' },
                        { icon: Target, label: t('Pass Threshold', 'حد النجاح'), value: `${selectedCampaign.passThreshold}%`, color: 'text-amber-400' },
                      ].map((stat, i) => (
                        <div key={i} className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-4 text-center">
                          <stat.icon size={18} className={`mx-auto mb-2 ${stat.color}`} />
                          <p className={`text-lg font-bold ${stat.color}`}>{stat.value}</p>
                          <p className="text-[10px] text-slate-600 mt-0.5">{stat.label}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[400px] bg-[#111827] border border-dashed border-slate-700/40 rounded-xl flex flex-col items-center justify-center text-center p-10">
              <BookOpen size={40} className="text-slate-700 mb-4" />
              <p className="text-slate-500 text-sm mb-2">{t('Select a campaign to view details', 'اختر حملة لعرض التفاصيل')}</p>
              <p className="text-slate-700 text-xs mb-6">{t('or create a new one to get started', 'أو أنشئ حملة جديدة للبدء')}</p>
              <button
                onClick={handleCreate}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
              >
                <Plus size={15} />
                {t('Create Campaign', 'إنشاء حملة')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}