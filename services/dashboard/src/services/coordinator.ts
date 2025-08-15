// Coordinator API client for Kenny v2 Dashboard
import { ApiClient } from './api'
import type { QueryRequest, QueryResponse, AgentInfo, CapabilityInfo } from '@/types'

export class CoordinatorAPI extends ApiClient {
  constructor() {
    super('/coordinator') // Proxied through Vite dev server to localhost:8002
  }

  // Health Check
  async getHealth(): Promise<{ status: string; service: string; version: string }> {
    return this.get<{ status: string; service: string; version: string }>('/health')
  }

  // Graph Information
  async getGraphInfo(): Promise<any> {
    return this.get<any>('/coordinator/graph')
  }

  // Multi-agent Processing
  async processRequest(request: QueryRequest): Promise<QueryResponse> {
    return this.post<QueryResponse>('/coordinator/process', request)
  }

  // Server-Sent Events for streaming coordinator responses
  createProcessStream(): EventSource {
    return this.createEventSource('/coordinator/process-stream')
  }

  // Agent Discovery (through coordinator)
  async getAvailableAgents(): Promise<{ agents: AgentInfo[]; count: number }> {
    return this.get<{ agents: AgentInfo[]; count: number }>('/agents')
  }

  async getAllCapabilities(): Promise<{ capabilities: CapabilityInfo[]; count: number }> {
    return this.get<{ capabilities: CapabilityInfo[]; count: number }>('/capabilities')
  }

  // Policy Management
  async getPolicyRules(): Promise<{ rules: any[]; total_count: number }> {
    return this.get<{ rules: any[]; total_count: number }>('/policy/rules')
  }

  async evaluatePolicy(context: any): Promise<any> {
    return this.post<any>('/policy/evaluate', context)
  }

  async addPolicyRule(rule: {
    name: string
    action: string
    conditions: any
    priority: number
  }): Promise<any> {
    return this.post<any>('/policy/rules', rule)
  }
}

export const coordinatorAPI = new CoordinatorAPI()