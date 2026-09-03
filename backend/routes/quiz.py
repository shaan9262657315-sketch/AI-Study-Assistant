from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
import requests
import re

from database import get_db
from dependencies import get_current_user
from models import Student, PDFDocument
from rag import search_documents
import rag


router = APIRouter(
    prefix="/quiz",
    tags=["Quiz"]
)


# =========================================================
# REQUEST MODEL
# =========================================================

class QuizGenerateRequest(BaseModel):
    mode: str = "topic"
    document_id: Optional[str] = None
    topic: Optional[str] = None
    chapter: Optional[str] = None
    difficulty: str = "medium"
    question_count: int = 5


# =========================================================
# JSON EXTRACTION
# =========================================================

def extract_json(text: str):

    if not text:
        return None

    text = text.strip()

    # -----------------------------------------------------
    # Direct JSON
    # -----------------------------------------------------

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # -----------------------------------------------------
    # Remove markdown code fences
    # -----------------------------------------------------

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```",
        "",
        text
    ).strip()

    # -----------------------------------------------------
    # Try again
    # -----------------------------------------------------

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # -----------------------------------------------------
    # Find JSON object
    # -----------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:

        json_text = text[start:end + 1]

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    # -----------------------------------------------------
    # Find JSON array
    # -----------------------------------------------------

    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end != -1 and end > start:

        json_text = text[start:end + 1]

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    return None


# =========================================================
# VALIDATE QUESTIONS
# =========================================================

def validate_questions(data, expected_count):

    if not isinstance(data, list):
        return None

    valid_questions = []

    for item in data:

        if not isinstance(item, dict):
            continue

        question = item.get("question")
        options = item.get("options")
        correct_answer = item.get("correct_answer")
        explanation = item.get("explanation")

        # -------------------------------------------------
        # Question check
        # -------------------------------------------------

        if not question:
            continue

        # -------------------------------------------------
        # Options check
        # -------------------------------------------------

        if not isinstance(options, list):
            continue

        if len(options) != 4:
            continue

        # Remove empty options
        options = [
            str(option).strip()
            for option in options
            if str(option).strip()
        ]

        if len(options) != 4:
            continue

        # Make sure options are different
        if len(set(options)) != 4:
            continue

        # -------------------------------------------------
        # Correct answer check
        # -------------------------------------------------

        if not correct_answer:
            continue

        correct_answer = str(correct_answer).strip()

        if correct_answer not in options:
            continue

        # -------------------------------------------------
        # Explanation
        # -------------------------------------------------

        if not explanation:

            explanation = "Explanation not provided."

        explanation = str(explanation).strip()

        valid_questions.append({
            "question": str(question).strip(),
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation
        })

    # -----------------------------------------------------
    # Need requested number
    # -----------------------------------------------------

    if len(valid_questions) < expected_count:
        return None

    return valid_questions[:expected_count]


# =========================================================
# DIFFICULTY INSTRUCTION
# =========================================================

def get_difficulty_instruction(difficulty: str):

    difficulty = difficulty.lower().strip()

    if difficulty == "easy":

        return """
DIFFICULTY: EASY

Create beginner-friendly questions.

Focus mainly on:
- Direct definitions
- Basic facts
- Simple concept recognition
- Basic formulas if present
- Direct understanding of the PDF

Avoid:
- Multi-step reasoning
- Tricky questions
- Combining many concepts
- Very indirect questions

A student who has read the PDF once should be able
to solve most questions.
"""

    elif difficulty == "hard":

        return """
DIFFICULTY: HARD

Create challenging exam-level questions.

Focus mainly on:
- Deep conceptual understanding
- Relationship between concepts
- Application of concepts
- Comparing closely related concepts
- Multi-concept reasoning
- Questions where the student must carefully analyze
  the information before selecting the answer

Avoid simple definition-only questions.

The correct answer should require genuine understanding
of the PDF rather than simple keyword matching.

Do NOT create impossible or outside-syllabus questions.
Everything must still be supported by the PDF.
"""

    # -----------------------------------------------------
    # MEDIUM
    # -----------------------------------------------------

    return """
DIFFICULTY: MEDIUM

Create moderate exam-level questions.

Focus mainly on:
- Conceptual understanding
- Applying a concept to a simple situation
- Comparing concepts
- Understanding why something happens
- Moderate reasoning
- Important formulas and their application

Avoid questions that are merely direct definitions.

The student should understand the topic,
not just memorize a sentence.
"""


# =========================================================
# OLLAMA
# =========================================================

def call_ollama(
    prompt: str,
    difficulty: str = "medium"
):

    difficulty = difficulty.lower().strip()

    # Different temperature for different difficulty
    if difficulty == "easy":
        temperature = 0.2

    elif difficulty == "hard":
        temperature = 0.65

    else:
        temperature = 0.4

    try:

        response = requests.post(
            "http://localhost:11434/api/generate",

            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,

                # Ask Ollama for JSON
                "format": "json",

                "options": {
                    "temperature": temperature,
                    "num_ctx": 4096,
                    "num_predict": 3500
                }
            },

            # Increased from 180 sec
            timeout=300
        )

        response.raise_for_status()

        result = response.json()

        answer = result.get("response", "")

        if not answer:
            raise HTTPException(
                status_code=500,
                detail="Ollama returned an empty response."
            )

        return answer

    except requests.exceptions.ConnectionError:

        raise HTTPException(
            status_code=503,
            detail="Ollama is not running."
        )

    except requests.exceptions.Timeout:

        raise HTTPException(
            status_code=504,
            detail="Ollama took too long to generate the quiz."
        )

    except requests.exceptions.RequestException as e:

        raise HTTPException(
            status_code=500,
            detail=f"Ollama request failed: {str(e)}"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Ollama error: {str(e)}"
        )


# =========================================================
# TOPIC QUIZ
# =========================================================

def generate_topic_quiz(
    topic,
    difficulty,
    question_count
):

    difficulty_instruction = get_difficulty_instruction(
        difficulty
    )

    prompt = f"""
You are an AI Study Assistant.

Create a multiple-choice quiz.

TOPIC:
{topic}

DIFFICULTY:
{difficulty}

NUMBER OF QUESTIONS:
{question_count}

{difficulty_instruction}

================================================
IMPORTANT RULES
================================================

1. Generate exactly {question_count} questions.

2. Every question must have exactly 4 options.

3. There must be exactly ONE correct answer.

4. correct_answer must exactly match
   one of the four options.

5. Do not repeat the same question.

6. Do not create two questions testing
   exactly the same concept.

7. Questions must genuinely match
   the requested difficulty.

8. Use general knowledge because this is
   a Topic Quiz.

9. Keep explanations short and useful.

10. Return ONLY valid JSON.

11. Do not use markdown.

12. Do not use code fences.

13. Do not write anything outside JSON.

================================================
JSON FORMAT
================================================

{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_answer": "Exactly one option text",
      "explanation": "Short explanation"
    }}
  ]
}}
"""

    raw = call_ollama(
        prompt,
        difficulty
    )

    data = extract_json(raw)

    if isinstance(data, dict):

        data = data.get("questions")

    questions = validate_questions(
        data,
        question_count
    )

    if questions is None:

        raise HTTPException(
            status_code=500,
            detail="Ollama returned invalid quiz JSON. Please try again."
        )

    return questions


# =========================================================
# GET PDF CONTENT
# =========================================================

def get_pdf_quiz_context(
    document_id,
    topic
):

    # -----------------------------------------------------
    # If topic is provided
    # -----------------------------------------------------

    if topic and topic.strip():

        results = search_documents(
            query=topic.strip(),
            top_k=6,
            selected_documents=[document_id]
        )

    # -----------------------------------------------------
    # No topic
    # -----------------------------------------------------

    else:

        results = [
            doc
            for doc in rag.documents
            if doc.get("document_id") == document_id
        ]

        # Maximum 6 chunks
        results = results[:6]

    if not results:

        raise HTTPException(
            status_code=404,
            detail="No content found in the selected PDF."
        )

    context_parts = []

    for result in results:

        text = result.get("text", "").strip()

        if not text:
            continue

        page = result.get("page", "Unknown")

        context_parts.append(
            f"Page {page}:\n{text}"
        )

    context = "\n\n".join(context_parts)

    if not context.strip():

        raise HTTPException(
            status_code=404,
            detail="No readable content found in the selected PDF."
        )

    # -----------------------------------------------------
    # HARD LIMIT
    # -----------------------------------------------------

    # Keep prompt small enough for llama3.2:3b
    if len(context) > 18000:

        context = context[:18000]

    return context


# =========================================================
# PDF QUIZ
# =========================================================

def generate_pdf_quiz(
    document_id,
    topic,
    difficulty,
    question_count
):

    context = get_pdf_quiz_context(
        document_id,
        topic
    )

    difficulty_instruction = get_difficulty_instruction(
        difficulty
    )

    topic_instruction = (
        topic.strip()
        if topic and topic.strip()
        else "the important concepts covered in the PDF"
    )

    prompt = f"""
You are an AI Study Assistant.

Create a multiple-choice quiz using ONLY
the PDF content provided below.

================================================
QUIZ INFORMATION
================================================

Quiz Topic:
{topic_instruction}

Difficulty:
{difficulty}

Number of Questions:
{question_count}

{difficulty_instruction}

================================================
SOURCE RULE
================================================

VERY IMPORTANT:

Use ONLY the information contained
in the PDF content below.

Do NOT use outside knowledge.

Do NOT invent facts.

Do NOT create questions about information
that is not present in the PDF.

================================================
QUESTION RULES
================================================

1. Generate exactly {question_count} questions.

2. Every question must have exactly 4 options.

3. There must be exactly ONE correct answer.

4. correct_answer must exactly match
   one option.

5. Do not repeat questions.

6. Do not ask the same concept repeatedly.

7. Make the questions genuinely match
   the requested difficulty.

8. Keep all questions relevant to:
   {topic_instruction}

9. Explanations must be based only
   on the PDF.

================================================
OUTPUT
================================================

Return ONLY valid JSON.

No markdown.

No code fences.

No text before JSON.

No text after JSON.

Use exactly this structure:

{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_answer": "Option A",
      "explanation": "Explanation based on PDF"
    }}
  ]
}}

================================================
PDF CONTENT
================================================

{context}
"""

    raw = call_ollama(
        prompt,
        difficulty
    )

    data = extract_json(raw)

    if isinstance(data, dict):

        data = data.get("questions")

    questions = validate_questions(
        data,
        question_count
    )

    if questions is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "Ollama returned invalid PDF quiz JSON. "
                "Please try again."
            )
        )

    return questions


# =========================================================
# API
# =========================================================

@router.post("/generate")
def generate_quiz(
    data: QuizGenerateRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):

    # =====================================================
    # QUESTION COUNT
    # =====================================================

    if data.question_count < 1:

        raise HTTPException(
            status_code=400,
            detail="Question count must be at least 1."
        )

    if data.question_count > 20:

        raise HTTPException(
            status_code=400,
            detail="Question count cannot exceed 20."
        )

    # =====================================================
    # DIFFICULTY
    # =====================================================

    difficulty = data.difficulty.lower().strip()

    if difficulty not in [
        "easy",
        "medium",
        "hard"
    ]:

        difficulty = "medium"

    # =====================================================
    # TOPIC QUIZ
    # =====================================================

    if data.mode == "topic":

        if not data.topic or not data.topic.strip():

            raise HTTPException(
                status_code=400,
                detail="Please enter a topic."
            )

        questions = generate_topic_quiz(
            data.topic.strip(),
            difficulty,
            data.question_count
        )

        return {
            "questions": questions,
            "difficulty": difficulty
        }

    # =====================================================
    # PDF QUIZ
    # =====================================================

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

        questions = generate_pdf_quiz(
            data.document_id,
            data.topic,
            difficulty,
            data.question_count
        )

        return {
            "questions": questions,
            "difficulty": difficulty
        }

    # =====================================================
    # INVALID MODE
    # =====================================================

    else:

        raise HTTPException(
            status_code=400,
            detail="Invalid quiz mode."
        )