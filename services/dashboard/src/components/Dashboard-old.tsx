import React, { useState } from 'react';
import {
  Grid,
  CardContent,
  Typography,
  Box,
  IconButton,
  Drawer,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Psychology as AgentsIcon,
  Security as SecurityIcon,
  Cable as ConnectionsIcon,
  Close as CloseIcon,
  CheckCircle,
  Warning,
  Error,
  TrendingUp,
  Memory,
  Speed,
} from '@mui/icons-material';
import { AnimatedCard, AnimatedGrid } from './AnimatedPrimitives';

// Mock data interfaces
interface SystemMetric {
  label: string;
  value: number;
  total?: number;
  status: 'success' | 'warning' | 'error';
  change?: string;
}

interface Agent {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'error';
  lastActive: string;
  tasksCompleted: number;
}

interface SecurityAlert {
  id: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  timestamp: string;
}

interface Connection {
  id: string;
  name: string;
  type: string;
  status: 'connected' | 'disconnected';
  latency?: number;
}

// Mock data - TODO: Replace with real API calls
const mockSystemMetrics: SystemMetric[] = [
  { label: 'CPU Usage', value: 45, total: 100, status: 'success', change: '+2%' },
  { label: 'Memory Usage', value: 78, total: 100, status: 'warning', change: '+5%' },
  { label: 'Active Agents', value: 8, status: 'success', change: '+1' },
  { label: 'Requests/sec', value: 1247, status: 'success', change: '+12%' },
];

const mockAgents: Agent[] = [
  { id: '1', name: 'Calendar Agent', status: 'online', lastActive: '2m ago', tasksCompleted: 45 },
  { id: '2', name: 'Email Agent', status: 'online', lastActive: '5m ago', tasksCompleted: 23 },
  { id: '3', name: 'iMessage Agent', status: 'error', lastActive: '1h ago', tasksCompleted: 12 },
  { id: '4', name: 'WhatsApp Agent', status: 'online', lastActive: '1m ago', tasksCompleted: 67 },
];

const mockSecurityAlerts: SecurityAlert[] = [
  { id: '1', severity: 'medium', message: 'Unusual API access pattern detected', timestamp: '10m ago' },
  { id: '2', severity: 'low', message: 'Failed login attempt', timestamp: '1h ago' },
  { id: '3', severity: 'high', message: 'Memory usage threshold exceeded', timestamp: '2h ago' },
];

const mockConnections: Connection[] = [
  { id: '1', name: 'Agent Registry', type: 'Service', status: 'connected', latency: 12 },
  { id: '2', name: 'Memory Store', type: 'Database', status: 'connected', latency: 8 },
  { id: '3', name: 'Gateway', type: 'API', status: 'connected', latency: 25 },
  { id: '4', name: 'External API', type: 'Third Party', status: 'disconnected' },
];

interface DashboardCardProps {
  title: string;
  icon: React.ReactNode;
  onClick?: () => void;
  children: React.ReactNode;
}

const DashboardCard: React.FC<DashboardCardProps> = ({ title, icon, onClick, children }) => (
  <AnimatedCard hoverElevation onClick={onClick}>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Avatar sx={{ bgcolor: 'primary.main', mr: 2, width: 32, height: 32 }}>
          {icon}
        </Avatar>
        <Typography variant="h6" component="h2">
          {title}
        </Typography>
      </Box>
      {children}
    </CardContent>
  </AnimatedCard>
);

interface SideSheetProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

const SideSheet: React.FC<SideSheetProps> = ({ open, title, onClose, children }) => (
  <Drawer
    anchor="right"
    open={open}
    onClose={onClose}
    sx={{
      '& .MuiDrawer-paper': {
        width: { xs: '100%', sm: 400, md: 500 },
        background: 'rgba(255, 255, 255, 0.08)',
        backdropFilter: 'blur(20px)',
      },
    }}
  >
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h5">{title}</Typography>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </Box>
      {children}
    </Box>
  </Drawer>
);

export const Dashboard: React.FC = () => {
  const [activeSheet, setActiveSheet] = useState<string | null>(null);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
      case 'online':
      case 'connected':
        return <CheckCircle color="success" />;
      case 'warning':
        return <Warning color="warning" />;
      case 'error':
      case 'offline':
      case 'disconnected':
        return <Error color="error" />;
      default:
        return <CheckCircle />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Box id="main-content" role="main">
      <Typography variant="h4" component="h1" sx={{ mb: 4, fontWeight: 600 }}>
        System Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* System Summary Card */}
        <Grid item xs={12} md={6}>
          <DashboardCard
            title="System Summary"
            icon={<DashboardIcon />}
            onClick={() => setActiveSheet('system')}
          >
            <Box sx={{ space: 2 }}>
              {mockSystemMetrics.map((metric, index) => (
                <Box key={index} sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">{metric.label}</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2">
                        {metric.value}{metric.total ? `/${metric.total}` : ''}
                      </Typography>
                      {getStatusIcon(metric.status)}
                    </Box>
                  </Box>
                  {metric.total && (
                    <LinearProgress
                      variant="determinate"
                      value={(metric.value / metric.total) * 100}
                      sx={{ height: 4, borderRadius: 2 }}
                    />
                  )}
                </Box>
              ))}
            </Box>
          </DashboardCard>
        </Grid>

        {/* Agents Card */}
        <Grid item xs={12} md={6}>
          <DashboardCard
            title="Active Agents"
            icon={<AgentsIcon />}
            onClick={() => setActiveSheet('agents')}
          >
            <List dense>
              {mockAgents.slice(0, 3).map((agent) => (
                <ListItem key={agent.id} sx={{ px: 0 }}>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    {getStatusIcon(agent.status)}
                  </ListItemIcon>
                  <ListItemText
                    primary={agent.name}
                    secondary={`Last active: ${agent.lastActive}`}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {agent.tasksCompleted} tasks
                  </Typography>
                </ListItem>
              ))}
            </List>
          </DashboardCard>
        </Grid>

        {/* Security Card */}
        <Grid item xs={12} md={6}>
          <DashboardCard
            title="Security & Alerts"
            icon={<SecurityIcon />}
            onClick={() => setActiveSheet('security')}
          >
            <Box>
              {mockSecurityAlerts.slice(0, 3).map((alert) => (
                <Box key={alert.id} sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Chip
                      label={alert.severity.toUpperCase()}
                      size="small"
                      color={getSeverityColor(alert.severity) as any}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {alert.timestamp}
                    </Typography>
                  </Box>
                  <Typography variant="body2">{alert.message}</Typography>
                </Box>
              ))}
            </Box>
          </DashboardCard>
        </Grid>

        {/* Connections Card */}
        <Grid item xs={12} md={6}>
          <DashboardCard
            title="System Connections"
            icon={<ConnectionsIcon />}
            onClick={() => setActiveSheet('connections')}
          >
            <List dense>
              {mockConnections.slice(0, 3).map((connection) => (
                <ListItem key={connection.id} sx={{ px: 0 }}>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    {getStatusIcon(connection.status)}
                  </ListItemIcon>
                  <ListItemText
                    primary={connection.name}
                    secondary={connection.type}
                  />
                  {connection.latency && (
                    <Typography variant="caption" color="text.secondary">
                      {connection.latency}ms
                    </Typography>
                  )}
                </ListItem>
              ))}
            </List>
          </DashboardCard>
        </Grid>
      </Grid>

      {/* Side Sheets */}
      <SideSheet
        open={activeSheet === 'system'}
        title="System Overview"
        onClose={() => setActiveSheet(null)}
      >
        <Typography variant="body1" gutterBottom>
          Detailed system metrics and performance data.
        </Typography>
        {/* TODO: Add detailed system metrics charts */}
      </SideSheet>

      <SideSheet
        open={activeSheet === 'agents'}
        title="Agent Management"
        onClose={() => setActiveSheet(null)}
      >
        <Typography variant="body1" gutterBottom>
          Manage and monitor all active agents.
        </Typography>
        {/* TODO: Add agent management controls */}
      </SideSheet>

      <SideSheet
        open={activeSheet === 'security'}
        title="Security Dashboard"
        onClose={() => setActiveSheet(null)}
      >
        <Typography variant="body1" gutterBottom>
          Security alerts and compliance monitoring.
        </Typography>
        {/* TODO: Add security monitoring tools */}
      </SideSheet>

      <SideSheet
        open={activeSheet === 'connections'}
        title="System Connections"
        onClose={() => setActiveSheet(null)}
      >
        <Typography variant="body1" gutterBottom>
          Monitor all system connections and API endpoints.
        </Typography>
        {/* TODO: Add connection management tools */}
      </SideSheet>
    </Box>
  );
};