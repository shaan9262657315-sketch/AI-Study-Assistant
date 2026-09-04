from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

import json
import requests
import re

import rag

from database import get_db
from dependencies import get_current_user
from models import Student, PDFDocument
from rag import search_documents


router = APIRouter(
    prefix="/quiz",
    tags=["Quiz"]
)


# =========================================================
# CONFIG
# =========================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"

GEMINI_MODEL = "gemini-3.6-flash"


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
        r"```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```\s*",
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

    # -----------------------------------------------------
    # Accept dictionary format
    # -----------------------------------------------------

    if isinstance(data, dict):

        data = data.get("questions")

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
        # Question
        # -------------------------------------------------

        if not question:

            continue

        question = str(question).strip()

        if not question:

            continue

        # -------------------------------------------------
        # Options
        # -------------------------------------------------

        if not isinstance(options, list):

            continue

        if len(options) != 4:

            continue

        cleaned_options = []

        for option in options:

            if option is None:

                continue

            option = str(option).strip()

            if option:

                cleaned_options.append(option)

        if len(cleaned_options) != 4:

            continue

        # -------------------------------------------------
        # Options must be different
        # -------------------------------------------------

        if len(set(cleaned_options)) != 4:

            continue

        # -------------------------------------------------
        # Correct answer
        # -------------------------------------------------

        if correct_answer is None:

            continue

        correct_answer = str(
            correct_answer
        ).strip()

        # -------------------------------------------------
        # Sometimes AI returns A/B/C/D
        # -------------------------------------------------

        if correct_answer.upper() in ["A", "B", "C", "D"]:

            index = ord(
                correct_answer.upper()
            ) - ord("A")

            correct_answer = cleaned_options[index]

        # -------------------------------------------------
        # Correct answer must exist
        # -------------------------------------------------

        if correct_answer not in cleaned_options:

            continue

        # -------------------------------------------------
        # Explanation
        # -------------------------------------------------

        if not explanation:

            explanation = (
                "Explanation not provided."
            )

        explanation = str(
            explanation
        ).strip()

        valid_questions.append({

            "question": question,

            "options": cleaned_options,

            "correct_answer": correct_answer,

            "explanation": explanation

        })

    # -----------------------------------------------------
    # Need requested count
    # -----------------------------------------------------

    if len(valid_questions) < expected_count:

        return None

    return valid_questions[:expected_count]


# =========================================================
# DIFFICULTY
# =========================================================

def get_difficulty_instruction(
    difficulty: str
):

    difficulty = difficulty.lower().strip()

    # -----------------------------------------------------
    # EASY
    # -----------------------------------------------------

    if difficulty == "easy":

        return """
DIFFICULTY: EASY

Create beginner-friendly questions.

Focus on:
- Basic definitions
- Direct facts
- Simple concept recognition
- Basic understanding
- Simple examples

Avoid:
- Complex reasoning
- Multi-step reasoning
- Tricky questions
- Multiple concepts in one question

Questions should be easy for a student
who has read the PDF once.
"""

    # -----------------------------------------------------
    # HARD
    # -----------------------------------------------------

    if difficulty == "hard":

        return """
DIFFICULTY: HARD

Create challenging exam-level questions.

Focus on:
- Deep conceptual understanding
- Application
- Comparison
- Relationships between concepts
- Multi-step reasoning
- Conceptual analysis

Avoid:
- Simple definition-only questions

Do not create questions outside the PDF.
Every question must still be answerable
from the supplied PDF context.
"""

    # -----------------------------------------------------
    # MEDIUM
    # -----------------------------------------------------

    return """
DIFFICULTY: MEDIUM

Create moderate exam-level questions.

Focus on:
- Conceptual understanding
- Simple application
- Comparing concepts
- Understanding why something happens
- Important formulas
- Moderate reasoning

Avoid questions that are only
simple definition memorization.

Questions should test understanding.
"""


# =========================================================
# OLLAMA CALL
# =========================================================

def call_ollama(
    prompt: str,
    difficulty: str = "medium"
):

    difficulty = difficulty.lower().strip()

    if difficulty == "easy":

        temperature = 0.2

    elif difficulty == "hard":

        temperature = 0.5

    else:

        temperature = 0.3

    try:

        response = requests.post(

            OLLAMA_URL,

            json={

                "model": OLLAMA_MODEL,

                "prompt": prompt,

                "stream": False,

                "format": "json",

                "options": {

                    "temperature": temperature,

                    "num_ctx": 8192,

                    "num_predict": 5000

                }

            },

            timeout=300

        )

        response.raise_for_status()

        result = response.json()

        answer = result.get(
            "response",
            ""
        )

        if not answer:

            raise HTTPException(

                status_code=500,

                detail=(
                    "Ollama returned an empty response."
                )

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

            detail=(
                "Ollama took too long to generate the quiz."
            )

        )

    except requests.exceptions.RequestException as e:

        raise HTTPException(

            status_code=500,

            detail=(
                f"Ollama request failed: {str(e)}"
            )

        )

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=f"Ollama error: {str(e)}"

        )


# =========================================================
# GEMINI CALL
# =========================================================

def call_gemini(
    prompt: str,
    difficulty: str = "medium"
):

    # -----------------------------------------------------
    # Check Gemini client
    # -----------------------------------------------------

    if not getattr(
        rag,
        "gemini_client",
        None
    ):

        raise HTTPException(

            status_code=503,

            detail=(
                "Gemini is not configured. "
                "Check GEMINI_API_KEY."
            )

        )

    try:

        response = rag.gemini_client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt,

            config={

                "temperature": 0.2,

                "response_mime_type": "application/json"

            }

        )

        # -------------------------------------------------
        # Gemini response text
        # -------------------------------------------------

        answer = getattr(
            response,
            "text",
            None
        )

        if not answer:

            raise HTTPException(

                status_code=500,

                detail=(
                    "Gemini returned an empty response."
                )

            )

        return answer.strip()

    except HTTPException:

        raise

    except Exception as e:

        print(
            "Gemini Quiz Error:",
            repr(e)
        )

        raise HTTPException(

            status_code=500,

            detail=(
                "Gemini failed to generate the quiz. "
                f"{str(e)}"
            )

        )


# =========================================================
# AI CALL
# =========================================================

def call_ai(
    prompt: str,
    difficulty: str = "medium"
):

    provider = getattr(
        rag,
        "AI_PROVIDER",
        "ollama"
    )

    provider = provider.lower().strip()

    print(
        f"Quiz AI Provider: {provider}"
    )

    # -----------------------------------------------------
    # GEMINI
    # -----------------------------------------------------

    if provider == "gemini":

        return call_gemini(
            prompt,
            difficulty
        )

    # -----------------------------------------------------
    # OLLAMA
    # -----------------------------------------------------

    return call_ollama(
        prompt,
        difficulty
    )


# =========================================================
# TOPIC QUIZ
# =========================================================

def generate_topic_quiz(
    topic,
    difficulty,
    question_count
):

    difficulty_instruction = (
        get_difficulty_instruction(
            difficulty
        )
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

5. Do not repeat questions.

6. Do not test the same concept repeatedly.

7. Questions must genuinely match
the requested difficulty.

8. This is a Topic Quiz.

9. General knowledge may be used.

10. Keep explanations short and useful.

11. Do not create unsafe or inappropriate
questions.

================================================
OUTPUT FORMAT
================================================

Return ONLY valid JSON.

Do NOT use markdown.

Do NOT use code fences.

Do NOT write anything before JSON.

Do NOT write anything after JSON.

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
      "correct_answer": "Exactly one option text",
      "explanation": "Short explanation"
    }}
  ]
}}
"""

    raw = call_ai(
        prompt,
        difficulty
    )

    data = extract_json(
        raw
    )

    questions = validate_questions(
        data,
        question_count
    )

    if questions is None:

        print(
            "Invalid Topic Quiz JSON:"
        )

        print(raw)

        raise HTTPException(

            status_code=500,

            detail=(
                "AI returned invalid quiz JSON. "
                "Please try again."
            )

        )

    return questions


# =========================================================
# GET PDF CONTEXT
# =========================================================

def get_pdf_quiz_context(
    document_id,
    topic
):

    # -----------------------------------------------------
    # Topic provided
    # -----------------------------------------------------

    if topic and topic.strip():

        results = search_documents(

            query=topic.strip(),

            top_k=8,

            selected_documents=[
                document_id
            ]

        )

    # -----------------------------------------------------
    # No topic
    # -----------------------------------------------------

    else:

        results = [

            doc

            for doc in rag.documents

            if doc.get(
                "document_id"
            ) == document_id

        ]

        # -------------------------------------------------
        # Limit chunks
        # -------------------------------------------------

        results = results[:8]

    # -----------------------------------------------------
    # No results
    # -----------------------------------------------------

    if not results:

        raise HTTPException(

            status_code=404,

            detail=(
                "No content found in the selected PDF."
            )

        )

    context_parts = []

    for result in results:

        text = result.get(
            "text",
            ""
        ).strip()

        if not text:

            continue

        page = result.get(
            "page",
            "Unknown"
        )

        context_parts.append(

            f"Page {page}:\n{text}"

        )

    context = "\n\n".join(
        context_parts
    )

    # -----------------------------------------------------
    # No readable content
    # -----------------------------------------------------

    if not context.strip():

        raise HTTPException(

            status_code=404,

            detail=(
                "No readable content found in the selected PDF."
            )

        )

    # -----------------------------------------------------
    # Context limit
    # -----------------------------------------------------

    if len(context) > 24000:

        context = context[:24000]

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

    difficulty_instruction = (
        get_difficulty_instruction(
            difficulty
        )
    )

    if topic and topic.strip():

        topic_instruction = topic.strip()

    else:

        topic_instruction = (
            "important concepts covered in the PDF"
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
STRICT PDF SOURCE RULE
================================================

VERY IMPORTANT:

Use ONLY the information contained
in the supplied PDF context.

Do NOT use outside knowledge.

Do NOT use information from your
pre-trained knowledge.

Do NOT invent facts.

Do NOT assume information that is
not present in the PDF.

Every question must be answerable
from the supplied PDF context.

Every correct answer must be supported
by the supplied PDF context.

Every explanation must be supported
by the supplied PDF context.

================================================
QUESTION RULES
================================================

1. Generate exactly {question_count} questions.

2. Every question must have exactly 4 options.

3. There must be exactly ONE correct answer.

4. correct_answer must exactly match
one of the four options.

5. Do not repeat questions.

6. Do not repeatedly test the same concept.

7. Questions must match the requested difficulty.

8. Keep questions relevant to:
{topic_instruction}

9. Do not create questions about information
not contained in the PDF.

10. Keep explanations concise.

11. If the PDF does not provide enough
information for a question, do not create
that question.

================================================
OUTPUT FORMAT
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
      "correct_answer": "Exactly one option text",
      "explanation": "Explanation based only on PDF"
    }}
  ]
}}

================================================
PDF CONTENT
================================================

{context}
"""

    raw = call_ai(

        prompt,

        difficulty

    )

    data = extract_json(
        raw
    )

    questions = validate_questions(

        data,

        question_count

    )

    if questions is None:

        print(
            "Invalid PDF Quiz JSON:"
        )

        print(raw)

        raise HTTPException(

            status_code=500,

            detail=(
                "AI returned invalid PDF quiz JSON. "
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

    current_user: Student = Depends(
        get_current_user
    )

):

    # =====================================================
    # QUESTION COUNT
    # =====================================================

    if data.question_count < 1:

        raise HTTPException(

            status_code=400,

            detail=(
                "Question count must be at least 1."
            )

        )

    if data.question_count > 20:

        raise HTTPException(

            status_code=400,

            detail=(
                "Question count cannot exceed 20."
            )

        )

    # =====================================================
    # DIFFICULTY
    # =====================================================

    difficulty = (
        data.difficulty
        .lower()
        .strip()
    )

    if difficulty not in [

        "easy",

        "medium",

        "hard"

    ]:

        difficulty = "medium"

    # =====================================================
    # MODE
    # =====================================================

    mode = (
        data.mode
        .lower()
        .strip()
    )

    # =====================================================
    # TOPIC QUIZ
    # =====================================================

    if mode == "topic":

        if not data.topic or not data.topic.strip():

            raise HTTPException(

                status_code=400,

                detail=(
                    "Please enter a topic."
                )

            )

        questions = generate_topic_quiz(

            topic=data.topic.strip(),

            difficulty=difficulty,

            question_count=data.question_count

        )

        return {

            "questions": questions,

            "difficulty": difficulty,

            "provider": getattr(
                rag,
                "AI_PROVIDER",
                "ollama"
            )

        }

    # =====================================================
    # PDF QUIZ
    # =====================================================

    elif mode == "pdf":

        if not data.document_id:

            raise HTTPException(

                status_code=400,

                detail=(
                    "Please select a PDF."
                )

            )

        # -------------------------------------------------
        # Check PDF exists
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Generate PDF quiz
        # -------------------------------------------------

        questions = generate_pdf_quiz(

            document_id=data.document_id,

            topic=data.topic,

            difficulty=difficulty,

            question_count=data.question_count

        )

        return {

            "questions": questions,

            "difficulty": difficulty,

            "provider": getattr(
                rag,
                "AI_PROVIDER",
                "ollama"
            )

        }

    # =====================================================
    # INVALID MODE
    # =====================================================

    else:

        raise HTTPException(

            status_code=400,

            detail="Invalid quiz mode."

        )