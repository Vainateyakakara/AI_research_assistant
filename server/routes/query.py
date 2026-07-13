"""
server/routes/query.py - POST /api/query endpoint.
Mirrors the query processing logic from Streamlit main.py.
Now persists messages to PostgreSQL.
"""

import uuid
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from server import db

router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    mode: str = "simple"  # "simple" | "analysis" | "research"
    show_details: bool = True
    conversation_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    type: str
    model: str
    sources: list
    pipeline: list
    num_chunks: Optional[int] = None
    rewritten_query: Optional[str] = None
    resolved_paper: Optional[str] = None
    extracted_info: Optional[str] = None
    conversation_id: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a research query through the appropriate pipeline."""
    from server.main import components, memory
    from conversation_history.query_rewriter import rewrite_query
    from conversation_history.reference_resolver import detect_reference, enrich_query_with_paper

    query = request.query.strip()
    mode = request.mode.lower().strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if mode not in ("simple", "analysis", "research"):
        raise HTTPException(status_code=400, detail="Mode must be 'simple', 'analysis', or 'research'")

    try:
        # ── Auto-create conversation if none provided ─────────────────
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = uuid.uuid4().hex[:12]
            title = query[:60] + ("..." if len(query) > 60 else "")
            db.execute(
                "INSERT INTO conversations (id, title) VALUES (%s, %s)",
                (conversation_id, title),
            )

        # ── Step 1: Reference resolution ──────────────────────────────
        is_reference, resolved_paper = detect_reference(query, memory)
        resolved_paper_title = None
        working_query = query

        if is_reference and resolved_paper:
            resolved_paper_title = resolved_paper.title
            working_query = enrich_query_with_paper(query, resolved_paper)

        # ── Step 2: Query rewriting ───────────────────────────────────
        rewritten_query = query
        if not is_reference:
            def _llm_rewrite_fn(prompt: str) -> str:
                try:
                    result = components['router'].route(prompt, mode="simple")
                    return result.get("answer", "").strip()
                except Exception:
                    return ""

            rewritten_query = rewrite_query(query, memory, llm_fn=_llm_rewrite_fn)

        # ── Step 3: Record user message in memory ─────────────────────
        memory.add_user_message(query)

        # ── Step 3b: Save user message to DB ──────────────────────────
        user_msg_id = uuid.uuid4().hex[:16]
        db.execute(
            """INSERT INTO messages (id, conversation_id, role, content, mode)
               VALUES (%s, %s, 'user', %s, %s)""",
            (user_msg_id, conversation_id, query, mode),
        )

        # ── Step 4: Route query ───────────────────────────────────────
        result = components['router'].route(working_query, mode=mode)

        # ── Step 5: Update memory with papers ─────────────────────────
        if result.get('sources'):
            raw_papers = []
            for s in result['sources']:
                raw_papers.append({
                    "title": s.get('title', s.get('source_file', 'Unknown')),
                    "authors": s.get('authors', []),
                    "summary": s.get('summary', s.get('abstract', '')),
                    "url": s.get('url', ''),
                    "arxiv_id": s.get('arxiv_id', ''),
                    "source": "arxiv" if result.get('type') == 'research' else "vector_store",
                })
            # Deduplicate by title
            seen = set()
            unique_papers = []
            for p in raw_papers:
                if p['title'] not in seen:
                    seen.add(p['title'])
                    unique_papers.append(p)
            memory.update_last_papers(unique_papers)

        # ── Step 6: Update topic in memory ────────────────────────────
        effective_query = rewritten_query if not is_reference else query
        _topic_raw = effective_query.lower().strip()
        for prefix in ("find", "search", "show me", "get", "what are", "tell me about"):
            if _topic_raw.startswith(prefix):
                _topic_raw = _topic_raw[len(prefix):].strip()
                break
        memory.set_last_topic(_topic_raw.capitalize()[:60])

        # ── Step 7: Record assistant response in memory ───────────────
        memory.add_assistant_message(result['answer'])

        # ── Step 7b: Save assistant message to DB ─────────────────────
        assistant_msg_id = uuid.uuid4().hex[:16]
        rq = rewritten_query if rewritten_query != query else None
        db.execute(
            """INSERT INTO messages
               (id, conversation_id, role, content, mode, model_used,
                sources_json, pipeline_json, rewritten_query, resolved_paper)
               VALUES (%s, %s, 'assistant', %s, %s, %s, %s, %s, %s, %s)""",
            (
                assistant_msg_id,
                conversation_id,
                result['answer'],
                mode,
                result.get('model', ''),
                json.dumps(result.get('sources', [])),
                json.dumps(result.get('pipeline', [])),
                rq,
                resolved_paper_title,
            ),
        )

        # ── Step 7c: Update conversation title & timestamp ────────────
        # Set title from first query if it's still "New Chat"
        db.execute(
            """UPDATE conversations
               SET updated_at = NOW(),
                   title = CASE
                       WHEN title = 'New Chat' THEN %s
                       ELSE title
                   END
               WHERE id = %s""",
            (query[:60] + ("..." if len(query) > 60 else ""), conversation_id),
        )

        # ── Step 8: Build response ────────────────────────────────────
        return QueryResponse(
            answer=result['answer'],
            type=result['type'],
            model=result['model'],
            sources=result.get('sources', []),
            pipeline=result.get('pipeline', []),
            num_chunks=result.get('num_chunks'),
            rewritten_query=rq,
            resolved_paper=resolved_paper_title,
            extracted_info=result.get('extracted_info'),
            conversation_id=conversation_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")
