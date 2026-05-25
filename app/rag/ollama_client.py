import requests

OLLAMA_URL = "http://localhost:11434"


def get_embedding(text: str):
    res = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text
        }
    )
    return res.json()["embedding"]


def chat(prompt: str):
    res = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": "llama3",
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
        }
    )
    return res.json()["message"]["content"]