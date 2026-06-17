/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { RoleGuard } from '../components/auth/RoleGuard';
import { Sidebar } from '../components/layout/Sidebar';
import { TeamManagerWorkspace } from '../pages/TeamManagerWorkspace';
import { PERMISSIONS } from '../lib/roles';
import { UserRole } from '../lib/types';

const mockUseApp = vi.fn();
const mockGetTeamManagerDashboard = vi.fn();
const mockGetTeamManagerTeams = vi.fn();
const mockGetTeamManagerAgents = vi.fn();
const mockGetTeamManagerSalesReport = vi.fn();
const mockGetTeamManagerRevenueReport = vi.fn();
const mockGetTeamManagerConversionReport = vi.fn();
const mockGetTeamManagerAttendanceReport = vi.fn();
const mockGetTeamManagerKpis = vi.fn();
const mockGetTeamManagerTransferRequests = vi.fn();
const mockCreateTeamManagerTransferRequest = vi.fn();
const mockCancelTeamManagerTransferRequest = vi.fn();

vi.mock('../context/AppContext', () => ({
  useApp: () => mockUseApp(),
}));

vi.mock('../lib/api', () => ({
  getTeamManagerDashboard: () => mockGetTeamManagerDashboard(),
  getTeamManagerTeams: () => mockGetTeamManagerTeams(),
  getTeamManagerAgents: (...args: unknown[]) => mockGetTeamManagerAgents(...args),
  getTeamManagerSalesReport: () => mockGetTeamManagerSalesReport(),
  getTeamManagerRevenueReport: () => mockGetTeamManagerRevenueReport(),
  getTeamManagerConversionReport: () => mockGetTeamManagerConversionReport(),
  getTeamManagerAttendanceReport: () => mockGetTeamManagerAttendanceReport(),
  getTeamManagerKpis: (...args: unknown[]) => mockGetTeamManagerKpis(...args),
  getTeamManagerTransferRequests: () => mockGetTeamManagerTransferRequests(),
  createTeamManagerTransferRequest: (...args: unknown[]) => mockCreateTeamManagerTransferRequest(...args),
  cancelTeamManagerTransferRequest: (...args: unknown[]) => mockCancelTeamManagerTransferRequest(...args),
  getApiErrorMessage: () => 'Mock API error',
}));

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

describe('Team Manager workspace', () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.TEAM_MANAGER,
      currentUser: { id: 61, name: 'TM User', email: 'tm@example.com', role: UserRole.TEAM_MANAGER, avatar: 'TM' },
      sidebarCollapsed: false,
      setSidebarCollapsed: vi.fn(),
      piiMaskingEnabled: true,
      setPiiMaskingEnabled: vi.fn(),
      setCurrentUser: vi.fn(),
      setUserRole: vi.fn(),
    });

    const teams = [
      {
        team_id: 7,
        team_name: 'Cairo Sales',
        campaign_id: 2,
        campaign_name: 'Summer Retention',
        leader_id: 51,
        leader_name: 'TL User',
        agent_count: 5,
        sales: 21,
        revenue: 62000,
        conversion_rate: 58.5,
        average_qa_score: 83.1,
        attendance_rate: 97.2,
      },
      {
        team_id: 8,
        team_name: 'Delta Sales',
        campaign_id: 3,
        campaign_name: 'Upgrade Wave',
        leader_id: 52,
        leader_name: 'Second Leader',
        agent_count: 4,
        sales: 20,
        revenue: 63000,
        conversion_rate: 66.5,
        average_qa_score: 85.3,
        attendance_rate: 96.1,
      },
    ];

    mockGetTeamManagerDashboard.mockResolvedValue({
      total_teams: 2,
      total_agents: 9,
      total_sales: 41,
      total_revenue: 125000,
      average_conversion_rate: 62.5,
      average_qa_score: 84.2,
      attendance_rate: 96.7,
      teams,
      alerts: [{ type: 'kpi', message: 'Conversion rate needs attention', severity: 'warning', team_id: 7 }],
    });
    mockGetTeamManagerTeams.mockResolvedValue(teams);
    mockGetTeamManagerAgents.mockResolvedValue([
      {
        agent_id: 88,
        agent_name: 'Mina Agent',
        email: 'mina@example.com',
        team_id: 7,
        team_name: 'Cairo Sales',
        campaign_id: 2,
        campaign_name: 'Summer Retention',
        sales: 6,
        revenue: 18000,
        conversion_rate: 60,
        qa_score: 85.4,
        attendance_rate: 96,
        status: 'active',
      },
    ]);
    mockGetTeamManagerSalesReport.mockResolvedValue({ teams: [{ team_id: 7, team_name: 'Cairo Sales', sales: 21, total_calls: 34 }], total_sales: 41 });
    mockGetTeamManagerRevenueReport.mockResolvedValue({ teams: [{ team_id: 7, team_name: 'Cairo Sales', revenue: 62000 }], total_revenue: 125000 });
    mockGetTeamManagerConversionReport.mockResolvedValue({ teams: [{ team_id: 7, team_name: 'Cairo Sales', sales: 21, total_calls: 34, conversion_rate: 58.5 }], average_conversion_rate: 62.5 });
    mockGetTeamManagerAttendanceReport.mockResolvedValue({ records: [], attendance_rate: 96.7 });
    mockGetTeamManagerKpis.mockResolvedValue({
      month: '2026-06',
      total_sales: 41,
      total_revenue: 125000,
      average_qa_score: 84.2,
      average_conversion_rate: 62.5,
      attendance_rate: 96.7,
    });
    mockGetTeamManagerTransferRequests.mockResolvedValue([
      {
        id: 900,
        agent_id: 88,
        agent_name: 'Mina Agent',
        from_team_id: 7,
        from_team_name: 'Cairo Sales',
        to_team_id: 8,
        to_team_name: 'Delta Sales',
        requested_by_id: 61,
        requested_by_name: 'TM User',
        status: 'PENDING',
        reason: 'Balance capacity across teams',
        review_note: null,
        created_at: '2026-06-10T00:00:00.000Z',
        reviewed_at: null,
      },
    ]);
  });

  it('blocks users without the team manager workspace permission', () => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.AGENT,
      currentUser: { id: 12, name: 'Agent', email: 'agent@example.com', role: UserRole.AGENT, avatar: 'AG' },
    });

    const result = RoleGuard({
      requiredPermission: PERMISSIONS.VIEW_TEAM_MANAGER_WORKSPACE,
      children: <div>Team manager only</div>,
    }) as unknown as { props?: { to?: string } };

    expect(result?.props?.to).toBe('/');
  });

  it('shows team manager navigation in the sidebar', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(html).toContain('Manager Workspace');
    expect(html).toContain('Workflow Notes');
    expect(html).not.toContain('Agent Profiles');
  });

  it('renders team manager dashboard, reports, agents, and transfer requests', async () => {
    const client = createClient();
    const today = new Date();
    const rangeStart = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
    const rangeEnd = today.toISOString().slice(0, 10);
    const startParam = `${rangeStart}T00:00:00`;
    const endParam = `${rangeEnd}T23:59:59.999999`;
    await Promise.all([
      client.prefetchQuery({ queryKey: ['team-manager-dashboard', startParam, endParam], queryFn: () => mockGetTeamManagerDashboard() }),
      client.prefetchQuery({ queryKey: ['team-manager-agents', 'all', startParam, endParam], queryFn: () => mockGetTeamManagerAgents() }),
      client.prefetchQuery({ queryKey: ['team-manager-report-sales', startParam, endParam], queryFn: () => mockGetTeamManagerSalesReport() }),
      client.prefetchQuery({ queryKey: ['team-manager-report-revenue', startParam, endParam], queryFn: () => mockGetTeamManagerRevenueReport() }),
      client.prefetchQuery({ queryKey: ['team-manager-report-conversion', startParam, endParam], queryFn: () => mockGetTeamManagerConversionReport() }),
      client.prefetchQuery({ queryKey: ['team-manager-report-attendance', startParam, endParam], queryFn: () => mockGetTeamManagerAttendanceReport() }),
      client.prefetchQuery({ queryKey: ['team-manager-kpis', startParam, endParam], queryFn: () => mockGetTeamManagerKpis() }),
      client.prefetchQuery({ queryKey: ['team-manager-transfer-requests'], queryFn: () => mockGetTeamManagerTransferRequests() }),
    ]);

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <TeamManagerWorkspace />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(html).toContain('Managed Teams');
    expect(html).toContain('Cairo Sales');
    expect(html).toContain('Mina Agent');
    expect(html).toContain('Reports');
    expect(html).toContain('New Transfer Request');
    expect(html).toContain('Balance capacity across teams');
  });
});
