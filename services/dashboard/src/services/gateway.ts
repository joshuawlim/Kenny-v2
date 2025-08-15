// Gateway API client for Kenny v2 Dashboard
import { ApiClient } from './api'
import type {
  SystemHealth,
  AgentInfo,
  CapabilityInfo,
  QueryRequest,
  QueryResponse,
} from '@/types'

export class GatewayAPI extends ApiClient {
  constructor() {
    super('/api') // Proxied through Vite dev server to localhost:9000
  }

  // Health & Discovery
  async getHealth(): Promise<SystemHealth> {
    return this.get<SystemHealth>('/health')
  }

  async getAgents(): Promise<{ agents: AgentInfo[] }> {
    return this.get<{ agents: AgentInfo[] }>('/agents')
  }

  async getCapabilities(): Promise<{ capabilities: CapabilityInfo[] }> {
    return this.get<{ capabilities: CapabilityInfo[] }>('/capabilities')
  }

  async getAgentCapabilities(agentId: string): Promise<string[]> {
    return this.get<string[]>(`/agent/${agentId}/capabilities`)
  }

  // Query Interface
  async query(request: QueryRequest): Promise<QueryResponse> {
    return this.post<QueryResponse>('/query', request)
  }

  // Direct Agent Calls
  async callAgent(
    agentId: string,
    capability: string,
    parameters: any
  ): Promise<any> {
    return this.post<any>(`/agent/${agentId}/${capability}`, { parameters })
  }

  // WebSocket for streaming queries
  createQueryWebSocket(): WebSocket {
    return this.createWebSocket('/stream')
  }
}

export const gatewayAPI = new GatewayAPI()