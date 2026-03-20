from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
# Carrega o .env da raiz do projeto, depois aplica backend/.env (override=False = não sobrescreve)
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent / ".env", override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import analyze, assets, auto_fix, export, font, generate, preview, upload
from services.stages.register_all import register_all

register_all()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event — runs cleanup on startup, nothing on shutdown."""
    # Remove orphaned job directories from previous server runs (Story 11.9)
    analyze._cleanup_orphaned_dirs()
    yield


app = FastAPI(title="Migrador Planet API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(preview.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(auto_fix.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(font.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
