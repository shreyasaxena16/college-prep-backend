from fastapi import APIRouter
from app.services.supabase_client import get_supabase
supabase = get_supabase()

router = APIRouter()

@router.post("/")
def add_grade(payload: dict):
    if not payload.get("subject_id"):
        return {"error": "subject_id is required"}, 400
    if payload.get("year") not in [9,10,11,12]:
        return {"error": "Invalid year"}, 400
    if payload.get("quarter") not in [1,2,3,4]:
        return {"error": "Invalid quarter"}, 400
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
    #Update existing if subject+year+qtr match, otherwise insert new
    existing = supabase.table("grades") \
    .select("id") \
    .eq("student_id", payload["student_id"]) \
    .eq("subject_id", payload["subject_id"]) \
    .eq("year", payload["year"]) \
    .eq("quarter", payload["quarter"]) \
    .execute().data
    if existing:
        response = supabase.table("grades").update(clean).eq("id", existing[0]["id"]).execute()
    else:
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
