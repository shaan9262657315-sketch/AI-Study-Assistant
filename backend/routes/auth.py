from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import create_access_token, hash_password, verify_password
from database import get_db
from models import Student
from schemas import LoginRequest, RegisterRequest, TokenResponse


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", response_model=TokenResponse)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(Student)
        .filter(Student.email == data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    student = Student(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),
        branch=data.branch,
        year=data.year
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    token = create_access_token({
        "sub": student.email
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    student = (
        db.query(Student)
        .filter(Student.email == data.email)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(data.password, student.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token({
        "sub": student.email
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout():
    return {
        "message": "Logout successful. Remove the token from frontend storage."
    }