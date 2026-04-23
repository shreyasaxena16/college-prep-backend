from fastapi import APIRouter
from app.services.supabase_client import supabase

router = APIRouter()

@router.post("/")
def create_subject(data: dict):
    response = supabase.table("subjects").insert(data).execute()
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