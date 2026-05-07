from app.services.supabase_client import get_supabase


def create_review(payload):
    supabase = get_supabase()

    data = {
        "name": payload.name,
        "role": payload.role,
        "rating": payload.rating,
        "comment": payload.comment,
        "user_id": None  # guests supported for now
    }

    res = supabase.table("reviews").insert(data).execute()

    return res.data[0]


def get_all_reviews():
    supabase = get_supabase()

    res = (
        supabase.table("reviews")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return res.data