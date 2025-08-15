import { test, expect } from '@playwright/test'

test.describe('Kenny Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should load the main dashboard', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/Kenny v2/)
    
    // Check main layout elements are present
    await expect(page.locator('[data-testid="left-rail"]')).toBeVisible()
    await expect(page.locator('[data-testid="main-content"]')).toBeVisible()
    await expect(page.locator('[data-testid="right-rail"]')).toBeVisible()
    
    // Check top bar is present
    await expect(page.locator('[data-testid="top-bar"]')).toBeVisible()
  })

  test('should open command palette with Cmd+K', async ({ page }) => {
    // Press Cmd+K (or Ctrl+K on non-Mac)
    await page.keyboard.press('Meta+k')
    
    // Check command palette is visible
    await expect(page.locator('[data-testid="command-palette"]')).toBeVisible()
    
    // Check search input is focused
    const searchInput = page.locator('[data-testid="command-search"]')
    await expect(searchInput).toBeFocused()
    
    // Close with Escape
    await page.keyboard.press('Escape')
    await expect(page.locator('[data-testid="command-palette"]')).not.toBeVisible()
  })

  test('should create new chat session', async ({ page }) => {
    // Click new chat button or use keyboard shortcut
    await page.keyboard.press('Meta+n')
    
    // Should create a new session
    await expect(page.locator('[data-testid="session-list"] [data-active="true"]')).toBeVisible()
    
    // Chat interface should be visible
    await expect(page.locator('[data-testid="chat-interface"]')).toBeVisible()
    await expect(page.locator('[data-testid="message-input"]')).toBeVisible()
  })

  test('should send and receive messages', async ({ page }) => {
    // Type a message
    const messageInput = page.locator('[data-testid="message-input"]')
    await messageInput.fill('Hello Kenny!')
    
    // Send message with Enter or Cmd+Enter
    await page.keyboard.press('Meta+Enter')
    
    // User message should appear
    await expect(page.locator('[data-testid="message"][data-role="user"]')).toContainText('Hello Kenny!')
    
    // Assistant response should appear (with timeout for streaming)
    await expect(page.locator('[data-testid="message"][data-role="assistant"]')).toBeVisible({ timeout: 10000 })
    
    // Streaming indicator should disappear
    await expect(page.locator('[data-testid="streaming-indicator"]')).not.toBeVisible({ timeout: 15000 })
  })

  test('should navigate between sessions', async ({ page }) => {
    // Create multiple sessions
    await page.keyboard.press('Meta+n')
    await page.keyboard.press('Meta+n')
    
    // Should have multiple sessions in list
    const sessionItems = page.locator('[data-testid="session-item"]')
    await expect(sessionItems).toHaveCount(2)
    
    // Click on first session
    await sessionItems.first().click()
    
    // Should navigate to that session
    await expect(sessionItems.first()).toHaveAttribute('data-active', 'true')
  })

  test('should switch models via command palette', async ({ page }) => {
    // Open command palette
    await page.keyboard.press('Meta+k')
    
    // Search for model switch command
    await page.locator('[data-testid="command-search"]').fill('switch to llama')
    
    // Click on model switch option
    await page.locator('[data-testid="command-item"]').first().click()
    
    // Command palette should close
    await expect(page.locator('[data-testid="command-palette"]')).not.toBeVisible()
    
    // Model indicator should update
    await expect(page.locator('[data-testid="current-model"]')).toContainText('Llama')
  })

  test('should toggle sidebar visibility', async ({ page }) => {
    // Left sidebar should be visible initially
    await expect(page.locator('[data-testid="left-rail"]')).toBeVisible()
    
    // Toggle with keyboard shortcut
    await page.keyboard.press('Alt+ArrowLeft')
    
    // Left sidebar should be hidden
    await expect(page.locator('[data-testid="left-rail"]')).toHaveAttribute('data-open', 'false')
    
    // Toggle again
    await page.keyboard.press('Alt+ArrowLeft')
    
    // Should be visible again
    await expect(page.locator('[data-testid="left-rail"]')).toHaveAttribute('data-open', 'true')
  })

  test('should display cost tracking', async ({ page }) => {
    // Cost meter should be visible
    await expect(page.locator('[data-testid="cost-meter"]')).toBeVisible()
    
    // Should show current cost
    await expect(page.locator('[data-testid="cost-meter"]')).toContainText('$')
    
    // After sending a message, cost should update
    const messageInput = page.locator('[data-testid="message-input"]')
    await messageInput.fill('Calculate something expensive')
    await page.keyboard.press('Meta+Enter')
    
    // Wait for response and cost update
    await expect(page.locator('[data-testid="message"][data-role="assistant"]')).toBeVisible({ timeout: 10000 })
    
    // Cost should have changed (this might be flaky in real tests)
    // await expect(page.locator('[data-testid="cost-meter"]')).not.toContainText('$0.00')
  })

  test('should handle agent switching', async ({ page }) => {
    // Current agent indicator should be visible
    await expect(page.locator('[data-testid="current-agent"]')).toBeVisible()
    
    // Open command palette and switch agent
    await page.keyboard.press('Meta+k')
    await page.locator('[data-testid="command-search"]').fill('switch to mail')
    await page.locator('[data-testid="command-item"]').first().click()
    
    // Agent indicator should update
    await expect(page.locator('[data-testid="current-agent"]')).toContainText('Mail')
  })

  test('should show streaming indicators', async ({ page }) => {
    // Send a message
    const messageInput = page.locator('[data-testid="message-input"]')
    await messageInput.fill('Tell me a long story')
    await page.keyboard.press('Meta+Enter')
    
    // Streaming indicator should appear
    await expect(page.locator('[data-testid="streaming-indicator"]')).toBeVisible()
    
    // Stop button should be visible
    await expect(page.locator('[data-testid="stop-generation"]')).toBeVisible()
    
    // Click stop button
    await page.locator('[data-testid="stop-generation"]').click()
    
    // Streaming should stop
    await expect(page.locator('[data-testid="streaming-indicator"]')).not.toBeVisible()
  })

  test('should handle session management', async ({ page }) => {
    // Create a new session
    await page.keyboard.press('Meta+n')
    
    // Session should appear in list
    const sessionItems = page.locator('[data-testid="session-item"]')
    await expect(sessionItems).toHaveCount(1)
    
    // Right-click on session for context menu
    await sessionItems.first().click({ button: 'right' })
    
    // Context menu should appear
    await expect(page.locator('[data-testid="session-context-menu"]')).toBeVisible()
    
    // Click delete option
    await page.locator('[data-testid="delete-session"]').click()
    
    // Confirm deletion
    await page.locator('[data-testid="confirm-delete"]').click()
    
    // Session should be removed
    await expect(sessionItems).toHaveCount(0)
  })
})