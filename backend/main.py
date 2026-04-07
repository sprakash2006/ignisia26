
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, documents, chat, emails, tickets

app = FastAPI(
    title="Ignisia26 API",
    description="Enterprise RAG Pipeline with RBAC & Conflict Detection",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(emails.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "ignisia26"}
