"""
Ignisia26 — Enterprise RAG Pipeline API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, documents, chat, emails

app = FastAPI(
    title="Ignisia26 API",
    description="Enterprise RAG Pipeline with RBAC & Conflict Detection",
    version="1.0.0",
)

# CORS — allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React / Vite defaults
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(emails.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "ignisia26"}
