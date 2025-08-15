// Reusable metric card component
import React from 'react'
import { LucideIcon } from 'lucide-react'
import clsx from 'clsx'

interface MetricCardProps {
  title: string
  value: string | number
  description?: string
  icon: LucideIcon
  trend?: {
    value: number
    isPositive: boolean
    label: string
  }
  status?: 'success' | 'warning' | 'error' | 'info'
  className?: string
  loading?: boolean
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  description,
  icon: Icon,
  trend,
  status = 'info',
  className,
  loading = false,
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'success': return 'text-kenny-success'
      case 'warning': return 'text-kenny-warning'
      case 'error': return 'text-kenny-error'
      default: return 'text-kenny-info'
    }
  }

  const getIconBackgroundColor = () => {
    switch (status) {
      case 'success': return 'bg-kenny-success/10'
      case 'warning': return 'bg-kenny-warning/10'
      case 'error': return 'bg-kenny-error/10'
      default: return 'bg-kenny-info/10'
    }
  }

  return (
    <div className={clsx('metric-card', className)}>
      <div className="flex items-center justify-between mb-4">
        <div className={clsx('p-3 rounded-xl', getIconBackgroundColor())}>
          <Icon className={clsx('w-6 h-6', getStatusColor())} />
        </div>
        
        {trend && (
          <div className={clsx(
            'flex items-center space-x-1 text-sm font-medium',
            trend.isPositive ? 'text-kenny-success' : 'text-kenny-error'
          )}>
            <span>{trend.isPositive ? '↗' : '↘'}</span>
            <span>{Math.abs(trend.value)}%</span>
          </div>
        )}
      </div>

      <div>
        <h3 className="text-sm font-medium text-kenny-gray-600 mb-2">
          {title}
        </h3>
        
        {loading ? (
          <div className="animate-pulse">
            <div className="h-8 bg-kenny-gray-200 rounded w-16 mb-2"></div>
            {description && (
              <div className="h-4 bg-kenny-gray-200 rounded w-24"></div>
            )}
          </div>
        ) : (
          <>
            <div className={clsx('text-3xl font-bold mb-1', getStatusColor())}>
              {value}
            </div>
            {description && (
              <p className="text-sm text-kenny-gray-500">
                {description}
              </p>
            )}
            {trend && (
              <p className="text-xs text-kenny-gray-500 mt-1">
                {trend.label}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}