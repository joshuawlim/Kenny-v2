'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { LeftRail } from './left-rail'
import { RightRail } from './right-rail'
import { TopBar } from './top-bar'
import { useHotkeys } from 'react-hotkeys-hook'
import { useSessionStore } from '@/lib/stores/session-store'

interface DashboardLayoutProps {
  children: React.ReactNode
  className?: string
}

export function DashboardLayout({ children, className }: DashboardLayoutProps) {
  const [leftRailOpen, setLeftRailOpen] = useState(true)
  const [rightRailOpen, setRightRailOpen] = useState(true)
  const { createSession } = useSessionStore()

  // Global keyboard shortcuts
  useHotkeys('cmd+n', () => {
    const sessionId = createSession({
      title: 'New Chat',
      agentId: 'default',
      modelId: 'qwen2.5:8b',
    })
    // Could navigate to new session here
  }, { preventDefault: true })

  useHotkeys('alt+left', () => {
    setLeftRailOpen(!leftRailOpen)
  }, { preventDefault: true })

  useHotkeys('alt+right', () => {
    setRightRailOpen(!rightRailOpen)
  }, { preventDefault: true })

  return (
    <div className={cn('h-screen flex flex-col', className)}>
      {/* Top navigation bar */}
      <TopBar 
        leftRailOpen={leftRailOpen}
        rightRailOpen={rightRailOpen}
        onToggleLeftRail={() => setLeftRailOpen(!leftRailOpen)}
        onToggleRightRail={() => setRightRailOpen(!rightRailOpen)}
      />

      {/* Main content area */}
      <div className="flex-1 flex min-h-0">
        {/* Left rail - Session list */}
        <LeftRail 
          isOpen={leftRailOpen}
          onToggle={() => setLeftRailOpen(!leftRailOpen)}
        />

        {/* Main content */}
        <main 
          className={cn(
            'flex-1 flex flex-col min-h-0 transition-all duration-300 ease-in-out',
            leftRailOpen && 'ml-0',
            rightRailOpen && 'mr-0'
          )}
        >
          {children}
        </main>

        {/* Right rail - Context panel */}
        <RightRail 
          isOpen={rightRailOpen}
          onToggle={() => setRightRailOpen(!rightRailOpen)}
        />
      </div>
    </div>
  )
}