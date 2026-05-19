import { createBrowserRouter } from 'react-router';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { CampaignManager } from './pages/CampaignManager';
import { CallExplorer } from './pages/CallExplorer';
import { CallDetail } from './pages/CallDetail';
import { BusinessIntelligence } from './pages/BusinessIntelligence';
import { SuccessLibrary } from './pages/SuccessLibrary';
import { AgentProfile } from './pages/AgentProfile';
import { DataCenter } from './pages/DataCenter';
import { SystemHealth } from './pages/SystemHealth';
import { HRDashboard } from './pages/HRDashboard';
import { HRManagement } from './pages/HRManagement';
import { Login } from './pages/Login';
import { RoleGuard } from './components/auth/RoleGuard';
import { UserRole } from './lib/types';

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <p className="text-foreground text-lg font-semibold">404 — Page not found</p>
      <p className="text-muted-foreground text-sm mt-2">The requested route does not exist.</p>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    path: '/login',
    Component: Login,
  },
  {
    path: '/',
    Component: Layout,
    children: [
      { index: true, Component: Dashboard },
      { path: 'campaigns', element: <RoleGuard allowedRoles={[UserRole.ADMIN, UserRole.MANAGER, UserRole.QA]}><CampaignManager /></RoleGuard> },
      { path: 'calls', Component: CallExplorer },
      { path: 'calls/:id', Component: CallDetail },
      { path: 'intelligence', element: <RoleGuard allowedRoles={[UserRole.ADMIN, UserRole.MANAGER]}><BusinessIntelligence /></RoleGuard> },
      { path: 'success-library', Component: SuccessLibrary },
      { path: 'agents/:id', Component: AgentProfile },
      { path: 'data-center', element: <RoleGuard allowedRoles={[UserRole.ADMIN, UserRole.MANAGER]}><DataCenter /></RoleGuard> },
      { path: 'system-health', element: <RoleGuard allowedRoles={[UserRole.ADMIN]}><SystemHealth /></RoleGuard> },
      { path: 'hr', element: <RoleGuard allowedRoles={[UserRole.ADMIN, UserRole.HR_MANAGER, UserRole.QA]}><HRDashboard /></RoleGuard> },
      { path: 'hr/agents', element: <RoleGuard allowedRoles={[UserRole.ADMIN, UserRole.HR_MANAGER]}><HRManagement /></RoleGuard> },
      { path: '*', Component: NotFound },
    ],
  },
]);
