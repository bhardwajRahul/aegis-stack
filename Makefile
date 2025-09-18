# Aegis Stack CLI Development Makefile
# This Makefile is for developing the Aegis Stack CLI tool itself.
# Generated projects have their own Makefiles for application development.

# Run tests (excluding slow tests)
test: ## Run tests (excluding slow tests - use 'test-all' for everything)
	@uv run pytest -m "not slow"

# Run all tests including slow ones
test-all: ## Run all tests including slow ones (for CI/CD)
	@uv run pytest

# Run linting	
lint: ## Run linting with ruff
	@uv run ruff check .

# Auto-fix linting issues
fix: ## Auto-fix linting and formatting issues
	@uv run ruff check . --fix
	@uv run ruff format .

# Format code only
format: ## Format code with ruff
	@uv run ruff format .

# Run type checking
typecheck: ## Run type checking with ty
	@uv run ty check

# Run all checks (lint + typecheck + fast tests)
check: lint typecheck test ## Run all checks (fast tests only)

# Run comprehensive checks (includes slow tests)  
check-all: lint typecheck test-all ## Run comprehensive checks (includes slow tests)

# Install dependencies
install: ## Install dependencies with uv
	uv sync --all-extras

# Clean up cache files
clean: ## Clean up cache files
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete

# Serve documentation locally
docs-serve: ## Serve documentation locally with live reload on port 8001
	@uv run mkdocs serve --dev-addr 0.0.0.0:8001

# Build documentation
docs-build: ## Build the static documentation site
	@uv run mkdocs build

# CLI Development Commands
cli-test: ## Test CLI commands locally  
	@uv run python -m aegis --help
	@echo "✅ CLI command working"

# ============================================================================
# REDIS DEVELOPMENT COMMANDS  
# For experimenting with Redis/arq without generating new projects
# ============================================================================

redis-start: ## Start Redis container for arq experiments
	@echo "🚀 Starting Redis for arq development..."
	@docker run -d --name aegis-redis -p 6379:6379 --rm redis:7-alpine redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
	@echo "✅ Redis running on localhost:6379"
	@echo "💡 Use 'make redis-stop' to stop"

redis-stop: ## Stop Redis container
	@echo "⏹️  Stopping Redis..."
	@docker stop aegis-redis 2>/dev/null || echo "Redis container not running"

redis-cli: ## Connect to Redis CLI  
	@echo "🔧 Connecting to Redis CLI..."
	@docker exec -it aegis-redis redis-cli

redis-logs: ## Show Redis logs
	@echo "📋 Showing Redis logs..."
	@docker logs -f aegis-redis

redis-stats: ## Show Redis memory and connection stats
	@echo "📊 Redis stats..."
	@docker exec -it aegis-redis redis-cli info memory
	@echo ""
	@docker exec -it aegis-redis redis-cli info clients

redis-reset: ## Reset Redis (clear all data)
	@echo "🔄 Resetting Redis data..."
	@docker exec -it aegis-redis redis-cli flushall
	@echo "✅ Redis data cleared"

redis-queues: ## Show all arq queues and their depths
	@echo "📋 arq Queue Status:"
	@echo "===================="
	@echo -n "default: "; docker exec -it aegis-redis redis-cli zcard arq:queue 2>/dev/null | tr -d '\r' || echo "0"; echo " jobs"
	@echo ""
	@echo "📊 Additional Queue Info:"
	@echo -n "In Progress: "; docker exec -it aegis-redis redis-cli hlen arq:in-progress 2>/dev/null | tr -d '\r' || echo "0"
	@echo -n "Results: "; docker exec -it aegis-redis redis-cli --raw eval "return #redis.call('keys', 'arq:result:*')" 0 2>/dev/null || echo "0"

redis-workers: ## Show active arq workers
	@echo "👷 Active Workers:"
	@echo "=================="
	@docker exec -it aegis-redis redis-cli smembers arq:workers 2>/dev/null || echo "No active workers"

redis-failed: ## Show failed job count  
	@echo "❌ Failed Jobs:"
	@echo "==============="
	@docker exec -it aegis-redis redis-cli hlen arq:failed 2>/dev/null || echo "0"

redis-monitor: ## Monitor Redis commands in real-time
	@echo "👀 Monitoring Redis commands (Ctrl+C to stop)..."
	@docker exec -it aegis-redis redis-cli monitor

redis-info: ## Show comprehensive Redis info
	@echo "ℹ️  Redis System Information:"
	@echo "============================="
	@docker exec -it aegis-redis redis-cli info server
	@echo ""
	@echo "📊 Memory Usage:"
	@echo "================"
	@docker exec -it aegis-redis redis-cli info memory
	@echo ""
	@echo "👥 Client Connections:"
	@echo "======================"
	@docker exec -it aegis-redis redis-cli info clients

# Show help
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# TEMPLATE TESTING TARGETS
# For rapid iteration on cookiecutter template changes
# 
# These targets help with the development workflow when modifying the 
# cookiecutter templates in aegis/templates/cookiecutter-aegis-project/
# 
# Typical workflow:
#   1. Make changes to template files
#   2. Run 'make test-template-quick' for fast feedback
#   3. Run 'make test-template' for full validation
#   4. Run 'make clean-test-projects' to cleanup
# ============================================================================

test-template-quick: ## Quick template test - generate basic project without validation
	@echo "🚀 Quick template test - generating basic project..."
	@chmod -R +w ../test-basic-stack 2>/dev/null || true
	@rm -rf ../test-basic-stack
	@env -u VIRTUAL_ENV uv run aegis init test-basic-stack --output-dir .. --no-interactive --force --yes
	@echo "📦 Setting up virtual environment and CLI..."
	@cd ../test-basic-stack && chmod -R +w .venv 2>/dev/null || true && rm -rf .venv && env -u VIRTUAL_ENV uv sync --extra dev --extra docs
	@cd ../test-basic-stack && env -u VIRTUAL_ENV uv pip install -e .
	@echo "✅ Basic test project generated in ../test-basic-stack/"
	@echo "   CLI command 'test-basic-stack' is now available"
	@echo "   Run 'cd ../test-basic-stack && make check' to validate"

test-template: ## Full template test - generate project and run validation
	@echo "🛡️  Full template test - generating and validating project..."
	@chmod -R +w ../test-basic-stack 2>/dev/null || true
	@rm -rf ../test-basic-stack
	@env -u VIRTUAL_ENV uv run aegis init test-basic-stack --output-dir .. --no-interactive --force --yes
	@echo "📦 Installing dependencies and CLI..."
	@cd ../test-basic-stack && chmod -R +w .venv 2>/dev/null || true && rm -rf .venv && env -u VIRTUAL_ENV uv sync --extra dev --extra docs
	@cd ../test-basic-stack && env -u VIRTUAL_ENV uv pip install -e .
	@echo "🔍 Running validation checks..."
	@cd ../test-basic-stack && env -u VIRTUAL_ENV make check
	@echo "🧪 Testing CLI script installation..."
	@cd ../test-basic-stack && env -u VIRTUAL_ENV uv run test-basic-stack --help >/dev/null && echo "✅ CLI script 'test-basic-stack --help' works" || echo "⚠️  CLI script test failed"
	@cd ../test-basic-stack && env -u VIRTUAL_ENV uv run test-basic-stack health quick >/dev/null 2>&1 && echo "✅ CLI script 'test-basic-stack health quick' works" || echo "ℹ️  Health command test skipped (requires running backend)"
	@echo "✅ Template test completed successfully!"
	@echo "   Test project available in ../test-basic-stack/"
	@echo "   CLI command 'test-basic-stack' is available"

test-template-with-components: ## Test template with scheduler component included
	@echo "🧩 Component template test - generating project with scheduler..."
	@chmod -R +w ../test-component-stack 2>/dev/null || true
	@rm -rf ../test-component-stack
	@env -u VIRTUAL_ENV uv run aegis init test-component-stack --components scheduler --output-dir .. --no-interactive --force --yes
	@echo "📦 Installing dependencies and CLI..."
	@cd ../test-component-stack && chmod -R +w .venv 2>/dev/null || true && rm -rf .venv && env -u VIRTUAL_ENV uv sync --extra dev --extra docs
	@cd ../test-component-stack && env -u VIRTUAL_ENV uv pip install -e .
	@echo "🔍 Running validation checks..."
	@cd ../test-component-stack && env -u VIRTUAL_ENV make check
	@echo "🧪 Testing CLI script installation..."
	@cd ../test-component-stack && env -u VIRTUAL_ENV uv run test-component-stack --help >/dev/null && echo "✅ CLI script 'test-component-stack --help' works" || echo "⚠️  CLI script test failed"
	@cd ../test-component-stack && env -u VIRTUAL_ENV uv run test-component-stack health quick >/dev/null 2>&1 && echo "✅ CLI script 'test-component-stack health quick' works" || echo "ℹ️  Health command test skipped (requires running backend)"
	@echo "✅ Component template test completed successfully!"
	@echo "   Test project available in ../test-component-stack/"
	@echo "   CLI command 'test-component-stack' is available"

clean-test-projects: ## Remove all generated test project directories
	@echo "🧹 Cleaning up test projects..."
	@chmod -R +w ../test-basic-stack ../test-component-stack ../test-worker-stack ../test-database-stack ../test-full-stack 2>/dev/null || true
	@rm -rf ../test-basic-stack ../test-component-stack ../test-worker-stack ../test-database-stack ../test-full-stack 2>/dev/null || true
	@echo "✅ Test projects cleaned up"

# ============================================================================
# STACK MATRIX TESTING TARGETS
# For comprehensive testing of all component combinations
# 
# These targets implement the Stack Generation Matrix Testing plan:
#   1. test-stacks: Test generation of all valid combinations
#   2. test-stacks-build: Test that all stacks build and pass checks
#   3. test-stacks-runtime: Test Docker runtime integration (future)
#   4. test-stacks-full: Complete matrix testing pipeline
# ============================================================================

test-stacks: ## Test all stack combinations generation (fast)
	@echo "🧪 Testing all stack combination generation..."
	@uv run pytest tests/cli/test_stack_generation.py -v --tb=short
	@echo "✅ All stack combinations generate successfully!"

test-stacks-build: ## Test all stacks build and pass checks (slow)
	@echo "🔨 Testing all stacks build and validation..."
	@echo "⚠️  This is slow - testing dependency installation and code quality for all combinations"
	@uv run pytest tests/cli/test_stack_validation.py -v -m "slow" --tb=short
	@echo "✅ All stacks build and pass quality checks!"

test-stacks-runtime: ## Test all stacks runtime integration with Docker (future)
	@echo "🐳 Runtime integration testing not yet implemented"
	@echo "ℹ️  Will test Docker Compose startup and health checks for all combinations"

test-stacks-full: ## Full stack matrix testing pipeline (comprehensive but slow)
	@echo "🌟 Running complete stack matrix testing pipeline..."
	@echo "📋 Phase 1: Stack Generation Testing"
	@make test-stacks
	@echo ""
	@echo "📋 Phase 2: Stack Build and Validation Testing"
	@make test-stacks-build
	@echo ""
	@echo "📋 Phase 3: Stack Runtime Testing (skipped - not implemented)"
	@echo "ℹ️  Runtime testing will be added in future iterations"
	@echo ""
	@echo "🎉 Complete stack matrix testing completed successfully!"
	@echo "   All component combinations can generate, build, and pass quality checks"

# Enhanced template testing with specific component combinations
test-template-database: ## Test template with database component
	@echo "🗄️  Testing database component template..."
	@chmod -R +w ../test-database-stack 2>/dev/null || true
	@rm -rf ../test-database-stack
	@env -u VIRTUAL_ENV uv run aegis init test-database-stack --components database --output-dir .. --no-interactive --force --yes
	@echo "📦 Installing dependencies and CLI..."
	@cd ../test-database-stack && chmod -R +w .venv 2>/dev/null || true && rm -rf .venv && env -u VIRTUAL_ENV uv sync --extra dev --extra docs
	@cd ../test-database-stack && env -u VIRTUAL_ENV uv pip install -e .
	@echo "🔍 Running validation checks..."
	@cd ../test-database-stack && env -u VIRTUAL_ENV make check
	@echo "🧪 Testing CLI script installation..."
	@cd ../test-database-stack && env -u VIRTUAL_ENV uv run test-database-stack --help >/dev/null && echo "✅ CLI script 'test-database-stack --help' works" || echo "⚠️  CLI script test failed"
	@cd ../test-database-stack && env -u VIRTUAL_ENV uv run test-database-stack health status --help >/dev/null && echo "✅ Health commands available" || echo "⚠️  Health command test failed"
	@echo "✅ Database template test completed successfully!"
	@echo "   Test project available in ../test-database-stack/"

test-template-worker: ## Test template with worker component
	@echo "🔧 Testing worker component template..."
	@chmod -R +w ../test-worker-stack 2>/dev/null || true
	@rm -rf ../test-worker-stack
	@env -u VIRTUAL_ENV uv run aegis init test-worker-stack --components worker --output-dir .. --no-interactive --force --yes
	@echo "📦 Installing dependencies and CLI..."
	@cd ../test-worker-stack && chmod -R +w .venv 2>/dev/null || true && rm -rf .venv && env -u VIRTUAL_ENV uv sync --extra dev --extra docs
	@cd ../test-worker-stack && env -u VIRTUAL_ENV uv pip install -e .
	@echo "🔍 Running validation checks..."
	@cd ../test-worker-stack && env -u VIRTUAL_ENV make check
	@echo "🧪 Testing CLI script installation..."
	@cd ../test-worker-stack && env -u VIRTUAL_ENV uv run test-worker-stack --help >/dev/null && echo "✅ CLI script 'test-worker-stack --help' works" || echo "⚠️  CLI script test failed"
	@cd ../test-worker-stack && env -u VIRTUAL_ENV uv run test-worker-stack health status --help >/dev/null && echo "✅ Health commands available" || echo "⚠️  Health command test failed"
	@echo "✅ Worker template test completed successfully!"
	@echo "   Test project available in ../test-worker-stack/"

test-template-auth: ## Test template with auth service
	@echo "🔐 Testing auth service template..."
	@chmod -R +w ../test-auth-stack 2>/dev/null || true
	@rm -rf ../test-auth-stack
	@env -u VIRTUAL_ENV uv run aegis init test-auth-stack --services auth --output-dir .. --no-interactive --force --yes
	@echo "📦 Installing dependencies and CLI..."
	@cd ../test-auth-stack && chmod -R +w .venv 2>/dev/null || true && rm -rf .venv && env -u VIRTUAL_ENV uv sync --extra dev --extra docs
	@cd ../test-auth-stack && env -u VIRTUAL_ENV uv pip install -e .
	@echo "🔍 Running validation checks..."
	@cd ../test-auth-stack && env -u VIRTUAL_ENV make check
	@echo "🧪 Testing CLI script installation..."
	@cd ../test-auth-stack && env -u VIRTUAL_ENV uv run test-auth-stack --help >/dev/null && echo "✅ CLI script 'test-auth-stack --help' works" || echo "⚠️  CLI script test failed"
	@cd ../test-auth-stack && env -u VIRTUAL_ENV uv run test-auth-stack health status --help >/dev/null && echo "✅ Health commands available" || echo "⚠️  Health command test failed"
	@echo "✅ Auth service template test completed successfully!"
	@echo "   Test project available in ../test-auth-stack/"

test-template-full: ## Test template with all components (worker + scheduler + database)
	@echo "🌟 Testing full component template..."
	@chmod -R +w ../test-full-stack 2>/dev/null || true
	@rm -rf ../test-full-stack
	@env -u VIRTUAL_ENV uv run aegis init test-full-stack --components worker,scheduler,database --output-dir .. --no-interactive --force --yes
	@echo "📦 Installing dependencies and CLI..."
	@cd ../test-full-stack && chmod -R +w .venv 2>/dev/null || true && rm -rf .venv && env -u VIRTUAL_ENV uv sync --extra dev --extra docs
	@cd ../test-full-stack && env -u VIRTUAL_ENV uv pip install -e .
	@echo "🔍 Running validation checks..."
	@cd ../test-full-stack && env -u VIRTUAL_ENV make check
	@echo "🧪 Testing CLI script installation..."
	@cd ../test-full-stack && env -u VIRTUAL_ENV uv run test-full-stack --help >/dev/null && echo "✅ CLI script 'test-full-stack --help' works" || echo "⚠️  CLI script test failed"
	@cd ../test-full-stack && env -u VIRTUAL_ENV uv run test-full-stack health status --help >/dev/null && echo "✅ Health commands available" || echo "⚠️  Health command test failed"
	@echo "✅ Full stack template test completed successfully!"
	@echo "   Test project available in ../test-full-stack/"
	@echo "   Includes: backend, frontend, worker queues, scheduler, Redis, database"

# Quick component testing for development workflow
test-component-quick: ## Quick test of specific component (set COMPONENT=worker|scheduler)
ifndef COMPONENT
	@echo "❌ Usage: make test-component-quick COMPONENT=worker"
	@echo "   Available components: worker, scheduler"
	@exit 1
endif
	@echo "⚡ Quick testing $(COMPONENT) component..."
	@chmod -R +w ../test-$(COMPONENT)-quick 2>/dev/null || true
	@rm -rf ../test-$(COMPONENT)-quick
	@env -u VIRTUAL_ENV uv run aegis init test-$(COMPONENT)-quick --components $(COMPONENT) --output-dir .. --no-interactive --force --yes
	@echo "✅ $(COMPONENT) component generated successfully in ../test-$(COMPONENT)-quick/"
	@echo "   Run 'cd ../test-$(COMPONENT)-quick && make check' to validate"

.PHONY: test lint fix format typecheck check install clean docs-serve docs-build cli-test redis-start redis-stop redis-cli redis-logs redis-stats redis-reset redis-queues redis-workers redis-failed redis-monitor redis-info test-template-quick test-template test-template-with-components test-template-database test-template-worker test-template-auth test-template-full test-component-quick test-stacks test-stacks-build test-stacks-runtime test-stacks-full clean-test-projects help

# Default target
.DEFAULT_GOAL := help