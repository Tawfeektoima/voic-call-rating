/**
 * Shared UI state primitives.
 * Use these instead of per-page ad-hoc skeleton/empty/error patterns.
 */
import { ReactNode } from 'react';
import { Loader2, AlertCircle, InboxIcon } from 'lucide-react';
import { cn } from './utils';

// ---------------------------------------------------------------------------
// PageLoader — full-screen spinner for top-level async bootstrapping
// ---------------------------------------------------------------------------
export function PageLoader({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full w-full gap-4 text-center p-8 min-h-[200px]">
      <Loader2 className="animate-spin text-primary size-8" />
      <p className="text-muted-foreground text-sm font-medium animate-pulse">{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SectionLoader — skeleton rows for list/table sections
// ---------------------------------------------------------------------------
export function SectionLoader({
  rows = 4,
  className,
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-12 rounded-lg bg-secondary animate-pulse"
          style={{ opacity: 1 - i * 0.15 }}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// EmptyState — icon + title + description for empty data sections
// ---------------------------------------------------------------------------
export function EmptyState({
  icon: Icon = InboxIcon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ElementType;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-10 text-center', className)}>
      <div className="size-12 rounded-xl bg-secondary flex items-center justify-center">
        <Icon size={22} className="text-muted-foreground" />
      </div>
      <div className="space-y-1">
        <p className="text-foreground text-sm font-medium">{title}</p>
        {description && <p className="text-muted-foreground text-xs max-w-xs">{description}</p>}
      </div>
      {action}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ErrorState — error card with optional retry
// ---------------------------------------------------------------------------
export function ErrorState({
  message = 'Something went wrong.',
  onRetry,
  className,
}: {
  message?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 py-10 text-center',
        className,
      )}
    >
      <div className="size-12 rounded-xl bg-red-500/10 flex items-center justify-center">
        <AlertCircle size={22} className="text-red-400" />
      </div>
      <div className="space-y-1">
        <p className="text-foreground text-sm font-medium">Failed to load data</p>
        <p className="text-muted-foreground text-xs max-w-xs">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 text-xs text-primary hover:text-primary/80 underline underline-offset-2 transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  );
}
