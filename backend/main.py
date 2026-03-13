from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import jobs, preview, progress, upload

app = FastAPI(title="Migrador Planet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(preview.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
