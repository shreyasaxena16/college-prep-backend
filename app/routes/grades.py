from fastapi import APIRouter
from app.services.supabase_client import get_supabase
supabase = get_supabase()

router = APIRouter()

@router.post("/")
def add_grade(payload: dict):
    clean = {
        "student_id": payload["student_id"],
        "subject_id": payload.get("subject_id"),
        "grade": payload["grade"],
        "credits": payload["credits"],
        "course_type": payload["course_type"],
        "year": payload["year"],
        "quarter": payload["quarter"],
    }   
    print("PAYLOAD:", payload)
    print("CLEAN:", clean)
    response = supabase.table("grades").insert(clean).execute()
    return response.data


@router.get("/")
def get_grades():
    response = supabase.table("grades").select("*").execute()
    return response.data

@router.get("/{student_id}")
def get_grades(student_id: str):
    return supabase.table("grades") \
        .select("*") \
        .eq("student_id", student_id) \
        .execute().data
