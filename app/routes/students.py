from fastapi import APIRouter
from app.services.supabase_client import get_supabase
supabase = get_supabase()

router = APIRouter()

@router.post("/")
def create_student(data: dict):
    response = supabase.table("students").insert(data).execute()
    return response.data


@router.get("/")
def get_students():
    response = supabase.table("students").select("*").execute()
    return response.data

@router.get("/{profile_id}")
def get_student(profile_id: str):
    return supabase.table("students") \
        .select("*") \
        .eq("profile_id", profile_id) \
        .execute().data

@router.get("/profile/{profile_id}")
def get_student_by_profile(profile_id: str):
    response = supabase.table("students") \
        .select("*") \
        .eq("profile_id", profile_id) \
        .single() \
        .execute()

    return response.data