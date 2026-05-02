import { RouterProvider } from 'react-router';
import { Toaster } from 'sonner';
import { router } from './routes';
import { LangProvider } from './context/LangContext';

import ErrorBoundary from './components/ErrorBoundary';

export default function App() {
  return (
    <ErrorBoundary>
      <LangProvider>
        <Toaster position="top-right" richColors />
        <RouterProvider router={router} />
      </LangProvider>
    </ErrorBoundary>
  );
}
