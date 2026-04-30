from fastapi import APIRouter
from app.services.supabase_client import get_supabase
supabase = get_supabase()

router = APIRouter()

#@router.post("/signup")
# def signup(payload: dict):

#     email = payload.get("email")
#     password = payload.get("password")
#     username = payload.get("username")

#     # 1. Create auth user in Supabase
#     auth = supabase.auth.sign_up({
#         "email": email,
#         "password": password
#     })

#     user = auth.user
#     if not user:
#         return {"error": "Signup failed"}

#     user_id = user.id

#     # 2. Create profile row
#     supabase.table("profiles").insert({
#         "id": user_id,
#         "email": email,
#         "username": username
#     }).execute()

#     # 3. Create student row (default)
#     supabase.table("students").insert({
#         "profile_id": user_id,
#         "grade_level": 11
#     }).execute()

#     return {
#         "message": "Signup successful",
#         "user_id": user_id
#     }

@router.post("/signup")
def signup(payload: dict):

    email = payload["email"]
    password = payload["password"]
    first_name = payload["first_name"]
    last_name = payload["last_name"]
    role = payload["role"]

    # 1. Create Supabase Auth user
    auth_response = supabase.auth.sign_up({
        "email": email,
        "password": password
    })

    user = auth_response.user

    if not user:
        return {"error": "Signup failed"}

    user_id = user.id

    # 2. Create profile in your table
    profile = {
        "id": user_id,  # link to auth user
        "firstname": first_name,
        "lastname": last_name,
        "username": f"{first_name}_{last_name}".lower(),
        "role": role
    }

    supabase.table("profiles").upsert(profile).execute()

    return {
        "message": "Signup successful",
        "user": profile
    }

@router.post("/login")
def login(payload: dict):

    email = payload["email"]
    password = payload["password"]

    try:
        auth = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        user = auth.user

        if not user:
            return {"error": "User does not exist. Please sign up"}

        # fetch profile from your table
        profile = supabase.table("profiles") \
            .select("*") \
            .eq("id", user.id) \
            .single() \
            .execute().data

        return {
            "user": profile
        }

    except Exception as e:
        return {
            "error": "User does not exist. Please sign up"
        }
    
@router.post("/debug-signup")
def debug_signup(payload: dict):

    email = payload.get("email")
    password = payload.get("password")

    try:
        print("🔥 DEBUG SIGNUP START")
        print("EMAIL:", email)

        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        print("🔥 RAW RESPONSE:", response)

        return {
            "success": True,
            "response": str(response)
        }

    except Exception as e:
        print("🔥 FULL ERROR:", repr(e))

        return {
            "success": False,
            "error": str(e)
        }