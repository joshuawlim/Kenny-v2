// Debug chat interface loading
const puppeteer = require('puppeteer');

async function debugChat() {
  console.log('🔍 Debugging Chat Interface...');
  
  const browser = await puppeteer.launch({
    headless: false,
    slowMo: 50,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1400, height: 900 }
  });
  
  const page = await browser.newPage();
  
  // Capture console messages
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    console.log(`Browser Console [${type.toUpperCase()}]: ${text}`);
  });
  
  // Capture errors
  page.on('error', error => {
    console.log(`Page Error: ${error.message}`);
  });
  
  page.on('pageerror', error => {
    console.log(`Page Error: ${error.message}`);
  });
  
  try {
    console.log('📱 Loading dashboard...');
    await page.goto('http://localhost:3001', { waitUntil: 'networkidle2' });
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Take screenshot of main page
    await page.screenshot({ path: 'debug-main.png' });
    
    console.log('🎯 Navigating to /chat...');
    await page.goto('http://localhost:3001/chat', { waitUntil: 'networkidle2' });
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Check what's actually rendered
    const pageAnalysis = await page.evaluate(() => {
      return {
        url: window.location.href,
        title: document.title,
        bodyText: document.body.innerText.slice(0, 1000),
        hasTextarea: document.querySelectorAll('textarea').length,
        hasButtons: document.querySelectorAll('button').length,
        hasChatInterface: document.body.innerHTML.includes('ChatInterface'),
        reactRoot: !!document.getElementById('root'),
        rootChildren: document.getElementById('root')?.children.length || 0,
        allElements: document.querySelectorAll('*').length,
        chatRelated: Array.from(document.querySelectorAll('*')).filter(el => 
          el.textContent?.includes('chat') || 
          el.textContent?.includes('Chat') ||
          el.className?.includes('chat')
        ).length
      };
    });
    
    console.log('📊 Page Analysis:');
    console.log(`   URL: ${pageAnalysis.url}`);
    console.log(`   Has textarea: ${pageAnalysis.hasTextarea}`);
    console.log(`   Has buttons: ${pageAnalysis.hasButtons}`);  
    console.log(`   React root: ${pageAnalysis.reactRoot}`);
    console.log(`   Root children: ${pageAnalysis.rootChildren}`);
    console.log(`   Total elements: ${pageAnalysis.allElements}`);
    console.log(`   Chat-related elements: ${pageAnalysis.chatRelated}`);
    
    // Take screenshot of chat page
    await page.screenshot({ path: 'debug-chat.png' });
    
    console.log('\nBody content:');
    console.log(pageAnalysis.bodyText);
    
    console.log('\n🔍 Browser open for inspection. Press Ctrl+C to close.');
    
    await new Promise(resolve => {
      process.on('SIGINT', () => {
        console.log('\n👋 Closing...');
        resolve();
      });
    });
    
  } catch (error) {
    console.error('❌ Debug failed:', error.message);
  } finally {
    await browser.close();
  }
}

debugChat().catch(console.error);