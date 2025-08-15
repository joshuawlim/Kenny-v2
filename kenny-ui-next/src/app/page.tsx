'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { ChatInterface } from '@/components/chat/chat-interface'
import { useSessionStore } from '@/lib/stores/session-store'
import { useModelStore } from '@/lib/stores/model-store'

export default function HomePage() {
  const router = useRouter()
  const { currentSessionId, createSession } = useSessionStore()
  const { initializeModels } = useModelStore()

  useEffect(() => {
    // Initialize stores on app load
    initializeModels()
    
    // Create default session if none exists
    if (!currentSessionId) {
      const sessionId = createSession({
        title: 'New Chat',
        agentId: 'default',
        modelId: 'qwen2.5:8b',
      })
      
      // Optionally redirect to specific session URL
      // router.push(`/chat/${sessionId}`)
    }
  }, [currentSessionId, createSession, initializeModels, router])

  return (
    <DashboardLayout>
      <div className="flex-1 flex flex-col min-h-0">
        <ChatInterface />
      </div>
    </DashboardLayout>
  )
}