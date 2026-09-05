from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# =========================================================
# STUDENT
# =========================================================

class StudentCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    branch: str
    year: Optional[int] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    branch: Optional[str] = None
    year: Optional[int] = None


class StudentResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    branch: str
    year: Optional[int]

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# AUTHENTICATION
# =========================================================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    branch: str
    year: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


# =========================================================
# PDF
# =========================================================

class PDFLibraryResponse(BaseModel):
    document_id: str
    filename: str
    page_count: int
    uploaded_at: Optional[str] = None


class RetrievedSource(BaseModel):
    document_id: str
    filename: str
    page: int
    text: str
    score: float


class PDFAskRequest(BaseModel):
    question: str
    mode: str = "pdf_gemini"
    language: str = "english"
    selected_documents: Optional[List[str]] = None
    top_k: int = 5


class PDFAskResponse(BaseModel):
    answer: str
    sources: List[RetrievedSource]


# =========================================================
# STUDY GUIDE
# =========================================================

class StudyGuideRequest(BaseModel):
    document_id: str
    question_count: int = 5
    language: str = "english"


# =========================================================
# QUIZ
# =========================================================

class QuizGenerateRequest(BaseModel):
    mode: str = "pdf"
    document_id: Optional[str] = None
    topic: Optional[str] = None
    chapter: Optional[str] = None
    difficulty: str = "medium"
    question_count: int = 5


class QuizOption(BaseModel):
    text: str


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    questions: List[QuizQuestion]