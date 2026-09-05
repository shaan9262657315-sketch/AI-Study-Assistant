from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import json
import re
import time
from typing import Optional

import rag

from database import get_db
from dependencies import get_current_user
from models import Student, PDFDocument

from schemas import (
    QuizGenerateRequest,
    QuizResponse,
    QuizQuestion
)


router = APIRouter(
    prefix="/quiz",
    tags=["Quiz"]
)


# =========================================================
# CONFIG
# =========================================================

GEMINI_MODEL = "gemini-3.8-flash"

MAX_QUESTION_COUNT = 20
DEFAULT_QUESTION_COUNT = 5

MAX_CONTEXT_LENGTH = 30000


# =========================================================
# GEMINI
# =========================================================

def call_gemini(prompt: str):

    if not getattr(
        rag,
        "gemini_client",
        None
    ):

        raise HTTPException(
            status_code=503,
            detail=(
                "Gemini is not configured. "
                "Please check GEMINI_API_KEY."
            )
        )

    max_retries = 3
    delay = 2

    for attempt in range(max_retries):
        try:
            response = (
                rag.gemini_client
                .models
                .generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config={
                        "response_mime_type":
                            "application/json"
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

            return answer.strip()

        except HTTPException as he:
            raise he

        except Exception as e:
            print(
                f"Gemini Quiz Error (Attempt {attempt + 1}/{max_retries}):",
                e
            )

            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=500,
                    detail=f"Gemini request failed after {max_retries} attempts: {str(e)}"
                )

            time.sleep(delay)
            delay *= 2


# =========================================================
# EXTRACT JSON
# =========================================================

def extract_json(text: str):

    if not text:

        return None

    text = text.strip()

    # -----------------------------------------------------
    # DIRECT JSON
    # -----------------------------------------------------

    try:

        return json.loads(
            text
        )

    except json.JSONDecodeError:

        pass

    # -----------------------------------------------------
    # REMOVE CODE FENCE
    # -----------------------------------------------------

    cleaned = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"```",
        "",
        cleaned
    ).strip()

    try:

        return json.loads(
            cleaned
        )

    except json.JSONDecodeError:

        pass

    # -----------------------------------------------------
    # FIND JSON OBJECT
    # -----------------------------------------------------

    start = cleaned.find(
        "{"
    )

    end = cleaned.rfind(
        "}"
    )

    if (
        start != -1
        and end != -1
        and end > start
    ):

        json_text = cleaned[
            start:end + 1
        ]

        try:

            return json.loads(
                json_text
            )

        except json.JSONDecodeError:

            pass

    return None


# =========================================================
# VALIDATE QUIZ
# =========================================================

def validate_quiz(
    data,
    expected_count: int
):

    if not isinstance(
        data,
        dict
    ):

        return None

    questions = data.get(
        "questions"
    )

    if not isinstance(
        questions,
        list
    ):

        return None

    valid_questions = []

    for item in questions:

        if not isinstance(
            item,
            dict
        ):

            continue

        question = item.get(
            "question"
        )

        options = item.get(
            "options"
        )

        correct_answer = item.get(
            "correct_answer"
        )

        explanation = item.get(
            "explanation"
        )

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if not question:
            continue

        if not options:
            continue

        if not correct_answer:
            continue

        if not explanation:
            continue

        # -------------------------------------------------
        # OPTIONS VALIDATION
        # -------------------------------------------------

        if not isinstance(
            options,
            list
        ):

            continue

        if len(options) != 4:

            continue

        cleaned_options = []

        for option in options:

            if option is None:
                continue

            option = str(
                option
            ).strip()

            if option:

                cleaned_options.append(
                    option
                )

        if len(cleaned_options) != 4:

            continue

        # -------------------------------------------------
        # CORRECT ANSWER MUST EXIST
        # -------------------------------------------------

        correct_answer = str(
            correct_answer
        ).strip()

        if correct_answer not in cleaned_options:

            continue

        # -------------------------------------------------
        # ADD VALID QUESTION
        # -------------------------------------------------

        valid_questions.append({

            "question":
                str(question).strip(),

            "options":
                cleaned_options,

            "correct_answer":
                correct_answer,

            "explanation":
                str(explanation).strip()

        })

    # -----------------------------------------------------
    # EXACT COUNT CHECK
    # -----------------------------------------------------

    if len(valid_questions) < expected_count:

        return None

    return valid_questions[
        :expected_count
    ]


# =========================================================
# TOPIC QUIZ
# =========================================================

def generate_topic_quiz(
    topic: str,
    difficulty: str,
    question_count: int
):

    prompt = f"""
You are an expert AI Study Assistant.

Create a multiple-choice educational quiz.

TOPIC:
{topic}

DIFFICULTY:
{difficulty}

NUMBER OF QUESTIONS:
{question_count}

================================================
REQUIREMENTS
================================================

Generate exactly {question_count} questions.

Each question must have:

1. One clear question.
2. Exactly four options.
3. Exactly one correct answer.
4. A short explanation.

The four options must be plausible.

Do not create duplicate questions.

Questions should test understanding, not just
memorisation whenever possible.

Difficulty should match:
{difficulty}

================================================
JSON FORMAT
================================================

Return ONLY valid JSON.

Do not use markdown.

Do not use code fences.

Do not write anything outside JSON.

Use exactly this structure:

{{
    "questions": [
        {{
            "question": "Question text",
            "options": [
                "Option 1",
                "Option 2",
                "Option 3",
                "Option 4"
            ],
            "correct_answer": "Correct option",
            "explanation": "Short explanation"
        }}
    ]
}}

The correct_answer value MUST exactly match
one of the four option strings.

Generate exactly {question_count} questions.
"""

    raw = call_gemini(
        prompt
    )

    data = extract_json(
        raw
    )

    questions = validate_quiz(
        data,
        question_count
    )

    # -----------------------------------------------------
    # RETRY
    # -----------------------------------------------------

    if questions is None:

        retry_prompt = f"""
Return ONLY valid JSON.

Create exactly {question_count}
multiple-choice questions about:

{topic}

Difficulty:
{difficulty}

Every question MUST contain:

- question
- exactly 4 options
- correct_answer
- explanation

The correct_answer MUST exactly match
one of the four options.

No markdown.
No code fences.
No extra text.

Use exactly:

{{
    "questions": [
        {{
            "question": "Question",
            "options": [
                "Option 1",
                "Option 2",
                "Option 3",
                "Option 4"
            ],
            "correct_answer": "Option 1",
            "explanation": "Explanation"
        }}
    ]
}}

Generate exactly {question_count} questions.
"""

        raw = call_gemini(
            retry_prompt
        )

        data = extract_json(
            raw
        )

        questions = validate_quiz(
            data,
            question_count
        )

    if questions is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "Gemini returned invalid quiz data. "
                "Please try again."
            )
        )

    return questions


# =========================================================
# PDF CONTEXT
# =========================================================

def get_pdf_context(
    document_id: str,
    topic: Optional[str] = None,
    chapter: Optional[str] = None
):

    # -----------------------------------------------------
    # BUILD SEARCH QUERY
    # -----------------------------------------------------

    search_parts = []

    if topic and topic.strip():

        search_parts.append(
            topic.strip()
        )

    if chapter and chapter.strip():

        search_parts.append(
            chapter.strip()
        )

    # -----------------------------------------------------
    # SEARCH RAG
    # -----------------------------------------------------

    if search_parts:

        search_query = " ".join(
            search_parts
        )

        results = rag.search_documents(

            query=search_query,

            top_k=10,

            selected_documents=[
                document_id
            ]

        )

    else:

        results = [

            item

            for item in rag.documents

            if item.get(
                "document_id"
            ) == document_id

        ]

        results = results[:10]

    # -----------------------------------------------------
    # NO RESULTS
    # -----------------------------------------------------

    if not results:

        return None

    # -----------------------------------------------------
    # BUILD CONTEXT
    # -----------------------------------------------------

    context_parts = []

    for result in results:

        page = result.get(
            "page",
            "Unknown"
        )

        text = result.get(
            "text",
            ""
        ).strip()

        if not text:
            continue

        context_parts.append(

            f"[Page {page}]\n"
            f"{text}"

        )

    if not context_parts:

        return None

    context = "\n\n".join(
        context_parts
    )

    # -----------------------------------------------------
    # LIMIT CONTEXT
    # -----------------------------------------------------

    if len(context) > MAX_CONTEXT_LENGTH:

        context = context[
            :MAX_CONTEXT_LENGTH
        ]

    return context


# =========================================================
# PDF QUIZ
# =========================================================

def generate_pdf_quiz(
    context: str,
    topic: Optional[str],
    chapter: Optional[str],
    difficulty: str,
    question_count: int
):

    topic_text = (

        topic.strip()

        if topic
        and topic.strip()

        else
        "all important concepts"

    )

    chapter_text = (

        chapter.strip()

        if chapter
        and chapter.strip()

        else
        "all available chapters"

    )

    prompt = f"""
You are an expert university-level AI Study Assistant.

Create a multiple-choice quiz using ONLY the supplied
PDF content.

================================================
QUIZ DETAILS
================================================

Topic:
{topic_text}

Chapter:
{chapter_text}

Difficulty:
{difficulty}

Number of questions:
{question_count}

================================================
STRICT SOURCE RULE
================================================

Use ONLY the information contained in the PDF.

Do NOT use outside knowledge.

Do NOT invent facts.

Every question, option, correct answer and explanation
must be supported by the supplied PDF.

If a requested topic is not sufficiently covered
by the PDF, create questions only from the relevant
information that actually exists.

================================================
QUESTION REQUIREMENTS
================================================

Generate exactly {question_count} questions.

Each question must contain:

1. One clear question.
2. Exactly four options.
3. Exactly one correct answer.
4. A useful explanation.

Questions should cover different concepts.

Avoid duplicate questions.

Prefer important concepts, definitions, principles,
formulas, examples and exam-relevant material
when supported by the PDF.

Difficulty:
{difficulty}

================================================
JSON REQUIREMENT
================================================

Return ONLY valid JSON.

Do not use markdown.

Do not use code fences.

Do not write anything outside JSON.

Use exactly this structure:

{{
    "questions": [
        {{
            "question": "Question text",
            "options": [
                "Option 1",
                "Option 2",
                "Option 3",
                "Option 4"
            ],
            "correct_answer": "Correct option",
            "explanation": "Explanation based only on PDF"
        }}
    ]
}}

IMPORTANT:

The correct_answer value MUST exactly match
one of the four option strings.

Generate exactly {question_count} questions.

================================================
PDF CONTENT
================================================

{context}
"""

    raw = call_gemini(
        prompt
    )

    data = extract_json(
        raw
    )

    questions = validate_quiz(
        data,
        question_count
    )

    # -----------------------------------------------------
    # RETRY
    # -----------------------------------------------------

    if questions is None:

        retry_prompt = f"""
Return ONLY valid JSON.

Create exactly {question_count}
multiple-choice questions from the supplied PDF.

Use ONLY the PDF.

Do NOT use outside knowledge.

Difficulty:
{difficulty}

Every question MUST contain:

- question
- exactly 4 options
- correct_answer
- explanation

The correct_answer MUST exactly match
one of the four options.

No markdown.
No code fences.
No text outside JSON.

Use exactly:

{{
    "questions": [
        {{
            "question": "Question",
            "options": [
                "Option 1",
                "Option 2",
                "Option 3",
                "Option 4"
            ],
            "correct_answer": "Correct option",
            "explanation": "PDF-based explanation"
        }}
    ]
}}

Generate exactly {question_count} questions.

================================================
PDF
================================================

{context}
"""

        raw = call_gemini(
            retry_prompt
        )

        data = extract_json(
            raw
        )

        questions = validate_quiz(
            data,
            question_count
        )

    if questions is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "Gemini returned invalid PDF quiz data. "
                "Please try again."
            )
        )

    return questions


# =========================================================
# API
# =========================================================

@router.post(
    "/generate",
    response_model=QuizResponse
)
def generate_quiz(

    data: QuizGenerateRequest,

    db: Session = Depends(
        get_db
    ),

    current_user: Student = Depends(
        get_current_user
    )

):

    # =====================================================
    # QUESTION COUNT
    # =====================================================

    question_count = data.question_count

    if question_count < 1:

        question_count = 1

    if question_count > MAX_QUESTION_COUNT:

        question_count = MAX_QUESTION_COUNT

    # =====================================================
    # MODE
    # =====================================================

    mode = (
        data.mode
        .lower()
        .strip()
    )

    # =====================================================
    # DIFFICULTY
    # =====================================================

    difficulty = (
        data.difficulty
        .lower()
        .strip()
    )

    allowed_difficulties = [
        "easy",
        "medium",
        "hard"
    ]

    if difficulty not in allowed_difficulties:

        difficulty = "medium"

    # =====================================================
    # TOPIC MODE
    # =====================================================

    if mode == "topic":

        if (
            not data.topic
            or not data.topic.strip()
        ):

            raise HTTPException(
                status_code=400,
                detail="Please enter a topic."
            )

        questions = generate_topic_quiz(

            topic=data.topic,

            difficulty=difficulty,

            question_count=question_count

        )

        return {
            "questions": questions
        }

    # =====================================================
    # PDF MODE
    # =====================================================

    if mode == "pdf":

        if not data.document_id:

            raise HTTPException(
                status_code=400,
                detail="Please select a PDF."
            )

        # -------------------------------------------------
        # CHECK PDF IN DATABASE
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
        # GET RAG CONTEXT
        # -------------------------------------------------

        context = get_pdf_context(

            document_id=data.document_id,

            topic=data.topic,

            chapter=data.chapter

        )

        if not context:

            raise HTTPException(
                status_code=404,
                detail=(
                    "No relevant content found "
                    "in the selected PDF."
                )
            )

        # -------------------------------------------------
        # GENERATE QUIZ
        # -------------------------------------------------

        questions = generate_pdf_quiz(

            context=context,

            topic=data.topic,

            chapter=data.chapter,

            difficulty=difficulty,

            question_count=question_count

        )

        return {
            "questions": questions
        }

    # =====================================================
    # INVALID MODE
    # =====================================================

    raise HTTPException(
        status_code=400,
        detail=(
            "Invalid quiz mode. "
            "Use 'topic' or 'pdf'."
        )
    )