from fastapi import APIRouter, HTTPException
from postgrest.exceptions import APIError
from app.services.supabase_client import get_supabase

router = APIRouter()
supabase = get_supabase()


@router.post("/")
def create_todo(payload: dict):
    student_id = payload.get("student_id")
    title = payload.get("title")

    if not student_id or not title:
        raise HTTPException(status_code=400, detail="student_id and title required")

    try:
        response = supabase.table("todos").insert(payload).execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return response.data


@router.get("/{student_id}")
def get_todos(student_id: str):

    try:
        todos = supabase.table("todos") \
            .select("*") \
            .eq("student_id", student_id) \
            .execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return todos.data or []
