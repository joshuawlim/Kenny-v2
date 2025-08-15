import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useKeyboard } from '@/lib/hooks/useKeyboard';

interface Command {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  shortcut?: string;
  category: 'session' | 'model' | 'agent' | 'tool' | 'navigation' | 'settings';
  action: () => void;
}

export const CommandPalette: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Register keyboard shortcut
  useKeyboard('cmd+k', () => setIsOpen(true));
  useKeyboard('escape', () => setIsOpen(false), isOpen);

  const commands: Command[] = useMemo(() => [
    // Session commands
    {
      id: 'new-chat',
      name: 'New Chat',
      description: 'Start a new chat session',
      icon: '💬',
      shortcut: '⌘N',
      category: 'session',
      action: () => {
        window.location.href = '/chat/new';
        setIsOpen(false);
      },
    },
    {
      id: 'search-sessions',
      name: 'Search Sessions',
      description: 'Search through chat history',
      icon: '🔍',
      category: 'session',
      action: () => {
        console.log('Search sessions');
        setIsOpen(false);
      },
    },
    // Model commands
    {
      id: 'switch-model',
      name: 'Switch Model',
      description: 'Change the active model',
      icon: '🤖',
      shortcut: '⌘M',
      category: 'model',
      action: () => {
        console.log('Switch model');
        setIsOpen(false);
      },
    },
    {
      id: 'model-qwen',
      name: 'Use Qwen3:8b',
      description: 'Switch to Qwen 3 8B model',
      icon: '🧠',
      category: 'model',
      action: () => {
        console.log('Switch to Qwen3:8b');
        setIsOpen(false);
      },
    },
    // Agent commands
    {
      id: 'toggle-agent',
      name: 'Toggle Agent',
      description: 'Enable/disable current agent',
      icon: '🎯',
      category: 'agent',
      action: () => {
        console.log('Toggle agent');
        setIsOpen(false);
      },
    },
    // Tool commands
    {
      id: 'tool-search',
      name: '/search',
      description: 'Search the web or documents',
      icon: '🔎',
      category: 'tool',
      action: () => {
        document.querySelector<HTMLInputElement>('input[type="text"]')?.focus();
        // Set input value to /search
        setIsOpen(false);
      },
    },
    {
      id: 'tool-summarize',
      name: '/summarize',
      description: 'Summarize content',
      icon: '📝',
      category: 'tool',
      action: () => {
        console.log('Summarize');
        setIsOpen(false);
      },
    },
    {
      id: 'tool-plan',
      name: '/plan',
      description: 'Create an action plan',
      icon: '📋',
      category: 'tool',
      action: () => {
        console.log('Plan');
        setIsOpen(false);
      },
    },
    // Navigation
    {
      id: 'go-agents',
      name: 'Go to Agents',
      description: 'Manage agents',
      icon: '🤖',
      category: 'navigation',
      action: () => {
        window.location.href = '/agents';
        setIsOpen(false);
      },
    },
    {
      id: 'go-logs',
      name: 'View Logs',
      description: 'View usage logs',
      icon: '📊',
      category: 'navigation',
      action: () => {
        window.location.href = '/logs';
        setIsOpen(false);
      },
    },
    {
      id: 'go-settings',
      name: 'Settings',
      description: 'Application settings',
      icon: '⚙️',
      shortcut: '⌘,',
      category: 'settings',
      action: () => {
        window.location.href = '/settings';
        setIsOpen(false);
      },
    },
    // Settings
    {
      id: 'toggle-theme',
      name: 'Toggle Theme',
      description: 'Switch between light and dark mode',
      icon: '🌓',
      category: 'settings',
      action: () => {
        document.documentElement.classList.toggle('dark');
        setIsOpen(false);
      },
    },
    {
      id: 'export-session',
      name: 'Export Session',
      description: 'Export current session as JSON',
      icon: '💾',
      category: 'session',
      action: () => {
        console.log('Export session');
        setIsOpen(false);
      },
    },
  ], []);

  // Filter commands based on search
  const filteredCommands = useMemo(() => {
    if (!search) return commands;
    
    const searchLower = search.toLowerCase();
    return commands.filter(cmd => 
      cmd.name.toLowerCase().includes(searchLower) ||
      cmd.description?.toLowerCase().includes(searchLower) ||
      cmd.category.toLowerCase().includes(searchLower)
    );
  }, [commands, search]);

  // Group commands by category
  const groupedCommands = useMemo(() => {
    const groups: Record<string, Command[]> = {};
    filteredCommands.forEach(cmd => {
      if (!groups[cmd.category]) {
        groups[cmd.category] = [];
      }
      groups[cmd.category].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => 
            prev < filteredCommands.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => 
            prev > 0 ? prev - 1 : filteredCommands.length - 1
          );
          break;
        case 'Enter':
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands]);

  // Reset selected index when search changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
        onClick={() => setIsOpen(false)}
      />
      
      {/* Command Palette */}
      <div className="fixed inset-x-0 top-[20%] max-w-2xl mx-auto z-50">
        <div className="bg-gray-900 rounded-lg shadow-2xl border border-gray-700 overflow-hidden">
          {/* Search Input */}
          <div className="flex items-center border-b border-gray-700">
            <span className="pl-4 text-gray-400">🔍</span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Type a command or search..."
              className="flex-1 px-4 py-3 bg-transparent text-gray-100 placeholder-gray-500 focus:outline-none"
              autoFocus
            />
            <span className="pr-4 text-xs text-gray-500">ESC to close</span>
          </div>
          
          {/* Commands List */}
          <div className="max-h-96 overflow-y-auto">
            {Object.entries(groupedCommands).map(([category, cmds]) => (
              <div key={category}>
                <div className="px-4 py-1 text-xs font-semibold text-gray-500 uppercase bg-gray-800/50">
                  {category}
                </div>
                {cmds.map((cmd, idx) => {
                  const globalIndex = filteredCommands.indexOf(cmd);
                  const isSelected = globalIndex === selectedIndex;
                  
                  return (
                    <div
                      key={cmd.id}
                      className={`flex items-center justify-between px-4 py-2 cursor-pointer ${
                        isSelected ? 'bg-blue-600/20 text-blue-300' : 'hover:bg-gray-800 text-gray-300'
                      }`}
                      onClick={() => cmd.action()}
                      onMouseEnter={() => setSelectedIndex(globalIndex)}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-lg">{cmd.icon}</span>
                        <div>
                          <div className="font-medium">{cmd.name}</div>
                          {cmd.description && (
                            <div className="text-xs text-gray-500">{cmd.description}</div>
                          )}
                        </div>
                      </div>
                      {cmd.shortcut && (
                        <kbd className="px-2 py-1 text-xs bg-gray-800 rounded border border-gray-700">
                          {cmd.shortcut}
                        </kbd>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
            
            {filteredCommands.length === 0 && (
              <div className="px-4 py-8 text-center text-gray-500">
                No commands found
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};