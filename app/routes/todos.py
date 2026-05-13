from fastapi import APIRouter, HTTPException
from postgrest.exceptions import APIError
from app.services.supabase_client import get_supabase
from app.services.gemini_service import generate_sat_todo_plan
from datetime import date
from datetime import datetime

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


def calculate_duration_weeks(sat_date: str):
    start = date.today()
    end = datetime.strptime(sat_date, "%Y-%m-%d").date()
    days = max((end - start).days, 1)
    return max(round(days / 7), 1)


def calculate_day_offset(task_date: str, current_date: str):
    if not task_date:
        return None

    task_day = datetime.strptime(task_date, "%Y-%m-%d").date()
    plan_start = datetime.strptime(current_date, "%Y-%m-%d").date()
    return max((task_day - plan_start).days, 0)


def date_from_offset(start_date: date, offset):
    if offset is None:
        return None

    from datetime import timedelta
    return (start_date + timedelta(days=int(offset))).isoformat()


def build_plan_title(duration_weeks: int, target_score_range: str):
    return f"{duration_weeks} week {target_score_range} plan"


def get_cached_plan(duration_weeks: int, target_score_range: str):
    response = supabase.table("sat_prep_plan_templates") \
        .select("*") \
        .eq("duration_weeks", duration_weeks) \
        .eq("target_score_range", target_score_range) \
        .limit(1) \
        .execute()

    plans = response.data or []
    return plans[0] if plans else None


def create_plan_template(
    plan: dict,
    duration_weeks: int,
    target_score_range: str,
    current_date: str,
):
    title = plan.get("plan_title") or build_plan_title(
        duration_weeks,
        target_score_range,
    )

    response = supabase.table("sat_prep_plan_templates").insert({
        "title": title,
        "summary": plan.get("summary"),
        "duration_weeks": duration_weeks,
        "target_score_range": target_score_range,
    }).execute()

    template = response.data[0]
    task_rows = []

    for index, task in enumerate(plan.get("tasks") or [], start=1):
        title = (task.get("title") or "").strip()
        if not title:
            continue

        task_rows.append({
            "plan_template_id": template["id"],
            "sort_order": index,
            "title": title,
            "description": task.get("description"),
            "relative_start_day": calculate_day_offset(
                task.get("start_date"),
                current_date,
            ),
            "relative_due_day": calculate_day_offset(
                task.get("due_date"),
                current_date,
            ),
            "reminder_enabled": bool(task.get("reminder_enabled", True)),
            "subtasks": task.get("subtasks") or [],
        })

    if task_rows:
        supabase.table("sat_prep_plan_template_tasks").insert(task_rows).execute()

    return template


def get_template_tasks(template_id: str):
    response = supabase.table("sat_prep_plan_template_tasks") \
        .select("*") \
        .eq("plan_template_id", template_id) \
        .order("sort_order") \
        .execute()

    return response.data or []


def get_student_plan(student_id: str, template_id: str, sat_date: str):
    response = supabase.table("student_sat_prep_plans") \
        .select("*") \
        .eq("student_id", student_id) \
        .eq("plan_template_id", template_id) \
        .eq("sat_date", sat_date) \
        .limit(1) \
        .execute()

    plans = response.data or []
    return plans[0] if plans else None


def create_student_plan(student_id: str, template: dict, sat_date: str):
    response = supabase.table("student_sat_prep_plans").insert({
        "student_id": student_id,
        "plan_template_id": template["id"],
        "title": template.get("title"),
        "sat_date": sat_date,
        "target_score_range": template.get("target_score_range"),
    }).execute()

    return response.data[0]


def copy_template_tasks_to_todos(
    student_id: str,
    student_plan: dict,
    template_id: str,
):
    existing = supabase.table("todos") \
        .select("id") \
        .eq("student_id", student_id) \
        .eq("plan_id", student_plan["id"]) \
        .execute()

    if existing.data:
        return []

    rows = []
    plan_start_date = date.today()
    for task in get_template_tasks(template_id):
        rows.append({
            "student_id": student_id,
            "plan_id": student_plan["id"],
            "title": task.get("title"),
            "description": format_task_description(task),
            "start_date": date_from_offset(
                plan_start_date,
                task.get("relative_start_day"),
            ),
            "due_date": date_from_offset(
                plan_start_date,
                task.get("relative_due_day"),
            ),
            "reminder_enabled": bool(task.get("reminder_enabled", True)),
        })

    if not rows:
        return []

    response = supabase.table("todos").insert(rows).execute()
    return response.data or []


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

    resolved_student_id = resolve_student_id(student_id)
    duration_weeks = calculate_duration_weeks(sat_date)
    current_date = date.today().isoformat()

    try:
        template = get_cached_plan(duration_weeks, target_score_range)

        generated = False
        if not template:
            plan = generate_sat_todo_plan(
                current_date=current_date,
                sat_date=sat_date,
                target_score_range=target_score_range,
            )

            if isinstance(plan, dict) and plan.get("error"):
                raise HTTPException(status_code=500, detail=plan["error"])

            tasks = plan.get("tasks") if isinstance(plan, dict) else None
            if not tasks:
                raise HTTPException(status_code=500, detail="Gemini returned no tasks")

            template = create_plan_template(
                plan=plan,
                duration_weeks=duration_weeks,
                target_score_range=target_score_range,
                current_date=current_date,
            )
            generated = True

        student_plan = get_student_plan(
            student_id=resolved_student_id,
            template_id=template["id"],
            sat_date=sat_date,
        )

        if not student_plan:
            student_plan = create_student_plan(
                student_id=resolved_student_id,
                template=template,
                sat_date=sat_date,
            )

        copied_tasks = copy_template_tasks_to_todos(
            student_id=resolved_student_id,
            student_plan=student_plan,
            template_id=template["id"],
        )
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return {
        "plan": student_plan,
        "template": template,
        "generated": generated,
        "inserted": len(copied_tasks),
        "tasks": copied_tasks,
    }


@router.get("/plans/{student_id}")
def get_student_plans(student_id: str):
    resolved_student_id = resolve_student_id(student_id)

    try:
        response = supabase.table("student_sat_prep_plans") \
            .select("*") \
            .eq("student_id", resolved_student_id) \
            .order("created_at", desc=True) \
            .execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return response.data or []


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
