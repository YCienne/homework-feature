import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import session_routes, action_routes, image_routes
from src.config.settings import get_settings
from src.store.redis_client import get_redis, close_redis
from src.store.db_client import close_db

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Homework Service starting up...")
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection established.")
    except Exception as e:
        logger.warning(f"Redis not available at startup: {e} — continuing for tests")
    yield
    logger.info("Homework Service shutting down...")
    await close_redis()
    await close_db()
    logger.info("Connections closed.")


app = FastAPI(
    title="Learnarium — Homework Help Service",
    description="Step-by-step AI tutoring. Controlled, curriculum-aligned, step-gated.",
    version="4.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else ["https://www.learnairium.ai"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# Request timing middleware 
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} ({duration_ms}ms)"
    )
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response


# Global error handler 
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "INTERNAL_ERROR", "message": "Something went wrong. Please try again."},
    )


# Routes 
app.include_router(session_routes.router)
app.include_router(action_routes.router)
app.include_router(image_routes.router)


@app.get("/health", tags=["ops"])
async def health_check():
    return {"status": "ok", "service": "homework-service", "version": "4.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port,
                reload=(settings.environment == "development"), log_level=settings.log_level)
