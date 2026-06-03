from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import os
from openai import OpenAI

router = APIRouter(prefix="/api/media", tags=["Media"])
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class TTSRequest(BaseModel):
    text: str

@router.get("/pdf")
def download_pdf():
    """
    Returns the latest compiled daily notes PDF.
    """
    pdf_path = os.path.join("app", "static", "latest_notes.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf", filename="SSC_Daily_Notes.pdf")
    raise HTTPException(status_code=404, detail="PDF not generated yet. Trigger ingestion pipeline first.")

@router.post("/tts")
def generate_tts(request: TTSRequest):
    """
    Uses OpenAI TTS API to generate audio.
    Normally we'd save this or stream it. We will return the raw audio bytes.
    """
    try:
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=request.text
        )
        return Response(content=response.read(), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
