import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie">{children}</div>
  ),
  Cell: ({ fill }: { fill: string }) => <div data-testid={`cell-${fill}`} />,
  Tooltip: () => <div data-testid="tooltip" />,
}));

import { CallAnalysis } from '../components/call/CallAnalysis';
import { OfferFunnel } from '../components/call/OfferFunnel';
import { TalkListenGauge } from '../components/call/TalkListenGauge';
import { EmptyState, ErrorState, PageLoader, SectionLoader } from '../components/ui/states';

describe('call presentation coverage', () => {
  it('renders strengths and weaknesses with stable content', () => {
    render(
      <CallAnalysis
        strengths={['Strong opening', 'Handled objections clearly']}
        weaknesses={[
          {
            issue: 'Missed discovery',
            detail: 'The caller skipped a qualifying question.',
            deduction: 8,
          },
        ]}
      />,
    );

    expect(screen.getByText('Strengths & Achievements')).toBeInTheDocument();
    expect(screen.getByText('Strong opening')).toBeInTheDocument();
    expect(screen.getByText('Handled objections clearly')).toBeInTheDocument();
    expect(screen.getByText('Deductions & Weaknesses')).toBeInTheDocument();
    expect(screen.getByText('Missed discovery')).toBeInTheDocument();
    expect(screen.getByText('The caller skipped a qualifying question.')).toBeInTheDocument();
    expect(screen.getByText('-8')).toBeInTheDocument();
  });

  it('renders empty analysis fallbacks when no data is present', () => {
    render(<CallAnalysis strengths={[]} weaknesses={[]} />);

    expect(screen.getByText('No notable strengths identified in this call.')).toBeInTheDocument();
    expect(screen.getByText('Perfect performance! No weaknesses identified.')).toBeInTheDocument();
  });

  it('renders offer funnel states for presented and skipped offers', () => {
    render(
      <OfferFunnel
        presented={['Premium Upgrade']}
        skipped={['Retention Bundle']}
        details={[
          {
            offer_name: 'Premium Upgrade',
            presented: true,
            skip_reason: null,
            qualifying_questions_asked: true,
            branch_followed_correctly: true,
          },
          {
            offer_name: 'Retention Bundle',
            presented: false,
            skip_reason: 'Customer already subscribed',
            qualifying_questions_asked: false,
            branch_followed_correctly: false,
          },
        ]}
      />,
    );

    expect(screen.getByText('Offer Presentation Funnel')).toBeInTheDocument();
    expect(screen.getByText('Presented to customer')).toBeInTheDocument();
    expect(screen.getByText('Skipped: Customer already subscribed')).toBeInTheDocument();
    expect(screen.getByText('Qualifying OK')).toBeInTheDocument();
    expect(screen.getByText('Branch OK')).toBeInTheDocument();
  });

  it('renders talk-listen metrics including silence and balance state', () => {
    render(<TalkListenGauge agentSeconds={60} customerSeconds={66} silenceSeconds={24} />);

    expect(screen.getByText('Talk-to-Listen Ratio')).toBeInTheDocument();
    expect(screen.getByText('Balanced')).toBeInTheDocument();
    expect(screen.getByText('Agent')).toBeInTheDocument();
    expect(screen.getByText('Customer')).toBeInTheDocument();
    expect(screen.getByText('Silence')).toBeInTheDocument();
    expect(screen.getByText(/Ratio = Customer\(s\)/)).toBeInTheDocument();
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('renders shared UI states and supports retry actions', () => {
    const handleRetry = vi.fn();
    const { container } = render(
      <div>
        <PageLoader message="Loading dashboard" />
        <SectionLoader rows={3} />
        <EmptyState title="No recordings yet" description="Upload or ingest audio to begin analysis." />
        <ErrorState message="Retry later." onRetry={handleRetry} />
      </div>,
    );

    expect(screen.getByText('Loading dashboard')).toBeInTheDocument();
    expect(screen.getByText('No recordings yet')).toBeInTheDocument();
    expect(screen.getByText('Upload or ingest audio to begin analysis.')).toBeInTheDocument();
    expect(screen.getByText('Failed to load data')).toBeInTheDocument();
    expect(screen.getByText('Retry later.')).toBeInTheDocument();
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThanOrEqual(4);

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });
});
