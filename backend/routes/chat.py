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

    try:
        answer = ask_gemini(prompt)

        return {
            "answer": answer
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI error: {str(e)}"
        )
