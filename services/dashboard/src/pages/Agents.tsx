// Agents monitoring page
import React from 'react'
import { Users, Activity, Clock, CheckCircle, AlertCircle } from 'lucide-react'
import { useAgents, useCapabilitiesByAgent } from '@/hooks'
import { MetricCard } from '@/components/dashboard'
import { format } from 'date-fns'

export const AgentsPage: React.FC = () => {
  const { data: agents, isLoading, error } = useAgents()
  const { capabilitiesByAgent, totalCapabilities } = useCapabilitiesByAgent()

  const healthyAgents = agents?.filter(agent => agent.is_healthy).length || 0
  const totalAgents = agents?.length || 0

  if (error) {
    return (
      <div className="glass-card rounded-2xl p-8 text-center">
        <AlertCircle className="w-12 h-12 text-kenny-error mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-kenny-gray-800 mb-2">
          Failed to Load Agents
        </h2>
        <p className="text-kenny-gray-600">
          Unable to connect to the agent registry. Please check your connection.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Agent Overview */}
      <div>
        <h1 className="text-3xl font-bold text-kenny-gray-800 mb-6">
          Agent Monitoring
        </h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard
            title="Total Agents"
            value={totalAgents}
            description="Registered agents"
            icon={Users}
            loading={isLoading}
          />
          
          <MetricCard
            title="Healthy Agents"
            value={healthyAgents}
            description={`${totalAgents > 0 ? ((healthyAgents / totalAgents) * 100).toFixed(0) : 0}% operational`}
            icon={CheckCircle}
            status={healthyAgents === totalAgents ? 'success' : 'warning'}
            loading={isLoading}
          />
          
          <MetricCard
            title="Total Capabilities"
            value={totalCapabilities}
            description="Available capabilities"
            icon={Activity}
            loading={isLoading}
          />
          
          <MetricCard
            title="Avg Response"
            value="42ms"
            description="Cross-agent average"
            icon={Clock}
            status="success"
          />
        </div>
      </div>

      {/* Agent Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          // Loading skeletons
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="glass-card rounded-2xl p-6 animate-pulse">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-kenny-gray-200 rounded-lg"></div>
                <div>
                  <div className="h-4 bg-kenny-gray-200 rounded w-24 mb-2"></div>
                  <div className="h-3 bg-kenny-gray-200 rounded w-16"></div>
                </div>
              </div>
              <div className="space-y-2">
                <div className="h-3 bg-kenny-gray-200 rounded"></div>
                <div className="h-3 bg-kenny-gray-200 rounded w-3/4"></div>
              </div>
            </div>
          ))
        ) : (
          agents?.map((agent) => (
            <div key={agent.agent_id} className="glass-card rounded-2xl p-6 hover:shadow-lg transition-shadow">
              {/* Agent Header */}
              <div className="flex items-center space-x-3 mb-4">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  agent.is_healthy ? 'bg-kenny-success/20' : 'bg-kenny-error/20'
                }`}>
                  {agent.is_healthy ? (
                    <CheckCircle className="w-5 h-5 text-kenny-success" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-kenny-error" />
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-kenny-gray-800">
                    {agent.display_name || agent.agent_id}
                  </h3>
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      agent.is_healthy 
                        ? 'bg-kenny-success/10 text-kenny-success' 
                        : 'bg-kenny-error/10 text-kenny-error'
                    }`}>
                      {agent.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Agent Details */}
              <div className="space-y-3">
                <div>
                  <div className="text-sm text-kenny-gray-600 mb-1">Last Seen</div>
                  <div className="text-sm font-medium text-kenny-gray-800">
                    {format(new Date(agent.last_seen), 'MMM dd, HH:mm:ss')}
                  </div>
                </div>

                <div>
                  <div className="text-sm text-kenny-gray-600 mb-2">
                    Capabilities ({agent.capabilities.length})
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {agent.capabilities.slice(0, 3).map((capability) => (
                      <span
                        key={capability}
                        className="inline-flex items-center px-2 py-1 rounded-md text-xs bg-kenny-primary/10 text-kenny-primary"
                      >
                        {capability}
                      </span>
                    ))}
                    {agent.capabilities.length > 3 && (
                      <span className="inline-flex items-center px-2 py-1 rounded-md text-xs bg-kenny-gray-100 text-kenny-gray-600">
                        +{agent.capabilities.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}