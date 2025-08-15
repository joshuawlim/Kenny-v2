// Kenny v2 Chat Interface - Real-time conversation with AI agents
import React, { useEffect, useRef } from 'react'
import { ChatMessage, ChatInput } from '@/components/chat'
import { useQuery } from '@/hooks/useQuery'
import { Wifi, WifiOff, Activity } from 'lucide-react'
import clsx from 'clsx'

export const ChatPage: React.FC = () => {
  const {
    messages,
    isStreaming,
    connectionStatus,
    isConnected,
    sendQuery,
    sendDirectQuery,
    clearConversation,
    connectWebSocket,
    error,
  } = useQuery()

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-connect WebSocket on component mount
  useEffect(() => {
    connectWebSocket()
  }, [connectWebSocket])

  const handleSendMessage = (message: string) => {
    if (isConnected) {
      sendQuery(message)
    } else {
      sendDirectQuery(message)
    }
  }

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'text-kenny-success'
      case 'connecting': return 'text-kenny-warning'
      case 'disconnected': return 'text-kenny-error'
      default: return 'text-kenny-gray-500'
    }
  }

  const getConnectionIcon = () => {
    if (connectionStatus === 'connected') {
      return <Wifi className="w-4 h-4" />
    } else if (connectionStatus === 'connecting') {
      return <Activity className="w-4 h-4 animate-pulse" />
    } else {
      return <WifiOff className="w-4 h-4" />
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 pb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold text-white mb-2">
              Kenny Chat Interface
            </h1>
            <p className="text-kenny-gray-300">
              Conversational AI powered by Qwen 8b with multi-agent orchestration
            </p>
          </div>
          
          {/* Connection Status & Controls */}
          <div className="flex items-center space-x-4">
            {/* Connection Status */}
            <div className={clsx(
              'flex items-center space-x-2 px-3 py-2 rounded-lg',
              'bg-kenny-gray-900/50 backdrop-blur-sm border',
              isConnected 
                ? 'border-kenny-success/30 bg-kenny-success/10' 
                : 'border-kenny-gray-600'
            )}>
              <div className={getConnectionStatusColor()}>
                {getConnectionIcon()}
              </div>
              <span className={clsx('text-sm font-medium', getConnectionStatusColor())}>
                {connectionStatus === 'connected' && 'Live Chat'}
                {connectionStatus === 'connecting' && 'Connecting...'}
                {connectionStatus === 'disconnected' && 'Offline Mode'}
              </span>
            </div>

            {/* Clear Chat Button */}
            {messages.length > 0 && (
              <button
                onClick={clearConversation}
                className="px-3 py-2 text-sm bg-kenny-gray-700 text-kenny-gray-300 rounded-lg hover:bg-kenny-gray-600 transition-colors"
              >
                Clear Chat
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Chat Messages Area */}
      <div className="flex-1 min-h-0 flex flex-col">
        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-1">
          {messages.length === 0 ? (
            /* Welcome Message */
            <div className="h-full flex flex-col items-center justify-center text-center py-12">
              <div className="w-16 h-16 bg-kenny-primary/20 rounded-full flex items-center justify-center mb-4">
                <span className="text-3xl">🤖</span>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Welcome to Kenny v2
              </h3>
              <p className="text-kenny-gray-400 mb-8 max-w-md">
                I'm your personal AI assistant powered by Qwen 8b. I can help you with emails, 
                calendar, contacts, documents, and much more through my specialized agents.
              </p>
              <div className="grid grid-cols-2 gap-3 max-w-md">
                <button
                  onClick={() => handleSendMessage('What can you help me with?')}
                  className="p-3 text-left text-sm bg-kenny-primary/10 border border-kenny-primary/20 rounded-lg hover:bg-kenny-primary/20 transition-colors"
                >
                  <div className="font-medium text-kenny-primary">What can you help with?</div>
                </button>
                <button
                  onClick={() => handleSendMessage('Check my recent emails')}
                  className="p-3 text-left text-sm bg-kenny-primary/10 border border-kenny-primary/20 rounded-lg hover:bg-kenny-primary/20 transition-colors"
                >
                  <div className="font-medium text-kenny-primary">Check my emails</div>
                </button>
                <button
                  onClick={() => handleSendMessage('Show my calendar for today')}
                  className="p-3 text-left text-sm bg-kenny-primary/10 border border-kenny-primary/20 rounded-lg hover:bg-kenny-primary/20 transition-colors"
                >
                  <div className="font-medium text-kenny-primary">Today's calendar</div>
                </button>
                <button
                  onClick={() => handleSendMessage('How are my agents doing?')}
                  className="p-3 text-left text-sm bg-kenny-primary/10 border border-kenny-primary/20 rounded-lg hover:bg-kenny-primary/20 transition-colors"
                >
                  <div className="font-medium text-kenny-primary">System status</div>
                </button>
              </div>
            </div>
          ) : (
            /* Chat Messages */
            <div className="space-y-1">
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  showTimestamp={true}
                  showAgents={true}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Error Banner */}
        {error && (
          <div className="flex-shrink-0 p-3 mb-4 bg-kenny-error/10 border border-kenny-error/20 rounded-lg">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-kenny-error rounded-full"></div>
              <span className="text-sm text-kenny-error font-medium">
                Connection Error
              </span>
              <span className="text-xs text-kenny-gray-400">
                {error instanceof Error ? error.message : 'Unknown error occurred'}
              </span>
            </div>
          </div>
        )}

        {/* Chat Input */}
        <div className="flex-shrink-0">
          <ChatInput
            onSendMessage={handleSendMessage}
            onSendStreamingMessage={sendQuery}
            isLoading={false}
            isStreaming={isStreaming}
            isConnected={isConnected}
            onConnect={connectWebSocket}
            placeholder="Ask Kenny anything... (or use quick actions above)"
          />
        </div>
      </div>
    </div>
  )
}

export default ChatPage