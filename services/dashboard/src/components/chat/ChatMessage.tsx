// Chat message component with agent indicators and metadata
import React from 'react'
import { User, Bot, Clock, CheckCircle, AlertCircle, Loader } from 'lucide-react'
import { format } from 'date-fns'
import clsx from 'clsx'
import type { ChatMessage as ChatMessageType } from '@/hooks/useQuery'

interface ChatMessageProps {
  message: ChatMessageType
  showTimestamp?: boolean
  showAgents?: boolean
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  showTimestamp = true,
  showAgents = true,
}) => {
  const isUser = message.type === 'user'
  const isSystem = message.type === 'system'
  const isAssistant = message.type === 'assistant'

  const getStatusIcon = () => {
    if (message.isStreaming) {
      return <Loader className="w-4 h-4 animate-spin text-kenny-primary" />
    }
    
    switch (message.metadata?.status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-kenny-success" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-kenny-error" />
      case 'partial':
        return <AlertCircle className="w-4 h-4 text-kenny-warning" />
      default:
        return null
    }
  }

  const getMessageIcon = () => {
    if (isUser) {
      return <User className="w-5 h-5 text-white" />
    } else if (isSystem) {
      return <Bot className="w-5 h-5 text-kenny-info" />
    } else {
      return <Bot className="w-5 h-5 text-white" />
    }
  }

  const formatContent = (content: string) => {
    // Simple markdown-like formatting
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code class="bg-kenny-gray-100 px-1 py-0.5 rounded text-sm">$1</code>')
  }

  return (
    <div className={clsx(
      'flex gap-3 mb-6',
      isUser ? 'justify-end' : 'justify-start'
    )}>
      {/* Avatar */}
      {!isUser && (
        <div className={clsx(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isSystem ? 'bg-kenny-info/20' : 'bg-kenny-primary'
        )}>
          {getMessageIcon()}
        </div>
      )}

      {/* Message Content */}
      <div className={clsx(
        'max-w-2xl',
        isUser ? 'ml-12' : 'mr-12'
      )}>
        {/* Message Bubble */}
        <div className={clsx(
          'rounded-2xl px-4 py-3 relative',
          isUser 
            ? 'bg-kenny-primary text-white rounded-br-sm'
            : isSystem
              ? 'bg-kenny-info/10 text-kenny-gray-800 border border-kenny-info/20'
              : 'bg-white text-kenny-gray-800 shadow-md rounded-bl-sm',
          message.isStreaming && 'animate-pulse'
        )}>
          {/* Streaming indicator */}
          {message.isStreaming && (
            <div className="absolute -top-2 -right-2 w-6 h-6 bg-kenny-primary rounded-full flex items-center justify-center">
              <div className="w-2 h-2 bg-white rounded-full animate-ping"></div>
            </div>
          )}

          {/* Content */}
          <div 
            className="prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ 
              __html: formatContent(message.content) 
            }}
          />

          {/* Agent indicators */}
          {showAgents && message.agentsUsed && message.agentsUsed.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {message.agentsUsed.map((agent) => (
                <span
                  key={agent}
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-kenny-primary/10 text-kenny-primary"
                >
                  {agent}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Metadata */}
        <div className="mt-2 flex items-center justify-between text-xs text-kenny-gray-500">
          <div className="flex items-center space-x-2">
            {/* Timestamp */}
            {showTimestamp && (
              <div className="flex items-center space-x-1">
                <Clock className="w-3 h-3" />
                <span>{format(message.timestamp, 'HH:mm')}</span>
              </div>
            )}

            {/* Status */}
            {getStatusIcon()}

            {/* Intent */}
            {message.metadata?.intent && (
              <span className="text-kenny-info font-medium">
                {message.metadata.intent}
              </span>
            )}

            {/* Duration */}
            {message.metadata?.duration && (
              <span>
                {message.metadata.duration < 1000 
                  ? `${message.metadata.duration}ms` 
                  : `${(message.metadata.duration / 1000).toFixed(1)}s`
                }
              </span>
            )}
          </div>

          {/* Execution path */}
          {message.executionPath && message.executionPath.length > 0 && (
            <div className="text-right">
              <span className="text-kenny-gray-400">
                Path: {message.executionPath.join(' → ')}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-kenny-secondary flex items-center justify-center">
          {getMessageIcon()}
        </div>
      )}
    </div>
  )
}