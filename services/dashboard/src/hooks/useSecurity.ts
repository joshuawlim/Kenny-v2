// Custom hooks for security monitoring
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { registryAPI } from '@/services'
import type { SecurityEvent, SecurityIncident, ComplianceSummary, ConnectionStatus } from '@/types'

export const useSecurityEvents = (hours: number = 24, severity?: string) => {
  return useQuery({
    queryKey: ['security-events', hours, severity],
    queryFn: () => registryAPI.getSecurityEvents(hours, severity),
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 3,
  })
}

export const useSecurityIncidents = (hours: number = 24, status?: string) => {
  return useQuery({
    queryKey: ['security-incidents', hours, status],
    queryFn: () => registryAPI.getSecurityIncidents(hours, status),
    refetchInterval: 60000, // Incidents change less frequently
    retry: 3,
  })
}

export const useComplianceSummary = () => {
  return useQuery({
    queryKey: ['compliance-summary'],
    queryFn: () => registryAPI.getComplianceSummary(),
    refetchInterval: 60000, // Check compliance every minute
    retry: 3,
  })
}

export const useSecurityDashboard = (hours: number = 24) => {
  return useQuery({
    queryKey: ['security-dashboard', hours],
    queryFn: () => registryAPI.getSecurityDashboard(hours),
    refetchInterval: 30000,
    retry: 3,
  })
}

export const useSecurityEventStream = () => {
  const [events, setEvents] = useState<SecurityEvent[]>([])
  const [incidents, setIncidents] = useState<SecurityIncident[]>([])
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
        eventSource = registryAPI.createSecurityEventStream()
        
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
            
            switch (eventData.type) {
              case 'new_security_events':
                if (eventData.events) {
                  setEvents(prev => [...eventData.events, ...prev].slice(0, 50)) // Keep latest 50
                }
                break
                
              case 'new_security_incidents':
                if (eventData.incidents) {
                  setIncidents(prev => [...eventData.incidents, ...prev].slice(0, 20)) // Keep latest 20
                }
                break
                
              case 'security_status_update':
                // Handle status updates if needed
                break
            }
          } catch (err) {
            console.error('Failed to parse security event stream:', err)
          }
        }

        eventSource.onerror = (err) => {
          console.error('Security event stream error:', err)
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
    events,
    incidents,
    connectionStatus,
    error,
    isConnected: connectionStatus.isConnected,
  }
}

// Transform security data for dashboard consumption
export const useSecurityMetrics = () => {
  const { data: events } = useSecurityEvents(24)
  const { data: incidents } = useSecurityIncidents(24)
  const { data: compliance } = useComplianceSummary()

  const eventsBySeverity = events?.events.reduce((acc, event) => {
    acc[event.severity] = (acc[event.severity] || 0) + 1
    return acc
  }, {} as Record<string, number>) || {}

  const incidentsByStatus = incidents?.incidents.reduce((acc, incident) => {
    acc[incident.status] = (acc[incident.status] || 0) + 1
    return acc
  }, {} as Record<string, number>) || {}

  const criticalEvents = eventsBySeverity.critical || 0
  const highEvents = eventsBySeverity.high || 0
  const openIncidents = incidentsByStatus.open || 0

  return {
    totalEvents: events?.total_count || 0,
    criticalEvents,
    highEvents,
    totalIncidents: incidents?.total_count || 0,
    openIncidents,
    complianceScore: compliance?.compliance_score || 100,
    complianceStatus: compliance?.compliance_status || 'unknown',
    securityScore: Math.max(0, 100 - (criticalEvents * 10) - (highEvents * 5) - (openIncidents * 15)),
  }
}