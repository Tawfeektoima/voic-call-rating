import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { AxiosError } from 'axios';
import { FileText, Filter } from 'lucide-react';
import { getTeamLeaderAgents, getTeamLeaderTeams } from '../lib/api';
import { TeamLeaderAgentRowOut } from '../lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { EmptyState, ErrorState, PageLoader } from '../components/ui/states';
import { buildNotesComposeUrl } from '../lib/noteNavigation';

function formatCurrency(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatPercent(value: number | null | undefined) {
  return `${(value || 0).toFixed(1)}%`;
}

function PermissionRestricted() {
  return (
    <EmptyState
      title="Access restricted"
      description="This team filter is outside your allowed scope, so the agent workspace cannot be shown."
    />
  );
}

export function TeamLeaderAgents() {
  const navigate = useNavigate();
  const [selectedTeamId, setSelectedTeamId] = useState<string>('all');

  const teamsQuery = useQuery({
    queryKey: ['team-leader-teams'],
    queryFn: getTeamLeaderTeams,
  });

  const agentsQuery = useQuery({
    queryKey: ['team-leader-agents', selectedTeamId],
    queryFn: () => getTeamLeaderAgents(selectedTeamId === 'all' ? undefined : { team_id: Number(selectedTeamId) }),
  });

  const error = agentsQuery.error as AxiosError | null;
  const isForbidden = error?.response?.status === 403;
  const teams = teamsQuery.data || [];
  const agents = agentsQuery.data || [];

  if (teamsQuery.isLoading || agentsQuery.isLoading) {
    return <PageLoader message="Loading scoped agents..." />;
  }

  if (isForbidden) {
    return <PermissionRestricted />;
  }

  if (teamsQuery.isError || agentsQuery.isError) {
    return <ErrorState message="Unable to load the scoped agents view." onRetry={() => {
      teamsQuery.refetch();
      agentsQuery.refetch();
    }} />;
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground font-semibold">Team Leader Workspace</p>
          <h1 className="text-2xl font-semibold text-foreground">Agents</h1>
          <p className="text-sm text-muted-foreground">Read-only agent metrics for the teams currently led by this session.</p>
        </div>

        <div className="w-full lg:w-72 space-y-2">
          <p className="text-xs text-muted-foreground flex items-center gap-2"><Filter size={12} /> Team filter</p>
          <Select value={selectedTeamId} onValueChange={setSelectedTeamId}>
            <SelectTrigger>
              <SelectValue placeholder="Filter by team" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All teams</SelectItem>
              {teams.map((team) => (
                <SelectItem key={team.team_id} value={String(team.team_id)}>{team.team_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Assigned agents</CardTitle>
        </CardHeader>
        <CardContent>
          {agents.length === 0 ? (
            <EmptyState title="No agents found" description="No active agents matched this team filter." />
          ) : (
            <div className="space-y-3">
              {agents.map((agent: TeamLeaderAgentRowOut) => (
                <div key={agent.agent_id} className="rounded-lg border border-border bg-card px-4 py-4">
                  <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-semibold text-foreground">{agent.agent_name}</p>
                        <span className="text-xs text-muted-foreground">{agent.email}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {agent.team_name} {agent.campaign_name ? `· ${agent.campaign_name}` : ''} · {agent.status}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 xl:min-w-[560px]">
                      <Metric label="Sales" value={agent.sales.toString()} />
                      <Metric label="Revenue" value={formatCurrency(agent.revenue)} />
                      <Metric label="Conversion" value={formatPercent(agent.conversion_rate)} />
                      <Metric label="QA" value={agent.qa_score?.toFixed(1) || '--'} />
                      <Metric label="Attendance" value={formatPercent(agent.attendance_rate)} />
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(buildNotesComposeUrl({
                        noteType: 'COACHING_NOTE',
                        employeeId: agent.agent_id,
                        teamId: agent.team_id,
                        campaignId: agent.campaign_id || undefined,
                        title: `Coaching note for ${agent.agent_name}`,
                      }))}
                    >
                      <FileText size={14} />
                      Coaching Note
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(buildNotesComposeUrl({
                        noteType: 'KPI_FOLLOW_UP',
                        teamId: agent.team_id,
                        employeeId: agent.agent_id,
                        campaignId: agent.campaign_id || undefined,
                        kpiKey: 'average_qa_score',
                        kpiLabel: 'Average QA Score',
                        currentValue: agent.qa_score || 0,
                        title: `Average QA Score KPI follow-up for ${agent.agent_name}`,
                      }))}
                    >
                      KPI Follow-up
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-sm font-medium text-foreground mt-1">{value}</p>
    </div>
  );
}
