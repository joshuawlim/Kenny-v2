// Web Monitoring Handler - Monitor webpages for changes
export class WebMonitorHandler {
  constructor() {
    this.monitoringSessions = new Map();
  }

  async handle({ browser, url, interval = 300 }) {
    const sessionId = this.generateSessionId();
    
    try {
      console.log(`📊 Starting monitor session ${sessionId} for: ${url}`);
      
      // Create initial snapshot
      const page = await browser.newPage();
      const initialSnapshot = await this.createSnapshot(page, url);
      await page.close();

      // Set up monitoring interval
      const monitoringSession = {
        id: sessionId,
        url,
        interval,
        startTime: Date.now(),
        lastCheck: Date.now(),
        snapshots: [initialSnapshot],
        changes: [],
        active: true
      };

      this.monitoringSessions.set(sessionId, monitoringSession);

      // Start monitoring loop
      this.startMonitoringLoop(browser, sessionId);

      return {
        status: 'success',
        session_id: sessionId,
        url,
        interval,
        initial_snapshot: initialSnapshot,
        message: `Monitoring started for ${url} with ${interval}s interval`,
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      console.error(`❌ Monitor setup failed for ${url}:`, error.message);
      
      return {
        status: 'error',
        url,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }

  async createSnapshot(page, url) {
    const startTime = Date.now();
    
    try {
      await page.goto(url, {
        waitUntil: 'networkidle2',
        timeout: 30000
      });

      // Extract key content for comparison
      const snapshot = await page.evaluate(() => {
        // Remove dynamic content that changes frequently
        const excludeSelectors = [
          'script',
          '.ad', '.advertisement',
          '.timestamp', '.time',
          '.live-update',
          '[data-timestamp]'
        ];

        // Clone body and remove excluded elements
        const body = document.body.cloneNode(true);
        excludeSelectors.forEach(selector => {
          body.querySelectorAll(selector).forEach(el => el.remove());
        });

        return {
          title: document.title,
          url: window.location.href,
          content_hash: this.hashContent(body.textContent),
          dom_hash: this.hashContent(body.innerHTML),
          meta: {
            description: document.querySelector('meta[name="description"]')?.content || '',
            lastModified: document.lastModified
          },
          key_elements: {
            headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.textContent.trim()),
            links: Array.from(document.querySelectorAll('a[href]')).slice(0, 20).map(a => a.href),
            images: Array.from(document.querySelectorAll('img[src]')).slice(0, 10).map(img => img.src)
          }
        };
      });

      // Add timing info
      snapshot.timestamp = new Date().toISOString();
      snapshot.load_time = Date.now() - startTime;

      return snapshot;

    } catch (error) {
      return {
        timestamp: new Date().toISOString(),
        error: error.message,
        load_time: Date.now() - startTime
      };
    }
  }

  async startMonitoringLoop(browser, sessionId) {
    const session = this.monitoringSessions.get(sessionId);
    if (!session || !session.active) return;

    const checkForChanges = async () => {
      try {
        const page = await browser.newPage();
        const newSnapshot = await this.createSnapshot(page, session.url);
        await page.close();

        const lastSnapshot = session.snapshots[session.snapshots.length - 1];
        const changes = this.detectChanges(lastSnapshot, newSnapshot);

        if (changes.hasChanges) {
          console.log(`🔄 Changes detected for ${session.url}:`, changes.summary);
          session.changes.push({
            timestamp: new Date().toISOString(),
            changes: changes.details,
            summary: changes.summary
          });
        }

        session.snapshots.push(newSnapshot);
        session.lastCheck = Date.now();

        // Keep only last 10 snapshots to save memory
        if (session.snapshots.length > 10) {
          session.snapshots = session.snapshots.slice(-10);
        }

      } catch (error) {
        console.error(`❌ Monitor check failed for ${session.url}:`, error.message);
      }

      // Schedule next check
      if (session.active) {
        setTimeout(checkForChanges, session.interval * 1000);
      }
    };

    // Start first check after interval
    setTimeout(checkForChanges, session.interval * 1000);
  }

  detectChanges(oldSnapshot, newSnapshot) {
    const changes = {
      hasChanges: false,
      details: [],
      summary: ''
    };

    if (!oldSnapshot || oldSnapshot.error || newSnapshot.error) {
      return changes;
    }

    // Check title changes
    if (oldSnapshot.title !== newSnapshot.title) {
      changes.hasChanges = true;
      changes.details.push({
        type: 'title_change',
        old: oldSnapshot.title,
        new: newSnapshot.title
      });
    }

    // Check content hash changes
    if (oldSnapshot.content_hash !== newSnapshot.content_hash) {
      changes.hasChanges = true;
      changes.details.push({
        type: 'content_change',
        description: 'Page content has changed'
      });
    }

    // Check DOM structure changes
    if (oldSnapshot.dom_hash !== newSnapshot.dom_hash) {
      changes.hasChanges = true;
      changes.details.push({
        type: 'structure_change',
        description: 'Page structure has changed'
      });
    }

    // Check heading changes
    const oldHeadings = oldSnapshot.key_elements?.headings || [];
    const newHeadings = newSnapshot.key_elements?.headings || [];
    if (JSON.stringify(oldHeadings) !== JSON.stringify(newHeadings)) {
      changes.hasChanges = true;
      changes.details.push({
        type: 'headings_change',
        old_count: oldHeadings.length,
        new_count: newHeadings.length
      });
    }

    // Create summary
    if (changes.hasChanges) {
      changes.summary = `${changes.details.length} change(s) detected: ${changes.details.map(c => c.type).join(', ')}`;
    }

    return changes;
  }

  // Get monitoring session status
  getSession(sessionId) {
    const session = this.monitoringSessions.get(sessionId);
    if (!session) {
      return { error: 'Session not found' };
    }

    return {
      id: session.id,
      url: session.url,
      interval: session.interval,
      active: session.active,
      runtime: Date.now() - session.startTime,
      snapshots_count: session.snapshots.length,
      changes_count: session.changes.length,
      last_check: session.lastCheck,
      recent_changes: session.changes.slice(-5)
    };
  }

  // Stop monitoring session
  stopSession(sessionId) {
    const session = this.monitoringSessions.get(sessionId);
    if (session) {
      session.active = false;
      this.monitoringSessions.delete(sessionId);
      return { message: `Monitoring stopped for session ${sessionId}` };
    }
    return { error: 'Session not found' };
  }

  generateSessionId() {
    return `monitor_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Simple hash function for content comparison
  hashContent(content) {
    let hash = 0;
    if (!content || content.length === 0) return hash;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash;
  }
}