"""ORACLE-X/N — FastAPI Application Factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, recommendations, reviews, users


def create_app() -> FastAPI:
    app = FastAPI(
        title="ORACLE-X/N",
        description=(
            "Behavioural Cognitive Graph Agent — "
            "Contextual recommendation & review intelligence for Nigerian e-commerce."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, tags=["System"])
    app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
    app.include_router(reviews.router, prefix="/api/v1", tags=["Reviews"])
    app.include_router(users.router, prefix="/api/v1", tags=["Users"])

    return app
