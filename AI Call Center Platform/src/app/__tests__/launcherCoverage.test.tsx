/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes } from 'react-router';
import { Dashboard } from '../pages/Dashboard';
import { AgentProfile } from '../pages/AgentProfile';
import { SystemHealth } from '../pages/SystemHealth';
import { UserRole } from '../lib/types';

const mockUseApp = vi.fn();
const mockUseDashboard = vi.fn();
const mockUseCalls = vi.fn();
const mockUseLeads = vi.fn();
const mockUseSystemMetrics = vi.fn();
const mockUseSystemAlerts = vi.fn();
const mockUseResolveAlert = vi.fn();
const mockUseMyPerformance = vi.fn();
const mockUseAgentDetails = vi.fn();
const mockUseAgents = vi.fn();

vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

vi.mock('../context/AppContext', () => ({
  useApp: () => mockUseApp(),
}));

vi.mock('../hooks/useDashboard', () => ({
  useDashboard: () => mockUseDashboard(),
}));

vi.mock('../hooks/useCalls', () => ({
  useCalls: (...args: unknown[]) => mockUseCalls(...args),
}));

vi.mock('../hooks/useLeads', () => ({
  useLeads: () => mockUseLeads(),
}));

vi.mock('../hooks/useSystemHealth', () => ({
  useSystemMetrics: () => mockUseSystemMetrics(),
  useSystemAlerts: () => mockUseSystemAlerts(),
  useResolveAlert: () => mockUseResolveAlert(),
}));

vi.mock('../hooks/useMyPerformance', () => ({
  useMyPerformance: (...args: unknown[]) => mockUseMyPerformance(...args),
}));

vi.mock('../hooks/useAgentDetails', () => ({
  useAgentDetails: (...args: unknown[]) => mockUseAgentDetails(...args),
}));

vi.mock('../hooks/useAgents', () => ({
  useAgents: () => mockUseAgents(),
}));

describe('Workflow launcher coverage', () => {
  beforeEach(() => {
    mockUseDashboard.mockReturnValue({
      data: {
        total_calls_today: 12,
        avg_qa_score: 83,
        queue_depth: 4,
        pass_rate: 69,
        weekly_trend: [],
        campaign_performance: [],
      },
      isLoading: false,
      dataUpdatedAt: Date.parse('2026-06-10T00:00:00Z'),
    });
    mockUseCalls.mockReturnValue({ data: [], isLoading: false });
    mockUseLeads.mockReturnValue({ data: [], isLoading: false });
    mockUseSystemMetrics.mockReturnValue({ data: null });
    mockUseSystemAlerts.mockReturnValue({ data: [], isLoading: false, isFetching: false, refetch: vi.fn() });
    mockUseResolveAlert.mockReturnValue({ mutate: vi.fn() });
    mockUseMyPerformance.mockReturnValue({
      data: {
        avg_score: 81,
        total_calls: 30,
        rank: 2,
        skills_matrix: { empathy: 85, compliance: 79 },
        cumulative_stats: {},
      },
      isLoading: false,
    });
    mockUseAgentDetails.mockReturnValue({
      data: {
        id: 7,
        name: 'Sara Leader',
        email: 'sara@example.com',
        avatar: 'SL',
        tier: 'gold',
        department: 'Sales',
        employee_code: 'A-7',
        skills: { empathy: 85, compliance: 79 },
      },
      isLoading: false,
    });
    mockUseAgents.mockReturnValue({ data: [] });
  });

  it('shows KPI follow-up launcher on dashboard for team leaders', () => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.TEAM_LEADER,
      currentUser: { id: 9, role: UserRole.TEAM_LEADER },
    });

    const html = renderToStaticMarkup(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    expect(html).toContain('Create KPI Follow-up');
    expect(html).toContain('Avg QA Score');
  });

  it('renders campaign performance rows on the dashboard', () => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.ADMIN,
      currentUser: { id: 1, role: UserRole.ADMIN },
    });
    mockUseDashboard.mockReturnValue({
      data: {
        total_calls_today: 12,
        avg_qa_score: 83,
        queue_depth: 4,
        pass_rate: 69,
        weekly_trend: [{ day: 'Mon', calls: 12, score: 83 }],
        campaign_performance: [{ name: 'Retention', score: 88, calls: 14 }],
      },
      isLoading: false,
      dataUpdatedAt: Date.parse('2026-06-10T00:00:00Z'),
    });
    mockUseCalls.mockReturnValue({
      data: [{ id: 17, call_summary: 'Saved a churned customer', processed_at: '2026-06-10T10:00:00Z', audio_duration: 125 }],
      isLoading: false,
    });

    const html = renderToStaticMarkup(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    expect(html).toContain('Campaign Performance');
    expect(html).toContain('Retention');
    expect(html).toContain('88/100');
    expect(html).toContain('14 calls');
  });

  it('renders system health loading placeholders and alert summary', () => {
    mockUseSystemMetrics.mockReturnValue({
      data: null,
      isLoading: true,
      isFetching: false,
      refetch: vi.fn(),
    });
    mockUseSystemAlerts.mockReturnValue({
      data: null,
      isLoading: true,
      isFetching: false,
      refetch: vi.fn(),
    });

    const html = renderToStaticMarkup(<SystemHealth />);

    expect(html).toContain('Inference Dashboard');
    expect(html).toContain('System Health Alerts');
    expect(html).toContain('Show Resolved');
  });

  it('renders system health metrics and active alerts', () => {
    mockUseSystemMetrics.mockReturnValue({
      data: {
        gpu_load: 74,
        cpu_load: 58,
        inference_time: 142,
        calls_processing: 3,
        queue_depth: 6,
        pipeline_latency: 18,
        uptime: 12,
        inference_history: [{ time: '09:00', value: 130 }],
        gpu_history: [{ time: '09:00', value: 72 }],
        services: [
          { name: 'FastAPI Backend', status: 'operational', latency: '12ms' },
          { name: 'Redis Queue', status: 'degraded', latency: '28ms' },
        ],
      },
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    });
    mockUseSystemAlerts.mockReturnValue({
      data: [
        {
          id: 5,
          error_type: 'low_score',
          severity: 'critical',
          error_message: 'Call quality dropped below SLA.',
          created_at: '2026-06-10T11:00:00Z',
          resolved: false,
        },
      ],
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    });

    const html = renderToStaticMarkup(<SystemHealth />);

    expect(html).toContain('1 Critical Active');
    expect(html).toContain('Call quality dropped below SLA.');
    expect(html).toContain('FastAPI Backend');
    expect(html).toContain('Redis Queue');
    expect(html).toContain('Processing');
  });

  it('shows coaching note action for team leaders on agent profiles', () => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.TEAM_LEADER,
      currentUser: { id: 9, role: UserRole.TEAM_LEADER },
    });

    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/agents/7']}>
        <Routes>
          <Route path="/agents/:id" element={<AgentProfile />} />
        </Routes>
      </MemoryRouter>
    );

    expect(html).toContain('Coaching Note');
    expect(html).not.toContain('Escalate');
  });

  it('shows escalation action for team managers on agent profiles', () => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.TEAM_MANAGER,
      currentUser: { id: 12, role: UserRole.TEAM_MANAGER },
    });

    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/agents/7']}>
        <Routes>
          <Route path="/agents/:id" element={<AgentProfile />} />
        </Routes>
      </MemoryRouter>
    );

    expect(html).toContain('Escalate');
    expect(html).not.toContain('Coaching Note');
  });
});
