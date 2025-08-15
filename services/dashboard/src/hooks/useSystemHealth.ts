// Custom hook for system health monitoring
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { registryAPI } from '@/services'
import type { HealthDashboard, ConnectionStatus } from '@/types'

export const useSystemHealth = () => {
  return useQuery({
    queryKey: ['system-health'],
    queryFn: () => registryAPI.getHealthDashboard(),
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 3,
  })
}

export const useSystemHealthStream = () => {
  const [data, setData] = useState<HealthDashboard | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    isConnected: false,
    reconnectAttempts: 0,
  })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let eventSource: EventSource | null = null
    let reconnectTimeout: NodeJS.Timeout | null = null

    const connect = () => {
      try {
        eventSource = registryAPI.createHealthStream()
        
        eventSource.onopen = () => {
          setConnectionStatus(prev => ({
            ...prev,
            isConnected: true,
            lastConnected: new Date(),
            reconnectAttempts: 0,
          }))
          setError(null)
        }

        eventSource.onmessage = (event) => {
          try {
            const eventData = JSON.parse(event.data)
            if (eventData.type === 'dashboard_update' && eventData.data) {
              setData(eventData.data)
            }
          } catch (err) {
            console.error('Failed to parse health stream event:', err)
          }
        }

        eventSource.onerror = (err) => {
          console.error('Health stream error:', err)
          setConnectionStatus(prev => ({
            ...prev,
            isConnected: false,
            lastError: 'Connection lost',
          }))
          
          // Attempt to reconnect with exponential backoff
          if (connectionStatus.reconnectAttempts < 5) {
            const delay = Math.pow(2, connectionStatus.reconnectAttempts) * 1000
            reconnectTimeout = setTimeout(() => {
              setConnectionStatus(prev => ({
                ...prev,
                reconnectAttempts: prev.reconnectAttempts + 1,
              }))
              connect()
            }, delay)
          } else {
            setError('Maximum reconnection attempts reached')
          }
        }
      } catch (err) {
        setError(`Failed to connect: ${err}`)
      }
    }

    connect()

    return () => {
      if (eventSource) {
        eventSource.close()
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
      }
    }
  }, []) // Empty dependency array since we handle reconnection internally

  return {
    data,
    connectionStatus,
    error,
    isConnected: connectionStatus.isConnected,
  }
}