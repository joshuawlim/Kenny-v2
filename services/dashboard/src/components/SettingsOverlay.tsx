import React, { useState } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Tabs,
  Tab,
  Switch,
  FormControlLabel,
  TextField,
  Button,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Card,
  CardContent,
  Chip,
  Alert,
} from '@mui/material';
import {
  Close as CloseIcon,
  Settings as GeneralIcon,
  Psychology as AgentsIcon,
  Security as SecurityIcon,
  Cable as IntegrationsIcon,
  Code as AdvancedIcon,
  Notifications,
  DarkMode,
  Language,
  Storage,
  Key,
  Shield,
  CloudSync,
  Api,
  Memory,
} from '@mui/icons-material';

interface SettingsOverlayProps {
  open: boolean;
  onClose: () => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

export const SettingsOverlay: React.FC<SettingsOverlayProps> = ({ open, onClose }) => {
  const [tabValue, setTabValue] = useState(0);

  // TODO: Connect to real settings state management
  const [settings, setSettings] = useState({
    theme: 'dark',
    notifications: true,
    autoSave: true,
    language: 'en',
    apiTimeout: 30000,
    maxMemory: 1024,
    debugMode: false,
    apiKey: '',
    encryptionEnabled: true,
    backupEnabled: true,
  });

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    // TODO: Persist settings to backend
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      sx={{
        '& .MuiDrawer-paper': {
          width: { xs: '100%', sm: 480, md: 520 },
          background: 'rgba(255, 255, 255, 0.08)',
          backdropFilter: 'blur(20px)',
        },
      }}
    >
      <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box sx={{ 
          p: 3, 
          pb: 0,
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          borderBottom: 1,
          borderColor: 'divider',
        }}>
          <Typography variant="h5" component="h2">
            Settings
          </Typography>
          <IconButton onClick={onClose} aria-label="Close settings">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Tabs */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            aria-label="Settings tabs"
          >
            <Tab
              icon={<GeneralIcon />}
              label="General"
              id="settings-tab-0"
              aria-controls="settings-tabpanel-0"
            />
            <Tab
              icon={<AgentsIcon />}
              label="Agents"
              id="settings-tab-1"
              aria-controls="settings-tabpanel-1"
            />
            <Tab
              icon={<SecurityIcon />}
              label="Security"
              id="settings-tab-2"
              aria-controls="settings-tabpanel-2"
            />
            <Tab
              icon={<IntegrationsIcon />}
              label="Integrations"
              id="settings-tab-3"
              aria-controls="settings-tabpanel-3"
            />
            <Tab
              icon={<AdvancedIcon />}
              label="Advanced"
              id="settings-tab-4"
              aria-controls="settings-tabpanel-4"
            />
          </Tabs>
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, overflow: 'auto', px: 3 }}>
          {/* General Settings */}
          <TabPanel value={tabValue} index={0}>
            <Typography variant="h6" gutterBottom>
              General Settings
            </Typography>
            
            <List>
              <ListItem>
                <ListItemIcon>
                  <DarkMode />
                </ListItemIcon>
                <ListItemText
                  primary="Dark Mode"
                  secondary="Use dark theme across the interface"
                />
                <ListItemSecondaryAction>
                  <Switch
                    checked={settings.theme === 'dark'}
                    onChange={(e) => handleSettingChange('theme', e.target.checked ? 'dark' : 'light')}
                  />
                </ListItemSecondaryAction>
              </ListItem>

              <ListItem>
                <ListItemIcon>
                  <Notifications />
                </ListItemIcon>
                <ListItemText
                  primary="Notifications"
                  secondary="Enable desktop notifications"
                />
                <ListItemSecondaryAction>
                  <Switch
                    checked={settings.notifications}
                    onChange={(e) => handleSettingChange('notifications', e.target.checked)}
                  />
                </ListItemSecondaryAction>
              </ListItem>

              <ListItem>
                <ListItemIcon>
                  <Storage />
                </ListItemIcon>
                <ListItemText
                  primary="Auto Save"
                  secondary="Automatically save changes"
                />
                <ListItemSecondaryAction>
                  <Switch
                    checked={settings.autoSave}
                    onChange={(e) => handleSettingChange('autoSave', e.target.checked)}
                  />
                </ListItemSecondaryAction>
              </ListItem>

              <ListItem>
                <ListItemIcon>
                  <Language />
                </ListItemIcon>
                <ListItemText primary="Language" />
                <TextField
                  select
                  size="small"
                  value={settings.language}
                  onChange={(e) => handleSettingChange('language', e.target.value)}
                  SelectProps={{ native: true }}
                  sx={{ minWidth: 120 }}
                >
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                </TextField>
              </ListItem>
            </List>
          </TabPanel>

          {/* Agents Settings */}
          <TabPanel value={tabValue} index={1}>
            <Typography variant="h6" gutterBottom>
              Agent Configuration
            </Typography>
            
            <Alert severity="info" sx={{ mb: 2 }}>
              Configure agent behavior and performance settings
            </Alert>

            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  Active Agents
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {['Calendar', 'Email', 'iMessage', 'WhatsApp', 'Memory'].map((agent) => (
                    <Chip 
                      key={agent}
                      label={agent}
                      color="primary"
                      variant="outlined"
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>

            <TextField
              fullWidth
              label="API Timeout (ms)"
              type="number"
              value={settings.apiTimeout}
              onChange={(e) => handleSettingChange('apiTimeout', parseInt(e.target.value))}
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              label="Max Memory Usage (MB)"
              type="number"
              value={settings.maxMemory}
              onChange={(e) => handleSettingChange('maxMemory', parseInt(e.target.value))}
              sx={{ mb: 2 }}
            />
          </TabPanel>

          {/* Security Settings */}
          <TabPanel value={tabValue} index={2}>
            <Typography variant="h6" gutterBottom>
              Security & Privacy
            </Typography>

            <List>
              <ListItem>
                <ListItemIcon>
                  <Shield />
                </ListItemIcon>
                <ListItemText
                  primary="End-to-End Encryption"
                  secondary="Encrypt all data in transit and at rest"
                />
                <ListItemSecondaryAction>
                  <Switch
                    checked={settings.encryptionEnabled}
                    onChange={(e) => handleSettingChange('encryptionEnabled', e.target.checked)}
                  />
                </ListItemSecondaryAction>
              </ListItem>

              <ListItem>
                <ListItemIcon>
                  <CloudSync />
                </ListItemIcon>
                <ListItemText
                  primary="Automatic Backups"
                  secondary="Regularly backup your data"
                />
                <ListItemSecondaryAction>
                  <Switch
                    checked={settings.backupEnabled}
                    onChange={(e) => handleSettingChange('backupEnabled', e.target.checked)}
                  />
                </ListItemSecondaryAction>
              </ListItem>
            </List>

            <Divider sx={{ my: 2 }} />

            <TextField
              fullWidth
              label="API Key"
              type="password"
              value={settings.apiKey}
              onChange={(e) => handleSettingChange('apiKey', e.target.value)}
              helperText="Secure API key for external integrations"
              sx={{ mb: 2 }}
            />

            <Button variant="outlined" color="error" fullWidth>
              Reset Security Settings
            </Button>
          </TabPanel>

          {/* Integrations Settings */}
          <TabPanel value={tabValue} index={3}>
            <Typography variant="h6" gutterBottom>
              External Integrations
            </Typography>

            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Api sx={{ mr: 1 }} />
                  <Typography variant="subtitle1">
                    API Endpoints
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Configure external API connections and webhooks
                </Typography>
              </CardContent>
            </Card>

            <List>
              <ListItem>
                <ListItemText
                  primary="Calendar Integration"
                  secondary="Connect to calendar services"
                />
                <Chip label="Connected" color="success" size="small" />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Email Integration"
                  secondary="Connect to email providers"
                />
                <Chip label="Connected" color="success" size="small" />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Messaging Integration"
                  secondary="Connect to messaging platforms"
                />
                <Chip label="Pending" color="warning" size="small" />
              </ListItem>
            </List>
          </TabPanel>

          {/* Advanced Settings */}
          <TabPanel value={tabValue} index={4}>
            <Typography variant="h6" gutterBottom>
              Advanced Configuration
            </Typography>

            <Alert severity="warning" sx={{ mb: 2 }}>
              These settings are for advanced users only. Incorrect values may affect system performance.
            </Alert>

            <List>
              <ListItem>
                <ListItemIcon>
                  <Code />
                </ListItemIcon>
                <ListItemText
                  primary="Debug Mode"
                  secondary="Enable verbose logging and debug features"
                />
                <ListItemSecondaryAction>
                  <Switch
                    checked={settings.debugMode}
                    onChange={(e) => handleSettingChange('debugMode', e.target.checked)}
                  />
                </ListItemSecondaryAction>
              </ListItem>

              <ListItem>
                <ListItemIcon>
                  <Memory />
                </ListItemIcon>
                <ListItemText
                  primary="Memory Management"
                  secondary="Configure garbage collection and memory limits"
                />
              </ListItem>
            </List>

            <Box sx={{ mt: 3 }}>
              <Button variant="outlined" color="warning" fullWidth sx={{ mb: 1 }}>
                Export Configuration
              </Button>
              <Button variant="outlined" color="info" fullWidth sx={{ mb: 1 }}>
                Import Configuration
              </Button>
              <Button variant="outlined" color="error" fullWidth>
                Reset All Settings
              </Button>
            </Box>
          </TabPanel>
        </Box>

        {/* Footer */}
        <Box sx={{ p: 3, borderTop: 1, borderColor: 'divider' }}>
          <Button
            variant="contained"
            fullWidth
            onClick={() => {
              // TODO: Save all settings
              onClose();
            }}
          >
            Save Changes
          </Button>
        </Box>
      </Box>
    </Drawer>
  );
};