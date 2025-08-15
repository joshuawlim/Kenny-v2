// Minimal App component for testing
import React from 'react';
import { Routes, Route, useNavigate, useLocation, Outlet } from 'react-router-dom';
import { ChatInterface } from './ChatInterface';

// Simple components without complex dependencies
const SimpleAppShell = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const navItems = [
    { path: '/', icon: '📊', label: 'Dashboard' },
    { path: '/chat', icon: '💬', label: 'Chat' },
    { path: '/agents', icon: '🤖', label: 'Agents' },
    { path: '/health', icon: '❤️', label: 'Health' },
    { path: '/security', icon: '🔒', label: 'Security' }
  ];

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: '#081f1a',
      color: 'white',
      fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif'
    }}>
      {/* Sidebar */}
      <div style={{
        width: '240px',
        background: 'rgba(255, 255, 255, 0.06)',
        padding: '20px',
        borderRight: '1px solid rgba(255, 255, 255, 0.12)'
      }}>
        <div style={{marginBottom: '30px'}}>
          <h2 style={{margin: '0 0 10px 0', fontSize: '18px'}}>Kenny v2</h2>
          <p style={{margin: 0, fontSize: '14px', opacity: 0.7}}>Dashboard</p>
        </div>
        
        <nav>
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <div
                key={item.path}
                onClick={() => navigate(item.path)}
                style={{
                  padding: '10px 15px',
                  color: isActive ? 'white' : 'rgba(255,255,255,0.7)',
                  backgroundColor: isActive ? 'rgba(20, 184, 138, 0.2)' : 'transparent',
                  borderRadius: '8px',
                  marginBottom: '5px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </div>
            );
          })}
        </nav>
      </div>
      
      {/* Main Content */}
      <div style={{
        flex: 1,
        padding: '30px',
        background: 'radial-gradient(1200px 800px at 30% -10%, #0e3b2e 0%, #0a2a22 60%, #081f1a 100%)'
      }}>
        <Outlet />
      </div>
    </div>
  );
};

const SimpleDashboard = () => {
  const [systemData, setSystemData] = React.useState({
    status: 'Loading...',
    agents: 0,
    healthyAgents: 0,
    responseTime: '...',
    gatewayHealth: 'Unknown',
    registryHealth: 'Unknown'
  });

  React.useEffect(() => {
    const fetchSystemData = async () => {
      try {
        // Fetch data from Kenny APIs via Vite proxy
        const [gatewayResponse, registryResponse] = await Promise.allSettled([
          fetch('/api/health').then(r => r.json()).catch(() => null),
          fetch('/registry/agents').then(r => r.json()).catch(() => null)
        ]);

        const gatewayHealth = gatewayResponse.status === 'fulfilled' && gatewayResponse.value;
        const registryData = registryResponse.status === 'fulfilled' && registryResponse.value;

        // registryData is an array of agents, not an object with agents property
        const agentCount = Array.isArray(registryData) ? registryData.length : 0;
        const healthyAgents = Array.isArray(registryData) ? 
          registryData.filter(agent => agent.is_healthy).length : 0;

        setSystemData({
          status: gatewayHealth ? 'Online' : 'Partial',
          agents: agentCount,
          healthyAgents,
          responseTime: gatewayHealth?.response_time_ms ? `${gatewayHealth.response_time_ms}ms` : 'N/A',
          gatewayHealth: gatewayHealth ? 'Online' : 'Offline',
          registryHealth: registryData ? 'Online' : 'Offline'
        });
      } catch (error) {
        console.error('Failed to fetch system data:', error);
        setSystemData({
          status: 'Error',
          agents: 0,
          healthyAgents: 0,
          responseTime: 'N/A',
          gatewayHealth: 'Error',
          registryHealth: 'Error'
        });
      }
    };

    fetchSystemData();
    const interval = setInterval(fetchSystemData, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'Online': return '#14b88a';
      case 'Partial': return '#f39c12';
      case 'Error': case 'Offline': return '#e74c3c';
      default: return '#95a5a6';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'Online': return '✅';
      case 'Partial': return '⚠️';
      case 'Error': case 'Offline': return '❌';
      default: return '⏳';
    }
  };

  return (
    <div>
      <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '30px'}}>
        Kenny v2 Dashboard
      </h1>
      
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
          padding: '24px'
        }}>
          <h3>System Status</h3>
          <div style={{fontSize: '24px', color: getStatusColor(systemData.status)}}>
            {getStatusIcon(systemData.status)} {systemData.status}
          </div>
          <div style={{fontSize: '12px', opacity: 0.7, marginTop: '10px'}}>
            Gateway: {systemData.gatewayHealth} • Registry: {systemData.registryHealth}
          </div>
        </div>
        
        <div style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '24px'
        }}>
          <h3>Active Agents</h3>
          <div style={{fontSize: '24px', color: '#3498db'}}>🤖 {systemData.agents}</div>
          <div style={{fontSize: '12px', opacity: 0.7, marginTop: '10px'}}>
            {systemData.healthyAgents} healthy • {systemData.agents - systemData.healthyAgents} unhealthy
          </div>
        </div>
        
        <div style={{
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '24px'
        }}>
          <h3>Response Time</h3>
          <div style={{fontSize: '24px', color: '#f39c12'}}>⚡ {systemData.responseTime}</div>
          <div style={{fontSize: '12px', opacity: 0.7, marginTop: '10px'}}>
            Gateway health check
          </div>
        </div>
      </div>

      <div style={{
        background: 'rgba(255, 255, 255, 0.06)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '12px',
        padding: '24px',
        marginTop: '20px'
      }}>
        <h3 style={{margin: '0 0 15px 0'}}>Quick Actions</h3>
        <div style={{display: 'flex', gap: '10px', flexWrap: 'wrap'}}>
          <button
            onClick={() => window.open('/registry/system/health/dashboard', '_blank')}
            style={{
              padding: '8px 16px',
              background: 'rgba(20, 184, 138, 0.2)',
              border: '1px solid rgba(20, 184, 138, 0.3)',
              borderRadius: '6px',
              color: 'white',
              cursor: 'pointer'
            }}
          >
            🔍 System Health
          </button>
          <button
            onClick={() => fetch('/api/agents').then(r => r.json()).then(data => alert(JSON.stringify(data, null, 2)))}
            style={{
              padding: '8px 16px',
              background: 'rgba(52, 152, 219, 0.2)',
              border: '1px solid rgba(52, 152, 219, 0.3)',
              borderRadius: '6px',
              color: 'white',
              cursor: 'pointer'
            }}
          >
            🤖 List Agents
          </button>
        </div>
      </div>
    </div>
  );
};

const SimpleChat = () => (
  <div>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Chat Interface</h1>
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px',
      textAlign: 'center'
    }}>
      <p>💬 Chat with Kenny v2</p>
      <p style={{opacity: 0.7}}>Real-time AI conversation interface</p>
    </div>
  </div>
);

const SimpleAgents = () => (
  <div>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Agent Management</h1>
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px'
    }}>
      <p>🤖 Managing 8 active agents</p>
      <ul style={{marginTop: '15px', paddingLeft: '20px'}}>
        <li>📧 Mail Agent - Processing emails</li>
        <li>📅 Calendar Agent - Managing schedules</li>
        <li>💬 Chat Agent - Handling conversations</li>
        <li>🔍 Search Agent - Finding information</li>
      </ul>
    </div>
  </div>
);

const SimpleHealth = () => (
  <div>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>System Health</h1>
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px'
    }}>
      <p>❤️ All systems are healthy</p>
      <div style={{marginTop: '20px'}}>
        <div>✅ API Gateway: Online</div>
        <div>✅ Agent Registry: Online</div>
        <div>✅ Coordinator: Online</div>
        <div>✅ Database: Online</div>
      </div>
    </div>
  </div>
);

const SimpleSecurity = () => (
  <div>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Security Center</h1>
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px'
    }}>
      <p>🔒 Security monitoring active</p>
      <div style={{marginTop: '20px'}}>
        <div>🛡️ Threat Level: Low</div>
        <div>🔐 Encryption: Active</div>
        <div>🚨 Active Alerts: 0</div>
      </div>
    </div>
  </div>
);

function App() {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'radial-gradient(1200px 800px at 30% -10%, #0e3b2e 0%, #0a2a22 60%, #081f1a 100%)',
    }}>
      <Routes>
        <Route path="/" element={<SimpleAppShell />}>
          <Route index element={<SimpleDashboard />} />
          <Route path="chat" element={<ChatInterface />} />
          <Route path="agents" element={<SimpleAgents />} />
          <Route path="health" element={<SimpleHealth />} />
          <Route path="security" element={<SimpleSecurity />} />
        </Route>
      </Routes>
    </div>
  );
}

export default App;