// Custom hooks for query management and streaming
import { useState, useRef, useCallback, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { gatewayAPI, coordinatorAPI } from '@/services'
import type { QueryRequest, QueryResponse, StreamEvent } from '@/types'

export interface ChatMessage {
  id: string
  type: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  agentsUsed?: string[]
  executionPath?: string[]
  isStreaming?: boolean
  metadata?: {
    intent?: string
    plan?: string[]
    duration?: number
    status?: 'success' | 'error' | 'partial'
  }
}

export interface ConversationContext {
  messages: ChatMessage[]
  sessionId: string
  lastActivity: Date
}

export const useQuery = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected')
  const websocketRef = useRef<WebSocket | null>(null)
  const sessionIdRef = useRef<string>(crypto.randomUUID())

  // Direct query mutation (non-streaming)
  const directQueryMutation = useMutation({
    mutationFn: async (request: QueryRequest): Promise<QueryResponse> => {
      return gatewayAPI.query(request)
    },
  })

  // Coordinator query mutation (non-streaming)
  const coordinatorQueryMutation = useMutation({
    mutationFn: async (request: QueryRequest): Promise<QueryResponse> => {
      return coordinatorAPI.processRequest(request)
    },
  })

  // Add a new message to the conversation
  const addMessage = useCallback((message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: crypto.randomUUID(),
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, newMessage])
    return newMessage.id
  }, [])

  // Update an existing message
  const updateMessage = useCallback((id: string, updates: Partial<ChatMessage>) => {
    setMessages(prev => prev.map(msg => 
      msg.id === id ? { ...msg, ...updates } : msg
    ))
  }, [])

  // Clear conversation history
  const clearConversation = useCallback(() => {
    setMessages([])
    sessionIdRef.current = crypto.randomUUID()
  }, [])

  // Connect to WebSocket for streaming
  const connectWebSocket = useCallback(() => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      setConnectionStatus('connecting')
      websocketRef.current = gatewayAPI.createQueryWebSocket()
      
      websocketRef.current.onopen = () => {
        setConnectionStatus('connected')
        console.log('WebSocket connected for query streaming')
      }

      websocketRef.current.onmessage = (event) => {
        try {
          const streamEvent: StreamEvent = JSON.parse(event.data)
          handleStreamEvent(streamEvent)
        } catch (error) {
          console.error('Failed to parse stream event:', error)
        }
      }

      websocketRef.current.onclose = () => {
        setConnectionStatus('disconnected')
        setIsStreaming(false)
        setStreamingMessageId(null)
        console.log('WebSocket disconnected')
      }

      websocketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus('disconnected')
        setIsStreaming(false)
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      setConnectionStatus('disconnected')
    }
  }, [])

  // Handle incoming stream events
  const handleStreamEvent = useCallback((event: StreamEvent) => {
    switch (event.type) {
      case 'status':
        if (streamingMessageId) {
          updateMessage(streamingMessageId, {
            content: event.message || 'Processing...',
            isStreaming: true,
          })
        }
        break

      case 'progress':
        if (streamingMessageId && event.data) {
          const progressContent = `**${event.data.agent || 'System'}**: ${event.data.message || event.message}`
          updateMessage(streamingMessageId, {
            content: progressContent,
            isStreaming: true,
            agentsUsed: event.data.agent ? [event.data.agent] : undefined,
          })
        }
        break

      case 'result':
        if (streamingMessageId && event.data) {
          const resultContent = formatQueryResult(event.data)
          updateMessage(streamingMessageId, {
            content: resultContent,
            isStreaming: false,
            metadata: {
              intent: event.data.intent,
              plan: event.data.plan,
              duration: event.data.duration_ms,
              status: 'success',
            },
            agentsUsed: event.data.execution_path || [],
            executionPath: event.data.execution_path || [],
          })
        }
        setIsStreaming(false)
        setStreamingMessageId(null)
        break

      case 'error':
        if (streamingMessageId) {
          updateMessage(streamingMessageId, {
            content: `❌ Error: ${event.message}`,
            isStreaming: false,
            metadata: { status: 'error' },
          })
        }
        setIsStreaming(false)
        setStreamingMessageId(null)
        break

      case 'complete':
        setIsStreaming(false)
        setStreamingMessageId(null)
        break
    }
  }, [streamingMessageId, updateMessage])

  // Format query result for display
  const formatQueryResult = (result: any): string => {
    if (typeof result === 'string') return result
    
    if (result.results && typeof result.results === 'object') {
      // Format multi-agent results
      const formattedResults = Object.entries(result.results)
        .map(([agent, data]: [string, any]) => {
          if (typeof data === 'object' && data.response) {
            return `**${agent}**: ${data.response}`
          }
          return `**${agent}**: ${JSON.stringify(data, null, 2)}`
        })
        .join('\n\n')
      
      return formattedResults
    }

    return JSON.stringify(result, null, 2)
  }

  // Send a streaming query
  const sendStreamingQuery = useCallback(async (query: string, context: Record<string, any> = {}) => {
    if (!query.trim()) return

    // Add user message
    addMessage({
      type: 'user',
      content: query,
    })

    // Connect WebSocket if needed
    if (websocketRef.current?.readyState !== WebSocket.OPEN) {
      connectWebSocket()
      // Wait a bit for connection
      await new Promise(resolve => setTimeout(resolve, 500))
    }

    if (websocketRef.current?.readyState === WebSocket.OPEN) {
      // Add placeholder assistant message
      const messageId = addMessage({
        type: 'assistant',
        content: 'Thinking...',
        isStreaming: true,
      })

      setIsStreaming(true)
      setStreamingMessageId(messageId)

      // Send query via WebSocket
      const queryRequest: QueryRequest = {
        query,
        context: {
          ...context,
          session_id: sessionIdRef.current,
          conversation_history: messages.slice(-10), // Last 10 messages for context
        }
      }

      websocketRef.current.send(JSON.stringify(queryRequest))
    } else {
      // Fallback to direct API call
      sendDirectQuery(query, context)
    }
  }, [addMessage, connectWebSocket, messages])

  // Send a direct (non-streaming) query
  const sendDirectQuery = useCallback(async (query: string, context: Record<string, any> = {}) => {
    if (!query.trim()) return

    // Add user message
    addMessage({
      type: 'user',
      content: query,
    })

    // Add loading message
    const messageId = addMessage({
      type: 'assistant',
      content: 'Processing your request...',
      isStreaming: true,
    })

    try {
      const queryRequest: QueryRequest = {
        query,
        context: {
          ...context,
          session_id: sessionIdRef.current,
        }
      }

      const response = await gatewayAPI.query(queryRequest)
      
      // Format the response
      const content = formatQueryResult(response.result)
      
      updateMessage(messageId, {
        content,
        isStreaming: false,
        metadata: {
          intent: response.result.intent,
          plan: response.result.plan,
          duration: response.duration_ms,
          status: response.result.status,
        },
        agentsUsed: response.execution_path,
        executionPath: response.execution_path,
      })
    } catch (error) {
      updateMessage(messageId, {
        content: `❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        isStreaming: false,
        metadata: { status: 'error' },
      })
    }
  }, [addMessage, updateMessage])

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close()
      }
    }
  }, [])

  // Get conversation context for persistence
  const getConversationContext = useCallback((): ConversationContext => ({
    messages,
    sessionId: sessionIdRef.current,
    lastActivity: new Date(),
  }), [messages])

  // Load conversation context
  const loadConversationContext = useCallback((context: ConversationContext) => {
    setMessages(context.messages)
    sessionIdRef.current = context.sessionId
  }, [])

  return {
    // State
    messages,
    isStreaming,
    connectionStatus,
    isConnected: connectionStatus === 'connected',

    // Actions
    sendQuery: sendStreamingQuery,
    sendDirectQuery,
    addMessage,
    updateMessage,
    clearConversation,
    connectWebSocket,

    // Context management
    getConversationContext,
    loadConversationContext,

    // Mutation states (for direct queries)
    isLoading: directQueryMutation.isPending || coordinatorQueryMutation.isPending,
    error: directQueryMutation.error || coordinatorQueryMutation.error,
  }
}