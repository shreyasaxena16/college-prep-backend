from fastapi import APIRouter, HTTPException
from postgrest.exceptions import APIError
from app.services.supabase_client import get_supabase

router = APIRouter()
supabase = get_supabase()


def get_student_ids(profile_or_student_id: str):
    ids = {profile_or_student_id}

    by_profile = supabase.table("students") \
        .select("id") \
        .eq("profile_id", profile_or_student_id) \
        .execute()

    for student in by_profile.data or []:
        if student.get("id"):
            ids.add(student["id"])

    by_id = supabase.table("students") \
        .select("id") \
        .eq("id", profile_or_student_id) \
        .execute()

    for student in by_id.data or []:
        if student.get("id"):
            ids.add(student["id"])

    return list(ids)


@router.post("/")
def create_todo(payload: dict):
    student_id = payload.get("student_id") or payload.get("profile_id")
    title = payload.get("title")

    if not student_id or not title:
        raise HTTPException(status_code=400, detail="student_id and title required")

    payload["student_id"] = get_student_ids(student_id)[0]

    try:
        response = supabase.table("todos").insert(payload).execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return response.data


@router.get("/{student_id}")
def get_todos(student_id: str):

    try:
        student_ids = get_student_ids(student_id)
        todos = supabase.table("todos") \
            .select("*") \
            .in_("student_id", student_ids) \
            .execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return todos.data or []
