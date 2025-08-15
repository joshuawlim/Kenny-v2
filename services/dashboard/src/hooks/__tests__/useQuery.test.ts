// Test for useQuery hook
import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { useQuery } from '../useQuery'
import { gatewayAPI } from '@/services'

// Mock the API
jest.mock('@/services', () => ({
  gatewayAPI: {
    query: jest.fn(),
    createQueryWebSocket: jest.fn(),
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

// Mock WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  readyState: WebSocket.OPEN,
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  onopen: null,
  onmessage: null,
  onclose: null,
  onerror: null,
}

describe('useQuery', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Reset WebSocket mock
    Object.assign(mockWebSocket, {
      send: jest.fn(),
      close: jest.fn(),
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null,
    })
    ;(gatewayAPI.createQueryWebSocket as jest.Mock).mockReturnValue(mockWebSocket)
  })

  it('initializes with empty state', () => {
    const { result } = renderHook(() => useQuery(), {
      wrapper: createWrapper(),
    })

    expect(result.current.messages).toEqual([])
    expect(result.current.isStreaming).toBe(false)
    expect(result.current.connectionStatus).toBe('disconnected')
    expect(result.current.isConnected).toBe(false)
  })

  it('adds messages correctly', () => {
    const { result } = renderHook(() => useQuery(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.addMessage({
        type: 'user',
        content: 'Hello',
      })
    })

    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].type).toBe('user')
    expect(result.current.messages[0].content).toBe('Hello')
    expect(result.current.messages[0].id).toBeDefined()
    expect(result.current.messages[0].timestamp).toBeInstanceOf(Date)
  })

  it('updates messages correctly', () => {
    const { result } = renderHook(() => useQuery(), {
      wrapper: createWrapper(),
    })

    let messageId: string

    act(() => {
      messageId = result.current.addMessage({
        type: 'assistant',
        content: 'Thinking...',
        isStreaming: true,
      })
    })

    act(() => {
      result.current.updateMessage(messageId, {
        content: 'Here is your answer',
        isStreaming: false,
      })
    })

    expect(result.current.messages[0].content).toBe('Here is your answer')
    expect(result.current.messages[0].isStreaming).toBe(false)
  })

  it('clears conversation correctly', () => {
    const { result } = renderHook(() => useQuery(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.addMessage({ type: 'user', content: 'Hello' })
      result.current.addMessage({ type: 'assistant', content: 'Hi!' })
    })

    expect(result.current.messages).toHaveLength(2)

    act(() => {
      result.current.clearConversation()
    })

    expect(result.current.messages).toHaveLength(0)
  })

  it('sends direct queries correctly', async () => {
    const mockResponse = {
      result: {
        intent: 'greeting',
        plan: [],
        execution_path: ['coordinator'],
        results: { message: 'Hello!' },
        errors: [],
        status: 'success',
      },
      execution_path: ['coordinator'],
      duration_ms: 100,
    }

    ;(gatewayAPI.query as jest.Mock).mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useQuery(), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.sendDirectQuery('Hello Kenny')
    })

    // Should have user message and assistant response
    expect(result.current.messages).toHaveLength(2)
    expect(result.current.messages[0].type).toBe('user')
    expect(result.current.messages[0].content).toBe('Hello Kenny')
    expect(result.current.messages[1].type).toBe('assistant')
    expect(result.current.messages[1].metadata?.intent).toBe('greeting')
  })

  it('handles API errors gracefully', async () => {
    ;(gatewayAPI.query as jest.Mock).mockRejectedValue(new Error('API Error'))

    const { result } = renderHook(() => useQuery(), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.sendDirectQuery('Hello Kenny')
    })

    // Should have user message and error response
    expect(result.current.messages).toHaveLength(2)
    expect(result.current.messages[1].content).toContain('Error: API Error')
    expect(result.current.messages[1].metadata?.status).toBe('error')
  })

  it('manages conversation context correctly', () => {
    const { result } = renderHook(() => useQuery(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.addMessage({ type: 'user', content: 'Hello' })
      result.current.addMessage({ type: 'assistant', content: 'Hi!' })
    })

    const context = result.current.getConversationContext()

    expect(context.messages).toHaveLength(2)
    expect(context.sessionId).toBeDefined()
    expect(context.lastActivity).toBeInstanceOf(Date)

    // Test loading context
    act(() => {
      result.current.clearConversation()
    })

    expect(result.current.messages).toHaveLength(0)

    act(() => {
      result.current.loadConversationContext(context)
    })

    expect(result.current.messages).toHaveLength(2)
  })
})