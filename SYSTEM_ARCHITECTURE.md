# Gramin Saathi - System Architecture & Design

## 1. High-Level Overview
Gramin Saathi is an intelligent conversational AI platform designed to assist users with Government Schemes (Yojanas). It employs a **Hybrid RAG (Retrieval-Augmented Generation)** architecture that combines static document knowledge (Pinecone) with real-time information (Web Search), wrapped in a user-friendly React frontend.

## 2. Frontend Architecture
The frontend is a **Single Page Application (SPA)** built for performance and interactivity.

### Tech Stack
- **Core**: React 18, TypeScript, Vite (Build Tool).
- **Styling**: Tailwind CSS, Shadcn/UI (Components).
- **Animations**: Framer Motion (Voice Overlay, Particles, Transitions).
- **Auth**: Clerk (Identity Management).
- **State**: React Hooks (`useState`, `useEffect`) + `localStorage` for session persistence.

### Key Modules
1.  **Chat Interface (`ChatPage.tsx`)**:
    - **Session Management**: Isolates chat history per user (`clerk_user_id`). Automatically generates chat titles based on the first query.
    - **Step Visualization**: Renders backend "Thinking Steps" (e.g., "Checking Cache", "Searching Web") in real-time.
    - **Dual-Language Support**: Detects user location/language and renders responses in both English and the local vernacular (e.g., Kannada, Hindi).
2.  **Voice Interaction (`VoiceChat.tsx`)**:
    - **Overlay UI**: Immersive full-screen modal with ambient particle effects.
    - **Visualizers**: Real-time audio waveform simulation to indicate "Listening" vs "Speaking" states.
3.  **Smart Input (`ai-input-with-loading.tsx`)**:
    - Custom auto-resizing textarea with "Sparkle" loading states, replacing standard HTML inputs.
4.  **Geolocation Service (`geolocation.ts`)**:
    - Hybrid detection: Tries GPS (`navigator.geolocation`) first, performs Reverse Geocoding, and falls back to IP-based detection if permission is denied.

## 3. Backend Architecture
The backend is a high-performance **FastAPI** service acting as the cognitive engine.

### Tech Stack
- **Framework**: FastAPI (Python), Uvicorn (ASGI Server).
- **LLM Orchestration**: LlamaIndex.
- **Model**: Google Gemini Pro (Embedding & Generation).
- **Vector Database**: Pinecone (Knowledge Base).
- **Search**: DuckDuckGo (Real-time fallback).
- **Caching**: Local memory / SQLite (via `langcache`).

### Core Services
1.  **RAG Service (`rag_service.py`)**: The brain of the system. Implements **Intelligent Query Routing**:
    *   **Path A: Conversational**: Detects greetings ("Hi", "Who are you"). -> Returns instant persona-based response.
    *   **Path B: Cache**: Checks if query was asked recently. -> Returns cached response.
    *   **Path C: Retrieval**: Queries Pinecone for relevant documents.
    *   **Path D: Web Search**: If RAG score < **0.68**, falls back to DuckDuckGo to answer current events (e.g., "IPL 2025").
    *   **Generation**: Synthesizes final answer using **Buffered Streaming** (accumulates full text, then streams to UI for stability).
2.  **Monitoring Service (`monitoring_service.py`)**:
    - Tracks query latency, token usage, and error rates.
3.  **Scraper Service (`scraper_service.py`)**:
    - Ingests government websites (HTML/PDF) into valid text chunks for embedding.

## 4. The Query Lifecycle (Data Flow)
1.  **User Input**: User types/speaks "What is PM Kisan?".
2.  **Context Injection**: Frontend appends `detected_language` (e.g., "Hindi") and `history`.
3.  **API Call**: Query sent to `POST /api/v1/rag/stream`.
4.  **Routing Decision**: Backend analyzes query. It's not a greeting, so it goes to **RAG**.
5.  **Retrieval**: System fetches top 3 matching nodes from Pinecone.
6.  **Scoring**:
    - If Score > 0.68: Use Documents. Context = "PM Kisan guidelines...".
    - If Score < 0.68: Use Web. Context = "Latest news on PM Kisan...".
7.  **Synthesis**: LLM accepts Context + System Prompt ("You are Gramin Saathi"). Generates English + Hindi response.
8.  **Streaming**: Response chunks sent to Frontend.
9.  **Rendering**: Frontend displays Markdown response + specific "Process Steps" used.

## 5. Security & Infrastructure
- **Proxy**: Vite config proxies `/api` to `127.0.0.1:8001` to bridge Frontend/Backend CORS/Port issues.
- **Environment**: Keys (`GEMINI_API_KEY`, `PINECONE_KEY`, `CLERK_KEY`) stored in `.env`.
- **Identity**: Usage of Clerk ensures users cannot see each others' chat sessions.
