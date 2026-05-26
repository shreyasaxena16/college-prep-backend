from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl
from requests import RequestException

from app.rag.ingestion import ingest_file, ingest_url
from app.rag.retriever import retrieve_chunks
from app.services.supabase_client import get_supabase


router = APIRouter(tags=["RAG"])


class WebsiteIngestRequest(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    uploaded_by: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    sat_band: Optional[str] = None


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    uploaded_by: str | None = Form(None),
    title: str | None = Form(None),
    subject: str | None = Form(None),
    topic: str | None = Form(None),
    sat_band: str | None = Form(None),
):
    try:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        return ingest_file(
            data=data,
            file_name=file.filename or "upload",
            mime_type=file.content_type,
            uploaded_by=uploaded_by,
            title=title,
            subject=subject,
            topic=topic,
            sat_band=sat_band,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Embedding/OCR service failed: {exc}") from exc


@router.post("/website")
def ingest_website(payload: WebsiteIngestRequest):
    try:
        return ingest_url(
            url=str(payload.url),
            uploaded_by=payload.uploaded_by,
            title=payload.title,
            subject=payload.subject,
            topic=payload.topic,
            sat_band=payload.sat_band,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Website or embedding service failed: {exc}") from exc


@router.get("/sources")
def list_sources():
    supabase = get_supabase()
    sources = supabase.table("sat_knowledge_sources") \
        .select("*") \
        .order("created_at", desc=True) \
        .limit(50) \
        .execute().data or []

    return sources


@router.get("/search")
def search_knowledge(
    q: str,
    top_k: int = 5,
    subject: str | None = None,
    topic: str | None = None,
):
    try:
        return retrieve_chunks(q, top_k=top_k, subject=subject, topic=topic)
    except RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Embedding service failed: {exc}") from exc
