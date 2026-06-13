import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { AxiosError } from 'axios';
import { ArrowLeft, ArrowRight, FileText } from 'lucide-react';
import { getTeamLeaderCalls } from '../lib/api';
import { TeamLeaderCallRowOut } from '../lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { EmptyState, ErrorState, PageLoader } from '../components/ui/states';
import { buildNotesComposeUrl } from '../lib/noteNavigation';

function formatDuration(value?: number | null) {
  if (!value) return '--';
  const totalSeconds = Math.round(value);
  return `${Math.floor(totalSeconds / 60)}m ${totalSeconds % 60}s`;
}

function PermissionRestricted() {
  return (
    <EmptyState
      title="Access restricted"
      description="This call set is outside your allowed team scope."
    />
  );
}

export function TeamLeaderCalls() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const callsQuery = useQuery({
    queryKey: ['team-leader-calls', page],
    queryFn: () => getTeamLeaderCalls({ skip: page * pageSize, limit: pageSize }),
  });

  const error = callsQuery.error as AxiosError | null;
  const isForbidden = error?.response?.status === 403;
  const items = callsQuery.data?.items || [];
  const total = callsQuery.data?.total || 0;
  const hasPrevious = page > 0;
  const hasNext = (page + 1) * pageSize < total;

  if (callsQuery.isLoading) {
    return <PageLoader message="Loading scoped call evaluations..." />;
  }

  if (isForbidden) {
    return <PermissionRestricted />;
  }

  if (callsQuery.isError) {
    return <ErrorState message="Unable to load the team-scoped calls view." onRetry={() => callsQuery.refetch()} />;
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground font-semibold">Team Leader Workspace</p>
        <h1 className="text-2xl font-semibold text-foreground">Calls</h1>
        <p className="text-sm text-muted-foreground">Evaluated calls only, limited to the teams assigned to this Team Leader scope.</p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Scoped call evaluations</CardTitle>
          <p className="text-xs text-muted-foreground">{total} total calls</p>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <EmptyState title="No calls available" description="There are no evaluated calls in this team scope yet." />
          ) : (
            <div className="space-y-3">
              {items.map((call: TeamLeaderCallRowOut) => {
                const displayScore = call.overridden_score ?? call.evaluation_score;
                return (
                  <div key={call.id} className="rounded-lg border border-border bg-card px-4 py-4">
                    <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-foreground">Call #{call.id}</p>
                        <p className="text-xs text-muted-foreground">
                          {call.employee_name || `Agent #${call.employee_id}`} · {call.campaign_name || `Campaign #${call.campaign_id}`} · {new Date(call.created_at).toLocaleString()}
                        </p>
                      </div>

                      <div className="grid grid-cols-3 gap-4 xl:min-w-[340px]">
                        <Metric label="Status" value={call.status} />
                        <Metric label="Score" value={displayScore?.toFixed(1) || '--'} />
                        <Metric label="Duration" value={formatDuration(call.audio_duration)} />
                      </div>

                      <div className="flex items-center gap-2 flex-wrap">
                        <Button variant="outline" size="sm" onClick={() => navigate(`/calls/${call.id}`)}>Details</Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(buildNotesComposeUrl({
                            noteType: 'QA_REVIEW_REQUEST',
                            callId: call.id,
                            employeeId: call.employee_id,
                            campaignId: call.campaign_id,
                            title: `QA review request for call #${call.id}`,
                          }))}
                        >
                          <FileText size={14} />
                          Request QA Review
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(buildNotesComposeUrl({
                            noteType: 'QA_DISPUTE',
                            callId: call.id,
                            employeeId: call.employee_id,
                            campaignId: call.campaign_id,
                            title: `QA dispute for call #${call.id}`,
                          }))}
                        >
                          Dispute QA Score
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(buildNotesComposeUrl({
                            noteType: 'GENERAL',
                            callId: call.id,
                            employeeId: call.employee_id,
                            campaignId: call.campaign_id,
                            title: `Workflow note for call #${call.id}`,
                          }))}
                        >
                          Add Note
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 mt-4">
            <Button variant="outline" size="sm" disabled={!hasPrevious} onClick={() => setPage((value) => value - 1)}>
              <ArrowLeft size={14} />
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={!hasNext} onClick={() => setPage((value) => value + 1)}>
              Next
              <ArrowRight size={14} />
            </Button>
          </div>
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
