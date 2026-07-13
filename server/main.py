"""
server/main.py - FastAPI application replacing Streamlit UI.
Wraps all existing Python modules with REST API endpoints.
"""

import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

# Add project root to path so all existing modules are importable
PROJECT_ROOT = str(Path(__file__).parent.parent)
sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import uvicorn

# Import existing modules
from app import config
from retrieval.vector_store import VectorStore
from retrieval.retriever import DocumentRetriever
from app.router import QueryRouter
from ingestion.loader import DocumentLoader
from ingestion.chunking import DocumentChunker
from conversation_history.session_memory import SessionMemory
from server.db import init_db

# ── Global components (initialized once) ─────────────────────────────────────
components = {}
memory = SessionMemory(max_history=30, max_papers=10)


def init_components():
    """Initialize all AI components (same as Streamlit's init_components)."""
    global components
    print("Initialising components...")
    vector_store = VectorStore()
    retriever = DocumentRetriever(vector_store)
    router = QueryRouter(retriever)
    components = {
        'vector_store': vector_store,
        'retriever': retriever,
        'router': router,
        'loader': DocumentLoader(),
        'chunker': DocumentChunker(),
    }
    print("All components initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Initialize PostgreSQL tables
    await run_in_threadpool(init_db)
    # Initialize AI components
    await run_in_threadpool(init_components)
    yield
    print("Shutting down...")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Research Assistant API",
    description="RAG-based AI system for academic research",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS - allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routes ──────────────────────────────────────────────────────────────
from server.routes.query import router as query_router
from server.routes.upload import router as upload_router
from server.routes.status import router as status_router
from server.routes.memory import router as memory_router
from server.routes.conversations import router as conversations_router

app.include_router(query_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(status_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "AI Research Assistant API v2.0", "status": "running"}


if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
