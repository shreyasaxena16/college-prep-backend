from fastapi import APIRouter, HTTPException
from app.models.test_schemas import QuestionRequest, AnswerRequest,TestStartRequest,AnswerItem,SubmitRequest
from app.services.question_service import get_questions
from app.services.attempt_service import submit_answer
from app.services.supabase_service import get_supabase
import random
import uuid
from app.services.supabase_service import get_student, get_profile

router = APIRouter(prefix="", tags=["Test"])

SAT_RANGE_TO_DIFFICULTY = {
    "1000-1200": "easy",
    "1200-1400": "medium",
    "1400+": "hard",
}

SAT_RANGE_BOUNDS = {
    "1000-1200": (1000, 1200),
    "1200-1400": (1200, 1400),
    "1400+": (1400, 1600),
}

DIFFICULTY_TO_SAT_RANGE = {
    "easy": "1000-1200",
    "medium": "1200-1400",
    "hard": "1400+",
}



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


def get_question_sat_range(question):
    sat_band = question.get("sat_band")
    difficulty = (question.get("difficulty") or "").lower()

    if difficulty in DIFFICULTY_TO_SAT_RANGE:
        return DIFFICULTY_TO_SAT_RANGE[difficulty]

    if sat_band in SAT_RANGE_BOUNDS:
        return sat_band

    return "1000-1200"


def to_projected_sat_score(answers):
    if not answers:
        return 400

    earned_scores = []
    for answer in answers:
        sat_range = get_question_sat_range(answer)
        lower, upper = SAT_RANGE_BOUNDS.get(sat_range, (1000, 1200))
        earned_scores.append(upper if answer.get("is_correct") else lower)

    projected = sum(earned_scores) / len(earned_scores)
    return round(projected / 10) * 10


def get_user_question_history(supabase, user_id):
    sessions = supabase.table("test_sessions") \
        .select("id") \
        .eq("user_id", user_id) \
        .execute().data or []

    session_ids = [session["id"] for session in sessions if session.get("id")]
    if not session_ids:
        return set(), set()

    answers = supabase.table("test_answers") \
        .select("question_id, is_correct") \
        .in_("session_id", session_ids) \
        .execute().data or []

    correct_question_ids = set()
    incorrect_question_ids = set()

    for answer in answers:
        question_id = answer.get("question_id")
        if not question_id:
            continue

        if answer.get("is_correct"):
            correct_question_ids.add(question_id)
        else:
            incorrect_question_ids.add(question_id)

    return correct_question_ids, incorrect_question_ids


def matches_test_filters(question, subjects, sat_range):
    if subjects and question.get("subject") not in subjects:
        return False

    target_difficulty = SAT_RANGE_TO_DIFFICULTY.get(sat_range)
    if target_difficulty and (question.get("difficulty") or "").lower() == target_difficulty:
        return True

    return question.get("sat_band") == sat_range


def select_test_questions(
    questions,
    total,
    correct_question_ids,
    incorrect_question_ids,
    include_previous_correct,
):
    unique_questions = list({q["id"]: q for q in questions}.values())
    previous_incorrect = [
        q for q in unique_questions
        if q["id"] in incorrect_question_ids
    ]
    new_question_pool = [
        q for q in unique_questions
        if q["id"] not in incorrect_question_ids
        and (
            include_previous_correct
            or q["id"] not in correct_question_ids
        )
    ]

    final_questions = []
    final_questions.extend(safe_sample(previous_incorrect, total))

    remaining_count = total - len(final_questions)
    if remaining_count > 0:
        final_questions.extend(safe_sample(new_question_pool, remaining_count))

    final_questions = unique_by_id(final_questions)
    random.shuffle(final_questions)
    return final_questions[:total]


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

    if not profile or profile.get("role") not in ["student", "admin"]:
        raise HTTPException(status_code=403, detail="Students and admins only")

    # 1. Create session
    session = supabase.table("test_sessions").insert({
        "user_id": req.user_id,
        "total_questions": req.total_questions,
        "current_index": 0,
        "score": 0,
        "status": "active"
    }).execute()

    session_id = session.data[0]["id"]

    # 2. Fetch questions for selected subject(s), then apply SAT range locally.
    query = supabase.table("questions").select("*")

    if req.subjects:
        query = query.in_("subject", req.subjects)

    questions = [
        question
        for question in query.execute().data or []
        if matches_test_filters(question, req.subjects, req.sat_range)
    ]

    total = req.total_questions
    correct_question_ids, incorrect_question_ids = get_user_question_history(
        supabase,
        req.user_id
    )

    final_questions = select_test_questions(
        questions=questions,
        total=total,
        correct_question_ids=correct_question_ids,
        incorrect_question_ids=incorrect_question_ids,
        include_previous_correct=req.include_previous_correct,
    )

    return {
        "session_id": session_id,
        "questions": final_questions,
        "included_previous_incorrect": len([
            q for q in final_questions
            if q["id"] in incorrect_question_ids
        ]),
        "excluded_previous_correct": not req.include_previous_correct
    }

from datetime import datetime
import uuid

@router.post("/submit_answers")
async def submit_answers(payload: SubmitRequest):
    supabase = get_supabase()

    correct_count = 0
    answers_to_insert = []
    result_items = []

    for ans in payload.answers:

        response = supabase.table("questions") \
            .select("id, question, options, correct_answer, explanation, subject, topic, difficulty, sat_band") \
            .eq("id", ans.question_id) \
            .single() \
            .execute()

        question = response.data
        if not question:
            raise HTTPException(
                status_code=404,
                detail=f"Question not found: {ans.question_id}"
            )

        is_correct = question["correct_answer"] == ans.selected_answer

        if is_correct:
            correct_count += 1

        answer_id = str(uuid.uuid4())
        answers_to_insert.append({
            "id": answer_id,
            "session_id": payload.session_id,
            "question_id": ans.question_id,
            "selected_answer": ans.selected_answer,
            "is_correct": is_correct
        })

        result_items.append({
            "answer_id": answer_id,
            "question_id": question["id"],
            "question": question.get("question"),
            "options": question.get("options") or [],
            "selected_answer": ans.selected_answer,
            "correct_answer": question.get("correct_answer"),
            "is_correct": is_correct,
            "explanation": question.get("explanation"),
            "subject": question.get("subject"),
            "topic": question.get("topic"),
            "difficulty": question.get("difficulty"),
            "sat_band": question.get("sat_band"),
        })

    # Insert all answers in one go (better)
    if answers_to_insert:
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
        "total": len(payload.answers),
        "correct": correct_count,
        "incorrect": len(payload.answers) - correct_count,
        "projected_sat_score": to_projected_sat_score(result_items),
        "answers": result_items
    }


@router.get("/results/{session_id}")
def get_test_results(session_id: str):
    supabase = get_supabase()

    session = supabase.table("test_sessions") \
        .select("*") \
        .eq("id", session_id) \
        .single() \
        .execute().data

    if not session:
        raise HTTPException(status_code=404, detail="Test session not found")

    saved_answers = supabase.table("test_answers") \
        .select("*") \
        .eq("session_id", session_id) \
        .execute().data or []

    question_ids = [
        answer["question_id"]
        for answer in saved_answers
        if answer.get("question_id")
    ]

    questions_by_id = {}
    if question_ids:
        questions = supabase.table("questions") \
            .select("id, question, options, correct_answer, explanation, subject, topic, difficulty, sat_band") \
            .in_("id", question_ids) \
            .execute().data or []

        questions_by_id = {question["id"]: question for question in questions}

    result_items = []
    for answer in saved_answers:
        question = questions_by_id.get(answer.get("question_id"), {})
        result_items.append({
            "answer_id": answer.get("id"),
            "question_id": answer.get("question_id"),
            "question": question.get("question"),
            "options": question.get("options") or [],
            "selected_answer": answer.get("selected_answer"),
            "correct_answer": question.get("correct_answer"),
            "is_correct": answer.get("is_correct"),
            "explanation": question.get("explanation"),
            "subject": question.get("subject"),
            "topic": question.get("topic"),
            "difficulty": question.get("difficulty"),
            "sat_band": question.get("sat_band"),
        })

    correct_count = sum(1 for item in result_items if item["is_correct"])
    total = len(result_items)

    return {
        "session_id": session_id,
        "status": session.get("status"),
        "score": session.get("score", correct_count),
        "total": total,
        "correct": correct_count,
        "incorrect": total - correct_count,
        "projected_sat_score": to_projected_sat_score(result_items),
        "answers": result_items
    }


@router.get("/history/{user_id}")
def get_test_history(user_id: str):
    supabase = get_supabase()

    sessions = supabase.table("test_sessions") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("status", "completed") \
        .order("created_at", desc=False) \
        .execute().data or []

    history = []
    for index, session in enumerate(sessions, start=1):
        saved_answers = supabase.table("test_answers") \
            .select("*") \
            .eq("session_id", session.get("id")) \
            .execute().data or []

        question_ids = [
            answer["question_id"]
            for answer in saved_answers
            if answer.get("question_id")
        ]

        questions_by_id = {}
        if question_ids:
            questions = supabase.table("questions") \
                .select("id, subject, topic, difficulty, sat_band") \
                .in_("id", question_ids) \
                .execute().data or []

            questions_by_id = {question["id"]: question for question in questions}

        scored_answers = []
        for answer in saved_answers:
            question = questions_by_id.get(answer.get("question_id"), {})
            scored_answers.append({
                "is_correct": answer.get("is_correct"),
                "difficulty": question.get("difficulty"),
                "sat_band": question.get("sat_band"),
            })

        score = sum(1 for answer in scored_answers if answer.get("is_correct"))
        total_questions = len(scored_answers) or session.get("total_questions") or 0
        percentage = round((score / total_questions) * 100, 1) if total_questions else 0

        history.append({
            "session_id": session.get("id"),
            "attempt_number": index,
            "taken_at": session.get("created_at"),
            "score": score,
            "total": total_questions,
            "percentage": percentage,
            "projected_sat_score": to_projected_sat_score(scored_answers),
            "status": session.get("status"),
        })

    latest = history[-1] if history else None
    previous = history[-2] if len(history) > 1 else None
    score_change = (
        latest["projected_sat_score"] - previous["projected_sat_score"]
        if latest and previous
        else 0
    )

    return {
        "user_id": user_id,
        "attempt_count": len(history),
        "latest": latest,
        "score_change": score_change,
        "history": history
    }
