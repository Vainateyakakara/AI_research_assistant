"""
reference_resolver.py - Resolves vague references like "this paper", "second paper",
"that transformer paper" into actual PaperReference objects stored in SessionMemory.

Makes the assistant usable in natural conversation since users won't repeat full
paper titles every time.
"""

import re
from typing import Optional, Tuple
from conversation_history.session_memory import SessionMemory, PaperReference


# ---------------------------------------------------------------------------
# Ordinal / positional word → integer index mapping
# ---------------------------------------------------------------------------
_ORDINAL_MAP = {
    # cardinal
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    # ordinal suffixes
    "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
    "6th": 6, "7th": 7, "8th": 8, "9th": 9, "10th": 10,
    # informal
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "last": -1,   # -1 means "last paper" → resolved dynamically
    "previous": -1,
    "latest": -1,
}

# Patterns that indicate the user is referring to a paper from the last results
_PAPER_REF_PATTERNS = [
    # "this paper", "that paper", "the paper"
    r"\b(this|that|the)\s+paper\b",
    # "the first paper", "second paper", "the last paper"
    r"\bthe\s+(\w+)\s+paper\b",
    r"\b(\w+)\s+paper\b",
    # "that one", "this one"
    r"\b(this|that)\s+one\b",
    # "the first one", "second one"
    r"\bthe\s+(\w+)\s+one\b",
    r"\b(\w+)\s+one\b",
    # "paper 2", "result 3"
    r"\b(paper|result|article)\s+(\d+)\b",
    # "#3", "number 2"
    r"#(\d+)\b",
    r"\bnumber\s+(\d+)\b",
]

# Phrases that strongly signal a reference is being made
_REF_TRIGGER_PHRASES = [
    "summarize", "summary of", "tell me about", "explain", "expand on",
    "more about", "details on", "details about", "what does",
    "what is", "who wrote", "when was", "cite", "citation for",
    "compare", "vs", "versus", "difference between",
    "abstract of", "authors of", "link to",
]


def detect_reference(query: str, memory: SessionMemory) -> Tuple[bool, Optional[PaperReference]]:
    """
    Detect whether the query references a previously discussed paper and resolve it.

    Returns:
        (is_reference, paper_or_None)
        - is_reference : True if the query appears to reference an earlier paper.
        - paper_or_None: The resolved PaperReference, or None if unresolvable.
    """
    if not memory.last_papers:
        return False, None

    q_lower = query.lower()

    # 1. Try to resolve via explicit ordinal ("first paper", "paper 2", "#3")
    paper = _resolve_by_ordinal(q_lower, memory)
    if paper:
        return True, paper

    # 2. Try to resolve via title fragment ("that transformer paper")
    paper = _resolve_by_title_fragment(q_lower, memory)
    if paper:
        return True, paper

    # 3. Check for generic references ("this paper", "that one") + trigger phrase
    if _has_generic_reference(q_lower) and _has_trigger_phrase(q_lower):
        # Default to most recently discussed paper
        paper = memory.get_paper_by_index(len(memory.last_papers))
        return True, paper

    # 4. Very short query with a trigger phrase and history → assume last paper
    words = q_lower.split()
    if len(words) <= 5 and _has_trigger_phrase(q_lower) and memory.chat_history:
        paper = memory.get_paper_by_index(len(memory.last_papers))
        return True, paper

    return False, None


def resolve_reference(query: str, memory: SessionMemory) -> Optional[PaperReference]:
    """
    Convenience wrapper: returns the resolved PaperReference or None.
    """
    _, paper = detect_reference(query, memory)
    return paper


def enrich_query_with_paper(query: str, paper: PaperReference) -> str:
    """
    Enrich a vague query by appending the resolved paper's title and abstract
    so the downstream LLM has full context.

    Example:
        query = "summarize that one"
        paper = PaperReference(title="Attention Is All You Need", ...)
        → "summarize that one\n\n[Resolved paper: Attention Is All You Need]\nAbstract: ..."
    """
    enriched = (
        f"{query}\n\n"
        f"[Resolved paper: {paper.title}]\n"
        f"Authors: {', '.join(paper.authors) if paper.authors else 'N/A'}\n"
        f"Abstract: {paper.summary}"
    )
    return enriched


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _resolve_by_ordinal(q_lower: str, memory: SessionMemory) -> Optional[PaperReference]:
    """Try to find an ordinal / positional reference in the query."""

    # Pattern: "paper 2", "result 3", "#3", "number 2"
    numeric_patterns = [
        r"\b(?:paper|result|article)\s+(\d+)\b",
        r"#(\d+)\b",
        r"\bnumber\s+(\d+)\b",
    ]
    for pat in numeric_patterns:
        m = re.search(pat, q_lower)
        if m:
            idx = int(m.group(1))
            return memory.get_paper_by_index(idx)

    # Pattern: ordinal words ("first paper", "second one", "the last paper")
    for word, idx in _ORDINAL_MAP.items():
        # Match ordinal word near "paper", "one", "result", "article"
        pattern = rf"\b{re.escape(word)}\s+(?:paper|one|result|article)\b"
        if re.search(pattern, q_lower):
            if idx == -1:
                # "last" / "previous"
                return memory.get_paper_by_index(len(memory.last_papers))
            return memory.get_paper_by_index(idx)

    return None


def _resolve_by_title_fragment(q_lower: str, memory: SessionMemory) -> Optional[PaperReference]:
    """
    Try to resolve by matching a distinctive keyword from known paper titles.

    Example: "that transformer paper" → looks for papers with "transformer" in title.
    """
    # Extract candidate keywords: remove stop words and short tokens
    stop_words = {
        "the", "a", "an", "that", "this", "those", "these", "paper", "one",
        "about", "on", "of", "for", "with", "and", "or", "is", "was", "by",
        "from", "in", "at", "to", "do", "can", "me", "it", "its",
    }
    tokens = [
        w for w in re.findall(r"[a-z]+", q_lower)
        if w not in stop_words and len(w) >= 4
    ]

    best_match: Optional[PaperReference] = None
    best_count = 0

    for paper in memory.last_papers:
        title_lower = paper.title.lower()
        count = sum(1 for token in tokens if token in title_lower)
        if count > best_count:
            best_count = count
            best_match = paper

    return best_match if best_count >= 1 else None


def _has_generic_reference(q_lower: str) -> bool:
    """Return True if the query contains a generic paper reference phrase."""
    generic_refs = [
        r"\b(this|that|the)\s+paper\b",
        r"\b(this|that)\s+one\b",
        r"\bthe\s+(first|second|third|last|previous)\b",
        r"\bit\b",
    ]
    for pat in generic_refs:
        if re.search(pat, q_lower):
            return True
    return False


def _has_trigger_phrase(q_lower: str) -> bool:
    """Return True if the query contains a phrase that implies action on a paper."""
    return any(phrase in q_lower for phrase in _REF_TRIGGER_PHRASES)


# ---------------------------------------------------------------------------
# Quick standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from session_memory import SessionMemory

    mem = SessionMemory()
    mem.update_last_papers([
        {
            "title": "Attention Is All You Need",
            "authors": ["Vaswani et al."],
            "summary": "Introduces the Transformer architecture based purely on attention mechanisms.",
            "source": "arxiv",
        },
        {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "authors": ["Devlin et al."],
            "summary": "Presents BERT, a pre-trained language model.",
            "source": "arxiv",
        },
        {
            "title": "RAG: Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
            "authors": ["Lewis et al."],
            "summary": "Combines parametric and non-parametric memory for generation.",
            "source": "arxiv",
        },
    ])
    mem.add_user_message("Find papers on transformers")
    mem.add_assistant_message("I found 3 papers ...")

    tests = [
        "summarize the first paper",
        "tell me more about that BERT paper",
        "who wrote paper 3",
        "expand on the last one",
        "summarize it",
        "what is the abstract of paper 2",
        "find papers on diffusion models",      # not a reference
    ]

    for q in tests:
        is_ref, paper = detect_reference(q, mem)
        title = paper.title if paper else "None"
        print(f"Query : {q!r}")
        print(f"Is ref: {is_ref}  →  {title}")
        print()