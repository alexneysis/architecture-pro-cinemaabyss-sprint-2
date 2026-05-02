import os
from fastapi import FastAPI, HTTPException, Path, Request, status
from database import lifespan
from models import MessageResponse, SensorCreate, Sensor
import random

class Settings(BaseSettings):
    MONOLITH_URL: str
    MOVIES_SERVICE_URL: str
    EVENTS_SERVICE_URL: str
    GRADUAL_MIGRATION: bool
    MOVIES_MIGRATION_PERCENT: int

settings = Settings()

app = FastAPI(
    title="CinemaAbyss Proxy",
    version="1.0.0",
    description="Reverse proxy for monolith and microservices",
)


def _response_headers(headers: httpx.Headers) -> dict[str, str]:
    excluded = {"connection", "content-length", "keep-alive", "transfer-encoding"}
    return {k: v for k, v in headers.items() if k.lower() not in excluded}


async def _forward(request: Request, upstream_host: str, upstream_path: str) -> Response:
    body = await request.body()
    request_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in {"host", "content-length"}
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream_response = await client.request(
                method=request.method,
                url=f"{upstream_host}{upstream_path}",
                params=request.query_params,
                content=body,
                headers=request_headers,
            )
    except httpx.HTTPError as exc:
        return JSONResponse(status_code=502, content={"detail": f"Upstream error: {exc}"})

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        media_type=upstream_response.headers.get("content-type"),
        headers=_response_headers(upstream_response.headers),
    )


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

@app.api_route("/api/payments", methods=["GET", "POST"])
async def proxy_payments(request: Request) -> Response:
    return await _forward(request, settings.MONOLITH_API_HOST, "/api/payments")


@app.api_route("/api/subscriptions", methods=["GET", "POST"])
async def proxy_subscriptions(request: Request) -> Response:
    return await _forward(request, settings.MONOLITH_API_HOST, "/api/subscriptions")


@app.api_route("/api/movies", methods=["GET", "POST"])
async def proxy_movies(request: Request) -> Response:
    if not settings.GRADUAL_MIGRATION:
        return await _forward(request, settings.MONOLITH_API_HOST, "/api/movies")

    use_movies_service = settings.MOVIES_MIGRATION_PERCENT == 100
    if not use_movies_service:
        use_movies_service = random.randint(1, 100) <= settings.MOVIES_MIGRATION_PERCENT

    target_host = settings.MOVIES_API_HOST if use_movies_service else settings.MONOLITH_API_HOST
    return await _forward(request, target_host, "/api/movies")
