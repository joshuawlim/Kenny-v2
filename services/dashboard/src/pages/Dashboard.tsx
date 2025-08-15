// Main dashboard page component
import React from 'react'
import { SystemOverview, PerformanceChart, RecentActivity } from '@/components/dashboard'

export const DashboardPage: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* System Overview Metrics */}
      <SystemOverview />

      {/* Charts and Activity Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Performance Chart - Takes 2 columns on large screens */}
        <div className="lg:col-span-2">
          <PerformanceChart />
        </div>

        {/* Recent Activity - Takes 1 column */}
        <div className="lg:col-span-1">
          <RecentActivity />
        </div>
      </div>
    </div>
  )
}