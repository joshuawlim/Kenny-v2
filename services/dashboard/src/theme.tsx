import { createTheme, ThemeProvider as MUIThemeProvider, CssBaseline, Box } from '@mui/material';
import { ReactNode } from 'react';

// Kenny color tokens
const kennyColors = {
  primary: {
    main: '#0e3b2e',
    dark: '#0a2a22',
    light: '#14b88a',
  },
  surface: 'rgba(255, 255, 255, 0.06)',
  border: 'rgba(255, 255, 255, 0.12)',
  backgroundGradient: 'radial-gradient(1200px 800px at 30% -10%, #0e3b2e 0%, #0a2a22 60%, #081f1a 100%)',
};

// Create MUI theme with Kenny design system
export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: kennyColors.primary,
    background: {
      default: '#081f1a',
      paper: kennyColors.surface,
    },
    divider: kennyColors.border,
    text: {
      primary: 'rgba(255, 255, 255, 0.95)',
      secondary: 'rgba(255, 255, 255, 0.70)',
    },
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: { fontWeight: 600 },
    h2: { fontWeight: 600 },
    h3: { fontWeight: 600 },
    body1: { fontWeight: 400 },
    body2: { fontWeight: 400 },
  },
  spacing: 8, // 8px base unit
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          background: kennyColors.backgroundGradient,
          minHeight: '100vh',
          fontSmooth: 'antialiased',
        },
        '*:focus-visible': {
          outline: `2px solid ${kennyColors.primary.light}`,
          outlineOffset: '2px',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          background: kennyColors.surface,
          backdropFilter: 'blur(20px)',
          borderRight: `1px solid ${kennyColors.border}`,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: kennyColors.surface,
          backdropFilter: 'blur(20px)',
          boxShadow: 'none',
          borderBottom: `1px solid ${kennyColors.border}`,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          background: kennyColors.surface,
          backdropFilter: 'blur(20px)',
          border: `1px solid ${kennyColors.border}`,
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
          },
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          transition: 'all 0.15s ease-in-out',
          '&:hover': {
            transform: 'scale(1.06)',
            backgroundColor: 'rgba(255, 255, 255, 0.08)',
          },
          '&:active': {
            transform: 'scale(0.98)',
          },
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          background: kennyColors.surface,
          backdropFilter: 'blur(20px)',
          border: `1px solid ${kennyColors.border}`,
          fontSize: '0.875rem',
        },
      },
    },
  },
});

interface ThemeProviderProps {
  children: ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  return (
    <MUIThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        sx={{
          minHeight: '100vh',
          background: kennyColors.backgroundGradient,
        }}
      >
        {children}
      </Box>
    </MUIThemeProvider>
  );
};

export { kennyColors };