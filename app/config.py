import os
from dotenv import load_dotenv
from supabase import create_client
from google import genai

load_dotenv()

# Gemini
def get_gemini_client():
     GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
     print("API KEY:", GEMINI_API_KEY)
     if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY missing")
     return genai.Client(api_key=GEMINI_API_KEY)    


# Supabase factory
def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("Missing Supabase env vars")

    return create_client(url, key)