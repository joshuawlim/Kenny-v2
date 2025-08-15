// Multi-agent query interface with real-time chat
import React, { useState, useEffect } from 'react'
import { MessageSquare, Wifi, WifiOff, Settings } from 'lucide-react'
import { ChatHistory, ChatInput, AgentIndicator } from '@/components/chat'
import { useQuery } from '@/hooks'
import { useAgents } from '@/hooks'

export const QueryPage: React.FC = () => {
  const {
    messages,
    isStreaming,
    connectionStatus,
    isConnected,
    sendQuery,
    sendDirectQuery,
    clearConversation,
    connectWebSocket,
    isLoading,
    error,
  } = useQuery()

  const { data: agentsData } = useAgents()
  const [showSettings, setShowSettings] = useState(false)

  // Auto-connect WebSocket on mount
  useEffect(() => {
    connectWebSocket()
  }, [connectWebSocket])

  // Mock agent activity for demonstration
  // In a real implementation, this would come from the query hook or separate agent monitoring
  const [agentActivity, setAgentActivity] = useState<Array<{
    agentId: string
    displayName: string
    status: 'idle' | 'thinking' | 'working' | 'responding' | 'completed' | 'error'
    progress?: number
    message?: string
  }>>([])

  // Simulate agent activity based on streaming status
  useEffect(() => {
    if (isStreaming) {
      // Find the latest message to get agent info
      const latestMessage = messages[messages.length - 1]
      if (latestMessage?.agentsUsed) {
        const activeAgents = latestMessage.agentsUsed.map(agentId => ({
          agentId,
          displayName: agentsData?.find(a => a.agent_id === agentId)?.display_name || agentId,
          status: 'working' as const,
          progress: Math.random() * 100,
          message: 'Processing your request...',
        }))
        setAgentActivity(activeAgents)
      } else {
        // Default activity
        setAgentActivity([
          {
            agentId: 'coordinator',
            displayName: 'Coordinator',
            status: 'thinking',
            message: 'Analyzing your request...',
          }
        ])
      }
    } else {
      setAgentActivity([])
    }
  }, [isStreaming, messages, agentsData])

  const handleSendMessage = (message: string) => {
    if (isConnected) {
      sendQuery(message)
    } else {
      sendDirectQuery(message)
    }
  }

  return (
    <div className="h-[calc(100vh-200px)] flex flex-col space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <MessageSquare className="w-8 h-8 text-kenny-primary" />
          <div>
            <h1 className="text-3xl font-bold text-kenny-gray-800">
              Chat with Kenny
            </h1>
            <p className="text-kenny-gray-600">
              Multi-agent personal assistant with real-time streaming
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Connection Status */}
          <div className="flex items-center space-x-2">
            {isConnected ? (
              <Wifi className="w-5 h-5 text-kenny-success" />
            ) : (
              <WifiOff className="w-5 h-5 text-kenny-warning" />
            )}
            <span className={`text-sm font-medium ${
              isConnected ? 'text-kenny-success' : 'text-kenny-warning'
            }`}>
              {connectionStatus === 'connecting' ? 'Connecting...' :
               isConnected ? 'Real-time' : 'Direct Mode'}
            </span>
          </div>

          {/* Settings */}
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 text-kenny-gray-400 hover:text-kenny-primary transition-colors"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-kenny-error/10 border border-kenny-error/20 rounded-lg">
          <div className="text-kenny-error font-medium">Error</div>
          <div className="text-sm text-kenny-error/80">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </div>
        </div>
      )}

      {/* Main Chat Interface */}
      <div className="flex-1 flex space-x-6 min-h-0">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col glass-card rounded-2xl min-h-0">
          <ChatHistory
            messages={messages}
            isStreaming={isStreaming}
            onClearHistory={clearConversation}
            className="flex-1 min-h-0"
          />
        </div>

        {/* Sidebar */}
        <div className="w-80 space-y-4">
          {/* Agent Activity */}
          <AgentIndicator agents={agentActivity} />

          {/* System Stats */}
          <div className="glass-card rounded-xl p-4">
            <h4 className="font-medium text-kenny-gray-800 mb-3">
              System Status
            </h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-kenny-gray-600">Available Agents</span>
                <span className="font-medium text-kenny-gray-800">
                  {agentsData?.filter(a => a.is_healthy).length || 0}/{agentsData?.length || 0}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-kenny-gray-600">Connection</span>
                <span className={`font-medium ${isConnected ? 'text-kenny-success' : 'text-kenny-warning'}`}>
                  {isConnected ? 'WebSocket' : 'HTTP'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-kenny-gray-600">Messages</span>
                <span className="font-medium text-kenny-gray-800">
                  {messages.length}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Tips */}
          <div className="glass-card rounded-xl p-4">
            <h4 className="font-medium text-kenny-gray-800 mb-3">
              💡 Tips
            </h4>
            <div className="space-y-2 text-sm text-kenny-gray-600">
              <div>• Ask about emails, calendar, or contacts</div>
              <div>• Request help with planning tasks</div>
              <div>• Use natural language - be conversational</div>
              <div>• Kenny can coordinate multiple agents</div>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Input */}
      <ChatInput
        onSendMessage={handleSendMessage}
        onSendStreamingMessage={sendQuery}
        isLoading={isLoading}
        isStreaming={isStreaming}
        isConnected={isConnected}
        onConnect={connectWebSocket}
        placeholder="Ask Kenny anything... (e.g., 'Show me my recent emails' or 'Help me plan my day')"
      />

      {/* Settings Panel */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="glass-card rounded-2xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-kenny-gray-800">
                Chat Settings
              </h3>
              <button
                onClick={() => setShowSettings(false)}
                className="text-kenny-gray-400 hover:text-kenny-gray-600"
              >
                ×
              </button>
            </div>
            
            <div className="space-y-4 text-sm">
              <div className="flex items-center justify-between">
                <span>Streaming Mode</span>
                <span className={isConnected ? 'text-kenny-success' : 'text-kenny-warning'}>
                  {isConnected ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Auto-scroll</span>
                <span className="text-kenny-success">Enabled</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Message History</span>
                <span className="text-kenny-gray-600">{messages.length} messages</span>
              </div>
            </div>

            <div className="mt-6 flex space-x-3">
              <button
                onClick={clearConversation}
                className="flex-1 py-2 px-4 bg-kenny-error/10 text-kenny-error rounded-lg hover:bg-kenny-error/20 transition-colors"
                disabled={messages.length === 0}
              >
                Clear History
              </button>
              <button
                onClick={connectWebSocket}
                className="flex-1 py-2 px-4 bg-kenny-primary text-white rounded-lg hover:bg-kenny-secondary transition-colors"
              >
                Reconnect
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}