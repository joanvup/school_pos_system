from sqlalchemy.orm import Session
from app.models.user import Student
from app.schemas.student import StudentCreate, StudentUpdate
from sqlalchemy import and_, or_ 

def create_student(db: Session, student: StudentCreate):
    db_student = Student(
        full_name=student.full_name,
        grade=student.grade,
        parent_id=student.parent_id
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

def get_student(db: Session, student_id: int):
    return db.query(Student).filter(Student.id == student_id).first()

def get_students(db: Session, skip: int = 0, limit: int = 100, search: str = None):
    query = db.query(Student)
    
    if search:
        search_words = search.strip().split()
        if search_words:
            conditions = []
            for word in search_words:
                # La palabra debe estar en el nombre completo
                conditions.append(Student.full_name.ilike(f"%{word}%"))
            
            query = query.filter(and_(*conditions))
            
    return query.offset(skip).limit(limit).all()

def get_students_by_parent(db: Session, parent_id: int):
    return db.query(Student).filter(Student.parent_id == parent_id).all()

def update_student(db: Session, db_student: Student, student_in: StudentUpdate):
    update_data = student_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_student, key, value)
    
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student