from app.rag.retriever import retrieve_chunks
from app.rag.prompt_builder import build_prompt
from app.rag.ollama_client import chat


def ask_tutor(question: str):
    chunks = retrieve_chunks(question)
    prompt = build_prompt(question, chunks)
    return chat(prompt)