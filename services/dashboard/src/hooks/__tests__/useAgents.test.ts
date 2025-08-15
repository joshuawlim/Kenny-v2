// Test for useAgents hook
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { useAgents, useAgentStatus } from '../useAgents'
import { gatewayAPI } from '@/services'

// Mock the API
jest.mock('@/services', () => ({
  gatewayAPI: {
    getAgents: jest.fn(),
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
    },
  })
  
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('useAgents', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('fetches agents successfully', async () => {
    const mockAgents = [
      {
        agent_id: 'test-agent',
        display_name: 'Test Agent',
        status: 'healthy',
        is_healthy: true,
        capabilities: ['test.capability'],
        last_seen: '2025-01-01T00:00:00Z',
      },
    ]

    ;(gatewayAPI.getAgents as jest.Mock).mockResolvedValue({
      agents: mockAgents,
    })

    const { result } = renderHook(() => useAgents(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(mockAgents)
  })

  it('handles API errors gracefully', async () => {
    ;(gatewayAPI.getAgents as jest.Mock).mockRejectedValue(
      new Error('API Error')
    )

    const { result } = renderHook(() => useAgents(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect(result.current.error).toBeDefined()
  })
})

describe('useAgentStatus', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('calculates agent health metrics correctly', async () => {
    const mockAgents = [
      {
        agent_id: 'agent-1',
        display_name: 'Agent 1',
        status: 'healthy',
        is_healthy: true,
        capabilities: [],
        last_seen: '2025-01-01T00:00:00Z',
      },
      {
        agent_id: 'agent-2',
        display_name: 'Agent 2',
        status: 'unhealthy',
        is_healthy: false,
        capabilities: [],
        last_seen: '2025-01-01T00:00:00Z',
      },
    ]

    ;(gatewayAPI.getAgents as jest.Mock).mockResolvedValue({
      agents: mockAgents,
    })

    const { result } = renderHook(() => useAgentStatus(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.healthyCount).toBe(1)
    expect(result.current.unhealthyCount).toBe(1)
    expect(result.current.totalCount).toBe(2)
    expect(result.current.healthPercentage).toBe(50)
  })
})