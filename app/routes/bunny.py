from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from requests import RequestException

from app.services.ollama_service import ask_ollama


router = APIRouter(tags=["Bunny"])


class BunnyChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: dict[str, Any] | None = None


@router.post("/chat")
def chat_with_bunny(payload: BunnyChatRequest):
    print("🔥 CONTEXT RECEIVED:", payload.context, flush=True)
    try:
        return ask_ollama(payload.message, payload.context)
    except RequestException as exc:
        raise HTTPException(
            status_code=503,
            detail="Bun Bun cannot reach Ollama right now. Check OLLAMA_BASE_URL and that the model is running.",
        ) from exc
