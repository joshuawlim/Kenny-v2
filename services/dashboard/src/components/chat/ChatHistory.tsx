// Chat history component with message management
import React, { useEffect, useRef } from 'react'
import { RotateCcw, Download, Trash2 } from 'lucide-react'
import { ChatMessage } from './ChatMessage'
import type { ChatMessage as ChatMessageType } from '@/hooks/useQuery'

interface ChatHistoryProps {
  messages: ChatMessageType[]
  isStreaming: boolean
  onClearHistory: () => void
  className?: string
}

export const ChatHistory: React.FC<ChatHistoryProps> = ({
  messages,
  isStreaming,
  onClearHistory,
  className = '',
}) => {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ 
        behavior: isStreaming ? 'smooth' : 'auto',
        block: 'end'
      })
    }
  }, [messages, isStreaming])

  const handleExportHistory = () => {
    const exportData = {
      timestamp: new Date().toISOString(),
      messages: messages.map(msg => ({
        type: msg.type,
        content: msg.content,
        timestamp: msg.timestamp.toISOString(),
        agentsUsed: msg.agentsUsed,
        metadata: msg.metadata,
      })),
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    })
    
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `kenny-conversation-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleClearHistory = () => {
    if (window.confirm('Are you sure you want to clear the conversation history? This cannot be undone.')) {
      onClearHistory()
    }
  }

  if (messages.length === 0) {
    return (
      <div className={`flex-1 flex items-center justify-center ${className}`}>
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-kenny-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <RotateCcw className="w-8 h-8 text-kenny-primary" />
          </div>
          <h3 className="text-xl font-semibold text-kenny-gray-800 mb-2">
            Start a conversation with Kenny
          </h3>
          <p className="text-kenny-gray-600 mb-6">
            Ask questions about your emails, calendar, contacts, or request help with any task. 
            Kenny can coordinate multiple agents to provide comprehensive assistance.
          </p>
          <div className="space-y-2 text-sm text-kenny-gray-500">
            <div>💬 Natural language queries</div>
            <div>🔄 Real-time streaming responses</div>
            <div>🤖 Multi-agent coordination</div>
            <div>🔒 Local-first privacy</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Chat Controls */}
      <div className="flex items-center justify-between p-4 border-b border-kenny-gray-200">
        <div className="text-sm text-kenny-gray-600">
          {messages.length} message{messages.length !== 1 ? 's' : ''}
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={handleExportHistory}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm text-kenny-gray-600 hover:text-kenny-primary transition-colors"
            disabled={messages.length === 0}
          >
            <Download className="w-4 h-4" />
            <span>Export</span>
          </button>
          
          <button
            onClick={handleClearHistory}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm text-kenny-error hover:text-kenny-error/80 transition-colors"
            disabled={messages.length === 0 || isStreaming}
          >
            <Trash2 className="w-4 h-4" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 chat-scroll"
      >
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            showTimestamp={true}
            showAgents={true}
          />
        ))}
        
        {/* Auto-scroll anchor */}
        <div ref={bottomRef} className="h-px" />
      </div>

      {/* Streaming Status */}
      {isStreaming && (
        <div className="p-4 border-t border-kenny-gray-200">
          <div className="flex items-center space-x-2 text-sm text-kenny-primary">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-kenny-primary rounded-full animate-pulse"></div>
              <div className="w-2 h-2 bg-kenny-primary rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-2 h-2 bg-kenny-primary rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
            </div>
            <span>Kenny is working on your request...</span>
          </div>
        </div>
      )}
    </div>
  )
}