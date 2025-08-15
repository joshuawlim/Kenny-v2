import type { Preview } from '@storybook/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '../src/theme';
import '../src/index.css';

// Create a query client for Storybook
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,
      cacheTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
});

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
    docs: {
      theme: {
        base: 'dark',
        colorPrimary: '#14b88a',
        colorSecondary: '#0e3b2e',
        appBg: '#081f1a',
        appContentBg: '#0a2a22',
        appBorderColor: 'rgba(255, 255, 255, 0.12)',
        textColor: 'rgba(255, 255, 255, 0.95)',
        textInverseColor: '#081f1a',
        barTextColor: 'rgba(255, 255, 255, 0.7)',
        barSelectedColor: '#14b88a',
        barBg: 'rgba(255, 255, 255, 0.06)',
        inputBg: 'rgba(255, 255, 255, 0.06)',
        inputBorder: 'rgba(255, 255, 255, 0.12)',
        inputTextColor: 'rgba(255, 255, 255, 0.95)',
        inputBorderRadius: 8,
      },
    },
    backgrounds: {
      default: 'kenny-dark',
      values: [
        {
          name: 'kenny-dark',
          value: 'radial-gradient(1200px 800px at 30% -10%, #0e3b2e 0%, #0a2a22 60%, #081f1a 100%)',
        },
        {
          name: 'kenny-solid',
          value: '#081f1a',
        },
        {
          name: 'white',
          value: '#ffffff',
        },
      ],
    },
  },
  decorators: [
    (Story) => (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ThemeProvider>
            <div style={{ 
              minHeight: '100vh', 
              background: 'radial-gradient(1200px 800px at 30% -10%, #0e3b2e 0%, #0a2a22 60%, #081f1a 100%)',
              padding: '20px'
            }}>
              <Story />
            </div>
          </ThemeProvider>
        </BrowserRouter>
      </QueryClientProvider>
    ),
  ],
};

export default preview;