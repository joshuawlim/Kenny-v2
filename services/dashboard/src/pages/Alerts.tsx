// Alerts management page - placeholder for now
import React from 'react'
import { AlertTriangle } from 'lucide-react'

export const AlertsPage: React.FC = () => {
  return (
    <div className="space-y-8">
      <div className="text-center py-12">
        <AlertTriangle className="w-16 h-16 text-kenny-error mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-kenny-gray-800 mb-2">
          Alert Management
        </h1>
        <p className="text-kenny-gray-600 max-w-md mx-auto">
          Alert management and notification system will be implemented in the next phase.
        </p>
      </div>
    </div>
  )
}