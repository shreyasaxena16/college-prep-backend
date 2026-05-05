from fastapi import APIRouter, HTTPException
from app.models.review_schemas import ReviewCreate, ReviewResponse
from app.services.review_service import (
    create_review,
    get_all_reviews
)

router = APIRouter()


@router.post("/", response_model=ReviewResponse)
def add_review(payload: ReviewCreate):
    return create_review(payload)


@router.get("/", response_model=list[ReviewResponse])
def fetch_reviews():
    return get_all_reviews()