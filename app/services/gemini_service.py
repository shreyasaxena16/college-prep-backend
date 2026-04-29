import json
import re
from supabase import create_client
from app.config import client


# ----------------------------
# GENERATE QUESTIONS (AI)
# ----------------------------
def generate_questions(category: str, subcategory: str, difficulty: str, count: int = 10):
    
    prompt = f"""
Generate {count} MCQ questions.

Category: {category}
Subcategory: {subcategory}
Difficulty: {difficulty}

Return JSON only with fields:
- question
- options
- correct_answer
- explanation
- category
- subcategory
- difficulty
"""

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt
    )

    text = response.text

    # Clean markdown if present
    cleaned = re.sub(r"```json|```", "", text).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        return {
            "raw_output": text,
            "error": "Failed to parse JSON"
        }
