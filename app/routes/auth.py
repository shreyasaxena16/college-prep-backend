from fastapi import APIRouter
from app.services.supabase_client import supabase

router = APIRouter()


@router.post("/signup")
def signup(payload: dict):

    email = payload.get("email")
    password = payload.get("password")
    username = payload.get("username")

    # 1. Create auth user in Supabase
    auth = supabase.auth.sign_up({
        "email": email,
        "password": password
    })

    user = auth.user
    if not user:
        return {"error": "Signup failed"}

    user_id = user.id

    # 2. Create profile row
    supabase.table("profiles").insert({
        "id": user_id,
        "email": email,
        "username": username
    }).execute()

    # 3. Create student row (default)
    supabase.table("students").insert({
        "profile_id": user_id,
        "grade_level": 11
    }).execute()

    return {
        "message": "Signup successful",
        "user_id": user_id
    }

@router.post("/login")
def login(payload: dict):

    email = payload.get("email")
    password = payload.get("password")

    auth = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })

    # 🔴 CRITICAL CHECK
    if not auth.session or not auth.user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "message": "Login successful",
        "user": {
            "id": auth.user.id,
            "email": auth.user.email
        }
    }