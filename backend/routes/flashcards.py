from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import re

import rag

from dependencies import get_current_user
from models import Student, PDFDocument, FlashcardHistory
from database import get_db
from sqlalchemy.orm import Session


router = APIRouter(
    prefix="/flashcards",
    tags=["Flashcards"]
)


# =========================================================
# CONFIG
# =========================================================

MAX_FLASHCARD_COUNT = 20
DEFAULT_FLASHCARD_COUNT = 10
MAX_TOPIC_LENGTH = 300
MAX_PDF_CONTEXT_LENGTH = 16000


# =========================================================
# REQUEST MODEL
# =========================================================

class FlashcardGenerateRequest(BaseModel):
    mode: str = "topic"
    topic: Optional[str] = None
    document_id: Optional[str] = None
    question_count: int = DEFAULT_FLASHCARD_COUNT


# =========================================================
# JSON EXTRACTION
# =========================================================

def extract_json(text: str):

    if not text:
        return None

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(
        r"```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"```\s*",
        "",
        cleaned
    ).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):
        json_text = cleaned[
            start:end + 1
        ]

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    return None


# =========================================================
# VALIDATE FLASHCARDS
# =========================================================

def validate_flashcards(
    data,
    expected_count: int
):

    if not isinstance(data, dict):
        return None

    cards = data.get("flashcards")

    if not isinstance(cards, list):
        return None

    valid_cards = []
    seen_questions = set()

    for item in cards:

        if not isinstance(item, dict):
            continue

        question = item.get("question")
        answer = item.get("answer")

        if question is None or answer is None:
            continue

        question = str(question).strip()
        answer = str(answer).strip()

        if not question or not answer:
            continue

        question_key = re.sub(
            r"\s+",
            " ",
            question.lower()
        )

        if question_key in seen_questions:
            continue

        seen_questions.add(
            question_key
        )

        valid_cards.append({
            "question": question,
            "answer": answer
        })

    if len(valid_cards) < expected_count:
        return None

    return valid_cards[:expected_count]


# =========================================================
# UNIFIED AI PROVIDER
# =========================================================

def call_ai(prompt: str):

    return rag.generate_answer(
        question=prompt,
        context="",
        language="english",
        outside_knowledge=True
    )


# =========================================================
# TOPIC FLASHCARDS
# =========================================================

def generate_topic_flashcards(
    topic: str,
    question_count: int
):

    prompt = f"""
You are an expert university-level AI Study Assistant.

Create exactly {question_count} high-quality study flashcards
about the following topic:

TOPIC:
{topic}

================================================
FLASHCARD QUALITY
================================================

Flashcards should help a student actually understand
and revise the topic.

Prefer questions about:

- important concepts
- definitions
- differences
- relationships
- working/mechanisms
- applications
- important properties
- advantages/disadvantages
- examples
- exam-relevant facts

Whenever possible, test understanding rather than
simple memorisation.

================================================
STRICT RULES
================================================

1. Generate exactly {question_count} flashcards.

2. Every flashcard must contain:
   - question
   - answer

3. Questions must be different.

4. Do not ask the same concept repeatedly.

5. Avoid trivial questions.

6. Answers must be concise but educational.

7. Do not include unnecessary introductions.

8. Do not include markdown.

9. Do not include code fences.

10. Return ONLY valid JSON.

================================================
JSON FORMAT
================================================

{{
    "flashcards": [
        {{
            "question": "Question text",
            "answer": "Clear educational answer"
        }}
    ]
}}

================================================
FINAL REQUIREMENT
================================================

Return exactly {question_count} flashcards.
"""

    raw = call_ai(prompt)
    data = extract_json(raw)
    cards = validate_flashcards(data, question_count)

    if cards is None:
        retry_prompt = f"""
Return ONLY valid JSON.

Generate exactly {question_count}
unique educational flashcards about:

{topic}

Each flashcard MUST contain:
question
answer

Rules:
- exactly {question_count} flashcards
- no duplicate questions
- answers must be useful for students
- no markdown
- no code fences
- no extra text

Use exactly this structure:
{{
    "flashcards": [
        {{
            "question": "Question",
            "answer": "Answer"
        }}
    ]
}}
"""
        raw = call_ai(retry_prompt)
        data = extract_json(raw)
        cards = validate_flashcards(data, question_count)

    if cards is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "AI returned invalid flashcard data. "
                "Please try again."
            )
        )

    return cards


# =========================================================
# PDF FLASHCARDS
# =========================================================

def generate_pdf_flashcards(
    document_id: str,
    topic: Optional[str],
    question_count: int
):

    if topic and topic.strip():
        results = rag.search_documents(
            query=topic.strip(),
            top_k=8,
            selected_documents=[
                document_id
            ]
        )
    else:
        results = [
            doc
            for doc in rag.documents
            if doc.get("document_id") == document_id
        ]
        results = results[:8]

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No content found in the selected PDF."
        )

    context_parts = []

    for result in results:
        page = result.get("page", "Unknown")
        text = result.get("text", "").strip()

        if not text:
            continue

        context_parts.append(
            f"[Page {page}]\n{text}"
        )

    if not context_parts:
        raise HTTPException(
            status_code=404,
            detail="No readable content found in the selected PDF."
        )

    context = "\n\n".join(context_parts)

    if len(context) > MAX_PDF_CONTEXT_LENGTH:
        context = context[:MAX_PDF_CONTEXT_LENGTH]

    topic_instruction = (
        topic.strip()
        if topic and topic.strip()
        else "important concepts from the PDF"
    )

    prompt = f"""
You are an expert university AI Study Assistant.

Create exactly {question_count} study flashcards
from the supplied PDF content.

================================================
STRICT SOURCE RULE
================================================

You MUST use ONLY the supplied PDF content.
Do NOT use outside knowledge.
Do NOT invent information.

================================================
TOPIC
================================================

{topic_instruction}

================================================
FLASHCARD QUALITY
================================================

Create useful exam-oriented flashcards from the text.

================================================
STRICT RULES
================================================

1. Exactly {question_count} flashcards.
2. Every card must contain question and answer.
3. Questions must be unique.
4. Return ONLY valid JSON.
5. No markdown or code fences.

================================================
JSON FORMAT
================================================

{{
    "flashcards": [
        {{
            "question": "Question based on PDF",
            "answer": "Answer supported by PDF"
        }}
    ]
}}

================================================
PDF CONTENT
================================================

{context}
"""

    raw = call_ai(prompt)
    data = extract_json(raw)
    cards = validate_flashcards(data, question_count)

    if cards is None:
        retry_prompt = f"""
Return ONLY valid JSON.
Create exactly {question_count} unique flashcards using ONLY the PDF content below.
Format:
{{
    "flashcards": [
        {{
            "question": "Question",
            "answer": "Answer from PDF"
        }}
    ]
}}

PDF CONTENT:
{context}
"""
        raw = call_ai(retry_prompt)
        data = extract_json(raw)
        cards = validate_flashcards(data, question_count)

    if cards is None:
        raise HTTPException(
            status_code=500,
            detail="AI returned invalid PDF flashcard data. Please try again."
        )

    return cards


# =========================================================
# LIBRARY ENDPOINTS (HISTORY SAVING & RETRIEVAL)
# =========================================================

@router.get("/library")
def get_flashcard_library(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    history_items = (
        db.query(FlashcardHistory)
        .filter(FlashcardHistory.user_id == current_user.id)
        .all()
    )
    
    result = []
    for item in history_items:
        result.append({
            "id": item.id,
            "mode": "pdf" if item.document_id else "topic",
            "topic": item.topic,
            "filename": item.filename,
            "document_id": item.document_id,
            "flashcards": item.flashcards,
            "created_at": item.created_at
        })
    return result


@router.delete("/library/{history_id}")
def delete_flashcard_set(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    item = (
        db.query(FlashcardHistory)
        .filter(
            FlashcardHistory.id == history_id,
            FlashcardHistory.user_id == current_user.id
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Flashcard set not found."
        )

    db.delete(item)
    db.commit()
    return {"message": "Flashcard set deleted successfully."}


# =========================================================
# API ENDPOINT (GENERATE & SAVE)
# =========================================================

@router.post("/generate")
def generate_flashcards(
    data: FlashcardGenerateRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(
        get_current_user
    )
):

    if (
        data.question_count < 1
        or
        data.question_count > MAX_FLASHCARD_COUNT
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Question count must be between 1 and {MAX_FLASHCARD_COUNT}."
        )

    mode = data.mode.lower().strip()

    if mode == "topic":
        if not data.topic or not data.topic.strip():
            raise HTTPException(
            status_code=400,
            detail="Please enter a topic."
        )

        topic = data.topic.strip()

        if len(topic) > MAX_TOPIC_LENGTH:
            raise HTTPException(
                status_code=400,
                detail="Topic is too long."
            )

        cards = generate_topic_flashcards(
            topic=topic,
            question_count=data.question_count
        )

        history_entry = FlashcardHistory(
            user_id=current_user.id,
            topic=topic,
            flashcards=cards
        )
        db.add(history_entry)
        db.commit()
        db.refresh(history_entry)

        return {
            "id": history_entry.id,
            "mode": "topic",
            "topic": topic,
            "flashcards": cards
        }

    if mode == "pdf":
        if not data.document_id:
            raise HTTPException(
                status_code=400,
                detail="Please select a PDF."
            )

        document = (
            db.query(PDFDocument)
            .filter(
                PDFDocument.document_id
                == data.document_id
            )
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail="PDF not found."
            )

        cards = generate_pdf_flashcards(
            document_id=data.document_id,
            topic=data.topic,
            question_count=data.question_count
        )

        set_title = data.topic.strip() if data.topic else document.filename

        history_entry = FlashcardHistory(
            user_id=current_user.id,
            topic=set_title,
            filename=document.filename,
            document_id=data.document_id,
            flashcards=cards
        )
        db.add(history_entry)
        db.commit()
        db.refresh(history_entry)

        return {
            "id": history_entry.id,
            "mode": "pdf",
            "document_id": data.document_id,
            "filename": document.filename,
            "flashcards": cards
        }

    raise HTTPException(
        status_code=400,
        detail="Invalid flashcard mode. Use 'topic' or 'pdf'."
    )