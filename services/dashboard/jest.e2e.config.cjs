// Jest configuration specifically for E2E tests
module.exports = {
  preset: 'jest-puppeteer',
  testMatch: ['**/e2e/**/*.test.js', '**/e2e/**/*.test.ts'],
  setupFilesAfterEnv: ['<rootDir>/e2e/setup.js'],
  testTimeout: 30000,
  globalSetup: '<rootDir>/e2e/global-setup.js',
  globalTeardown: '<rootDir>/e2e/global-teardown.js',
  collectCoverage: false,
  verbose: true,
  testEnvironment: 'node'
};