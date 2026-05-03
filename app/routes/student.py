from fastapi import APIRouter
from app.services.supabase_service import get_supabase
from pydantic import BaseModel

router = APIRouter()
supabase = get_supabase()


class AttemptRequest(BaseModel):
    student_id: str
    question_id: str
    selected_answer: str

@router.post("/attempt")
def save_attempt(req: AttemptRequest):

    # 1. get correct answer
    res = supabase.table("questions") \
        .select("correct_answer") \
        .eq("id", req.question_id) \
        .execute()

    correct_answer = res.data[0]["correct_answer"]

    # 2. check correctness
    is_correct = req.selected_answer == correct_answer

    # 3. insert attempt
    supabase.table("student_attempts").insert({
        "student_id": req.student_id,
        "question_id": req.question_id,
        "selected_answer": req.selected_answer,
        "is_correct": is_correct
    }).execute()

    return {
        "correct": is_correct
    }

@router.get("/incorrect")
def get_incorrect_questions(student_id: str):

    res = supabase.rpc(
        "get_incorrect_questions",
        {"student_id_input": student_id}
    ).execute()

    return res.data

@router.get("/unattempted")
def get_unattempted_questions(student_id: str):

    res = supabase.rpc(
        "get_unattempted_questions",
        {"student_id_input": student_id}
    ).execute()

    return res.data