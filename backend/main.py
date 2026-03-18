from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import analyze, assets, auto_fix, export, font, generate, jobs, preview, progress, upload

app = FastAPI(title="Migrador Planet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(preview.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(auto_fix.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(font.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
