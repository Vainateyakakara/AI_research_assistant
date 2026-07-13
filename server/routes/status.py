"""
server/routes/status.py - GET /api/status endpoint.
Returns system status: API keys, DB stats, uploaded papers.
"""

import os
from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_status():
    """Get system status including API key configuration and database stats."""
    from server.main import components
    from app import config

    stats = components['vector_store'].get_collection_stats()

    pdf_files = []
    if os.path.exists(config.DATA_RAW_PATH):
        pdf_files = [f for f in os.listdir(config.DATA_RAW_PATH) if f.endswith('.pdf')]

    return {
        "groqConfigured": bool(config.GROQ_API_KEY),
        "geminiConfigured": bool(config.GEMINI_API_KEY),
        "numDocuments": stats['num_documents'],
        "uploadedPapers": pdf_files,
    }
