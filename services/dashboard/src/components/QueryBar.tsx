import React, { useState, useCallback, useRef } from 'react';
import {
  Box,
  InputBase,
  IconButton,
  Paper,
  Tooltip,
  Typography,
  Chip,
} from '@mui/material';
import {
  Send as SendIcon,
  Mic as MicIcon,
  Stop as StopIcon,
} from '@mui/icons-material';
import { useSpring, animated } from '@react-spring/web';

interface QueryBarProps {
  onSubmit?: (query: string) => void;
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
}

export const QueryBar: React.FC<QueryBarProps> = ({
  onSubmit,
  placeholder = 'Ask Kenny anything...',
  disabled = false,
  loading = false,
}) => {
  const [query, setQuery] = useState('');
  const [isListening, setIsListening] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Animation for the entire query bar
  const barSpring = useSpring({
    scale: loading ? 1.02 : 1,
    boxShadow: loading
      ? '0 8px 32px rgba(20, 184, 138, 0.15)'
      : '0 4px 20px rgba(0, 0, 0, 0.1)',
    config: { tension: 200, friction: 20 },
  });

  // Animation for the send button
  const [sendSpring, sendApi] = useSpring(() => ({
    scale: 1,
    rotate: 0,
    config: { tension: 300, friction: 10 },
  }));

  const handleSubmit = useCallback((e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim() || disabled || loading) return;

    // Trigger send animation
    sendApi.start({
      scale: 1.2,
      rotate: 15,
      config: { tension: 400, friction: 8 },
    });

    setTimeout(() => {
      sendApi.start({
        scale: 1,
        rotate: 0,
        config: { tension: 300, friction: 10 },
      });
    }, 150);

    onSubmit?.(query.trim());
    setQuery('');
  }, [query, disabled, loading, onSubmit, sendApi]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (e.metaKey || e.ctrlKey) {
        handleSubmit();
      }
    }
  };

  const toggleListening = () => {
    // TODO: Implement speech recognition
    setIsListening(!isListening);
  };

  const canSubmit = query.trim() && !disabled && !loading;

  return (
    <animated.div style={barSpring}>
      <Paper
        component="form"
        onSubmit={handleSubmit}
        sx={{
          display: 'flex',
          alignItems: 'center',
          width: '100%',
          maxWidth: 600,
          height: 56,
          background: 'rgba(255, 255, 255, 0.08)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: 3,
          px: 2,
          py: 1,
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            background: 'rgba(255, 255, 255, 0.12)',
            borderColor: 'rgba(255, 255, 255, 0.2)',
          },
          '&:focus-within': {
            background: 'rgba(255, 255, 255, 0.12)',
            borderColor: 'primary.light',
            boxShadow: '0 0 0 2px rgba(20, 184, 138, 0.2)',
          },
        }}
        elevation={0}
      >
        {/* Main Input */}
        <InputBase
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          sx={{
            flex: 1,
            fontSize: '1rem',
            color: 'text.primary',
            '& input': {
              padding: 0,
            },
            '& input::placeholder': {
              color: 'text.secondary',
              opacity: 0.7,
            },
          }}
          inputProps={{
            'aria-label': 'Query input',
            'aria-describedby': 'query-shortcut-hint',
          }}
        />

        {/* Keyboard Shortcut Hint */}
        {!query && (
          <Chip
            id="query-shortcut-hint"
            label="⌘+Enter"
            size="small"
            variant="outlined"
            sx={{
              height: 24,
              fontSize: '0.75rem',
              borderColor: 'rgba(255, 255, 255, 0.2)',
              color: 'text.secondary',
              mr: 1,
              '& .MuiChip-label': {
                px: 1,
              },
            }}
          />
        )}

        {/* Voice Input Button */}
        <Tooltip title={isListening ? 'Stop listening' : 'Voice input'}>
          <IconButton
            onClick={toggleListening}
            disabled={disabled}
            size="small"
            sx={{
              mr: 0.5,
              color: isListening ? 'error.main' : 'text.secondary',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
              },
            }}
            aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
          >
            {isListening ? <StopIcon /> : <MicIcon />}
          </IconButton>
        </Tooltip>

        {/* Send Button */}
        <Tooltip title="Send query (⌘+Enter)">
          <span>
            <animated.div style={sendSpring}>
              <IconButton
                type="submit"
                disabled={!canSubmit}
                size="small"
                sx={{
                  backgroundColor: canSubmit ? 'primary.main' : 'rgba(255, 255, 255, 0.1)',
                  color: canSubmit ? 'white' : 'text.disabled',
                  '&:hover': {
                    backgroundColor: canSubmit ? 'primary.dark' : 'rgba(255, 255, 255, 0.1)',
                  },
                  '&.Mui-disabled': {
                    color: 'text.disabled',
                  },
                }}
                aria-label="Send query"
              >
                <SendIcon fontSize="small" />
              </IconButton>
            </animated.div>
          </span>
        </Tooltip>
      </Paper>

      {/* Loading indicator */}
      {loading && (
        <Box sx={{ mt: 1, textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Processing your request...
          </Typography>
        </Box>
      )}
    </animated.div>
  );
};