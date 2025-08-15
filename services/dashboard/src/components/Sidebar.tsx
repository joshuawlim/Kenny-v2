import React from 'react';
import { Box, IconButton, Tooltip, useTheme } from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Chat as ChatIcon,
  Psychology as AgentsIcon,
  Security as SecurityIcon,
  Analytics as AnalyticsIcon,
  HealthAndSafety as HealthIcon,
  Timeline as TracesIcon,
  Warning as AlertsIcon,
  Search as QueryIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useSpring, animated } from '@react-spring/web';

interface NavItem {
  icon: React.ReactNode;
  route: string;
  label: string;
  ariaLabel: string;
}

const navItems: NavItem[] = [
  {
    icon: <DashboardIcon />,
    route: '/',
    label: 'Dashboard',
    ariaLabel: 'Go to Dashboard',
  },
  {
    icon: <QueryIcon />,
    route: '/query',
    label: 'Query',
    ariaLabel: 'Go to Query interface',
  },
  {
    icon: <ChatIcon />,
    route: '/chat',
    label: 'Chat',
    ariaLabel: 'Go to Chat',
  },
  {
    icon: <AgentsIcon />,
    route: '/agents',
    label: 'Agents',
    ariaLabel: 'Go to Agents management',
  },
  {
    icon: <SecurityIcon />,
    route: '/security',
    label: 'Security',
    ariaLabel: 'Go to Security dashboard',
  },
  {
    icon: <AnalyticsIcon />,
    route: '/analytics',
    label: 'Analytics',
    ariaLabel: 'Go to Analytics',
  },
  {
    icon: <HealthIcon />,
    route: '/health',
    label: 'Health',
    ariaLabel: 'Go to System Health',
  },
  {
    icon: <TracesIcon />,
    route: '/traces',
    label: 'Traces',
    ariaLabel: 'Go to Request Traces',
  },
  {
    icon: <AlertsIcon />,
    route: '/alerts',
    label: 'Alerts',
    ariaLabel: 'Go to Alerts',
  },
];

interface AnimatedNavItemProps {
  item: NavItem;
  isActive: boolean;
  onClick: () => void;
}

const AnimatedNavItem: React.FC<AnimatedNavItemProps> = ({ item, isActive, onClick }) => {
  const theme = useTheme();
  const [springs, api] = useSpring(() => ({
    scale: 1,
    y: 0,
    config: { tension: 220, friction: 18 },
  }));

  const activePillSpring = useSpring({
    opacity: isActive ? 1 : 0,
    scale: isActive ? 1 : 0.8,
    config: { tension: 300, friction: 20 },
  });

  return (
    <Box sx={{ position: 'relative', mb: 1 }}>
      {/* Active indicator pill */}
      <animated.div
        style={{
          ...activePillSpring,
          position: 'absolute',
          top: 4,
          left: 4,
          right: 4,
          bottom: 4,
          background: theme.palette.primary.main,
          borderRadius: theme.shape.borderRadius,
          zIndex: 0,
        }}
      />
      
      <Tooltip
        title={item.label}
        placement="right"
        arrow
        enterDelay={300}
        enterNextDelay={300}
      >
        <animated.div style={springs}>
          <IconButton
            onClick={onClick}
            aria-label={item.ariaLabel}
            sx={{
              width: 56,
              height: 56,
              position: 'relative',
              zIndex: 1,
              color: isActive ? 'white' : 'text.primary',
              '&:hover': {
                backgroundColor: isActive ? 'transparent' : 'rgba(255, 255, 255, 0.08)',
              },
            }}
            onMouseEnter={() => {
              api.start({ scale: 1.06, y: -2 });
            }}
            onMouseLeave={() => {
              api.start({ scale: 1, y: 0 });
            }}
            onMouseDown={() => {
              api.start({ scale: 0.98, y: 0 });
            }}
            onMouseUp={() => {
              api.start({ scale: 1.06, y: -2 });
            }}
          >
            {item.icon}
          </IconButton>
        </animated.div>
      </Tooltip>
    </Box>
  );
};

interface SidebarProps {
  onItemClick?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onItemClick }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();

  const handleNavigation = (route: string) => {
    navigate(route);
    onItemClick?.();
  };

  const isActive = (route: string) => {
    if (route === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(route);
  };

  return (
    <Box
      sx={{
        width: '100%',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        py: 3,
        borderRight: `1px solid ${theme.palette.divider}`,
        background: 'rgba(255, 255, 255, 0.02)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Kenny Logo/Brand */}
      <Box
        sx={{
          width: 40,
          height: 40,
          background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.light})`,
          borderRadius: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          mb: 4,
          fontSize: '1.25rem',
          fontWeight: 'bold',
          color: 'white',
        }}
      >
        K
      </Box>

      {/* Navigation Items */}
      <Box sx={{ flex: 1, width: '100%' }}>
        {navItems.map((item) => (
          <AnimatedNavItem
            key={item.route}
            item={item}
            isActive={isActive(item.route)}
            onClick={() => handleNavigation(item.route)}
          />
        ))}
      </Box>

      {/* Skip to main content link for accessibility */}
      <Box
        component="a"
        href="#main-content"
        sx={{
          position: 'absolute',
          left: '-9999px',
          top: 0,
          '&:focus': {
            left: 0,
            top: 0,
            zIndex: 9999,
            background: theme.palette.primary.main,
            color: 'white',
            padding: 1,
            textDecoration: 'none',
            borderRadius: 1,
          },
        }}
      >
        Skip to main content
      </Box>
    </Box>
  );
};