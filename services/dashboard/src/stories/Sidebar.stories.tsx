import type { Meta, StoryObj } from '@storybook/react';
import React, { useState } from 'react';

interface SidebarProps {
  activeItem?: string;
  onNavigate?: (path: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeItem = '/', onNavigate = () => {} }) => {
  const navItems = [
    { path: '/', icon: '📊', label: 'Dashboard' },
    { path: '/chat', icon: '💬', label: 'Chat' },
    { path: '/agents', icon: '🤖', label: 'Agents' },
    { path: '/query', icon: '🔍', label: 'Query' },
    { path: '/health', icon: '❤️', label: 'Health' },
    { path: '/security', icon: '🔒', label: 'Security' }
  ];

  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  return (
    <div style={{
      width: '240px',
      background: 'rgba(255, 255, 255, 0.06)',
      padding: '20px',
      borderRight: '1px solid rgba(255, 255, 255, 0.12)',
      backdropFilter: 'blur(20px)',
      height: '100vh'
    }}>
      <div style={{color: 'white', marginBottom: '30px'}}>
        <h2 style={{margin: '0 0 10px 0', fontSize: '18px', fontWeight: 600}}>Kenny v2</h2>
        <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>Dashboard</p>
      </div>
      
      <nav>
        {navItems.map((item) => {
          const isActive = activeItem === item.path;
          const isHovered = hoveredItem === item.path;
          
          return (
            <div
              key={item.path}
              onClick={() => onNavigate(item.path)}
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
      
      {/* Footer */}
      <div style={{
        position: 'absolute',
        bottom: '20px',
        left: '20px',
        right: '20px',
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
            background: '#14b88a',
            animation: 'pulse 2s infinite'
          }}></span>
          All systems operational
        </div>
      </div>
    </div>
  );
};

const meta = {
  title: 'Components/Sidebar',
  component: Sidebar,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'Navigation sidebar with Kenny branding and menu items. Supports active states and hover effects.'
      }
    }
  },
  argTypes: {
    activeItem: {
      control: 'select',
      options: ['/', '/chat', '/agents', '/query', '/health', '/security'],
      description: 'Currently active navigation item'
    },
    onNavigate: {
      action: 'navigate',
      description: 'Callback function when navigation item is clicked'
    }
  }
} satisfies Meta<typeof Sidebar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    activeItem: '/',
  },
  parameters: {
    docs: {
      description: {
        story: 'Default sidebar with Dashboard active.'
      }
    }
  }
};

export const ChatActive: Story = {
  args: {
    activeItem: '/chat',
  },
  parameters: {
    docs: {
      description: {
        story: 'Sidebar with Chat section active.'
      }
    }
  }
};

export const AgentsActive: Story = {
  args: {
    activeItem: '/agents',
  },
  parameters: {
    docs: {
      description: {
        story: 'Sidebar with Agents section active.'
      }
    }
  }
};

export const SecurityActive: Story = {
  args: {
    activeItem: '/security',
  },
  parameters: {
    docs: {
      description: {
        story: 'Sidebar with Security section active.'
      }
    }
  }
};

export const Interactive: Story = {
  render: () => {
    const [activeItem, setActiveItem] = useState('/');
    
    return (
      <Sidebar 
        activeItem={activeItem} 
        onNavigate={(path) => {
          setActiveItem(path);
          console.log('Navigated to:', path);
        }} 
      />
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Interactive sidebar where you can click to change the active item.'
      }
    }
  }
};