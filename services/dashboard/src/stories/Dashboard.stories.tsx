import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

// Import the dashboard component from our App.tsx
const SimpleDashboard = () => {
  return (
    <div style={{color: 'white'}}>
      <h1 style={{
        fontSize: '32px',
        fontWeight: 600,
        marginBottom: '30px',
        color: 'rgba(255, 255, 255, 0.95)'
      }}>
        System Dashboard
      </h1>
      
      {/* Metrics Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '20px',
        marginBottom: '30px'
      }}>
        {/* System Status Card */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '24px',
          backdropFilter: 'blur(20px)'
        }}>
          <div style={{display: 'flex', alignItems: 'center', marginBottom: '15px'}}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'rgba(20, 184, 138, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '15px'
            }}>
              ✅
            </div>
            <div>
              <h3 style={{margin: 0, fontSize: '16px', fontWeight: 600}}>System Status</h3>
              <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>All systems operational</p>
            </div>
          </div>
          <div style={{fontSize: '24px', fontWeight: 600, color: '#14b88a'}}>Online</div>
        </div>

        {/* Agents Card */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '24px',
          backdropFilter: 'blur(20px)'
        }}>
          <div style={{display: 'flex', alignItems: 'center', marginBottom: '15px'}}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'rgba(52, 152, 219, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '15px'
            }}>
              🤖
            </div>
            <div>
              <h3 style={{margin: 0, fontSize: '16px', fontWeight: 600}}>Active Agents</h3>
              <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>Currently running</p>
            </div>
          </div>
          <div style={{fontSize: '24px', fontWeight: 600, color: '#3498db'}}>8</div>
        </div>

        {/* Performance Card */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '24px',
          backdropFilter: 'blur(20px)'
        }}>
          <div style={{display: 'flex', alignItems: 'center', marginBottom: '15px'}}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'rgba(243, 156, 18, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '15px'
            }}>
              ⚡
            </div>
            <div>
              <h3 style={{margin: 0, fontSize: '16px', fontWeight: 600}}>Response Time</h3>
              <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>Average latency</p>
            </div>
          </div>
          <div style={{fontSize: '24px', fontWeight: 600, color: '#f39c12'}}>145ms</div>
        </div>
      </div>

      {/* Recent Activity */}
      <div style={{
        background: 'rgba(255, 255, 255, 0.06)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '12px',
        padding: '24px',
        backdropFilter: 'blur(20px)'
      }}>
        <h3 style={{margin: '0 0 20px 0', fontSize: '18px', fontWeight: 600}}>Recent Activity</h3>
        <div style={{space: '15px'}}>
          <div style={{
            padding: '12px 0',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            display: 'flex',
            alignItems: 'center'
          }}>
            <span style={{marginRight: '15px', fontSize: '20px'}}>📧</span>
            <div style={{flex: 1}}>
              <div style={{fontSize: '14px'}}>Mail agent processed 12 emails</div>
              <div style={{fontSize: '12px', opacity: 0.6}}>2 minutes ago</div>
            </div>
          </div>
          <div style={{
            padding: '12px 0',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            display: 'flex',
            alignItems: 'center'
          }}>
            <span style={{marginRight: '15px', fontSize: '20px'}}>📅</span>
            <div style={{flex: 1}}>
              <div style={{fontSize: '14px'}}>Calendar sync completed</div>
              <div style={{fontSize: '12px', opacity: 0.6}}>5 minutes ago</div>
            </div>
          </div>
          <div style={{
            padding: '12px 0',
            display: 'flex',
            alignItems: 'center'
          }}>
            <span style={{marginRight: '15px', fontSize: '20px'}}>🔄</span>
            <div style={{flex: 1}}>
              <div style={{fontSize: '14px'}}>System health check passed</div>
              <div style={{fontSize: '12px', opacity: 0.6}}>10 minutes ago</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const meta = {
  title: 'Pages/Dashboard',
  component: SimpleDashboard,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'The main dashboard page showing system overview, metrics, and recent activity.'
      }
    }
  },
} satisfies Meta<typeof SimpleDashboard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  parameters: {
    docs: {
      description: {
        story: 'Default dashboard view with all metrics and activity feed.'
      }
    }
  }
};

export const WithDifferentMetrics: Story = {
  render: () => (
    <div style={{color: 'white'}}>
      <h1 style={{
        fontSize: '32px',
        fontWeight: 600,
        marginBottom: '30px',
        color: 'rgba(255, 255, 255, 0.95)'
      }}>
        System Dashboard
      </h1>
      
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '20px',
        marginBottom: '30px'
      }}>
        {/* System Status Card - Warning */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(243, 156, 18, 0.3)',
          borderRadius: '12px',
          padding: '24px',
          backdropFilter: 'blur(20px)'
        }}>
          <div style={{display: 'flex', alignItems: 'center', marginBottom: '15px'}}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'rgba(243, 156, 18, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '15px'
            }}>
              ⚠️
            </div>
            <div>
              <h3 style={{margin: 0, fontSize: '16px', fontWeight: 600}}>System Status</h3>
              <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>Minor issues detected</p>
            </div>
          </div>
          <div style={{fontSize: '24px', fontWeight: 600, color: '#f39c12'}}>Degraded</div>
        </div>

        {/* Agents Card - More agents */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '24px',
          backdropFilter: 'blur(20px)'
        }}>
          <div style={{display: 'flex', alignItems: 'center', marginBottom: '15px'}}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'rgba(52, 152, 219, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '15px'
            }}>
              🤖
            </div>
            <div>
              <h3 style={{margin: 0, fontSize: '16px', fontWeight: 600}}>Active Agents</h3>
              <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>Currently running</p>
            </div>
          </div>
          <div style={{fontSize: '24px', fontWeight: 600, color: '#3498db'}}>12</div>
        </div>

        {/* Performance Card - Higher latency */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(231, 76, 60, 0.3)',
          borderRadius: '12px',
          padding: '24px',
          backdropFilter: 'blur(20px)'
        }}>
          <div style={{display: 'flex', alignItems: 'center', marginBottom: '15px'}}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'rgba(231, 76, 60, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '15px'
            }}>
              🐌
            </div>
            <div>
              <h3 style={{margin: 0, fontSize: '16px', fontWeight: 600}}>Response Time</h3>
              <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>Higher than usual</p>
            </div>
          </div>
          <div style={{fontSize: '24px', fontWeight: 600, color: '#e74c3c'}}>852ms</div>
        </div>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Dashboard showing warning states and different metrics.'
      }
    }
  }
};