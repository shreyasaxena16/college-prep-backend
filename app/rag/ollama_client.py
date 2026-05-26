import os

import requests

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


def get_embedding(text: str):
    res = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={
            "model": EMBEDDING_MODEL,
            "prompt": text
        },
        timeout=30,
    )
    res.raise_for_status()
    return res.json()["embedding"]


def chat(prompt: str):
    res = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": CHAT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert SAT tutor. Explain concepts step by step."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False
        },
        timeout=60,
    )
    res.raise_for_status()
    return res.json()["message"]["content"]
