"""
conversation_manager.py - The brain of the Research AI Assistant.

Decides whether to:
  1. Rewrite the query (query_rewriter)
  2. Resolve vague paper references (reference_resolver)
  3. Use the local vector retriever, arXiv, or both
  4. Generate the final LLM response
  5. Update session memory after every turn

Keeps main.py clean by centralising all orchestration logic here.
"""

from typing import Optional, List, Dict, Callable, Any
from conversation_history.session_memory import SessionMemory, PaperReference
from conversation_history.query_rewriter import rewrite_query
from conversation_history.reference_resolver import detect_reference, enrich_query_with_paper


# ---------------------------------------------------------------------------
# Type aliases for pluggable components
# ---------------------------------------------------------------------------
LLMFn = Callable[[str], str]                  # (prompt) → response text
RetrieverFn = Callable[[str, int], List[Dict]]  # (query, k) → list of paper dicts
ArxivFn = Callable[[str, int], str]            # (query, max) → formatted string


class ConversationManager:
    """
    Orchestrates a multi-turn research assistant conversation.

    Usage:
        manager = ConversationManager(
            llm_fn=your_llm_function,
            retriever_fn=your_retriever_function,   # optional
            arxiv_fn=your_arxiv_search_function,    # optional
        )
        response = manager.handle_turn("Find RAG papers from 2024")
        response = manager.handle_turn("Summarize the second one")
    """

    def __init__(
        self,
        llm_fn: LLMFn,
        retriever_fn: Optional[RetrieverFn] = None,
        arxiv_fn: Optional[ArxivFn] = None,
        memory: Optional[SessionMemory] = None,
        max_retriever_results: int = 5,
        max_arxiv_results: int = 3,
        use_arxiv_fallback: bool = True,
    ):
        self.llm_fn = llm_fn
        self.retriever_fn = retriever_fn
        self.arxiv_fn = arxiv_fn
        self.memory = memory or SessionMemory()
        self.max_retriever_results = max_retriever_results
        self.max_arxiv_results = max_arxiv_results
        self.use_arxiv_fallback = use_arxiv_fallback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_turn(self, user_query: str) -> str:
        """
        Process a single user turn and return the assistant's response.

        Full pipeline:
          1. Save the raw user message to memory.
          2. Resolve vague paper references ("that one", "second paper").
          3. Rewrite incomplete follow-up queries into standalone queries.
          4. Retrieve relevant papers (vector store + optional arXiv).
          5. Build a prompt with context and chat history.
          6. Call the LLM for the final answer.
          7. Save the assistant response to memory.
        """
        # Step 1: Record raw user message
        self.memory.add_user_message(user_query)

        # Step 2: Reference resolution
        is_reference, resolved_paper = detect_reference(user_query, self.memory)
        working_query = user_query

        if is_reference and resolved_paper:
            # Enrich the query with the resolved paper so the LLM has full context
            working_query = enrich_query_with_paper(user_query, resolved_paper)
            # Build response directly from the resolved paper (no retrieval needed)
            response = self._respond_about_paper(user_query, resolved_paper)
            self.memory.add_assistant_message(response)
            return response

        # Step 3: Query rewriting (for incomplete follow-ups)
        rewritten_query = rewrite_query(
            working_query,
            self.memory,
            llm_fn=self._simple_llm_fn,   # use LLM for rewriting when available
        )

        # Track topic for future follow-ups
        self._update_topic(rewritten_query)

        # Step 4: Retrieval
        context_text, retrieved_papers = self._retrieve(rewritten_query)

        # Update memory with newly retrieved papers
        if retrieved_papers:
            self.memory.update_last_papers(retrieved_papers)

        # Step 5 & 6: Build prompt and call LLM
        prompt = self._build_response_prompt(user_query, rewritten_query, context_text)
        response = self.llm_fn(prompt)

        # Step 7: Save assistant response
        self.memory.add_assistant_message(response)
        return response

    def clear_session(self) -> None:
        """Reset the conversation (useful for 'new chat' functionality)."""
        self.memory.clear()

    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Return the current memory state (for debugging / persistence)."""
        return self.memory.to_dict()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _retrieve(self, query: str) -> tuple[str, List[Dict]]:
        """
        Run retrieval from vector store and/or arXiv.

        Returns:
            (context_text, list_of_paper_dicts)
        """
        context_parts: List[str] = []
        all_papers: List[Dict] = []

        # Vector store retrieval
        if self.retriever_fn:
            try:
                vector_papers = self.retriever_fn(query, self.max_retriever_results)
                if vector_papers:
                    all_papers.extend(vector_papers)
                    formatted = _format_papers_for_prompt(vector_papers, source_label="Local Knowledge Base")
                    context_parts.append(formatted)
            except Exception as e:
                context_parts.append(f"[Vector retriever error: {e}]")

        # arXiv search (always, or as fallback)
        run_arxiv = self.use_arxiv_fallback and self.arxiv_fn is not None
        if run_arxiv:
            try:
                arxiv_text = self.arxiv_fn(query, self.max_arxiv_results)
                if arxiv_text:
                    context_parts.append(f"--- arXiv Search Results ---\n{arxiv_text}")
                    # arXiv results arrive as formatted text; we can't easily parse them
                    # back into structured dicts here, so we leave all_papers as-is.
            except Exception as e:
                context_parts.append(f"[arXiv error: {e}]")

        context_text = "\n\n".join(context_parts) if context_parts else "No relevant papers found."
        return context_text, all_papers

    def _respond_about_paper(self, original_query: str, paper: PaperReference) -> str:
        """
        Generate an LLM response focused on a single resolved paper.
        """
        history_text = self.memory.format_history_for_prompt(n=4)
        prompt = f"""You are a helpful research assistant.

The user asked: "{original_query}"

You have resolved this to the following paper:
Title: {paper.title}
Authors: {', '.join(paper.authors) if paper.authors else 'N/A'}
Source: {paper.source}
Abstract/Summary:
{paper.summary}

Recent conversation:
{history_text}

Provide a helpful, detailed response to the user's question about this paper.
"""
        return self.llm_fn(prompt)

    def _build_response_prompt(
        self,
        original_query: str,
        rewritten_query: str,
        context_text: str,
    ) -> str:
        """Build the main response prompt including chat history and retrieved context."""
        history_text = self.memory.format_history_for_prompt(n=6)
        last_topic = self.memory.get_last_topic()

        rewrite_note = ""
        if rewritten_query != original_query:
            rewrite_note = f"\n(Note: The query was interpreted as: \"{rewritten_query}\")\n"

        prompt = f"""You are an expert research assistant specializing in academic papers.

Conversation history:
{history_text}

User's latest query: "{original_query}"{rewrite_note}

Retrieved context from papers:
{context_text}

Instructions:
- Answer the user's question using the retrieved papers as your primary source.
- Cite paper titles when referring to specific papers.
- If the retrieved context doesn't fully answer the question, say so clearly.
- Maintain a natural conversational tone consistent with prior exchanges.
- If multiple papers are relevant, compare or synthesize them helpfully.
- Current topic context: {last_topic if last_topic else 'General research query'}

Your response:"""
        return prompt

    def _simple_llm_fn(self, prompt: str) -> str:
        """
        Thin wrapper so query_rewriter can call the same LLM.
        Keeps responses short (rewriting only needs a single line output).
        """
        return self.llm_fn(prompt)

    def _update_topic(self, rewritten_query: str) -> None:
        """
        Extract a short topic label from the rewritten query and store it.

        Simple heuristic: strip common verbs and take the first ~5 meaningful words.
        """
        strip_prefixes = [
            "find", "search", "look for", "show me", "get", "retrieve",
            "give me", "list", "what are", "tell me about", "explain",
        ]
        topic = rewritten_query.lower().strip()
        for prefix in strip_prefixes:
            if topic.startswith(prefix):
                topic = topic[len(prefix):].strip()
                break

        # Capitalise and truncate to ~60 chars
        topic = topic.strip(" .,?!").capitalize()[:60]
        if topic:
            self.memory.set_last_topic(topic)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _format_papers_for_prompt(papers: List[Dict], source_label: str = "Retrieved Papers") -> str:
    """Format a list of paper dicts into a readable block for LLM prompts."""
    if not papers:
        return ""
    lines = [f"--- {source_label} ---"]
    for i, p in enumerate(papers, 1):
        title = p.get("title", "Unknown Title")
        authors = ", ".join(p.get("authors", [])) or "N/A"
        summary = p.get("summary", p.get("abstract", "No abstract available."))
        lines.append(f"\n[{i}] {title}")
        lines.append(f"    Authors: {authors}")
        lines.append(f"    Abstract: {summary[:400]}{'...' if len(summary) > 400 else ''}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Mock LLM that echoes the prompt summary
    def mock_llm(prompt: str) -> str:
        lines = prompt.strip().split("\n")
        return f"[MockLLM response] Received {len(lines)}-line prompt. Answering query."

    # Mock retriever
    def mock_retriever(query: str, k: int) -> List[Dict]:
        return [
            {
                "title": "Attention Is All You Need",
                "authors": ["Vaswani", "Shazeer"],
                "summary": "Introduces the Transformer model using self-attention.",
                "source": "vector_store",
            },
            {
                "title": "BERT Pre-training",
                "authors": ["Devlin et al."],
                "summary": "Bidirectional transformer for language understanding.",
                "source": "vector_store",
            },
        ]

    manager = ConversationManager(
        llm_fn=mock_llm,
        retriever_fn=mock_retriever,
    )

    turns = [
        "Find papers on transformer architectures",
        "only from 2023",                          
        "summarize the first paper",                
        "who are the authors of paper 2",           
        "Find papers on diffusion models",
    ]

    for turn in turns:
        print(f"\n{'='*60}")
        print(f"User: {turn}")
        response = manager.handle_turn(turn)
        print(f"Assistant: {response}")

    print(f"\nMemory snapshot: {manager.memory}")