# 🔬 AI Research Assistant

An advanced **RAG-based AI system** that enables academic research, document analysis, and real-time AI responses using live arXiv papers and uploaded PDFs.

Built with **React.js** frontend + **FastAPI** (Python) backend.

---

## 🚀 Features

### 🧠 Multi-Mode Query System

- **📊 Analysis Mode** → Compare uploaded PDFs using Retrieval + Gemini  
- **🔬 Research Mode** → Full pipeline: Query → arXiv Search → PDF Download → Chunking → Temp Vector DB → Retrieval → LLM
- **⚡ Simple Mode** → Fast responses via Groq (Llama 3.1)

### 🔍 Retrieval-Augmented Generation (RAG)

- Context-aware answers using uploaded documents and real-time arXiv papers
- Semantic retrieval using HuggingFace embeddings
- Source attribution with paper titles, arXiv links, and relevance scores

### 📄 Document Processing

- Upload research papers (PDF)
- Automatic chunking & embedding
- Stored in ChromaDB vector database

### 🤖 Multi-Model Orchestration

- **Groq (Llama 3.1)** → fast responses
- **Gemini Pro** → document analysis & research synthesis

### 💬 Conversational Memory

- Multi-turn context awareness
- Query rewriting for follow-up questions
- Paper reference resolution ("summarize the first paper")

---

## 🏗️ Architecture

```
React.js Frontend (Vite)  ←→  FastAPI Backend (Python)
     ↓                              ↓
  Premium UI               Existing Python Modules:
  - Chat Interface          - LLMs (Groq + Gemini)
  - Upload Panel            - ChromaDB Vector Store
  - Sidebar Stats           - Document Ingestion
                            - arXiv Search Pipeline
                            - Conversation Memory
```

---

## 🧪 Tech Stack

- **Frontend**: React.js, Vite, Vanilla CSS
- **Backend**: FastAPI, Python
- **AI/ML**: Groq API (Llama 3.1), Google Gemini API
- **Vector DB**: ChromaDB
- **Embeddings**: HuggingFace (all-MiniLM-L6-v2)
- **Papers**: arXiv API
- **PDF Parsing**: PyMuPDF

---

## ⚡ Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-research-assistant.git
cd ai-research-assistant
```

### 2. Set up environment variables

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
pip install -r server/requirements.txt
```

### 4. Install frontend dependencies

```bash
cd client
npm install
cd ..
```

### 5. Start the backend (Terminal 1)

```bash
python -m uvicorn server.main:app --reload --port 8000
```

### 6. Start the frontend (Terminal 2)

```bash
cd client
npm run dev
```

The app will be available at **http://localhost:5173** (frontend) calling **http://localhost:8000** (API).

---

## 📖 Usage

### Upload Papers
- Go to the **Upload Papers** tab
- Drag & drop or select a PDF
- Click **Process** to add to your knowledge base

### Ask Questions
- Enter your query in the text box
- Select a mode:
  - 📊 **Analyse** — query your uploaded docs
  - 🔬 **Research** — search arXiv for fresh papers
  - ⚡ **Quick Answer** — direct LLM response
- Conversational follow-ups like "only from 2024" or "summarize the first one" work automatically

---

## 📌 Example Queries

- What is a transformer?
- Compare BERT and GPT architectures
- Find papers on retrieval-augmented generation
- State of research on multimodal learning

---

## 🧠 Author

Akash
