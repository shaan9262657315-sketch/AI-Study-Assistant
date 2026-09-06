from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from schemas import StudyGuideRequest
from database import get_db
from dependencies import get_current_user
from models import Student, PDFDocument, StudyGuideHistory

import json
import re
import pymupdf
import rag


router = APIRouter(
    prefix="/study-guide",
    tags=["Study Guide"]
)


# =========================================================
# LANGUAGE INSTRUCTIONS
# =========================================================

def language_instruction(language: str):
    language = language.lower().strip()

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

    if language == "hindi":
        return """
Write in simple Hindi.
Keep standard technical and scientific terms in English
where necessary.
Use student-friendly language.
"""

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

    return """
Write in clear and simple English.
Use student-friendly English.
Explain concepts properly.
Avoid unnecessarily difficult vocabulary.
The answer should be suitable for a student
preparing for exams.
"""


# =========================================================
# UNIFIED AI PROVIDER CALL
# =========================================================

def call_ai(
    prompt: str,
    json_mode: bool = False
):
    try:
        response = rag.generate_answer(
            question=prompt,
            context="",
            language="english",
            outside_knowledge=True
        )
        if isinstance(response, dict):
            return response.get("answer", str(response))
        return str(response).strip()
    except Exception as e:
        print("AI Study Guide Error:", e)
        raise HTTPException(
            status_code=500,
            detail=f"AI request failed: {str(e)}"
        )


# =========================================================
# LOAD PDF CONTENT
# =========================================================

def get_pdf_content(
    document_id: str,
    pdf: PDFDocument
):
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

    if context_parts:
        return "\n".join(context_parts)

    try:
        pdf_file = pymupdf.open(pdf.file_path)
        direct_parts = []
        for page_number, page in enumerate(pdf_file, start=1):
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
# GENERATE SUMMARY (FULL DETAILED PROMPT RESTORED)
# =========================================================

def generate_summary(
    context: str,
    language: str
):
    lang = language_instruction(language)

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

Create a useful, highly detailed, and well-organised study summary.
Cover all the important material present in the PDF thoroughly.

Include, whenever supported by the PDF:
1. Introduction / overview
2. Major topics with detailed explanations
3. Important concepts explained step-by-step
4. Important definitions
5. Important laws and principles
6. Important formulas (with variable breakdowns)
7. Important facts
8. Important examples (explaining their purpose)
9. Relationships between concepts
10. Important exam points
11. Key things to remember

Explain concepts thoroughly instead of simply listing them.
Do not add information that is not present in the PDF.
The summary should help a student completely revise for university examinations.

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

    return call_ai(prompt, json_mode=False)


# =========================================================
# CLEAN JSON RESPONSE
# =========================================================

def extract_json(raw: str):
    if not raw:
        return None

    raw = raw.strip()
    raw = re.sub(r"```json", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```", "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


# =========================================================
# VALIDATE QUESTIONS
# =========================================================

def validate_questions(data, question_count):
    if not isinstance(data, dict):
        return None

    questions = data.get("important_questions")
    if not isinstance(questions, list):
        return None

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

        if not question or not answer:
            continue

        valid_questions.append({
            "question": question,
            "answer": answer
        })

    if len(valid_questions) < question_count:
        return None

    return valid_questions[:question_count]


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
You are an expert university exam question generator.
Create important examination questions ONLY from the supplied PDF content.

================================================
STRICT SOURCE RULE
================================================

Use ONLY the PDF content.
Do NOT use outside knowledge.
Do NOT invent facts.
Every question and answer must be supported by the supplied PDF.

================================================
LANGUAGE
================================================

{lang}

================================================
TASK
================================================

Generate EXACTLY {question_count} important exam-oriented questions.
Questions should cover different important concepts, definitions, laws, principles, formulas, and examples from the PDF.
Each question MUST have a comprehensive, highly useful answer to help a student prepare for university exams.

================================================
JSON REQUIREMENT
================================================

Return ONLY valid JSON.
Do NOT return markdown or code fences.
The JSON MUST have exactly this structure:

{{
  "important_questions": [
    {{
      "question": "Question text",
      "answer": "Detailed answer text"
    }}
  ]
}}

Generate exactly {question_count} objects.

================================================
PDF CONTENT
================================================

{context}
"""

    raw = call_ai(prompt, json_mode=True)
    data = extract_json(raw)
    questions = validate_questions(data, question_count)

    if questions is None:
        retry_prompt = f"""
You must return ONLY valid JSON with exactly {question_count} important exam questions.
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
- Use ONLY the PDF content
- No markdown or code fences

{lang}

PDF CONTENT:
{context}
"""
        raw = call_ai(retry_prompt, json_mode=True)
        data = extract_json(raw)
        questions = validate_questions(data, question_count)

    if questions is None:
        raise HTTPException(
            status_code=500,
            detail="AI returned invalid study-guide question JSON. Please try again."
        )

    return questions


# =========================================================
# LIBRARY ENDPOINTS (HISTORY FETCHING & DELETION)
# =========================================================

@router.get("/library")
def get_study_guide_library(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    history_items = (
        db.query(StudyGuideHistory)
        .filter(StudyGuideHistory.user_id == current_user.id)
        .all()
    )
    
    result = []
    for item in history_items:
        result.append({
            "id": item.id,
            "document_id": item.document_id,
            "filename": item.filename,
            "language": item.language,
            "summary": item.summary,
            "important_questions": item.important_questions,
            "created_at": item.created_at
        })
    return result


@router.delete("/library/{history_id}")
def delete_study_guide(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    item = (
        db.query(StudyGuideHistory)
        .filter(
            StudyGuideHistory.id == history_id,
            StudyGuideHistory.user_id == current_user.id
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Study guide not found."
        )

    db.delete(item)
    db.commit()
    return {"message": "Study guide deleted successfully."}


# =========================================================
# API ENDPOINT (GENERATE & SAVE)
# =========================================================

@router.post("/generate")
def generate_study_guide(
    data: StudyGuideRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    document_id = data.document_id
    question_count = max(1, min(20, data.question_count))
    language = data.language.lower().strip()

    pdf = db.query(PDFDocument).filter(PDFDocument.document_id == document_id).first()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found in database.")

    context = get_pdf_content(document_id, pdf)
    if not context.strip():
        raise HTTPException(status_code=400, detail="No content found in the selected PDF.")

    if len(context) > 50000:
        context = context[:50000]

    summary = generate_summary(context, language)
    important_questions = generate_questions(context, question_count, language)

    # Convert questions list to string format if required by model definition, or pass directly depending on model
    # (Humne aapke models.py ke hisaab se important_questions ko Text column rakha hai, isliye stringify kar rahe hain)
    questions_text = json.dumps(important_questions) if isinstance(important_questions, list) else str(important_questions)

    # Save to Database
    history_entry = StudyGuideHistory(
        user_id=current_user.id,
        document_id=document_id,
        filename=pdf.filename,
        language=language,
        summary=summary,
        important_questions=questions_text
    )
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    return {
        "id": history_entry.id,
        "document_id": document_id,
        "filename": pdf.filename,
        "language": language,
        "summary": summary,
        "important_questions": important_questions
    }