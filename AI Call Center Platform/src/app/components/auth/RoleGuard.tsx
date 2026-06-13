import { ReactNode } from 'react';
import { Navigate } from 'react-router';
import { useApp } from '../../context/AppContext';
import { UserRole } from '../../lib/types';
import { Permission, hasPermission } from '../../lib/roles';

interface Props {
  children: ReactNode;
  allowedRoles?: UserRole[];
  requiredPermission?: Permission;
  anyPermissions?: Permission[];
}

/**
 * Protects a route by redirecting unauthenticated users to login and
 * authenticated users without the required role/permission to the dashboard.
 */
export function RoleGuard({ children, allowedRoles, requiredPermission, anyPermissions }: Props) {
  const { currentUser, userRole } = useApp();

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  const allowedByRole = allowedRoles ? allowedRoles.includes(userRole) : true;
  const allowedByPermission = requiredPermission
    ? hasPermission(userRole, requiredPermission, currentUser.permissions)
    : true;
  const allowedByAnyPermission = anyPermissions
    ? anyPermissions.some((permission) => hasPermission(userRole, permission, currentUser.permissions))
    : true;

  if (!allowedByRole || !allowedByPermission || !allowedByAnyPermission) {
    const pathname = typeof window !== 'undefined' ? window.location.pathname : '';
    return <Navigate to={pathname === '/' ? '/notes' : '/'} replace />;
  }

  return <>{children}</>;
}
