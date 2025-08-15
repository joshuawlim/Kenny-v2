// Web Navigation Handler - Navigate to URLs and extract basic info
export class WebNavigateHandler {
  async handle({ page, url, wait_for, screenshot = false }) {
    const startTime = Date.now();
    
    try {
      console.log(`🌐 Navigating to: ${url}`);
      
      // Navigate to URL
      const response = await page.goto(url, {
        waitUntil: 'networkidle2',
        timeout: 30000
      });

      // Wait for specific element if specified
      if (wait_for) {
        console.log(`⏳ Waiting for: ${wait_for}`);
        await page.waitForSelector(wait_for, { timeout: 10000 });
      }

      // Extract basic page information
      const pageInfo = await page.evaluate(() => {
        return {
          title: document.title,
          url: window.location.href,
          meta: {
            description: document.querySelector('meta[name="description"]')?.content || '',
            keywords: document.querySelector('meta[name="keywords"]')?.content || '',
            ogTitle: document.querySelector('meta[property="og:title"]')?.content || '',
            ogDescription: document.querySelector('meta[property="og:description"]')?.content || ''
          },
          links: Array.from(document.querySelectorAll('a[href]')).slice(0, 10).map(a => ({
            text: a.textContent.trim(),
            href: a.href
          })),
          headings: Array.from(document.querySelectorAll('h1, h2, h3')).slice(0, 10).map(h => ({
            level: h.tagName.toLowerCase(),
            text: h.textContent.trim()
          }))
        };
      });

      let screenshotData = null;
      if (screenshot) {
        console.log('📸 Taking screenshot...');
        screenshotData = await page.screenshot({
          type: 'png',
          encoding: 'base64',
          fullPage: false,
          clip: { x: 0, y: 0, width: 1200, height: 800 }
        });
      }

      const duration = Date.now() - startTime;
      
      return {
        status: 'success',
        url,
        status_code: response.status(),
        page_info: pageInfo,
        screenshot: screenshotData,
        duration_ms: duration,
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(`❌ Navigation failed for ${url}:`, error.message);
      
      return {
        status: 'error',
        url,
        error: error.message,
        duration_ms: duration,
        timestamp: new Date().toISOString()
      };
    }
  }
}