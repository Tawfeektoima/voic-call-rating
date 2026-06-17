/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { RoleGuard } from '../components/auth/RoleGuard';
import { Sidebar } from '../components/layout/Sidebar';
import { TeamLeaderDashboard } from '../pages/TeamLeaderDashboard';
import { TeamLeaderAgents } from '../pages/TeamLeaderAgents';
import { TeamLeaderCalls } from '../pages/TeamLeaderCalls';
import { TeamLeaderKpis } from '../pages/TeamLeaderKpis';
import { UserRole } from '../lib/types';

const mockUseApp = vi.fn();
const mockGetTeamLeaderDashboard = vi.fn();
const mockGetTeamLeaderTeams = vi.fn();
const mockGetTeamLeaderAgents = vi.fn();
const mockGetTeamLeaderCalls = vi.fn();
const mockGetTeamLeaderKpis = vi.fn();

vi.mock('../context/AppContext', () => ({
  useApp: () => mockUseApp(),
}));

vi.mock('../lib/api', () => ({
  getTeamLeaderDashboard: () => mockGetTeamLeaderDashboard(),
  getTeamLeaderTeams: () => mockGetTeamLeaderTeams(),
  getTeamLeaderAgents: (...args: unknown[]) => mockGetTeamLeaderAgents(...args),
  getTeamLeaderCalls: (...args: unknown[]) => mockGetTeamLeaderCalls(...args),
  getTeamLeaderKpis: (...args: unknown[]) => mockGetTeamLeaderKpis(...args),
}));

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

describe('Team Leader workspace', () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.TEAM_LEADER,
      currentUser: { id: 51, name: 'TL User', email: 'tl@example.com', role: UserRole.TEAM_LEADER, avatar: 'TL' },
      sidebarCollapsed: false,
      setSidebarCollapsed: vi.fn(),
      piiMaskingEnabled: true,
      setPiiMaskingEnabled: vi.fn(),
      setCurrentUser: vi.fn(),
      setUserRole: vi.fn(),
    });

    mockGetTeamLeaderDashboard.mockResolvedValue({
      team_count: 2,
      agent_count: 9,
      average_qa_score: 84.2,
      attendance_rate: 0,
      sales: 41,
      revenue: 125000,
      conversion_rate: 62.5,
      pending_notes_count: 4,
      pending_transfer_requests_count: 1,
    });
    mockGetTeamLeaderTeams.mockResolvedValue([
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
        attendance_rate: 0,
      },
    ]);
    mockGetTeamLeaderAgents.mockResolvedValue([
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
        attendance_rate: 0,
        status: 'active',
      },
    ]);
    mockGetTeamLeaderCalls.mockResolvedValue({
      items: [
        {
          id: 301,
          employee_id: 88,
          employee_name: 'Mina Agent',
          campaign_id: 2,
          campaign_name: 'Summer Retention',
          status: 'evaluated',
          evaluation_score: 86.2,
          overridden_score: null,
          audio_duration: 187,
          created_at: '2026-06-10T00:00:00.000Z',
        },
      ],
      total: 1,
    });
    mockGetTeamLeaderKpis.mockResolvedValue({
      month: '2026-06',
      total_sales: 41,
      total_revenue: 125000,
      average_qa_score: 84.2,
      average_conversion_rate: 62.5,
      attendance_rate: 0,
    });
  });

  it('blocks non-team-leader roles from team leader routes', () => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.AGENT,
      currentUser: { id: 12, name: 'Agent', email: 'agent@example.com', role: UserRole.AGENT, avatar: 'AG' },
    });

    const result = RoleGuard({
      allowedRoles: [UserRole.ADMIN, UserRole.TEAM_LEADER],
      children: <div>Team leader only</div>,
    }) as unknown as { props?: { to?: string } };

    expect(result?.props?.to).toBe('/');
  });

  it('shows team leader navigation links in the sidebar', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(html).toContain('Team Overview');
    expect(html).toContain('Team Agents');
    expect(html).toContain('Team Calls');
    expect(html).toContain('Team KPIs');
    expect(html).not.toContain('Agent Profiles');
    expect(html).not.toContain('Dashboard');
  });

  it('renders the dashboard, agents, calls, and kpis pages from prefetched data', async () => {
    const client = createClient();
    const currentMonth = new Date().toISOString().slice(0, 7);
    await Promise.all([
      client.prefetchQuery({ queryKey: ['team-leader-dashboard'], queryFn: () => mockGetTeamLeaderDashboard() }),
      client.prefetchQuery({ queryKey: ['team-leader-teams'], queryFn: () => mockGetTeamLeaderTeams() }),
      client.prefetchQuery({ queryKey: ['team-leader-agents', 'all'], queryFn: () => mockGetTeamLeaderAgents() }),
      client.prefetchQuery({ queryKey: ['team-leader-calls', 0], queryFn: () => mockGetTeamLeaderCalls() }),
      client.prefetchQuery({ queryKey: ['team-leader-kpis', currentMonth], queryFn: () => mockGetTeamLeaderKpis() }),
    ]);

    const dashboardHtml = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <TeamLeaderDashboard />
        </MemoryRouter>
      </QueryClientProvider>
    );
    const agentsHtml = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <TeamLeaderAgents />
        </MemoryRouter>
      </QueryClientProvider>
    );
    const callsHtml = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <TeamLeaderCalls />
        </MemoryRouter>
      </QueryClientProvider>
    );
    const kpisHtml = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <TeamLeaderKpis />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(dashboardHtml).toContain('Operational Overview');
    expect(dashboardHtml).toContain('Cairo Sales');
    expect(dashboardHtml).toContain('Team context for KPI notes');
    expect(dashboardHtml).toContain('Open Notes Queue');
    expect(agentsHtml).toContain('Assigned agents');
    expect(agentsHtml).toContain('Mina Agent');
    expect(agentsHtml).toContain('KPI Follow-up');
    expect(callsHtml).toContain('Scoped call evaluations');
    expect(callsHtml).toContain('Request QA Review');
    expect(callsHtml).toContain('Add Note');
    expect(kpisHtml).toContain('Monthly KPIs');
    expect(kpisHtml).toContain('Total Revenue');
    expect(kpisHtml).toContain('Reporting month');
    expect(kpisHtml).toContain('Team context for KPI notes');
  });
});
