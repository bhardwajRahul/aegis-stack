# Backend Component

!!! example "Musings: On Backend Choices (November 2025)"
    Most of my experience is with [FastAPI](https://fastapi.tiangolo.com/), but I did have the chance to do some [Flask](https://flask.palletsprojects.com/) work in a production environment this past summer, and it was rather fun.

    Regarding using it as a backend, I mean, it's just another backend to learn, and if I can just deal with the sync/async stuff, it's something I can confidently say I wouldn't mind throwing in as an option.

    Of course, with Flet as the frontend (though perhaps forced dependency goes away?), FastAPI will always be there as its own backend. But all API related stuff is handled in Flask... In theory...

The **Backend Component** handles HTTP requests and API endpoints for your Aegis Stack application using [FastAPI](https://fastapi.tiangolo.com/).

## Adding API Routes

API routes require **explicit registration** to maintain clear dependency tracking:

**Step 1: Create your router**
```python
# app/components/backend/api/data.py
from fastapi import APIRouter
from app.services.data_service import get_dashboard_stats, trigger_manual_ingestion

router = APIRouter()

@router.get("/data/stats")
async def get_stats():
    stats = await get_dashboard_stats()
    return {"status": "success", "data": stats}

@router.post("/data/ingest")
async def trigger_ingestion():
    await trigger_manual_ingestion()
    return {"status": "ingestion_started"}
```

**Step 2: Register explicitly**
```python
# app/components/backend/api/routing.py
from app.components.backend.api import data

def include_routers(app: FastAPI) -> None:
    app.include_router(data.router, prefix="/api", tags=["data"])
```

> **Why manual registration?** API routes define your application's public interface. Explicit registration makes dependencies clear and prevents accidental exposure of endpoints.

## Adding Backend Hooks (Auto-Discovered)

Backend hooks are **automatically discovered** by dropping files in designated folders:

```
app/components/backend/
├── middleware/     # Auto-discovered middleware  
├── startup/        # Auto-discovered startup hooks
└── shutdown/       # Auto-discovered shutdown hooks
```

**Example: Add CORS middleware**
```python
# app/components/backend/middleware/cors.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

async def register_middleware(app: FastAPI) -> None:
    """Auto-discovered middleware registration."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"]
    )
```

**No registration required** - just drop the file and restart. See the [Integration Patterns](../integration-patterns.md) for complete details.

!!! example "Musings: Backend Middleware Auto-Discovery (November 22nd, 2025)"
    I'm not sure how I ultimately feel about the auto-discovery middleware pattern. I don't have enough experience with FastAPI plugins yet, but it's something I'm thinking about as the architecture evolves.

    The current approach works well for explicit component registration, but auto-discovery could reduce boilerplate at the cost of making the registration flow less obvious. Trade-offs worth considering as Aegis Stack matures.

## Integration

FastAPI integrates with your application and provides:

- **Interactive docs** at `/docs` (Swagger UI)
- **API schema** at `/openapi.json`  
- **Health check** at `/health`
- **CORS enabled** for frontend integration

## Next Steps

- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** - Complete API framework capabilities
- **[FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)** - Building APIs with FastAPI
- **[Component Overview](./index.md)** - Understanding Aegis Stack's component architecture