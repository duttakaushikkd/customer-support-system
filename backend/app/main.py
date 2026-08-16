import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes import router
from app.config import settings
from app.services import mongo
from app.services.auth import seed_users
from app.services.kb import seed_kb_if_needed

logging.basicConfig(
    level=logging.INFO,
    format='{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)

KB_DIR = Path(__file__).resolve().parent.parent / "kb" / "articles"
_bootstrapped = False


def bootstrap() -> None:
    global _bootstrapped
    if _bootstrapped:
        return
    # #region agent log
    from app.services.mongo import _agent_log

    _agent_log("D", "main.py:bootstrap", "bootstrap start", {"already": _bootstrapped})
    # #endregion
    mongo.ensure_indexes()
    seed_users()
    seed_kb_if_needed(KB_DIR)
    _bootstrapped = True
    # #region agent log
    _agent_log("D", "main.py:bootstrap", "bootstrap complete", {"ok": True})
    # #endregion


def static_dir() -> Path | None:
    candidates = [
        Path(__file__).resolve().parent.parent / "static",
        Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    ]
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bootstrap()
    yield


app = FastAPI(title="Customer Support Agent", lifespan=lifespan)
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if origins == ["*"] else origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.middleware("http")
async def ensure_bootstrap(request: Request, call_next):
    bootstrap()
    # Vercel FastAPI rewrites can collapse paths to /api; restore the original URI.
    path = request.scope.get("path", "")
    original = request.headers.get("x-forwarded-uri") or request.headers.get("x-invoke-path")
    if path in {"/api", "/api/"} and original:
        restored = original.split("?", 1)[0]
        if restored and restored not in {"/api", "/api/"}:
            request.scope["path"] = restored
    return await call_next(request)


@app.get("/{full_path:path}")
def spa(full_path: str):
    root = static_dir()
    if root is None:
        raise HTTPException(status_code=404, detail="Not Found")
    if full_path in {"api", "auth", "tickets", "health"}:
        raise HTTPException(status_code=404, detail="Not Found")
    target = (root / full_path).resolve()
    if str(target).startswith(str(root.resolve())) and target.is_file():
        return FileResponse(target)
    return FileResponse(root / "index.html")
