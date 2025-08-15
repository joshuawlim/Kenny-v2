# Kenny v2 Puppeteer Integration

Puppeteer has been successfully integrated into Kenny v2 for both **E2E testing** and **web automation capabilities**.

## 🎭 E2E Testing Setup

### Quick Start

```bash
# Run E2E tests (requires Kenny Dashboard to be running)
npm run test:e2e

# Run E2E tests in development mode with watching
npm run test:e2e:dev

# Run E2E tests for CI (headless mode)
npm run test:e2e:ci
```

### Test Structure

- **`e2e/dashboard.test.js`** - Core dashboard functionality tests
- **`e2e/kenny-integration.test.js`** - Backend integration and API tests
- **`e2e/setup.js`** - Test utilities and global helpers
- **`e2e/screenshots/`** - Automated screenshots for debugging

### Test Features

✅ **Dashboard Navigation** - Sidebar navigation, page routing  
✅ **Chat Interface** - Input functionality, connection status  
✅ **API Integration** - Gateway connectivity, WebSocket testing  
✅ **Visual Testing** - Screenshot capture, responsive design  
✅ **Performance** - Load time monitoring, error detection  
✅ **Error Handling** - Graceful degradation, offline mode  

### Test Configuration

- **`jest-puppeteer.config.js`** - Puppeteer launch options
- **`jest.e2e.config.js`** - Jest test configuration
- **Headless Mode**: CI=true for headless, false for visible browser
- **Screenshots**: Automatically captured on test actions

## 🌐 Web Agent Service

### Kenny Web Agent Features

- **Port**: 8008
- **Headless**: Production mode, visible in development
- **Capabilities**:
  - `web.navigate` - Navigate to URLs and extract page info
  - `web.extract` - Extract specific data using CSS selectors  
  - `web.interact` - Perform actions (click, type, form fill)
  - `web.monitor` - Monitor pages for changes

### Usage Examples

```javascript
// Navigate to a page
await fetch('http://localhost:8008/web/navigate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: 'https://example.com',
    screenshot: true,
    wait_for: '.content'
  })
});

// Extract data from page
await fetch('http://localhost:8008/web/extract', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: 'https://news.ycombinator.com',
    selectors: {
      titles: '.titleline > a',
      scores: '.score',
      comments: '.subtext a[href*="item"]'
    }
  })
});

// Interact with page elements
await fetch('http://localhost:8008/web/interact', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: 'https://google.com',
    actions: [
      { type: 'fill', selector: 'input[name="q"]', value: 'Kenny AI assistant' },
      { type: 'click', selector: 'input[type="submit"]' },
      { type: 'screenshot' }
    ]
  })
});
```

## 🔧 Development Workflow

### Starting Services

```bash
# 1. Start Kenny Gateway (required for integration tests)
cd "Kenny v2/services/gateway" && python3 -m src.main

# 2. Start Kenny Dashboard (required for E2E tests)  
cd "Kenny v2/services/dashboard" && npm run dev

# 3. Start Web Agent (optional, for web automation)
cd "Kenny v2/services/web-agent" && npm install && npm start

# 4. Run E2E tests
npm run test:e2e
```

### Test Development

1. **Write Tests**: Add new tests to `e2e/` directory
2. **Debug**: Tests run in visible browser mode locally
3. **Screenshots**: Auto-captured for debugging failed tests
4. **Selectors**: Use data-testid attributes for reliable element selection

### Kenny Integration

The Web Agent is designed to integrate with Kenny's multi-agent architecture:

- **Gateway Integration**: Accessible via `/capability/web.*` endpoints
- **Agent Registry**: Registers itself with manifest.json capabilities
- **Coordinator**: Can be orchestrated for complex web workflows
- **Dashboard**: Can be monitored through Kenny's health system

## 📊 Test Examples

### Dashboard Tests
- ✅ Homepage loads with Kenny branding
- ✅ Navigation between pages (Dashboard, Chat, Agents, etc.)
- ✅ Chat interface displays and accepts input
- ✅ Connection status indicators work
- ✅ Responsive design on mobile/tablet

### Integration Tests  
- ✅ API connectivity to Kenny Gateway
- ✅ WebSocket connection testing
- ✅ Offline mode graceful degradation
- ✅ Backend service health checks
- ✅ Error handling and recovery

### Web Agent Tests
- ✅ Page navigation and content extraction
- ✅ Form interactions and data submission
- ✅ Screenshot capture and visual monitoring
- ✅ Change detection and monitoring
- ✅ Multi-step automation workflows

## 🚀 Production Deployment

### Environment Variables

```bash
# Dashboard E2E Tests
CI=true                    # Enable headless mode
NODE_ENV=production       # Production optimizations

# Web Agent
PORT=8008                 # Web agent port
NODE_ENV=production       # Headless browser mode
```

### CI/CD Integration

```yaml
# Example GitHub Actions
- name: E2E Tests
  run: |
    npm run build
    npm run test:e2e:ci
  env:
    CI: true
```

## 🔍 Debugging

### Screenshots
All tests automatically capture screenshots saved to:
- `e2e/screenshots/dashboard-homepage.png`
- `e2e/screenshots/chat-interface.png`
- `e2e/screenshots/mobile-view.png`

### Console Logs
Tests capture and filter console errors, excluding:
- 404 errors (expected during development)
- WebSocket connection errors (when services are down)
- Network fetch failures (handled gracefully)

### Test Utilities
Global `Kenny` object provides utilities:
- `Kenny.waitForDashboard(page)` - Wait for dashboard to load
- `Kenny.waitForChat(page)` - Wait for chat interface  
- `Kenny.screenshot(page, name)` - Take debug screenshot
- `Kenny.checkServices(page)` - Verify backend connectivity

---

Puppeteer is now fully integrated into Kenny v2, providing comprehensive testing and web automation capabilities! 🎉