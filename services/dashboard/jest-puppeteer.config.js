// Jest Puppeteer configuration for Kenny v2 Dashboard E2E tests
module.exports = {
  launch: {
    headless: process.env.CI === 'true', // Run headless in CI, visible locally
    devtools: false,
    slowMo: process.env.CI === 'true' ? 0 : 50, // Slow down for debugging locally
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-web-security',
      '--disable-features=VizDisplayCompositor'
    ]
  },
  server: {
    command: 'npm run dev',
    port: 3001,
    launchTimeout: 30000,
    debug: false
  },
  browserContext: 'default'
};