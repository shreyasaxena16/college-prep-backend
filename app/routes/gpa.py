from fastapi import APIRouter
from app.services.supabase_client import supabase

router = APIRouter()

GRADE_MAP = {
    "A": 4.0,
    "B": 3.0,
    "C": 2.0,
    "D": 1.0,
    "F": 0.0
}

LEVEL_BONUS = {
    "OnLevel": 0.0,
    "Advanced": 0.5,
    "AP": 1.0
}


@router.get("/{profile_id}")
def calculate_gpa(profile_id: str):

    # 🔥 STEP 1: Get student using profile_id
    student = supabase.table("students") \
        .select("*") \
        .eq("profile_id", profile_id) \
        .single() \
        .execute().data

    if not student:
        return {"gpa": 0, "error": "Student not found"}

    student_id = student["id"]

    # 🔥 STEP 2: Use student_id correctly
    subjects = supabase.table("subjects") \
        .select("*") \
        .eq("student_id", student_id) \
        .execute().data or []

    total_points = 0
    total_credits = 0

    for subject in subjects:

        grades = supabase.table("grades") \
            .select("*") \
            .eq("subject_id", subject["id"]) \
            .execute().data or []

        if not grades:
            continue

        level = (subject.get("level") or "").strip()
        bonus = LEVEL_BONUS.get(level, 0)
        credits = subject.get("credits", 1)

        for g in grades:

            grade_value = (g.get("grade") or "").strip().upper()

            if grade_value not in GRADE_MAP:
                continue

            base = GRADE_MAP[grade_value]

            total_points += (base + bonus) * credits
            total_credits += credits

    if total_credits == 0:
        return {"gpa": 0}

    gpa = total_points / total_credits

    return {
        "profile_id": profile_id,
        "student_id": student_id,
        "gpa": round(gpa, 2)
    }