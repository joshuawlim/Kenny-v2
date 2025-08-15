// System overview component with key metrics
import React from 'react'
import { Activity, Users, Shield, Zap, Clock, CheckCircle } from 'lucide-react'
import { MetricCard } from './MetricCard'
import { useSystemHealthStream, useAgentStatus, useSecurityMetrics } from '@/hooks'

export const SystemOverview: React.FC = () => {
  const { data: healthData, isConnected } = useSystemHealthStream()
  const { healthyCount, totalCount, healthPercentage } = useAgentStatus()
  const { securityScore, complianceScore, totalEvents, openIncidents } = useSecurityMetrics()

  const performanceData = healthData?.performance_overview
  const avgResponseTime = performanceData?.average_response_time_ms || 0
  const successRate = performanceData?.average_success_rate_percent || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-kenny-gray-800">
          System Overview
        </h2>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-kenny-success' : 'bg-kenny-error'} animate-pulse`}></div>
          <span className="text-sm text-kenny-gray-600">
            {isConnected ? 'Live Data' : 'Offline'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
        {/* Agent Health */}
        <MetricCard
          title="Agent Health"
          value={`${healthyCount}/${totalCount}`}
          description={`${healthPercentage.toFixed(0)}% operational`}
          icon={Users}
          status={healthPercentage >= 80 ? 'success' : healthPercentage >= 60 ? 'warning' : 'error'}
          trend={{
            value: 2.5,
            isPositive: true,
            label: 'vs last hour'
          }}
        />

        {/* Security Score */}
        <MetricCard
          title="Security Score"
          value={`${securityScore.toFixed(0)}%`}
          description="Overall security health"
          icon={Shield}
          status={securityScore >= 90 ? 'success' : securityScore >= 70 ? 'warning' : 'error'}
          trend={{
            value: 1.2,
            isPositive: securityScore >= 80,
            label: 'vs yesterday'
          }}
        />

        {/* Compliance Rate */}
        <MetricCard
          title="Compliance"
          value={`${complianceScore.toFixed(1)}%`}
          description="ADR-0019 compliance"
          icon={CheckCircle}
          status={complianceScore >= 95 ? 'success' : complianceScore >= 90 ? 'warning' : 'error'}
        />

        {/* Response Time */}
        <MetricCard
          title="Response Time"
          value={avgResponseTime < 1000 ? `${avgResponseTime.toFixed(0)}ms` : `${(avgResponseTime/1000).toFixed(1)}s`}
          description="Average response time"
          icon={Clock}
          status={avgResponseTime < 100 ? 'success' : avgResponseTime < 500 ? 'warning' : 'error'}
          trend={{
            value: 8.3,
            isPositive: false,
            label: 'vs last hour'
          }}
        />

        {/* Success Rate */}
        <MetricCard
          title="Success Rate"
          value={`${successRate.toFixed(1)}%`}
          description="Request success rate"
          icon={Activity}
          status={successRate >= 95 ? 'success' : successRate >= 90 ? 'warning' : 'error'}
        />

        {/* Incidents */}
        <MetricCard
          title="Open Incidents"
          value={openIncidents}
          description={`${totalEvents} events today`}
          icon={Zap}
          status={openIncidents === 0 ? 'success' : openIncidents <= 2 ? 'warning' : 'error'}
        />
      </div>
    </div>
  )
}