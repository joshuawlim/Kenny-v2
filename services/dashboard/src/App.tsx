// Main App component with routing
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './theme';
import { AppShell } from './components/AppShell';
import { Dashboard } from './components/Dashboard';
import { Chat } from './components/Chat';
import { AgentsPage } from '@/pages/Agents';
import { QueryPage } from '@/pages/Query';
import { HealthPage } from '@/pages/Health';
import { SecurityPage } from '@/pages/Security';
import { AnalyticsPage } from '@/pages/Analytics';
import { TracesPage } from '@/pages/Traces';
import { AlertsPage } from '@/pages/Alerts';
import { NotFoundPage } from '@/pages/NotFound';

function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="chat" element={<Chat />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="query" element={<QueryPage />} />
          <Route path="health" element={<HealthPage />} />
          <Route path="security" element={<SecurityPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="traces" element={<TracesPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </ThemeProvider>
  );
}

export default App;