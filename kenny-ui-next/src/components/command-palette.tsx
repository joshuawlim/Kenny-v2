'use client'

import { useState, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { Command, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem } from '@/components/ui/command'
import { useHotkeys } from 'react-hotkeys-hook'
import { useSessionStore } from '@/lib/stores/session-store'
import { useModelStore } from '@/lib/stores/model-store'
import { useAgentStore } from '@/lib/stores/agent-store'
import { 
  MessageSquare, 
  Bot, 
  Cpu, 
  Settings, 
  FileText, 
  Brain, 
  BarChart3,
  Search,
  Plus,
  Download,
  Upload,
  Trash2,
  Copy
} from 'lucide-react'
import type { Command as CommandType } from '@/lib/types'

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const router = useRouter()
  
  const { createSession, sessions, currentSessionId, deleteSession } = useSessionStore()
  const { models, setCurrentModel, currentModelId } = useModelStore()
  const { agents, setCurrentAgent, currentAgentId } = useAgentStore()

  // Toggle command palette with ⌘K
  useHotkeys('cmd+k', (e) => {
    e.preventDefault()
    setOpen(true)
  }, { preventDefault: true })

  // Close on escape
  useHotkeys('escape', () => {
    if (open) {
      setOpen(false)
      setSearch('')
    }
  }, { enabled: open })

  // Define all available commands
  const commands = useMemo((): CommandType[] => [
    // Navigation
    {
      id: 'nav-home',
      title: 'Go to Chat',
      description: 'Open main chat interface',
      category: 'navigation',
      keywords: ['home', 'chat', 'main'],
      icon: 'MessageSquare',
      action: () => {
        router.push('/')
        setOpen(false)
      },
    },
    {
      id: 'nav-agents',
      title: 'Go to Agents',
      description: 'Manage and configure agents',
      category: 'navigation',
      keywords: ['agents', 'bots', 'configure'],
      icon: 'Bot',
      action: () => {
        router.push('/agents')
        setOpen(false)
      },
    },
    {
      id: 'nav-models',
      title: 'Go to Models',
      description: 'Manage AI models',
      category: 'navigation',
      keywords: ['models', 'ai', 'llm'],
      icon: 'Cpu',
      action: () => {
        router.push('/models')
        setOpen(false)
      },
    },
    {
      id: 'nav-settings',
      title: 'Go to Settings',
      description: 'Configure preferences',
      category: 'navigation',
      keywords: ['settings', 'preferences', 'config'],
      icon: 'Settings',
      action: () => {
        router.push('/settings')
        setOpen(false)
      },
    },

    // Session management
    {
      id: 'session-new',
      title: 'New Chat',
      description: 'Create a new chat session',
      category: 'session',
      keywords: ['new', 'chat', 'session'],
      shortcut: '⌘N',
      icon: 'Plus',
      action: () => {
        const sessionId = createSession({
          title: 'New Chat',
          agentId: currentAgentId || 'default',
          modelId: currentModelId || 'qwen2.5:8b',
        })
        router.push(`/chat/${sessionId}`)
        setOpen(false)
      },
    },
    {
      id: 'session-delete',
      title: 'Delete Current Session',
      description: 'Delete the current chat session',
      category: 'session',
      keywords: ['delete', 'remove', 'session'],
      icon: 'Trash2',
      isEnabled: !!currentSessionId,
      action: () => {
        if (currentSessionId) {
          deleteSession(currentSessionId)
          router.push('/')
        }
        setOpen(false)
      },
    },

    // Model switching
    ...models.map((model) => ({
      id: `model-${model.id}`,
      title: `Switch to ${model.name}`,
      description: `Use ${model.name} for responses`,
      category: 'agent' as const,
      keywords: ['model', 'switch', model.name.toLowerCase()],
      icon: 'Cpu',
      action: () => {
        setCurrentModel(model.id)
        setOpen(false)
      },
    })),

    // Agent switching
    ...agents.map((agent) => ({
      id: `agent-${agent.id}`,
      title: `Switch to ${agent.name}`,
      description: agent.description,
      category: 'agent' as const,
      keywords: ['agent', 'switch', agent.name.toLowerCase()],
      icon: 'Bot',
      action: () => {
        setCurrentAgent(agent.id)
        setOpen(false)
      },
    })),

    // Slash commands
    {
      id: 'cmd-search',
      title: '/search',
      description: 'Search across your data',
      category: 'tool',
      keywords: ['search', 'find', 'query'],
      icon: 'Search',
      action: () => {
        // Implement search functionality
        setOpen(false)
      },
    },
    {
      id: 'cmd-summarize',
      title: '/summarize',
      description: 'Summarize the current conversation',
      category: 'tool',
      keywords: ['summarize', 'summary'],
      icon: 'FileText',
      action: () => {
        // Implement summarization
        setOpen(false)
      },
    },
    {
      id: 'cmd-memory',
      title: '/memory',
      description: 'Access session memory',
      category: 'tool',
      keywords: ['memory', 'context', 'remember'],
      icon: 'Brain',
      action: () => {
        // Open memory panel
        setOpen(false)
      },
    },

    // System commands
    {
      id: 'system-export',
      title: 'Export Session',
      description: 'Export chat as JSON',
      category: 'system',
      keywords: ['export', 'download', 'backup'],
      icon: 'Download',
      isEnabled: !!currentSessionId,
      action: () => {
        // Implement export
        setOpen(false)
      },
    },
    {
      id: 'system-import',
      title: 'Import Session',
      description: 'Import chat from file',
      category: 'system',
      keywords: ['import', 'upload', 'restore'],
      icon: 'Upload',
      action: () => {
        // Implement import
        setOpen(false)
      },
    },
  ], [
    router, 
    createSession, 
    deleteSession, 
    currentSessionId, 
    currentAgentId, 
    currentModelId,
    models, 
    agents, 
    setCurrentModel, 
    setCurrentAgent
  ])

  // Filter commands based on search
  const filteredCommands = useMemo(() => {
    if (!search) return commands

    const searchLower = search.toLowerCase()
    return commands.filter((command) => 
      command.isEnabled !== false && (
        command.title.toLowerCase().includes(searchLower) ||
        command.description?.toLowerCase().includes(searchLower) ||
        command.keywords.some(keyword => keyword.includes(searchLower))
      )
    )
  }, [commands, search])

  // Group commands by category
  const groupedCommands = useMemo(() => {
    const groups: Record<string, CommandType[]> = {}
    
    filteredCommands.forEach((command) => {
      if (!groups[command.category]) {
        groups[command.category] = []
      }
      groups[command.category].push(command)
    })

    return groups
  }, [filteredCommands])

  const categoryLabels = {
    navigation: 'Navigation',
    session: 'Sessions', 
    agent: 'Models & Agents',
    tool: 'Tools',
    system: 'System',
  }

  const getIcon = (iconName: string) => {
    const icons = {
      MessageSquare,
      Bot,
      Cpu,
      Settings,
      FileText,
      Brain,
      BarChart3,
      Search,
      Plus,
      Download,
      Upload,
      Trash2,
      Copy,
    }
    return icons[iconName as keyof typeof icons] || MessageSquare
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="p-0 max-w-2xl command-palette">
        <Command>
          <CommandInput
            placeholder="Type a command or search..."
            value={search}
            onValueChange={setSearch}
            className="border-0 border-b border-border"
          />
          <CommandList className="max-h-80 overflow-auto">
            <CommandEmpty>No commands found.</CommandEmpty>
            
            {Object.entries(groupedCommands).map(([category, commands]) => (
              <CommandGroup 
                key={category} 
                heading={categoryLabels[category as keyof typeof categoryLabels]}
              >
                {commands.map((command) => {
                  const Icon = getIcon(command.icon || 'MessageSquare')
                  
                  return (
                    <CommandItem
                      key={command.id}
                      onSelect={() => command.action()}
                      className="flex items-center gap-3 px-4 py-3 cursor-pointer"
                    >
                      <Icon className="w-4 h-4 text-kenny-gray-400" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="font-medium truncate">
                            {command.title}
                          </span>
                          {command.shortcut && (
                            <span className="kbd ml-2">
                              {command.shortcut}
                            </span>
                          )}
                        </div>
                        {command.description && (
                          <p className="text-sm text-kenny-gray-400 truncate">
                            {command.description}
                          </p>
                        )}
                      </div>
                    </CommandItem>
                  )
                })}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  )
}