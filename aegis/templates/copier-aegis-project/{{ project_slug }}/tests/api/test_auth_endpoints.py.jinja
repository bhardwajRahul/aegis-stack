"""
Tests for authentication API endpoints.

This module tests the auth endpoints including user registration,
login, token validation, and protected endpoint access.
"""

import pytest
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.services.auth.user_service import UserService
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession


class TestAuthEndpoints:
    """Test auth API endpoints."""

    @pytest.mark.asyncio
    async def test_register_new_user(
        self, async_client_with_db: TestClient, async_db_session: AsyncSession
    ):
        """Test user registration with valid data."""
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "testpassword123"
        }

        response = async_client_with_db.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        # Ensure password is not returned
        assert "password" not in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, async_client_with_db: TestClient, async_db_session: AsyncSession
    ):
        """Test registration with already existing email."""
        # Create a user first
        user_service = UserService(async_db_session)
        existing_user = UserCreate(
            email="existing@example.com",
            full_name="Existing User",
            password="password123"
        )
        await user_service.create_user(existing_user)

        # Try to register with same email
        duplicate_user_data = {
            "email": "existing@example.com",
            "full_name": "Another User",
            "password": "differentpassword"
        }

        response = async_client_with_db.post(
            "/api/v1/auth/register", json=duplicate_user_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_data(self, async_client_with_db: TestClient):
        """Test registration with invalid data."""
        invalid_user_data = {
            "email": "not-an-email",  # Invalid email format
            "password": "123"  # Too short
        }

        response = async_client_with_db.post(
            "/api/v1/auth/register", json=invalid_user_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_valid_credentials(
        self, async_client_with_db: TestClient, async_db_session: AsyncSession
    ):
        """Test login with valid credentials."""
        # Create a user first
        user_service = UserService(async_db_session)
        user_data = UserCreate(
            email="login@example.com",
            full_name="Login User",
            password="loginpassword123"
        )
        await user_service.create_user(user_data)

        # Login with valid credentials
        login_data = {
            "username": "login@example.com",  # OAuth2 uses username field
            "password": "loginpassword123"
        }

        response = async_client_with_db.post("/api/v1/auth/token", data=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, async_client_with_db: TestClient):
        """Test login with non-existent email."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "somepassword"
        }

        response = async_client_with_db.post("/api/v1/auth/token", data=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self, async_client_with_db: TestClient, async_db_session: AsyncSession
    ):
        """Test login with wrong password."""
        # Create a user first
        user_service = UserService(async_db_session)
        user_data = UserCreate(
            email="wrongpass@example.com",
            full_name="Wrong Pass User",
            password="correctpassword"
        )
        await user_service.create_user(user_data)

        # Login with wrong password
        login_data = {
            "username": "wrongpass@example.com",
            "password": "wrongpassword"
        }

        response = async_client_with_db.post("/api/v1/auth/token", data=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(
        self, async_client_with_db: TestClient, async_db_session: AsyncSession
    ):
        """Test getting current user with valid token."""
        # Create a user first
        user_service = UserService(async_db_session)
        user_data = UserCreate(
            email="currentuser@example.com",
            full_name="Current User",
            password="password123"
        )
        created_user = await user_service.create_user(user_data)

        # Create a valid token
        token = create_access_token(data={"sub": created_user.email})

        # Get current user
        response = async_client_with_db.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == created_user.email
        assert data["full_name"] == created_user.full_name
        assert data["id"] == created_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(
        self, async_client_with_db: TestClient
    ):
        """Test getting current user with invalid token."""
        response = async_client_with_db.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, async_client_with_db: TestClient):
        """Test getting current user without token."""
        response = async_client_with_db.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(
        self, async_client_with_db: TestClient, async_db_session: AsyncSession
    ):
        """Test getting current user with expired token."""
        # Create a user first
        user_service = UserService(async_db_session)
        user_data = UserCreate(
            email="expiredtoken@example.com",
            full_name="Expired Token User",
            password="password123"
        )
        created_user = await user_service.create_user(user_data)

        # Create an expired token (negative expiry)
        from datetime import timedelta
        expired_token = create_access_token(
            data={"sub": created_user.email},
            expires_delta=timedelta(seconds=-1)
        )

        # Try to get current user with expired token
        response = async_client_with_db.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthIntegration:
    """Integration tests for auth flow."""

    @pytest.mark.asyncio
    async def test_full_auth_flow(
        self, async_client_with_db: TestClient, async_db_session: AsyncSession
    ):
        """Test complete auth flow: register -> login -> protected endpoint."""
        # Step 1: Register new user
        user_data = {
            "email": "fullflow@example.com",
            "full_name": "Full Flow User",
            "password": "fullflowpassword123"
        }

        register_response = async_client_with_db.post(
            "/api/v1/auth/register", json=user_data
        )
        assert register_response.status_code == status.HTTP_200_OK

        # Step 2: Login with credentials
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }

        login_response = async_client_with_db.post(
            "/api/v1/auth/token", data=login_data
        )
        assert login_response.status_code == status.HTTP_200_OK

        token = login_response.json()["access_token"]

        # Step 3: Access protected endpoint
        me_response = async_client_with_db.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert me_response.status_code == status.HTTP_200_OK
        user_info = me_response.json()
        assert user_info["email"] == user_data["email"]
        assert user_info["full_name"] == user_data["full_name"]

    @pytest.mark.asyncio
    async def test_user_persistence_across_requests(
        self, async_client_with_db: TestClient, async_db_session: AsyncSession
    ):
        """Test that users are properly persisted in database."""
        # Register user
        user_data = {
            "email": "persistent@example.com",
            "full_name": "Persistent User",
            "password": "persistentpassword"
        }

        async_client_with_db.post("/api/v1/auth/register", json=user_data)

        # Login in separate request
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }

        login_response = async_client_with_db.post(
            "/api/v1/auth/token", data=login_data
        )
        assert login_response.status_code == status.HTTP_200_OK

        # Verify user exists in database
        user_service = UserService(async_db_session)
        db_user = await user_service.get_user_by_email(user_data["email"])

        assert db_user is not None
        assert db_user.email == user_data["email"]
        assert db_user.full_name == user_data["full_name"]
        assert db_user.is_active is True
