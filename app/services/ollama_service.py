import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from app.rag.tutor_service import retrieve_chunks

import requests


OLLAMA_SYSTEM_PROMPT = """
You are Bun Bun, a quick, kind, funny college-prep bunny assistant.
Help students with short local questions, SAT/test-prep mistakes, study plans,
college application workflow, motivation, and clean jokes.

Rules:
- Keep most answers under 120 words unless the student asks for detail.
- For wrong test questions, explain the idea, why the correct answer works,
  and give one tiny practice tip.
- Be playful, but never distracting during serious academic help.
- Do not claim to know private student data unless it was included in the prompt.
- If auth_status is guest, give general site guidance and preparation advice.
- If auth_status is student, use the provided GPA, test history, weak areas,
  and current page/question context to personalize the answer.
- If asked to generate full SAT tests or large question banks, say the test
  generator handles that separately.
"""


@lru_cache(maxsize=1)
def get_site_context() -> str:
    context_path = Path(__file__).with_name("bunny_context.md")
    try:
        return context_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def get_ollama_config() -> tuple[str, str, str]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    api_style = os.getenv("OLLAMA_API_STYLE", "native").lower()
    return base_url, model, api_style


def ask_ollama(prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    print("🔥 ask_ollama CALLED")
    base_url, model, api_style = get_ollama_config()
    context_text = ""
    site_context = get_site_context()

    rag_context_text = ""

    try:
        chunks = retrieve_chunks(
            prompt,
            subject=context.get("subject") if context else None,
            topic=context.get("topic") if context else None,
        )

        if chunks:
            rag_context_text = "\n\nSAT Knowledge Context:\n" + "\n\n".join(
                [c.get("chunk_text") or c.get("content") or "" for c in chunks]
            )
            print("RAG CHUNKS USED:", len(chunks))
            print([c.get("topic") for c in chunks])

    except Exception as e:
        rag_context_text = ""

    if context:
        context_lines = [
            f"{key}: {value}"
            for key, value in context.items()
            if value not in (None, "", [])
        ]
        if context_lines:
            context_text = "Student context:\n" + "\n".join(context_lines) + "\n\n"

    full_prompt = (
        f"{OLLAMA_SYSTEM_PROMPT}\n\n"
        f"Website context:\n{site_context}\n\n"
        f"{context_text}"
        f"{rag_context_text}\n\n"
        f"Student: {prompt}\nBun Bun:"
    )

    if api_style == "wrapper":
        response = requests.post(
            f"{base_url}/ask",
            json={"prompt": full_prompt},
            timeout=25,
        )
    else:
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.75,
                    "num_predict": 220,
                },
            },
            timeout=25,
        )

    response.raise_for_status()
    data = response.json()

    return {
        "model": model,
        "response": (data.get("response") or "").strip(),
        "done": data.get("done", True),
    }
