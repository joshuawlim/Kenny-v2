# Kenny UI Development Makefile

.PHONY: install dev build test test-watch test-e2e clean lint type-check storybook help

# Default target
all: install dev

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	npm install

# Development server
dev:
	@echo "🚀 Starting development server..."
	npm run dev

# Build for production
build:
	@echo "🏗️  Building for production..."
	npm run build

# Run all tests
test:
	@echo "🧪 Running unit tests..."
	npm run test

# Run tests in watch mode
test-watch:
	@echo "👀 Running tests in watch mode..."
	npm run test:watch

# Run end-to-end tests
test-e2e:
	@echo "🎭 Running E2E tests..."
	npm run test:e2e

# Run tests with UI
test-ui:
	@echo "🖥️  Running tests with UI..."
	npm run test:e2e:ui

# Development with tests
dev-all:
	@echo "🚀 Starting development with tests..."
	npm run dev:all

# Lint code
lint:
	@echo "🔍 Linting code..."
	npm run lint

# Type checking
type-check:
	@echo "📝 Type checking..."
	npm run type-check

# Start Storybook
storybook:
	@echo "📚 Starting Storybook..."
	npm run storybook

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf .next dist node_modules/.cache

# Format code
format:
	@echo "💅 Formatting code..."
	npx prettier --write "src/**/*.{ts,tsx,js,jsx,json,css,md}"

# Verify everything works
verify: lint type-check test build
	@echo "✅ All checks passed!"

# Start Kenny backend services (requires Docker)
backend:
	@echo "🤖 Starting Kenny backend services..."
	cd ../.. && ./kenny-launch.sh

# Full development setup
setup: install backend dev-all

# Help
help:
	@echo "Kenny UI Development Commands:"
	@echo ""
	@echo "  install      Install dependencies"
	@echo "  dev          Start development server"
	@echo "  dev-all      Start dev server with tests"
	@echo "  build        Build for production"
	@echo "  test         Run unit tests"
	@echo "  test-watch   Run tests in watch mode"
	@echo "  test-e2e     Run E2E tests"
	@echo "  test-ui      Run E2E tests with UI"
	@echo "  lint         Lint code"
	@echo "  type-check   Check TypeScript types"
	@echo "  format       Format code with Prettier"
	@echo "  storybook    Start Storybook"
	@echo "  verify       Run all checks"
	@echo "  backend      Start Kenny backend services"
	@echo "  setup        Full development setup"
	@echo "  clean        Clean build artifacts"
	@echo "  help         Show this help"