# routes.colleges.py

from fastapi import APIRouter
from app.services.supabase_client import get_supabase
supabase = get_supabase()
router = APIRouter()

# GET all colleges
@router.get("/colleges")
def get_colleges():
    supabase = get_supabase()
    res = supabase.table("Colleges").select("*").execute()
    return res.data


# INSERT college
@router.post("/colleges")
def create_college(data: dict):
    supabase = get_supabase()
    res = supabase.table("Colleges").insert(data).execute()
    return res.data