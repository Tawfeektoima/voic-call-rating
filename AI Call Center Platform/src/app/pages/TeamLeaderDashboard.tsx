import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { ArrowUpRight, FileText, Inbox, Phone, Users } from 'lucide-react';
import { getTeamLeaderDashboard, getTeamLeaderTeams } from '../lib/api';
import { TeamLeaderDashboardOut, TeamLeaderTeamRowOut } from '../lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { EmptyState, ErrorState, PageLoader } from '../components/ui/states';
import { buildNotesComposeUrl } from '../lib/noteNavigation';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

function formatPercent(value: number) {
  return `${value.toFixed(1)}%`;
}

function formatCurrency(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function MetricCard({
  label,
  value,
  sublabel,
  action,
}: {
  label: string;
  value: string;
  sublabel?: string;
  action?: () => void;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-2xl font-semibold text-foreground">{value}</p>
            {sublabel && <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>}
          </div>
          {action && (
            <Button variant="outline" size="sm" onClick={action}>
              <FileText size={14} />
              Create KPI Note
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function TeamLeaderDashboard() {
  const navigate = useNavigate();
  const [selectedTeamId, setSelectedTeamId] = useState<string>('');
  const dashboardQuery = useQuery({
    queryKey: ['team-leader-dashboard'],
    queryFn: getTeamLeaderDashboard,
  });
  const teamsQuery = useQuery({
    queryKey: ['team-leader-teams'],
    queryFn: getTeamLeaderTeams,
  });

  const dashboard = dashboardQuery.data;
  const teams = teamsQuery.data || [];
  const resolvedTeamId = selectedTeamId ? Number(selectedTeamId) : teams[0]?.team_id;

  useEffect(() => {
    if (!selectedTeamId && teams.length > 0) {
      setSelectedTeamId(String(teams[0].team_id));
    }
  }, [selectedTeamId, teams]);

  const openKpiNote = (params: { teamId?: number; kpiKey: string; kpiLabel: string; currentValue?: number }) => {
    navigate(buildNotesComposeUrl({
      noteType: 'KPI_FOLLOW_UP',
      teamId: params.teamId,
      kpiKey: params.kpiKey,
      kpiLabel: params.kpiLabel,
      currentValue: params.currentValue,
      title: `${params.kpiLabel} KPI follow-up`,
    }));
  };

  if (dashboardQuery.isLoading || teamsQuery.isLoading) {
    return <PageLoader message="Loading team leader workspace..." />;
  }

  if (dashboardQuery.isError || teamsQuery.isError) {
    return <ErrorState message="Unable to load the Team Leader dashboard right now." onRetry={() => {
      dashboardQuery.refetch();
      teamsQuery.refetch();
    }} />;
  }

  if (!dashboard) {
    return <EmptyState title="No team leader data" description="This workspace will populate once team scope is available." />;
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div className="flex flex-col xl:flex-row xl:items-end xl:justify-between gap-4">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground font-semibold">Team Leader Workspace</p>
          <h1 className="text-2xl font-semibold text-foreground">Operational Overview</h1>
          <p className="text-sm text-muted-foreground max-w-2xl">Read-only team operations with scoped KPIs, call review visibility, and workflow note entry points.</p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 xl:min-w-[420px]">
          <div className="space-y-2 flex-1">
            <p className="text-xs text-muted-foreground">Team context for KPI notes</p>
            <Select value={selectedTeamId} onValueChange={setSelectedTeamId}>
              <SelectTrigger>
                <SelectValue placeholder="Select team context" />
              </SelectTrigger>
              <SelectContent>
                {teams.map((team) => (
                  <SelectItem key={team.team_id} value={String(team.team_id)}>{team.team_name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" className="self-end" onClick={() => navigate('/notes')}>
            <Inbox size={14} />
            Open Notes Queue
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard label="Teams" value={dashboard.team_count.toString()} sublabel="Teams currently in your scope" />
        <MetricCard label="Agents" value={dashboard.agent_count.toString()} sublabel="Active assigned agents" />
        <MetricCard label="Average QA Score" value={dashboard.average_qa_score.toFixed(1)} sublabel="Out of 100 points" action={() => openKpiNote({ teamId: resolvedTeamId, kpiKey: 'average_qa_score', kpiLabel: 'Average QA Score', currentValue: dashboard.average_qa_score })} />
        <MetricCard label="Attendance Rate" value={formatPercent(dashboard.attendance_rate)} sublabel="Placeholder until attendance integration is live" action={() => openKpiNote({ teamId: resolvedTeamId, kpiKey: 'attendance_rate', kpiLabel: 'Attendance Rate', currentValue: dashboard.attendance_rate })} />
        <MetricCard label="Sales" value={dashboard.sales.toString()} sublabel="Successful outcomes in your scope" action={() => openKpiNote({ teamId: resolvedTeamId, kpiKey: 'total_sales', kpiLabel: 'Total Sales', currentValue: dashboard.sales })} />
        <MetricCard label="Revenue" value={formatCurrency(dashboard.revenue)} sublabel="Outcome value from evaluated calls" action={() => openKpiNote({ teamId: resolvedTeamId, kpiKey: 'total_revenue', kpiLabel: 'Total Revenue', currentValue: dashboard.revenue })} />
        <MetricCard label="Conversion Rate" value={formatPercent(dashboard.conversion_rate)} sublabel="Successes vs evaluated calls" action={() => openKpiNote({ teamId: resolvedTeamId, kpiKey: 'conversion_rate', kpiLabel: 'Conversion Rate', currentValue: dashboard.conversion_rate })} />
        <MetricCard label="Pending Notes" value={dashboard.pending_notes_count.toString()} sublabel={`${dashboard.pending_transfer_requests_count} transfer requests also waiting`} action={() => navigate('/notes')} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Teams in Scope</CardTitle>
        </CardHeader>
        <CardContent>
          {teams.length === 0 ? (
            <EmptyState title="No teams assigned" description="No active team scope is available for this role right now." />
          ) : (
            <div className="space-y-3">
              {teams.map((team: TeamLeaderTeamRowOut) => (
                <div key={team.team_id} className="rounded-lg border border-border bg-card px-4 py-4">
                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-semibold text-foreground">{team.team_name}</p>
                        {team.campaign_name && <span className="text-xs text-muted-foreground">{team.campaign_name}</span>}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {team.agent_count} agents · QA {team.average_qa_score.toFixed(1)} · Conversion {formatPercent(team.conversion_rate)} · Attendance {formatPercent(team.attendance_rate)}
                      </p>
                    </div>

                    <div className="flex items-center gap-4 flex-wrap">
                      <div className="text-sm text-foreground">
                        <span className="font-medium">{team.sales}</span>
                        <span className="text-muted-foreground text-xs ml-1">sales</span>
                      </div>
                      <div className="text-sm text-foreground">
                        <span className="font-medium">{formatCurrency(team.revenue)}</span>
                        <span className="text-muted-foreground text-xs ml-1">revenue</span>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => openKpiNote({ teamId: team.team_id, kpiKey: 'conversion_rate', kpiLabel: 'Conversion Rate', currentValue: team.conversion_rate })}>
                        Create KPI Note
                        <ArrowUpRight size={14} />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Users className="text-primary" size={18} />
              <div>
                <p className="text-sm font-medium text-foreground">Agent monitoring</p>
                <p className="text-xs text-muted-foreground">Review scoped agent performance and launch coaching notes.</p>
              </div>
            </div>
            <Button variant="outline" className="mt-4" onClick={() => navigate('/team-leader/agents')}>Open Agents</Button>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Phone className="text-primary" size={18} />
              <div>
                <p className="text-sm font-medium text-foreground">Call evaluations</p>
                <p className="text-xs text-muted-foreground">Open scoped call evaluations and route QA review requests safely.</p>
              </div>
            </div>
            <Button variant="outline" className="mt-4" onClick={() => navigate('/team-leader/calls')}>Open Calls</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
