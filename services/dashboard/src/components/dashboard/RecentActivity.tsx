// Recent activity feed component
import React from 'react'
import { Activity, AlertTriangle, CheckCircle, Info, Shield } from 'lucide-react'
import { useSecurityEventStream } from '@/hooks'
import { format } from 'date-fns'
import clsx from 'clsx'

interface ActivityItem {
  id: string
  type: 'event' | 'incident' | 'health' | 'security'
  title: string
  description: string
  timestamp: Date
  severity: 'low' | 'medium' | 'high' | 'critical'
  source?: string
}

export const RecentActivity: React.FC = () => {
  const { events, incidents } = useSecurityEventStream()

  // Combine and sort recent events and incidents
  const activities: ActivityItem[] = React.useMemo(() => {
    const items: ActivityItem[] = []

    // Add security events
    events.slice(0, 5).forEach(event => {
      items.push({
        id: `event-${event.event_id}`,
        type: 'event',
        title: event.title,
        description: event.description,
        timestamp: new Date(event.timestamp),
        severity: event.severity,
        source: event.source_service,
      })
    })

    // Add security incidents
    incidents.slice(0, 3).forEach(incident => {
      items.push({
        id: `incident-${incident.incident_id}`,
        type: 'incident',
        title: incident.title,
        description: incident.description,
        timestamp: new Date(incident.created_at),
        severity: incident.severity,
      })
    })

    // Add some mock system activities for demonstration
    const now = new Date()
    items.push(
      {
        id: 'health-1',
        type: 'health',
        title: 'Agent Health Check Completed',
        description: 'All 7 agents passed health verification',
        timestamp: new Date(now.getTime() - 5 * 60 * 1000),
        severity: 'low',
      },
      {
        id: 'security-1',
        type: 'security',
        title: 'Compliance Scan Completed',
        description: 'ADR-0019 compliance check passed with 98.5% score',
        timestamp: new Date(now.getTime() - 15 * 60 * 1000),
        severity: 'low',
      }
    )

    // Sort by timestamp (newest first)
    return items.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()).slice(0, 10)
  }, [events, incidents])

  const getActivityIcon = (type: string, severity: string) => {
    switch (type) {
      case 'incident':
        return <AlertTriangle className="w-5 h-5" />
      case 'security':
        return <Shield className="w-5 h-5" />
      case 'health':
        return <CheckCircle className="w-5 h-5" />
      default:
        return <Info className="w-5 h-5" />
    }
  }

  const getActivityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-kenny-error bg-kenny-error/10 border-kenny-error/20'
      case 'high':
        return 'text-kenny-error bg-kenny-error/10 border-kenny-error/20'
      case 'medium':
        return 'text-kenny-warning bg-kenny-warning/10 border-kenny-warning/20'
      default:
        return 'text-kenny-info bg-kenny-info/10 border-kenny-info/20'
    }
  }

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-kenny-gray-800">
          Recent Activity
        </h3>
        <div className="flex items-center space-x-2">
          <Activity className="w-5 h-5 text-kenny-primary" />
          <span className="text-sm text-kenny-gray-600">Live Feed</span>
        </div>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto scrollbar-hide">
        {activities.length === 0 ? (
          <div className="text-center text-kenny-gray-500 py-8">
            <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No recent activity</p>
          </div>
        ) : (
          activities.map((activity) => (
            <div
              key={activity.id}
              className={clsx(
                'p-4 rounded-lg border transition-all duration-200 hover:shadow-md',
                getActivityColor(activity.severity)
              )}
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 mt-1">
                  {getActivityIcon(activity.type, activity.severity)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-medium text-kenny-gray-800 truncate">
                      {activity.title}
                    </h4>
                    <span className="text-xs text-kenny-gray-500 flex-shrink-0 ml-2">
                      {format(activity.timestamp, 'HH:mm')}
                    </span>
                  </div>
                  <p className="text-sm text-kenny-gray-600 mt-1 line-clamp-2">
                    {activity.description}
                  </p>
                  {activity.source && (
                    <span className="text-xs text-kenny-gray-500 mt-1 block">
                      Source: {activity.source}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {activities.length > 0 && (
        <div className="mt-4 pt-4 border-t border-kenny-gray-200">
          <button className="w-full text-sm text-kenny-primary hover:text-kenny-secondary font-medium transition-colors">
            View All Activity →
          </button>
        </div>
      )}
    </div>
  )
}