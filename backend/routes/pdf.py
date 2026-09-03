import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import PDFDocument, Student
from rag import (
    ask_question,
    index_pdf,
    load_existing_pdfs,
    remove_document
)
from schemas import PDFAskRequest, PDFAskResponse


router = APIRouter(
    prefix="/pdf",
    tags=["PDF"]
)


PDF_FOLDER = "pdfs"
os.makedirs(PDF_FOLDER, exist_ok=True)


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    document_id = str(uuid.uuid4())

    safe_filename = os.path.basename(file.filename)

    stored_filename = (
        f"{document_id}_{safe_filename}"
    )

    file_path = os.path.join(
        PDF_FOLDER,
        stored_filename
    )

    content = await file.read()

    with open(file_path, "wb") as pdf_file:
        pdf_file.write(content)

    try:
        page_count = index_pdf(
            file_path,
            document_id,
            safe_filename
        )
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=400,
            detail="Could not process PDF"
        )

    record = PDFDocument(
        document_id=document_id,
        filename=safe_filename,
        file_path=file_path,
        page_count=page_count
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "PDF uploaded successfully",
        "document_id": document_id,
        "filename": safe_filename,
        "page_count": page_count
    }


@router.get("/library")
def get_pdf_library(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    records = (
        db.query(PDFDocument)
        .order_by(PDFDocument.id.desc())
        .all()
    )

    return [
        {
            "document_id": record.document_id,
            "filename": record.filename,
            "page_count": record.page_count,
            "uploaded_at": (
                record.uploaded_at.isoformat()
                if record.uploaded_at
                else None
            )
        }
        for record in records
    ]


@router.get("/library/{document_id}")
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    record = (
        db.query(PDFDocument)
        .filter(
            PDFDocument.document_id == document_id
        )
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="PDF not found"
        )

    return {
        "document_id": record.document_id,
        "filename": record.filename,
        "page_count": record.page_count,
        "uploaded_at": (
            record.uploaded_at.isoformat()
            if record.uploaded_at
            else None
        )
    }


@router.delete("/library/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    record = (
        db.query(PDFDocument)
        .filter(
            PDFDocument.document_id == document_id
        )
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="PDF not found"
        )

    if os.path.exists(record.file_path):
        os.remove(record.file_path)

    remove_document(document_id)

    db.delete(record)
    db.commit()

    return {
        "message": "PDF deleted successfully",
        "document_id": document_id
    }


@router.post("/reload")
def reload_pdf_library(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    records = db.query(PDFDocument).all()

    load_existing_pdfs(records)

    return {
        "message": "PDF library reloaded",
        "documents_loaded": len(records)
    }


@router.post("/ask", response_model=PDFAskResponse)
def ask_pdf_question(
    data: PDFAskRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    result = ask_question(
        question=data.question,
        mode=data.mode,
        language=data.language,
        selected_documents=data.selected_documents,
        top_k=data.top_k
    )

    return result