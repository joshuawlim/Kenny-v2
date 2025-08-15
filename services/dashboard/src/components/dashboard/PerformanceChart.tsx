// Performance metrics chart component
import React, { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { useSystemHealthStream } from '@/hooks'
import { format } from 'date-fns'

interface DataPoint {
  timestamp: string
  responseTime: number
  successRate: number
  agentHealth: number
}

export const PerformanceChart: React.FC = () => {
  const { data: healthData } = useSystemHealthStream()

  // Generate sample historical data for demonstration
  // In a real implementation, this would come from the analytics API
  const chartData = useMemo<DataPoint[]>(() => {
    const now = new Date()
    const data: DataPoint[] = []
    
    for (let i = 23; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000)
      data.push({
        timestamp: format(timestamp, 'HH:mm'),
        responseTime: Math.random() * 200 + 50,
        successRate: 95 + Math.random() * 5,
        agentHealth: 90 + Math.random() * 10,
      })
    }

    // Use current data for the latest point if available
    if (healthData?.performance_overview) {
      const currentData = data[data.length - 1]
      currentData.responseTime = healthData.performance_overview.average_response_time_ms
      currentData.successRate = healthData.performance_overview.average_success_rate_percent
      currentData.agentHealth = (healthData.system_overview.healthy_agents / 
                                 healthData.system_overview.total_agents) * 100
    }

    return data
  }, [healthData])

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-kenny-gray-800">
          Performance Trends
        </h3>
        <div className="flex items-center space-x-4 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-kenny-primary rounded-full"></div>
            <span className="text-kenny-gray-600">Response Time</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-kenny-success rounded-full"></div>
            <span className="text-kenny-gray-600">Success Rate</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-kenny-warning rounded-full"></div>
            <span className="text-kenny-gray-600">Agent Health</span>
          </div>
        </div>
      </div>

      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
            <XAxis 
              dataKey="timestamp" 
              stroke="#6b7280"
              fontSize={12}
            />
            <YAxis 
              stroke="#6b7280"
              fontSize={12}
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: 'none',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
              formatter={(value: number, name: string) => {
                if (name === 'responseTime') return [`${value.toFixed(0)}ms`, 'Response Time']
                if (name === 'successRate') return [`${value.toFixed(1)}%`, 'Success Rate']
                if (name === 'agentHealth') return [`${value.toFixed(1)}%`, 'Agent Health']
                return [value, name]
              }}
            />
            <Line 
              type="monotone" 
              dataKey="responseTime" 
              stroke="#667eea" 
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#667eea' }}
            />
            <Line 
              type="monotone" 
              dataKey="successRate" 
              stroke="#27ae60" 
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#27ae60' }}
            />
            <Line 
              type="monotone" 
              dataKey="agentHealth" 
              stroke="#f39c12" 
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#f39c12' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-4 text-center">
        <div className="p-3 bg-kenny-primary/10 rounded-lg">
          <div className="text-sm text-kenny-gray-600">Avg Response</div>
          <div className="text-lg font-semibold text-kenny-primary">
            {healthData?.performance_overview?.average_response_time_ms?.toFixed(0) || '--'}ms
          </div>
        </div>
        <div className="p-3 bg-kenny-success/10 rounded-lg">
          <div className="text-sm text-kenny-gray-600">Success Rate</div>
          <div className="text-lg font-semibold text-kenny-success">
            {healthData?.performance_overview?.average_success_rate_percent?.toFixed(1) || '--'}%
          </div>
        </div>
        <div className="p-3 bg-kenny-warning/10 rounded-lg">
          <div className="text-sm text-kenny-gray-600">Agent Health</div>
          <div className="text-lg font-semibold text-kenny-warning">
            {healthData?.system_overview ? 
              ((healthData.system_overview.healthy_agents / healthData.system_overview.total_agents) * 100).toFixed(0) 
              : '--'}%
          </div>
        </div>
      </div>
    </div>
  )
}