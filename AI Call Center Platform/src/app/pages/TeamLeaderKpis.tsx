import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { FileText } from 'lucide-react';
import { getTeamLeaderKpis, getTeamLeaderTeams } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { ErrorState, PageLoader } from '../components/ui/states';
import { buildNotesComposeUrl } from '../lib/noteNavigation';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

function currentMonthValue() {
  return new Date().toISOString().slice(0, 7);
}

function formatCurrency(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatPercent(value: number) {
  return `${value.toFixed(1)}%`;
}

export function TeamLeaderKpis() {
  const navigate = useNavigate();
  const [month, setMonth] = useState(currentMonthValue());
  const [selectedTeamId, setSelectedTeamId] = useState<string>('');

  const teamsQuery = useQuery({
    queryKey: ['team-leader-teams'],
    queryFn: getTeamLeaderTeams,
  });

  const query = useQuery({
    queryKey: ['team-leader-kpis', month],
    queryFn: () => getTeamLeaderKpis({ month }),
  });

  const teams = teamsQuery.data || [];
  const resolvedTeamId = selectedTeamId ? Number(selectedTeamId) : teams[0]?.team_id;

  useEffect(() => {
    if (!selectedTeamId && teams.length > 0) {
      setSelectedTeamId(String(teams[0].team_id));
    }
  }, [selectedTeamId, teams]);

  const periodWindow = useMemo(() => {
    const [yearString, monthString] = month.split('-');
    const year = Number(yearString);
    const monthIndex = Number(monthString);
    const periodStart = `${month}-01`;
    const periodEndDate = new Date(year, monthIndex, 0);
    const periodEnd = `${month}-${String(periodEndDate.getDate()).padStart(2, '0')}`;
    return { periodStart, periodEnd };
  }, [month]);

  if (query.isLoading || teamsQuery.isLoading) {
    return <PageLoader message="Loading monthly KPI summary..." />;
  }

  if (query.isError || teamsQuery.isError || !query.data) {
    return <ErrorState message="Unable to load the team-scoped KPI summary." onRetry={() => {
      query.refetch();
      teamsQuery.refetch();
    }} />;
  }

  const data = query.data;

  const openKpiNote = (kpiKey: string, kpiLabel: string, currentValue: number) => {
    navigate(buildNotesComposeUrl({
      noteType: 'KPI_FOLLOW_UP',
      teamId: resolvedTeamId,
      kpiKey,
      kpiLabel,
      currentValue,
      periodStart: periodWindow.periodStart,
      periodEnd: periodWindow.periodEnd,
      title: `${kpiLabel} KPI follow-up`,
    }));
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground font-semibold">Team Leader Workspace</p>
          <h1 className="text-2xl font-semibold text-foreground">Monthly KPIs</h1>
          <p className="text-sm text-muted-foreground">Month-by-month operational summary for the teams in this Team Leader scope.</p>
        </div>

        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">Reporting month</p>
          <input
            type="month"
            value={month}
            onChange={(event) => setMonth(event.target.value)}
            className="h-10 rounded-md border border-border bg-background px-3 text-sm text-foreground"
          />
        </div>
        <div className="space-y-2 lg:min-w-[240px]">
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
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <KpiBlock title="Total Sales" value={data.total_sales.toString()} sublabel={`Month ${data.month}`} onNote={() => openKpiNote('total_sales', 'Total Sales', data.total_sales)} />
        <KpiBlock title="Total Revenue" value={formatCurrency(data.total_revenue)} sublabel={`Month ${data.month}`} onNote={() => openKpiNote('total_revenue', 'Total Revenue', data.total_revenue)} />
        <KpiBlock title="Average QA Score" value={data.average_qa_score.toFixed(1)} sublabel="Team-scoped QA average" onNote={() => openKpiNote('average_qa_score', 'Average QA Score', data.average_qa_score)} />
        <KpiBlock title="Average Conversion Rate" value={formatPercent(data.average_conversion_rate)} sublabel="Successful outcomes per evaluated call" onNote={() => openKpiNote('conversion_rate', 'Conversion Rate', data.average_conversion_rate)} />
        <KpiBlock title="Attendance Rate" value={formatPercent(data.attendance_rate)} sublabel="Placeholder until attendance integration is live" onNote={() => openKpiNote('attendance_rate', 'Attendance Rate', data.attendance_rate)} />
      </div>
    </div>
  );
}

function KpiBlock({
  title,
  value,
  sublabel,
  onNote,
}: {
  title: string;
  value: string;
  sublabel: string;
  onNote: () => void;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold text-foreground">{value}</p>
        <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={onNote}>
          <FileText size={14} />
          Create KPI Note
        </Button>
      </CardContent>
    </Card>
  );
}
