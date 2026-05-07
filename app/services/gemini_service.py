import json
import re
from supabase import create_client
from app.config import get_gemini_client




# ----------------------------
# GENERATE QUESTIONS (AI)
# ----------------------------
def generate_questions(subject: str, topic: str = None,count: int = 1, sat_distribution: dict[str, int] = None, difficulty: str = "medium" ):
    client = get_gemini_client()
    prompt = f"""
You are an expert SAT exam content creator.

Generate EXACTLY {count} high-quality SAT-style multiple choice questions.

Subject: {subject}
Topic: {topic}
SAT DISTRIBUTION (IMPORTANT):
{sat_distribution}
Difficulty: {difficulty} (ensure it matches the SAT band)

CRITICAL RULES:
- Each question must have exactly 4 options (A, B, C, D)
- correct_answer must match one option index (A/B/C/D)
- Questions must resemble real SAT questions (not generic trivia)
- sat_band must match difficulty level
- no missing fields allowed
- NO repetition allowed
- Ensure increasing difficulty across SAT bands
- Explanations must clearly justify WHY the correct answer is right
- Incorrect options should be plausible (not obvious throwaways)

DIFFICULTY FIELD RULE:
- Map SAT bands to difficulty as:
  - 1000-1200 → "easy"
  - 1200-1400 → "medium"
  - 1400+ → "hard"

Return ONLY valid JSON array. No text outside JSON.

Each object MUST follow this schema:

{{
  "question": "string",
  "options": ["string", "string", "string", "string"],
  "correct_answer": "A | B | C | D",
  "explanation": "string",
  "category": "{category}",
  "subcategory": "{subcategory}",
  "sat_band": "1000-1200 | 1200-1400 | 1400+",
  "difficulty": "easy | medium | hard"
}}

Example format:

[
  {{
    "question": "What is 2+2?",
    "options": ["1", "2", "3", "4"],
    "correct_answer": "4",
    "explanation": "2+2 equals 4.",
    "subject": "{subject}",
    "topic": "{topic}",
    "difficulty": "easy",
    "sat_band": "1000-1200"
  }}
]
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
