import os
import time
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import Student, ChatHistory

try:
    from gemini import ask_gemini
except ImportError:
    ask_gemini = None

router = APIRouter(
    prefix="/chat",
    tags=["AI Chat"]
)

class ChatRequest(BaseModel):
    question: str
    provider: str = None

def get_ai_response(prompt: str, requested_provider: str = None):
    gemini_key = os.getenv("GEMINI_API_KEY")
    provider = requested_provider or os.getenv("AI_PROVIDER", "ollama" if not gemini_key else "gemini")

    # 1. Try Gemini if requested and key exists
    if provider == "gemini" and gemini_key and ask_gemini:
        return ask_gemini(prompt)
    
    # 2. Direct Local Ollama HTTP call (Bypasses import issues completely)
    try:
        ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model_name = os.getenv("OLLAMA_MODEL", "llama3") # Change model name if you use mistral/phi3 etc.
        
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        print(f"Ollama local connection error: {e}")

    # 3. Fallback to Gemini if Ollama fails and key is available
    if ask_gemini and gemini_key:
        return ask_gemini(prompt)
        
    raise HTTPException(
        status_code=500,
        detail="Ollama is not running locally and GEMINI_API_KEY is not configured."
    )

@router.post("/ask")
def ask_chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    if not data.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    prompt = f"""
You are an AI Study Assistant.
Answer the following question clearly and accurately in simple language.

Question:
{data.question}
"""

    max_retries = 3
    retry_delays = [2, 5, 10]
    last_error = None

    for attempt in range(max_retries):
        try:
            answer = get_ai_response(prompt, data.provider)

            if answer:
                history = ChatHistory(
                    user_id=current_user.id,
                    question=data.question.strip(),
                    answer=answer.strip()
                )
                db.add(history)
                db.commit()
                db.refresh(history)

                return {
                    "id": history.id,
                    "answer": answer,
                    "created_at": history.created_at.isoformat() if history.created_at else None
                }

            last_error = "AI returned an empty response."

        except Exception as e:
            last_error = str(e)
            error_text = str(e).lower()

            temporary_error = any(x in error_text for x in ["503", "unavailable", "high demand", "overloaded"])

            if temporary_error and attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
                continue

            if not temporary_error:
                break

    raise HTTPException(
        status_code=503,
        detail=f"AI service temporarily unavailable: {last_error}"
    )

@router.get("/history")
def get_chat_history(db: Session = Depends(get_db), current_user: Student = Depends(get_current_user)):
    history = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id).order_by(ChatHistory.id.desc()).all()
    return [{
        "id": item.id,
        "question": item.question,
        "answer": item.answer,
        "created_at": item.created_at.isoformat() if item.created_at else None
    } for item in history]

@router.get("/history/{history_id}")
def get_single_chat(history_id: int, db: Session = Depends(get_db), current_user: Student = Depends(get_current_user)):
    history = db.query(ChatHistory).filter(ChatHistory.id == history_id, ChatHistory.user_id == current_user.id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Chat history not found")
    return {
        "id": history.id,
        "question": history.question,
        "answer": history.answer,
        "created_at": history.created_at.isoformat() if history.created_at else None
    }

@router.delete("/history/{history_id}")
def delete_chat_history(history_id: int, db: Session = Depends(get_db), current_user: Student = Depends(get_current_user)):
    history = db.query(ChatHistory).filter(ChatHistory.id == history_id, ChatHistory.user_id == current_user.id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Chat history not found")
    db.delete(history)
    db.commit()
    return {"message": "Chat history deleted successfully", "id": history_id}

@router.delete("/history")
def delete_all_chat_history(db: Session = Depends(get_db), current_user: Student = Depends(get_current_user)):
    deleted_count = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id).delete(synchronize_session=False)
    db.commit()
    return {"message": "All chat history deleted successfully", "deleted_count": deleted_count}