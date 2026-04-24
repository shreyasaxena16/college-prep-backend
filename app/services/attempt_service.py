from app.services.supabase_client import supabase


def submit_answer(user_id, question_id, selected_answer):

    q = supabase.table("questions") \
        .select("correct_answer, explanation") \
        .eq("id", question_id) \
        .execute()

    correct = q.data[0]["correct_answer"]
    explanation = q.data[0]["explanation"]

    is_correct = selected_answer == correct

    supabase.table("attempts").insert({
        "user_id": user_id,
        "question_id": question_id,
        "selected_answer": selected_answer,
        "is_correct": is_correct
    }).execute()

    return {
        "correct": is_correct,
        "correct_answer": correct,
        "explanation": explanation
    }