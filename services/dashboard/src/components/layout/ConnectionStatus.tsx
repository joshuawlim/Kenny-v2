// Connection status indicator component
import React from 'react'
import { Wifi, WifiOff, RotateCw } from 'lucide-react'
import { useSystemHealthStream, useSecurityEventStream } from '@/hooks'

export const ConnectionStatus: React.FC = () => {
  const { connectionStatus: healthConnection } = useSystemHealthStream()
  const { connectionStatus: securityConnection } = useSecurityEventStream()

  const isHealthConnected = healthConnection.isConnected
  const isSecurityConnected = securityConnection.isConnected
  const overallConnected = isHealthConnected && isSecurityConnected

  const getStatusColor = () => {
    if (overallConnected) return 'bg-kenny-success'
    if (isHealthConnected || isSecurityConnected) return 'bg-kenny-warning'
    return 'bg-kenny-error'
  }

  const getStatusText = () => {
    if (overallConnected) return 'Connected'
    if (isHealthConnected || isSecurityConnected) return 'Partial Connection'
    
    const maxAttempts = Math.max(
      healthConnection.reconnectAttempts,
      securityConnection.reconnectAttempts
    )
    
    if (maxAttempts > 0) return `Reconnecting (${maxAttempts}/5)`
    return 'Disconnected'
  }

  const getIcon = () => {
    if (overallConnected) return <Wifi className="w-4 h-4" />
    if (healthConnection.reconnectAttempts > 0 || securityConnection.reconnectAttempts > 0) {
      return <RotateCw className="w-4 h-4 animate-spin" />
    }
    return <WifiOff className="w-4 h-4" />
  }

  return (
    <div className="flex items-center space-x-2">
      <div className={`${getStatusColor()} rounded-full p-2 text-white`}>
        {getIcon()}
      </div>
      <div className="text-sm">
        <div className="font-medium text-kenny-gray-700">
          {getStatusText()}
        </div>
        <div className="text-xs text-kenny-gray-500">
          Health: {isHealthConnected ? '✓' : '✗'} | 
          Security: {isSecurityConnected ? '✓' : '✗'}
        </div>
      </div>
    </div>
  )
}