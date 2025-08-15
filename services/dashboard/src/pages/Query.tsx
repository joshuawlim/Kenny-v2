// Query interface page - placeholder for now
import React from 'react'
import { MessageSquare } from 'lucide-react'

export const QueryPage: React.FC = () => {
  return (
    <div className="space-y-8">
      <div className="text-center py-12">
        <MessageSquare className="w-16 h-16 text-kenny-primary mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-kenny-gray-800 mb-2">
          Multi-Agent Query Interface
        </h1>
        <p className="text-kenny-gray-600 max-w-md mx-auto">
          Query interface with WebSocket streaming will be implemented in the next phase.
        </p>
      </div>
    </div>
  )
}