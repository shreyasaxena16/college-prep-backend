from collections import defaultdict
from typing import Any

from app.services.supabase_client import get_supabase


GRADE_MAP = {
    "A": 4.0,
    "B": 3.0,
    "C": 2.0,
    "D": 1.0,
    "F": 0.0,
}


def _compact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _compact(item)
            for key, item in value.items()
            if item not in (None, "", [])
        }
    if isinstance(value, list):
        return [_compact(item) for item in value if item not in (None, "", [])]
    return value


def _first(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return None


def _resolve_student(supabase: Any, profile_id: str) -> dict[str, Any] | None:
    by_profile = supabase.table("students") \
        .select("*") \
        .eq("profile_id", profile_id) \
        .execute().data

    student = _first(by_profile)
    if student:
        return student

    by_id = supabase.table("students") \
        .select("*") \
        .eq("id", profile_id) \
        .execute().data

    return _first(by_id)


def _calculate_gpa(grades: list[dict[str, Any]]) -> float | None:
    total_points = 0.0
    total_credits = 0.0

    for grade in grades:
        grade_value = (grade.get("grade") or "").strip().upper()
        if grade_value not in GRADE_MAP:
            continue

        credits = grade.get("credits") or 1
        course_type = (grade.get("course_type") or "on_level").lower()
        bonus = 0.5 if course_type == "advanced" else 1.0 if course_type == "ap" else 0.0

        total_points += (GRADE_MAP[grade_value] + bonus) * credits
        total_credits += credits

    if total_credits == 0:
        return None

    return round(total_points / total_credits, 2)


def _summarize_grades(supabase: Any, student_id: str) -> dict[str, Any]:
    grades = supabase.table("grades") \
        .select("*") \
        .eq("student_id", student_id) \
        .execute().data or []

    return {
        "weighted_gpa": _calculate_gpa(grades),
        "grade_entries": len(grades),
    }


def _summarize_tests(supabase: Any, profile_id: str) -> dict[str, Any]:
    sessions = supabase.table("test_sessions") \
        .select("*") \
        .eq("user_id", profile_id) \
        .eq("status", "completed") \
        .order("created_at", desc=True) \
        .limit(5) \
        .execute().data or []

    session_ids = [session["id"] for session in sessions if session.get("id")]
    if not session_ids:
        return {
            "completed_tests": 0,
        }

    answers = supabase.table("test_answers") \
        .select("*") \
        .in_("session_id", session_ids) \
        .execute().data or []

    question_ids = [answer["question_id"] for answer in answers if answer.get("question_id")]
    questions_by_id: dict[str, dict[str, Any]] = {}
    if question_ids:
        questions = supabase.table("questions") \
            .select("id, subject, topic, difficulty, sat_band") \
            .in_("id", question_ids) \
            .execute().data or []
        questions_by_id = {question["id"]: question for question in questions}

    total = len(answers)
    correct = sum(1 for answer in answers if answer.get("is_correct"))
    topic_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"missed": 0, "total": 0})

    for answer in answers:
        question = questions_by_id.get(answer.get("question_id"), {})
        subject = question.get("subject") or "Unknown subject"
        topic = question.get("topic") or "Unknown topic"
        label = f"{subject}: {topic}"

        topic_stats[label]["total"] += 1
        if not answer.get("is_correct"):
            topic_stats[label]["missed"] += 1

    weak_areas = [
        {
            "area": area,
            "missed": stats["missed"],
            "attempted": stats["total"],
        }
        for area, stats in sorted(
            topic_stats.items(),
            key=lambda item: (item[1]["missed"], item[1]["total"]),
            reverse=True,
        )
        if stats["missed"] > 0
    ][:5]

    latest = sessions[0] if sessions else {}

    return {
        "completed_tests": len(sessions),
        "recent_answer_accuracy": round((correct / total) * 100, 1) if total else None,
        "latest_test_score": latest.get("score"),
        "latest_test_total": latest.get("total_questions"),
        "weak_areas": weak_areas,
    }


def build_bunny_context(context: dict[str, Any] | None) -> dict[str, Any]:
    base_context = _compact(context or {})
    auth_status = base_context.get("auth_status")
    user_id = base_context.get("user_id")

    if not user_id:
        return {
            **base_context,
            "auth_status": "guest",
            "learner_context": "Guest user. Give general site guidance and preparation advice based only on the question and public site features.",
        }

    student_context: dict[str, Any] = {
        "auth_status": auth_status or "student",
        "profile_id": user_id,
    }

    try:
        supabase = get_supabase()
        student = _resolve_student(supabase, str(user_id))

        if student:
            student_id = student.get("id")
            student_context["student_id"] = student_id
            student_context["student_name"] = " ".join(
                part
                for part in [
                    student.get("first_name") or student.get("firstname"),
                    student.get("last_name") or student.get("lastname"),
                ]
                if part
            )

            if student_id:
                student_context["gpa_summary"] = _summarize_grades(supabase, student_id)

        student_context["test_prep_summary"] = _summarize_tests(supabase, str(user_id))
        student_context["learner_context"] = (
            "Logged-in student. Use available GPA, test history, weak areas, and page/question context. "
            "If a detail is missing, say what to add or where to track it."
        )
    except Exception as exc:
        student_context["context_warning"] = f"Student history lookup failed: {exc}"
        student_context["learner_context"] = (
            "Logged-in student, but historical data could not be loaded. Use provided page/question context."
        )

    return _compact({
        **base_context,
        **student_context,
    })
