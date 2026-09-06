from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine, SessionLocal
from models import PDFDocument, FlashcardHistory
from rag import load_existing_pdfs

from routes.auth import router as auth_router
from routes.student import router as student_router
from routes.pdf import router as pdf_router
from routes.chat import router as chat_router
from routes.quiz import router as quiz_router
from routes.study import router as study_router
from routes.flashcards import router as flashcards_router


app = FastAPI(
    title="AI Study Assistant"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ai-study-assistant-frontend-u7wu.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)


db = SessionLocal()

try:
    pdf_records = db.query(PDFDocument).all()
    load_existing_pdfs(pdf_records)
finally:
    db.close()


app.include_router(auth_router)
app.include_router(student_router)
app.include_router(pdf_router)
app.include_router(chat_router)
app.include_router(quiz_router)
app.include_router(study_router)
app.include_router(flashcards_router)


@app.get("/")
def root():
    return {
        "message": "AI Study Assistant Backend is running"
    }
