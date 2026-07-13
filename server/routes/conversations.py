"""
server/routes/conversations.py - CRUD endpoints for conversation management.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from server import db

router = APIRouter()


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Chat"


class ConversationRename(BaseModel):
    title: str


@router.get("/conversations")
async def list_conversations():
    """List all conversations, newest first."""
    rows = db.fetchall("""
        SELECT
            c.id,
            c.title,
            c.created_at,
            c.updated_at,
            COUNT(m.id) AS message_count
        FROM conversations c
        LEFT JOIN messages m ON m.conversation_id = c.id
        GROUP BY c.id
        ORDER BY c.updated_at DESC
    """)
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
            "updatedAt": r["updated_at"].isoformat() if r["updated_at"] else None,
            "messageCount": r["message_count"],
        }
        for r in rows
    ]


@router.post("/conversations")
async def create_conversation(body: ConversationCreate = ConversationCreate()):
    """Create a new conversation."""
    conv_id = uuid.uuid4().hex[:12]
    db.execute(
        "INSERT INTO conversations (id, title) VALUES (%s, %s)",
        (conv_id, body.title),
    )
    return {"id": conv_id, "title": body.title}


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """Get all messages in a conversation."""
    # Verify conversation exists
    conv = db.fetchone(
        "SELECT id, title FROM conversations WHERE id = %s",
        (conversation_id,),
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    rows = db.fetchall(
        "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
        (conversation_id,),
    )
    return {
        "conversationId": conversation_id,
        "title": conv["title"],
        "messages": [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "mode": r["mode"],
                "modelUsed": r["model_used"],
                "sources": r["sources_json"],
                "pipeline": r["pipeline_json"],
                "rewrittenQuery": r["rewritten_query"],
                "resolvedPaper": r["resolved_paper"],
                "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    conv = db.fetchone(
        "SELECT id FROM conversations WHERE id = %s",
        (conversation_id,),
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
    return {"success": True}


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: str, body: ConversationRename):
    """Rename a conversation."""
    conv = db.fetchone(
        "SELECT id FROM conversations WHERE id = %s",
        (conversation_id,),
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.execute(
        "UPDATE conversations SET title = %s, updated_at = NOW() WHERE id = %s",
        (body.title, conversation_id),
    )
    return {"success": True, "title": body.title}
