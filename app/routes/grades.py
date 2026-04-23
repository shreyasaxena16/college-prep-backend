from fastapi import APIRouter
from app.services.supabase_client import supabase

router = APIRouter()

@router.post("/")
def add_grade(data: dict):
    response = supabase.table("grades").insert(data).execute()
    return response.data


@router.get("/")
def get_grades():
    response = supabase.table("grades").select("*").execute()
    return response.data

@router.get("/{subject_id}")
def get_grades(subject_id: str):
    return supabase.table("grades") \
        .select("*") \
        .eq("subject_id", subject_id) \
        .execute().data