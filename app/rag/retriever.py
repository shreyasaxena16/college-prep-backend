from app.services.supabase_client import get_supabase
from app.rag.ollama_client import get_embedding


def retrieve_chunks(query: str, top_k: int = 5):
    supabase = get_supabase()

    embedding = get_embedding(query)

    res = supabase.rpc(
        "match_chunks",
        {
            "query_embedding": embedding,
            "match_count": top_k
        }
    ).execute()

    return res.data