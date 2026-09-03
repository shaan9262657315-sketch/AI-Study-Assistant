from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import Student
from schemas import StudentCreate, StudentResponse, StudentUpdate


router = APIRouter(
    prefix="/students",
    tags=["Students"]
)


@router.post("/", response_model=StudentResponse)
def create_student(
    data: StudentCreate,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    existing = (
        db.query(Student)
        .filter(Student.email == data.email)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    student = Student(
        name=data.name,
        email=data.email,
        password=data.password,
        branch=data.branch,
        year=data.year
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    return student


@router.get("/", response_model=list[StudentResponse])
def get_students(
    search: Optional[str] = None,
    branch: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    query = db.query(Student)

    if search:
        query = query.filter(
            Student.name.ilike(f"%{search}%")
        )

    if branch:
        query = query.filter(
            Student.branch == branch
        )

    offset = (page - 1) * limit

    return query.offset(offset).limit(limit).all()


@router.get("/branches")
def get_branches(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    branches = (
        db.query(Student.branch)
        .distinct()
        .order_by(Student.branch)
        .all()
    )

    return {
        "branches": [branch[0] for branch in branches]
    }


@router.get("/statistics")
def get_statistics(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    total = db.query(Student).count()

    branches = (
        db.query(Student.branch)
        .distinct()
        .count()
    )

    return {
        "total_students": total,
        "total_branches": branches
    }


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return student


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(student, key, value)

    db.commit()
    db.refresh(student)

    return student


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    db.delete(student)
    db.commit()

    return {
        "message": "Student deleted successfully"
    }