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


def generate_sat_todo_plan(
    current_date: str,
    sat_date: str,
    target_score_range: str,
):
    client = get_gemini_client()
    prompt = f"""
You are an expert SAT prep coach and academic planner.

Create a granular SAT preparation plan that can be converted directly into a student's Todo list.

Current date: {current_date}
Planned SAT test date: {sat_date}
Target SAT score range: {target_score_range}

The plan must be realistic for the available duration between the current date and the SAT test date.
It must be specific enough that a student can track progress week by week and task by task.

Planning requirements:
- Include diagnostic/mock tests at sensible points.
- Include review tasks after mock tests.
- Include Math tasks such as Algebra, Advanced Math, Problem Solving/Data Analysis, Geometry, and Trigonometry where appropriate.
- Include Reading/Writing tasks such as Craft and Structure, Information and Ideas, Standard English Conventions, and Expression of Ideas.
- Match task difficulty to the target score range:
  - 1000-1200: foundation-building, easy-range mastery, accuracy, core formulas, basic grammar.
  - 1200-1400: medium-range mastery, timing, mixed-topic sets, error-log review, strategy refinement.
  - 1400+: hard-range mastery, advanced pacing, trap-answer analysis, high-difficulty drills, full-test endurance.
- Spread work across the available dates. Do not put every task on the same date.
- Every task must have a tentative start_date and due_date in YYYY-MM-DD format.
- Tasks may include subtasks. Subtasks must be concrete and checkable.
- Keep task titles short enough for a Todo table.
- Descriptions should explain what the student actually needs to do.
- Avoid vague tasks like "study more"; make each task actionable.

Return ONLY valid JSON. No markdown. No text outside JSON.

Required JSON shape:
{{
  "plan_title": "string",
  "summary": "string",
  "tasks": [
    {{
      "title": "string",
      "description": "string",
      "start_date": "YYYY-MM-DD",
      "due_date": "YYYY-MM-DD",
      "reminder_enabled": true,
      "subtasks": ["string", "string"]
    }}
  ]
}}
"""

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt
    )

    text = response.text
    cleaned = re.sub(r"```json|```", "", text).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        return {
            "raw_output": text,
            "error": "Failed to parse JSON"
        }
