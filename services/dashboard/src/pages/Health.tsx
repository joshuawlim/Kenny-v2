// Enhanced Health monitoring page with performance metrics
import React, { useState, useEffect } from 'react'
import { Activity, Database, Clock, TrendingUp, Zap } from 'lucide-react'

interface CacheStats {
  l1_cache: {
    size: number
    max_size: number
    utilization_percent: number
    avg_access_count: number
    avg_age_seconds: number
    ttl_seconds: number
    estimated_memory_mb: number
  }
  performance: {
    eviction_policy: string
    access_weight: number
  }
}

interface PerformanceMetrics {
  cache_hit_rate_percent: number
  estimated_performance_improvement_percent: number
  cache_statistics: CacheStats
  avg_response_time: number
  total_queries: number
  cache_enabled: boolean
  cache_policy: string
}

export const HealthPage: React.FC = () => {
  const [performanceData, setPerformanceData] = useState<Record<string, PerformanceMetrics>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPerformanceMetrics = async () => {
      try {
        // Fetch performance metrics from key intelligent agents
        const agents = ['mail-agent:8000', 'contacts-agent:8003', 'calendar-agent:8007', 'imessage-agent:8006']
        const metrics: Record<string, PerformanceMetrics> = {}
        
        for (const agent of agents) {
          const [name, port] = agent.split(':')
          try {
            const response = await fetch(`http://localhost:${port}/health/performance`)
            if (response.ok) {
              const data = await response.json()
              metrics[name] = data
            }
          } catch (error) {
            console.error(`Failed to fetch metrics for ${name}:`, error)
          }
        }
        
        setPerformanceData(metrics)
      } catch (error) {
        console.error('Error fetching performance metrics:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchPerformanceMetrics()
    const interval = setInterval(fetchPerformanceMetrics, 30000) // Update every 30 seconds
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="text-center py-12">
          <Activity className="w-16 h-16 text-kenny-success mx-auto mb-4 animate-pulse" />
          <h1 className="text-3xl font-bold text-kenny-gray-800 mb-2">Loading Performance Metrics...</h1>
        </div>
      </div>
    )
  }

  const agents = Object.entries(performanceData)

  return (
    <div className="space-y-8">
      <div className="text-center py-8">
        <Activity className="w-16 h-16 text-kenny-success mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-kenny-gray-800 mb-2">
          System Performance & Cache Metrics
        </h1>
        <p className="text-kenny-gray-600 max-w-2xl mx-auto">
          Real-time performance monitoring with enhanced L1 cache statistics for all intelligent agents.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
        {agents.map(([agentName, metrics]) => (
          <div key={agentName} className="bg-white rounded-lg shadow-lg p-6 border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800 capitalize">
                {agentName.replace('-agent', '')} Agent
              </h3>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-sm text-gray-600">Online</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="flex items-center space-x-2">
                <TrendingUp className="w-5 h-5 text-blue-500" />
                <div>
                  <p className="text-xs text-gray-500">Cache Hit Rate</p>
                  <p className="text-lg font-bold text-blue-600">
                    {metrics.cache_hit_rate_percent?.toFixed(1) || '0.0'}%
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Zap className="w-5 h-5 text-green-500" />
                <div>
                  <p className="text-xs text-gray-500">Performance Boost</p>
                  <p className="text-lg font-bold text-green-600">
                    {metrics.estimated_performance_improvement_percent?.toFixed(1) || '0.0'}%
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Clock className="w-5 h-5 text-orange-500" />
                <div>
                  <p className="text-xs text-gray-500">Avg Response</p>
                  <p className="text-lg font-bold text-orange-600">
                    {(metrics.avg_response_time * 1000)?.toFixed(0) || '0'}ms
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Database className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-xs text-gray-500">Cache Size</p>
                  <p className="text-lg font-bold text-purple-600">
                    {metrics.cache_statistics?.l1_cache?.size || 0}/{metrics.cache_statistics?.l1_cache?.max_size || 500}
                  </p>
                </div>
              </div>
            </div>

            {metrics.cache_statistics?.l1_cache && (
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Enhanced L1 Cache Details</h4>
                <div className="text-xs text-gray-600 space-y-1">
                  <div>Utilization: {metrics.cache_statistics.l1_cache.utilization_percent?.toFixed(1)}%</div>
                  <div>TTL: {metrics.cache_statistics.l1_cache.ttl_seconds}s</div>
                  <div>Avg Access: {metrics.cache_statistics.l1_cache.avg_access_count?.toFixed(1)}</div>
                  <div>Memory: ~{metrics.cache_statistics.l1_cache.estimated_memory_mb?.toFixed(1)}MB</div>
                  <div className="font-medium">Policy: {metrics.cache_policy || 'Enhanced LFU-LRU'}</div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {agents.length === 0 && (
        <div className="text-center py-12">
          <Activity className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-600 mb-2">No Performance Data Available</h2>
          <p className="text-gray-500">Intelligent agents may be starting up or unavailable.</p>
        </div>
      )}
    </div>
  )
}