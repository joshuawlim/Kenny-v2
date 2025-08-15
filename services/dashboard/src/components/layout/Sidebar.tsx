// Sidebar navigation component
import React from 'react'
import { NavLink } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Activity, 
  Users, 
  Shield, 
  MessageSquare, 
  BarChart3, 
  AlertTriangle,
  Settings,
  Search
} from 'lucide-react'
import clsx from 'clsx'

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
}

const navigationItems = [
  {
    name: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
    description: 'System overview'
  },
  {
    name: 'Agents',
    href: '/agents',
    icon: Users,
    description: 'Agent monitoring'
  },
  {
    name: 'Query',
    href: '/query',
    icon: MessageSquare,
    description: 'Multi-agent interface'
  },
  {
    name: 'Health',
    href: '/health',
    icon: Activity,
    description: 'System health'
  },
  {
    name: 'Security',
    href: '/security',
    icon: Shield,
    description: 'Security monitoring'
  },
  {
    name: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
    description: 'Performance metrics'
  },
  {
    name: 'Traces',
    href: '/traces',
    icon: Search,
    description: 'Request tracing'
  },
  {
    name: 'Alerts',
    href: '/alerts',
    icon: AlertTriangle,
    description: 'Alert management'
  },
]

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onToggle }) => {
  return (
    <>
      {/* Backdrop for mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
          onClick={onToggle}
        />
      )}
      
      {/* Sidebar */}
      <aside className={clsx(
        'fixed left-0 top-0 h-full w-64 glass-card transform transition-transform duration-300 ease-in-out z-50',
        'lg:translate-x-0 lg:static lg:z-auto',
        isOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-kenny-primary rounded-lg flex items-center justify-center">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="font-bold text-kenny-gray-800">Kenny v2</h2>
                <p className="text-xs text-kenny-gray-600">Dashboard</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
            {navigationItems.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  clsx(
                    'sidebar-item group',
                    isActive && 'active'
                  )
                }
                onClick={() => {
                  // Close sidebar on mobile when navigating
                  if (window.innerWidth < 1024) {
                    onToggle()
                  }
                }}
              >
                <item.icon className="w-5 h-5 text-kenny-gray-600 group-hover:text-white transition-colors" />
                <div className="flex-1">
                  <div className="font-medium text-kenny-gray-700 group-hover:text-white">
                    {item.name}
                  </div>
                  <div className="text-xs text-kenny-gray-500 group-hover:text-white/80">
                    {item.description}
                  </div>
                </div>
              </NavLink>
            ))}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-white/10">
            <div className="text-xs text-kenny-gray-500 text-center">
              <div>Local-first • Privacy-focused</div>
              <div className="mt-1">v2.0.0 • Phase 6</div>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}