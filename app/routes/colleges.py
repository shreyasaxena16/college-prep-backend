# routes.colleges.py

from fastapi import APIRouter
from app.services.supabase_client import supabase

router = APIRouter()

# GET all colleges
@router.get("/colleges")
def get_colleges():
    res = supabase.table("Colleges").select("*").execute()
    return res.data


# INSERT college
@router.post("/colleges")
def create_college(data: dict):
    res = supabase.table("Colleges").insert(data).execute()
    return res.data