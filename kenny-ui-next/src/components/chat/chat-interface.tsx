'use client'

import { useState, useRef, useEffect } from 'react'
import { useSessionStore } from '@/lib/stores/session-store'
import { useStreamingChat } from '@/lib/hooks/use-streaming-chat'
import { MessageList } from './message-list'
import { MessageInput } from './message-input'
import { StreamingIndicator } from './streaming-indicator'
import { WelcomeScreen } from './welcome-screen'
import { cn } from '@/lib/utils'

export function ChatInterface() {
  const { currentSessionId, messages, addMessage, updateMessage } = useSessionStore()
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const {
    sendMessage,
    stopGeneration,
    isConnected,
    isStreaming,
    error,
  } = useStreamingChat({
    sessionId: currentSessionId,
    onMessageUpdate: updateMessage,
  })

  const sessionMessages = currentSessionId ? messages[currentSessionId] || [] : []
  const hasMessages = sessionMessages.length > 0

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [sessionMessages])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !currentSessionId) return

    const userMessageId = addMessage(currentSessionId, {
      role: 'user',
      content: inputValue,
    })

    const assistantMessageId = addMessage(currentSessionId, {
      role: 'assistant',
      content: '',
      isStreaming: true,
    })

    setInputValue('')

    try {
      await sendMessage(inputValue, {
        messageId: assistantMessageId,
        userMessageId,
      })
    } catch (error) {
      updateMessage(currentSessionId, assistantMessageId, {
        content: 'Sorry, I encountered an error. Please try again.',
        isStreaming: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      })
    }
  }

  if (!currentSessionId) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <WelcomeScreen />
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Messages area */}
      <div className="flex-1 overflow-hidden">
        {hasMessages ? (
          <>
            <MessageList 
              messages={sessionMessages}
              className="h-full"
            />
            <div ref={messagesEndRef} />
          </>
        ) : (
          <div className="h-full flex items-center justify-center">
            <WelcomeScreen showQuickActions />
          </div>
        )}
      </div>

      {/* Connection status & streaming indicator */}
      {(isStreaming || !isConnected || error) && (
        <div className="border-t border-border/50 px-4 py-2">
          <StreamingIndicator 
            isStreaming={isStreaming}
            isConnected={isConnected}
            error={error}
            onStop={stopGeneration}
          />
        </div>
      )}

      {/* Message input */}
      <div className="border-t border-border/50 p-4">
        <MessageInput
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSendMessage}
          disabled={isStreaming}
          placeholder={
            hasMessages 
              ? "Ask Kenny anything..." 
              : "Start a conversation with Kenny..."
          }
        />
      </div>
    </div>
  )
}