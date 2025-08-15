/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  async rewrites() {
    return [
      // Proxy to existing Kenny services
      {
        source: '/api/gateway/:path*',
        destination: 'http://localhost:9000/:path*',
      },
      {
        source: '/api/registry/:path*', 
        destination: 'http://localhost:8001/:path*',
      },
      {
        source: '/api/coordinator/:path*',
        destination: 'http://localhost:8002/:path*',
      },
    ]
  },
  // WebSocket proxy for streaming
  async headers() {
    return [
      {
        source: '/api/stream/:path*',
        headers: [
          { key: 'Connection', value: 'Upgrade' },
          { key: 'Upgrade', value: 'websocket' },
        ],
      },
    ]
  },
}

module.exports = nextConfig