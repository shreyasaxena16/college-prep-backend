from fastapi import APIRouter
from app.models.test_schemas import QuestionRequest, AnswerRequest,TestStartRequest,AnswerItem,SubmitRequest
from app.services.question_service import get_questions
from app.services.attempt_service import submit_answer
from app.services.supabase_service import get_supabase
import random
import uuid
from app.services.supabase_service import get_student, get_profile

router = APIRouter(prefix="", tags=["Test"])



# -------------------------
# QUESTION + ANSWER APIs
# -------------------------
@router.post("/question")
def fetch_question(req: QuestionRequest):
    return get_questions(req.user_id, req.topic, req.difficulty)


@router.post("/submit")
def submit(req: AnswerRequest):
    return submit_answer(
        req.user_id,
        req.question_id,
        req.selected_answer
    )


# -------------------------
# HELPERS
# -------------------------
def unique_by_id(questions):
    seen = set()
    out = []
    for q in questions:
        if q["id"] not in seen:
            out.append(q)
            seen.add(q["id"])
    return out


def safe_sample(pool, k):
    if len(pool) <= k:
        return pool.copy()
    return random.sample(pool, k)


# -------------------------
# START TEST
# -------------------------
@router.post("/start_test")
def start_test(req: TestStartRequest):
    
    supabase = get_supabase()
    profile = supabase.table("profiles") \
    .select("*") \
    .eq("id", req.user_id) \
    .single() \
    .execute().data

    if not profile or profile.get("role") != "student":
        return {"error": "Students only"}

    # 1. Create session
    session = supabase.table("test_sessions").insert({
        "user_id": req.user_id,
        "total_questions": req.total_questions,
        "current_index": 0,
        "score": 0,
        "status": "active"
    }).execute()

    session_id = session.data[0]["id"]

    # 2. Fetch questions (multi-subject safe)
    query = supabase.table("questions").select("*")

    if req.subjects:
        query = query.in_("subject", req.subjects)

    questions = query.execute().data or []

    # 3. HARD dedup at DB-result level
    unique_questions = {q["id"]: q for q in questions}.values()

    # 4. Split by difficulty
    easy_pool = [q for q in unique_questions if q["difficulty"] == "easy"]
    medium_pool = [q for q in unique_questions if q["difficulty"] == "medium"]
    hard_pool = [q for q in unique_questions if q["difficulty"] == "hard"]

    total = req.total_questions

    easy_count = round(total * req.difficulty_mix.easy)
    medium_count = round(total * req.difficulty_mix.medium)
    hard_count = total - easy_count - medium_count

    def safe_sample(pool, k):
        pool = list(pool)
        if len(pool) <= k:
            return pool
        return random.sample(pool, k)

    # 5. Sample WITHOUT overlap risk
    selected = []

    selected.extend(safe_sample(easy_pool, easy_count))
    selected.extend(safe_sample(medium_pool, medium_count))
    selected.extend(safe_sample(hard_pool, hard_count))

    # 6. FINAL safety dedup (critical)
    seen = set()
    final_questions = []

    for q in selected:
        if q["id"] not in seen:
            final_questions.append(q)
            seen.add(q["id"])

    # 7. Ensure exact count
    random.shuffle(final_questions)
    final_questions = final_questions[:total]

    return {
        "session_id": session_id,
        "questions": final_questions
    }

from datetime import datetime
import uuid

@router.post("/submit_answers")
async def submit_answers(payload: SubmitRequest):
    supabase = get_supabase()

    correct_count = 0
    answers_to_insert = []

    for ans in payload.answers:

        response = supabase.table("questions") \
            .select("correct_answer") \
            .eq("id", ans.question_id) \
            .single() \
            .execute()

        question = response.data

        is_correct = question["correct_answer"] == ans.selected_answer

        if is_correct:
            correct_count += 1

        answers_to_insert.append({
            "id": str(uuid.uuid4()),
            "session_id": payload.session_id,
            "question_id": ans.question_id,
            "selected_answer": ans.selected_answer,
            "is_correct": is_correct
        })

    # Insert all answers in one go (better)
    supabase.table("test_answers").insert(answers_to_insert).execute()

    # Update session ONCE
    supabase.table("test_sessions") \
        .update({
            "score": correct_count,
            "status": "completed",
            
        }) \
        .eq("id", payload.session_id) \
        .execute()

    return {
        "session_id": payload.session_id,
        "score": correct_count,
        "total": len(payload.answers)
    }