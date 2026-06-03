from dotenv import load_dotenv
# Load environment variables from .env BEFORE loading custom modules!
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.services.vector_db import init_pinecone
from app.routers import ingest, chat, media

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Application Startup: Initializing Vector DB...")
    init_pinecone()
    yield
    # Shutdown logic
    print("Application Shutdown...")

app = FastAPI(
    title="Current Affairs AI API",
    description="API for fetching summaries, answering questions via RAG, and generating media.",
    lifespan=lifespan
)

# Allow CORS for Next.js app communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # NOTE: Update with Vercel URL in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(media.router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Backend is running!"}
