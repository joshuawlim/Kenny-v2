// Security monitoring page - placeholder for now
import React from 'react'
import { Shield } from 'lucide-react'

export const SecurityPage: React.FC = () => {
  return (
    <div className="space-y-8">
      <div className="text-center py-12">
        <Shield className="w-16 h-16 text-kenny-info mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-kenny-gray-800 mb-2">
          Security Monitoring
        </h1>
        <p className="text-kenny-gray-600 max-w-md mx-auto">
          Live security events and compliance monitoring will be implemented in the next phase.
        </p>
      </div>
    </div>
  )
}