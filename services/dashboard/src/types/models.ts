// Data Models for Kenny v2

export interface Session {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  model: string;
  agentId?: string;
  messages: Message[];
  metadata: {
    totalTokens: number;
    estimatedCost: number;
    tags: string[];
  };
}

export interface Message {
  id: string;
  role: 'system' | 'user' | 'assistant';
  content: string;
  timestamp: Date;
  tokens?: number;
  cost?: number;
  toolCalls?: ToolCall[];
  metadata?: {
    model?: string;
    temperature?: number;
    maxTokens?: number;
    latencyMs?: number;
  };
}

export interface ToolCall {
  id: string;
  tool: string;
  args: Record<string, any>;
  result?: any;
  status: 'pending' | 'running' | 'success' | 'error';
  startTime?: Date;
  endTime?: Date;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  systemPrompt: string;
  tools: string[];
  capabilities: string[];
  safetyLimits: {
    maxTokensPerRequest: number;
    maxRequestsPerMinute: number;
    allowedDomains?: string[];
  };
  isActive: boolean;
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  category: 'search' | 'calendar' | 'email' | 'files' | 'web' | 'custom';
  parameters: ToolParameter[];
  capabilities: string[];
  requiresAuth: boolean;
  isEnabled: boolean;
}

export interface ToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description: string;
  required: boolean;
  default?: any;
}

export interface Model {
  id: string;
  name: string;
  provider: 'ollama' | 'openai' | 'anthropic' | 'local';
  size: string;
  contextWindow: number;
  costPer1kTokens: {
    input: number;
    output: number;
  };
  capabilities: string[];
  isDefault: boolean;
  isAvailable: boolean;
}

export interface Memory {
  id: string;
  sessionId: string;
  content: string;
  embedding?: number[];
  metadata: {
    source: string;
    timestamp: Date;
    relevanceScore?: number;
  };
}

export interface UsageLog {
  id: string;
  timestamp: Date;
  sessionId: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  latencyMs: number;
  toolCalls: string[];
  status: 'success' | 'error';
}