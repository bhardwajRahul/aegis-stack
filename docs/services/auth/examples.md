# Real-World Examples

Complete examples showing how to use the auth service in applications.

## Basic Authentication Flow

### Project Setup

Generate a project with the auth service:

```bash
# Create project with auth
aegis init my-auth-app --services auth --components database
cd my-auth-app
uv sync && source .venv/bin/activate

# Start the application (spins up all infrastructure)
make server

# In a new terminal, create test users
my-auth-app auth create-test-user --email "admin@test.com" --password "admin123"
my-auth-app auth create-test-users --count 3
```

### Frontend Login Application

A complete Flet application with authentication:

```python
# app/components/frontend/main.py
import flet as ft
import httpx
from typing import Optional

class AuthApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Auth Demo"
        self.current_user: Optional[dict] = None
        self.token: Optional[str] = None

    async def main(self):
        """Main application entry point."""
        await self.check_existing_auth()

        if self.current_user:
            await self.show_dashboard()
        else:
            await self.show_login()

    async def check_existing_auth(self):
        """Check if user is already logged in."""
        token = await self.page.client_storage.get_async("auth_token")
        if token:
            user = await self.get_current_user(token)
            if user:
                self.token = token
                self.current_user = user

    async def show_login(self):
        """Show login form."""
        self.page.clean()

        email_field = ft.TextField(
            label="Email",
            width=300,
            keyboard_type=ft.KeyboardType.EMAIL
        )

        password_field = ft.TextField(
            label="Password",
            width=300,
            password=True,
            can_reveal_password=True
        )

        error_text = ft.Text(color=ft.colors.RED, visible=False)

        async def handle_login(e):
            if not email_field.value or not password_field.value:
                error_text.value = "Please fill in all fields"
                error_text.visible = True
                self.page.update()
                return

            token_data = await self.login_user(email_field.value, password_field.value)

            if token_data:
                self.token = token_data["access_token"]
                await self.page.client_storage.set_async("auth_token", self.token)

                self.current_user = await self.get_current_user(self.token)
                await self.show_dashboard()
            else:
                error_text.value = "Invalid email or password"
                error_text.visible = True
                self.page.update()

        login_button = ft.ElevatedButton(
            "Login",
            on_click=handle_login,
            width=300
        )

        self.page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("Login", size=24, weight=ft.FontWeight.BOLD),
                    email_field,
                    password_field,
                    error_text,
                    login_button,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                expand=True
            )
        )

    async def show_dashboard(self):
        """Show user dashboard."""
        self.page.clean()

        async def handle_logout(e):
            await self.page.client_storage.remove_async("auth_token")
            self.token = None
            self.current_user = None
            await self.show_login()

        self.page.add(
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"Welcome, {self.current_user['full_name'] or self.current_user['email']}",
                               size=20),
                        ft.IconButton(ft.icons.LOGOUT, on_click=handle_logout)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Text(f"User ID: {self.current_user['id']}"),
                    ft.Text(f"Email: {self.current_user['email']}"),
                    ft.Text(f"Account Status: {'Active' if self.current_user['is_active'] else 'Inactive'}"),
                    ft.Text(f"Member Since: {self.current_user['created_at'][:10]}"),
                ]),
                padding=20
            )
        )

    async def login_user(self, email: str, password: str) -> Optional[dict]:
        """Call the auth API to login user."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "http://localhost:8000/api/v1/auth/token",
                    data={"username": email, "password": password},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except httpx.RequestError:
                return None

    async def get_current_user(self, token: str) -> Optional[dict]:
        """Get current user from API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "http://localhost:8000/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except httpx.RequestError:
                return None

async def main(page: ft.Page):
    app = AuthApp(page)
    await app.main()

if __name__ == "__main__":
    ft.app(target=main, port=8080)
```


## Testing Examples

### CLI Testing Workflow

```bash
# Setup test users
my-app auth create-test-user --email "test@example.com" --password "test123"
my-app auth create-test-users --count 5 --prefix "user"

# Verify users were created
my-app auth list-users

# Test API endpoints
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=test@example.com&password=test12345"

# Use token for protected routes
TOKEN="your_token_here"
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Automated API Testing

```python
# tests/integration/test_auth_flow.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_complete_auth_flow(async_client: AsyncClient):
    """Test complete authentication flow."""

    # Register new user
    user_data = {
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "testpassword123"
    }

    response = await async_client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    user = response.json()
    assert user["email"] == "test@example.com"

    # Login with credentials
    login_data = {
        "username": "test@example.com",
        "password": "testpassword123"
    }
    response = await async_client.post("/api/v1/auth/token", data=login_data)
    assert response.status_code == 200
    token_data = response.json()
    token = token_data["access_token"]

    # Access protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    profile = response.json()
    assert profile["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_invalid_credentials(async_client: AsyncClient):
    """Test authentication with invalid credentials."""

    # Try login with non-existent user
    login_data = {
        "username": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    response = await async_client.post("/api/v1/auth/token", data=login_data)
    assert response.status_code == 401

    # Try accessing protected endpoint without token
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
```


---

**Next Steps:**

- **[API Reference](api.md)** - Complete endpoint documentation
- **[Integration Guide](integration.md)** - Frontend/backend integration patterns
- **[CLI Commands](cli.md)** - User management from command line