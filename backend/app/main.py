import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler

app = FastAPI(title="GovRAG API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix="/api/v1")

# Events
@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()

# Serve frontend from frontend/dist/ so both UI and Backend run on port 8001
_DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))

if os.path.isdir(_DIST_DIR):
    assets_dir = os.path.join(_DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # If the requested file directly exists in dist (e.g. favicon.ico, registerSW.js)
        target_file = os.path.join(_DIST_DIR, full_path)
        if full_path and os.path.isfile(target_file):
            return FileResponse(target_file)
        # Otherwise return index.html for React Router with no-cache headers
        index_file = os.path.join(_DIST_DIR, "index.html")
        return FileResponse(
            index_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
else:
    @app.get("/")
    async def root():
        return {"message": "GovRAG API is running"}
