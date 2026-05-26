from app.services.supabase_client import get_supabase
from app.rag.ollama_client import get_embedding


def retrieve_chunks(
    query: str,
    top_k: int = 5,
    subject: str | None = None,
    topic: str | None = None,
):
    supabase = get_supabase()

    embedding = get_embedding(query)

    res = supabase.rpc(
        "match_sat_knowledge",
        {
            "query_embedding": embedding,
            "match_count": top_k,
            "filter_subject": subject,
            "filter_topic": topic,
        }
    ).execute()

    chunks = res.data or []
    for chunk in chunks:
        chunk["chunk_text"] = chunk.get("content") or chunk.get("chunk_text") or ""
    return chunks
