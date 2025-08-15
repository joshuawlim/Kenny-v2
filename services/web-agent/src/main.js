// Kenny v2 Web Agent - Puppeteer-powered web automation
import express from 'express';
import cors from 'cors';
import puppeteer from 'puppeteer';
import { WebNavigateHandler } from './handlers/navigate.js';
import { WebExtractHandler } from './handlers/extract.js';
import { WebInteractHandler } from './handlers/interact.js';
import { WebMonitorHandler } from './handlers/monitor.js';

const app = express();
const PORT = process.env.PORT || 8008;

// Middleware
app.use(cors());
app.use(express.json());

// Global Puppeteer browser instance
let browser = null;

// Initialize browser
async function initBrowser() {
  try {
    browser = await puppeteer.launch({
      headless: process.env.NODE_ENV === 'production' ? 'new' : false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-web-security'
      ]
    });
    console.log('✅ Puppeteer browser initialized');
    return browser;
  } catch (error) {
    console.error('❌ Failed to initialize Puppeteer browser:', error);
    throw error;
  }
}

// Cleanup browser on exit
process.on('SIGINT', async () => {
  console.log('🛑 Shutting down Web Agent...');
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});

// Initialize handlers
const handlers = {
  navigate: new WebNavigateHandler(),
  extract: new WebExtractHandler(),
  interact: new WebInteractHandler(),
  monitor: new WebMonitorHandler()
};

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'web-agent',
    version: '1.0.0',
    browser_ready: browser !== null,
    timestamp: new Date().toISOString(),
    capabilities: [
      'web.navigate',
      'web.extract', 
      'web.interact',
      'web.monitor'
    ]
  });
});

// Web navigation endpoint
app.post('/web/navigate', async (req, res) => {
  try {
    const { url, wait_for, screenshot = false } = req.body;
    
    if (!url) {
      return res.status(400).json({ error: 'URL is required' });
    }

    const page = await browser.newPage();
    const result = await handlers.navigate.handle({
      page,
      url,
      wait_for,
      screenshot
    });
    
    await page.close();
    res.json(result);
  } catch (error) {
    console.error('Navigation error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Web data extraction endpoint
app.post('/web/extract', async (req, res) => {
  try {
    const { url, selectors } = req.body;
    
    if (!url || !selectors) {
      return res.status(400).json({ error: 'URL and selectors are required' });
    }

    const page = await browser.newPage();
    const result = await handlers.extract.handle({
      page,
      url,
      selectors
    });
    
    await page.close();
    res.json(result);
  } catch (error) {
    console.error('Extraction error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Web interaction endpoint
app.post('/web/interact', async (req, res) => {
  try {
    const { url, actions } = req.body;
    
    if (!url || !actions) {
      return res.status(400).json({ error: 'URL and actions are required' });
    }

    const page = await browser.newPage();
    const result = await handlers.interact.handle({
      page,
      url,
      actions
    });
    
    await page.close();
    res.json(result);
  } catch (error) {
    console.error('Interaction error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Web monitoring endpoint
app.post('/web/monitor', async (req, res) => {
  try {
    const { url, interval = 300 } = req.body;
    
    if (!url) {
      return res.status(400).json({ error: 'URL is required' });
    }

    const result = await handlers.monitor.handle({
      browser,
      url,
      interval
    });
    
    res.json(result);
  } catch (error) {
    console.error('Monitoring error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Generic capability endpoint for Kenny integration
app.post('/capability/:capability', async (req, res) => {
  try {
    const { capability } = req.params;
    const parameters = req.body;

    let result;
    switch (capability) {
      case 'web.navigate':
        const page = await browser.newPage();
        result = await handlers.navigate.handle({ page, ...parameters });
        await page.close();
        break;
      case 'web.extract':
        const extractPage = await browser.newPage();
        result = await handlers.extract.handle({ page: extractPage, ...parameters });
        await extractPage.close();
        break;
      case 'web.interact':
        const interactPage = await browser.newPage();
        result = await handlers.interact.handle({ page: interactPage, ...parameters });
        await interactPage.close();
        break;
      case 'web.monitor':
        result = await handlers.monitor.handle({ browser, ...parameters });
        break;
      default:
        return res.status(404).json({ error: `Unknown capability: ${capability}` });
    }

    res.json({
      status: 'success',
      capability,
      result,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error(`Capability ${req.params.capability} error:`, error);
    res.status(500).json({ 
      status: 'error',
      capability: req.params.capability,
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// Start server
async function startServer() {
  try {
    // Initialize browser first
    await initBrowser();
    
    // Start Express server
    app.listen(PORT, () => {
      console.log(`🌐 Kenny Web Agent running on port ${PORT}`);
      console.log(`📋 Health check: http://localhost:${PORT}/health`);
      console.log(`🎭 Browser mode: ${process.env.NODE_ENV === 'production' ? 'headless' : 'visible'}`);
    });
  } catch (error) {
    console.error('❌ Failed to start Web Agent:', error);
    process.exit(1);
  }
}

startServer();