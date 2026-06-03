from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ai_service import get_embedding, generate_rag_answer
from app.services.vector_db import query_context

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    context_used: bool

@router.post("/", response_model=ChatResponse)
def ask_question(request: ChatRequest):
    """
    RAG Endpoint: 
    1. Embeds user question.
    2. Searches Vector DB for relevant context.
    3. Generates LLM response.
    """
    try:
        # Step 1: Embed question
        question_embedding = get_embedding(request.question)
        
        # Step 2: Retrieve Context
        context = query_context(question_embedding, top_k=3)
        has_context = len(context.strip()) > 0
        
        # Step 3: Ask LLM
        if not has_context:
            # Fallback if no news matches the database
            context = "No relevant daily news found in the database for this topic."
            
        answer = generate_rag_answer(request.question, context)
        
        return ChatResponse(answer=answer, context_used=has_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
