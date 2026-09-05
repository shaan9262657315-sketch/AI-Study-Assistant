from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import time
import rag
from dependencies import get_current_user
from models import Student, PDFDocument
from database import get_db
from sqlalchemy.orm import Session


router = APIRouter(
    prefix="/flashcards",
    tags=["Flashcards"]
)


class FlashcardGenerateRequest(BaseModel):
    mode: str = "topic"
    topic: Optional[str] = None
    document_id: Optional[str] = None
    question_count: int = 10


def extract_json(text: str):

    text = text.strip()

    try:
        return json.loads(text)
    except:
        pass

    if "```json" in text:

        try:
            text = text.split("```json", 1)[1]
            text = text.split("```", 1)[0]

            return json.loads(
                text.strip()
            )

        except:
            pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:

        try:
            return json.loads(
                text[start:end + 1]
            )

        except:
            pass

    return None


def validate_flashcards(
    data,
    expected_count
):

    if isinstance(data, dict):

        data = data.get(
            "flashcards"
        )

    if not isinstance(data, list):

        return None

    valid_cards = []

    for item in data:

        if not isinstance(item, dict):

            continue

        question = item.get(
            "question"
        )

        answer = item.get(
            "answer"
        )

        if not question or not answer:

            continue

        valid_cards.append({

            "question":
                str(question).strip(),

            "answer":
                str(answer).strip()

        })

    if len(valid_cards) < expected_count:

        return None

    return valid_cards[:expected_count]


# =========================================================
# GEMINI
# =========================================================
import time

def call_gemini(prompt):

    if not getattr(rag, "gemini_client", None):

        raise HTTPException(
            status_code=503,
            detail="Gemini is not configured. Check GEMINI_API_KEY."
        )

    max_retries = 3
    delays = [2, 5, 10]

    for attempt in range(max_retries):

        try:

            response = (
                rag.gemini_client
                .models
                .generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json"
                    }
                )
            )

            answer = getattr(
                response,
                "text",
                None
            )

            if not answer:

                raise HTTPException(
                    status_code=500,
                    detail="Gemini returned an empty response."
                )

            return answer

        except HTTPException:
            raise

        except Exception as e:

            error_text = str(e)

            print(
                f"Gemini Flashcard attempt "
                f"{attempt + 1}/{max_retries} failed:",
                error_text
            )

            if (
                "503" in error_text
                or "UNAVAILABLE" in error_text
            ):

                if attempt < max_retries - 1:

                    time.sleep(
                        delays[attempt]
                    )

                    continue

            raise HTTPException(
                status_code=500,
                detail=f"Gemini error: {error_text}"
            )

# =========================================================
# TOPIC FLASHCARDS
# =========================================================

def generate_topic_flashcards(
    topic,
    question_count
):

    prompt = f"""
You are an AI Study Assistant.

Generate {question_count} educational flashcards about:

Topic: {topic}

Return ONLY valid JSON.

Use this exact structure:

{{
    "flashcards": [
        {{
            "question": "Question",
            "answer": "Clear answer"
        }}
    ]
}}

Rules:

1. Generate exactly {question_count} flashcards.
2. Questions must test important concepts.
3. Answers must be clear and educational.
4. Keep answers concise.
5. Do not use markdown.
6. Do not add text outside JSON.
7. Do not use code fences.
8. Avoid duplicate questions.
"""

    raw = call_gemini(
        prompt
    )

    data = extract_json(
        raw
    )

    cards = validate_flashcards(
        data,
        question_count
    )

    if cards is None:

        raise HTTPException(

            status_code=500,

            detail=(
                "Gemini returned invalid "
                "flashcard JSON. Please try again."
            )

        )

    return cards


# =========================================================
# PDF FLASHCARDS
# =========================================================

def generate_pdf_flashcards(
    document_id,
    topic,
    question_count
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

            if doc["document_id"]
            == document_id

        ]

        results = results[:8]

    if not results:

        raise HTTPException(

            status_code=404,

            detail=(
                "No content found in "
                "the selected PDF."
            )

        )

    context_parts = []

    for result in results:

        context_parts.append(

            f"Page {result['page']}:\n"
            f"{result['text']}"

        )

    context = "\n\n".join(
        context_parts
    )

    if len(context) > 16000:

        context = context[:16000]

    topic_instruction = (

        topic.strip()

        if topic
        and topic.strip()

        else
        "important concepts from this PDF"

    )

    prompt = f"""
You are an AI Study Assistant.

Create {question_count} study flashcards.

Topic:
{topic_instruction}

IMPORTANT:

Use ONLY the information provided in the PDF.

Do NOT use outside knowledge.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "flashcards": [
        {{
            "question": "Question",
            "answer": "Answer based only on PDF"
        }}
    ]
}}

Rules:

1. Generate exactly {question_count} flashcards.
2. Questions should test important concepts.
3. Answers must come ONLY from the PDF.
4. Keep answers clear and concise.
5. Do not create duplicate questions.
6. Do not use markdown.
7. Do not use code fences.
8. Do not write anything outside JSON.

PDF CONTENT:

{context}
"""

    raw = call_gemini(
        prompt
    )

    data = extract_json(
        raw
    )

    cards = validate_flashcards(
        data,
        question_count
    )

    if cards is None:

        raise HTTPException(

            status_code=500,

            detail=(
                "Gemini returned invalid "
                "PDF flashcard JSON. Please try again."
            )

        )

    return cards


# =========================================================
# API
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
        or data.question_count > 20
    ):

        raise HTTPException(

            status_code=400,

            detail=(
                "Question count must be "
                "between 1 and 20."
            )

        )

    mode = (
        data.mode
        .lower()
        .strip()
    )

    # -----------------------------------------------------
    # TOPIC
    # -----------------------------------------------------

    if mode == "topic":

        if (
            not data.topic
            or not data.topic.strip()
        ):

            raise HTTPException(

                status_code=400,

                detail="Please enter a topic."

            )

        cards = generate_topic_flashcards(

            data.topic,

            data.question_count

        )

        return {

            "flashcards": cards,

            "provider": "gemini"

        }

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    elif mode == "pdf":

        if not data.document_id:

            raise HTTPException(

                status_code=400,

                detail="Please select a PDF."

            )

        document = (

            db.query(
                PDFDocument
            )

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

            data.document_id,

            data.topic,

            data.question_count

        )

        return {

            "flashcards": cards,

            "provider": "gemini"

        }

    else:

        raise HTTPException(

            status_code=400,

            detail="Invalid flashcard mode."

        )




