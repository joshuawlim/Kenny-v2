// Agent Registry API client for Kenny v2 Dashboard
import { ApiClient } from './api'
import type {
  HealthDashboard,
  SecurityEvent,
  SecurityIncident,
  ComplianceSummary,
  TraceInfo,
  AnalyticsDashboard,
} from '@/types'

export class RegistryAPI extends ApiClient {
  constructor() {
    super('/registry') // Proxied through Vite dev server to localhost:8001
  }

  // Health & Monitoring
  async getSystemHealth(): Promise<any> {
    return this.get<any>('/system/health')
  }

  async getHealthDashboard(): Promise<HealthDashboard> {
    return this.get<HealthDashboard>('/system/health/dashboard')
  }

  // Server-Sent Events for live health updates
  createHealthStream(): EventSource {
    return this.createEventSource('/system/health/dashboard/stream')
  }

  // Security Monitoring
  async getSecurityDashboard(hours: number = 24): Promise<any> {
    return this.get<any>(`/security/dashboard?hours=${hours}`)
  }

  async getSecurityEvents(
    hours: number = 24,
    severity?: string,
    eventType?: string
  ): Promise<{ events: SecurityEvent[]; total_count: number }> {
    const params = new URLSearchParams({ hours: hours.toString() })
    if (severity) params.append('severity', severity)
    if (eventType) params.append('event_type', eventType)
    
    return this.get<{ events: SecurityEvent[]; total_count: number }>(
      `/security/events?${params.toString()}`
    )
  }

  async getSecurityIncidents(
    hours: number = 24,
    status?: string
  ): Promise<{ incidents: SecurityIncident[]; total_count: number }> {
    const params = new URLSearchParams({ hours: hours.toString() })
    if (status) params.append('status', status)
    
    return this.get<{ incidents: SecurityIncident[]; total_count: number }>(
      `/security/incidents?${params.toString()}`
    )
  }

  async getComplianceSummary(): Promise<ComplianceSummary> {
    return this.get<ComplianceSummary>('/security/compliance/summary')
  }

  // Server-Sent Events for live security events
  createSecurityEventStream(): EventSource {
    return this.createEventSource('/security/events/stream')
  }

  // Request Tracing
  async getTraces(limit: number = 50): Promise<{ traces: TraceInfo[]; total_count: number }> {
    return this.get<{ traces: TraceInfo[]; total_count: number }>(`/traces?limit=${limit}`)
  }

  async getTraceDetails(correlationId: string): Promise<any> {
    return this.get<any>(`/traces/${correlationId}`)
  }

  // Server-Sent Events for live traces
  createTraceStream(): EventSource {
    return this.createEventSource('/traces/stream/live')
  }

  // Analytics
  async getAnalyticsDashboard(hours: number = 24): Promise<AnalyticsDashboard> {
    return this.get<AnalyticsDashboard>(`/analytics/dashboard?hours=${hours}`)
  }

  async getMetricData(
    metricName: string,
    hours: number = 24,
    resolution: number = 5
  ): Promise<any> {
    return this.get<any>(
      `/analytics/metrics/${metricName}?hours=${hours}&resolution_minutes=${resolution}`
    )
  }

  // Alerts
  async getActiveAlerts(severity?: string): Promise<any> {
    const params = severity ? `?severity=${severity}` : ''
    return this.get<any>(`/alerts${params}`)
  }

  async getAlertSummary(): Promise<any> {
    return this.get<any>('/alerts/summary')
  }

  // Server-Sent Events for live alerts
  createAlertStream(): EventSource {
    return this.createEventSource('/alerts/stream/live')
  }

  // Acknowledge alert
  async acknowledgeAlert(alertId: string, acknowledgedBy: string, notes?: string): Promise<any> {
    return this.post<any>(`/alerts/${alertId}/acknowledge`, {
      acknowledged_by: acknowledgedBy,
      notes,
    })
  }

  // Resolve alert
  async resolveAlert(alertId: string, resolvedBy: string, resolutionNotes: string): Promise<any> {
    return this.post<any>(`/alerts/${alertId}/resolve`, {
      resolved_by: resolvedBy,
      resolution_notes: resolutionNotes,
    })
  }
}

export const registryAPI = new RegistryAPI()