// E2E test setup for Kenny v2 Dashboard
const { configureToMatchImageSnapshot } = require('jest-image-snapshot');

// Configure image snapshot matching
const toMatchImageSnapshot = configureToMatchImageSnapshot({
  threshold: 0.2,
  thresholdType: 'percent'
});

expect.extend({ toMatchImageSnapshot });

// Global test utilities
global.Kenny = {
  // Wait for Kenny dashboard to be ready
  async waitForDashboard(page, timeout = 10000) {
    await page.waitForSelector('[data-testid="kenny-dashboard"]', { timeout });
    await page.waitForLoadState('networkidle');
  },

  // Wait for chat interface to be ready
  async waitForChat(page, timeout = 10000) {
    await page.waitForSelector('[data-testid="chat-interface"]', { timeout });
    await page.waitForSelector('[data-testid="chat-input"]', { timeout });
  },

  // Common navigation helper
  async navigate(page, route) {
    await page.goto(`http://localhost:3001${route}`);
    await this.waitForDashboard(page);
  },

  // Take screenshot for debugging
  async screenshot(page, name) {
    await page.screenshot({ 
      path: `e2e/screenshots/${name}-${Date.now()}.png`,
      fullPage: true 
    });
  },

  // Check if Kenny services are running
  async checkServices(page) {
    const response = await page.evaluate(async () => {
      try {
        const res = await fetch('/api/health');
        return await res.json();
      } catch (error) {
        return { error: error.message };
      }
    });
    return response;
  }
};