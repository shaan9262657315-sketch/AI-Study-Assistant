import json
import re
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import rag

from database import get_db
from dependencies import get_current_user
from models import Student, PDFDocument, QuizHistory

from schemas import (
    QuizGenerateRequest,
    QuizResponse,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/quiz",
    tags=["Quiz"]
)


# =========================================================
# CONFIG
# =========================================================

MAX_QUESTION_COUNT = 20
DEFAULT_QUESTION_COUNT = 5
MAX_CONTEXT_LENGTH = 30000
MAX_RETRY = 2


# =========================================================
# AI
# =========================================================

def call_ai(prompt: str) -> str:
    """
    AI generation goes through rag.generate_answer().

    Local development:
        Ollama

    Production:
        Gemini 3.8 Flash

    Provider selection remains inside rag.py.
    """

    return rag.generate_answer(
        question=prompt,
        context="",
        language="english",
        outside_knowledge=True
    )


# =========================================================
# JSON PARSER
# =========================================================

def extract_json(text: Optional[str]):
    if not text:
        return None

    text = str(text).strip()

    # Remove markdown fences
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    # Direct JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # JSON inside extra text
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        return json.loads(
            text[start:end + 1]
        )
    except json.JSONDecodeError:
        return None


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)

    # Fix common AI spacing problems
    replacements = {
        "Whatis": "What is",
        "Whichis": "Which is",
        "Whichof": "Which of",
        "Thepurposeof": "The purpose of",
        "usedto": "used to",
        "usedfor": "used for",
        "methodand": "method and",
        "afinal": "a final",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Normal whitespace
    text = text.replace(
        "\u00a0",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# QUIZ VALIDATION
# =========================================================

def validate_quiz(
    data: Dict[str, Any],
    expected_count: int
):
    if not isinstance(data, dict):
        return None

    questions = data.get("questions")

    if not isinstance(questions, list):
        return None

    valid_questions = []
    seen = set()

    for item in questions:

        if not isinstance(item, dict):
            continue

        question = clean_text(
            item.get("question")
        )

        options = item.get("options")

        correct_answer = clean_text(
            item.get("correct_answer")
        )

        explanation = clean_text(
            item.get("explanation")
        )

        # Required fields
        if not question:
            continue

        if not isinstance(options, list):
            continue

        if not correct_answer:
            continue

        if not explanation:
            continue

        # Exactly 4 options
        if len(options) != 4:
            continue

        options = [
            clean_text(option)
            for option in options
        ]

        # Empty option
        if any(not option for option in options):
            continue

        # Duplicate options
        normalized_options = [
            re.sub(
                r"\s+",
                " ",
                option.lower()
            ).strip()
            for option in options
        ]

        if len(set(normalized_options)) != 4:
            continue

        # Correct answer must exist
        correct_normalized = re.sub(
            r"\s+",
            " ",
            correct_answer.lower()
        ).strip()

        matched_answer = None

        for option in options:

            option_normalized = re.sub(
                r"\s+",
                " ",
                option.lower()
            ).strip()

            if option_normalized == correct_normalized:
                matched_answer = option
                break

        if matched_answer is None:
            continue

        correct_answer = matched_answer

        # Duplicate question detection
        normalized_question = re.sub(
            r"[^a-z0-9\s]",
            "",
            question.lower()
        )

        normalized_question = re.sub(
            r"\s+",
            " ",
            normalized_question
        ).strip()

        if normalized_question in seen:
            continue

        seen.add(normalized_question)

        # Basic quality check
        if len(question) < 15:
            continue

        if len(explanation) < 20:
            continue

        valid_questions.append({
            "question": question,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation
        })

        if len(valid_questions) >= expected_count:
            break

    if len(valid_questions) < expected_count:
        return None

    return valid_questions[:expected_count]


# =========================================================
# TOPIC PROMPT
# =========================================================

def build_topic_prompt(
    topic: str,
    difficulty: str,
    question_count: int
) -> str:

    return f"""
You are an expert university-level AI Study Assistant.

Generate an academic multiple-choice quiz.

TOPIC:
{topic}

DIFFICULTY:
{difficulty}

Generate exactly {question_count} questions.

IMPORTANT:
Return ONLY valid JSON.

Do NOT return:
- Markdown
- ```json
- ``` 
- introductory text
- concluding text
- comments

Use exactly this JSON structure:

{{
  "questions": [
    {{
      "question": "Clear academic question?",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_answer": "Exact text of the correct option",
      "explanation": "Clear explanation of why the answer is correct."
    }}
  ]
}}

RULES:

1. Generate exactly {question_count} questions.

2. Every question must be factually correct.

3. Every question must have exactly 4 options.

4. Exactly ONE option must be correct.

5. correct_answer MUST exactly match one option.

6. Options must be realistic and plausible.

7. Distractors should represent common student mistakes.

8. Do not use:
   - None of the above
   - All of the above
   - Both
   - It depends

9. Use clean English.

10. Never join words together.

WRONG:
Whatis inheritance?

CORRECT:
What is inheritance?

11. Do not generate duplicate questions.

12. Do not repeatedly ask the same concept.

13. Mix:
   - conceptual questions
   - application questions
   - reasoning
   - comparisons
   - important exam concepts

14. Difficulty must be genuinely {difficulty}.

15. Explanations must clearly explain why the correct answer is correct.

FINAL CHECK BEFORE RESPONSE:

- Exactly {question_count} questions
- Exactly 4 options each
- One correct answer
- correct_answer matches an option
- No duplicate questions
- No duplicate options
- Clean English
- Proper spacing

Return ONLY JSON.
"""


# =========================================================
# PDF PROMPT
# =========================================================

def build_pdf_prompt(
    context: str,
    topic: Optional[str],
    chapter: Optional[str],
    difficulty: str,
    question_count: int
) -> str:

    topic_text = (
        topic.strip()
        if topic and topic.strip()
        else "PDF concepts"
    )

    chapter_text = (
        chapter.strip()
        if chapter and chapter.strip()
        else "selected PDF content"
    )

    return f"""
You are an expert university-level AI Study Assistant.

Generate an academic multiple-choice quiz using ONLY
the supplied PDF content.

TOPIC:
{topic_text}

CHAPTER:
{chapter_text}

DIFFICULTY:
{difficulty}

Generate exactly {question_count} questions.

CRITICAL SOURCE RULE:

Use ONLY information present in the supplied PDF content.

Do NOT:
- use outside knowledge
- guess
- extrapolate
- invent facts
- assume missing information

Return ONLY valid JSON.

Do NOT return Markdown or ```json.

Use exactly this structure:

{{
  "questions": [
    {{
      "question": "Clear question derived from the PDF?",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_answer": "Exact text of the correct option",
      "explanation": "Explanation based strictly on the PDF."
    }}
  ]
}}

RULES:

1. Exactly {question_count} questions.

2. Exactly 4 options per question.

3. Exactly ONE correct option.

4. correct_answer must exactly match one option.

5. Every question must be directly answerable from the PDF.

6. Do not use unsupported outside knowledge.

7. Options must be realistic and plausible.

8. Do not use:
   - None of the above
   - All of the above
   - Both
   - It depends

9. Use clean English spacing.

10. Do not create duplicate questions.

11. Mix conceptual, application, reasoning,
    comparison and exam-oriented questions.

12. Explanations must be supported by the PDF.

FINAL CHECK:

- Exactly {question_count} questions
- Exactly 4 options
- One correct answer
- correct_answer matches an option
- No duplicate questions
- No duplicate options
- No unsupported claims
- Clean English

PDF CONTENT:

{context}

Return ONLY JSON.
"""


# =========================================================
# TOPIC QUIZ GENERATION
# =========================================================

def generate_topic_quiz(
    topic: str,
    difficulty: str,
    question_count: int
):

    prompt = build_topic_prompt(
        topic=topic,
        difficulty=difficulty,
        question_count=question_count
    )

    for attempt in range(MAX_RETRY + 1):

        current_prompt = prompt

        if attempt > 0:

            current_prompt += f"""

RETRY {attempt}

The previous response failed validation.

Generate a completely NEW quiz.

Do not repeat previous questions.

Pay special attention to:

- factual correctness
- exactly 4 options
- exactly one correct answer
- correct_answer matching an option
- clean English spacing
- realistic distractors
- no duplicate questions
"""

        raw = call_ai(
            current_prompt
        )

        data = extract_json(raw)

        questions = validate_quiz(
            data,
            question_count
        )

        if questions is not None:
            return questions

    raise HTTPException(
        status_code=500,
        detail="AI failed to generate a valid quiz. Please try again."
    )


# =========================================================
# PDF CONTEXT
# =========================================================

def get_pdf_context(
    document: PDFDocument,
    topic: Optional[str] = None,
    chapter: Optional[str] = None
):

    context_parts = []

    try:

        if not hasattr(
            rag,
            "search_documents"
        ):
            return ""

        query_parts = []

        if topic:
            query_parts.append(
                topic.strip()
            )

        if chapter:
            query_parts.append(
                chapter.strip()
            )

        query = " ".join(
            query_parts
        ).strip()

        if not query:
            query = document.filename

        results = rag.search_documents(
            query=query,
            top_k=10,
            selected_documents=[
                document.document_id
            ]
        )

        if not results:
            return ""

        for item in results:

            if not isinstance(item, dict):
                continue

            text = item.get("text")

            if not text:
                continue

            page = item.get("page")

            if page is not None:

                context_parts.append(
                    f"[Page {page}]\n{text}"
                )

            else:

                context_parts.append(
                    str(text)
                )

    except Exception as e:

        print(
            "PDF Context Error:",
            e
        )

    context = "\n\n".join(
        context_parts
    )

    return context[:MAX_CONTEXT_LENGTH]


# =========================================================
# PDF QUIZ GENERATION
# =========================================================

def generate_pdf_quiz(
    context: str,
    topic: Optional[str],
    chapter: Optional[str],
    difficulty: str,
    question_count: int
):

    prompt = build_pdf_prompt(
        context=context,
        topic=topic,
        chapter=chapter,
        difficulty=difficulty,
        question_count=question_count
    )

    for attempt in range(MAX_RETRY + 1):

        current_prompt = prompt

        if attempt > 0:

            current_prompt += """

RETRY

The previous quiz failed validation.

Generate a completely NEW quiz.

Use ONLY the supplied PDF content.

Do not repeat previous questions.

Check:
- source grounding
- factual correctness
- exactly 4 options
- exactly one correct answer
- correct_answer matching an option
- clean grammar
"""

        raw = call_ai(
            current_prompt
        )

        data = extract_json(raw)

        questions = validate_quiz(
            data,
            question_count
        )

        if questions is not None:
            return questions

    raise HTTPException(
        status_code=500,
        detail="AI failed to generate a valid PDF quiz. Please try again."
    )


# =========================================================
# SAVE QUIZ HISTORY
# =========================================================

def save_quiz_history(
    db: Session,
    current_user: Student,
    topic: str,
    difficulty: str,
    questions: List[Dict[str, Any]]
):

    try:

        history = QuizHistory(
            user_id=current_user.id,
            topic=topic,
            difficulty=difficulty,
            questions=json.dumps(
                questions,
                ensure_ascii=False
            )
        )

        db.add(history)
        db.commit()
        db.refresh(history)

        return history

    except Exception as e:

        db.rollback()

        print(
            "Quiz History Error:",
            e
        )

        return None


# =========================================================
# GENERATE QUIZ API
# =========================================================

@router.post(
    "/generate",
    response_model=QuizResponse
)
def generate_quiz(

    data: QuizGenerateRequest,

    db: Session = Depends(get_db),

    current_user: Student = Depends(
        get_current_user
    )
):

    # -----------------------------------------------------
    # Question count
    # -----------------------------------------------------

    question_count = (
        data.question_count
        or DEFAULT_QUESTION_COUNT
    )

    question_count = max(
        1,
        min(
            question_count,
            MAX_QUESTION_COUNT
        )
    )

    # -----------------------------------------------------
    # Difficulty
    # -----------------------------------------------------

    difficulty = (
        data.difficulty
        or "medium"
    ).lower().strip()

    if difficulty not in {
        "easy",
        "medium",
        "hard"
    }:
        difficulty = "medium"

    # -----------------------------------------------------
    # Mode
    # -----------------------------------------------------

    mode = (
        data.mode
        or "topic"
    ).lower().strip()

    # =====================================================
    # TOPIC MODE
    # =====================================================

    if mode == "topic":

        if not data.topic or not data.topic.strip():

            raise HTTPException(
                status_code=400,
                detail="Please enter a topic."
            )

        topic = data.topic.strip()

        questions = generate_topic_quiz(
            topic=topic,
            difficulty=difficulty,
            question_count=question_count
        )

        save_quiz_history(
            db=db,
            current_user=current_user,
            topic=topic,
            difficulty=difficulty,
            questions=questions
        )

        return {
            "questions": questions
        }

    # =====================================================
    # PDF MODE
    # =====================================================

    if mode == "pdf":

        document = None

        # Search by document_id
        if getattr(
            data,
            "document_id",
            None
        ):

            document = (
                db.query(PDFDocument)
                .filter(
                    PDFDocument.document_id
                    == data.document_id
                )
                .first()
            )

        # Search by filename
        elif getattr(
            data,
            "filename",
            None
        ):

            document = (
                db.query(PDFDocument)
                .filter(
                    PDFDocument.filename
                    == data.filename
                )
                .first()
            )

        if document is None:

            raise HTTPException(
                status_code=404,
                detail="PDF document not found."
            )

        # Get RAG context
        context = get_pdf_context(
            document=document,
            topic=getattr(
                data,
                "topic",
                None
            ),
            chapter=getattr(
                data,
                "chapter",
                None
            )
        )

        if not context.strip():

            raise HTTPException(
                status_code=404,
                detail="No relevant content found in the selected PDF."
            )

        questions = generate_pdf_quiz(
            context=context,
            topic=getattr(
                data,
                "topic",
                None
            ),
            chapter=getattr(
                data,
                "chapter",
                None
            ),
            difficulty=difficulty,
            question_count=question_count
        )

        history_topic = (
            data.topic.strip()
            if getattr(
                data,
                "topic",
                None
            )
            and data.topic.strip()
            else f"PDF: {document.filename}"
        )

        save_quiz_history(
            db=db,
            current_user=current_user,
            topic=history_topic,
            difficulty=difficulty,
            questions=questions
        )

        return {
            "questions": questions
        }

    # =====================================================
    # INVALID MODE
    # =====================================================

    raise HTTPException(
        status_code=400,
        detail="Invalid quiz mode. Use 'topic' or 'pdf'."
    )


# =========================================================
# QUIZ HISTORY
# =========================================================

@router.get("/history")
def get_quiz_history(

    db: Session = Depends(get_db),

    current_user: Student = Depends(
        get_current_user
    )
):

    histories = (
        db.query(QuizHistory)
        .filter(
            QuizHistory.user_id
            == current_user.id
        )
        .order_by(
            QuizHistory.id.desc()
        )
        .all()
    )

    result = []

    for history in histories:

        try:
            questions = json.loads(
                history.questions
            )
        except Exception:
            questions = []

        result.append({
            "id": history.id,
            "topic": history.topic,
            "difficulty": history.difficulty,
            "questions": questions,
            "created_at": history.created_at
        })

    return result


# =========================================================
# DELETE ONE HISTORY
# =========================================================

@router.delete(
    "/history/{history_id}"
)
def delete_quiz_history(

    history_id: int,

    db: Session = Depends(get_db),

    current_user: Student = Depends(
        get_current_user
    )
):

    history = (
        db.query(QuizHistory)
        .filter(
            QuizHistory.id == history_id,
            QuizHistory.user_id == current_user.id
        )
        .first()
    )

    if history is None:

        raise HTTPException(
            status_code=404,
            detail="Quiz history not found."
        )

    db.delete(history)
    db.commit()

    return {
        "message": "Quiz history deleted successfully."
    }


# =========================================================
# DELETE ALL HISTORY
# =========================================================

@router.delete(
    "/history"
)
def delete_all_quiz_history(

    db: Session = Depends(get_db),

    current_user: Student = Depends(
        get_current_user
    )
):

    (
        db.query(QuizHistory)
        .filter(
            QuizHistory.user_id
            == current_user.id
        )
        .delete(
            synchronize_session=False
        )
    )

    db.commit()

    return {
        "message": "All quiz history deleted successfully."
    }