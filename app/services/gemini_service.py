import json
import re
from supabase import create_client
from app.config import get_gemini_client



# ----------------------------
# GENERATE QUESTIONS (AI)
# ----------------------------
def generate_questions(subject: str, difficulty: str, topic:str=None,count: int = 1):
    client = get_gemini_client()
    prompt = f"""
Generate {count} MCQ questions.

Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}

HARD RULES:
- Return ONLY JSON
- Return EXACTLY {count} items in the array
- Do NOT add extra questions
- Do NOT explain outside JSON
- Difficulty should be one of: easy, medium, hard
- Each question should have 4 options

Return JSON only with fields:
- question
- options
- correct_answer
- explanation
- subject
- subcategory
- difficulty
"""

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt
    )

    text = response.text
    print("RAW GEMINI OUTPUT:")
    print(text)
    # Clean markdown if present
    cleaned = re.sub(r"```json|```", "", text).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        return {
            "raw_output": text,
            "error": "Failed to parse JSON"
        }
