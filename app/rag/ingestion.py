import hashlib
import os
import re
from html import unescape
from typing import Any
from urllib.parse import urlparse

import requests

from app.config import get_gemini_client
from app.rag.ollama_client import EMBEDDING_MODEL, get_embedding
from app.services.supabase_client import get_supabase


TEXT_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
}


def _clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _none_if_blank(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    try:
        from io import BytesIO

        reader = PdfReader(BytesIO(data))
        return _clean_text("\n\n".join(page.extract_text() or "" for page in reader.pages))
    except Exception:
        return ""


def _extract_docx_text(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        return ""

    try:
        from io import BytesIO

        document = Document(BytesIO(data))
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        return _clean_text("\n\n".join(paragraphs))
    except Exception:
        return ""


def _extract_html_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "noscript"]):
            element.decompose()
        return _clean_text(soup.get_text("\n"))
    except ImportError:
        html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
        html = re.sub(r"(?s)<[^>]+>", " ", html)
        return _clean_text(html)


def _ocr_with_gemini(data: bytes, mime_type: str, file_name: str) -> str:
    try:
        from google.genai import types
    except ImportError:
        return ""

    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model=os.getenv("GEMINI_OCR_MODEL", "models/gemini-2.5-flash"),
            contents=[
                "Extract all readable study material from this file. Preserve headings, math expressions, answer choices, and handwritten notes as plain text. Do not summarize.",
                types.Part.from_bytes(data=data, mime_type=mime_type or "application/octet-stream"),
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="text/plain",
            ),
        )
        return _clean_text(response.text or "")
    except Exception as exc:
        print(f"OCR failed for {file_name}: {exc}", flush=True)
        return ""


def extract_text_from_file(data: bytes, file_name: str, mime_type: str | None) -> tuple[str, str]:
    mime_type = mime_type or "application/octet-stream"
    lower_name = file_name.lower()

    if mime_type in TEXT_MIME_TYPES or lower_name.endswith((".txt", ".md", ".csv", ".json")):
        return _clean_text(data.decode("utf-8", errors="ignore")), "text"

    if mime_type == "application/pdf" or lower_name.endswith(".pdf"):
        text = _extract_pdf_text(data)
        if text:
            return text, "pdf_text"
        return _ocr_with_gemini(data, "application/pdf", file_name), "gemini_pdf_ocr"

    if (
        mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or lower_name.endswith(".docx")
    ):
        return _extract_docx_text(data), "docx"

    if mime_type.startswith("image/") or lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return _ocr_with_gemini(data, mime_type, file_name), "gemini_image_ocr"

    return _clean_text(data.decode("utf-8", errors="ignore")), "binary_text_fallback"


def extract_text_from_url(url: str) -> tuple[str, dict[str, Any]]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported")

    response = requests.get(
        url,
        headers={"User-Agent": "CollegePrepRAG/1.0"},
        timeout=20,
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type == "application/pdf" or parsed.path.lower().endswith(".pdf"):
        text, extractor = extract_text_from_file(response.content, parsed.path.rsplit("/", 1)[-1] or "website.pdf", content_type)
    else:
        text = _extract_html_text(response.text)
        extractor = "website_html"

    return text, {
        "content_type": content_type,
        "extractor": extractor,
    }


def chunk_text(text: str, max_chars: int = 1400, overlap: int = 180) -> list[str]:
    text = _clean_text(text)
    if not text:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            start = 0
            while start < len(paragraph):
                chunks.append(paragraph[start:start + max_chars].strip())
                start += max_chars - overlap
            continue

        next_text = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(next_text) <= max_chars:
            current = next_text
        else:
            chunks.append(current.strip())
            current = paragraph

    if current:
        chunks.append(current.strip())

    return chunks


def _upload_original_file(supabase: Any, data: bytes, file_name: str) -> tuple[str | None, str | None]:
    bucket = os.getenv("RAG_STORAGE_BUCKET")
    if not bucket:
        return None, None

    digest = hashlib.sha256(data).hexdigest()[:16]
    storage_path = f"rag/{digest}/{file_name}"
    try:
        supabase.storage.from_(bucket).upload(
            storage_path,
            data,
            {"content-type": "application/octet-stream", "upsert": "true"},
        )
        return bucket, storage_path
    except Exception as exc:
        print(f"Original file storage skipped: {exc}", flush=True)
        return None, None


def ingest_text(
    *,
    title: str,
    text: str,
    source_type: str,
    uploaded_by: str | None = None,
    file_name: str | None = None,
    file_mime_type: str | None = None,
    url: str | None = None,
    subject: str | None = None,
    topic: str | None = None,
    sat_band: str | None = None,
    metadata: dict[str, Any] | None = None,
    storage_bucket: str | None = None,
    storage_path: str | None = None,
) -> dict[str, Any]:
    uploaded_by = _none_if_blank(uploaded_by)
    subject = _none_if_blank(subject)
    topic = _none_if_blank(topic)
    sat_band = _none_if_blank(sat_band)
    title = _none_if_blank(title) or "Untitled source"

    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No extractable text found. For scans/images, configure GEMINI_API_KEY for OCR.")

    supabase = get_supabase()
    source_payload = {
        "uploaded_by": uploaded_by,
        "title": title,
        "source_type": source_type,
        "file_name": file_name,
        "file_mime_type": file_mime_type,
        "storage_bucket": storage_bucket,
        "storage_path": storage_path,
        "url": url,
        "subject": subject or None,
        "topic": topic or None,
        "sat_band": sat_band or None,
        "metadata": metadata or {},
    }
    source_payload = {key: value for key, value in source_payload.items() if value is not None}

    source = supabase.table("sat_knowledge_sources").insert(source_payload).execute().data[0]
    source_id = source["id"]

    rows = []
    for index, chunk in enumerate(chunks):
        rows.append({
            "source_id": source_id,
            "chunk_index": index,
            "content": chunk,
            "subject": subject or None,
            "topic": topic or None,
            "sat_band": sat_band or None,
            "token_count": len(chunk.split()),
            "metadata": {"title": title},
            "embedding": get_embedding(chunk),
            "embedding_model": EMBEDDING_MODEL,
        })

    supabase.table("sat_knowledge_chunks").insert(rows).execute()

    return {
        "source_id": source_id,
        "title": title,
        "chunk_count": len(rows),
        "embedding_model": EMBEDDING_MODEL,
    }


def ingest_file(
    *,
    data: bytes,
    file_name: str,
    mime_type: str | None,
    uploaded_by: str | None = None,
    title: str | None = None,
    subject: str | None = None,
    topic: str | None = None,
    sat_band: str | None = None,
) -> dict[str, Any]:
    supabase = get_supabase()
    storage_bucket, storage_path = _upload_original_file(supabase, data, file_name)
    text, extractor = extract_text_from_file(data, file_name, mime_type)

    return ingest_text(
        title=title or file_name,
        text=text,
        source_type="upload",
        uploaded_by=uploaded_by,
        file_name=file_name,
        file_mime_type=mime_type,
        subject=subject,
        topic=topic,
        sat_band=sat_band,
        metadata={"extractor": extractor},
        storage_bucket=storage_bucket,
        storage_path=storage_path,
    )


def ingest_url(
    *,
    url: str,
    uploaded_by: str | None = None,
    title: str | None = None,
    subject: str | None = None,
    topic: str | None = None,
    sat_band: str | None = None,
) -> dict[str, Any]:
    text, metadata = extract_text_from_url(url)
    return ingest_text(
        title=title or url,
        text=text,
        source_type="url",
        uploaded_by=uploaded_by,
        url=url,
        subject=subject,
        topic=topic,
        sat_band=sat_band,
        metadata=metadata,
    )
