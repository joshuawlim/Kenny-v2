// Test for ChatMessage component
import { render, screen } from '@testing-library/react'
import { ChatMessage } from '../ChatMessage'
import type { ChatMessage as ChatMessageType } from '@/hooks/useQuery'

const mockUserMessage: ChatMessageType = {
  id: '1',
  type: 'user',
  content: 'Hello Kenny',
  timestamp: new Date('2025-01-01T12:00:00Z'),
}

const mockAssistantMessage: ChatMessageType = {
  id: '2',
  type: 'assistant',
  content: 'Hello! How can I help you today?',
  timestamp: new Date('2025-01-01T12:00:30Z'),
  agentsUsed: ['coordinator'],
  metadata: {
    intent: 'greeting',
    duration: 500,
    status: 'success',
  },
}

const mockStreamingMessage: ChatMessageType = {
  id: '3',
  type: 'assistant',
  content: 'Thinking...',
  timestamp: new Date('2025-01-01T12:01:00Z'),
  isStreaming: true,
}

describe('ChatMessage', () => {
  it('renders user messages correctly', () => {
    render(<ChatMessage message={mockUserMessage} />)
    
    expect(screen.getByText('Hello Kenny')).toBeInTheDocument()
    expect(screen.getByText('12:00')).toBeInTheDocument()
  })

  it('renders assistant messages correctly', () => {
    render(<ChatMessage message={mockAssistantMessage} />)
    
    expect(screen.getByText('Hello! How can I help you today?')).toBeInTheDocument()
    expect(screen.getByText('12:00')).toBeInTheDocument()
    expect(screen.getByText('coordinator')).toBeInTheDocument()
    expect(screen.getByText('greeting')).toBeInTheDocument()
    expect(screen.getByText('500ms')).toBeInTheDocument()
  })

  it('shows streaming indicator for streaming messages', () => {
    render(<ChatMessage message={mockStreamingMessage} />)
    
    expect(screen.getByText('Thinking...')).toBeInTheDocument()
    // Streaming indicator should be present (pulse animation)
    const messageElement = screen.getByText('Thinking...').closest('.rounded-2xl')
    expect(messageElement).toHaveClass('animate-pulse')
  })

  it('renders agent indicators when agents are used', () => {
    render(<ChatMessage message={mockAssistantMessage} showAgents={true} />)
    
    expect(screen.getByText('coordinator')).toBeInTheDocument()
  })

  it('hides agent indicators when showAgents is false', () => {
    render(<ChatMessage message={mockAssistantMessage} showAgents={false} />)
    
    expect(screen.queryByText('coordinator')).not.toBeInTheDocument()
  })

  it('formats markdown content correctly', () => {
    const messageWithMarkdown: ChatMessageType = {
      id: '4',
      type: 'assistant',
      content: '**Bold text** and *italic text* and `code text`',
      timestamp: new Date(),
    }

    render(<ChatMessage message={messageWithMarkdown} />)
    
    // Should render HTML formatted content
    const contentElement = screen.getByText(/Bold text/)
    expect(contentElement.innerHTML).toContain('<strong>Bold text</strong>')
    expect(contentElement.innerHTML).toContain('<em>italic text</em>')
    expect(contentElement.innerHTML).toContain('<code')
  })

  it('shows execution path when available', () => {
    const messageWithPath: ChatMessageType = {
      id: '5',
      type: 'assistant',
      content: 'Task completed',
      timestamp: new Date(),
      executionPath: ['coordinator', 'mail-agent', 'calendar-agent'],
    }

    render(<ChatMessage message={messageWithPath} />)
    
    expect(screen.getByText('Path: coordinator → mail-agent → calendar-agent')).toBeInTheDocument()
  })
})