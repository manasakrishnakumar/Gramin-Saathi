# Gramin Saathi

**An AI-powered, multilingual, voice-enabled assistant that helps Indian citizens discover, understand, and check their eligibility for government welfare schemes.**

Gramin Saathi combines a Hybrid Retrieval-Augmented Generation (RAG) pipeline, a rule-based eligibility engine, and a suite of custom-trained ML models behind a React chat/voice frontend — built to serve India's linguistically diverse and often low-literacy rural population.

> 5th-semester Engineering Clinic (EL) project — prototype / academic build.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Backend Setup](#2-backend-setup)
  - [3. Frontend Setup](#3-frontend-setup)
  - [4. Running the App](#4-running-the-app)
  - [5. (Optional) Training / Re-training the ML Models](#5-optional-training--re-training-the-ml-models)
- [Environment Variables Reference](#environment-variables-reference)
- [API Overview](#api-overview)
- [ML Pipeline](#ml-pipeline)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)

---

## Overview

Gramin Saathi is an intelligent conversational AI platform for Government Schemes (Yojanas). It uses a **Hybrid RAG** architecture that combines:

- **Static document knowledge** — government scheme documents embedded and indexed in Pinecone, retrieved via a hybrid of BM25 (sparse) and dense vector search, then re-ranked with a cross-encoder and fused via Reciprocal Rank Fusion (RRF).
- **Real-time web search fallback** — when retrieval confidence is low, the system falls back to live web search (DuckDuckGo) so it can still answer current-events-style queries.
- **A rule-based eligibility & recommendation engine** — determines whether a citizen actually qualifies for a scheme, rather than leaving that judgment to the LLM.
- **Multilingual + voice support** — responses are generated in both English and the user's local language (Hindi, Kannada, etc.), with speech-to-text/text-to-speech via Sarvam AI for users who cannot read or type comfortably.
- **A layer of custom-trained ML models** (intent classification, retrieval re-ranking, groundedness/hallucination scoring, recommendation ranking, anomaly detection, forecasting, NER, clustering, contextual bandit ranking, voice-quality classification) that sit alongside the core RAG pipeline — see [ML Pipeline](#ml-pipeline) for what's live vs. standalone.

## Key Features

- 💬 **Conversational chat interface** with per-user session history and auto-generated chat titles (via Clerk auth + `localStorage`).
- 🎙️ **Voice interaction** — full-screen voice overlay with real-time waveform visualization, powered by Sarvam STT/TTS.
- 🌐 **Multilingual responses** — auto-detects user location/language and renders answers in English + the local vernacular.
- ✅ **Eligibility checking** — rule-based engine cross-checks a citizen's profile against scheme criteria; a clearly-labeled synthetic ML "approval likelihood" demo sits alongside it, never merged with the real verdict.
- 🔎 **Hybrid RAG retrieval** — BM25 + dense (Pinecone/FAISS) + cross-encoder re-ranking + RRF fusion, with automatic fallback to live web search when retrieval confidence drops below threshold.
- 📊 **Recommendation engine** — reorders eligible schemes using a trained ranking model (`ml_engagement_score`), on top of the rule engine's hard eligibility gate.
- 🤖 **12 custom-trained ML models** for intent classification, groundedness scoring, anomaly detection, forecasting, NER, clustering, bandit-based ranking, and voice-quality assessment — see [`backend/ml/README.md`](backend/ml/README.md) for full details and metrics.
- 🕸️ **Automated scraping pipeline** — ingests government scheme websites (HTML/PDF) into the knowledge base on a schedule (via APScheduler / Trigger.dev).
- 📈 **Monitoring** — tracks query latency, token usage, and error rates.

## Tech Stack

### Frontend
- **Core**: React 18, TypeScript, Vite
- **Styling**: Tailwind CSS, Shadcn/UI
- **Animations**: Framer Motion
- **Auth**: Clerk
- **State**: React Hooks + `localStorage`

### Backend
- **Framework**: FastAPI (Python), Uvicorn (ASGI)
- **LLM Orchestration**: LlamaIndex
- **LLM / Embeddings**: Google Gemini (`gemini-2.5-flash`, `text-embedding-004`)
- **Vector Database**: Pinecone
- **Hybrid Retrieval**: `rank-bm25`, `faiss-cpu`, `sentence-transformers`
- **Voice**: Sarvam AI (STT / TTS / Translate)
- **Web Search Fallback**: DuckDuckGo (`ddgs`)
- **Caching**: LangCache (Redis-backed)
- **ML**: scikit-learn, sentence-transformers, torch (CPU), sklearn-crfsuite
- **Scheduling**: APScheduler, Trigger.dev

## Project Structure

```
boston/
├── backend/                   # FastAPI backend (the "cognitive engine")
│   ├── app/
│   │   ├── api/v1/             # Route definitions (rag, voice, eligibility, ml_*, etc.)
│   │   ├── core/                # Settings, scheduler
│   │   ├── models/              # Trained ML model artifacts (.joblib, .pkl, manifests)
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Business logic (rag_service, eligibility_service, ml_*_service, ...)
│   │   └── main.py              # FastAPI app entrypoint
│   ├── ml/                      # ML training scripts, datasets, docs (see backend/ml/README.md)
│   ├── sarvam_services/         # Sarvam STT / TTS / translation integration
│   ├── data/                    # Scraped/ingested scheme documents
│   └── requirements.txt
├── frontend/                   # React + Vite SPA (chat UI, voice overlay, recommendations)
│   ├── src/
│   └── package.json
├── chat/                        # Additional Next.js-style chat module
├── trigger/                     # Trigger.dev background jobs (e.g. daily_scrape.ts)
├── SYSTEM_ARCHITECTURE.md       # Detailed architecture & data-flow doc
├── SETUP.md                     # Original quick-start setup notes
└── README.md                    # You are here
```

## Prerequisites

Make sure you have the following installed before you begin:

| Tool | Version | Notes |
|---|---|---|
| [Node.js](https://nodejs.org/) | v18+ | For the frontend (and `trigger/` jobs) |
| [Python](https://www.python.org/) | v3.10+ | For the backend |
| [Git](https://git-scm.com/) | any recent | To clone the repo |

You will also need API keys for the services below (see [Environment Variables Reference](#environment-variables-reference)):

- **Google Gemini API key** (LLM + embeddings) — required
- **Pinecone API key** (vector database) — required
- **Clerk publishable key** (frontend auth) — required
- **Sarvam AI API key** (voice STT/TTS/translate) — required for voice features
- Apify token, LangCache credentials — optional integrations

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd boston
```

### 2. Backend Setup

Navigate to the backend folder:

```bash
cd backend
```

**a) Create and activate a virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**b) Install dependencies**

```bash
pip install -r requirements.txt
```

> Note: `requirements.txt` installs a CPU-only build of PyTorch (`torch==2.4.1+cpu`) to avoid CUDA DLL issues on Windows. This is intentional — the Hybrid RAG / ML components run inference-only and don't need a GPU.

**c) Create your `.env` file**

Create a file named `.env` inside `backend/` with the following keys:

```env
# --- AI & Vector DB (required) ---
GEMINI_API_KEY=your_gemini_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=gov-documents
PINECONE_REGION=us-east-1

# --- Voice (required for /voice endpoints) ---
SARVAM_API_KEY=your_sarvam_key

# --- Optional integrations ---
APIFY_TOKEN=your_apify_token
LANGCACHE_API_KEY=your_langcache_key
LANGCACHE_CACHE_ID=your_langcache_id
LANGCACHE_SERVER_URL=https://aws-ap-south-1.langcache.redis.io
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# --- Application settings (defaults shown) ---
LLM_MODEL=models/gemini-2.5-flash
EMBEDDING_MODEL=models/text-embedding-004
SCRAPE_SCHEDULE=0 2 * * *
GOV_SITES=https://scholarships.gov.in/All-Scholarships
MAX_LOCAL_CACHE=50
CACHE_TTL=86400
```

**d) Run the backend server**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

The API will be available at `http://localhost:8001` (interactive docs at `http://localhost:8001/docs`).

### 3. Frontend Setup

Open a **new terminal** in the `frontend/` folder:

```bash
cd frontend
```

**a) Create your `.env` file**

```env
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
```

**b) Install dependencies**

```bash
npm install
```

**c) Run the development server**

```bash
npm run dev
```

The app will be available at `http://localhost:5173` (or the port shown in your terminal). Vite is pre-configured to proxy `/api` requests to `http://127.0.0.1:8001`, so make sure the backend is running first.

### 4. Running the App

With both servers running:

1. Backend → `http://localhost:8001`
2. Frontend → `http://localhost:5173`

Open the frontend URL in your browser, sign in via Clerk, and start chatting. Try asking about a scheme (e.g. "What is PM Kisan?") or open the voice overlay to speak your query.

### 5. (Optional) Training / Re-training the ML Models

All 12 ML models already ship as trained artifacts under `backend/app/models/`, so you don't need to retrain anything to run the app. If you want to reproduce or re-run the training pipeline:

```bash
cd backend
venv\Scripts\python.exe -m pip install sklearn-crfsuite   # the one genuinely new ML dependency

# Intent classifier + retrieval fine-tunes
venv\Scripts\python.exe ml\data\generate_intent_dataset.py
venv\Scripts\python.exe ml\train_intent_classifier.py
venv\Scripts\python.exe ml\data\generate_retrieval_dataset.py
venv\Scripts\python.exe ml\finetune_reranker.py
venv\Scripts\python.exe ml\finetune_multilingual.py

# Recommendation ranker
venv\Scripts\python.exe ml\data\generate_ranker_bootstrap.py
venv\Scripts\python.exe ml\train_ranker_bootstrap.py

# Outcome / approval-likelihood (SYNTHETIC DEMO)
venv\Scripts\python.exe ml\data\generate_outcome_bootstrap.py
venv\Scripts\python.exe ml\train_outcome_model_DEMO.py

# Query volume forecasting
venv\Scripts\python.exe ml\data\generate_query_volume_bootstrap.py
venv\Scripts\python.exe ml\train_query_forecast.py

# Profile anomaly detection
venv\Scripts\python.exe ml\data\generate_profile_distribution.py
venv\Scripts\python.exe ml\train_anomaly_detector.py

# Answer groundedness / hallucination scorer
venv\Scripts\python.exe ml\data\generate_groundedness_dataset.py
venv\Scripts\python.exe ml\train_groundedness_classifier.py

# Scheme-data NER
venv\Scripts\python.exe ml\data\generate_ner_dataset.py
venv\Scripts\python.exe ml\train_ner_model.py

# User segmentation
venv\Scripts\python.exe ml\train_profile_clusters.py

# Contextual bandit ranker (simulation)
venv\Scripts\python.exe ml\simulate_bandit.py

# Voice transcription quality classifier
venv\Scripts\python.exe ml\data\generate_transcript_quality_dataset.py
venv\Scripts\python.exe ml\train_transcript_quality_classifier.py
```

All scripts are deterministic (seeded) except the two neural fine-tunes, which vary slightly run to run. Full details, metrics, and honesty notes on synthetic vs. real data are in [`backend/ml/README.md`](backend/ml/README.md).

## Environment Variables Reference

### `backend/.env`

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | — | Google Gemini API key (LLM + embeddings) |
| `PINECONE_API_KEY` | ✅ | — | Pinecone vector database API key |
| `PINECONE_INDEX_NAME` | | `gov-documents` | Pinecone index name |
| `PINECONE_REGION` | | `us-east-1` | Pinecone region |
| `SARVAM_API_KEY` | ✅ (for voice) | — | Sarvam AI key for STT/TTS/translation |
| `LLM_MODEL` | | `models/gemini-2.5-flash` | Gemini model used for generation |
| `EMBEDDING_MODEL` | | `models/text-embedding-004` | Gemini embedding model |
| `APIFY_TOKEN` | optional | — | For Apify-based scraping integrations |
| `LANGCACHE_API_KEY` / `LANGCACHE_CACHE_ID` / `LANGCACHE_SERVER_URL` | optional | — | Redis-backed semantic caching via LangCache |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` | optional | `localhost` / `6379` / — | Redis connection (if used directly) |
| `SCRAPE_SCHEDULE` | | `0 2 * * *` | Cron schedule for the daily scraper |
| `GOV_SITES` | | `https://scholarships.gov.in/All-Scholarships` | Seed URL(s) for the scraper |
| `MAX_LOCAL_CACHE` | | `50` | In-memory cache size |
| `CACHE_TTL` | | `86400` | Cache TTL in seconds |

### `frontend/.env`

| Variable | Required | Description |
|---|---|---|
| `VITE_CLERK_PUBLISHABLE_KEY` | ✅ | Clerk publishable key for auth |

> IP geolocation currently falls back to a free tier internally — no key required.

## API Overview

All backend routes are mounted under `/api/v1`. Interactive Swagger docs are available at `http://localhost:8001/docs` once the server is running.

| Prefix | Purpose |
|---|---|
| `/api/v1/rag` | Core chat / RAG streaming endpoint |
| `/api/v1/voice` | Voice conversation (STT → RAG → TTS) |
| `/api/v1/monitor` | Latency / usage / error monitoring |
| `/api/v1/scraper` | Trigger/manage scheme-document scraping |
| `/api/v1/recommend` | Scheme recommendation (rule engine + ML ranker) |
| `/api/v1/eligibility` | Rule-based eligibility checking |
| `/api/v1/intent` | Intent classification |
| `/api/v1/ml/*` | ML endpoints — feedback logging, ranking, outcomes, anomaly, clusters, forecast, NER, groundedness, voice quality (see `backend/ml/README.md`) |

## ML Pipeline

Gramin Saathi includes 12 custom-trained ML models. Some are fully wired into the live chat/recommendation/voice flow; others are trained and verified but kept standalone (not yet fed live traffic). Full status table, metrics, honesty notes on synthetic vs. real data, and re-run instructions live in:

📄 **[`backend/ml/README.md`](backend/ml/README.md)**

Highlights:
- **Wired into the live app**: intent classifier (95.3% acc), answer groundedness scorer, recommendation ranker (ROC-AUC 0.719), voice-quality classifier.
- **Trained, standalone**: RAG reranker fine-tune, multilingual embedder fine-tune, outcome/approval-likelihood predictor (clearly labeled `SYNTHETIC_DEMO`, never merged with real eligibility results), query-volume forecasting, profile anomaly detection, scheme-data NER, user segmentation, contextual bandit ranker.

## Documentation

- [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md) — detailed frontend/backend architecture and query lifecycle
- [`SETUP.md`](SETUP.md) — original quick-start setup notes
- [`backend/ml/README.md`](backend/ml/README.md) — full ML pipeline documentation
- [`backend/ml/PHASE3_NOTES.md`](backend/ml/PHASE3_NOTES.md) — design notes on the synthetic outcome-prediction model

## Troubleshooting

- **`ImportError` / missing package on backend start** — make sure the virtual environment is activated and `pip install -r requirements.txt` completed without errors.
- **CORS / 404 on `/api/...` from the frontend** — confirm the backend is running on port `8001` before starting the frontend (Vite proxies `/api` to `127.0.0.1:8001`).
- **`PINECONE_API_KEY` / `GEMINI_API_KEY` errors on startup** — these are required; the app will fail to start without valid values in `backend/.env`.
- **Voice endpoints failing** — check that `SARVAM_API_KEY` is set; voice quality scoring only supports English transcripts currently.
- **Torch install issues on Windows** — `requirements.txt` already pins the CPU-only wheel via `--extra-index-url https://download.pytorch.org/whl/cpu`; if you hit CUDA-related errors, ensure you didn't override this in a global `pip.conf`.
