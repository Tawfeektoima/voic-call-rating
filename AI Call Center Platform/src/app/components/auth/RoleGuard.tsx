import { ReactNode } from 'react';
import { Navigate } from 'react-router';
import { useApp } from '../../context/AppContext';
import { UserRole } from '../../lib/types';

interface Props {
  children: ReactNode;
  allowedRoles: UserRole[];
}

export function RoleGuard({ children, allowedRoles }: Props) {
  const { userRole } = useApp();

  if (!allowedRoles.includes(userRole)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
