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
import { HRInterviews } from './pages/HRInterviews';
import { InterviewCandidateReview } from './pages/InterviewCandidateReview';
import { InterviewMcqReview } from './pages/InterviewMcqReview';
import { Login } from './pages/Login';
import { NotesInbox } from './pages/NotesInbox';
import { NoteThread } from './pages/NoteThread';
import { PublicInterviewPortal } from './pages/PublicInterviewPortal';
import { TeamLeaderDashboard } from './pages/TeamLeaderDashboard';
import { TeamLeaderAgents } from './pages/TeamLeaderAgents';
import { TeamLeaderCalls } from './pages/TeamLeaderCalls';
import { TeamLeaderKpis } from './pages/TeamLeaderKpis';
import { TeamManagerWorkspace } from './pages/TeamManagerWorkspace';
import { RoleGuard } from './components/auth/RoleGuard';
import { PERMISSIONS } from './lib/roles';
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
    path: '/interview-portal',
    Component: PublicInterviewPortal,
  },
  {
    path: '/',
    Component: Layout,
    children: [
      { index: true, element: <RoleGuard anyPermissions={[PERMISSIONS.VIEW_OWN_DASHBOARD, PERMISSIONS.VIEW_GLOBAL_DASHBOARD]}><Dashboard /></RoleGuard> },
      { path: 'campaigns', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_CAMPAIGNS}><CampaignManager /></RoleGuard> },
      { path: 'calls', element: <RoleGuard anyPermissions={[PERMISSIONS.VIEW_OWN_CALLS, PERMISSIONS.VIEW_RAW_CALLS]}><CallExplorer /></RoleGuard> },
      { path: 'calls/:id', element: <RoleGuard anyPermissions={[PERMISSIONS.VIEW_OWN_CALLS, PERMISSIONS.VIEW_RAW_CALLS]}><CallDetail /></RoleGuard> },
      { path: 'intelligence', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_BI}><BusinessIntelligence /></RoleGuard> },
      { path: 'success-library', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_SUCCESS_LIBRARY}><SuccessLibrary /></RoleGuard> },
      { path: 'agents/:id', element: <RoleGuard allowedRoles={[UserRole.AGENT, UserRole.ADMIN, UserRole.QA]} anyPermissions={[PERMISSIONS.VIEW_OWN_PROFILE, PERMISSIONS.VIEW_AGENT_PROFILES]}><AgentProfile /></RoleGuard> },
      { path: 'data-center', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_DATA_CENTER}><DataCenter /></RoleGuard> },
      { path: 'system-health', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_SYSTEM_HEALTH}><SystemHealth /></RoleGuard> },
      { path: 'hr', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_HR_DASHBOARD}><HRDashboard /></RoleGuard> },
      { path: 'hr/agents', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_EMPLOYEES}><HRManagement /></RoleGuard> },
      { path: 'hr/interviews', element: <RoleGuard anyPermissions={[PERMISSIONS.MANAGE_INTERVIEW_JOBS, PERMISSIONS.VIEW_INTERVIEW_CANDIDATES]}><HRInterviews /></RoleGuard> },
      { path: 'hr/interviews/candidates/:candidateId/review', element: <RoleGuard anyPermissions={[PERMISSIONS.VIEW_INTERVIEW_CANDIDATES]}><InterviewCandidateReview /></RoleGuard> },
      { path: 'hr/interviews/candidates/:candidateId/mcq-review', element: <RoleGuard anyPermissions={[PERMISSIONS.VIEW_INTERVIEW_CANDIDATES]}><InterviewMcqReview /></RoleGuard> },
      { path: 'team-leader', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_TEAM_LEADER_WORKSPACE}><TeamLeaderDashboard /></RoleGuard> },
      { path: 'team-leader/agents', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_TEAM_LEADER_WORKSPACE}><TeamLeaderAgents /></RoleGuard> },
      { path: 'team-leader/calls', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_TEAM_LEADER_WORKSPACE}><TeamLeaderCalls /></RoleGuard> },
      { path: 'team-leader/kpis', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_TEAM_LEADER_WORKSPACE}><TeamLeaderKpis /></RoleGuard> },
      { path: 'team-manager', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_TEAM_MANAGER_WORKSPACE}><TeamManagerWorkspace /></RoleGuard> },
      { path: 'notes', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_NOTES}><NotesInbox /></RoleGuard> },
      { path: 'notes/:noteId', element: <RoleGuard requiredPermission={PERMISSIONS.VIEW_NOTES}><NoteThread /></RoleGuard> },
      { path: '*', Component: NotFound },
    ],
  },
]);
