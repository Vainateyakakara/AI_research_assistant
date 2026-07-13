"""
query_rewriter.py - Converts short follow-up questions into complete standalone queries.

Improves retrieval quality because vector DB and arXiv search need full context,
not vague queries like "only from 2024".
"""

from typing import Optional
from conversation_history.session_memory import SessionMemory


_FOLLOWUP_SIGNALS = [
    "only from",
    "only in",
    "but from",
    "but in",
    "that one",
    "those ones",
    "same topic",
    "more of those",
    "more papers",
    "also find",
    "also search",
    "and also",
    "what about",
    "how about",
    "what else",
    "any more",
    "different year",
    "newer",
    "older",
    "recent ones",
    "latest ones",
    "tell me more",
    "give me more",
    "show me more",
    "expand on",
    "similar papers",
    "related papers",
    "related to that",
    "like the previous",
    "like the last",
    "like those",
]


def _is_likely_followup(query: str, memory: SessionMemory) -> bool:
    """
    Return True if the query is probably a follow-up (incomplete) question.

    Criteria:
    1. Very short query (≤ 6 words) AND there is prior chat history.
    2. Query contains known follow-up signal phrases.
    3. Query starts with a pronoun/demonstrative without subject context.
    """
    if not memory.chat_history:
        return False                     
    q_lower = query.lower().strip()
    words = q_lower.split()

    # Short query with existing history
    if len(words) <= 6:
        return True

    # Contains explicit follow-up phrase
    for signal in _FOLLOWUP_SIGNALS:
        if signal in q_lower:
            return True

    # Starts with pronoun/demonstrative
    pronoun_starts = ("it", "they", "this", "that", "these", "those", "he", "she")
    if words and words[0] in pronoun_starts:
        return True

    return False


def rewrite_query(query: str, memory: SessionMemory, llm_fn=None) -> str:
    """
    Rewrite a potentially ambiguous follow-up query into a fully self-contained query.

    Strategy:
    - If the query looks complete and standalone, return it unchanged.
    - Otherwise, build a rewriting prompt with recent history and call the LLM.
    - If no LLM is provided, fall back to a simple rule-based rewrite.

    Args:
        query    : The raw user query.
        memory   : The current SessionMemory instance.
        llm_fn   : Optional callable (str) → str that wraps your LLM.
                   Signature: llm_fn(prompt: str) -> str
                   If None, a rule-based fallback is used.

    Returns:
        A rewritten, standalone query string.
    """
    if not _is_likely_followup(query, memory):
        return query                       # Already self-contained

    history_text = memory.format_history_for_prompt(n=6)
    last_topic = memory.get_last_topic()

    # ---- LLM-based rewriting (preferred) --------------------------------
    if llm_fn is not None:
        prompt = _build_rewrite_prompt(query, history_text, last_topic)
        try:
            rewritten = llm_fn(prompt).strip()
            if rewritten and len(rewritten) > 3:
                return rewritten
        except Exception:
            pass                           # Fall through to rule-based

    # ---- Rule-based fallback --------------------------------------------
    return _rule_based_rewrite(query, last_topic)


def _build_rewrite_prompt(query: str, history_text: str, last_topic: str) -> str:
    """Build the LLM prompt for query rewriting."""
    topic_hint = f"\nThe previous topic was: {last_topic}" if last_topic else ""
    return f"""You are a query rewriter for a research paper assistant.

Given the conversation history and the user's latest message, rewrite the user's 
message into a complete, standalone search query that can be understood without 
any prior context.

Rules:
- Output ONLY the rewritten query. No explanation, no preamble.
- Keep it concise (1-2 sentences max).
- Preserve any year, author, or domain filters mentioned.
- Do not add information that was not implied by the conversation.

Conversation history:
{history_text}{topic_hint}

User's latest message: "{query}"

Rewritten standalone query:"""


def _rule_based_rewrite(query: str, last_topic: str) -> str:
    """
    Simple rule-based fallback when no LLM is available.

    Prepends the last known topic to the query to add context.
    """
    q = query.strip()
    if not last_topic:
        return q

    q_lower = q.lower()

    # "only from 2024" → "RAG papers only from 2024"
    time_prefixes = ("only from", "only in", "but from", "but in", "from", "in")
    for prefix in time_prefixes:
        if q_lower.startswith(prefix):
            return f"{last_topic} papers {q}"

    # "more papers" → "more papers on RAG"
    if any(q_lower.startswith(p) for p in ("more papers", "more results", "find more", "show more")):
        return f"{q} on {last_topic}"

    # Generic: prepend topic
    return f"{last_topic} - {q}"


# ---------------------------------------------------------------------------
# Quick standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from session_memory import SessionMemory

    mem = SessionMemory()
    mem.add_user_message("Find me papers on Retrieval Augmented Generation")
    mem.add_assistant_message("Here are some papers on RAG: ...")
    mem.set_last_topic("Retrieval Augmented Generation")

    tests = [
        "only from 2024",
        "what about newer ones?",
        "more papers",
        "Find papers on diffusion models",           # standalone – should not change
        "those from Google",
    ]

    for t in tests:
        print(f"Input : {t!r}")
        print(f"Output: {rewrite_query(t, mem)!r}")
        print()