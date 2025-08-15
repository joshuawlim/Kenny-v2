import React, { useState, useEffect, useRef } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: {
    agents?: string[];
    requestId?: string;
    duration?: number;
  };
}

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Test connection on mount
  useEffect(() => {
    testConnection();
  }, []);

  const testConnection = async () => {
    try {
      const response = await fetch('/api/health');
      setConnectionStatus(response.ok ? 'connected' : 'error');
    } catch (error) {
      setConnectionStatus('error');
    }
  };

  const sendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: inputValue,
          context: {
            session_id: `chat-${Date.now()}`,
            user_id: 'dashboard-user'
          }
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: data.result?.message || JSON.stringify(data.result, null, 2),
          timestamp: new Date(),
          metadata: {
            agents: data.execution_path || [],
            requestId: data.request_id,
            duration: data.duration_ms
          }
        };

        setMessages(prev => [...prev, assistantMessage]);
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const testPrompts = [
    "What was my last 3 emails to Krista Hiob?",
    "What were the last 3 messages I sent to Courtney?",
    "Whose birthday is next?"
  ];

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      minHeight: '500px'
    }}>
      {/* Header */}
      <div style={{
        padding: '20px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
        background: 'rgba(255, 255, 255, 0.03)'
      }}>
        <h2 style={{margin: '0 0 10px 0', fontSize: '20px'}}>Kenny Chat Interface</h2>
        <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: connectionStatus === 'connected' ? '#14b88a' : '#ef4444'
          }} />
          <span style={{fontSize: '14px', opacity: 0.7}}>
            {connectionStatus === 'connected' ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Quick Test Buttons */}
      <div style={{
        padding: '15px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
        background: 'rgba(255, 255, 255, 0.02)'
      }}>
        <div style={{fontSize: '12px', marginBottom: '10px', opacity: 0.7}}>
          Quick Test Prompts:
        </div>
        <div style={{display: 'flex', gap: '8px', flexWrap: 'wrap'}}>
          {testPrompts.map((prompt, index) => (
            <button
              key={index}
              onClick={() => setInputValue(prompt)}
              style={{
                padding: '6px 12px',
                background: 'rgba(20, 184, 138, 0.1)',
                border: '1px solid rgba(20, 184, 138, 0.3)',
                borderRadius: '6px',
                color: 'white',
                fontSize: '12px',
                cursor: 'pointer'
              }}
            >
              Test {index + 1}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px'
      }}>
        {messages.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '40px',
            opacity: 0.7
          }}>
            <div style={{fontSize: '48px', marginBottom: '20px'}}>🤖</div>
            <h3>Welcome to Kenny</h3>
            <p>Start a conversation with your AI assistant</p>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} style={{
              marginBottom: '20px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: message.role === 'user' ? 'flex-end' : 'flex-start'
            }}>
              <div style={{
                maxWidth: '80%',
                padding: '12px 16px',
                borderRadius: '12px',
                backgroundColor: message.role === 'user' 
                  ? 'rgba(20, 184, 138, 0.2)' 
                  : message.role === 'system'
                    ? 'rgba(239, 68, 68, 0.2)'
                    : 'rgba(255, 255, 255, 0.06)',
                border: `1px solid ${
                  message.role === 'user' 
                    ? 'rgba(20, 184, 138, 0.3)' 
                    : message.role === 'system'
                      ? 'rgba(239, 68, 68, 0.3)'
                      : 'rgba(255, 255, 255, 0.12)'
                }`
              }}>
                <div style={{
                  fontSize: '12px',
                  opacity: 0.7,
                  marginBottom: '4px'
                }}>
                  {message.role === 'user' ? 'You' : message.role === 'assistant' ? 'Kenny' : 'System'}
                  {message.metadata?.agents && (
                    <span style={{marginLeft: '8px'}}>
                      via {message.metadata.agents.join(', ')}
                    </span>
                  )}
                </div>
                <div style={{
                  whiteSpace: 'pre-wrap',
                  lineHeight: '1.4'
                }}>
                  {message.content}
                </div>
                {message.metadata?.duration && (
                  <div style={{
                    fontSize: '11px',
                    opacity: 0.5,
                    marginTop: '4px'
                  }}>
                    {message.metadata.duration}ms
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '20px',
        borderTop: '1px solid rgba(255, 255, 255, 0.12)',
        background: 'rgba(255, 255, 255, 0.03)'
      }}>
        <div style={{display: 'flex', gap: '10px'}}>
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask Kenny anything..."
            disabled={isLoading}
            rows={2}
            style={{
              flex: 1,
              padding: '12px',
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '8px',
              color: 'white',
              fontSize: '14px',
              resize: 'none',
              fontFamily: 'inherit'
            }}
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !inputValue.trim()}
            style={{
              padding: '12px 20px',
              background: isLoading ? 'rgba(255, 255, 255, 0.1)' : 'rgba(20, 184, 138, 0.2)',
              border: '1px solid rgba(20, 184, 138, 0.3)',
              borderRadius: '8px',
              color: 'white',
              cursor: isLoading ? 'default' : 'pointer',
              fontSize: '14px'
            }}
          >
            {isLoading ? '...' : 'Send'}
          </button>
        </div>
        <div style={{
          fontSize: '12px',
          opacity: 0.5,
          marginTop: '8px'
        }}>
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  );
};