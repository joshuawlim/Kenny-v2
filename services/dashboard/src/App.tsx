// Main App component with routing
import React from 'react';
import { Routes, Route, useNavigate, useLocation, Outlet } from 'react-router-dom';
import { ThemeProvider } from './theme';

// Create error boundary component for debugging
class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: any}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error('Dashboard Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{padding: '20px', color: 'white', background: '#e74c3c', minHeight: '100vh'}}>
          <h1>Dashboard Error</h1>
          <p>Something went wrong: {String(this.state.error)}</p>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Simplified components for testing
const SimpleAppShell = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const navItems = [
    { path: '/', icon: '📊', label: 'Dashboard' },
    { path: '/chat', icon: '💬', label: 'Chat' },
    { path: '/agents', icon: '🤖', label: 'Agents' },
    { path: '/query', icon: '🔍', label: 'Query' },
    { path: '/health', icon: '❤️', label: 'Health' },
    { path: '/security', icon: '🔒', label: 'Security' }
  ];

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: '#081f1a'
    }}>
      {/* Sidebar */}
      <div style={{
        width: '240px',
        background: 'rgba(255, 255, 255, 0.06)',
        padding: '20px',
        borderRight: '1px solid rgba(255, 255, 255, 0.12)'
      }}>
        <div style={{color: 'white', marginBottom: '30px'}}>
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
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }
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

// Create placeholder page components
const ChatPage = () => (
  <div style={{color: 'white'}}>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Chat Interface</h1>
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px',
      backdropFilter: 'blur(20px)'
    }}>
      <p>💬 Multi-agent chat interface coming soon...</p>
      <p style={{opacity: 0.7}}>This will be your central hub for communicating with Kenny's agents.</p>
    </div>
  </div>
);

const AgentsPage = () => (
  <div style={{color: 'white'}}>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Agent Management</h1>
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px',
      backdropFilter: 'blur(20px)'
    }}>
      <p>🤖 Currently managing 8 active agents:</p>
      <ul style={{margin: '15px 0', paddingLeft: '20px'}}>
        <li>📧 Mail Agent - Processing emails</li>
        <li>📅 Calendar Agent - Managing schedules</li>
        <li>💬 Chat Agent - Handling conversations</li>
        <li>🔍 Search Agent - Finding information</li>
        <li>📝 Note Agent - Managing documents</li>
        <li>🌐 Web Agent - Browsing and research</li>
        <li>🔄 Sync Agent - Data synchronization</li>
        <li>🛡️ Security Agent - Monitoring threats</li>
      </ul>
    </div>
  </div>
);

const QueryPage = () => (
  <div style={{color: 'white'}}>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Query Interface</h1>
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px',
      backdropFilter: 'blur(20px)'
    }}>
      <p>🔍 Advanced query interface for Kenny's knowledge base</p>
      <p style={{opacity: 0.7}}>Search across all your data sources and get intelligent responses.</p>
    </div>
  </div>
);

const HealthPage = () => (
  <div style={{color: 'white'}}>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>System Health</h1>
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px',
      backdropFilter: 'blur(20px)'
    }}>
      <p>❤️ All systems are healthy</p>
      <div style={{marginTop: '20px'}}>
        <div style={{margin: '10px 0'}}>✅ API Gateway: Online</div>
        <div style={{margin: '10px 0'}}>✅ Agent Registry: Online</div>
        <div style={{margin: '10px 0'}}>✅ Coordinator: Online</div>
        <div style={{margin: '10px 0'}}>✅ Database: Online</div>
        <div style={{margin: '10px 0'}}>✅ Memory Store: Online</div>
      </div>
    </div>
  </div>
);

const SecurityPage = () => (
  <div style={{color: 'white'}}>
    <h1 style={{fontSize: '32px', fontWeight: 600, marginBottom: '20px'}}>Security Center</h1>
    <div style={{
      background: 'rgba(255, 255, 255, 0.06)',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      borderRadius: '12px',
      padding: '24px',
      backdropFilter: 'blur(20px)'
    }}>
      <p>🔒 Security monitoring and threat detection</p>
      <div style={{marginTop: '20px'}}>
        <div style={{margin: '10px 0'}}>🛡️ Threat Level: Low</div>
        <div style={{margin: '10px 0'}}>🔐 Encryption: Active</div>
        <div style={{margin: '10px 0'}}>🚨 Active Alerts: 0</div>
        <div style={{margin: '10px 0'}}>🔍 Last Scan: 2 minutes ago</div>
      </div>
    </div>
  </div>
);

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <Routes>
          <Route path="/" element={<SimpleAppShell />}>
            <Route index element={<SimpleDashboard />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="agents" element={<AgentsPage />} />
            <Route path="query" element={<QueryPage />} />
            <Route path="health" element={<HealthPage />} />
            <Route path="security" element={<SecurityPage />} />
          </Route>
        </Routes>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;