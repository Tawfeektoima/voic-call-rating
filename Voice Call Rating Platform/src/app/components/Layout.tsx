import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router';
import {
  LayoutDashboard, Phone, BookOpen, Users, Settings, Bell, Search,
  ChevronDown, LogOut, Globe, Menu, X, Zap, Shield
} from 'lucide-react';
import { useLang } from '../context/LangContext';

const navItems = [
  { to: '/', label: 'Dashboard', labelAr: 'لوحة التحكم', icon: LayoutDashboard, exact: true },
  { to: '/calls', label: 'Call Explorer', labelAr: 'مستكشف المكالمات', icon: Phone },
  { to: '/campaigns', label: 'Campaigns', labelAr: 'الحملات', icon: BookOpen },
  { to: '/agents', label: 'Agent Analytics', labelAr: 'تحليلات الوكلاء', icon: Users },
];

export function Layout() {
  const { lang, setLang } = useLang();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const isRtl = lang === 'ar';
  const t = (en: string, ar: string) => isRtl ? ar : en;

  return (
    <div className={`flex h-screen bg-[#070b14] text-slate-100 overflow-hidden ${isRtl ? 'rtl' : 'ltr'}`}>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 z-20 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 z-30 w-64 flex flex-col bg-[#0d1225] border-r border-slate-800/60 transition-transform duration-300
        ${isRtl ? 'right-0 border-r-0 border-l border-slate-800/60' : 'left-0'}
        ${sidebarOpen ? 'translate-x-0' : isRtl ? 'translate-x-full lg:translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-800/60">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center flex-shrink-0">
            <Zap size={16} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white tracking-wide">VoiceQA</p>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest">{t('Enterprise', 'المؤسسة')}</p>
          </div>
          <button className="ml-auto lg:hidden text-slate-400 hover:text-white" onClick={() => setSidebarOpen(false)}>
            <X size={18} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest px-3 mb-2">
            {t('Main Menu', 'القائمة الرئيسية')}
          </p>
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150
                ${isActive
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/20'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 border border-transparent'
                }`
              }
            >
              <item.icon size={17} className="flex-shrink-0" />
              <span>{isRtl ? item.labelAr : item.label}</span>
            </NavLink>
          ))}

          <div className="pt-4">
            <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest px-3 mb-2">
              {t('System', 'النظام')}
            </p>
            <NavLink
              to="/settings"
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 border
                ${isActive ? 'bg-indigo-600/20 text-indigo-400 border-indigo-500/20' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 border-transparent'}`
              }
            >
              <Settings size={17} />
              <span>{t('Settings', 'الإعدادات')}</span>
            </NavLink>
          </div>
        </nav>

        {/* Live status */}
        <div className="px-4 py-3 border-t border-slate-800/60">
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/10 border border-green-500/20">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse flex-shrink-0" />
            <span className="text-xs text-green-400">{t('AI Engine Online', 'محرك الذكاء الاصطناعي متصل')}</span>
          </div>
        </div>

        {/* User */}
        <div className="px-4 pb-4 border-t border-slate-800/60 pt-3">
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-800/50 transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs font-semibold text-white flex-shrink-0">
                QA
              </div>
              <div className="flex-1 text-left min-w-0">
                <p className="text-sm text-slate-200 truncate">{t('QA Supervisor', 'مشرف ضمان الجودة')}</p>
                <p className="text-[11px] text-slate-500 truncate">supervisor@company.com</p>
              </div>
              <ChevronDown size={14} className="text-slate-500 flex-shrink-0" />
            </button>
            {userMenuOpen && (
              <div className="absolute bottom-full mb-1 left-0 right-0 bg-[#1a2235] border border-slate-700/60 rounded-lg shadow-xl py-1 z-50">
                <button className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700/40 hover:text-white transition-colors">
                  <Shield size={14} /> {t('My Profile', 'ملفي الشخصي')}
                </button>
                <button className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700/40 hover:text-white transition-colors">
                  <LogOut size={14} /> {t('Sign Out', 'تسجيل الخروج')}
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top header */}
        <header className="h-14 flex items-center gap-4 px-5 border-b border-slate-800/60 bg-[#0d1225]/80 backdrop-blur-sm flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-slate-400 hover:text-white"
          >
            <Menu size={20} />
          </button>

          {/* Search */}
          <div className="flex-1 max-w-md relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder={t('Search calls, agents, campaigns...', 'بحث في المكالمات والوكلاء والحملات...')}
              className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 focus:bg-slate-800 transition-colors"
            />
          </div>

          <div className="flex items-center gap-2 ml-auto">
            {/* Language toggle */}
            <button
              onClick={() => setLang(lang === 'en' ? 'ar' : 'en')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <Globe size={13} />
              {lang === 'en' ? 'عربي' : 'English'}
            </button>

            {/* Notifications */}
            <div className="relative">
              <button
                onClick={() => setNotifOpen(!notifOpen)}
                className="relative p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
              >
                <Bell size={17} />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
              </button>
              {notifOpen && (
                <div className="absolute top-full right-0 mt-2 w-80 bg-[#1a2235] border border-slate-700/60 rounded-xl shadow-2xl z-50 overflow-hidden">
                  <div className="px-4 py-3 border-b border-slate-700/60 flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-200">{t('Notifications', 'الإشعارات')}</span>
                    <span className="text-xs text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full">3 {t('new', 'جديد')}</span>
                  </div>
                  {[
                    { icon: '⚠️', text: t("James Park's score dropped below threshold", 'انخفضت نقاط جيمس باك دون الحد'), time: '5m ago' },
                    { icon: '✅', text: t('47 calls processed successfully', '47 مكالمة تمت معالجتها بنجاح'), time: '12m ago' },
                    { icon: '🔴', text: t('1 call failed processing (audio corrupt)', 'فشلت معالجة مكالمة واحدة'), time: '1h ago' },
                  ].map((n, i) => (
                    <div key={i} className="px-4 py-3 hover:bg-slate-700/20 transition-colors border-b border-slate-800/40 last:border-0">
                      <div className="flex gap-3">
                        <span className="text-base flex-shrink-0">{n.icon}</span>
                        <div>
                          <p className="text-xs text-slate-300">{n.text}</p>
                          <p className="text-[10px] text-slate-600 mt-0.5">{n.time}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs font-semibold text-white">
              QA
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
