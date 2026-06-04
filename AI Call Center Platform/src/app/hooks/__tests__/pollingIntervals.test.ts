// @vitest-environment node

import { describe, expect, it } from 'vitest';

import { DASHBOARD_REFETCH_INTERVAL_MS } from '../useDashboard';
import { LEADS_REFETCH_INTERVAL_MS } from '../useLeads';
import {
  SYSTEM_ALERTS_REFETCH_INTERVAL_MS,
  SYSTEM_METRICS_REFETCH_INTERVAL_MS,
} from '../useSystemHealth';

describe('polling intervals', () => {
  it('keeps dashboard and system polling bounded', () => {
    expect(DASHBOARD_REFETCH_INTERVAL_MS).toBe(30000);
    expect(SYSTEM_METRICS_REFETCH_INTERVAL_MS).toBe(30000);
    expect(SYSTEM_ALERTS_REFETCH_INTERVAL_MS).toBe(120000);
    expect(LEADS_REFETCH_INTERVAL_MS).toBe(120000);
  });
});
