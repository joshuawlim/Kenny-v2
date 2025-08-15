// Agent activity indicator component
import React from 'react'
import { Bot, Activity, CheckCircle, AlertCircle, Clock } from 'lucide-react'
import clsx from 'clsx'

interface AgentStatus {
  agentId: string
  displayName: string
  status: 'idle' | 'thinking' | 'working' | 'responding' | 'completed' | 'error'
  progress?: number
  message?: string
}

interface AgentIndicatorProps {
  agents: AgentStatus[]
  className?: string
}

export const AgentIndicator: React.FC<AgentIndicatorProps> = ({
  agents,
  className = '',
}) => {
  if (agents.length === 0) {
    return null
  }

  const getStatusIcon = (status: AgentStatus['status']) => {
    switch (status) {
      case 'thinking':
        return <Clock className="w-4 h-4 text-kenny-warning animate-pulse" />
      case 'working':
        return <Activity className="w-4 h-4 text-kenny-primary animate-bounce" />
      case 'responding':
        return <Bot className="w-4 h-4 text-kenny-info animate-pulse" />
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-kenny-success" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-kenny-error" />
      default:
        return <Bot className="w-4 h-4 text-kenny-gray-400" />
    }
  }

  const getStatusColor = (status: AgentStatus['status']) => {
    switch (status) {
      case 'thinking':
        return 'border-kenny-warning bg-kenny-warning/5'
      case 'working':
        return 'border-kenny-primary bg-kenny-primary/5'
      case 'responding':
        return 'border-kenny-info bg-kenny-info/5'
      case 'completed':
        return 'border-kenny-success bg-kenny-success/5'
      case 'error':
        return 'border-kenny-error bg-kenny-error/5'
      default:
        return 'border-kenny-gray-200 bg-kenny-gray-50'
    }
  }

  const getStatusLabel = (status: AgentStatus['status']) => {
    switch (status) {
      case 'thinking':
        return 'Analyzing...'
      case 'working':
        return 'Processing...'
      case 'responding':
        return 'Responding...'
      case 'completed':
        return 'Complete'
      case 'error':
        return 'Error'
      default:
        return 'Ready'
    }
  }

  const activeAgents = agents.filter(agent => agent.status !== 'idle')
  
  if (activeAgents.length === 0) {
    return null
  }

  return (
    <div className={`glass-card rounded-xl p-4 ${className}`}>
      <div className="flex items-center space-x-2 mb-3">
        <Activity className="w-5 h-5 text-kenny-primary" />
        <h4 className="font-medium text-kenny-gray-800">
          Agent Activity
        </h4>
      </div>

      <div className="space-y-3">
        {activeAgents.map((agent) => (
          <div
            key={agent.agentId}
            className={clsx(
              'flex items-center justify-between p-3 rounded-lg border',
              getStatusColor(agent.status),
              'transition-all duration-300'
            )}
          >
            <div className="flex items-center space-x-3">
              {getStatusIcon(agent.status)}
              <div className="min-w-0 flex-1">
                <div className="font-medium text-kenny-gray-800 truncate">
                  {agent.displayName}
                </div>
                <div className="text-sm text-kenny-gray-600">
                  {agent.message || getStatusLabel(agent.status)}
                </div>
              </div>
            </div>

            {/* Progress indicator */}
            {agent.progress !== undefined && agent.status === 'working' && (
              <div className="flex items-center space-x-2">
                <div className="w-16 h-1.5 bg-kenny-gray-200 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-kenny-primary transition-all duration-300"
                    style={{ width: `${agent.progress}%` }}
                  />
                </div>
                <span className="text-xs text-kenny-gray-600 font-medium">
                  {agent.progress}%
                </span>
              </div>
            )}

            {/* Pulse animation for active states */}
            {(['thinking', 'working', 'responding'].includes(agent.status)) && (
              <div className="absolute inset-0 rounded-lg border-2 border-current opacity-25 animate-ping pointer-events-none" />
            )}
          </div>
        ))}
      </div>

      {/* Overall Status */}
      <div className="mt-4 pt-3 border-t border-kenny-gray-200">
        <div className="flex items-center justify-between text-sm">
          <span className="text-kenny-gray-600">
            {activeAgents.filter(a => a.status === 'completed').length} of {activeAgents.length} completed
          </span>
          
          {activeAgents.some(a => a.status === 'error') && (
            <span className="text-kenny-error">
              Some agents encountered issues
            </span>
          )}
        </div>
      </div>
    </div>
  )
}