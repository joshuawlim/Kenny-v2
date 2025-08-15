export * from './api'

export interface ConnectionStatus {
  isConnected: boolean
  reconnectAttempts: number
  lastConnected?: Date
  lastError?: string
}

export interface DashboardTab {
  id: string
  label: string
  icon: string
  path: string
}

export interface NotificationItem {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  timestamp: Date
  read: boolean
  actions?: Array<{
    label: string
    action: () => void
  }>
}

export interface ChartDataPoint {
  timestamp: string
  value: number
  label?: string
}

export interface MetricTrend {
  current: number
  previous: number
  change: number
  changePercent: number
  trend: 'up' | 'down' | 'stable'
}

export interface AgentStatus {
  id: string
  name: string
  status: 'healthy' | 'warning' | 'error' | 'unknown'
  responseTime: number
  successRate: number
  lastSeen: Date
  capabilities: string[]
  isOnline: boolean
}

export interface QueryHistory {
  id: string
  query: string
  timestamp: Date
  duration: number
  status: 'success' | 'error' | 'partial'
  agentsUsed: string[]
  results?: any
}

export interface AlertRule {
  id: string
  name: string
  condition: string
  threshold: number
  severity: 'low' | 'medium' | 'high' | 'critical'
  enabled: boolean
  lastTriggered?: Date
}