import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Typography,
  Avatar,
  Paper,
  Popover,
  Chip,
  Tooltip,
  Fab,
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachIcon,
  Info as InfoIcon,
  MoreVert as MoreIcon,
  KeyboardVoice as VoiceIcon,
} from '@mui/icons-material';
import { useSpring, animated, useTransition } from '@react-spring/web';
import { format } from 'date-fns';

// Message interfaces
interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'kenny';
  timestamp: Date;
  status?: 'sending' | 'sent' | 'delivered' | 'read';
  attachments?: string[];
}

interface ChatBubbleProps {
  message: ChatMessage;
  isLast: boolean;
}

// CSS-in-JS styles for iMessage-like bubbles
const getBubbleStyles = (sender: 'user' | 'kenny', isLast: boolean) => ({
  maxWidth: '70%',
  margin: sender === 'user' ? '4px 8px 4px auto' : '4px auto 4px 8px',
  padding: '12px 16px',
  borderRadius: sender === 'user' 
    ? '20px 20px 6px 20px' 
    : '20px 20px 20px 6px',
  background: sender === 'user'
    ? 'linear-gradient(135deg, #0e3b2e 0%, #14b88a 100%)'
    : 'rgba(255, 255, 255, 0.1)',
  color: 'white',
  position: 'relative',
  wordBreak: 'break-word',
  backdropFilter: 'blur(10px)',
  border: sender === 'kenny' ? '1px solid rgba(255, 255, 255, 0.15)' : 'none',
  
  // Bubble tail using pseudo-element
  '&::after': isLast ? {
    content: '""',
    position: 'absolute',
    bottom: 0,
    [sender === 'user' ? 'right' : 'left']: -8,
    width: 0,
    height: 0,
    borderStyle: 'solid',
    borderWidth: sender === 'user' ? '8px 8px 0 0' : '8px 0 0 8px',
    borderColor: sender === 'user' 
      ? '#14b88a transparent transparent transparent'
      : 'rgba(255, 255, 255, 0.1) transparent transparent transparent',
  } : {},
});

const ChatBubble: React.FC<ChatBubbleProps> = ({ message, isLast }) => {
  const [showTimestamp, setShowTimestamp] = useState(false);
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);

  // Animation for bubble entrance
  const bubbleSpring = useSpring({
    from: { opacity: 0, transform: 'scale(0.8) translateY(20px)' },
    to: { opacity: 1, transform: 'scale(1) translateY(0px)' },
    config: { tension: 300, friction: 20 },
  });

  // Animation for timestamp
  const timestampSpring = useSpring({
    opacity: showTimestamp ? 1 : 0,
    transform: showTimestamp ? 'translateY(0px)' : 'translateY(-10px)',
    config: { tension: 200, friction: 15 },
  });

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setShowTimestamp(!showTimestamp);
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setShowTimestamp(false);
    setAnchorEl(null);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: message.sender === 'user' ? 'row-reverse' : 'row',
        alignItems: 'flex-end',
        mb: 1,
      }}
    >
      {/* Avatar (only for Kenny) */}
      {message.sender === 'kenny' && (
        <Avatar
          sx={{
            width: 24,
            height: 24,
            mr: 1,
            background: 'linear-gradient(135deg, #0e3b2e, #14b88a)',
            fontSize: '0.75rem',
          }}
        >
          K
        </Avatar>
      )}

      {/* Message Bubble */}
      <animated.div style={bubbleSpring}>
        <Paper
          onClick={handleClick}
          sx={{
            ...getBubbleStyles(message.sender, isLast),
            cursor: 'pointer',
            transition: 'all 0.1s ease-in-out',
            '&:hover': {
              transform: 'scale(1.01)',
            },
            '&:active': {
              transform: 'scale(0.99)',
            },
          }}
          elevation={message.sender === 'user' ? 2 : 1}
        >
          <Typography variant="body1" sx={{ fontSize: '0.95rem', lineHeight: 1.4 }}>
            {message.content}
          </Typography>
        </Paper>

        {/* Timestamp Popover */}
        <Popover
          open={showTimestamp}
          anchorEl={anchorEl}
          onClose={handleClose}
          anchorOrigin={{
            vertical: 'top',
            horizontal: message.sender === 'user' ? 'right' : 'left',
          }}
          transformOrigin={{
            vertical: 'bottom',
            horizontal: message.sender === 'user' ? 'right' : 'left',
          }}
          sx={{ pointerEvents: 'none' }}
        >
          <animated.div style={timestampSpring}>
            <Box sx={{ p: 1 }}>
              <Typography variant="caption" color="text.secondary">
                {format(message.timestamp, 'MMM d, h:mm a')}
              </Typography>
              {message.status && (
                <Chip
                  label={message.status}
                  size="small"
                  color={message.status === 'read' ? 'success' : 'default'}
                  sx={{ ml: 1, height: 16, fontSize: '0.6rem' }}
                />
              )}
            </Box>
          </animated.div>
        </Popover>
      </animated.div>
    </Box>
  );
};

// Input bar component
interface ChatInputProps {
  onSendMessage: (content: string) => void;
  disabled?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, disabled = false }) => {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    // TODO: Implement voice recording
  };

  const canSend = input.trim() && !disabled;

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        position: 'sticky',
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(20px)',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        p: 2,
        zIndex: 1000,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1 }}>
        {/* Voice Recording Button */}
        <IconButton
          onClick={toggleRecording}
          size="small"
          sx={{
            color: isRecording ? 'error.main' : 'text.secondary',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
            },
          }}
          aria-label={isRecording ? 'Stop recording' : 'Start voice recording'}
        >
          <VoiceIcon />
        </IconButton>

        {/* Text Input */}
        <TextField
          fullWidth
          multiline
          maxRows={4}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Message Kenny..."
          disabled={disabled}
          variant="outlined"
          sx={{
            '& .MuiOutlinedInput-root': {
              background: 'rgba(255, 255, 255, 0.05)',
              borderRadius: '24px',
              paddingRight: 1,
              '& fieldset': {
                border: '1px solid rgba(255, 255, 255, 0.2)',
              },
              '&:hover fieldset': {
                borderColor: 'rgba(255, 255, 255, 0.3)',
              },
              '&.Mui-focused fieldset': {
                borderColor: 'primary.light',
              },
            },
            '& .MuiInputBase-input': {
              padding: '12px 16px',
              color: 'text.primary',
              '&::placeholder': {
                color: 'text.secondary',
                opacity: 0.7,
              },
            },
          }}
        />

        {/* Attach File Button */}
        <IconButton
          size="small"
          sx={{
            color: 'text.secondary',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
            },
          }}
          aria-label="Attach file"
        >
          <AttachIcon />
        </IconButton>

        {/* Send Button */}
        <IconButton
          type="submit"
          disabled={!canSend}
          sx={{
            backgroundColor: canSend ? 'primary.main' : 'rgba(255, 255, 255, 0.1)',
            color: canSend ? 'white' : 'text.disabled',
            width: 40,
            height: 40,
            '&:hover': {
              backgroundColor: canSend ? 'primary.dark' : 'rgba(255, 255, 255, 0.1)',
              transform: 'scale(1.05)',
            },
            '&:active': {
              transform: 'scale(0.95)',
            },
            '&.Mui-disabled': {
              color: 'text.disabled',
            },
          }}
          aria-label="Send message"
        >
          <SendIcon />
        </IconButton>
      </Box>
    </Box>
  );
};

// Main Chat component
export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: 'Hi! I\'m Kenny, your AI assistant. How can I help you today?',
      sender: 'kenny',
      timestamp: new Date(Date.now() - 300000),
      status: 'read',
    },
  ]);
  const [infoOpen, setInfoOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Animate messages on mount
  const transitions = useTransition(messages, {
    from: { opacity: 0, transform: 'translateY(20px)' },
    enter: { opacity: 1, transform: 'translateY(0px)' },
    config: { tension: 200, friction: 20 },
  });

  const handleSendMessage = (content: string) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content,
      sender: 'user',
      timestamp: new Date(),
      status: 'sending',
    };

    setMessages(prev => [...prev, userMessage]);

    // TODO: Send to Kenny API and get response
    // Simulate Kenny response
    setTimeout(() => {
      const kennyResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: `I understand you said "${content}". Let me help you with that!`,
        sender: 'kenny',
        timestamp: new Date(),
        status: 'delivered',
      };
      setMessages(prev => [...prev, kennyResponse]);
    }, 1000);
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Chat Header */}
      <Box
        sx={{
          p: 2,
          background: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar sx={{ 
            background: 'linear-gradient(135deg, #0e3b2e, #14b88a)',
            width: 32,
            height: 32,
          }}>
            K
          </Avatar>
          <Box>
            <Typography variant="h6">Kenny</Typography>
            <Typography variant="caption" color="text.secondary">
              AI Assistant • Online
            </Typography>
          </Box>
        </Box>

        <Tooltip title="Chat info">
          <IconButton
            onClick={() => setInfoOpen(!infoOpen)}
            aria-label="Show chat information"
          >
            <InfoIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Messages Container */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          py: 2,
          px: 1,
        }}
      >
        {messages.map((message, index) => (
          <ChatBubble
            key={message.id}
            message={message}
            isLast={index === messages.length - 1 || 
              messages[index + 1]?.sender !== message.sender}
          />
        ))}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Bar */}
      <ChatInput onSendMessage={handleSendMessage} />

      {/* Floating Action Button for Quick Actions */}
      {infoOpen && (
        <Fab
          size="small"
          color="primary"
          sx={{ position: 'fixed', bottom: 100, right: 24 }}
          onClick={() => setInfoOpen(false)}
          aria-label="Hide chat info"
        >
          <MoreIcon />
        </Fab>
      )}
    </Box>
  );
};