import type { Meta, StoryObj } from '@storybook/react';
import React, { useState } from 'react';

// Complete App Layout Component
interface AppLayoutProps {
  initialPage?: string;
}

const AppLayout: React.FC<AppLayoutProps> = ({ initialPage = '/' }) => {
  const [currentPage, setCurrentPage] = useState(initialPage);
  
  const navItems = [
    { path: '/', icon: '📊', label: 'Dashboard' },
    { path: '/chat', icon: '💬', label: 'Chat' },
    { path: '/agents', icon: '🤖', label: 'Agents' },
    { path: '/query', icon: '🔍', label: 'Query' },
    { path: '/health', icon: '❤️', label: 'Health' },
    { path: '/security', icon: '🔒', label: 'Security' }
  ];

  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const renderPageContent = () => {
    switch (currentPage) {
      case '/':
        return (
          <div style={{color: 'white'}}>
            <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '30px'}}>System Dashboard</h1>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
              gap: '20px',
              marginBottom: '30px'
            }}>
              <div style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '12px',
                padding: '24px',
                backdropFilter: 'blur(20px)'
              }}>
                <div style={{display: 'flex', alignItems: 'center', marginBottom: '15px'}}>
                  <div style={{
                    width: '40px', height: '40px', borderRadius: '10px',
                    background: 'rgba(20, 184, 138, 0.2)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', marginRight: '15px'
                  }}>✅</div>
                  <div>
                    <h3 style={{margin: 0, fontSize: '16px', fontWeight: 600}}>System Status</h3>
                    <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>All systems operational</p>
                  </div>
                </div>
                <div style={{fontSize: '24px', fontWeight: 600, color: '#14b88a'}}>Online</div>
              </div>
              <div style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '12px',
                padding: '24px',
                backdropFilter: 'blur(20px)'
              }}>
                <div style={{display: 'flex', alignItems: 'center', marginBottom: '15px'}}>
                  <div style={{
                    width: '40px', height: '40px', borderRadius: '10px',
                    background: 'rgba(52, 152, 219, 0.2)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', marginRight: '15px'
                  }}>🤖</div>
                  <div>
                    <h3 style={{margin: 0, fontSize: '16px', fontWeight: 600}}>Active Agents</h3>
                    <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>Currently running</p>
                  </div>
                </div>
                <div style={{fontSize: '24px', fontWeight: 600, color: '#3498db'}}>8</div>
              </div>
            </div>
          </div>
        );
      case '/chat':
        return (
          <div style={{color: 'white'}}>
            <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Chat Interface</h1>
            <div style={{
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '12px',
              padding: '24px',
              backdropFilter: 'blur(20px)'
            }}>
              <p>💬 Multi-agent chat interface</p>
              <div style={{
                background: 'rgba(20, 184, 138, 0.1)',
                padding: '12px',
                borderRadius: '8px',
                marginTop: '15px'
              }}>
                <strong>Kenny:</strong> Hello! How can I help you today?
              </div>
            </div>
          </div>
        );
      case '/agents':
        return (
          <div style={{color: 'white'}}>
            <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Agent Management</h1>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
              gap: '15px'
            }}>
              {['📧 Mail Agent', '📅 Calendar Agent', '💬 Chat Agent', '🔍 Search Agent'].map((agent, index) => (
                <div key={index} style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '12px',
                  padding: '20px',
                  backdropFilter: 'blur(20px)'
                }}>
                  <h3 style={{margin: 0, fontSize: '16px'}}>{agent}</h3>
                  <div style={{marginTop: '10px', display: 'flex', alignItems: 'center', gap: '8px'}}>
                    <span style={{width: '8px', height: '8px', borderRadius: '50%', background: '#14b88a'}}></span>
                    <span style={{fontSize: '12px', opacity: 0.7}}>Online</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      case '/health':
        return (
          <div style={{color: 'white'}}>
            <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>System Health</h1>
            <div style={{
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(20, 184, 138, 0.3)',
              borderRadius: '12px',
              padding: '24px',
              backdropFilter: 'blur(20px)'
            }}>
              <div style={{display: 'flex', alignItems: 'center', gap: '15px'}}>
                <div style={{fontSize: '32px'}}>❤️</div>
                <div>
                  <h2 style={{margin: 0, fontSize: '24px', color: '#14b88a'}}>All Systems Healthy</h2>
                  <p style={{margin: 0, opacity: 0.7}}>Last updated: 2 minutes ago</p>
                </div>
              </div>
            </div>
          </div>
        );
      case '/security':
        return (
          <div style={{color: 'white'}}>
            <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Security Center</h1>
            <div style={{
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(20, 184, 138, 0.3)',
              borderRadius: '12px',
              padding: '24px',
              backdropFilter: 'blur(20px)'
            }}>
              <div style={{display: 'flex', alignItems: 'center', gap: '15px'}}>
                <div style={{fontSize: '32px'}}>🛡️</div>
                <div>
                  <h2 style={{margin: 0, fontSize: '24px', color: '#14b88a'}}>Threat Level: Low</h2>
                  <p style={{margin: 0, opacity: 0.7}}>No active threats detected</p>
                </div>
              </div>
            </div>
          </div>
        );
      default:
        return <div style={{color: 'white'}}>Page not found</div>;
    }
  };

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: '#081f1a',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Sidebar */}
      <div style={{
        width: '240px',
        background: 'rgba(255, 255, 255, 0.06)',
        padding: '20px',
        borderRight: '1px solid rgba(255, 255, 255, 0.12)',
        backdropFilter: 'blur(20px)'
      }}>
        <div style={{color: 'white', marginBottom: '30px'}}>
          <h2 style={{margin: '0 0 10px 0', fontSize: '18px', fontWeight: 600}}>Kenny v2</h2>
          <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>Dashboard</p>
        </div>
        
        <nav>
          {navItems.map((item) => {
            const isActive = currentPage === item.path;
            const isHovered = hoveredItem === item.path;
            
            return (
              <div
                key={item.path}
                onClick={() => setCurrentPage(item.path)}
                onMouseEnter={() => setHoveredItem(item.path)}
                onMouseLeave={() => setHoveredItem(null)}
                style={{
                  padding: '10px 15px',
                  color: isActive ? 'white' : 'rgba(255,255,255,0.7)',
                  backgroundColor: isActive 
                    ? 'rgba(20, 184, 138, 0.2)' 
                    : isHovered 
                      ? 'rgba(255, 255, 255, 0.1)' 
                      : 'transparent',
                  borderRadius: '8px',
                  marginBottom: '5px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  border: isActive ? '1px solid rgba(20, 184, 138, 0.3)' : '1px solid transparent'
                }}
              >
                <span>{item.icon}</span>
                <span style={{ fontWeight: isActive ? 600 : 400 }}>{item.label}</span>
              </div>
            );
          })}
        </nav>
        
        {/* Status Footer */}
        <div style={{
          position: 'absolute',
          bottom: '20px',
          left: '20px',
          right: '260px',
          padding: '15px',
          background: 'rgba(255, 255, 255, 0.03)',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: 'rgba(255, 255, 255, 0.6)',
            fontSize: '12px'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#14b88a'
            }}></span>
            All systems operational
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div style={{
        flex: 1,
        padding: '30px',
        background: 'radial-gradient(1200px 800px at 30% -10%, #0e3b2e 0%, #0a2a22 60%, #081f1a 100%)',
        overflow: 'auto'
      }}>
        {renderPageContent()}
      </div>
    </div>
  );
};

const meta = {
  title: 'App/Complete Layout',
  component: AppLayout,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'Complete Kenny dashboard layout with sidebar navigation and page content. Fully interactive navigation between all sections.'
      }
    }
  },
  argTypes: {
    initialPage: {
      control: 'select',
      options: ['/', '/chat', '/agents', '/query', '/health', '/security'],
      description: 'Which page to start on'
    }
  }
} satisfies Meta<typeof AppLayout>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Dashboard: Story = {
  args: {
    initialPage: '/'
  },
  parameters: {
    docs: {
      description: {
        story: 'Complete Kenny dashboard starting on the main dashboard page. Try clicking the sidebar items to navigate!'
      }
    }
  }
};

export const ChatView: Story = {
  args: {
    initialPage: '/chat'
  },
  parameters: {
    docs: {
      description: {
        story: 'Kenny dashboard starting on the chat interface page.'
      }
    }
  }
};

export const AgentsView: Story = {
  args: {
    initialPage: '/agents'
  },
  parameters: {
    docs: {
      description: {
        story: 'Kenny dashboard starting on the agents management page.'
      }
    }
  }
};

export const HealthView: Story = {
  args: {
    initialPage: '/health'
  },
  parameters: {
    docs: {
      description: {
        story: 'Kenny dashboard starting on the system health page.'
      }
    }
  }
};

export const SecurityView: Story = {
  args: {
    initialPage: '/security'
  },
  parameters: {
    docs: {
      description: {
        story: 'Kenny dashboard starting on the security center page.'
      }
    }
  }
};