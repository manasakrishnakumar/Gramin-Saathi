# Gramin Saathi - Setup Guide

## Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- Git

## 1. Environment Setup

### Backend (.env)
1. Navigate to `backend/`.
2. Create a file named `.env`.
3. Add the following keys (replace with your actual keys):

```env
# AI & Vector DB
GEMINI_API_KEY=your_gemini_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=gov-documents
PINECONE_REGION=us-east-1

# Optional Integrations
APIFY_TOKEN=your_apify_token
LANGCACHE_API_KEY=your_langcache_key
LANGCACHE_CACHE_ID=your_langcache_id
LANGCACHE_SERVER_URL=https://aws-ap-south-1.langcache.redis.io

# Application Settings
LLM_MODEL=models/gemini-2.5-flash
EMBEDDING_MODEL=models/text-embedding-004
```

### Frontend (.env)
1. Navigate to `frontend/`.
2. Create a file named `.env`.
3. Add:

```env
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
```

> **Note**: The IP Geolocation API key is currently handled internally or falls back to free tiers.

## 2. Installation & Running

### Backend
Open a terminal in the `backend` folder:
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Frontend
Open a new terminal in the `frontend` folder:
```bash
# Install dependencies
npm install

# Run Development Server
npm run dev
```

The app will be available at `http://localhost:5173` (or the port shown in terminal).

## 3. Git Push Instructions

To push this code to a new repository:

1. **Initialize Git** (if not done):
   ```bash
   git init
   ```

2. **Add Files**:
   ```bash
   git add .
   ```

3. **Commit**:
   ```bash
   git commit -m "Initial commit: Gramin Saathi setup"
   ```

4. **Connect to Remote** (Replace URL with your GitHub repo):
   ```bash
   git remote add origin https://github.com/yourusername/gramin-saathi.git
   ```

5. **Push**:
   ```bash
   git push -u origin main
   ```
