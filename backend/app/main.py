from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.location import router as location_router
from backend.app.api.airfield import router as airfield_router
from backend.app.api.models import router as models_router
from backend.app.api.replay import router as replay_router
from backend.app.core.config import settings

app = FastAPI(
    title="VAJRA V2 Location Intelligence API",
    description="Issue-time-safe replay, tracked baseline forecasts, and location intelligence.",
    version="0.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(location_router, prefix="/api/v1/location", tags=["location-intelligence"])
app.include_router(airfield_router, prefix="/api/v1/airfield", tags=["airfield-simulator"])
app.include_router(replay_router, prefix="/api/v1/replay", tags=["data-replay"])
app.include_router(models_router, prefix="/api/v1/models", tags=["model-registry"])


@app.get("/api/v1/health")
@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {
        "status": "ready",
        "service": "vajra-api",
        "version": app.version,
        "mode": "REPLAY",
    }
