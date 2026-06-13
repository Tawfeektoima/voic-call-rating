import { Outlet, useLocation, Navigate } from 'react-router';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useApp } from '../../context/AppContext';

const pageTitles: Record<string, string> = {
  '/':               'Operations Dashboard',
  '/campaigns':      'Campaign Management',
  '/calls':          'Call Explorer',
  '/intelligence':   'Business Intelligence Hub',
  '/success-library':'Success Library',
  '/data-center':    'Data Center & Exports',
  '/system-health':  'System Health Monitor',
  '/hr':             'HR Dashboard',
  '/hr/agents':      'Agent Directory',
  '/team-leader':    'Team Leader Overview',
  '/team-leader/agents': 'Team Leader Agents',
  '/team-leader/calls':  'Team Leader Calls',
  '/team-leader/kpis':   'Team Leader KPIs',
  '/team-manager':   'Team Manager Workspace',
  '/notes':          'Workflow Notes',
};

function getTitle(pathname: string): string {
  if (pageTitles[pathname]) return pageTitles[pathname];
  if (pathname.startsWith('/calls/'))  return 'Call Analysis Engine';
  if (pathname.startsWith('/agents/')) return 'Agent Momentum Profile';
  if (pathname.startsWith('/notes/'))  return 'Workflow Thread';
  return 'VoiceQA Enterprise';
}

export function Layout() {
  const location = useLocation();
  const title = getTitle(location.pathname);
  const { currentUser } = useApp();

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

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
