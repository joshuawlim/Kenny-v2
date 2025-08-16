// Integration test for Kenny agent coordination with real backend
const puppeteer = require('puppeteer');

const TEST_PROMPTS = [
  "What was my last 3 emails to Krista Hiob?",
  "What were the last 3 messages I sent to Courtney?", 
  "Whose birthday is next?"
];

async function testAgentIntegration() {
  console.log('🤖 Starting Kenny Agent Integration Test...');
  
  const browser = await puppeteer.launch({
    headless: false,
    slowMo: 250,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1400, height: 900 }
  });
  
  try {
    const page = await browser.newPage();
    
    // Enable request interception to monitor API calls
    await page.setRequestInterception(true);
    
    const apiCalls = [];
    const agentCalls = [];
    
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/') || url.includes(':8001') || url.includes(':9000')) {
        apiCalls.push({
          url: url,
          method: request.method(),
          postData: request.postData(),
          timestamp: new Date()
        });
      }
      
      if (url.includes('agent') || url.includes('coordinator')) {
        agentCalls.push({
          url: url,
          method: request.method(),
          timestamp: new Date()
        });
      }
      
      request.continue();
    });
    
    // Monitor console for agent activity
    const consoleLogs = [];
    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push({ type: msg.type(), text, timestamp: new Date() });
      if (text.includes('agent') || text.includes('coordinator')) {
        console.log(`[BROWSER] ${msg.type()}: ${text}`);
      }
    });
    
    console.log('📱 Navigating to dashboard...');
    await page.goto('http://localhost:3001', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    // Wait for initial load and React hydration
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    console.log('🔍 Checking dashboard load and agent connectivity...');
    
    // Check if dashboard loaded successfully
    const pageText = await page.evaluate(() => document.body.innerText);
    if (pageText.length < 100) {
      throw new Error('Dashboard appears to be blank');
    }
    
    // Check agent status display
    try {
      await page.waitForSelector('[class*="agent"]', { timeout: 5000 });
      console.log('✅ Agent UI elements detected');
    } catch (e) {
      console.log('⚠️ No agent UI elements found');
    }
    
    // Check API connectivity
    const testApiCall = async (endpoint, description) => {
      try {
        const response = await page.evaluate(async (url) => {
          const res = await fetch(url);
          return {
            status: res.status,
            ok: res.ok,
            data: await res.text()
          };
        }, endpoint);
        
        console.log(`✅ ${description}: ${response.status} ${response.ok ? 'OK' : 'FAIL'}`);
        return response.ok;
      } catch (error) {
        console.log(`❌ ${description}: ${error.message}`);
        return false;
      }
    };
    
    await testApiCall('http://localhost:9000/health', 'Gateway Health');
    await testApiCall('http://localhost:8001/agents', 'Agent Registry');
    await testApiCall('http://localhost:8002/health', 'Coordinator Health');
    
    console.log('\n🧪 Testing Agent Coordination with Real Prompts...\n');
    
    for (const [index, prompt] of TEST_PROMPTS.entries()) {
      console.log(`\n--- Test ${index + 1}/3: "${prompt}" ---`);
      
      try {
        // Find message input (multiple possible selectors)
        let messageInput;
        const inputSelectors = [
          'textarea[placeholder*="Ask"]',
          'textarea[placeholder*="message"]',
          'input[placeholder*="Ask"]',
          'input[placeholder*="message"]',
          '[data-testid="message-input"]',
          'textarea',
          'input[type="text"]'
        ];
        
        for (const selector of inputSelectors) {
          try {
            messageInput = await page.$(selector);
            if (messageInput) {
              console.log(`✅ Found input with selector: ${selector}`);
              break;
            }
          } catch (e) {
            // Continue to next selector
          }
        }
        
        if (!messageInput) {
          console.log('❌ Could not find message input element');
          console.log('Available inputs on page:');
          const inputs = await page.$$eval('input, textarea', elements => 
            elements.map(el => ({
              tag: el.tagName,
              type: el.type,
              placeholder: el.placeholder,
              id: el.id,
              className: el.className
            }))
          );
          console.log(inputs);
          continue;
        }
        
        // Clear and type the prompt
        await messageInput.click();
        await page.keyboard.down('Meta');
        await page.keyboard.press('a');
        await page.keyboard.up('Meta');
        await messageInput.type(prompt);
        
        console.log(`💭 Typed prompt: "${prompt}"`);
        
        // Send the message (try multiple methods)
        const sendMethods = [
          async () => {
            await page.keyboard.down('Meta');
            await page.keyboard.press('Enter');
            await page.keyboard.up('Meta');
          },
          async () => {
            await page.keyboard.press('Enter');
          },
          async () => {
            const sendButton = await page.$('button[type="submit"], button:contains("Send"), [aria-label*="send"]');
            if (sendButton) await sendButton.click();
          }
        ];
        
        let sent = false;
        for (const method of sendMethods) {
          try {
            await method();
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Check if message appeared
            const newText = await page.evaluate(() => document.body.innerText);
            if (newText.includes(prompt)) {
              console.log('✅ Message sent successfully');
              sent = true;
              break;
            }
          } catch (e) {
            // Try next method
          }
        }
        
        if (!sent) {
          console.log('❌ Failed to send message');
          continue;
        }
        
        // Monitor for response and agent activity
        console.log('⏳ Waiting for agent response...');
        
        const startTime = Date.now();
        let responseReceived = false;
        let agentActivity = false;
        
        // Wait up to 30 seconds for response
        while (Date.now() - startTime < 30000 && !responseReceived) {
          await new Promise(resolve => setTimeout(resolve, 1000));
          
          // Check for new API calls
          const recentCalls = apiCalls.filter(call => 
            call.timestamp > new Date(startTime) &&
            (call.url.includes('coordinator') || call.url.includes('agent'))
          );
          
          if (recentCalls.length > 0 && !agentActivity) {
            console.log(`🔄 Agent activity detected: ${recentCalls.length} API calls`);
            agentActivity = true;
            recentCalls.forEach(call => {
              console.log(`  - ${call.method} ${call.url}`);
            });
          }
          
          // Check for streaming or response indicators
          const indicators = await page.$$eval('[class*="streaming"], [class*="loading"], [class*="thinking"]', 
            elements => elements.length
          );
          
          if (indicators > 0) {
            console.log('🔄 Streaming/loading indicators detected');
          }
          
          // Check for new message content (assistant response)
          const currentText = await page.evaluate(() => document.body.innerText);
          const hasResponse = currentText.toLowerCase().includes('assistant') || 
                             currentText.toLowerCase().includes('kenny') ||
                             currentText.length > pageText.length + prompt.length + 100;
          
          if (hasResponse && !responseReceived) {
            console.log('✅ Response received from agent');
            responseReceived = true;
          }
        }
        
        // Take screenshot of the result
        await page.screenshot({ 
          path: `agent-test-${index + 1}-${Date.now()}.png`, 
          fullPage: false 
        });
        
        // Analyze the response
        if (responseReceived) {
          console.log('✅ Test completed successfully');
          
          // Extract response content
          const finalText = await page.evaluate(() => document.body.innerText);
          const responseSection = finalText.slice(pageText.length);
          
          // Look for agent-specific indicators
          const agentIndicators = ['mail', 'email', 'calendar', 'contact', 'birthday', 'message'];
          const foundIndicators = agentIndicators.filter(indicator => 
            responseSection.toLowerCase().includes(indicator)
          );
          
          if (foundIndicators.length > 0) {
            console.log(`🎯 Agent-specific content detected: ${foundIndicators.join(', ')}`);
          }
          
        } else {
          console.log('⚠️ No response received within timeout');
        }
        
        // Brief pause between tests
        await new Promise(resolve => setTimeout(resolve, 2000));
        
      } catch (error) {
        console.log(`❌ Test failed: ${error.message}`);
      }
    }
    
    // Final summary
    console.log('\n📊 Integration Test Summary:');
    console.log(`- API calls made: ${apiCalls.length}`);
    console.log(`- Agent-related calls: ${agentCalls.length}`);
    console.log(`- Console logs: ${consoleLogs.length}`);
    
    // Show recent API activity
    const recentCalls = apiCalls.slice(-10);
    if (recentCalls.length > 0) {
      console.log('\nRecent API Activity:');
      recentCalls.forEach(call => {
        console.log(`  ${call.timestamp.toLocaleTimeString()} - ${call.method} ${call.url}`);
      });
    }
    
    console.log('\n✅ Agent integration test completed!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error(error.stack);
  } finally {
    // Keep browser open for inspection
    console.log('\n🔍 Browser left open for manual inspection...');
    console.log('Press Ctrl+C to close and exit.');
    
    // Wait indefinitely
    await new Promise(() => {});
  }
}

// Run the test
testAgentIntegration().catch(console.error);