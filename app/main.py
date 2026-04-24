# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 
from app.routes.colleges import router as college_router
from app.routes.students import router as students_router
from app.routes.subjects import router as subjects_router
from app.routes.grades import router as grades_router
from app.routes.gpa import router as gpa_router
from app.routes.auth import router as auth_router
from app.routes.test import router as test_router



app = FastAPI()
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#app.include_router(college_router, prefix="/api/colleges")
app.include_router(students_router, prefix="/api/students")
app.include_router(subjects_router, prefix="/api/subjects")
app.include_router(grades_router, prefix="/api/grades")
app.include_router(gpa_router, prefix="/api/gpa")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(test_router, prefix="/api/test")

@app.get("/")
def root():
    return {"message": "Backend running"}