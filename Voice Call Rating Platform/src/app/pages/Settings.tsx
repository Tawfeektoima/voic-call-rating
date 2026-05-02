import { useState } from 'react';
import {
  Settings as SettingsIcon, User, Bell, Shield, Database, Cpu, Globe,
  Save, Eye, EyeOff, ChevronRight, Check
} from 'lucide-react';
import { useLang } from '../context/LangContext';

interface SettingsProps {
  lang: 'en' | 'ar';
}

export function Settings() {
  const { lang } = useLang();
  const isRtl = lang === 'ar';
  const t = (en: string, ar: string) => isRtl ? ar : en;

  const [activeSection, setActiveSection] = useState('general');
  const [saved, setSaved] = useState(false);
  const [showKey, setShowKey] = useState(false);

  const [settings, setSettings] = useState({
    siteName: 'VoiceQA Enterprise',
    defaultLanguage: 'en',
    qualityThreshold: 75,
    emailNotifications: true,
    webhookNotifications: false,
    autoProcess: true,
    retentionDays: 90,
    apiKey: 'sk-vqa-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    llmModel: 'gpt-4o',
    whisperModel: 'large-v3',
    maxConcurrent: 5,
  });

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const sections = [
    { id: 'general', label: t('General', 'عام'), icon: SettingsIcon },
    { id: 'ai', label: t('AI Configuration', 'إعداد الذكاء الاصطناعي'), icon: Cpu },
    { id: 'notifications', label: t('Notifications', 'الإشعارات'), icon: Bell },
    { id: 'security', label: t('Security & Access', 'الأمان والوصول'), icon: Shield },
    { id: 'data', label: t('Data & Storage', 'البيانات والتخزين'), icon: Database },
  ];

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white">{t('System Settings', 'إعدادات النظام')}</h1>
        <p className="text-sm text-slate-500 mt-0.5">{t('Configure your VoiceQA platform', 'تكوين منصة VoiceQA الخاصة بك')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <nav className="bg-[#111827] border border-slate-800/60 rounded-xl overflow-hidden">
            {sections.map(sec => (
              <button
                key={sec.id}
                onClick={() => setActiveSection(sec.id)}
                className={`w-full flex items-center justify-between px-4 py-3.5 text-sm transition-colors border-b border-slate-800/40 last:border-0
                  ${activeSection === sec.id
                    ? 'bg-indigo-600/20 text-indigo-400'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
                  }`}
              >
                <div className="flex items-center gap-3">
                  <sec.icon size={15} />
                  {sec.label}
                </div>
                <ChevronRight size={13} className="text-slate-600" />
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="lg:col-span-3 bg-[#111827] border border-slate-800/60 rounded-xl p-6">
          {activeSection === 'general' && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-white">{t('General Settings', 'الإعدادات العامة')}</h2>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-500 mb-1.5 block">{t('Platform Name', 'اسم المنصة')}</label>
                  <input
                    type="text"
                    value={settings.siteName}
                    onChange={e => setSettings(p => ({ ...p, siteName: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1.5 block">{t('Default Language', 'اللغة الافتراضية')}</label>
                  <select
                    value={settings.defaultLanguage}
                    onChange={e => setSettings(p => ({ ...p, defaultLanguage: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
                  >
                    <option value="en">English</option>
                    <option value="ar">العربية</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1.5 block">{t('Default Quality Threshold (%)', 'حد الجودة الافتراضي (%)')}</label>
                  <input
                    type="number"
                    min="0" max="100"
                    value={settings.qualityThreshold}
                    onChange={e => setSettings(p => ({ ...p, qualityThreshold: parseInt(e.target.value) }))}
                    className="w-32 bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
                  />
                </div>
              </div>
            </div>
          )}

          {activeSection === 'ai' && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-white">{t('AI Configuration', 'إعداد الذكاء الاصطناعي')}</h2>
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-xs text-amber-400">
                ⚠ {t('Changes to AI settings will affect all future evaluations. Existing evaluations will not be re-scored.', 'ستؤثر التغييرات على إعدادات الذكاء الاصطناعي على جميع التقييمات المستقبلية. لن يتم إعادة تقييم التقييمات الموجودة.')}
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-500 mb-1.5 block">{t('LLM Model', 'نموذج LLM')}</label>
                  <select
                    value={settings.llmModel}
                    onChange={e => setSettings(p => ({ ...p, llmModel: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
                  >
                    <option value="gpt-4o">GPT-4o (Recommended)</option>
                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                    <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1.5 block">{t('Whisper Model (Transcription)', 'نموذج Whisper (النسخ)')}</label>
                  <select
                    value={settings.whisperModel}
                    onChange={e => setSettings(p => ({ ...p, whisperModel: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
                  >
                    <option value="large-v3">WhisperX Large-v3 (Best Quality)</option>
                    <option value="medium">Whisper Medium (Balanced)</option>
                    <option value="small">Whisper Small (Fastest)</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1.5 block">{t('Max Concurrent Processing Jobs', 'الحد الأقصى لوظائف المعالجة المتزامنة')}</label>
                  <input
                    type="number"
                    min="1" max="20"
                    value={settings.maxConcurrent}
                    onChange={e => setSettings(p => ({ ...p, maxConcurrent: parseInt(e.target.value) }))}
                    className="w-32 bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1.5 block">{t('API Key', 'مفتاح API')}</label>
                  <div className="flex items-center gap-2">
                    <input
                      type={showKey ? 'text' : 'password'}
                      value={settings.apiKey}
                      onChange={e => setSettings(p => ({ ...p, apiKey: e.target.value }))}
                      className="flex-1 bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 font-mono focus:outline-none focus:border-indigo-500/50 transition-colors"
                    />
                    <button
                      onClick={() => setShowKey(!showKey)}
                      className="p-2.5 bg-slate-800 border border-slate-700/50 rounded-lg text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>
                <div className="flex items-center justify-between p-4 bg-slate-800/30 border border-slate-700/30 rounded-lg">
                  <div>
                    <p className="text-sm text-slate-300">{t('Auto-process uploads', 'المعالجة التلقائية للتحميلات')}</p>
                    <p className="text-xs text-slate-600 mt-0.5">{t('Automatically start evaluation after upload', 'بدء التقييم تلقائياً بعد التحميل')}</p>
                  </div>
                  <button
                    onClick={() => setSettings(p => ({ ...p, autoProcess: !p.autoProcess }))}
                    className={`w-11 h-6 rounded-full transition-colors relative ${settings.autoProcess ? 'bg-indigo-600' : 'bg-slate-700'}`}
                  >
                    <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all ${settings.autoProcess ? 'right-1' : 'left-1'}`} />
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'notifications' && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-white">{t('Notification Settings', 'إعدادات الإشعارات')}</h2>
              <div className="space-y-3">
                {[
                  { key: 'emailNotifications', label: t('Email Notifications', 'إشعارات البريد الإلكتروني'), desc: t('Receive email alerts for failed calls and at-risk agents', 'تلقي تنبيهات بالبريد للمكالمات الفاشلة والوكلاء في خطر') },
                  { key: 'webhookNotifications', label: t('Webhook Notifications', 'إشعارات Webhook'), desc: t('Push real-time events to your webhook URL', 'إرسال أحداث في الوقت الفعلي إلى رابط webhook الخاص بك') },
                ].map(item => (
                  <div key={item.key} className="flex items-center justify-between p-4 bg-slate-800/30 border border-slate-700/30 rounded-lg">
                    <div>
                      <p className="text-sm text-slate-300">{item.label}</p>
                      <p className="text-xs text-slate-600 mt-0.5">{item.desc}</p>
                    </div>
                    <button
                      onClick={() => setSettings(p => ({ ...p, [item.key]: !p[item.key as keyof typeof p] }))}
                      className={`w-11 h-6 rounded-full transition-colors relative ${settings[item.key as keyof typeof settings] ? 'bg-indigo-600' : 'bg-slate-700'}`}
                    >
                      <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all ${settings[item.key as keyof typeof settings] ? 'right-1' : 'left-1'}`} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSection === 'data' && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-white">{t('Data & Storage', 'البيانات والتخزين')}</h2>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-500 mb-1.5 block">{t('Data Retention Period (days)', 'فترة الاحتفاظ بالبيانات (أيام)')}</label>
                  <input
                    type="number"
                    min="30"
                    value={settings.retentionDays}
                    onChange={e => setSettings(p => ({ ...p, retentionDays: parseInt(e.target.value) }))}
                    className="w-32 bg-slate-800 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
                  />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: t('Total Storage Used', 'إجمالي التخزين المستخدم'), value: '47.3 GB', pct: 47 },
                    { label: t('Audio Files', 'الملفات الصوتية'), value: '38.1 GB', pct: 81 },
                    { label: t('Transcripts & Data', 'النصوص والبيانات'), value: '9.2 GB', pct: 19 },
                  ].map((s, i) => (
                    <div key={i} className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-4">
                      <p className="text-lg font-bold text-white">{s.value}</p>
                      <p className="text-[11px] text-slate-600 mt-0.5">{s.label}</p>
                      <div className="w-full bg-slate-800 rounded-full h-1 mt-2">
                        <div className="h-1 rounded-full bg-indigo-500" style={{ width: `${s.pct}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeSection === 'security' && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-white">{t('Security & Access Control', 'الأمان والتحكم في الوصول')}</h2>
              <div className="space-y-3">
                {[
                  { role: 'Administrator', perms: ['Full system access', 'User management', 'Campaign creation'], color: '#ef4444' },
                  { role: 'QA Supervisor', perms: ['View all calls', 'Override scores', 'Export reports'], color: '#f59e0b' },
                  { role: 'Agent', perms: ['View own calls', 'View own scores', 'View own transcripts'], color: '#22c55e' },
                ].map((r, i) => (
                  <div key={i} className="p-4 bg-slate-800/30 border border-slate-700/30 rounded-xl">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: r.color }} />
                      <p className="text-sm font-medium text-slate-200">{r.role}</p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {r.perms.map((p, j) => (
                        <span key={j} className="flex items-center gap-1 text-[11px] text-slate-400 bg-slate-700/30 px-2 py-0.5 rounded-full">
                          <Check size={10} className="text-green-500" /> {p}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Save button */}
          <div className="mt-8 pt-5 border-t border-slate-800/60 flex items-center justify-end gap-3">
            {saved && (
              <div className="flex items-center gap-1.5 text-sm text-green-400">
                <Check size={14} /> {t('Settings saved!', 'تم حفظ الإعدادات!')}
              </div>
            )}
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
            >
              <Save size={14} />
              {t('Save Changes', 'حفظ التغييرات')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}