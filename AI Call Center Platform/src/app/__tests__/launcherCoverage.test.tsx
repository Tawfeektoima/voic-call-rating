/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes } from 'react-router';
import { Dashboard } from '../pages/Dashboard';
import { AgentProfile } from '../pages/AgentProfile';
import { UserRole } from '../lib/types';

const mockUseApp = vi.fn();
const mockUseDashboard = vi.fn();
const mockUseCalls = vi.fn();
const mockUseLeads = vi.fn();
const mockUseSystemMetrics = vi.fn();
const mockUseMyPerformance = vi.fn();
const mockUseAgentDetails = vi.fn();
const mockUseAgents = vi.fn();

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
