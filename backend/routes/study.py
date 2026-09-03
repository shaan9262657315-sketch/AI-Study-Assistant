from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from schemas import StudyGuideRequest
from database import get_db
from dependencies import get_current_user
from models import Student, PDFDocument

import requests
import json
import re
import pymupdf
import rag


router = APIRouter(
    prefix="/study-guide",
    tags=["Study Guide"]
)


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"


# =========================================================
# OLLAMA
# =========================================================

def ask_ollama(prompt: str, json_mode: bool = False):

    try:

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": 8192,
                "num_predict": 6000
            }
        }

        # Force JSON response when required
        if json_mode:
            payload["format"] = {
                "type": "object",
                "properties": {
                    "important_questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {
                                    "type": "string"
                                },
                                "answer": {
                                    "type": "string"
                                }
                            },
                            "required": [
                                "question",
                                "answer"
                            ]
                        }
                    }
                },
                "required": [
                    "important_questions"
                ]
            }

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=300
        )

        response.raise_for_status()

        result = response.json()

        return result.get("response", "").strip()

    except requests.exceptions.ConnectionError:

        raise HTTPException(
            status_code=503,
            detail="Ollama is not running."
        )

    except requests.exceptions.Timeout:

        raise HTTPException(
            status_code=504,
            detail="Ollama request timed out."
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Ollama error: {str(e)}"
        )


# =========================================================
# LANGUAGE
# =========================================================

def language_instruction(language: str):

    if language.lower() == "hinglish":

        return """
Write in natural Hinglish.

Use a natural combination of Hindi and English.

Keep technical terms, scientific terms, formulas,
laws and important terminology in English.

Do not translate technical terms unnecessarily.

Example:
"Force ek push ya pull hota hai jo kisi object ki
motion ya state ko change kar sakta hai."

Use simple Hindi words.

Do not use very difficult Hindi.
"""

    return """
Write in simple and clear English.

Use student-friendly English.

Explain concepts properly.

Avoid unnecessarily difficult vocabulary.

The answer should be suitable for a student
preparing for exams.
"""


# =========================================================
# LOAD PDF CONTENT
# =========================================================

def get_pdf_content(document_id: str, pdf: PDFDocument):

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

        text = item.get("text", "").strip()

        if text:

            page = item.get("page", "Unknown")

            context_parts.append(
                f"\n--- PAGE {page} ---\n{text}"
            )

    # -----------------------------------------------------
    # IF RAG CONTENT EXISTS
    # -----------------------------------------------------

    if context_parts:

        return "\n".join(context_parts)

    # -----------------------------------------------------
    # FALLBACK: DIRECT PDF READING
    # -----------------------------------------------------

    try:

        pdf_file = pymupdf.open(pdf.file_path)

        direct_parts = []

        for page_number, page in enumerate(
            pdf_file,
            start=1
        ):

            text = page.get_text("text").strip()

            if text:

                direct_parts.append(
                    f"\n--- PAGE {page_number} ---\n{text}"
                )

        pdf_file.close()

        context = "\n".join(direct_parts)

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

    lang = language_instruction(language)

    prompt = f"""
You are an expert teacher creating a study guide
from an uploaded educational PDF.

STRICT SOURCE RULE:

Use ONLY the PDF content provided below.

Do NOT use outside knowledge.

Do NOT invent information.

Every explanation must be supported by the PDF.

{lang}

================================================
TASK: CREATE STUDY SUMMARY
================================================

Create a detailed study summary.

Cover the important material present in the PDF.

Include where supported:

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

Do not add outside information.

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

Start directly with the summary.
"""

    return ask_ollama(prompt)


# =========================================================
# CLEAN JSON RESPONSE
# =========================================================

def extract_json(raw: str):

    if not raw:
        return None

    raw = raw.strip()

    # Remove markdown code fences
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
    # FIRST TRY: DIRECT JSON
    # -----------------------------------------------------

    try:

        return json.loads(raw)

    except json.JSONDecodeError:
        pass

    # -----------------------------------------------------
    # SECOND TRY: FIND JSON OBJECT
    # -----------------------------------------------------

    start = raw.find("{")
    end = raw.rfind("}")

    if start != -1 and end != -1 and end > start:

        json_text = raw[start:end + 1]

        try:

            return json.loads(json_text)

        except json.JSONDecodeError:
            pass

    return None


# =========================================================
# GENERATE IMPORTANT QUESTIONS
# =========================================================

def generate_questions(
    context: str,
    question_count: int,
    language: str
):

    lang = language_instruction(language)

    prompt = f"""
You are an expert exam question generator.

Create important exam questions ONLY from the PDF.

STRICT SOURCE RULE:

Use ONLY the PDF content.

Do NOT use outside knowledge.

Do NOT invent facts.

{lang}

================================================
TASK
================================================

Generate exactly {question_count} important questions.

Questions should cover different important concepts.

Prefer:

- Definitions
- Important concepts
- Laws
- Principles
- Formulas
- Important facts
- Conceptual questions
- Important examples
- Exam-oriented questions

Do NOT repeat the same concept.

================================================
ANSWER REQUIREMENTS
================================================

Each question MUST have an answer.

For conceptual questions:

Give a clear and useful explanation.

For factual questions:

Give a concise but explanatory answer.

Do not give one-word answers.

Answers should help a student prepare for exams.

================================================
VERY IMPORTANT JSON RULE
================================================

Return ONLY JSON.

Do NOT write any introduction.

Do NOT write any explanation outside JSON.

Do NOT use markdown.

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
    # FIRST ATTEMPT
    # -----------------------------------------------------

    raw = ask_ollama(
        prompt,
        json_mode=True
    )

    data = extract_json(raw)

    # -----------------------------------------------------
    # RETRY IF JSON FAILED
    # -----------------------------------------------------

    if data is None:

        retry_prompt = f"""
Return ONLY valid JSON.

Create exactly {question_count} important
exam questions from the PDF below.

Each object MUST contain:

question
answer

Required format:

{{
  "important_questions": [
    {{
      "question": "Question",
      "answer": "Answer"
    }}
  ]
}}

No markdown.
No code fences.
No text outside JSON.

Use ONLY the PDF content.

{lang}

PDF:

{context}
"""

        raw = ask_ollama(
            retry_prompt,
            json_mode=True
        )

        data = extract_json(raw)

    # -----------------------------------------------------
    # FINAL JSON CHECK
    # -----------------------------------------------------

    if data is None:

        raise HTTPException(
            status_code=500,
            detail="Ollama returned invalid question JSON."
        )

    questions = data.get("important_questions")

    if not isinstance(questions, list):

        raise HTTPException(
            status_code=500,
            detail="Invalid question format returned by Ollama."
        )

    # -----------------------------------------------------
    # VALIDATE QUESTIONS
    # -----------------------------------------------------

    valid_questions = []

    for item in questions:

        if not isinstance(item, dict):
            continue

        question = item.get("question")
        answer = item.get("answer")

        if question is None or answer is None:
            continue

        question = str(question).strip()
        answer = str(answer).strip()

        if question and answer:

            valid_questions.append({
                "question": question,
                "answer": answer
            })

    # -----------------------------------------------------
    # CHECK MINIMUM
    # -----------------------------------------------------

    if not valid_questions:

        raise HTTPException(
            status_code=500,
            detail="No valid questions generated."
        )

    # -----------------------------------------------------
    # RETURN REQUESTED NUMBER
    # -----------------------------------------------------

    return valid_questions[:question_count]


# =========================================================
# API
# =========================================================

@router.post("/generate")
def generate_study_guide(
    data: StudyGuideRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
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

    language = language.lower().strip()

    if language not in ["english", "hinglish"]:

        language = "english"

    # =====================================================
    # FIND PDF
    # =====================================================

    pdf = (
        db.query(PDFDocument)
        .filter(
            PDFDocument.document_id == document_id
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

    # Prevent the small local model from getting
    # overloaded with too much input.
    if len(context) > 35000:

        context = context[:35000]

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