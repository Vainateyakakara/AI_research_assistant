"""
server/routes/upload.py - POST /api/upload endpoint.
Handles PDF upload, processing, and indexing into ChromaDB.
"""

import os
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file into the vector database."""
    from server.main import components
    from app import config

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        # ── Step 1: Save PDF ──────────────────────────────────────────
        filename = os.path.basename(file.filename)
        save_path = os.path.join(config.DATA_RAW_PATH, filename)

        content = await file.read()
        with open(save_path, 'wb') as f:
            f.write(content)

        # ── Step 2: Load document ─────────────────────────────────────
        docs = components['loader'].load_pdf_pymupdf(save_path)

        # ── Step 3: Chunk text ────────────────────────────────────────
        chunks = components['chunker'].chunk_documents(docs)
        chunk_stats = components['chunker'].get_chunk_stats(chunks)

        # ── Step 4: Add to ChromaDB ───────────────────────────────────
        components['vector_store'].add_documents(chunks, show_progress=False)

        # ── Step 5: Get updated stats ─────────────────────────────────
        new_stats = components['vector_store'].get_collection_stats()

        return {
            "success": True,
            "filename": filename,
            "pages": len(docs),
            "chunks": chunk_stats['num_chunks'],
            "avgChunkSize": round(chunk_stats['avg_chunk_size']),
            "totalDocuments": new_stats['num_documents'],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
