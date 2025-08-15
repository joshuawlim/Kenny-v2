// Web Interaction Handler - Perform actions on webpage elements
export class WebInteractHandler {
  async handle({ page, url, actions }) {
    const startTime = Date.now();
    const actionResults = [];
    
    try {
      console.log(`⚡ Interacting with: ${url}`);
      
      // Navigate to URL
      await page.goto(url, {
        waitUntil: 'networkidle2',
        timeout: 30000
      });

      // Execute each action sequentially
      for (let i = 0; i < actions.length; i++) {
        const action = actions[i];
        const actionStart = Date.now();
        
        try {
          const result = await this.executeAction(page, action);
          actionResults.push({
            action_index: i,
            action_type: action.type,
            status: 'success',
            result,
            duration_ms: Date.now() - actionStart
          });
          
          // Small delay between actions
          await page.waitForTimeout(500);
          
        } catch (error) {
          console.error(`❌ Action ${i} failed:`, error.message);
          actionResults.push({
            action_index: i,
            action_type: action.type,
            status: 'error',
            error: error.message,
            duration_ms: Date.now() - actionStart
          });
          
          // Continue with next action unless it's a critical failure
          if (action.critical) {
            throw error;
          }
        }
      }

      // Take final screenshot
      const screenshot = await page.screenshot({
        type: 'png',
        encoding: 'base64',
        fullPage: false
      });

      const duration = Date.now() - startTime;
      
      return {
        status: 'success',
        url,
        actions_completed: actionResults.filter(r => r.status === 'success').length,
        actions_failed: actionResults.filter(r => r.status === 'error').length,
        action_results: actionResults,
        final_screenshot: screenshot,
        duration_ms: duration,
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(`❌ Interaction failed for ${url}:`, error.message);
      
      return {
        status: 'error',
        url,
        actions,
        action_results: actionResults,
        error: error.message,
        duration_ms: duration,
        timestamp: new Date().toISOString()
      };
    }
  }

  async executeAction(page, action) {
    const { type, selector, value, options = {} } = action;
    
    console.log(`🎯 Executing: ${type} on ${selector}`);
    
    // Wait for element to be available
    await page.waitForSelector(selector, { timeout: 10000 });
    
    switch (type) {
      case 'click':
        await page.click(selector, options);
        return { action: 'clicked', selector };
      
      case 'type':
        if (!value) throw new Error('Value required for type action');
        await page.type(selector, value, options);
        return { action: 'typed', selector, value };
      
      case 'fill':
        if (!value) throw new Error('Value required for fill action');
        await page.fill(selector, value);
        return { action: 'filled', selector, value };
      
      case 'select':
        if (!value) throw new Error('Value required for select action');
        await page.selectOption(selector, value);
        return { action: 'selected', selector, value };
      
      case 'hover':
        await page.hover(selector);
        return { action: 'hovered', selector };
      
      case 'scroll':
        await page.evaluate((sel) => {
          const element = document.querySelector(sel);
          if (element) element.scrollIntoView();
        }, selector);
        return { action: 'scrolled', selector };
      
      case 'wait':
        const timeout = options.timeout || 3000;
        await page.waitForTimeout(timeout);
        return { action: 'waited', timeout };
      
      case 'screenshot':
        const screenshot = await page.screenshot({
          type: 'png',
          encoding: 'base64',
          ...options
        });
        return { action: 'screenshot', data: screenshot };
      
      case 'evaluate':
        if (!value) throw new Error('JavaScript code required for evaluate action');
        const result = await page.evaluate(value);
        return { action: 'evaluated', code: value, result };
      
      case 'extract_text':
        const text = await page.textContent(selector);
        return { action: 'extracted_text', selector, text };
      
      case 'extract_attribute':
        const attribute = options.attribute || 'href';
        const attrValue = await page.getAttribute(selector, attribute);
        return { action: 'extracted_attribute', selector, attribute, value: attrValue };
      
      default:
        throw new Error(`Unknown action type: ${type}`);
    }
  }

  // Predefined action sequences for common workflows
  static commonWorkflows = {
    login: (username, password, loginUrl) => [
      { type: 'fill', selector: 'input[name="username"], input[name="email"], #username, #email', value: username },
      { type: 'fill', selector: 'input[name="password"], #password', value: password },
      { type: 'click', selector: 'button[type="submit"], .login-button, #login' }
    ],
    
    search: (query) => [
      { type: 'fill', selector: 'input[type="search"], input[name="q"], .search-input', value: query },
      { type: 'click', selector: 'button[type="submit"], .search-button' }
    ],
    
    form_fill: (formData) => Object.entries(formData).map(([field, value]) => ({
      type: 'fill',
      selector: `input[name="${field}"], #${field}`,
      value
    }))
  };
}