// Global setup for E2E tests - ensure Kenny services are ready
const fs = require('fs');
const path = require('path');

module.exports = async () => {
  console.log('🚀 Setting up Kenny v2 E2E test environment...');
  
  // Create screenshots directory
  const screenshotDir = path.join(__dirname, 'screenshots');
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }

  // Check if Kenny Gateway is running
  try {
    const response = await fetch('http://localhost:9000/health');
    if (response.ok) {
      console.log('✅ Kenny Gateway is running');
    } else {
      console.log('⚠️ Kenny Gateway responded with error');
    }
  } catch (error) {
    console.log('❌ Kenny Gateway is not running - tests will run in offline mode');
  }

  // Check if Dashboard dev server is running
  try {
    const response = await fetch('http://localhost:3001');
    if (response.ok) {
      console.log('✅ Kenny Dashboard is running');
    } else {
      console.log('❌ Kenny Dashboard is not responding');
    }
  } catch (error) {
    console.log('❌ Kenny Dashboard is not running - starting via jest-puppeteer');
  }

  console.log('🎭 E2E test environment ready');
};