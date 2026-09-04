from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from schemas import StudyGuideRequest
from database import get_db
from dependencies import get_current_user
from models import Student, PDFDocument

import json
import re
import pymupdf
import rag


router = APIRouter(
    prefix="/study-guide",
    tags=["Study Guide"]
)


# =========================================================
# AI CONFIG
# =========================================================

GEMINI_MODEL = "gemini-3.6-flash"


# =========================================================
# LANGUAGE
# =========================================================

def language_instruction(language: str):

    language = language.lower().strip()

    # -----------------------------------------------------
    # HINGLISH
    # -----------------------------------------------------

    if language == "hinglish":

        return """
Write in natural Hinglish.

Use a natural combination of Hindi and English.

Keep technical terms, scientific terms, formulas,
laws and important terminology in English.

Do not translate technical terms unnecessarily.

Use simple Hindi words.

Do not use very difficult Hindi.

Example:
"Force ek push ya pull hota hai jo kisi object ki
motion ya state ko change kar sakta hai."
"""

    # -----------------------------------------------------
    # HINDI
    # -----------------------------------------------------

    if language == "hindi":

        return """
Write in simple Hindi.

Keep standard technical and scientific terms in English
where necessary.

Use student-friendly language.
"""

    # -----------------------------------------------------
    # GB ENGLISH
    # -----------------------------------------------------

    if language in [
        "gb english",
        "british english",
        "english uk",
        "uk english"
    ]:

        return """
Write in clear British English (GB English).

Use British spelling where applicable, for example:

- organise
- analyse
- behaviour
- centre
- practise

Use simple and student-friendly English.

The explanation should be suitable for a student
preparing for university examinations.
"""

    # -----------------------------------------------------
    # DEFAULT ENGLISH
    # -----------------------------------------------------

    return """
Write in clear and simple English.

Use student-friendly English.

Explain concepts properly.

Avoid unnecessarily difficult vocabulary.

The answer should be suitable for a student
preparing for exams.
"""


# =========================================================
# GEMINI CALL
# =========================================================

def ask_gemini(
    prompt: str,
    json_mode: bool = False
):

    # -----------------------------------------------------
    # CHECK GEMINI
    # -----------------------------------------------------

    if not rag.gemini_client:

        raise HTTPException(
            status_code=503,
            detail="Gemini is not configured. Please check GEMINI_API_KEY."
        )

    try:

        # -------------------------------------------------
        # NORMAL TEXT
        # -------------------------------------------------

        if not json_mode:

            response = rag.gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )

        # -------------------------------------------------
        # JSON RESPONSE
        # -------------------------------------------------

        else:

            response = rag.gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )

        # -------------------------------------------------
        # RESPONSE TEXT
        # -------------------------------------------------

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

    # -----------------------------------------------------
    # GEMINI ERROR
    # -----------------------------------------------------

    except HTTPException:

        raise

    except Exception as e:

        print("Gemini Study Guide Error:", e)

        raise HTTPException(
            status_code=500,
            detail=f"Gemini request failed: {str(e)}"
        )


# =========================================================
# LOAD PDF CONTENT
# =========================================================

def get_pdf_content(
    document_id: str,
    pdf: PDFDocument
):

    # -----------------------------------------------------
    # FIRST: CHECK RAG DOCUMENTS
    # -----------------------------------------------------

    pdf_documents = [
        item
        for item in rag.documents
        if item.get("document_id") == document_id
    ]

    context_parts = []

    for item in pdf_documents:

        text = item.get(
            "text",
            ""
        ).strip()

        if text:

            page = item.get(
                "page",
                "Unknown"
            )

            context_parts.append(
                f"\n--- PAGE {page} ---\n{text}"
            )

    # -----------------------------------------------------
    # IF RAG CONTENT EXISTS
    # -----------------------------------------------------

    if context_parts:

        return "\n".join(
            context_parts
        )

    # -----------------------------------------------------
    # FALLBACK: DIRECT PDF READING
    # -----------------------------------------------------

    try:

        pdf_file = pymupdf.open(
            pdf.file_path
        )

        direct_parts = []

        for page_number, page in enumerate(
            pdf_file,
            start=1
        ):

            text = page.get_text(
                "text"
            ).strip()

            if text:

                direct_parts.append(
                    f"\n--- PAGE {page_number} ---\n{text}"
                )

        pdf_file.close()

        context = "\n".join(
            direct_parts
        )

        if context.strip():

            return context

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to read PDF: {str(e)}"
        )

    raise HTTPException(
        status_code=400,
        detail="No readable content found in the selected PDF."
    )


# =========================================================
# GENERATE SUMMARY
# =========================================================

def generate_summary(
    context: str,
    language: str
):

    lang = language_instruction(
        language
    )

    prompt = f"""
You are an expert university teacher creating
a study guide from an uploaded educational PDF.

================================================
STRICT SOURCE RULE
================================================

Use ONLY the PDF content provided below.

Do NOT use outside knowledge.

Do NOT invent information.

Every explanation must be supported by the PDF.

================================================
LANGUAGE
================================================

{lang}

================================================
TASK: CREATE STUDY SUMMARY
================================================

Create a useful and well-organised study summary.

Cover the important material present in the PDF.

Include, whenever supported by the PDF:

1. Introduction / overview
2. Major topics
3. Important concepts
4. Important definitions
5. Important laws and principles
6. Important formulas
7. Important facts
8. Important examples
9. Relationships between concepts
10. Important exam points
11. Key things to remember

Explain concepts instead of simply listing them.

If formulas are present, write and explain them.

If examples are present, explain their purpose.

Do not add information that is not present
in the PDF.

The summary should help a student revise
for university examinations.

================================================
PDF CONTENT
================================================

{context}

================================================
OUTPUT
================================================

Return ONLY the summary text.

Do not return JSON.

Do not use code fences.

Do not write an introduction before the summary.

Start directly with the study summary.
"""

    return ask_gemini(
        prompt,
        json_mode=False
    )


# =========================================================
# CLEAN JSON RESPONSE
# =========================================================

def extract_json(raw: str):

    if not raw:

        return None

    raw = raw.strip()

    # -----------------------------------------------------
    # REMOVE CODE FENCES
    # -----------------------------------------------------

    raw = re.sub(
        r"```json",
        "",
        raw,
        flags=re.IGNORECASE
    )

    raw = re.sub(
        r"```",
        "",
        raw
    ).strip()

    # -----------------------------------------------------
    # DIRECT JSON
    # -----------------------------------------------------

    try:

        return json.loads(
            raw
        )

    except json.JSONDecodeError:

        pass

    # -----------------------------------------------------
    # FIND JSON OBJECT
    # -----------------------------------------------------

    start = raw.find(
        "{"
    )

    end = raw.rfind(
        "}"
    )

    if (
        start != -1
        and end != -1
        and end > start
    ):

        json_text = raw[
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
# VALIDATE QUESTIONS
# =========================================================

def validate_questions(
    data,
    question_count
):

    if not isinstance(
        data,
        dict
    ):

        return None

    questions = data.get(
        "important_questions"
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

        answer = item.get(
            "answer"
        )

        if question is None:
            continue

        if answer is None:
            continue

        question = str(
            question
        ).strip()

        answer = str(
            answer
        ).strip()

        if not question:
            continue

        if not answer:
            continue

        valid_questions.append({
            "question": question,
            "answer": answer
        })

    # -----------------------------------------------------
    # NEED EXACT NUMBER
    # -----------------------------------------------------

    if len(valid_questions) < question_count:

        return None

    return valid_questions[
        :question_count
    ]


# =========================================================
# GENERATE IMPORTANT QUESTIONS
# =========================================================

def generate_questions(
    context: str,
    question_count: int,
    language: str
):

    lang = language_instruction(
        language
    )

    prompt = f"""
You are an expert university exam question generator.

Create important examination questions ONLY from
the supplied PDF content.

================================================
STRICT SOURCE RULE
================================================

Use ONLY the PDF content.

Do NOT use outside knowledge.

Do NOT invent facts.

Every question and answer must be supported
by the supplied PDF.

================================================
LANGUAGE
================================================

{lang}

================================================
TASK
================================================

Generate EXACTLY {question_count}
important questions.

Questions should cover different important
concepts from the PDF.

Prefer:

- Important definitions
- Important concepts
- Laws
- Principles
- Formulas
- Important facts
- Conceptual questions
- Important examples
- Exam-oriented questions

Do NOT repeat the same concept.

Each question MUST have a useful answer.

Answers should help a student prepare
for university examinations.

Avoid one-word answers unless the PDF itself
requires a specific technical term.

================================================
JSON REQUIREMENT
================================================

Return ONLY valid JSON.

Do NOT return markdown.

Do NOT use code fences.

Do NOT write anything before or after JSON.

The JSON MUST have exactly this structure:

{{
  "important_questions": [
    {{
      "question": "Question text",
      "answer": "Answer text"
    }}
  ]
}}

Generate exactly {question_count} objects.

================================================
PDF CONTENT
================================================

{context}
"""

    # -----------------------------------------------------
    # FIRST GEMINI REQUEST
    # -----------------------------------------------------

    raw = ask_gemini(
        prompt,
        json_mode=True
    )

    data = extract_json(
        raw
    )

    questions = validate_questions(
        data,
        question_count
    )

    # -----------------------------------------------------
    # RETRY
    # -----------------------------------------------------

    if questions is None:

        retry_prompt = f"""
You must return ONLY valid JSON.

Create exactly {question_count}
important exam questions from the PDF.

Every object MUST contain:

question
answer

Use this exact structure:

{{
  "important_questions": [
    {{
      "question": "Question",
      "answer": "Answer"
    }}
  ]
}}

Rules:

- Exactly {question_count} objects
- Every question must be different
- Every answer must be non-empty
- Use ONLY the PDF
- Do NOT use outside knowledge
- No markdown
- No code fences
- No text outside JSON

{lang}

================================================
PDF
================================================

{context}
"""

        raw = ask_gemini(
            retry_prompt,
            json_mode=True
        )

        data = extract_json(
            raw
        )

        questions = validate_questions(
            data,
            question_count
        )

    # -----------------------------------------------------
    # FINAL CHECK
    # -----------------------------------------------------

    if questions is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI returned invalid study-guide "
                "question JSON. Please try again."
            )
        )

    return questions


# =========================================================
# API
# =========================================================

@router.post("/generate")
def generate_study_guide(
    data: StudyGuideRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(
        get_current_user
    )
):

    # =====================================================
    # REQUEST DATA
    # =====================================================

    document_id = data.document_id

    question_count = data.question_count

    language = data.language

    # =====================================================
    # VALIDATE QUESTION COUNT
    # =====================================================

    if question_count < 1:

        question_count = 1

    if question_count > 20:

        question_count = 20

    # =====================================================
    # VALIDATE LANGUAGE
    # =====================================================

    language = (
        language
        .lower()
        .strip()
    )

    allowed_languages = [
        "english",
        "gb english",
        "british english",
        "english uk",
        "uk english",
        "hinglish",
        "hindi"
    ]

    if language not in allowed_languages:

        language = "english"

    # =====================================================
    # FIND PDF
    # =====================================================

    pdf = (
        db.query(
            PDFDocument
        )
        .filter(
            PDFDocument.document_id
            == document_id
        )
        .first()
    )

    if not pdf:

        raise HTTPException(
            status_code=404,
            detail="PDF not found in database."
        )

    # =====================================================
    # GET PDF CONTENT
    # =====================================================

    context = get_pdf_content(
        document_id,
        pdf
    )

    if not context.strip():

        raise HTTPException(
            status_code=400,
            detail="No content found in the selected PDF."
        )

    # =====================================================
    # LIMIT CONTEXT
    # =====================================================

    # Gemini can handle a much larger context than
    # llama3.2:3b, but keeping a reasonable limit
    # makes the request faster and focused.

    if len(context) > 50000:

        context = context[
            :50000
        ]

    # =====================================================
    # STEP 1: SUMMARY
    # =====================================================

    summary = generate_summary(
        context,
        language
    )

    # =====================================================
    # STEP 2: IMPORTANT QUESTIONS
    # =====================================================

    important_questions = generate_questions(
        context,
        question_count,
        language
    )

    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    return {
        "document_id": document_id,
        "filename": pdf.filename,
        "language": language,
        "summary": summary,
        "important_questions": important_questions
    }