import { Outlet, useLocation } from 'react-router';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

const pageTitles: Record<string, string> = {
  '/': 'Operations Dashboard',
  '/campaigns': 'Campaign Management',
  '/intelligence': 'Business Intelligence Hub',
  '/success-library': 'Success Library',
  '/data-center': 'Data Center & Exports',
  '/system-health': 'System Health Monitor',
};

function getTitle(pathname: string): string {
  if (pathname.startsWith('/calls/')) return 'Call Analysis Engine';
  if (pathname.startsWith('/agents/')) return 'Agent Momentum Profile';
  return pageTitles[pathname] || 'VoiceQA Enterprise';
}

export function Layout() {
  const location = useLocation();
  const title = getTitle(location.pathname);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title={title} />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
