from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import requests

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
            return json.loads(text.strip())
        except:
            pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except:
            pass

    return None


def validate_flashcards(data, expected_count):

    if isinstance(data, dict):
        data = data.get("flashcards")

    if not isinstance(data, list):
        return None

    valid_cards = []

    for item in data:

        if not isinstance(item, dict):
            continue

        question = item.get("question")
        answer = item.get("answer")

        if not question or not answer:
            continue

        valid_cards.append({
            "question": str(question).strip(),
            "answer": str(answer).strip()
        })

    if len(valid_cards) < expected_count:
        return None

    return valid_cards[:expected_count]


def call_ollama(prompt):

    try:

        response = requests.post(
            "http://localhost:11434/api/generate",

            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "format": "json",

                "options": {
                    "temperature": 0.3,
                    "num_ctx": 4096,
                    "num_predict": 3000
                }
            },

            timeout=300
        )

        response.raise_for_status()

        result = response.json()

        return result.get("response", "")

    except requests.exceptions.ConnectionError:

        raise HTTPException(
            status_code=503,
            detail="Ollama is not running."
        )

    except requests.exceptions.Timeout:

        raise HTTPException(
            status_code=504,
            detail="Ollama took too long to respond."
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Ollama error: {str(e)}"
        )


def generate_topic_flashcards(topic, question_count):

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

    raw = call_ollama(prompt)

    data = extract_json(raw)

    cards = validate_flashcards(
        data,
        question_count
    )

    if cards is None:

        raise HTTPException(
            status_code=500,
            detail="Ollama returned invalid flashcard JSON. Please try again."
        )

    return cards


def generate_pdf_flashcards(document_id, topic, question_count):

    if topic and topic.strip():

        results = rag.search_documents(
            query=topic.strip(),
            top_k=8,
            selected_documents=[document_id]
        )

    else:

        results = [
            doc
            for doc in rag.documents
            if doc["document_id"] == document_id
        ]

        results = results[:8]

    if not results:

        raise HTTPException(
            status_code=404,
            detail="No content found in the selected PDF."
        )

    context_parts = []

    for result in results:

        context_parts.append(
            f"Page {result['page']}:\n{result['text']}"
        )

    context = "\n\n".join(context_parts)

    if len(context) > 16000:
        context = context[:16000]

    topic_instruction = (
        topic.strip()
        if topic and topic.strip()
        else "important concepts from this PDF"
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

    raw = call_ollama(prompt)

    data = extract_json(raw)

    cards = validate_flashcards(
        data,
        question_count
    )

    if cards is None:

        raise HTTPException(
            status_code=500,
            detail="Ollama returned invalid PDF flashcard JSON. Please try again."
        )

    return cards


@router.post("/generate")
def generate_flashcards(
    data: FlashcardGenerateRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):

    if data.question_count < 1 or data.question_count > 20:

        raise HTTPException(
            status_code=400,
            detail="Question count must be between 1 and 20."
        )

    if data.mode == "topic":

        if not data.topic or not data.topic.strip():

            raise HTTPException(
                status_code=400,
                detail="Please enter a topic."
            )

        cards = generate_topic_flashcards(
            data.topic,
            data.question_count
        )

        return {
            "flashcards": cards
        }

    elif data.mode == "pdf":

        if not data.document_id:

            raise HTTPException(
                status_code=400,
                detail="Please select a PDF."
            )

        document = (
            db.query(PDFDocument)
            .filter(
                PDFDocument.document_id == data.document_id
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
            "flashcards": cards
        }

    else:

        raise HTTPException(
            status_code=400,
            detail="Invalid flashcard mode."
        )