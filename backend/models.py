from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func

from database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    branch = Column(String(100), nullable=False)
    year = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PDFDocument(Base):
    __tablename__ = "pdf_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(100), unique=True, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    page_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        index=True
    )

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class QuizHistory(Base):
    __tablename__ = "quiz_history"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        index=True
    )

    topic = Column(String(255), nullable=True)
    difficulty = Column(String(50), nullable=True)
    questions = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class FlashcardHistory(Base):
    __tablename__ = "flashcard_history"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        index=True
    )

    topic = Column(String(255), nullable=True)
    filename = Column(String(255), nullable=True)  # PDF se generate hone par filename ke liye
    document_id = Column(String(100), nullable=True)  # Reference ke liye
    flashcards = Column(JSON, nullable=False)  # Text ki jagah JSON use kiya taaki list/dict direct save ho

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class StudyGuideHistory(Base):
    __tablename__ = "study_guide_history"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        index=True
    )

    document_id = Column(
        String(100),
        nullable=False,
        index=True
    )

    filename = Column(String(255), nullable=True)
    language = Column(String(50), nullable=True)
    summary = Column(Text, nullable=False)
    important_questions = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )