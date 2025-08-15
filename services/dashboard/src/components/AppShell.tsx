import React, { useState } from 'react';
import {
  AppBar,
  Box,
  Drawer,
  IconButton,
  Toolbar,
  Typography,
  Popover,
  Chip,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { Settings as SettingsIcon, Circle } from '@mui/icons-material';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { QueryBar } from './QueryBar';
import { SettingsOverlay } from './SettingsOverlay';

const SIDEBAR_WIDTH = 72;

interface StatusIndicatorProps {
  status: 'online' | 'offline' | 'degraded';
  message: string;
  details?: string[];
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status, message, details = [] }) => {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const statusColors = {
    online: '#14b88a',
    degraded: '#f59e0b',
    offline: '#ef4444',
  };

  return (
    <>
      <Chip
        icon={<Circle sx={{ color: statusColors[status], fontSize: '8px !important' }} />}
        label={message}
        size="small"
        onClick={handleClick}
        sx={{
          cursor: 'pointer',
          backgroundColor: 'rgba(255, 255, 255, 0.05)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.08)',
          },
        }}
      />
      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        sx={{
          '& .MuiPaper-root': {
            mt: 1,
            minWidth: 280,
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            System Status
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {message}
          </Typography>
          {details.map((detail, index) => (
            <Typography key={index} variant="caption" display="block" color="text.secondary">
              • {detail}
            </Typography>
          ))}
        </Box>
      </Popover>
    </>
  );
};

export const AppShell: React.FC = () => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // TODO: Connect to real system status
  const systemStatus: StatusIndicatorProps = {
    status: 'online',
    message: 'All systems operational',
    details: [
      'API Gateway: Online',
      'Agent Registry: Online', 
      'Memory Service: Online',
      'Dashboard: Online',
    ],
  };

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <Box
        component="nav"
        sx={{
          width: { md: SIDEBAR_WIDTH },
          flexShrink: { md: 0 },
        }}
      >
        {/* Mobile Drawer */}
        {isMobile && (
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={handleDrawerToggle}
            ModalProps={{
              keepMounted: true, // Better mobile performance
            }}
            sx={{
              '& .MuiDrawer-paper': {
                width: SIDEBAR_WIDTH,
              },
            }}
          >
            <Sidebar onItemClick={() => setMobileOpen(false)} />
          </Drawer>
        )}
        
        {/* Desktop Drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': {
              width: SIDEBAR_WIDTH,
              position: 'fixed',
              height: '100vh',
            },
          }}
        >
          <Sidebar />
        </Drawer>
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${SIDEBAR_WIDTH}px)` },
          ml: { md: `${SIDEBAR_WIDTH}px` },
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* AppBar */}
        <AppBar
          position="fixed"
          sx={{
            width: { md: `calc(100% - ${SIDEBAR_WIDTH}px)` },
            ml: { md: `${SIDEBAR_WIDTH}px` },
            zIndex: theme.zIndex.drawer + 1,
          }}
        >
          <Toolbar sx={{ justifyContent: 'space-between' }}>
            {/* Mobile Menu Button */}
            {isMobile && (
              <IconButton
                color="inherit"
                aria-label="open drawer"
                edge="start"
                onClick={handleDrawerToggle}
              >
                <SettingsIcon />
              </IconButton>
            )}

            {/* Centered Query Bar */}
            <Box sx={{ 
              flex: 1, 
              display: 'flex', 
              justifyContent: 'center',
              px: { xs: 2, md: 8 },
            }}>
              <QueryBar />
            </Box>

            {/* Right Side Actions */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <StatusIndicator {...systemStatus} />
              <IconButton
                color="inherit"
                onClick={() => setSettingsOpen(true)}
                aria-label="Open settings"
              >
                <SettingsIcon />
              </IconButton>
            </Box>
          </Toolbar>
        </AppBar>

        {/* Content Area */}
        <Box
          sx={{
            flexGrow: 1,
            pt: 8, // Account for AppBar height
            px: { xs: 2, md: 4 },
            pb: 4,
          }}
        >
          <Box sx={{ maxWidth: '100%', mx: 'auto', mt: 2 }}>
            <Outlet />
          </Box>
        </Box>
      </Box>

      {/* Settings Overlay */}
      <SettingsOverlay
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </Box>
  );
};