import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import close_pool, open_pool
# FIX: module is workspaces.py (plural) per the guide; singular would be an ImportError.
from app.routers import chat, documents, roadmap, workspaces

# Register all Routers 

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Code before 'yield' runs at startup; code after runs at shutdown."""
    open_pool()
    yield
    close_pool()


settings = get_settings()
app = FastAPI (title="EduMap API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,  # exact origins, never "*" in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health() -> dict:
    """Used by Render's health check and by the frontend to wake up a sleeping server."""
    return {"status": "ok"}

app.include_router(workspaces.router)  # FIX: was workspace.router (undefined name).
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(roadmap.router)
