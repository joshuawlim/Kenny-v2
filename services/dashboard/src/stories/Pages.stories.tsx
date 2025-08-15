import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

// Page Components
const ChatPage = () => (
  <div style={{color: 'white'}}>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Chat Interface</h1>
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px',
      backdropFilter: 'blur(20px)',
      marginBottom: '20px'
    }}>
      <p>💬 Multi-agent chat interface coming soon...</p>
      <p style={{opacity: 0.7}}>This will be your central hub for communicating with Kenny's agents.</p>
    </div>
    
    {/* Mock Chat Interface */}
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px',
      backdropFilter: 'blur(20px)',
      height: '400px',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{ flex: 1, marginBottom: '20px', padding: '10px' }}>
        <div style={{
          background: 'rgba(20, 184, 138, 0.1)',
          padding: '12px',
          borderRadius: '8px',
          marginBottom: '10px',
          border: '1px solid rgba(20, 184, 138, 0.2)'
        }}>
          <strong>Kenny:</strong> Hello! How can I help you today?
        </div>
        <div style={{
          background: 'rgba(52, 152, 219, 0.1)',
          padding: '12px',
          borderRadius: '8px',
          marginLeft: '20px',
          border: '1px solid rgba(52, 152, 219, 0.2)'
        }}>
          <strong>You:</strong> Check my calendar for tomorrow
        </div>
      </div>
      <div style={{
        display: 'flex',
        gap: '10px',
        padding: '10px',
        background: 'rgba(255, 255, 255, 0.03)',
        borderRadius: '8px'
      }}>
        <input 
          style={{
            flex: 1,
            padding: '10px',
            background: 'rgba(255, 255, 255, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '6px',
            color: 'white'
          }}
          placeholder="Type your message..."
        />
        <button style={{
          padding: '10px 20px',
          background: '#14b88a',
          border: 'none',
          borderRadius: '6px',
          color: 'white',
          cursor: 'pointer'
        }}>
          Send
        </button>
      </div>
    </div>
  </div>
);

const AgentsPage = () => (
  <div style={{color: 'white'}}>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Agent Management</h1>
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
      gap: '20px'
    }}>
      {[
        { name: 'Mail Agent', icon: '📧', status: 'online', activity: 'Processing emails' },
        { name: 'Calendar Agent', icon: '📅', status: 'online', activity: 'Managing schedules' },
        { name: 'Chat Agent', icon: '💬', status: 'online', activity: 'Handling conversations' },
        { name: 'Search Agent', icon: '🔍', status: 'online', activity: 'Finding information' },
        { name: 'Note Agent', icon: '📝', status: 'idle', activity: 'Managing documents' },
        { name: 'Web Agent', icon: '🌐', status: 'online', activity: 'Browsing and research' },
        { name: 'Sync Agent', icon: '🔄', status: 'online', activity: 'Data synchronization' },
        { name: 'Security Agent', icon: '🛡️', status: 'online', activity: 'Monitoring threats' }
      ].map((agent, index) => (
        <div key={index} style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px',
          backdropFilter: 'blur(20px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
            <span style={{ fontSize: '32px', marginRight: '15px' }}>{agent.icon}</span>
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>{agent.name}</h3>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px',
                marginTop: '5px'
              }}>
                <span style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: agent.status === 'online' ? '#14b88a' : '#f39c12'
                }}></span>
                <span style={{ 
                  fontSize: '12px', 
                  opacity: 0.7,
                  textTransform: 'capitalize'
                }}>
                  {agent.status}
                </span>
              </div>
            </div>
          </div>
          <p style={{ margin: 0, fontSize: '14px', opacity: 0.8 }}>{agent.activity}</p>
        </div>
      ))}
    </div>
  </div>
);

const HealthPage = () => (
  <div style={{color: 'white'}}>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>System Health</h1>
    
    {/* Overall Status */}
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(20, 184, 138, 0.3)',
      borderRadius: '12px',
      padding: '24px',
      backdropFilter: 'blur(20px)',
      marginBottom: '20px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
        <div style={{
          width: '50px',
          height: '50px',
          borderRadius: '25px',
          background: 'rgba(20, 184, 138, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px'
        }}>
          ❤️
        </div>
        <div>
          <h2 style={{ margin: 0, fontSize: '24px', color: '#14b88a' }}>All Systems Healthy</h2>
          <p style={{ margin: 0, opacity: 0.7 }}>Last updated: 2 minutes ago</p>
        </div>
      </div>
    </div>

    {/* Service Status Grid */}
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
      gap: '15px'
    }}>
      {[
        { name: 'API Gateway', status: 'healthy', uptime: '99.9%' },
        { name: 'Agent Registry', status: 'healthy', uptime: '99.8%' },
        { name: 'Coordinator', status: 'healthy', uptime: '99.9%' },
        { name: 'Database', status: 'healthy', uptime: '100%' },
        { name: 'Memory Store', status: 'healthy', uptime: '99.7%' },
        { name: 'File Storage', status: 'healthy', uptime: '99.9%' }
      ].map((service, index) => (
        <div key={index} style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '8px',
          padding: '16px',
          backdropFilter: 'blur(20px)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontWeight: 600 }}>{service.name}</span>
            <span style={{
              padding: '4px 8px',
              background: 'rgba(20, 184, 138, 0.2)',
              borderRadius: '4px',
              fontSize: '12px',
              color: '#14b88a'
            }}>
              ✅ {service.status}
            </span>
          </div>
          <div style={{ fontSize: '14px', opacity: 0.7 }}>
            Uptime: {service.uptime}
          </div>
        </div>
      ))}
    </div>
  </div>
);

const SecurityPage = () => (
  <div style={{color: 'white'}}>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Security Center</h1>
    
    {/* Threat Level */}
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(20, 184, 138, 0.3)',
      borderRadius: '12px',
      padding: '24px',
      backdropFilter: 'blur(20px)',
      marginBottom: '20px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
        <div style={{
          width: '50px',
          height: '50px',
          borderRadius: '25px',
          background: 'rgba(20, 184, 138, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px'
        }}>
          🛡️
        </div>
        <div>
          <h2 style={{ margin: 0, fontSize: '24px', color: '#14b88a' }}>Threat Level: Low</h2>
          <p style={{ margin: 0, opacity: 0.7 }}>No active threats detected</p>
        </div>
      </div>
    </div>

    {/* Security Metrics */}
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '15px',
      marginBottom: '20px'
    }}>
      {[
        { icon: '🔐', label: 'Encryption', value: 'Active', color: '#14b88a' },
        { icon: '🚨', label: 'Active Alerts', value: '0', color: '#14b88a' },
        { icon: '🔍', label: 'Last Scan', value: '2 min ago', color: '#14b88a' },
        { icon: '🔒', label: 'Failed Logins', value: '0 today', color: '#14b88a' }
      ].map((metric, index) => (
        <div key={index} style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '8px',
          padding: '20px',
          backdropFilter: 'blur(20px)',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '24px', marginBottom: '10px' }}>{metric.icon}</div>
          <div style={{ fontSize: '18px', fontWeight: 600, color: metric.color, marginBottom: '5px' }}>
            {metric.value}
          </div>
          <div style={{ fontSize: '14px', opacity: 0.7 }}>{metric.label}</div>
        </div>
      ))}
    </div>

    {/* Recent Security Events */}
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px',
      backdropFilter: 'blur(20px)'
    }}>
      <h3 style={{ margin: '0 0 15px 0', fontSize: '18px', fontWeight: 600 }}>Recent Security Events</h3>
      <div>
        {[
          { type: 'success', message: 'Security scan completed successfully', time: '2 minutes ago' },
          { type: 'info', message: 'Encryption keys rotated', time: '1 hour ago' },
          { type: 'success', message: 'All authentication attempts successful', time: '3 hours ago' }
        ].map((event, index) => (
          <div key={index} style={{
            display: 'flex',
            alignItems: 'center',
            padding: '10px 0',
            borderBottom: index < 2 ? '1px solid rgba(255, 255, 255, 0.1)' : 'none'
          }}>
            <span style={{
              marginRight: '15px',
              fontSize: '16px'
            }}>
              {event.type === 'success' ? '✅' : 'ℹ️'}
            </span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '14px' }}>{event.message}</div>
              <div style={{ fontSize: '12px', opacity: 0.6 }}>{event.time}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

// Combined component for story organization
const PageShowcase: React.FC<{ page: string }> = ({ page }) => {
  switch (page) {
    case 'chat':
      return <ChatPage />;
    case 'agents':
      return <AgentsPage />;
    case 'health':
      return <HealthPage />;
    case 'security':
      return <SecurityPage />;
    default:
      return <div>Select a page to preview</div>;
  }
};

const meta = {
  title: 'Pages/All Pages',
  component: PageShowcase,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'Collection of all Kenny dashboard pages with their unique content and layouts.'
      }
    }
  },
  argTypes: {
    page: {
      control: 'select',
      options: ['chat', 'agents', 'health', 'security'],
      description: 'Select which page to display'
    }
  }
} satisfies Meta<typeof PageShowcase>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ChatInterface: Story = {
  args: {
    page: 'chat'
  },
  parameters: {
    docs: {
      description: {
        story: 'Multi-agent chat interface with mock conversation and input field.'
      }
    }
  }
};

export const AgentManagement: Story = {
  args: {
    page: 'agents'
  },
  parameters: {
    docs: {
      description: {
        story: 'Agent management page showing all 8 active agents with their status.'
      }
    }
  }
};

export const SystemHealth: Story = {
  args: {
    page: 'health'
  },
  parameters: {
    docs: {
      description: {
        story: 'System health monitoring with service status and uptime metrics.'
      }
    }
  }
};

export const SecurityCenter: Story = {
  args: {
    page: 'security'
  },
  parameters: {
    docs: {
      description: {
        story: 'Security monitoring dashboard with threat levels and recent events.'
      }
    }
  }
};