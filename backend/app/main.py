from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import create_tables
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create all tables
    create_tables()
    from app.services.demo_seed import seed_demo_company
    seed_demo_company()
    print(f"✅ {settings.APP_NAME} started. Database tables ready.")
    yield
    # Shutdown
    print("🛑 Application shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise HRMS & Compensation Management Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS — allow the React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trust Render's proxy so redirects keep https
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Mount all API routes under /api/v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/api/docs",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
