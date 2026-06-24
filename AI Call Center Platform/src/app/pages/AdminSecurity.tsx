import { useState, useEffect, useCallback } from 'react';
import { 
  Shield, Users, KeyRound, Calendar, Clock, Plus, Edit, XCircle, 
  CheckCircle, Search, Loader2, AlertTriangle, RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../components/ui/utils';
import { getApiErrorMessage } from '../lib/api';
import {
  listSecurityShifts,
  createSecurityShift,
  updateSecurityShift,
  deleteSecurityShift,
  listSecuritySessions,
  revokeSecuritySession,
  listTrustedDevices,
  approveTrustedDevice,
  revokeTrustedDevice,
  getSecuritySummary,
  listSecurityAuditEvents
} from '../lib/securityAdminApi';
import { SecurityShift, SecuritySession, TrustedDevice, SecuritySummary, SecurityAuditEvent } from '../lib/types';

interface ConfirmDialogState {
  isOpen: boolean;
  action: 'cancel_shift' | 'revoke_session' | 'approve_device' | 'revoke_device' | null;
  title: string;
  targetId: number | null;
  employeeId: string;
  reason: string;
}

interface ShiftModalState {
  isOpen: boolean;
  mode: 'create' | 'update';
  shiftId?: number;
  employeeId: string;
  workDate: string;
  startsAt: string;
  endsAt: string;
  status: string;
  graceBefore: number;
  graceAfter: number;
  reason: string;
}

export function AdminSecurity({ 
  initialTab = 'shifts',
  initialShiftModal,
  initialConfirmDialog
}: { 
  initialTab?: 'shifts' | 'sessions' | 'devices' | 'events';
  initialShiftModal?: Partial<ShiftModalState>;
  initialConfirmDialog?: Partial<ConfirmDialogState>;
} = {}) {
  const [activeTab, setActiveTab] = useState<'shifts' | 'sessions' | 'devices' | 'events'>(initialTab);

  // Loading & State
  const [loading, setLoading] = useState(false);
  const [shifts, setShifts] = useState<SecurityShift[]>([]);
  const [sessions, setSessions] = useState<SecuritySession[]>([]);
  const [devices, setDevices] = useState<TrustedDevice[]>([]);
  const [events, setEvents] = useState<SecurityAuditEvent[]>([]);
  const [eventsTotal, setEventsTotal] = useState(0);
  const [eventsOffset, setEventsOffset] = useState(0);

  // Security Observability Summary State
  const [summary, setSummary] = useState<SecuritySummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  // Filters
  const [filterEmployeeId, setFilterEmployeeId] = useState('');
  const [filterDate, setFilterDate] = useState('');
  const [filterActiveOnly, setFilterActiveOnly] = useState(false);
  const [filterTrustedOnly, setFilterTrustedOnly] = useState(false);
  const [eventFilterAction, setEventFilterAction] = useState('');
  const [eventFilterEmployeeId, setEventFilterEmployeeId] = useState('');
  const [eventFilterOutcome, setEventFilterOutcome] = useState<'all' | 'success' | 'failure'>('all');
  const [eventSearch, setEventSearch] = useState('');
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState<string | null>(null);

  // Modals / Dialogs
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    isOpen: false,
    action: null,
    title: '',
    targetId: null,
    employeeId: '',
    reason: '',
    ...initialConfirmDialog
  });

  const [shiftModal, setShiftModal] = useState<ShiftModalState>({
    isOpen: false,
    mode: 'create',
    employeeId: '',
    workDate: '',
    startsAt: '09:00:00',
    endsAt: '17:00:00',
    status: 'scheduled',
    graceBefore: 10,
    graceAfter: 10,
    reason: '',
    ...initialShiftModal
  });

  // Fetch Logic
  const fetchSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const data = await getSecuritySummary(24);
      setSummary(data);
    } catch (error) {
      const errMsg = getApiErrorMessage(error, 'Failed to fetch security summary');
      setSummaryError(errMsg);
      toast.error(errMsg);
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  const fetchShifts = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (filterEmployeeId.trim()) params.employee_id = filterEmployeeId.trim();
      if (filterDate.trim()) params.work_date = filterDate.trim();
      const data = await listSecurityShifts(params);
      setShifts(data);
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Failed to fetch shifts'));
    } finally {
      setLoading(false);
    }
  }, [filterEmployeeId, filterDate]);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (filterEmployeeId.trim()) params.employee_id = filterEmployeeId.trim();
      if (filterActiveOnly) params.active_only = true;
      const data = await listSecuritySessions(params);
      setSessions(data);
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Failed to fetch sessions'));
    } finally {
      setLoading(false);
    }
  }, [filterEmployeeId, filterActiveOnly]);

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (filterEmployeeId.trim()) params.employee_id = filterEmployeeId.trim();
      if (filterTrustedOnly) params.trusted_only = true;
      const data = await listTrustedDevices(params);
      setDevices(data);
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Failed to fetch trusted devices'));
    } finally {
      setLoading(false);
    }
  }, [filterEmployeeId, filterTrustedOnly]);

  const fetchEvents = useCallback(async (options?: { reset?: boolean }) => {
    setEventsLoading(true);
    setEventsError(null);
    try {
      const reset = options?.reset ?? true;
      const offset = reset ? 0 : eventsOffset;
      const data = await listSecurityAuditEvents({
        hours: 24,
        limit: 10,
        offset,
        action: eventFilterAction.trim() || undefined,
        employee_id: eventFilterEmployeeId.trim() || undefined,
        success: eventFilterOutcome === 'all' ? undefined : eventFilterOutcome === 'success',
        q: eventSearch.trim() || undefined,
      });
      setEvents((current) => (reset ? data.items : [...current, ...data.items]));
      setEventsTotal(data.total);
      setEventsOffset(offset + data.items.length);
    } catch (error) {
      const errMsg = getApiErrorMessage(error, 'Failed to fetch security events');
      setEventsError(errMsg);
      toast.error(errMsg);
    } finally {
      setEventsLoading(false);
    }
  }, [eventFilterAction, eventFilterEmployeeId, eventFilterOutcome, eventSearch, eventsOffset]);

  const refreshActiveTab = useCallback(() => {
    fetchSummary();
    if (activeTab === 'shifts') fetchShifts();
    else if (activeTab === 'sessions') fetchSessions();
    else if (activeTab === 'devices') fetchDevices();
    else if (activeTab === 'events') fetchEvents({ reset: true });
  }, [activeTab, fetchShifts, fetchSessions, fetchDevices, fetchEvents, fetchSummary]);

  useEffect(() => {
    if (activeTab !== 'events') {
      refreshActiveTab();
    }
  }, [activeTab, filterActiveOnly, filterTrustedOnly, refreshActiveTab]);

  useEffect(() => {
    if (activeTab === 'events') {
      fetchEvents({ reset: true });
    }
  }, [activeTab, eventFilterAction, eventFilterEmployeeId, eventFilterOutcome, eventSearch, fetchEvents]);

  // Actions
  const handleOpenCancelShift = (shift: SecurityShift) => {
    setConfirmDialog({
      isOpen: true,
      action: 'cancel_shift',
      title: 'Cancel Shift',
      targetId: shift.id,
      employeeId: shift.employee_id,
      reason: ''
    });
  };

  const handleOpenRevokeSession = (session: SecuritySession) => {
    setConfirmDialog({
      isOpen: true,
      action: 'revoke_session',
      title: 'Revoke Active Session',
      targetId: session.id,
      employeeId: session.employee_id,
      reason: ''
    });
  };

  const handleOpenApproveDevice = (device: TrustedDevice) => {
    setConfirmDialog({
      isOpen: true,
      action: 'approve_device',
      title: 'Approve Trusted Device',
      targetId: device.id,
      employeeId: device.employee_id,
      reason: ''
    });
  };

  const handleOpenRevokeDevice = (device: TrustedDevice) => {
    setConfirmDialog({
      isOpen: true,
      action: 'revoke_device',
      title: 'Revoke Trusted Device',
      targetId: device.id,
      employeeId: device.employee_id,
      reason: ''
    });
  };

  const handleConfirmAction = async () => {
    if (!confirmDialog.reason.trim()) {
      toast.error('A reason is required to perform this action');
      return;
    }

    const targetId = confirmDialog.targetId;
    if (targetId === null) return;

    try {
      if (confirmDialog.action === 'cancel_shift') {
        await deleteSecurityShift(targetId, confirmDialog.reason.trim());
        toast.success('Shift cancelled successfully');
      } else if (confirmDialog.action === 'revoke_session') {
        const res = await revokeSecuritySession(targetId, { reason: confirmDialog.reason.trim() });
        toast.success(res.message || 'Session revoked successfully');
      } else if (confirmDialog.action === 'approve_device') {
        await approveTrustedDevice(targetId, { reason: confirmDialog.reason.trim() });
        toast.success('Device approved successfully');
      } else if (confirmDialog.action === 'revoke_device') {
        await revokeTrustedDevice(targetId, { reason: confirmDialog.reason.trim() });
        toast.success('Device revoked successfully');
      }

      setConfirmDialog({ isOpen: false, action: null, title: '', targetId: null, employeeId: '', reason: '' });
      refreshActiveTab();
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Action failed'));
    }
  };

  const handleOpenCreateShift = () => {
    setShiftModal({
      isOpen: true,
      mode: 'create',
      employeeId: '',
      workDate: new Date().toISOString().split('T')[0],
      startsAt: '09:00:00',
      endsAt: '17:00:00',
      status: 'scheduled',
      graceBefore: 10,
      graceAfter: 10,
      reason: ''
    });
  };

  const handleOpenUpdateShift = (shift: SecurityShift) => {
    setShiftModal({
      isOpen: true,
      mode: 'update',
      shiftId: shift.id,
      employeeId: shift.employee_id,
      workDate: shift.work_date,
      startsAt: shift.starts_at,
      endsAt: shift.ends_at,
      status: shift.status,
      graceBefore: 10,
      graceAfter: 10,
      reason: ''
    });
  };

  const handleSaveShift = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shiftModal.employeeId.trim() || !shiftModal.workDate || !shiftModal.startsAt || !shiftModal.endsAt) {
      toast.error('All required fields must be filled');
      return;
    }
    if (shiftModal.mode === 'update' && !shiftModal.reason.trim()) {
      toast.error('Reason for update is required');
      return;
    }

    try {
      if (shiftModal.mode === 'create') {
        await createSecurityShift({
          employee_id: shiftModal.employeeId.trim(),
          work_date: shiftModal.workDate,
          starts_at: shiftModal.startsAt,
          ends_at: shiftModal.endsAt,
          status: shiftModal.status
        });
        toast.success('Shift created successfully');
      } else if (shiftModal.mode === 'update' && shiftModal.shiftId !== undefined) {
        await updateSecurityShift(shiftModal.shiftId, {
          work_date: shiftModal.workDate,
          starts_at: shiftModal.startsAt,
          ends_at: shiftModal.endsAt,
          status: shiftModal.status,
          reason: shiftModal.reason.trim()
        });
        toast.success('Shift updated successfully');
      }

      setShiftModal({ ...shiftModal, isOpen: false, reason: '' });
      fetchShifts();
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Failed to save shift'));
    }
  };



  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-100 flex items-center gap-3">
            <Shield className="text-primary size-8" />
            Security Administration
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage employee shift rosters, active user sessions, and trusted device tokens.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={refreshActiveTab}
            className="p-2.5 rounded-xl border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition-all"
            title="Refresh list"
          >
            <RefreshCw size={18} />
          </button>
          {activeTab === 'shifts' && (
            <button
              onClick={handleOpenCreateShift}
              className="bg-primary hover:bg-indigo-400 text-white font-medium px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-500/10 flex items-center gap-2"
            >
              <Plus size={18} />
              Schedule Shift
            </button>
          )}
        </div>
      </div>

      {/* Security Overview */}
      <div className="bg-card border border-border rounded-3xl p-6 space-y-4 shadow-xl">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2.5">
            <Shield className="text-primary size-5" />
            <h2 className="text-xl font-bold text-slate-100">Security Overview</h2>
            <span className="text-xs bg-secondary px-2.5 py-1 rounded-lg text-muted-foreground font-medium">Last 24 Hours</span>
          </div>
          <button
            onClick={fetchSummary}
            disabled={summaryLoading}
            className="p-2 rounded-xl border border-border bg-card/50 hover:bg-secondary text-muted-foreground hover:text-foreground transition-all flex items-center gap-1.5 disabled:opacity-50"
            title="Refresh summary"
            data-testid="refresh-summary-btn"
          >
            <RefreshCw size={16} className={cn(summaryLoading && "animate-spin")} />
          </button>
        </div>

        {summaryLoading ? (
          <div data-testid="summary-loading" className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-background/40 border border-border/50 rounded-2xl p-4 h-24 flex flex-col justify-between animate-pulse">
                <div className="h-3 bg-muted rounded w-3/4"></div>
                <div className="h-6 bg-muted rounded w-1/3 mt-2"></div>
              </div>
            ))}
          </div>
        ) : summaryError ? (
          <div data-testid="summary-error" className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} />
              <span className="text-sm font-medium">{summaryError}</span>
            </div>
            <button
              onClick={fetchSummary}
              className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500 text-red-400 hover:text-white rounded-lg text-xs font-semibold border border-red-500/30 transition-all flex items-center gap-1.5"
            >
              <RefreshCw size={12} />
              Retry
            </button>
          </div>
        ) : summary && (
          (summary.audit_policy_violations +
           summary.enforced_policy_denials +
           summary.denied_logins +
           summary.denied_protected_requests +
           summary.revoked_sessions +
           summary.revoked_devices +
           summary.cancelled_shifts +
           summary.websocket_security_closes === 0) ? (
            <div data-testid="summary-empty" className="bg-background/20 border border-border/40 rounded-2xl p-6 text-center text-muted-foreground flex flex-col items-center justify-center gap-2">
              <CheckCircle className="text-emerald-500/60 size-8" />
              <p className="text-sm font-medium text-slate-300">No security events occurred today.</p>
              <p className="text-xs text-muted-foreground">The center remains fully protected and secure.</p>
            </div>
          ) : (
            <div data-testid="summary-counts" className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
              <div className="bg-background/40 border border-border/50 rounded-2xl p-4 flex flex-col justify-between hover:border-primary/30 transition-colors">
                <span className="text-xs font-semibold text-muted-foreground">Audit-only violations</span>
                <span data-testid="count-audit_policy_violations" className="text-2xl font-bold text-slate-100 mt-2">{summary.audit_policy_violations}</span>
              </div>
              <div className="bg-background/40 border border-border/50 rounded-2xl p-4 flex flex-col justify-between hover:border-primary/30 transition-colors">
                <span className="text-xs font-semibold text-muted-foreground">Enforced denials</span>
                <span data-testid="count-enforced_policy_denials" className="text-2xl font-bold text-slate-100 mt-2">{summary.enforced_policy_denials}</span>
              </div>
              <div className="bg-background/40 border border-border/50 rounded-2xl p-4 flex flex-col justify-between hover:border-primary/30 transition-colors">
                <span className="text-xs font-semibold text-muted-foreground">Login denials</span>
                <span data-testid="count-denied_logins" className="text-2xl font-bold text-slate-100 mt-2">{summary.denied_logins}</span>
              </div>
              <div className="bg-background/40 border border-border/50 rounded-2xl p-4 flex flex-col justify-between hover:border-primary/30 transition-colors">
                <span className="text-xs font-semibold text-muted-foreground">Request denials</span>
                <span data-testid="count-denied_protected_requests" className="text-2xl font-bold text-slate-100 mt-2">{summary.denied_protected_requests}</span>
              </div>
              <div className="bg-background/40 border border-border/50 rounded-2xl p-4 flex flex-col justify-between hover:border-primary/30 transition-colors">
                <span className="text-xs font-semibold text-muted-foreground">Revoked sessions</span>
                <span data-testid="count-revoked_sessions" className="text-2xl font-bold text-slate-100 mt-2">{summary.revoked_sessions}</span>
              </div>
              <div className="bg-background/40 border border-border/50 rounded-2xl p-4 flex flex-col justify-between hover:border-primary/30 transition-colors">
                <span className="text-xs font-semibold text-muted-foreground">Revoked devices</span>
                <span data-testid="count-revoked_devices" className="text-2xl font-bold text-slate-100 mt-2">{summary.revoked_devices}</span>
              </div>
              <div className="bg-background/40 border border-border/50 rounded-2xl p-4 flex flex-col justify-between hover:border-primary/30 transition-colors">
                <span className="text-xs font-semibold text-muted-foreground">Cancelled shifts</span>
                <span data-testid="count-cancelled_shifts" className="text-2xl font-bold text-slate-100 mt-2">{summary.cancelled_shifts}</span>
              </div>
              <div className="bg-background/40 border border-border/50 rounded-2xl p-4 flex flex-col justify-between hover:border-primary/30 transition-colors">
                <span className="text-xs font-semibold text-muted-foreground">WebSocket closes</span>
                <span data-testid="count-websocket_security_closes" className="text-2xl font-bold text-slate-100 mt-2">{summary.websocket_security_closes}</span>
              </div>
            </div>
          )
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border gap-1">
        <button
          onClick={() => setActiveTab('shifts')}
          className={cn(
            "px-5 py-3 border-b-2 font-medium text-sm transition-all flex items-center gap-2",
            activeTab === 'shifts'
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <Calendar size={16} />
          Employee Shifts
        </button>
        <button
          onClick={() => setActiveTab('sessions')}
          className={cn(
            "px-5 py-3 border-b-2 font-medium text-sm transition-all flex items-center gap-2",
            activeTab === 'sessions'
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <Users size={16} />
          Active Sessions
        </button>
        <button
          onClick={() => setActiveTab('devices')}
          className={cn(
            "px-5 py-3 border-b-2 font-medium text-sm transition-all flex items-center gap-2",
            activeTab === 'devices'
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <KeyRound size={16} />
          Trusted Devices
        </button>
        <button
          onClick={() => setActiveTab('events')}
          className={cn(
            "px-5 py-3 border-b-2 font-medium text-sm transition-all flex items-center gap-2",
            activeTab === 'events'
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <AlertTriangle size={16} />
          Investigations
        </button>
      </div>

      {/* Filters Area */}
      <div className="bg-card/50 border border-border rounded-2xl p-4 flex flex-wrap gap-4 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground size-4" />
          <input
            type="text"
            placeholder="Search by Employee ID..."
            value={filterEmployeeId}
            onChange={(e) => setFilterEmployeeId(e.target.value)}
            className="w-full bg-background/50 border border-border rounded-xl pl-10 pr-4 py-2 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
          />
        </div>

        {activeTab === 'shifts' && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Date</span>
            <input
              type="date"
              value={filterDate}
              onChange={(e) => setFilterDate(e.target.value)}
              className="bg-background/50 border border-border rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
            />
          </div>
        )}

        {activeTab === 'sessions' && (
          <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-muted-foreground hover:text-foreground transition-colors">
            <input
              type="checkbox"
              checked={filterActiveOnly}
              onChange={(e) => setFilterActiveOnly(e.target.checked)}
              className="rounded border-border text-primary focus:ring-primary size-4"
            />
            <span>Active Only</span>
          </label>
        )}

        {activeTab === 'devices' && (
          <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-muted-foreground hover:text-foreground transition-colors">
            <input
              type="checkbox"
              checked={filterTrustedOnly}
              onChange={(e) => setFilterTrustedOnly(e.target.checked)}
              className="rounded border-border text-primary focus:ring-primary size-4"
            />
            <span>Trusted Only</span>
          </label>
        )}

        {activeTab === 'events' && (
          <>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Action</span>
              <select
                value={eventFilterAction}
                onChange={(e) => setEventFilterAction(e.target.value)}
                className="bg-background/50 border border-border rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
              >
                <option value="">All actions</option>
                <option value="SECURITY_POLICY_DENIAL">Policy denials</option>
                <option value="SESSION_REVOKED">Session revokes</option>
                <option value="DEVICE_REVOKED">Device revokes</option>
                <option value="DEVICE_APPROVED">Device approvals</option>
                <option value="SHIFT_CREATE">Shift creates</option>
                <option value="SHIFT_UPDATE">Shift updates</option>
                <option value="SHIFT_CANCEL">Shift cancels</option>
              </select>
            </div>
            <div className="relative flex-1 min-w-[180px]">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground size-4" />
              <input
                type="text"
                placeholder="Filter by employee ID..."
                value={eventFilterEmployeeId}
                onChange={(e) => setEventFilterEmployeeId(e.target.value)}
                className="w-full bg-background/50 border border-border rounded-xl pl-10 pr-4 py-2 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
              />
            </div>
            <div className="relative flex-1 min-w-[220px]">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground size-4" />
              <input
                type="text"
                placeholder="Search event text..."
                value={eventSearch}
                onChange={(e) => setEventSearch(e.target.value)}
                className="w-full bg-background/50 border border-border rounded-xl pl-10 pr-4 py-2 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Outcome</span>
              <select
                value={eventFilterOutcome}
                onChange={(e) => setEventFilterOutcome(e.target.value as 'all' | 'success' | 'failure')}
                className="bg-background/50 border border-border rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
              >
                <option value="all">All outcomes</option>
                <option value="success">Success only</option>
                <option value="failure">Failures only</option>
              </select>
            </div>
          </>
        )}

        <button
          onClick={refreshActiveTab}
          className="px-4 py-2 bg-secondary hover:bg-secondary/80 border border-border text-sm font-medium rounded-xl transition-all ml-auto"
        >
          Apply Filters
        </button>
      </div>

      {/* Main Content Area */}
      <div className="bg-card/30 border border-border rounded-3xl overflow-hidden min-h-[300px] flex flex-col">
        {((activeTab === 'events' ? eventsLoading : loading)) ? (
          <div className="flex-1 flex flex-col items-center justify-center py-20 gap-3">
            <Loader2 className="animate-spin text-primary size-8" />
            <p className="text-muted-foreground text-sm font-medium">Loading records...</p>
          </div>
        ) : (
          <>
            {/* SHIFTS TAB */}
            {activeTab === 'shifts' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border bg-secondary/30 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      <th className="px-6 py-4">ID</th>
                      <th className="px-6 py-4">Employee ID</th>
                      <th className="px-6 py-4">Work Date</th>
                      <th className="px-6 py-4">Hours</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {shifts.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="text-center py-16 text-muted-foreground text-sm">
                          No shifts scheduled.
                        </td>
                      </tr>
                    ) : (
                      shifts.map((shift) => (
                        <tr key={shift.id} className="hover:bg-secondary/10 transition-colors">
                          <td className="px-6 py-4 text-sm font-medium text-slate-300">#{shift.id}</td>
                          <td className="px-6 py-4 text-sm text-foreground">Employee {shift.employee_id}</td>
                          <td className="px-6 py-4 text-sm text-muted-foreground">{shift.work_date}</td>
                          <td className="px-6 py-4 text-sm text-foreground font-medium flex items-center gap-1.5 py-5">
                            <Clock size={14} className="text-primary" />
                            {shift.starts_at} - {shift.ends_at}
                          </td>
                          <td className="px-6 py-4">
                            <span className={cn(
                              "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border",
                              shift.status === 'scheduled' && "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
                              shift.status === 'disabled' && "bg-slate-500/10 text-slate-400 border-slate-500/20",
                              shift.status === 'cancelled' && "bg-red-500/10 text-red-400 border-red-500/20"
                            )}>
                              {shift.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right space-x-2">
                            {shift.status !== 'cancelled' && (
                              <>
                                <button
                                  onClick={() => handleOpenUpdateShift(shift)}
                                  className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
                                  title="Edit Shift"
                                >
                                  <Edit size={15} />
                                </button>
                                <button
                                  onClick={() => handleOpenCancelShift(shift)}
                                  className="p-1.5 rounded-lg text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-all"
                                  title="Cancel Shift"
                                >
                                  <XCircle size={15} />
                                </button>
                              </>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* SESSIONS TAB */}
            {activeTab === 'sessions' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border bg-secondary/30 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      <th className="px-6 py-4">ID</th>
                      <th className="px-6 py-4">Employee ID</th>
                      <th className="px-6 py-4">Created At</th>
                      <th className="px-6 py-4">Expires At</th>
                      <th className="px-6 py-4">Last Seen At</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {sessions.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="text-center py-16 text-muted-foreground text-sm">
                          No active sessions found.
                        </td>
                      </tr>
                    ) : (
                      sessions.map((session) => (
                        <tr key={session.id} className="hover:bg-secondary/10 transition-colors">
                          <td className="px-6 py-4 text-sm font-medium text-slate-300">#{session.id}</td>
                          <td className="px-6 py-4 text-sm text-foreground">Employee {session.employee_id}</td>
                          <td className="px-6 py-4 text-sm text-muted-foreground">
                            {session.created_at ? new Date(session.created_at).toLocaleString() : '-'}
                          </td>
                          <td className="px-6 py-4 text-sm text-muted-foreground">
                            {session.expires_at ? new Date(session.expires_at).toLocaleString() : '-'}
                          </td>
                          <td className="px-6 py-4 text-sm text-muted-foreground">
                            {session.last_seen_at ? new Date(session.last_seen_at).toLocaleString() : '-'}
                          </td>
                          <td className="px-6 py-4">
                            <span className={cn(
                              "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border",
                              session.is_active 
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                                : "bg-red-500/10 text-red-400 border-red-500/20"
                            )}>
                              {session.is_active ? 'Active' : 'Revoked'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right">
                            {session.is_active && (
                              <button
                                onClick={() => handleOpenRevokeSession(session)}
                                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white border border-red-500/20 transition-all"
                              >
                                Revoke
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* TRUSTED DEVICES TAB */}
            {activeTab === 'devices' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border bg-secondary/30 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      <th className="px-6 py-4">ID</th>
                      <th className="px-6 py-4">Employee ID</th>
                      <th className="px-6 py-4">Label</th>
                      <th className="px-6 py-4">Fingerprint</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4">Last Seen At</th>
                      <th className="px-6 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {devices.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="text-center py-16 text-muted-foreground text-sm">
                          No devices registered.
                        </td>
                      </tr>
                    ) : (
                      devices.map((device) => (
                        <tr key={device.id} className="hover:bg-secondary/10 transition-colors">
                          <td className="px-6 py-4 text-sm font-medium text-slate-300">#{device.id}</td>
                          <td className="px-6 py-4 text-sm text-foreground">Employee {device.employee_id}</td>
                          <td className="px-6 py-4 text-sm text-foreground font-medium">{device.label || 'Unnamed Device'}</td>
                          <td className="px-6 py-4 text-sm font-mono text-muted-foreground">
                            {device.fingerprint || 'N/A'}
                          </td>
                          <td className="px-6 py-4">
                            <span className={cn(
                              "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border",
                              device.is_trusted 
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                                : "bg-red-500/10 text-red-400 border-red-500/20"
                            )}>
                              {device.is_trusted ? 'Trusted' : 'Revoked'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-sm text-muted-foreground">
                            {device.last_seen_at ? new Date(device.last_seen_at).toLocaleString() : '-'}
                          </td>
                          <td className="px-6 py-4 text-right space-x-2">
                            {device.is_trusted ? (
                              <button
                                onClick={() => handleOpenRevokeDevice(device)}
                                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white border border-red-500/20 transition-all"
                              >
                                Revoke
                              </button>
                            ) : (
                              <button
                                onClick={() => handleOpenApproveDevice(device)}
                                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/10 hover:bg-emerald-500 text-emerald-400 hover:text-white border border-emerald-500/20 transition-all"
                              >
                                Approve
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'events' && (
              <div className="space-y-4 p-4">
                {eventsError ? (
                  <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertTriangle size={18} />
                      <span className="text-sm font-medium">{eventsError}</span>
                    </div>
                    <button
                      onClick={() => fetchEvents({ reset: true })}
                      className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500 text-red-400 hover:text-white rounded-lg text-xs font-semibold border border-red-500/30 transition-all flex items-center gap-1.5"
                    >
                      <RefreshCw size={12} />
                      Retry
                    </button>
                  </div>
                ) : null}

                {events.length === 0 ? (
                  <div className="bg-background/20 border border-border/40 rounded-2xl p-8 text-center text-muted-foreground flex flex-col items-center justify-center gap-2">
                    <CheckCircle className="text-emerald-500/60 size-8" />
                    <p className="text-sm font-medium text-slate-300">No security events matched the current filters.</p>
                    <p className="text-xs text-muted-foreground">Use the filters above to inspect sessions, devices, shifts, and policy denials.</p>
                  </div>
                ) : (
                  <>
                    <div className="text-xs text-muted-foreground font-medium">
                      Showing {events.length} of {eventsTotal} events
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="border-b border-border bg-secondary/30 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                            <th className="px-6 py-4">Time</th>
                            <th className="px-6 py-4">Action</th>
                            <th className="px-6 py-4">Subject</th>
                            <th className="px-6 py-4">Actor</th>
                            <th className="px-6 py-4">Outcome</th>
                            <th className="px-6 py-4">Summary</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/60">
                          {events.map((event) => (
                            <tr key={event.id} className="hover:bg-secondary/10 transition-colors align-top">
                              <td className="px-6 py-4 text-sm text-muted-foreground whitespace-nowrap">
                                {new Date(event.created_at).toLocaleString()}
                              </td>
                              <td className="px-6 py-4 text-sm font-medium text-slate-100 whitespace-nowrap">
                                {event.action}
                              </td>
                              <td className="px-6 py-4 text-sm text-foreground">
                                <div className="space-y-1">
                                  <div>{event.subject_employee_id ? `Employee ${event.subject_employee_id}` : 'Unknown subject'}</div>
                                  {event.target && <div className="text-xs text-muted-foreground">{event.target}</div>}
                                </div>
                              </td>
                              <td className="px-6 py-4 text-sm text-muted-foreground">
                                <div className="space-y-1">
                                  <div>{event.actor_email || `Employee ${event.actor_id ?? 'system'}`}</div>
                                  <div className="text-xs">{event.reason || 'No reason supplied'}</div>
                                </div>
                              </td>
                              <td className="px-6 py-4">
                                <span className={cn(
                                  "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border",
                                  event.success ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-red-500/10 text-red-400 border-red-500/20"
                                )}>
                                  {event.success ? 'Success' : 'Failure'}
                                </span>
                              </td>
                              <td className="px-6 py-4 text-sm text-muted-foreground">
                                <div className="max-w-3xl space-y-1">
                                  <div className="text-foreground">{event.summary || 'No summary available'}</div>
                                  {event.details && <div className="text-xs whitespace-pre-wrap break-words">{event.details}</div>}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {eventsOffset < eventsTotal && (
                      <div className="flex justify-center">
                        <button
                          onClick={() => fetchEvents({ reset: false })}
                          className="px-4 py-2 bg-secondary hover:bg-secondary/80 border border-border text-sm font-medium rounded-xl transition-all"
                        >
                          Load More
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* CONFIRM ACTION DIALOG (MODAL) */}
      {confirmDialog.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-3xl w-full max-w-md p-6 shadow-2xl space-y-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-red-500/10 text-red-400 border border-red-500/20 rounded-2xl flex-shrink-0">
                <AlertTriangle size={24} />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-xl font-bold text-slate-100">{confirmDialog.title}</h3>
                <p className="text-sm text-muted-foreground">
                  Confirming this action will apply lifecycle changes for <strong>Employee {confirmDialog.employeeId}</strong>.
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">
                Reason for action <span className="text-red-400">*</span>
              </label>
              <textarea
                required
                rows={3}
                placeholder="Specify the reason (e.g. Schedule cancellation, Device security audit...)"
                value={confirmDialog.reason}
                onChange={(e) => setConfirmDialog({ ...confirmDialog, reason: e.target.value })}
                className="w-full bg-background border border-border rounded-2xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all resize-none"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setConfirmDialog({ isOpen: false, action: null, title: '', targetId: null, employeeId: '', reason: '' })}
                className="flex-1 px-4 py-3 bg-secondary hover:bg-secondary/80 border border-border text-sm font-bold rounded-2xl transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAction}
                className="flex-1 px-4 py-3 bg-red-500 hover:bg-red-400 disabled:bg-secondary disabled:text-muted-foreground text-white text-sm font-bold rounded-2xl transition-all shadow-lg shadow-red-500/10"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SHIFT SCHEDULER / EDITOR MODAL */}
      {shiftModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-3xl w-full max-w-lg p-6 shadow-2xl space-y-6">
            <div className="space-y-1.5">
              <h3 className="text-2xl font-bold text-slate-100">
                {shiftModal.mode === 'create' ? 'Schedule Employee Shift' : 'Edit Shift Schedule'}
              </h3>
              <p className="text-sm text-muted-foreground">
                Set employee shift timings and operational lifecycle parameters.
              </p>
            </div>

            <form onSubmit={handleSaveShift} className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">
                    Employee ID <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    disabled={shiftModal.mode === 'update'}
                    value={shiftModal.employeeId}
                    onChange={(e) => setShiftModal({ ...shiftModal, employeeId: e.target.value })}
                    placeholder="e.g. 123"
                    className="w-full bg-background border border-border rounded-2xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all disabled:opacity-50"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">
                    Work Date <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={shiftModal.workDate}
                    onChange={(e) => setShiftModal({ ...shiftModal, workDate: e.target.value })}
                    className="w-full bg-background border border-border rounded-2xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">
                    Shift Starts At <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={shiftModal.startsAt}
                    onChange={(e) => setShiftModal({ ...shiftModal, startsAt: e.target.value })}
                    placeholder="09:00:00"
                    className="w-full bg-background border border-border rounded-2xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">
                    Shift Ends At <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={shiftModal.endsAt}
                    onChange={(e) => setShiftModal({ ...shiftModal, endsAt: e.target.value })}
                    placeholder="17:00:00"
                    className="w-full bg-background border border-border rounded-2xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">Status</label>
                <select
                  value={shiftModal.status}
                  onChange={(e) => setShiftModal({ ...shiftModal, status: e.target.value })}
                  className="w-full bg-background border border-border rounded-2xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
                >
                  <option value="scheduled">Scheduled</option>
                  <option value="disabled">Disabled</option>
                </select>
              </div>

              {shiftModal.mode === 'update' && (
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">
                    Reason for update <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={shiftModal.reason}
                    onChange={(e) => setShiftModal({ ...shiftModal, reason: e.target.value })}
                    placeholder="Specify the reason for updating this shift..."
                    className="w-full bg-background border border-border rounded-2xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-primary/50 transition-all"
                  />
                </div>
              )}

              <div className="flex gap-3 pt-3 border-t border-border/60">
                <button
                  type="button"
                  onClick={() => setShiftModal({ ...shiftModal, isOpen: false, reason: '' })}
                  className="flex-1 px-4 py-3 bg-secondary hover:bg-secondary/80 border border-border text-sm font-bold rounded-2xl transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-3 bg-primary hover:bg-indigo-400 text-white text-sm font-bold rounded-2xl transition-all shadow-lg shadow-indigo-500/10"
                >
                  Save Schedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
export default AdminSecurity;
