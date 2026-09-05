import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dependencies import get_current_user
from models import Student
from gemini import ask_gemini


router = APIRouter(
    prefix="/chat",
    tags=["AI Chat"]
)


class ChatRequest(BaseModel):
    question: str


@router.post("/ask")
def ask_chat(
    data: ChatRequest,
    current_user: Student = Depends(get_current_user)
):

    if not data.question.strip():

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    prompt = f"""
You are an AI Study Assistant.

Answer the following question clearly and accurately.

Question:
{data.question}

Give the answer in simple language.
"""

    # =====================================================
    # GEMINI REQUEST WITH RETRY
    # =====================================================

    max_retries = 3

    retry_delays = [
        2,
        5,
        10
    ]

    last_error = None

    for attempt in range(max_retries):

        try:

            answer = ask_gemini(
                prompt
            )

            if answer:

                return {
                    "answer": answer
                }

            last_error = "Gemini returned an empty response."

        except Exception as e:

            last_error = str(e)

            error_text = str(e).lower()

            # ---------------------------------------------
            # TEMPORARY GEMINI ERROR
            # ---------------------------------------------

            temporary_error = (
                "503" in error_text
                or
                "unavailable" in error_text
                or
                "high demand" in error_text
                or
                "overloaded" in error_text
            )

            if temporary_error:

                if attempt < max_retries - 1:

                    time.sleep(
                        retry_delays[attempt]
                    )

                    continue

                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Gemini is temporarily unavailable. "
                        "Please try again in a few moments."
                    )
                )

            # ---------------------------------------------
            # OTHER GEMINI ERROR
            # ---------------------------------------------

            raise HTTPException(
                status_code=500,
                detail=f"AI error: {last_error}"
            )

    # =====================================================
    # FINAL FALLBACK
    # =====================================================

    raise HTTPException(
        status_code=503,
        detail=(
            "Gemini is temporarily unavailable. "
            "Please try again later."
        )
    )