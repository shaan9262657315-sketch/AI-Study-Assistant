from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import requests

from dependencies import get_current_user
from models import Student


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

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            },
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        return {
            "answer": result.get(
                "response",
                "Sorry, I could not generate an answer."
            )
        }

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
            detail=f"AI error: {str(e)}"
        )