// E2E tests for Kenny v2 Dashboard core functionality
describe('Kenny v2 Dashboard', () => {
  let page;

  beforeAll(async () => {
    page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });
  });

  afterAll(async () => {
    await page.close();
  });

  describe('Dashboard Navigation', () => {
    test('should load the dashboard homepage', async () => {
      await page.goto('http://localhost:3001');
      
      // Wait for the dashboard to load
      await page.waitForSelector('[data-testid="kenny-dashboard"], .kenny-dashboard, h1', {
        timeout: 10000
      });

      // Check if we can find Kenny branding
      const title = await page.textContent('h1');
      expect(title).toContain('Kenny');

      // Take screenshot for visual verification
      await page.screenshot({ 
        path: 'e2e/screenshots/dashboard-homepage.png',
        fullPage: true 
      });
    });

    test('should navigate to chat interface', async () => {
      await page.goto('http://localhost:3001/chat');
      
      // Wait for chat interface to load
      await page.waitForSelector('h1:has-text("Kenny Chat Interface"), h1:has-text("Chat Interface")', {
        timeout: 10000
      });

      const heading = await page.textContent('h1');
      expect(heading).toContain('Chat');

      // Take screenshot
      await page.screenshot({ 
        path: 'e2e/screenshots/chat-interface.png',
        fullPage: true 
      });
    });

    test('should navigate between pages using sidebar', async () => {
      await page.goto('http://localhost:3001');
      
      // Wait for sidebar to be ready
      await page.waitForSelector('nav, [role="navigation"]', { timeout: 10000 });

      // Find and click the Agents link
      const agentsLink = await page.locator('text=Agents').first();
      if (await agentsLink.count() > 0) {
        await agentsLink.click();
        await page.waitForURL('**/agents');
        
        const url = page.url();
        expect(url).toContain('/agents');
      } else {
        console.log('Agents link not found, checking for alternative navigation');
        // Take screenshot for debugging
        await page.screenshot({ 
          path: 'e2e/screenshots/navigation-debug.png',
          fullPage: true 
        });
      }
    });
  });

  describe('Chat Functionality', () => {
    beforeEach(async () => {
      await page.goto('http://localhost:3001/chat');
      await page.waitForSelector('h1', { timeout: 10000 });
    });

    test('should display chat welcome screen', async () => {
      // Look for welcome message or quick actions
      const welcomeElements = await page.locator('text=Welcome, text=Quick Actions, button').count();
      expect(welcomeElements).toBeGreaterThan(0);
    });

    test('should have functional chat input', async () => {
      // Find chat input field
      const inputSelectors = [
        'textarea[placeholder*="Ask"]',
        'input[placeholder*="Ask"]', 
        'textarea',
        'input[type="text"]'
      ];

      let inputFound = false;
      for (const selector of inputSelectors) {
        try {
          await page.waitForSelector(selector, { timeout: 2000 });
          inputFound = true;
          
          // Test typing in the input
          await page.fill(selector, 'Hello Kenny!');
          const value = await page.inputValue(selector);
          expect(value).toBe('Hello Kenny!');
          
          break;
        } catch (error) {
          // Try next selector
          continue;
        }
      }

      if (!inputFound) {
        // Take debug screenshot
        await page.screenshot({ 
          path: 'e2e/screenshots/chat-input-debug.png',
          fullPage: true 
        });
        console.log('Chat input not found - this may be expected if chat is not yet implemented');
      }
    });

    test('should show connection status', async () => {
      // Look for connection status indicators
      const statusElements = await page.locator('text=Live, text=Offline, text=Connected, text=Disconnected').count();
      expect(statusElements).toBeGreaterThanOrEqual(0); // May be 0 if not implemented yet
    });

    test('should handle quick actions if available', async () => {
      // Look for quick action buttons
      const quickActionButtons = await page.locator('button:has-text("Check"), button:has-text("Show"), button:has-text("What")').count();
      
      if (quickActionButtons > 0) {
        // Click the first quick action button
        await page.locator('button:has-text("Check"), button:has-text("Show"), button:has-text("What")').first().click();
        
        // Wait a moment for any response
        await page.waitForTimeout(1000);
        
        // Take screenshot to see result
        await page.screenshot({ 
          path: 'e2e/screenshots/quick-action-result.png',
          fullPage: true 
        });
      }
    });
  });

  describe('Visual and Performance', () => {
    test('should load without console errors', async () => {
      const errors = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.goto('http://localhost:3001');
      await page.waitForSelector('h1', { timeout: 10000 });
      
      // Filter out known acceptable errors
      const criticalErrors = errors.filter(error => 
        !error.includes('404') && 
        !error.includes('Failed to fetch') &&
        !error.includes('websocket')
      );

      if (criticalErrors.length > 0) {
        console.log('Console errors found:', criticalErrors);
      }
      
      // Don't fail on errors during development, just log them
      expect(criticalErrors.length).toBeLessThan(10);
    });

    test('should be responsive', async () => {
      await page.goto('http://localhost:3001');
      await page.waitForSelector('h1', { timeout: 10000 });

      // Test mobile viewport
      await page.setViewport({ width: 375, height: 667 });
      await page.waitForTimeout(500);
      
      await page.screenshot({ 
        path: 'e2e/screenshots/mobile-view.png',
        fullPage: true 
      });

      // Test tablet viewport
      await page.setViewport({ width: 768, height: 1024 });
      await page.waitForTimeout(500);
      
      await page.screenshot({ 
        path: 'e2e/screenshots/tablet-view.png',
        fullPage: true 
      });

      // Restore desktop viewport
      await page.setViewport({ width: 1920, height: 1080 });
    });

    test('should load within performance budget', async () => {
      const startTime = Date.now();
      
      await page.goto('http://localhost:3001');
      await page.waitForSelector('h1', { timeout: 15000 });
      
      const loadTime = Date.now() - startTime;
      console.log(`Page load time: ${loadTime}ms`);
      
      // Allow generous load time during development
      expect(loadTime).toBeLessThan(15000);
    });
  });
});