import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserRole, CurrentUser } from '../lib/types';
import { getCurrentUser } from '../lib/api';
import { Loader2 } from 'lucide-react';

interface AppContextType {
  userRole: UserRole;
  setUserRole: (role: UserRole) => void;
  currentUser: CurrentUser | null;
  setCurrentUser: (user: CurrentUser | null) => void;
  piiMaskingEnabled: boolean;
  setPiiMaskingEnabled: (v: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [userRole, setUserRoleState] = useState<UserRole>(UserRole.AGENT);
  const [piiMaskingEnabled, setPiiMaskingEnabled] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    document.documentElement.classList.add('dark');

    const bootstrapSession = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const data = await getCurrentUser();
        const normalizedRole = (data.role ? data.role.toLowerCase() : 'agent') as UserRole;
        const normalizedUser: CurrentUser = {
          id: data.id,
          name: data.name,
          email: data.email || '',
          role: normalizedRole,
          avatar: data.avatar || '',
          account_status: data.account_status || data.status || 'active',
        };
        setCurrentUser(normalizedUser);
        setUserRoleState(normalizedRole);
        localStorage.setItem('user', JSON.stringify(normalizedUser));
      } catch (error) {
        console.error('Session bootstrap failed:', error);
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        setCurrentUser(null);
        setUserRoleState(UserRole.AGENT);
      } finally {
        setLoading(false);
      }
    };

    bootstrapSession();
  }, []);

  const setUserRole = (role: UserRole) => {
    const normalizedRole = role.toLowerCase() as UserRole;
    setUserRoleState(normalizedRole);
    if (currentUser) {
      const updated = { ...currentUser, role: normalizedRole };
      setCurrentUser(updated);
      localStorage.setItem('user', JSON.stringify(updated));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 text-center p-4">
        <Loader2 className="animate-spin text-primary size-10" />
        <p className="text-muted-foreground text-sm font-medium animate-pulse">Initializing Secure Session...</p>
      </div>
    );
  }

  return (
    <AppContext.Provider value={{
      userRole,
      setUserRole,
      currentUser,
      setCurrentUser,
      piiMaskingEnabled,
      setPiiMaskingEnabled,
      sidebarCollapsed,
      setSidebarCollapsed,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
