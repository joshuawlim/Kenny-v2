// Web Data Extraction Handler - Extract specific data using CSS selectors
export class WebExtractHandler {
  async handle({ page, url, selectors }) {
    const startTime = Date.now();
    
    try {
      console.log(`🔍 Extracting data from: ${url}`);
      
      // Navigate to URL
      await page.goto(url, {
        waitUntil: 'networkidle2',
        timeout: 30000
      });

      // Extract data using provided selectors
      const extractedData = await page.evaluate((selectorMap) => {
        const results = {};
        
        for (const [key, selector] of Object.entries(selectorMap)) {
          try {
            const elements = document.querySelectorAll(selector);
            
            if (elements.length === 0) {
              results[key] = null;
            } else if (elements.length === 1) {
              // Single element - return direct value
              const element = elements[0];
              results[key] = {
                text: element.textContent?.trim() || '',
                html: element.innerHTML,
                attributes: {
                  href: element.href || null,
                  src: element.src || null,
                  alt: element.alt || null,
                  title: element.title || null
                }
              };
            } else {
              // Multiple elements - return array
              results[key] = Array.from(elements).map(element => ({
                text: element.textContent?.trim() || '',
                html: element.innerHTML,
                attributes: {
                  href: element.href || null,
                  src: element.src || null,
                  alt: element.alt || null,
                  title: element.title || null
                }
              }));
            }
          } catch (error) {
            results[key] = { error: error.message };
          }
        }
        
        return results;
      }, selectors);

      const duration = Date.now() - startTime;
      
      return {
        status: 'success',
        url,
        selectors,
        data: extractedData,
        duration_ms: duration,
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(`❌ Extraction failed for ${url}:`, error.message);
      
      return {
        status: 'error',
        url,
        selectors,
        error: error.message,
        duration_ms: duration,
        timestamp: new Date().toISOString()
      };
    }
  }

  // Helper method for common extraction patterns
  static commonSelectors = {
    title: 'title, h1',
    description: 'meta[name="description"], .description, .summary',
    price: '.price, [data-price], .cost',
    images: 'img[src]',
    links: 'a[href]',
    articles: 'article, .article, .post',
    navigation: 'nav a, .nav a, .menu a',
    tables: 'table',
    forms: 'form',
    buttons: 'button, .button, input[type="submit"]'
  };
}