// Header component for Kenny v2 Dashboard
import React from 'react'
import { Activity, Shield, Zap, Users } from 'lucide-react'
import { useSystemHealth, useAgentStatus, useSecurityMetrics } from '@/hooks'
import { ConnectionStatus } from './ConnectionStatus'

export const Header: React.FC = () => {
  const { data: healthData } = useSystemHealth()
  const { healthyCount, totalCount } = useAgentStatus()
  const { securityScore, complianceScore } = useSecurityMetrics()

  const systemStatus = healthData?.system_overview?.status || 'unknown'
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-kenny-success'
      case 'warning': return 'text-kenny-warning'
      case 'error': return 'text-kenny-error'
      default: return 'text-kenny-gray-400'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return '🟢'
      case 'warning': return '🟡'
      case 'error': return '🔴'
      default: return '⚪'
    }
  }

  return (
    <header className="glass-card rounded-2xl p-6 mb-6 animate-slide-up">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-kenny-primary rounded-xl flex items-center justify-center">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-kenny-gray-800">
                Kenny v2 Dashboard
              </h1>
              <p className="text-kenny-gray-600">
                Local-first multi-agent system
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className={`text-lg ${getStatusColor(systemStatus)}`}>
              {getStatusIcon(systemStatus)}
            </span>
            <span className={`font-medium ${getStatusColor(systemStatus)}`}>
              {systemStatus.toUpperCase()}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-6">
          {/* Quick Stats */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Users className="w-5 h-5 text-kenny-info" />
              <span className="text-sm font-medium text-kenny-gray-700">
                {healthyCount}/{totalCount} Agents
              </span>
            </div>
            
            <div className="flex items-center space-x-2">
              <Shield className="w-5 h-5 text-kenny-success" />
              <span className="text-sm font-medium text-kenny-gray-700">
                {securityScore.toFixed(0)}% Security
              </span>
            </div>
            
            <div className="flex items-center space-x-2">
              <Zap className="w-5 h-5 text-kenny-warning" />
              <span className="text-sm font-medium text-kenny-gray-700">
                {complianceScore.toFixed(1)}% Compliance
              </span>
            </div>
          </div>

          <ConnectionStatus />
        </div>
      </div>

      {/* Last Updated */}
      <div className="mt-4 pt-4 border-t border-kenny-gray-200">
        <div className="flex items-center justify-between text-sm text-kenny-gray-500">
          <span>
            Last Updated: {healthData?.system_overview?.timestamp 
              ? new Date(healthData.system_overview.timestamp).toLocaleString()
              : 'Loading...'
            }
          </span>
          <span className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-kenny-success rounded-full animate-pulse"></div>
            <span>Live Monitoring Active</span>
          </span>
        </div>
      </div>
    </header>
  )
}