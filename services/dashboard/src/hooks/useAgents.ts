// Custom hooks for agent management
import { useQuery } from '@tanstack/react-query'
import { gatewayAPI } from '@/services'
import type { AgentInfo, CapabilityInfo } from '@/types'

export const useAgents = () => {
  return useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const response = await gatewayAPI.getAgents()
      return response.agents
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 3,
  })
}

export const useCapabilities = () => {
  return useQuery({
    queryKey: ['capabilities'],
    queryFn: async () => {
      const response = await gatewayAPI.getCapabilities()
      return response.capabilities
    },
    refetchInterval: 60000, // Capabilities change less frequently
    retry: 3,
  })
}

export const useAgentCapabilities = (agentId: string | null) => {
  return useQuery({
    queryKey: ['agent-capabilities', agentId],
    queryFn: () => agentId ? gatewayAPI.getAgentCapabilities(agentId) : Promise.resolve([]),
    enabled: !!agentId,
    retry: 3,
  })
}

// Transform agents data for UI consumption
export const useAgentStatus = () => {
  const { data: agents, ...rest } = useAgents()
  
  const agentsByStatus = agents?.reduce((acc, agent) => {
    const status = agent.is_healthy ? 'healthy' : 'unhealthy'
    acc[status] = (acc[status] || 0) + 1
    return acc
  }, {} as Record<string, number>) || {}

  const healthyCount = agentsByStatus.healthy || 0
  const unhealthyCount = agentsByStatus.unhealthy || 0
  const totalCount = healthyCount + unhealthyCount

  return {
    agents,
    healthyCount,
    unhealthyCount,
    totalCount,
    healthPercentage: totalCount > 0 ? (healthyCount / totalCount) * 100 : 0,
    ...rest,
  }
}

// Group capabilities by agent for easier display
export const useCapabilitiesByAgent = () => {
  const { data: capabilities, ...rest } = useCapabilities()
  
  const capabilitiesByAgent = capabilities?.reduce((acc, capability) => {
    if (!acc[capability.agent_id]) {
      acc[capability.agent_id] = []
    }
    acc[capability.agent_id].push(capability)
    return acc
  }, {} as Record<string, CapabilityInfo[]>) || {}

  return {
    capabilitiesByAgent,
    totalCapabilities: capabilities?.length || 0,
    ...rest,
  }
}