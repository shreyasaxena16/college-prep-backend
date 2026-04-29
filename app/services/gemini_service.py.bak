import google.generativeai as genai
import json
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")


def generate_questions(topic, difficulty):
    prompt = f"""
    Generate 5 SAT {topic} questions ({difficulty})

    Return JSON:
    [
      {{
        "question": "...",
        "options": {{"A":"...","B":"...","C":"...","D":"..."}},
        "answer": "A",
        "explanation": "..."
      }}
    ]
    """

    response = model.generate_content(prompt)
    return json.loads(response.text)