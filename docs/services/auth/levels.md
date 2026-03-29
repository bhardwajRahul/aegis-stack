# Auth Levels

Aegis Stack's authentication service supports three progressive levels. Start with basic JWT auth and upgrade as your needs grow.

## Choosing Your Level

<div class="grid cards" markdown>

-   **Basic**

    ---

    Registration, login, JWT tokens, user management.

    ```bash
    aegis add-service auth
    ```

-   **RBAC**

    ---

    Everything in Basic + role-based access control with `require_role()`.

    ```bash
    aegis add-service auth[rbac]
    ```

-   **Organization**

    ---

    Everything in RBAC + multi-tenant organization support.

    ```bash
    aegis add-service auth[org]
    ```

</div>

## Level Comparison

| Feature | Basic | RBAC | Org |
|---------|:-----:|:----:|:---:|
| User registration & login | :material-check: | :material-check: | :material-check: |
| JWT token authentication | :material-check: | :material-check: | :material-check: |
| User management (activate/deactivate/delete) | :material-check: | :material-check: | :material-check: |
| Password hashing (bcrypt) | :material-check: | :material-check: | :material-check: |
| Protected routes | :material-check: | :material-check: | :material-check: |
| Dashboard user management tab | :material-check: | :material-check: | :material-check: |
| Role field on user model | | :material-check: | :material-check: |
| `require_role()` endpoint protection | | :material-check: | :material-check: |
| Role constants (admin, moderator, user) | | :material-check: | :material-check: |
| Organization CRUD | | | :material-check: |
| Membership management | | | :material-check: |
| Org role hierarchy (owner/admin/member) | | | :material-check: |
| Dashboard organizations tab | | | :material-check: |

## RBAC (Role-Based Access Control)

### Role Constants

When RBAC is enabled, your project includes predefined role constants:

```python
# app/core/security.py
ROLE_ADMIN = "admin"
ROLE_MODERATOR = "moderator"
ROLE_USER = "user"
VALID_ROLES = {ROLE_ADMIN, ROLE_MODERATOR, ROLE_USER}
```

The user model gains a `role` field:

```python
# app/models/user.py
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True)
    full_name: str | None = None
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    role: str = Field(default="user")  # Added by RBAC
```

### Protecting Endpoints with `require_role()`

The `require_role()` function is a FastAPI dependency that checks the authenticated user's role:

```python
from app.services.auth.auth_service import require_role
from fastapi import Depends

@router.get("/admin/dashboard")
async def admin_dashboard(user=Depends(require_role("admin"))):
    """Only accessible to admin users."""
    return {"message": f"Welcome, admin {user.email}"}

@router.get("/moderation")
async def moderation_panel(user=Depends(require_role("admin", "moderator"))):
    """Accessible to admins and moderators."""
    return {"queue": [...]}
```

If the user's role doesn't match, a `403 Forbidden` response is returned automatically.

### Assigning Roles

Roles default to `"user"` on registration. To assign roles, update the user via the API:

```bash
# Update a user's role (admin endpoint)
curl -X PATCH http://localhost:8000/api/v1/auth/users/1 \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

## Organization Level

### What You Get

The Organization level adds multi-tenant support with:

- **Organization model** — name, slug, description, active status
- **Membership model** — links users to organizations with roles
- **OrgService** — CRUD operations for organizations
- **MembershipService** — Add/remove members, update roles, list memberships
- **REST API** — Full org and membership management endpoints
- **Dashboard tab** — Organizations management in the Overseer UI

### Organization Models

```python
# app/models/org.py
class Organization(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    description: str | None = None
    is_active: bool = Field(default=True)
    created_at: datetime
    updated_at: datetime | None = None

class OrganizationMember(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    user_id: int = Field(foreign_key="user.id")
    role: str = Field(default="member")  # owner, admin, or member
    joined_at: datetime
```

### Organization API Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/orgs` | Create organization | Authenticated |
| `GET` | `/api/v1/orgs` | List user's organizations | Authenticated |
| `GET` | `/api/v1/orgs/{id}` | Get organization details | Authenticated |
| `PATCH` | `/api/v1/orgs/{id}` | Update organization | Admin/Owner |
| `DELETE` | `/api/v1/orgs/{id}` | Delete organization | Owner |
| `GET` | `/api/v1/orgs/{id}/members` | List members | Member+ |
| `POST` | `/api/v1/orgs/{id}/members` | Add member | Admin/Owner |
| `PATCH` | `/api/v1/orgs/{id}/members/{uid}` | Update member role | Admin/Owner |
| `DELETE` | `/api/v1/orgs/{id}/members/{uid}` | Remove member | Admin/Owner |

### Membership Management

```python
from app.services.auth.membership_service import MembershipService
from app.services.auth.org_service import OrgService

# Create an organization
org_service = OrgService(db)
org = await org_service.create_org(OrgCreate(
    name="Acme Corp",
    slug="acme-corp",
))

# Add members
membership_service = MembershipService(db)
await membership_service.add_member(org.id, user.id, role="owner")
await membership_service.add_member(org.id, other_user.id, role="member")

# List members
members = await membership_service.list_org_members(org.id)

# Update role
await membership_service.update_member_role(org.id, other_user.id, "admin")

# List user's organizations
orgs = await membership_service.list_user_orgs(user.id)
```

### Org Role Hierarchy

| Role | Manage Members | Update Org | Delete Org |
|------|:--------------:|:----------:|:----------:|
| **Owner** | :material-check: | :material-check: | :material-check: |
| **Admin** | :material-check: | :material-check: | |
| **Member** | | | |

- The **creator** of an organization is automatically assigned the `owner` role
- Owners cannot be removed from the organization
- Admins can add/remove members and update roles, but cannot delete the organization

## Upgrading Between Levels

### Basic to RBAC

```bash
# Regenerate with RBAC level
aegis add-service auth[rbac]
```

**What changes:**

- `role` field added to the User model
- `require_role()` dependency available in `auth_service.py`
- Role constants (`ROLE_ADMIN`, `ROLE_MODERATOR`, `ROLE_USER`) added to `security.py`
- Admin-protected user management endpoints

### RBAC to Organization

```bash
# Regenerate with org level
aegis add-service auth[org]
```

**What changes (in addition to RBAC):**

- Organization and OrganizationMember models added
- OrgService and MembershipService added
- Organization REST API endpoints at `/api/v1/orgs`
- Organizations tab in the Overseer dashboard
- Org column in the Users tab showing membership

## Next Steps

| Topic | Description |
|-------|-------------|
| **[API Reference](api.md)** | Complete endpoint documentation |
| **[Service Layer](integration.md)** | Service architecture and integration |
| **[CLI Commands](cli.md)** | User management CLI tools |
| **[Examples](examples.md)** | Real-world usage patterns |
