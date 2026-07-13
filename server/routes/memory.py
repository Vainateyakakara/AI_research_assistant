"""
server/routes/memory.py - GET/DELETE /api/memory endpoints.
Conversation memory management with DB-backed loading.
"""

import json
from fastapi import APIRouter
from typing import Optional
from conversation_history.session_memory import SessionMemory
from server import db

router = APIRouter()


@router.get("/memory")
async def get_memory():
    """Get current conversation memory state."""
    from server.main import memory

    return {
        "chatHistory": [t.to_dict() for t in memory.chat_history],
        "lastPapers": [p.to_dict() for p in memory.last_papers],
        "lastTopic": memory.last_topic,
        "lastQuery": memory.last_query,
        "turnsCount": len(memory.chat_history),
        "papersCount": len(memory.last_papers),
    }


@router.delete("/memory")
async def clear_memory():
    """Clear in-memory conversation cache (DB data is preserved)."""
    from server import main as server_main
    server_main.memory = SessionMemory(max_history=30, max_papers=10)
    return {"success": True}


@router.post("/memory/load/{conversation_id}")
async def load_conversation_into_memory(conversation_id: str):
    """Load a past conversation from DB into the active SessionMemory cache."""
    from server import main as server_main

    # Fetch messages from DB
    rows = db.fetchall(
        "SELECT role, content, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
        (conversation_id,),
    )

    if not rows:
        return {"success": True, "loaded": 0}

    # Reset memory and populate from DB
    new_memory = SessionMemory(max_history=30, max_papers=10)
    for row in rows:
        if row["role"] == "user":
            new_memory.add_user_message(row["content"])
        elif row["role"] == "assistant":
            new_memory.add_assistant_message(row["content"])

    server_main.memory = new_memory
    return {"success": True, "loaded": len(rows)}
