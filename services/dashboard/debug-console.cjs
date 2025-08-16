// Simple script to capture console errors and debug React loading
const puppeteer = require('puppeteer');

async function debugDashboard() {
  console.log('🔍 Debugging dashboard console errors...');
  
  const browser = await puppeteer.launch({
    headless: false, 
    devtools: true,
    slowMo: 100
  });
  
  try {
    const page = await browser.newPage();
    
    // Capture all console logs
    const logs = [];
    page.on('console', msg => {
      const type = msg.type();
      const text = msg.text();
      logs.push({ type, text });
      console.log(`[${type.toUpperCase()}] ${text}`);
    });
    
    // Capture network failures
    page.on('requestfailed', request => {
      console.log(`[NETWORK FAILED] ${request.url()} - ${request.failure()?.errorText}`);
    });
    
    // Capture unhandled errors
    page.on('pageerror', error => {
      console.log(`[PAGE ERROR] ${error.message}`);
      console.log(error.stack);
    });
    
    console.log('📱 Loading dashboard...');
    await page.goto('http://localhost:3001', { 
      waitUntil: 'networkidle0',
      timeout: 30000 
    });
    
    // Wait for potential React loading
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Check what's in the root div
    const rootContent = await page.evaluate(() => {
      const root = document.getElementById('root');
      return {
        hasChildren: root ? root.children.length : 0,
        innerHTML: root ? root.innerHTML.slice(0, 500) : 'No root element found',
        outerHTML: root ? root.outerHTML.slice(0, 500) : 'No root element found'
      };
    });
    
    console.log('Root element info:', rootContent);
    
    // Check if main.tsx is loading
    const scriptTags = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('script')).map(script => ({
        src: script.src,
        type: script.type,
        loaded: script.src ? 'unknown' : 'inline'
      }));
    });
    
    console.log('Script tags:', scriptTags);
    
    // Keep the browser open for inspection
    console.log('Browser left open for manual inspection. Press Ctrl+C to close.');
    
    // Wait indefinitely (until manually closed)
    await new Promise(() => {});
    
  } catch (error) {
    console.error('Debug failed:', error);
  } finally {
    await browser.close();
  }
}

debugDashboard().catch(console.error);