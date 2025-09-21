# API Reference

Complete documentation for authentication API endpoints.

## Base URL

All authentication endpoints are available under the `/auth` prefix:

```
http://localhost:8000/auth/*
```

## Public Endpoints

These endpoints don't require authentication.

### POST /auth/register

Register a new user account.

**Request:**
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "full_name": "John Doe",
  "password": "securepassword123"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**

| Status | Condition | Response |
|--------|-----------|----------|
| 400 | Email already exists | `{"detail": "Email already registered"}` |
| 422 | Invalid email format | `{"detail": [{"field": "email", "message": "Invalid email format"}]}` |
| 422 | Password too short | `{"detail": [{"field": "password", "message": "Password too short"}]}` |

---

### POST /auth/token

Login and receive an access token.

**Request:**
```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword123
```

!!! note "OAuth2 Password Flow"
    This endpoint follows the OAuth2 password flow standard. The email is passed as `username` in form data, not JSON.

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**

| Status | Condition | Response |
|--------|-----------|----------|
| 401 | Invalid credentials | `{"detail": "Incorrect email or password"}` |
| 401 | User not found | `{"detail": "Incorrect email or password"}` |
| 401 | User deactivated | `{"detail": "Inactive user"}` |

## Protected Endpoints

These endpoints require a valid JWT token in the Authorization header.

### GET /auth/me

Get current user profile information.

**Request:**
```http
GET /auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**

| Status | Condition | Response |
|--------|-----------|----------|
| 401 | Missing token | `{"detail": "Not authenticated"}` |
| 401 | Invalid token | `{"detail": "Could not validate credentials"}` |
| 401 | Expired token | `{"detail": "Could not validate credentials"}` |
| 401 | User not found | `{"detail": "Could not validate credentials"}` |
| 401 | User deactivated | `{"detail": "Inactive user"}` |

## Data Models

### UserCreate

User registration data model.

```json
{
  "email": "string",           // Required: Valid email address
  "full_name": "string",       // Optional: User's display name
  "password": "string",        // Required: Minimum 8 characters
  "is_active": true            // Optional: Defaults to true
}
```

**Field Validation:**
- `email`: Must be valid email format, unique across users
- `full_name`: Optional, 1-100 characters if provided
- `password`: Minimum 8 characters, automatically hashed before storage
- `is_active`: Boolean, defaults to `true`

### UserResponse

User data returned by API (excludes password fields).

```json
{
  "id": 1,                     // Unique user identifier
  "email": "string",           // User's email address
  "full_name": "string",       // User's display name
  "is_active": true,           // Account status
  "created_at": "2024-01-15T10:30:00Z",  // UTC timestamp
  "updated_at": "2024-01-15T10:30:00Z"   // UTC timestamp
}
```

### TokenResponse

JWT token response from login.

```json
{
  "access_token": "string",    // JWT token string
  "token_type": "bearer"       // Always "bearer"
}
```

## Testing Examples

### Using curl

```bash
# Register a new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "secure123"
  }'

# Login and save token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=secure123" | \
  jq -r '.access_token')

# Use token to access protected endpoint
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Using Python requests

```python
import requests

base_url = "http://localhost:8000"

# Register user
register_data = {
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "secure123"
}
response = requests.post(f"{base_url}/auth/register", json=register_data)
print("Register:", response.status_code, response.json())

# Login
login_data = {
    "username": "test@example.com",
    "password": "secure123"
}
response = requests.post(f"{base_url}/auth/token", data=login_data)
token_data = response.json()
token = token_data["access_token"]
print("Login:", response.status_code, token_data)

# Access protected endpoint
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{base_url}/auth/me", headers=headers)
print("Profile:", response.status_code, response.json())
```

### Using httpx (async)

```python
import httpx
import asyncio

async def test_auth_api():
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # Register user
        register_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "secure123"
        }
        response = await client.post(f"{base_url}/auth/register", json=register_data)
        print("Register:", response.status_code, response.json())

        # Login
        login_data = {
            "username": "test@example.com",
            "password": "secure123"
        }
        response = await client.post(f"{base_url}/auth/token", data=login_data)
        token = response.json()["access_token"]

        # Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(f"{base_url}/auth/me", headers=headers)
        print("Profile:", response.status_code, response.json())

# Run the async test
asyncio.run(test_auth_api())
```

## HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful login or profile retrieval |
| 201 | Created | Successful user registration |
| 400 | Bad Request | Duplicate email, invalid data |
| 401 | Unauthorized | Invalid credentials, missing/invalid token |
| 422 | Unprocessable Entity | Validation errors in request data |
| 500 | Internal Server Error | Server-side errors |

## Rate Limiting

!!! info "Future Enhancement"
    Rate limiting is not currently implemented but should be added for production use:

    - Registration: 5 attempts per IP per hour
    - Login: 10 attempts per IP per hour
    - Token validation: 1000 requests per token per hour

---

**Next Steps:**

- **[Integration Guide](integration.md)** - Learn how to integrate auth into your app
- **[CLI Commands](cli.md)** - Manage users from command line
- **[Examples](examples.md)** - See complete implementation examples