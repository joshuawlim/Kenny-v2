// API Response Types for Kenny v2 Dashboard

export interface SystemHealth {
  status: 'healthy' | 'warning' | 'error' | 'unknown'
  total_agents: number
  healthy_agents: number
  unhealthy_agents: number
  total_capabilities: number
  timestamp: string
}

export interface AgentInfo {
  agent_id: string
  display_name: string
  status: 'healthy' | 'unhealthy' | 'unknown'
  is_healthy: boolean
  capabilities: string[]
  last_seen: string
  url?: string
  port?: number
}

export interface CapabilityInfo {
  verb: string
  agent_id: string
  agent_name: string
  description?: string
  safety_annotations?: string[]
}

export interface HealthDashboard {
  system_overview: {
    status: string
    total_agents: number
    healthy_agents: number
    unhealthy_agents: number
    total_capabilities: number
    timestamp: string
  }
  performance_overview: {
    average_response_time_ms: number
    average_success_rate_percent: number
    total_request_count: number
    total_error_count: number
  }
  agent_details: Record<string, AgentDetails>
  streaming_info?: {
    last_update: number
    update_interval_seconds: number
    is_live: boolean
  }
}

export interface AgentDetails {
  basic_info: {
    agent_id: string
    display_name: string
    status: string
    is_healthy: boolean
    last_seen: string
    capabilities: string[]
  }
  health_summary: {
    current_status: string
    last_health_check: string
    consecutive_failures: number
    total_requests: number
    successful_requests: number
    failed_requests: number
    average_response_time_ms: number
  }
  performance_summary?: {
    current_metrics: Record<string, number>
    sla_compliance: {
      overall_compliant: boolean
      response_time_compliant: boolean
      success_rate_compliant: boolean
    }
    trend_analysis: {
      trend: 'improving' | 'stable' | 'degrading'
      change_percent: number
    }
  }
}

export interface SecurityEvent {
  event_id: string
  timestamp: string
  event_type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  source_service: string
  title: string
  description: string
  metadata?: Record<string, any>
}

export interface SecurityIncident {
  incident_id: string
  created_at: string
  updated_at: string
  status: 'open' | 'investigating' | 'resolved' | 'false_positive'
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  description: string
  event_ids: string[]
  assigned_to?: string
  resolution_notes?: string
}

export interface ComplianceSummary {
  compliance_score: number
  compliance_status: string
  event_summary: {
    total_events_24h: number
    critical_count: number
    high_count: number
    medium_count: number
    low_count: number
  }
  egress_rules_count: number
  egress_rules_enabled: number
  assessment_timestamp: string
}

export interface QueryRequest {
  query: string
  context?: Record<string, any>
}

export interface QueryResponse {
  request_id: string
  result: {
    intent: string
    plan: string[]
    execution_path: string[]
    results: Record<string, any>
    errors: string[]
    status: string
  }
  execution_path: string[]
  duration_ms: number
}

export interface StreamEvent {
  type: 'status' | 'progress' | 'result' | 'error' | 'complete'
  message?: string
  data?: any
  timestamp: number
}

export interface TraceInfo {
  correlation_id: string
  service_name: string
  operation_name: string
  start_time: string
  duration_ms: number
  status: 'success' | 'error'
  span_count: number
}

export interface AnalyticsDashboard {
  time_period_hours: number
  performance_overview: {
    average_response_time_ms: number
    p95_response_time_ms: number
    success_rate_percent: number
    total_requests: number
    error_rate_percent: number
  }
  capacity_analysis: {
    current_load_percent: number
    peak_load_percent: number
    capacity_remaining_percent: number
    projected_capacity_days: number
  }
  trending_metrics: Array<{
    metric_name: string
    current_value: number
    trend: 'up' | 'down' | 'stable'
    change_percent: number
  }>
  timestamp: string
}