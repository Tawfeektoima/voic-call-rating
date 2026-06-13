import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BarChart3, FileText, GitPullRequestArrow, Inbox, Users } from 'lucide-react';
import { toast } from 'sonner';
import {
  cancelTeamManagerTransferRequest,
  createTeamManagerTransferRequest,
  getTeamManagerAgents,
  getTeamManagerDashboard,
  getTeamManagerKpis,
  getTeamManagerTransferRequests,
  getApiErrorMessage,
} from '../lib/api';
import { AgentTransferRequestOut, TeamManagerAgentRowOut, TeamManagerTeamRowOut } from '../lib/types';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { EmptyState, ErrorState, PageLoader } from '../components/ui/states';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Input } from '../components/ui/input';

function currentMonthValue() {
  return new Date().toISOString().slice(0, 7);
}

function formatCurrency(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatPercent(value: number | null | undefined) {
  return `${(value || 0).toFixed(1)}%`;
}

function formatDate(value?: string | null) {
  if (!value) return '--';
  return new Date(value).toLocaleDateString();
}

function statusVariant(status: string): 'default' | 'secondary' | 'outline' | 'destructive' {
  const normalized = status.toUpperCase();
  if (normalized === 'PENDING') return 'default';
  if (normalized === 'CANCELED') return 'outline';
  if (normalized === 'REJECTED') return 'destructive';
  return 'secondary';
}

function MetricCard({ label, value, sublabel }: { label: string; value: string; sublabel?: string }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold text-foreground">{value}</p>
        {sublabel && <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>}
      </CardContent>
    </Card>
  );
}

function InlineMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-sm font-medium text-foreground mt-1">{value}</p>
    </div>
  );
}

export function TeamManagerWorkspace() {
  const queryClient = useQueryClient();
  const [selectedTeamId, setSelectedTeamId] = useState('all');
  const [month, setMonth] = useState(currentMonthValue());
  const [transferForm, setTransferForm] = useState({
    agentId: '',
    fromTeamId: '',
    toTeamId: '',
    reason: '',
  });

  const dashboardQuery = useQuery({
    queryKey: ['team-manager-dashboard'],
    queryFn: getTeamManagerDashboard,
  });
  const agentsQuery = useQuery({
    queryKey: ['team-manager-agents', selectedTeamId],
    queryFn: () => getTeamManagerAgents(selectedTeamId === 'all' ? undefined : { team_id: Number(selectedTeamId) }),
  });
  const kpisQuery = useQuery({
    queryKey: ['team-manager-kpis', month],
    queryFn: () => getTeamManagerKpis({ month }),
  });
  const transferRequestsQuery = useQuery({
    queryKey: ['team-manager-transfer-requests'],
    queryFn: getTeamManagerTransferRequests,
  });

  const teams = dashboardQuery.data?.teams || [];
  const agents = agentsQuery.data || [];
  const selectedAgent = agents.find((agent) => String(agent.agent_id) === transferForm.agentId);
  const targetTeams = teams.filter((team) => String(team.team_id) !== transferForm.fromTeamId);

  useEffect(() => {
    if (selectedAgent && !transferForm.fromTeamId) {
      setTransferForm((current) => ({ ...current, fromTeamId: String(selectedAgent.team_id) }));
    }
  }, [selectedAgent, transferForm.fromTeamId]);

  const reports = useMemo(() => ({
    totalSales: kpisQuery.data?.total_sales ?? dashboardQuery.data?.total_sales ?? 0,
    totalRevenue: kpisQuery.data?.total_revenue ?? dashboardQuery.data?.total_revenue ?? 0,
    conversionRate: kpisQuery.data?.average_conversion_rate ?? dashboardQuery.data?.average_conversion_rate ?? 0,
    attendanceRate: kpisQuery.data?.attendance_rate ?? dashboardQuery.data?.attendance_rate ?? 0,
  }), [dashboardQuery.data, kpisQuery.data]);

  const createTransferMutation = useMutation({
    mutationFn: createTeamManagerTransferRequest,
    onSuccess: () => {
      toast.success('Transfer request created');
      setTransferForm({ agentId: '', fromTeamId: '', toTeamId: '', reason: '' });
      queryClient.invalidateQueries({ queryKey: ['team-manager-transfer-requests'] });
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to create transfer request.'));
    },
  });

  const cancelTransferMutation = useMutation({
    mutationFn: cancelTeamManagerTransferRequest,
    onSuccess: () => {
      toast.success('Transfer request canceled');
      queryClient.invalidateQueries({ queryKey: ['team-manager-transfer-requests'] });
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to cancel transfer request.'));
    },
  });

  const handleTransferSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!transferForm.agentId || !transferForm.fromTeamId || !transferForm.toTeamId || !transferForm.reason.trim()) {
      toast.error('Select an agent, source team, target team, and reason.');
      return;
    }

    createTransferMutation.mutate({
      agent_id: Number(transferForm.agentId),
      from_team_id: Number(transferForm.fromTeamId),
      to_team_id: Number(transferForm.toTeamId),
      reason: transferForm.reason.trim(),
    });
  };

  if (dashboardQuery.isLoading || agentsQuery.isLoading || kpisQuery.isLoading || transferRequestsQuery.isLoading) {
    return <PageLoader message="Loading team manager workspace..." />;
  }

  if (dashboardQuery.isError || agentsQuery.isError || kpisQuery.isError || transferRequestsQuery.isError || !dashboardQuery.data || !kpisQuery.data) {
    return <ErrorState message="Unable to load the Team Manager workspace." onRetry={() => {
      dashboardQuery.refetch();
      agentsQuery.refetch();
      kpisQuery.refetch();
      transferRequestsQuery.refetch();
    }} />;
  }

  const dashboard = dashboardQuery.data;
  const kpis = kpisQuery.data;
  const transferRequests = transferRequestsQuery.data || [];

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div className="flex flex-col xl:flex-row xl:items-end xl:justify-between gap-4">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground font-semibold">Team Manager Workspace</p>
          <h1 className="text-2xl font-semibold text-foreground">Managed Teams</h1>
          <p className="text-sm text-muted-foreground max-w-3xl">
            Scoped view of team performance, agents, KPI reports, workflow alerts, and transfer requests for the teams managed by this role.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="space-y-2 sm:w-64">
            <p className="text-xs text-muted-foreground">Agent team filter</p>
            <Select value={selectedTeamId} onValueChange={setSelectedTeamId}>
              <SelectTrigger>
                <SelectValue placeholder="Filter agents" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All managed teams</SelectItem>
                {teams.map((team) => (
                  <SelectItem key={team.team_id} value={String(team.team_id)}>{team.team_name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2 sm:w-44">
            <p className="text-xs text-muted-foreground">KPI month</p>
            <Input type="month" value={month} onChange={(event) => setMonth(event.target.value)} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard label="Managed Teams" value={dashboard.total_teams.toString()} sublabel="Active teams in scope" />
        <MetricCard label="Scoped Agents" value={dashboard.total_agents.toString()} sublabel="Agents assigned to managed teams" />
        <MetricCard label="Average QA Score" value={dashboard.average_qa_score.toFixed(1)} sublabel="Across evaluated calls" />
        <MetricCard label="Conversion Rate" value={formatPercent(dashboard.average_conversion_rate)} sublabel="Successful outcomes per evaluated call" />
        <MetricCard label="Sales" value={dashboard.total_sales.toString()} sublabel="Team-scoped successful outcomes" />
        <MetricCard label="Revenue" value={formatCurrency(dashboard.total_revenue)} sublabel="Outcome value in scope" />
        <MetricCard label="Attendance" value={formatPercent(dashboard.attendance_rate)} sublabel="Attendance records in scope" />
        <MetricCard label="Open Transfers" value={transferRequests.filter((request) => request.status === 'PENDING').length.toString()} sublabel="Pending manager requests" />
      </div>

      {dashboard.alerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2"><Inbox size={16} /> Alerts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboard.alerts.map((alert, index) => (
              <div key={`${alert.type}-${index}`} className="rounded-lg border border-border bg-card px-4 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-foreground">{alert.message}</p>
                  <p className="text-xs text-muted-foreground mt-1">{alert.type}</p>
                </div>
                <Badge variant={alert.severity === 'critical' ? 'destructive' : 'outline'}>{alert.severity}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2"><Users size={16} /> Teams in Scope</CardTitle>
        </CardHeader>
        <CardContent>
          {teams.length === 0 ? (
            <EmptyState title="No teams managed" description="This workspace will populate once active team assignments are available." />
          ) : (
            <div className="space-y-3">
              {teams.map((team: TeamManagerTeamRowOut) => (
                <div key={team.team_id} className="rounded-lg border border-border bg-card px-4 py-4">
                  <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-foreground">{team.team_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {team.campaign_name || 'No campaign'} - Leader {team.leader_name || '--'} - {team.agent_count} agents
                      </p>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 xl:min-w-[620px]">
                      <InlineMetric label="Sales" value={team.sales.toString()} />
                      <InlineMetric label="Revenue" value={formatCurrency(team.revenue)} />
                      <InlineMetric label="Conversion" value={formatPercent(team.conversion_rate)} />
                      <InlineMetric label="QA" value={team.average_qa_score.toFixed(1)} />
                      <InlineMetric label="Attendance" value={formatPercent(team.attendance_rate)} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.4fr)_minmax(360px,0.8fr)] gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2"><Users size={16} /> Agents</CardTitle>
          </CardHeader>
          <CardContent>
            {agents.length === 0 ? (
              <EmptyState title="No agents found" description="No active agents matched this managed-team filter." />
            ) : (
              <div className="space-y-3">
                {agents.map((agent: TeamManagerAgentRowOut) => (
                  <div key={agent.agent_id} className="rounded-lg border border-border bg-card px-4 py-4">
                    <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-foreground">{agent.agent_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {agent.email} - {agent.team_name} {agent.campaign_name ? `- ${agent.campaign_name}` : ''} - {agent.status}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 xl:min-w-[560px]">
                        <InlineMetric label="Sales" value={agent.sales.toString()} />
                        <InlineMetric label="Revenue" value={formatCurrency(agent.revenue)} />
                        <InlineMetric label="Conversion" value={formatPercent(agent.conversion_rate)} />
                        <InlineMetric label="QA" value={agent.qa_score?.toFixed(1) || '--'} />
                        <InlineMetric label="Attendance" value={formatPercent(agent.attendance_rate)} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2"><BarChart3 size={16} /> Reports</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <ReportTile label="Sales" value={reports.totalSales.toString()} />
              <ReportTile label="Revenue" value={formatCurrency(reports.totalRevenue)} />
              <ReportTile label="Conversion" value={formatPercent(reports.conversionRate)} />
              <ReportTile label="Attendance" value={formatPercent(reports.attendanceRate)} />
              <ReportTile label="QA Score" value={kpis.average_qa_score.toFixed(1)} />
              <ReportTile label="KPI Month" value={kpis.month} />
            </div>
            <p className="text-xs text-muted-foreground">Report cards use monthly KPI data scoped by the backend to the current manager.</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(360px,0.8fr)_minmax(0,1.2fr)] gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2"><GitPullRequestArrow size={16} /> New Transfer Request</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleTransferSubmit}>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Agent</p>
                <Select
                  value={transferForm.agentId}
                  onValueChange={(value) => {
                    const agent = agents.find((item) => String(item.agent_id) === value);
                    setTransferForm((current) => ({
                      ...current,
                      agentId: value,
                      fromTeamId: agent ? String(agent.team_id) : '',
                      toTeamId: '',
                    }));
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select agent" />
                  </SelectTrigger>
                  <SelectContent>
                    {agents.map((agent) => (
                      <SelectItem key={agent.agent_id} value={String(agent.agent_id)}>{agent.agent_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">From team</p>
                  <Select
                    value={transferForm.fromTeamId}
                    onValueChange={(value) => setTransferForm((current) => ({ ...current, fromTeamId: value, toTeamId: current.toTeamId === value ? '' : current.toTeamId }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Source team" />
                    </SelectTrigger>
                    <SelectContent>
                      {teams.map((team) => (
                        <SelectItem key={team.team_id} value={String(team.team_id)}>{team.team_name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">To team</p>
                  <Select value={transferForm.toTeamId} onValueChange={(value) => setTransferForm((current) => ({ ...current, toTeamId: value }))}>
                    <SelectTrigger>
                      <SelectValue placeholder="Target team" />
                    </SelectTrigger>
                    <SelectContent>
                      {targetTeams.map((team) => (
                        <SelectItem key={team.team_id} value={String(team.team_id)}>{team.team_name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Reason</p>
                <Textarea
                  value={transferForm.reason}
                  onChange={(event) => setTransferForm((current) => ({ ...current, reason: event.target.value }))}
                  placeholder="Business reason for the transfer request"
                  className="min-h-24"
                />
              </div>

              <Button type="submit" disabled={createTransferMutation.isPending || teams.length < 2 || agents.length === 0}>
                <FileText size={14} />
                Submit Request
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Transfer Requests</CardTitle>
          </CardHeader>
          <CardContent>
            {transferRequests.length === 0 ? (
              <EmptyState title="No transfer requests" description="Requests created from this workspace will appear here." />
            ) : (
              <div className="space-y-3">
                {transferRequests.map((request: AgentTransferRequestOut) => (
                  <div key={request.id} className="rounded-lg border border-border bg-card px-4 py-4">
                    <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm font-semibold text-foreground">Request #{request.id}</p>
                          <Badge variant={statusVariant(request.status)}>{request.status}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {request.agent_name || `Agent #${request.agent_id}`} - {request.from_team_name || `Team #${request.from_team_id}`} to {request.to_team_name || `Team #${request.to_team_id || '--'}`} - {formatDate(request.created_at)}
                        </p>
                        <p className="text-sm text-foreground mt-2">{request.reason}</p>
                        {request.review_note && <p className="text-xs text-muted-foreground mt-1">Review: {request.review_note}</p>}
                      </div>
                      {request.status === 'PENDING' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => cancelTransferMutation.mutate(request.id)}
                          disabled={cancelTransferMutation.isPending}
                        >
                          Cancel
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ReportTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-secondary/30 px-3 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold text-foreground mt-1">{value}</p>
    </div>
  );
}
