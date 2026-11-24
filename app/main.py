"""
app/main.py - Main Streamlit application (with conversational memory)
"""

import streamlit as st
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
    
from router import QueryRouter
from ingestion.loader import DocumentLoader
from ingestion.chunking import DocumentChunker
from ingestion.embeddings import EmbeddingGenerator
from retrieval.vector_store import VectorStore
from retrieval.retriever import DocumentRetriever
from conversation_history.session_memory import SessionMemory
from conversation_history.query_rewriter import rewrite_query
from conversation_history.reference_resolver import detect_reference, enrich_query_with_paper
from conversation_history import conversation_manager
import config

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stAlert { padding: 1rem; border-radius: 0.5rem; }
    .mode-badge {
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.2rem;
    }
    .simple     { background: #e3f2fd; color: #1976d2; }
    .analytical { background: #fff3e0; color: #f57c00; }
    .research   { background: #fce4ec; color: #c2185b; }
    .upload-success { background: #e8f5e9; padding: 1rem; border-radius: 0.5rem; }

    /* Chat bubble styles */
    .chat-user {
        background: #e8f0fe;
        border-radius: 1rem 1rem 0.2rem 1rem;
        padding: 0.75rem 1rem;
        margin: 0.4rem 0;
        max-width: 80%;
        margin-left: auto;
        color: #1a1a2e;
        font-size: 0.95rem;
    }
    .chat-assistant {
        background: #f1f3f4;
        border-radius: 1rem 1rem 1rem 0.2rem;
        padding: 0.75rem 1rem;
        margin: 0.4rem 0;
        max-width: 85%;
        color: #1a1a2e;
        font-size: 0.95rem;
    }
    .chat-label {
        font-size: 0.75rem;
        color: #888;
        margin-bottom: 0.15rem;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .rewrite-pill {
        background: #fff8e1;
        color: #f57f17;
        border-radius: 0.5rem;
        padding: 0.2rem 0.6rem;
        font-size: 0.78rem;
        border: 1px solid #ffe082;
        display: inline-block;
        margin-bottom: 0.4rem;
    }
    .ref-pill {
        background: #e8f5e9;
        color: #2e7d32;
        border-radius: 0.5rem;
        padding: 0.2rem 0.6rem;
        font-size: 0.78rem;
        border: 1px solid #a5d6a7;
        display: inline-block;
        margin-bottom: 0.4rem;
    }

    div[data-testid="column"] .stButton > button {
        height: 3rem;
        font-size: 1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'history' not in st.session_state:
    st.session_state.history = []          # raw Streamlit history (backward compat)
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []

# ── Conversational memory (persists across reruns via session_state) ───────────
if 'session_memory' not in st.session_state:
    st.session_state.session_memory = SessionMemory(max_history=30, max_papers=10)

# ── Rich chat log (stores extra metadata per turn for display) ─────────────────
if 'chat_log' not in st.session_state:
    st.session_state.chat_log = []
    # Each entry:  {
    #   'query'         : str  (original user text)
    #   'rewritten'     : str  (rewritten query, may equal query)
    #   'resolved_paper': str | None  (title of resolved paper if any)
    #   'result'        : dict (router result)
    #   'mode'          : str  ('analysis' | 'research' | 'simple')
    # }


# ── Cached component initialisation ───────────────────────────────────────────
@st.cache_resource
def init_components():
    print("Initialising components...")
    vector_store = VectorStore()
    retriever    = DocumentRetriever(vector_store)
    router       = QueryRouter(retriever)
    return {
        'vector_store': vector_store,
        'retriever':    retriever,
        'router':       router,
        'loader':       DocumentLoader(),
        'chunker':      DocumentChunker(),
    }


with st.spinner("Loading AI models..."):
    components = init_components()
    st.session_state.vector_store = components['vector_store']


# ── Convenience shorthand ──────────────────────────────────────────────────────
mem: SessionMemory = st.session_state.session_memory


# ── LLM wrapper (used by query_rewriter for LLM-based rewriting) ───────────────
def _llm_rewrite_fn(prompt: str) -> str:
    """
    Thin wrapper so query_rewriter can call the existing router's LLM.
    We route as 'simple' (direct LLM, no retrieval) to keep it fast.
    """
    try:
        result = components['router'].route(prompt, mode="simple")
        return result.get("answer", "").strip()
    except Exception:
        return ""


# ── Header ─────────────────────────────────────────────────────────────────────
st.title("AI Research Assistant 🔬")
st.caption("Powered by Groq (Llama 3.1) + Google Gemini Pro • 100 % Free")


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("System Status")

    groq_status   = "configured" if config.GROQ_API_KEY   else "not configured"
    gemini_status = "configured" if config.GEMINI_API_KEY else "not configured"

    st.markdown(f"""
    **API Keys:**
    - Groq: {groq_status}
    - Gemini: {gemini_status}
    """)

    stats = st.session_state.vector_store.get_collection_stats()
    st.metric("Local Documents in DB", stats['num_documents'])

    st.divider()

    # ── Conversation memory stats ──────────────────────────────────────────
    st.header("Conversation Memory")
    st.metric("Turns in memory", len(mem.chat_history))
    st.metric("Papers in memory", len(mem.last_papers))
    if mem.last_topic:
        st.caption(f" Last topic: **{mem.last_topic}**")
    if mem.last_query:
        st.caption(f" Last query: *{mem.last_query[:50]}{'...' if len(mem.last_query) > 50 else ''}*")

    if mem.last_papers:
        with st.expander(f"Papers in memory ({len(mem.last_papers)})"):
            for i, p in enumerate(mem.last_papers, 1):
                st.caption(f"{i}. {p.title[:60]}...")

    if st.button(" Clear Conversation Memory"):
        st.session_state.session_memory = SessionMemory(max_history=30, max_papers=10)
        st.session_state.chat_log = []
        st.session_state.history  = []
        st.rerun()

    st.divider()

    st.header("Query Modes")
    st.markdown("""
    <div style='font-size:0.85rem;'>
    <span class='mode-badge analytical'>ANALYSE</span><br>
    Compare & analyse your <b>uploaded</b> documents<br>
    <i>Retrieval from local DB → Gemini</i>
    <br><br>
    <span class='mode-badge research'>RESEARCH</span><br>
    Search the latest papers on arXiv<br>
    <i>arXiv Search → Download → Chunk → Temp DB → Retrieve → LLM</i>
    <br><br>
    <span class='mode-badge simple'>SIMPLE</span><br>
    Direct Groq answer — no document lookup
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.header("Uploaded Papers")
    pdf_files = [f for f in os.listdir(config.DATA_RAW_PATH) if f.endswith('.pdf')]
    if pdf_files:
        for pdf in pdf_files:
            st.text(f"• {pdf}")
    else:
        st.caption("No papers uploaded yet")


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Ask Questions", "Upload Papers"])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 – QUERY INTERFACE
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Ask a Research Question")

    query = st.text_area(
        "Enter your question:",
        height=100,
        placeholder=(
            "e.g. 'Compare the two uploaded papers on attention'  •  "
            "'Latest research on RAG systems'  •  "
            "'What is a transformer?'  •  "
            "'only from 2024'  •  'summarize the second one'"
        ),
    )

    show_details = st.checkbox("Show pipeline details", value=True)

    # ── Three-column button row ────────────────────────────────────────────────
    st.markdown("**Choose how to process your question:**")
    col_analysis, col_research, col_simple = st.columns(3)

    with col_analysis:
        analysis_btn = st.button(
            " Analyse Documents",
            use_container_width=True,
            help="Compare & analyse your uploaded PDFs — Retrieval from local DB + Gemini",
        )
    with col_research:
        research_btn = st.button(
            " Research",
            use_container_width=True,
            help=(
                "Full arXiv pipeline: Search → Download PDFs → Chunk → "
                "Temp Vector DB → Retrieve → LLM"
            ),
        )
    with col_simple:
        simple_btn = st.button(
            " Quick Answer",
            use_container_width=True,
            help="Direct Groq answer — fast, no document retrieval",
        )

    st.caption(
        "**Analyse** uses your uploaded docs.  "
        "**Research** fetches fresh papers from arXiv.  "
        "Conversational follow-ups like *'only from 2024'* or *'summarize the first one'* work automatically."
    )

    # ── Determine mode ─────────────────────────────────────────────────────────
    if analysis_btn:
        selected_mode = "analysis"
    elif research_btn:
        selected_mode = "research"
    elif simple_btn:
        selected_mode = "simple"
    else:
        selected_mode = None

    # ── Process ────────────────────────────────────────────────────────────────
    if selected_mode and query.strip():

        # ── Step 1: Reference resolution ──────────────────────────────────────
        is_reference, resolved_paper = detect_reference(query, mem)
        resolved_paper_title = None
        working_query = query

        if is_reference and resolved_paper:
            resolved_paper_title = resolved_paper.title
            # Enrich the query so the LLM has full paper context
            working_query = enrich_query_with_paper(query, resolved_paper)

        # ── Step 2: Query rewriting ────────────────────────────────────────────
        # Only rewrite if it's NOT already a resolved reference (reference
        # resolution already handled the context enrichment in that case).
        rewritten_query = query
        if not is_reference:
            rewritten_query = rewrite_query(query, mem, llm_fn=_llm_rewrite_fn)

        # ── Step 3: Record user message in memory ──────────────────────────────
        mem.add_user_message(query)

        # ── Step 4: Route to the router with the enriched / rewritten query ────
        spinner_msg = {
            "analysis": " Retrieving from local DB and analysing with Gemini...",
            "research": (
                " Searching arXiv, downloading papers, indexing & retrieving... "
                "(this may take ~30–60 s)"
            ),
            "simple":   " Generating quick answer...",
        }[selected_mode]

        with st.spinner(spinner_msg):
            result = components['router'].route(working_query, mode=selected_mode)

        # ── Step 5: Update memory with retrieved papers ────────────────────────
        if result.get('sources'):
            raw_papers = []
            for s in result['sources']:
                raw_papers.append({
                    "title":    s.get('title', s.get('source_file', 'Unknown')),
                    "authors":  s.get('authors', []),
                    "summary":  s.get('summary', s.get('abstract', '')),
                    "url":      s.get('url', ''),
                    "arxiv_id": s.get('arxiv_id', ''),
                    "source":   "arxiv" if result.get('type') == 'research' else "vector_store",
                })
            # Deduplicate by title before saving to memory
            seen = set()
            unique_papers = []
            for p in raw_papers:
                if p['title'] not in seen:
                    seen.add(p['title'])
                    unique_papers.append(p)
            mem.update_last_papers(unique_papers)

        # ── Step 6: Update topic in memory ────────────────────────────────────
        effective_query = rewritten_query if not is_reference else query
        _topic_raw = effective_query.lower().strip()
        for prefix in ("find", "search", "show me", "get", "what are", "tell me about"):
            if _topic_raw.startswith(prefix):
                _topic_raw = _topic_raw[len(prefix):].strip()
                break
        mem.set_last_topic(_topic_raw.capitalize()[:60])

        # ── Step 7: Record assistant response in memory ────────────────────────
        mem.add_assistant_message(result['answer'])

        # ── Step 8: Append to rich chat log ───────────────────────────────────
        st.session_state.chat_log.append({
            'query':          query,
            'rewritten':      rewritten_query,
            'resolved_paper': resolved_paper_title,
            'result':         result,
            'mode':           selected_mode,
        })
        st.session_state.history.append({'query': query, 'result': result})

        st.divider()

        # ── Display: mode badge + model ────────────────────────────────────────
        badge_class = {
            'simple':     'simple',
            'analytical': 'analytical',
            'research':   'research',
        }.get(result['type'], 'simple')

        st.markdown(f"""
        <div style='margin-bottom:0.5rem;'>
        <span class='mode-badge {badge_class}'>{result['type'].upper()}</span>
        <span style='color:#666; margin-left:1rem; font-size:0.85rem;'>
            Model: {result['model']}
        </span>
        </div>
        """, unsafe_allow_html=True)

        # ── Display: conversational memory annotations ─────────────────────────
        if show_details:
            if resolved_paper_title:
                st.markdown(
                    f"<span class='ref-pill'>📎 Resolved reference → <b>{resolved_paper_title[:70]}</b></span>",
                    unsafe_allow_html=True,
                )
            if rewritten_query != query and not is_reference:
                st.markdown(
                    f"<span class='rewrite-pill'> Query interpreted as → <b>{rewritten_query}</b></span>",
                    unsafe_allow_html=True,
                )
            st.caption("Pipeline: " + " → ".join(result['pipeline']))

        # ── Display: answer ────────────────────────────────────────────────────
        st.markdown("### Answer")
        st.write(result['answer'])

        # ── Display: sources ───────────────────────────────────────────────────
        if result.get('sources'):
            is_research = result['type'] == 'research'
            if is_research:
                unique_sources = {}
                for s in result['sources']:
                    arxiv_id = s.get('arxiv_id')
                    if arxiv_id not in unique_sources:
                        unique_sources[arxiv_id] = s
                display_sources = list(unique_sources.values())
            else:
                display_sources = result['sources']

            num_chunks = len(result['sources'])
            num_unique = len(display_sources)

            label = (
                f"arXiv Sources — {num_unique} paper(s), {num_chunks} chunks retrieved"
                if is_research
                else f" Local Sources ({num_chunks} chunks)"
            )

            with st.expander(label):
                for i, source in enumerate(display_sources, 1):
                    if is_research:
                        arxiv_id  = source.get('arxiv_id', '')
                        title     = source.get('title', source.get('source_file', 'Unknown'))
                        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None
                        st.markdown(
                            f"**{i}. {title}**"
                            + (f" — [arXiv:{arxiv_id}]({arxiv_url})" if arxiv_url else "")
                            + f"  (Page {source.get('page', 'N/A')})"
                        )
                    else:
                        st.markdown(
                            f"**{i}. {source.get('source_file', 'Unknown')}** "
                            f"(Page {source.get('page', 'N/A')})"
                        )

                    if 'relevance_score' in source:
                        st.caption(f"Relevance: {source['relevance_score']:.3f}")
                    st.divider()

        # ── Display: extracted info (research mode) ────────────────────────────
        if result.get('extracted_info') and show_details:
            with st.expander(" Extracted Information (pre-synthesis)"):
                st.write(result['extracted_info'])

    elif selected_mode and not query.strip():
        st.warning(" Please enter a question before clicking a button.")

    # ── Clear history button ───────────────────────────────────────────────────
    if st.button(" Clear History"):
        st.session_state.history  = []
        st.session_state.chat_log = []
        st.session_state.session_memory = SessionMemory(max_history=30, max_papers=10)
        st.rerun()

    # ── Conversational chat log ────────────────────────────────────────────────
    if st.session_state.chat_log:
        st.divider()
        st.header(" Conversation History")

        for i, entry in enumerate(st.session_state.chat_log, 1):
            # ── User bubble ───────────────────────────────────────────────────
            st.markdown(f"<div class='chat-label' style='text-align:right;'>You</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='chat-user'>{entry['query']}</div>", unsafe_allow_html=True)

            # ── Memory annotation pills ───────────────────────────────────────
            pills_html = ""
            if entry.get('resolved_paper'):
                pills_html += f"<span class='ref-pill'> {entry['resolved_paper'][:55]}...</span> "
            if entry['rewritten'] != entry['query'] and not entry.get('resolved_paper'):
                pills_html += f"<span class='rewrite-pill'> {entry['rewritten'][:70]}</span>"
            if pills_html:
                st.markdown(pills_html, unsafe_allow_html=True)

            # ── Assistant bubble ──────────────────────────────────────────────
            badge_class = {
                'simple':     'simple',
                'analytical': 'analytical',
                'research':   'research',
            }.get(entry['result']['type'], 'simple')

            st.markdown(f"<div class='chat-label'>🔬 Assistant <span class='mode-badge {badge_class}' style='font-size:0.7rem;padding:0.1rem 0.5rem;'>{entry['result']['type'].upper()}</span></div>", unsafe_allow_html=True)
            answer_preview = entry['result']['answer']
            st.markdown(f"<div class='chat-assistant'>{answer_preview[:500]}{'...' if len(answer_preview) > 500 else ''}</div>", unsafe_allow_html=True)

            # ── Full answer toggle ────────────────────────────────────────────
            if len(answer_preview) > 500:
                with st.expander("Read full answer"):
                    st.write(entry['result']['answer'])

            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 – UPLOAD INTERFACE  (unchanged)
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("📤 Upload Research Papers")
    st.info(
        " Upload PDFs here to add them to your **local knowledge base**. "
        "Use ** Analyse Documents** to query them. "
        "The ** Research** button fetches fresh papers from arXiv instead."
    )

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload research papers to add to your local knowledge base",
    )

    if uploaded_file:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f" File selected: **{uploaded_file.name}**")
            st.caption(f"Size: {uploaded_file.size / 1024:.1f} KB")
        with col2:
            process_btn = st.button(" Process", type="primary", use_container_width=True)

        if process_btn:
            with st.spinner("Processing document..."):
                try:
                    st.info(" Saving PDF to data/raw/...")
                    filename  = os.path.basename(uploaded_file.name)
                    save_path = os.path.join(config.DATA_RAW_PATH, filename)
                    with open(save_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f" Saved to {save_path}")

                    st.info(" Loading document...")
                    docs = components['loader'].load_pdf_pymupdf(save_path)
                    st.success(f" Loaded {len(docs)} pages")

                    st.info(" Chunking text...")
                    chunks      = components['chunker'].chunk_documents(docs)
                    chunk_stats = components['chunker'].get_chunk_stats(chunks)
                    st.success(f" Created {chunk_stats['num_chunks']} chunks")

                    st.info(" Adding to ChromaDB...")
                    st.session_state.vector_store.add_documents(chunks, show_progress=False)
                    st.success(" Added to local vector database")

                    st.markdown("---")
                    st.markdown("###  Processing Complete!")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Pages",    len(docs))
                    c2.metric("Chunks",   chunk_stats['num_chunks'])
                    c3.metric("Avg Size", f"{chunk_stats['avg_chunk_size']:.0f}")

                    new_stats = st.session_state.vector_store.get_collection_stats()
                    st.info(f" Total documents in local database: **{new_stats['num_documents']}**")
                    st.session_state.uploaded_files.append(uploaded_file.name)

                except Exception as e:
                    st.error(f" Error processing file: {e}")

    st.divider()
    st.header(" Current Local Database")
    db_stats = st.session_state.vector_store.get_collection_stats()
    c1, c2 = st.columns(2)
    c1.metric("Total Chunks", db_stats['num_documents'])
    c2.metric("Papers", len([f for f in os.listdir(config.DATA_RAW_PATH) if f.endswith('.pdf')]))


# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
col1, col2 = st.columns([3, 1])
with col1:
    st.caption("Powered by Groq (Llama 3.1) + Google Gemini Pro • 100 % Free Tier")
with col2:
    if st.button(" Reload App"):
        st.rerun()