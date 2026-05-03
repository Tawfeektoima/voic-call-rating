import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserRole } from '../lib/types';

interface CurrentUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  avatar: string;
}

interface AppContextType {
  userRole: UserRole;
  setUserRole: (role: UserRole) => void;
  currentUser: CurrentUser;
  piiMaskingEnabled: boolean;
  setPiiMaskingEnabled: (v: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;
}

const AppContext = createContext<AppContextType | null>(null);

// Fallback user for demo purposes when no real session is active
const fallbackUser = {
  id: 1,
  name: 'Demo Admin',
  email: 'admin@voiceqa.ai',
  role: UserRole.ADMIN,
  avatar: 'AD'
};

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [userRole, setUserRole] = useState<UserRole>(UserRole.ADMIN);
  const [piiMaskingEnabled, setPiiMaskingEnabled] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  // In a real app, this would be fetched from /api/auth/me or similar
  const currentUser: CurrentUser = {
    ...fallbackUser,
    role: userRole,
    avatar: userRole.substring(0, 2).toUpperCase()
  };

  return (
    <AppContext.Provider value={{
      userRole,
      setUserRole,
      currentUser,
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
