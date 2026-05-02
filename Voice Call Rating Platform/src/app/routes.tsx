import { createBrowserRouter } from 'react-router';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { CallExplorer } from './pages/CallExplorer';
import { CallDetail } from './pages/CallDetail';
import { CampaignManager } from './pages/CampaignManager';
import { AgentAnalytics } from './pages/AgentAnalytics';
import { AgentProfile } from './pages/AgentProfile';
import { Settings } from './pages/Settings';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'calls', element: <CallExplorer /> },
      { path: 'calls/:id', element: <CallDetail /> },
      { path: 'campaigns', element: <CampaignManager /> },
      { path: 'agents', element: <AgentAnalytics /> },
      { path: 'agents/:id', element: <AgentProfile /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
]);
