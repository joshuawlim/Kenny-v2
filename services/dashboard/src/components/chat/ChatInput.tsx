// Chat input component with suggestions and controls
import React, { useState, useRef, useCallback } from 'react'
import { Send, Mic, Paperclip, Zap, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

interface ChatInputProps {
  onSendMessage: (message: string) => void
  onSendStreamingMessage?: (message: string) => void
  isLoading: boolean
  isStreaming: boolean
  isConnected: boolean
  onConnect: () => void
  placeholder?: string
  disabled?: boolean
}

const QUICK_ACTIONS = [
  { label: 'Check my emails', query: 'Show me my recent emails' },
  { label: 'Today\'s meetings', query: 'What meetings do I have today?' },
  { label: 'System status', query: 'How are all the agents doing?' },
  { label: 'Help me plan', query: 'Help me plan my day based on my calendar and emails' },
]

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onSendStreamingMessage,
  isLoading,
  isStreaming,
  isConnected,
  onConnect,
  placeholder = "Ask Kenny anything...",
  disabled = false,
}) => {
  const [input, setInput] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = useCallback((message: string = input) => {
    if (!message.trim() || isLoading || isStreaming) return

    const trimmedMessage = message.trim()
    
    // Use streaming if connected, otherwise fall back to direct
    if (isConnected && onSendStreamingMessage) {
      onSendStreamingMessage(trimmedMessage)
    } else {
      onSendMessage(trimmedMessage)
    }
    
    setInput('')
    setShowSuggestions(false)
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [input, isLoading, isStreaming, isConnected, onSendMessage, onSendStreamingMessage])

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }, [handleSubmit])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setInput(value)
    
    // Auto-resize textarea
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
    
    // Show/hide suggestions
    setShowSuggestions(value.length === 0)
  }, [])

  const handleQuickAction = useCallback((query: string) => {
    handleSubmit(query)
  }, [handleSubmit])

  const isDisabled = disabled || isLoading || isStreaming

  return (
    <div className="relative">
      {/* Connection Status Banner */}
      {!isConnected && (
        <div className="mb-3 p-3 bg-kenny-warning/10 border border-kenny-warning/20 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-kenny-warning rounded-full"></div>
              <span className="text-sm text-kenny-warning font-medium">
                Real-time chat unavailable
              </span>
              <span className="text-xs text-kenny-gray-600">
                Falling back to direct queries
              </span>
            </div>
            <button
              onClick={onConnect}
              className="flex items-center space-x-1 text-xs text-kenny-warning hover:text-kenny-warning/80 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      {showSuggestions && (
        <div className="mb-4 p-4 bg-kenny-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-kenny-gray-700 mb-3">
            Quick Actions
          </h4>
          <div className="grid grid-cols-2 gap-2">
            {QUICK_ACTIONS.map((action, index) => (
              <button
                key={index}
                onClick={() => handleQuickAction(action.query)}
                className="p-2 text-left text-sm bg-white rounded-lg border border-kenny-gray-200 hover:border-kenny-primary hover:bg-kenny-primary/5 transition-all duration-200"
                disabled={isDisabled}
              >
                <div className="font-medium text-kenny-gray-800">
                  {action.label}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="glass-card rounded-2xl p-4">
        <div className="flex items-end space-x-3">
          {/* Text Input */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              onFocus={() => setShowSuggestions(input.length === 0)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder={placeholder}
              disabled={isDisabled}
              className={clsx(
                'w-full resize-none bg-transparent border-none outline-none',
                'text-kenny-gray-800 placeholder-kenny-gray-500',
                'min-h-[40px] max-h-[120px] py-2',
                'disabled:opacity-50'
              )}
              style={{ height: '40px' }}
            />
            
            {/* Character indicator for long messages */}
            {input.length > 500 && (
              <div className="absolute bottom-1 right-2 text-xs text-kenny-gray-400">
                {input.length}/2000
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-2">
            {/* Streaming Indicator */}
            {isConnected && (
              <div className="flex items-center space-x-1 px-2 py-1 bg-kenny-success/10 rounded-full">
                <Zap className="w-3 h-3 text-kenny-success" />
                <span className="text-xs text-kenny-success font-medium">Live</span>
              </div>
            )}

            {/* Future: Voice Input */}
            <button
              type="button"
              className="p-2 text-kenny-gray-400 hover:text-kenny-primary transition-colors disabled:opacity-50"
              disabled={true} // Not implemented yet
              title="Voice input (coming soon)"
            >
              <Mic className="w-5 h-5" />
            </button>

            {/* Future: File Attachment */}
            <button
              type="button"
              className="p-2 text-kenny-gray-400 hover:text-kenny-primary transition-colors disabled:opacity-50"
              disabled={true} // Not implemented yet
              title="Attach file (coming soon)"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            {/* Send Button */}
            <button
              type="button"
              onClick={() => handleSubmit()}
              disabled={!input.trim() || isDisabled}
              className={clsx(
                'p-2 rounded-lg transition-all duration-200',
                input.trim() && !isDisabled
                  ? 'bg-kenny-primary text-white hover:bg-kenny-secondary shadow-lg'
                  : 'bg-kenny-gray-200 text-kenny-gray-400 cursor-not-allowed'
              )}
            >
              {isLoading || isStreaming ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        {/* Status Bar */}
        {(isLoading || isStreaming) && (
          <div className="mt-3 pt-3 border-t border-kenny-gray-200">
            <div className="flex items-center space-x-2">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-kenny-primary rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-kenny-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-kenny-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
              <span className="text-sm text-kenny-gray-600">
                {isStreaming ? 'Kenny is responding...' : 'Processing your request...'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}