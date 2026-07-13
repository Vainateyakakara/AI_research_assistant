"""
session_memory.py - Stores current conversation history, previous queries,
responses, and last discussed papers for the Research AI Assistant.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PaperReference:
    """Represents a paper that was discussed in the session."""
    title: str
    authors: List[str]
    summary: str
    url: str = ""
    arxiv_id: str = ""
    source: str = "arxiv"           # "arxiv" or "vector_store"
    discussed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "summary": self.summary,
            "url": self.url,
            "arxiv_id": self.arxiv_id,
            "source": self.source,
            "discussed_at": self.discussed_at,
        }

    @staticmethod
    def from_dict(data: Dict) -> "PaperReference":
        return PaperReference(
            title=data.get("title", ""),
            authors=data.get("authors", []),
            summary=data.get("summary", ""),
            url=data.get("url", ""),
            arxiv_id=data.get("arxiv_id", ""),
            source=data.get("source", "arxiv"),
            discussed_at=data.get("discussed_at", datetime.now().isoformat()),
        )


@dataclass
class ChatTurn:
    """A single turn in the conversation."""
    role: str           # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @staticmethod
    def from_dict(data: Dict) -> "ChatTurn":
        return ChatTurn(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


class SessionMemory:
    """
    Central memory store for a single research assistant session.

    Maintains:
    - chat_history   : ordered list of user/assistant turns
    - last_papers    : most recently retrieved/discussed papers (up to max_papers)
    - last_topic     : the topic of the last user query (for context continuity)
    - last_query     : the raw last user query
    """

    def __init__(self, max_history: int = 20, max_papers: int = 10):
        self.max_history = max_history
        self.max_papers = max_papers

        self.chat_history: List[ChatTurn] = []
        self.last_papers: List[PaperReference] = []
        self.last_topic: str = ""
        self.last_query: str = ""

    # ------------------------------------------------------------------
    # Chat history management
    # ------------------------------------------------------------------

    def add_user_message(self, message: str) -> None:
        """Record a user message and update last_query."""
        self.last_query = message
        self.chat_history.append(ChatTurn(role="user", content=message))
        self._trim_history()

    def add_assistant_message(self, message: str) -> None:
        """Record an assistant response."""
        self.chat_history.append(ChatTurn(role="assistant", content=message))
        self._trim_history()

    def _trim_history(self) -> None:
        """Keep only the most recent max_history turns."""
        if len(self.chat_history) > self.max_history:
            self.chat_history = self.chat_history[-self.max_history:]

    def get_chat_history(self) -> List[Dict]:
        """Return the full chat history as a list of dicts."""
        return [turn.to_dict() for turn in self.chat_history]

    def get_recent_history(self, n: int = 6) -> List[Dict]:
        """Return the last n turns (useful for context injection into prompts)."""
        return [turn.to_dict() for turn in self.chat_history[-n:]]

    def format_history_for_prompt(self, n: int = 6) -> str:
        """
        Format recent history into a plain-text block suitable for LLM prompts.

        Example output:
            User: what is RAG?
            Assistant: RAG stands for Retrieval Augmented Generation ...
        """
        turns = self.chat_history[-n:]
        lines = []
        for turn in turns:
            label = "User" if turn.role == "user" else "Assistant"
            lines.append(f"{label}: {turn.content}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Paper management
    # ------------------------------------------------------------------

    def update_last_papers(self, papers: List[Dict]) -> None:
        """
        Replace the current last_papers list with newly retrieved papers.

        Accepts dicts with at least 'title' and 'summary' keys (as returned by
        arxiv_search or the vector store retriever).
        """
        self.last_papers = []
        for p in papers[:self.max_papers]:
            ref = PaperReference(
                title=p.get("title", "Unknown Title"),
                authors=p.get("authors", []),
                summary=p.get("summary", p.get("abstract", "")),
                url=p.get("url", p.get("entry_id", "")),
                arxiv_id=p.get("arxiv_id", ""),
                source=p.get("source", "arxiv"),
            )
            self.last_papers.append(ref)

    def get_last_papers(self) -> List[Dict]:
        """Return the last discussed papers as a list of dicts."""
        return [p.to_dict() for p in self.last_papers]

    def get_paper_by_index(self, index: int) -> Optional[PaperReference]:
        """Return a paper by its 1-based index (e.g. 'first paper' → index=1)."""
        if 1 <= index <= len(self.last_papers):
            return self.last_papers[index - 1]
        return None

    def get_paper_by_title_fragment(self, fragment: str) -> Optional[PaperReference]:
        """Find a paper whose title contains the given fragment (case-insensitive)."""
        fragment_lower = fragment.lower()
        for paper in self.last_papers:
            if fragment_lower in paper.title.lower():
                return paper
        return None

    # ------------------------------------------------------------------
    # Topic tracking
    # ------------------------------------------------------------------

    def set_last_topic(self, topic: str) -> None:
        self.last_topic = topic

    def get_last_topic(self) -> str:
        return self.last_topic

    # ------------------------------------------------------------------
    # Serialisation helpers (useful if you want to persist across restarts)
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chat_history": [t.to_dict() for t in self.chat_history],
            "last_papers": [p.to_dict() for p in self.last_papers],
            "last_topic": self.last_topic,
            "last_query": self.last_query,
        }

    def load_from_dict(self, data: Dict[str, Any]) -> None:
        self.chat_history = [ChatTurn.from_dict(t) for t in data.get("chat_history", [])]
        self.last_papers = [PaperReference.from_dict(p) for p in data.get("last_papers", [])]
        self.last_topic = data.get("last_topic", "")
        self.last_query = data.get("last_query", "")

    def clear(self) -> None:
        """Reset the entire session."""
        self.chat_history = []
        self.last_papers = []
        self.last_topic = ""
        self.last_query = ""

    def __repr__(self) -> str:
        return (
            f"SessionMemory("
            f"turns={len(self.chat_history)}, "
            f"papers={len(self.last_papers)}, "
            f"last_topic='{self.last_topic}')"
        )