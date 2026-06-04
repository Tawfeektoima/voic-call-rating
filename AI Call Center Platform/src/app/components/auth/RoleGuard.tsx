import { ReactNode } from 'react';
import { Navigate } from 'react-router';
import { useApp } from '../../context/AppContext';
import { UserRole } from '../../lib/types';

interface Props {
  children: ReactNode;
  allowedRoles: UserRole[];
}

/**
 * Protects a route by:
 * 1. Redirecting unauthenticated users (no currentUser) to /login.
 * 2. Redirecting users whose role is not in allowedRoles to the home page.
 */
export function RoleGuard({ children, allowedRoles }: Props) {
  const { currentUser, userRole } = useApp();

  // Not authenticated — send to login
  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  // Authenticated but wrong role — send to dashboard
  if (!allowedRoles.includes(userRole)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
