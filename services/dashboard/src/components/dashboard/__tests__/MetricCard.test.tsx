// Test for MetricCard component
import { render, screen } from '@testing-library/react'
import { Activity } from 'lucide-react'
import { MetricCard } from '../MetricCard'

describe('MetricCard', () => {
  it('renders metric card with basic props', () => {
    render(
      <MetricCard
        title="Test Metric"
        value="42"
        description="Test description"
        icon={Activity}
      />
    )

    expect(screen.getByText('Test Metric')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('Test description')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(
      <MetricCard
        title="Test Metric"
        value="42"
        icon={Activity}
        loading={true}
      />
    )

    // Should show loading skeletons
    expect(screen.queryByText('42')).not.toBeInTheDocument()
  })

  it('displays trend information', () => {
    render(
      <MetricCard
        title="Test Metric"
        value="42"
        icon={Activity}
        trend={{
          value: 5.2,
          isPositive: true,
          label: 'vs last hour'
        }}
      />
    )

    expect(screen.getByText('5.2%')).toBeInTheDocument()
    expect(screen.getByText('vs last hour')).toBeInTheDocument()
    expect(screen.getByText('↗')).toBeInTheDocument()
  })

  it('applies correct status styling', () => {
    const { rerender } = render(
      <MetricCard
        title="Test Metric"
        value="42"
        icon={Activity}
        status="success"
      />
    )

    let valueElement = screen.getByText('42')
    expect(valueElement).toHaveClass('text-kenny-success')

    rerender(
      <MetricCard
        title="Test Metric"
        value="42"
        icon={Activity}
        status="error"
      />
    )

    valueElement = screen.getByText('42')
    expect(valueElement).toHaveClass('text-kenny-error')
  })
})