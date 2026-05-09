import os
import random

import httpx
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

MONOLITH_URL = os.getenv("MONOLITH_URL")
MOVIES_SERVICE_URL = os.getenv("MOVIES_SERVICE_URL")
EVENTS_SERVICE_URL = os.getenv("EVENTS_SERVICE_URL")
GRADUAL_MIGRATION = True if os.getenv("GRADUAL_MIGRATION") in ("true", "True", 1, "1") else False
MOVIES_MIGRATION_PERCENT = int(os.getenv("MOVIES_MIGRATION_PERCENT"))

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
    return await _forward(request, MONOLITH_URL, "/api/payments")


@app.api_route("/api/users", methods=["GET", "POST"])
async def proxy_users(request: Request) -> Response:
    return await _forward(request, MONOLITH_URL, "/api/users")


@app.api_route("/api/subscriptions", methods=["GET", "POST"])
async def proxy_subscriptions(request: Request) -> Response:
    return await _forward(request, MONOLITH_URL, "/api/subscriptions")


@app.api_route("/api/movies", methods=["GET", "POST"])
async def proxy_movies(request: Request) -> Response:
    if not GRADUAL_MIGRATION:
        print("Proxy to monolith")
        return await _forward(request, MONOLITH_URL, "/api/movies")

    use_movies_service = MOVIES_MIGRATION_PERCENT == 100
    if not use_movies_service:
        use_movies_service = random.randint(1, 100) <= MOVIES_MIGRATION_PERCENT

    target_host = MOVIES_SERVICE_URL if use_movies_service else MONOLITH_URL
    if not use_movies_service:
        print("Proxy to monolith")
    return await _forward(request, target_host, "/api/movies")
