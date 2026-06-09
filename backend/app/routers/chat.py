from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.advanced_rag import run_advanced_rag

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    question: str
    user_id: str = "student_default"

class ChatResponse(BaseModel):
    answer: str
    context_used: bool
    intent: str
    security_flags: list[str]

@router.post("/", response_model=ChatResponse)
def ask_question(request: ChatRequest):
    """
    Advanced RAG Endpoint:
    Dispatches query to the LangGraph State Machine.
    """
    try:
        output = run_advanced_rag(request.question, request.user_id)
        context_used = output["intent"] in ["rag", "hybrid"]
        return ChatResponse(
            answer=output["answer"],
            context_used=context_used,
            intent=output["intent"],
            security_flags=output["security_flags"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

