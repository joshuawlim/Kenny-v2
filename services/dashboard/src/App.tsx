// Main App component with routing
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/layout'
import { DashboardPage } from '@/pages/Dashboard'
import { AgentsPage } from '@/pages/Agents'
import { QueryPage } from '@/pages/Query'
import { HealthPage } from '@/pages/Health'
import { SecurityPage } from '@/pages/Security'
import { AnalyticsPage } from '@/pages/Analytics'
import { TracesPage } from '@/pages/Traces'
import { AlertsPage } from '@/pages/Alerts'
import { NotFoundPage } from '@/pages/NotFound'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<DashboardPage />} />
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
  )
}

export default App