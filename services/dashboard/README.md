# Kenny v2 React Dashboard

A modern, real-time dashboard for monitoring and interacting with the Kenny v2 multi-agent system.

## Features

- **Real-time System Health**: Live SSE streaming from agent registry
- **Agent Monitoring**: Visual status grids with health indicators
- **Performance Metrics**: Interactive charts and trend analysis
- **Security Monitoring**: Live security events and compliance tracking
- **Local-first**: No external dependencies, fully self-contained
- **Responsive Design**: Optimized for desktop browsers with mobile support

## Architecture

- **React 18** with TypeScript for type safety
- **Vite** for fast development and optimized builds
- **TailwindCSS** for consistent styling (no external CDNs)
- **React Query** for efficient API state management
- **Recharts** for data visualization
- **WebSocket/SSE** for real-time updates

## Development

### Prerequisites

- Node.js 18+
- Kenny v2 backend services running (Gateway, Registry, Coordinator)

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint
```

### Development Server

The development server runs on `http://localhost:3001` with API proxying:

- `/api/*` → Gateway Service (localhost:9000)
- `/registry/*` → Agent Registry (localhost:8001)  
- `/coordinator/*` → Coordinator Service (localhost:8002)

## API Integration

### Real-time Connections

- **Health Stream**: SSE from `/registry/system/health/dashboard/stream`
- **Security Events**: SSE from `/registry/security/events/stream`
- **Query Stream**: WebSocket to `/api/stream` (future)

### REST APIs

- Gateway API (port 9000): System health, agents, capabilities, queries
- Registry API (port 8001): Health dashboard, security monitoring, traces
- Coordinator API (port 8002): Multi-agent orchestration, graph info

## Deployment

### Docker Build

```bash
# Build image
docker build -t kenny-dashboard .

# Run container
docker run -p 3001:80 kenny-dashboard
```

### Production Deployment

The dashboard is designed to be deployed alongside the Kenny v2 backend services:

1. **Local-first**: All dependencies bundled, no external CDNs
2. **Nginx routing**: API requests proxied to backend services
3. **Health monitoring**: Built-in health checks and error boundaries
4. **Performance optimized**: <2s load time, <1s update latency

## Configuration

### Environment Variables

- `VITE_API_BASE_URL`: Override API base URL (default: uses proxy)
- `VITE_ENABLE_ANALYTICS`: Enable performance analytics (default: true)

### Nginx Configuration

The production nginx config includes:

- API proxying to backend services
- WebSocket/SSE support for real-time features
- Security headers and compression
- SPA routing support
- Health check endpoint at `/health`

## Components

### Layout Components

- `Header`: System status and quick metrics
- `Sidebar`: Navigation with live indicators
- `ConnectionStatus`: Real-time connection monitoring

### Dashboard Components

- `SystemOverview`: Key metrics grid with status indicators
- `PerformanceChart`: Real-time performance trends
- `RecentActivity`: Live activity feed from security events
- `MetricCard`: Reusable metric display component

### Page Components

- `DashboardPage`: Main system overview
- `AgentsPage`: Agent monitoring and capabilities
- `QueryPage`: Multi-agent query interface (future)
- `SecurityPage`: Security monitoring (future)
- `AnalyticsPage`: Performance analytics (future)

## Testing

```bash
# Run unit tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run tests in watch mode
npm test -- --watch
```

Test setup includes:

- Jest + Vitest for test runner
- React Testing Library for component tests
- Mock implementations for WebSocket/SSE
- API mocking for integration tests

## Performance

### Bundle Optimization

- Code splitting by route and functionality
- Lazy loading for chart components
- Efficient WebSocket connection management
- Optimized bundle size with tree shaking

### Monitoring

- Real-time performance metrics
- Connection stability tracking
- Error boundary reporting
- Load time optimization

## Browser Support

- Chrome 90+ (primary target)
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Follow TypeScript strict mode
2. Use ESLint configuration
3. Write tests for new components
4. Maintain 100% type coverage
5. Document API changes

## License

Part of Kenny v2 - Local-first multi-agent personal assistant system.