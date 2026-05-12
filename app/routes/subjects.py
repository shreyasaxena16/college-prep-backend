from fastapi import APIRouter,HTTPException
from app.services.supabase_client import get_supabase
supabase = get_supabase()

router = APIRouter()

@router.post("/")
def create_subject(data: dict):

    if "subject_name" not in data:
        raise HTTPException(status_code=400, detail="subject_name required")

    clean_data = {
        "subject_name": data["subject_name"].strip(),
        "level": data.get("level", "on_level"),
        "year": data.get("year", 9),
        "student_id": data.get("student_id"),
    }

    response = supabase.table("subjects").insert(clean_data).execute()

    if response.data is None:
        raise HTTPException(status_code=500, detail="Insert failed")

    return response.data


@router.get("/")
def get_subjects():
    response = supabase.table("subjects").select("*").execute()
    return response.data

@router.get("/{student_id}")
def get_subjects(student_id: str):
    return supabase.table("subjects") \
        .select("*") \
        .eq("student_id", student_id) \
        .execute().data