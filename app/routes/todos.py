from fastapi import APIRouter, HTTPException
from app.services.supabase_client import get_supabase

router = APIRouter()
supabase = get_supabase()


@router.post("/")
def create_todo(payload: dict):
    student_id = payload.get("student_id")
    title = payload.get("title")

    if not student_id or not title:
        raise HTTPException(status_code=400, detail="student_id and title required")

    response = supabase.table("todos").insert(payload).execute()

    return response.data


@router.get("/{student_id}")
def get_todos(student_id: str):

    todos = supabase.table("todos") \
        .select("*") \
        .eq("student_id", student_id) \
        .execute()

    return todos.data or []