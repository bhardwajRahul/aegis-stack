# CLI Commands

**Part of the Generated Project CLI** - See [CLI Reference](../../cli-reference.md#service-clis) for complete overview.

Manage users from the command line with development-focused CLI commands.

## Overview

The auth service includes 3 CLI commands designed for development and testing workflows. All commands are accessible through your project's CLI tool.

## Available Commands

### create-test-user

Create a single test user with automatic email generation and password creation.

```bash
# Create test user with auto-generated email and password
my-app auth create-test-user

# Create with specific email
my-app auth create-test-user --email "admin@example.com"

# Create with custom password
my-app auth create-test-user --password "mypassword123"

# Create with full name
my-app auth create-test-user --full-name "Test Admin"

# Customize auto-generated email pattern
my-app auth create-test-user --prefix "admin" --domain "company.com"
```

**Options:**

- `--email` - User email address (auto-generated if not provided)
- `--password` - User password (auto-generated if not provided)
- `--full-name` - User's full name
- `--prefix` - Email prefix for auto-generated emails (default: "test")
- `--domain` - Email domain for auto-generated emails (default: "example.com")

**Auto-increment Email Feature:**

If you don't specify an email, the command automatically finds the next available email in sequence:

- First user: `test@example.com`
- Second user: `test1@example.com`
- Third user: `test2@example.com`

### create-test-users

Create multiple test users with shared credentials for bulk testing.

```bash
# Create 5 test users with auto-generated emails
my-app auth create-test-users --count 5

# Create users with custom prefix and shared password
my-app auth create-test-users --count 3 --prefix "admin" --password "shared123"

# Create users with custom domain
my-app auth create-test-users --count 10 --domain "company.com"
```

**Options:**

- `--count` - Number of test users to create (default: 5)
- `--prefix` - Email prefix for generated users (default: "test")
- `--domain` - Email domain for generated users (default: "example.com")
- `--password` - Shared password for all users (auto-generated if not provided)

### list-users

Display all users in the system.

```bash
# List all users
my-app auth list-users
```

Shows user ID, email, full name (if set), and creation date.

## Testing API Integration

After creating test users, you can immediately test the authentication API:

```bash
# Create test user
my-app auth create-test-user --email "api@test.com" --password "test123"

# Test login endpoint
curl -X POST http://localhost:8000/auth/token \
  -d "username=api@test.com&password=test123"

# Use returned token for protected endpoints
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## See Also

- **[CLI Reference](../../cli-reference.md)** - Complete CLI overview and all commands
- **[Auth Service Documentation](index.md)** - Main auth service documentation
- **[API Reference](api.md)** - Test the endpoints with your created users
- **[Integration Guide](integration.md)** - Build frontend login forms