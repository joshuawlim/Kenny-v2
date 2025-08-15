// Health monitoring page - placeholder for now
import React from 'react'
import { Activity } from 'lucide-react'

export const HealthPage: React.FC = () => {
  return (
    <div className="space-y-8">
      <div className="text-center py-12">
        <Activity className="w-16 h-16 text-kenny-success mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-kenny-gray-800 mb-2">
          System Health Monitoring
        </h1>
        <p className="text-kenny-gray-600 max-w-md mx-auto">
          Detailed health monitoring dashboard will be implemented in the next phase.
        </p>
      </div>
    </div>
  )
}