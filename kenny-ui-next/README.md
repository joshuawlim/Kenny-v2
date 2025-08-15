# Kenny v2 UI - Next.js Dashboard

A modern, keyboard-first dashboard for Kenny, your local multi-agent AI assistant. Inspired by Open WebUI with a focus on privacy, performance, and power-user workflows.

## ✨ Features

- **🎯 Keyboard-First**: Full keyboard navigation with hotkeys (⌘K command palette, ⌘N new chat, etc.)
- **🤖 Multi-Agent**: Seamless switching between specialized agents (Mail, Calendar, Contacts, etc.)
- **💬 Real-time Chat**: WebSocket streaming with token-by-token responses
- **📊 Cost Tracking**: Live token usage and cost monitoring
- **🔍 Command Palette**: Fuzzy search for all actions and navigation
- **🎨 Modern UI**: Glass morphism design with dark/light themes
- **📱 Responsive**: Works on desktop, tablet, and mobile
- **♿ Accessible**: WCAG AA compliant with screen reader support
- **🔒 Privacy-First**: Local-first architecture with offline capabilities

## 🚀 Quick Start

```bash
# Install dependencies
make install

# Start development server (with Kenny backend)
make setup

# Or just the frontend
make dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 🏗️ Architecture

```
├── src/
│   ├── app/                 # Next.js app router
│   ├── components/          # Reusable UI components
│   │   ├── chat/           # Chat interface components
│   │   ├── layout/         # Layout components
│   │   ├── ui/             # Base UI primitives
│   │   └── providers/      # Context providers
│   ├── lib/
│   │   ├── stores/         # Zustand state management
│   │   ├── hooks/          # Custom React hooks
│   │   ├── types/          # TypeScript definitions
│   │   └── utils/          # Utility functions
│   └── tests/              # Test files
├── tests/e2e/              # Playwright E2E tests
└── docs/                   # Documentation
```

## 🎹 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘K` | Open command palette |
| `⌘N` | New chat session |
| `⌘↩` | Send message |
| `Esc` | Stop generation |
| `⌥↑` | Edit last message |
| `⌘]` | Cycle models |
| `⌥←/→` | Toggle sidebars |

## 🔌 Integration with Kenny Backend

The UI connects to your existing Kenny services:

- **Gateway** (port 9000): Main API and WebSocket streaming
- **Registry** (port 8001): Agent discovery and health
- **Coordinator** (port 8002): Multi-agent orchestration

Routes are automatically proxied through Next.js:
- `/api/gateway/*` → `http://localhost:9000/*`
- `/api/registry/*` → `http://localhost:8001/*`
- `/api/coordinator/*` → `http://localhost:8002/*`

## 🧪 Testing

```bash
# Unit tests
make test

# E2E tests
make test-e2e

# Tests with UI
make test-ui

# Run all checks
make verify
```

## 🎨 Theming

The UI uses a design system inspired by Open WebUI with Kenny branding:

### Color Tokens
```css
--kenny-primary: #14b8a6     /* Teal brand color */
--kenny-gray-900: #0f172a    /* Dark background */
--kenny-gray-800: #1e293b    /* Card backgrounds */
--surface: rgba(255,255,255,0.06)  /* Glass effect */
--border: rgba(255,255,255,0.12)   /* Subtle borders */
```

### Dark/Light Mode
- Automatic system detection
- Manual toggle in settings
- Persistent user preference
- Smooth transitions

## 📊 State Management

Uses Zustand for lightweight, typed state management:

- **SessionStore**: Chat sessions, messages, streaming
- **ModelStore**: Available models, current selection
- **AgentStore**: Agent registry, health status
- **SettingsStore**: User preferences, theme

## 🔧 Configuration

### Environment Variables
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:9000
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:9000
NEXT_PUBLIC_ANALYTICS_ENABLED=false
```

### Model Configuration
Models are auto-discovered from your Kenny backend, but you can override:

```typescript
// lib/config/models.ts
export const modelOverrides = {
  'qwen2.5:8b': {
    displayName: 'Qwen 2.5 8B (Local)',
    costPer1kTokens: 0,
    contextLength: 32768,
  }
}
```

## 🚀 Deployment

### Development
```bash
make dev
```

### Production Build
```bash
make build
npm start
```

### Docker
```bash
docker build -t kenny-ui .
docker run -p 3000:3000 kenny-ui
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `make verify`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Inspired by [Open WebUI](https://github.com/open-webui/open-webui) design patterns
- Built with [Next.js](https://nextjs.org/), [Tailwind CSS](https://tailwindcss.com/), and [Radix UI](https://www.radix-ui.com/)
- Icons from [Lucide](https://lucide.dev/)