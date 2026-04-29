# main.py

print("🔥 MAIN STARTED")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 
from app.routes.colleges import router as college_router
from app.routes.students import router as students_router
from app.routes.subjects import router as subjects_router
from app.routes.grades import router as grades_router
from app.routes.gpa import router as gpa_router
from app.routes.auth import router as auth_router
from app.routes.test import router as test_router
from app.routes.admin import router as admin_router
from app.routes.questions import router as questions_router



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


try:
    app.include_router(college_router, prefix="/api/colleges")
    print("✔ colleges imported", flush=True)
except Exception as e:
    print("❌ colleges import failed:", e, flush=True)
    raise
try:    
    app.include_router(students_router, prefix="/api/students")
    print("✔ students imported", flush=True)
except Exception as e:
    print("❌ students import failed:", e, flush=True)
    raise
try:    
    app.include_router(subjects_router, prefix="/api/subjects")
    print("✔ subjects imported", flush=True)
except Exception as e:
    print("❌ subjects import failed:", e, flush=True)
    raise
try:    
    app.include_router(grades_router, prefix="/api/grades")
    print("✔ grades imported", flush=True)
except Exception as e:
    print("❌ grades import failed:", e, flush=True)
    raise
try:    
    app.include_router(gpa_router, prefix="/api/gpa")
    print("✔ gpa imported", flush=True)
except Exception as e:
    print("❌ gpa import failed:", e, flush=True)
    raise    
try:
    app.include_router(auth_router, prefix="/api/auth")
    print("✔ auth imported", flush=True)
except Exception as e:
    print("❌ auth import failed:", e, flush=True)
    raise    
try:
    app.include_router(test_router, prefix="/api/test")
    print("✔ test imported", flush=True)
except Exception as e:
    print("❌ test import failed:", e, flush=True)
    raise    
try:
    app.include_router(admin_router, prefix="/api/admin")
    print("✔ admin imported", flush=True)
except Exception as e:
    print("❌ admin import failed:", e, flush=True)
    raise    
try:
    app.include_router(questions_router, prefix="/api/questions")
    print("✔ questions imported", flush=True)
except Exception as e:
    print("❌ questions import failed:", e, flush=True)
    raise    

@app.get("/")
def root():
    return {"message": "Backend running"}