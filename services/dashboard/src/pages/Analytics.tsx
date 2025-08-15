// Analytics page - placeholder for now
import React from 'react'
import { BarChart3 } from 'lucide-react'

export const AnalyticsPage: React.FC = () => {
  return (
    <div className="space-y-8">
      <div className="text-center py-12">
        <BarChart3 className="w-16 h-16 text-kenny-warning mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-kenny-gray-800 mb-2">
          Performance Analytics
        </h1>
        <p className="text-kenny-gray-600 max-w-md mx-auto">
          Detailed performance analytics and visualization will be implemented in the next phase.
        </p>
      </div>
    </div>
  )
}