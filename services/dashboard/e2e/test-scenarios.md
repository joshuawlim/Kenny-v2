# Kenny v2 E2E Test Scenarios

## 1. Basic Chat Flow
**Scenario**: User sends a message and receives streaming response
- Navigate to `/chat`
- Type "Hello Kenny" in input field
- Press Cmd+Enter
- Verify streaming tokens appear
- Verify token count updates
- Verify cost meter increments

**Selectors**:
- Input: `[data-testid="chat-input"]`
- Send button: `[data-testid="send-button"]`
- Message bubble: `[data-testid="message-bubble"]`
- Token counter: `[data-testid="token-counter"]`

## 2. Command Palette Navigation
**Scenario**: User opens command palette and navigates to agents
- Press Cmd+K anywhere in app
- Type "agents"
- Press Enter on "Go to Agents"
- Verify navigation to `/agents`

**Selectors**:
- Command palette: `[data-testid="command-palette"]`
- Search input: `[data-testid="command-search"]`
- Command item: `[data-testid="command-item"]`

## 3. Model Switching
**Scenario**: User switches between models mid-conversation
- Start chat with default model
- Click model switcher dropdown
- Select "Llama3:70b"
- Send new message
- Verify model badge updates
- Verify cost calculation changes

**Selectors**:
- Model switcher: `[data-testid="model-switcher"]`
- Model option: `[data-testid="model-option"]`
- Model badge: `[data-testid="current-model"]`

## 4. Tool Invocation
**Scenario**: User triggers a tool call
- Type "Check my calendar for tomorrow"
- Send message
- Verify tool indicator appears
- Verify tool result displays inline
- Verify tool execution time shows

**Selectors**:
- Tool indicator: `[data-testid="tool-call"]`
- Tool result: `[data-testid="tool-result"]`
- Tool status: `[data-testid="tool-status"]`

## 5. Session Management
**Scenario**: User creates, searches, and switches sessions
- Click "New Chat" button
- Send message in new session
- Open sidebar
- Search for previous session
- Click to switch sessions
- Verify message history loads

**Selectors**:
- New chat button: `[data-testid="new-chat"]`
- Session list: `[data-testid="session-list"]`
- Session search: `[data-testid="session-search"]`
- Session item: `[data-testid="session-item"]`

## 6. Keyboard Shortcuts
**Scenario**: User navigates using keyboard only
- Press Cmd+N for new chat
- Type message
- Press Cmd+Enter to send
- Press Escape to stop generation
- Press Alt+Up to edit last message
- Press Cmd+] to cycle models

**Verification**: All actions complete without mouse

## 7. Cost Tracking
**Scenario**: User monitors token usage and costs
- Send multiple messages
- Open logs view
- Verify JSONL entries created
- Download logs
- Verify cost accumulation correct

**Selectors**:
- Cost meter: `[data-testid="cost-meter"]`
- Logs view: `[data-testid="logs-view"]`
- Download button: `[data-testid="download-logs"]`

## 8. Agent Configuration
**Scenario**: User configures and activates an agent
- Navigate to `/agents`
- Click on Calendar Agent
- Update system prompt
- Toggle agent active
- Return to chat
- Verify agent appears in selector

**Selectors**:
- Agent card: `[data-testid="agent-card"]`
- Agent toggle: `[data-testid="agent-toggle"]`
- System prompt: `[data-testid="system-prompt"]`

## 9. Theme Switching
**Scenario**: User toggles between light and dark themes
- Press Cmd+Shift+L
- Verify dark theme applies
- Press again
- Verify light theme applies
- Check persistence on reload

**Verification**: CSS classes change on `<html>`

## 10. Slash Commands
**Scenario**: User uses slash commands in chat
- Type "/" in empty input
- Verify command menu appears
- Select "/summarize"
- Verify input prefilled
- Complete and send command
- Verify appropriate tool invocation

**Selectors**:
- Slash menu: `[data-testid="slash-menu"]`
- Slash command: `[data-testid="slash-command"]`
- Input field: `[data-testid="chat-input"]`

## Test Utilities

```typescript
// Helper functions for tests
export const selectors = {
  chatInput: '[data-testid="chat-input"]',
  sendButton: '[data-testid="send-button"]',
  messageBubble: '[data-testid="message-bubble"]',
  commandPalette: '[data-testid="command-palette"]',
  modelSwitcher: '[data-testid="model-switcher"]',
  costMeter: '[data-testid="cost-meter"]',
  sessionList: '[data-testid="session-list"]',
};

export async function waitForStreaming(page: Page) {
  await page.waitForSelector('[data-testid="streaming-indicator"]');
  await page.waitForSelector('[data-testid="streaming-indicator"]', {
    state: 'hidden',
  });
}

export async function sendMessage(page: Page, message: string) {
  await page.fill(selectors.chatInput, message);
  await page.keyboard.press('Meta+Enter');
  await waitForStreaming(page);
}
```