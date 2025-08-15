import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Message, ToolCall } from '@/types/models';
import { useKeyboard } from '@/lib/hooks/useKeyboard';

interface StreamingChatProps {
  sessionId: string;
  model: string;
  agent?: string;
}

export const StreamingChat: React.FC<StreamingChatProps> = ({ sessionId, model, agent }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [totalTokens, setTotalTokens] = useState(0);
  const [estimatedCost, setEstimatedCost] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Keyboard shortcuts
  useKeyboard('cmd+enter', () => handleSend());
  useKeyboard('escape', () => handleStop());
  useKeyboard('alt+up', () => editLastMessage());

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);
    setStreamingContent('');

    try {
      abortControllerRef.current = new AbortController();
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          model,
          agent,
          messages: [...messages, userMessage],
          stream: true,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) throw new Error('Stream failed');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';
      let tokenCount = 0;

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'token') {
                accumulatedContent += data.content;
                setStreamingContent(accumulatedContent);
                tokenCount++;
                setTotalTokens(prev => prev + 1);
              } else if (data.type === 'tool_call') {
                // Handle tool calls
                console.log('Tool call:', data);
              } else if (data.type === 'done') {
                const assistantMessage: Message = {
                  id: `msg-${Date.now()}`,
                  role: 'assistant',
                  content: accumulatedContent,
                  timestamp: new Date(),
                  tokens: tokenCount,
                  cost: data.cost,
                  metadata: {
                    model,
                    latencyMs: data.latencyMs,
                  },
                };
                setMessages(prev => [...prev, assistantMessage]);
                setEstimatedCost(prev => prev + (data.cost || 0));
              }
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Stream error:', error);
        // Add error message
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          role: 'system',
          content: `Error: ${error.message}`,
          timestamp: new Date(),
        } as Message]);
      }
    } finally {
      setIsStreaming(false);
      setStreamingContent('');
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const editLastMessage = () => {
    const lastUserMessage = messages.filter(m => m.role === 'user').pop();
    if (lastUserMessage) {
      setInput(lastUserMessage.content);
      setMessages(prev => prev.filter(m => m.id !== lastUserMessage.id));
    }
  };

  const handleSlashCommand = (command: string) => {
    const commands = {
      '/search': 'Search for: ',
      '/summarize': 'Summarize this: ',
      '/plan': 'Create a plan for: ',
      '/tool': 'Use tool: ',
    };
    
    if (commands[command]) {
      setInput(commands[command]);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold">Chat</h2>
          <span className="text-sm text-gray-400">{model}</span>
          {agent && (
            <span className="px-2 py-1 text-xs bg-blue-900 text-blue-200 rounded">
              {agent}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-400">
            {totalTokens} tokens
          </span>
          <span className="text-sm text-green-400">
            ${estimatedCost.toFixed(4)}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {isStreaming && streamingContent && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
              K
            </div>
            <div className="flex-1 bg-gray-800 rounded-lg p-3">
              <div className="text-sm whitespace-pre-wrap">{streamingContent}</div>
              <StreamingIndicator />
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && e.metaKey) {
                handleSend();
              } else if (e.key === '/' && input === '') {
                e.preventDefault();
                // Show slash commands
              }
            }}
            placeholder="Type a message or / for commands..."
            className="flex-1 bg-gray-800 text-gray-100 px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStreaming ? 'Stop' : 'Send ⌘↩'}
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Press / for commands • ⌘↩ to send • Esc to stop • ⌥↑ to edit last
        </div>
      </div>
    </div>
  );
};

const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-green-600' : message.role === 'system' ? 'bg-red-600' : 'bg-blue-600'
      }`}>
        {isUser ? 'U' : message.role === 'system' ? 'S' : 'K'}
      </div>
      <div className={`flex-1 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`bg-gray-800 rounded-lg p-3 ${isUser ? 'bg-gray-700' : ''}`}>
          <div className="text-sm whitespace-pre-wrap">{message.content}</div>
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mt-2 space-y-1">
              {message.toolCalls.map((tool) => (
                <ToolCallDisplay key={tool.id} toolCall={tool} />
              ))}
            </div>
          )}
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
          {message.tokens && <span>{message.tokens} tokens</span>}
          {message.cost && <span>${message.cost.toFixed(4)}</span>}
          {message.metadata?.latencyMs && <span>{message.metadata.latencyMs}ms</span>}
        </div>
      </div>
    </div>
  );
};

const ToolCallDisplay: React.FC<{ toolCall: ToolCall }> = ({ toolCall }) => {
  return (
    <div className="bg-gray-900 rounded px-2 py-1 text-xs">
      <span className="text-yellow-400">🔧 {toolCall.tool}</span>
      {toolCall.status === 'running' && <span className="ml-2 text-blue-400">Running...</span>}
      {toolCall.status === 'success' && <span className="ml-2 text-green-400">✓</span>}
      {toolCall.status === 'error' && <span className="ml-2 text-red-400">✗</span>}
    </div>
  );
};

const StreamingIndicator: React.FC = () => {
  return (
    <div className="flex gap-1 mt-2">
      <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
      <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
      <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
    </div>
  );
};