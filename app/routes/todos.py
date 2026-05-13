from fastapi import APIRouter, HTTPException
from postgrest.exceptions import APIError
from app.services.supabase_client import get_supabase
from app.services.gemini_service import generate_sat_todo_plan
from datetime import date

router = APIRouter()
supabase = get_supabase()


def get_student_ids(profile_or_student_id: str):
    ids = [profile_or_student_id]

    by_profile = supabase.table("students") \
        .select("id") \
        .eq("profile_id", profile_or_student_id) \
        .execute()

    for student in by_profile.data or []:
        if student.get("id") and student["id"] not in ids:
            ids.append(student["id"])

    by_id = supabase.table("students") \
        .select("id") \
        .eq("id", profile_or_student_id) \
        .execute()

    for student in by_id.data or []:
        if student.get("id") and student["id"] not in ids:
            ids.append(student["id"])

    return ids


def resolve_student_id(profile_or_student_id: str):
    student_ids = get_student_ids(profile_or_student_id)
    return student_ids[0] if student_ids else profile_or_student_id


def format_task_description(task: dict):
    description = task.get("description") or ""
    subtasks = task.get("subtasks") or []

    if not subtasks:
        return description

    subtask_text = "\n".join(f"- {subtask}" for subtask in subtasks)
    return f"{description}\n\nSubtasks:\n{subtask_text}".strip()


@router.post("/")
def create_todo(payload: dict):
    student_id = payload.get("student_id") or payload.get("profile_id")
    title = payload.get("title")

    if not student_id or not title:
        raise HTTPException(status_code=400, detail="student_id and title required")

    payload["student_id"] = resolve_student_id(student_id)

    try:
        response = supabase.table("todos").insert(payload).execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return response.data


@router.post("/generate-plan")
def generate_todo_plan(payload: dict):
    student_id = payload.get("student_id") or payload.get("profile_id")
    sat_date = payload.get("sat_date")
    target_score_range = payload.get("target_score_range")

    if not student_id or not sat_date or not target_score_range:
        raise HTTPException(
            status_code=400,
            detail="student_id, sat_date, and target_score_range are required"
        )

    plan = generate_sat_todo_plan(
        current_date=date.today().isoformat(),
        sat_date=sat_date,
        target_score_range=target_score_range,
    )

    if isinstance(plan, dict) and plan.get("error"):
        raise HTTPException(status_code=500, detail=plan["error"])

    tasks = plan.get("tasks") if isinstance(plan, dict) else None
    if not tasks:
        raise HTTPException(status_code=500, detail="Gemini returned no tasks")

    resolved_student_id = resolve_student_id(student_id)
    rows = []

    for task in tasks:
        title = (task.get("title") or "").strip()
        if not title:
            continue

        rows.append({
            "student_id": resolved_student_id,
            "title": title,
            "description": format_task_description(task),
            "start_date": task.get("start_date") or None,
            "due_date": task.get("due_date") or None,
            "reminder_enabled": bool(task.get("reminder_enabled", True)),
        })

    if not rows:
        raise HTTPException(status_code=500, detail="Gemini returned invalid tasks")

    try:
        response = supabase.table("todos").insert(rows).execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return {
        "plan_title": plan.get("plan_title"),
        "summary": plan.get("summary"),
        "inserted": len(response.data or []),
        "tasks": response.data or [],
    }


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
