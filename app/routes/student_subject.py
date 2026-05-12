from fastapi import APIRouter, HTTPException
from app.services.supabase_client import get_supabase

supabase = get_supabase()
router = APIRouter()


@router.post("/")
def save_student_subjects(payload: dict):

    student_id = payload.get("student_id")
    subjects = payload.get("subjects", [])

    if not student_id:
        raise HTTPException(status_code=400, detail="student_id required")

    if not isinstance(subjects, list):
        raise HTTPException(status_code=400, detail="subjects must be a list")

    inserted = []

    for s in subjects:

        subject_id = s.get("subject_id")
        level = s.get("level")
        grade_year = s.get("grade_year")

        if not subject_id:
            continue

        row = {
            "student_id": student_id,
            "subject_id": subject_id,
            "level": level,
            "grade_year": grade_year
        }

        response = supabase.table("student_subjects").insert(row).execute()

        if response.data:
            inserted.append(response.data)

    return {
        "message": "student subjects saved",
        "data": inserted
    }