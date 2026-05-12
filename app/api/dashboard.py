"""
Dashboard API Routes - FastAPI
Tableau de bord enseignant avec statistiques
"""
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app import SessionLocal
from app.models.user import User
from app.models.exercise import Exercise, ExerciseAttempt
from app.models.progress import UserProgress
from app.models.scenario import Scenario
from app.api.auth import get_current_user

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Dépendance DB
# ─────────────────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────────────────────
# Vérification enseignant
# ─────────────────────────────────────────────────────────────────────────────
def require_teacher(current_user: User = Depends(get_current_user)):
    if not current_user.is_teacher():
        raise HTTPException(status_code=403, detail="Unauthorized")
    return current_user

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/stats")
def get_stats(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for teachers"""
    total_students = db.query(User).filter_by(role='student').count()
    total_teachers = db.query(User).filter(User.role.in_(['teacher', 'admin'])).count()
    total_exercises = db.query(Exercise).count()
    total_attempts = db.query(ExerciseAttempt).count()
    correct_attempts = db.query(ExerciseAttempt).filter_by(is_correct=True).count()
    success_rate = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0

    module_stats = db.query(
        Exercise.module,
        func.count(ExerciseAttempt.id).label('attempts'),
        func.avg(ExerciseAttempt.score).label('avg_score')
    ).outerjoin(ExerciseAttempt).group_by(Exercise.module).all()

    recent_attempts = db.query(ExerciseAttempt).order_by(desc(ExerciseAttempt.created_at)).limit(10).all()

    top_students = db.query(
        User,
        func.sum(ExerciseAttempt.score).label('total_score'),
        func.count(ExerciseAttempt.id).label('attempt_count')
    ).join(ExerciseAttempt).group_by(User.id).order_by(desc('total_score')).limit(10).all()

    return {
        'overview': {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_exercises': total_exercises,
            'total_attempts': total_attempts,
            'success_rate': round(success_rate, 2)
        },
        'module_stats': [
            {
                'module': m.module,
                'attempts': m.attempts,
                'avg_score': round(m.avg_score, 2) if m.avg_score else 0
            } for m in module_stats
        ],
        'recent_activity': [a.to_dict() for a in recent_attempts],
        'top_students': [
            {
                'user': s.User.to_dict(),
                'total_score': s.total_score,
                'attempt_count': s.attempt_count
            } for s in top_students
        ]
    }

@router.get("/students")
def get_students(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """Get detailed student information"""
    students = db.query(User).filter_by(role='student').all()
    result = []
    for student in students:
        progress = db.query(UserProgress).filter_by(user_id=student.id).all()
        attempts = db.query(ExerciseAttempt).filter_by(user_id=student.id).count()
        correct = db.query(ExerciseAttempt).filter_by(user_id=student.id, is_correct=True).count()
        result.append({
            'student': student.to_dict(),
            'progress': [p.to_dict() for p in progress],
            'stats': {
                'total_attempts': attempts,
                'correct_attempts': correct,
                'success_rate': round(correct / attempts * 100, 2) if attempts > 0 else 0
            }
        })
    return {'students': result}

@router.get("/student/{student_id}")
def get_student_detail(
    student_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific student"""
    student = db.query(User).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    attempts = db.query(ExerciseAttempt).filter_by(user_id=student_id).order_by(desc(ExerciseAttempt.created_at)).all()
    progress = db.query(UserProgress).filter_by(user_id=student_id).all()
    time_per_module = {p.module: p.time_spent for p in progress}

    return {
        'student': student.to_dict(),
        'attempts': [a.to_dict() for a in attempts],
        'progress': [p.to_dict() for p in progress],
        'time_per_module': time_per_module
    }

@router.get("/exercises")
def get_exercise_stats(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """Get exercise statistics"""
    exercises = db.query(Exercise).all()
    result = []
    for exercise in exercises:
        attempts_query = db.query(ExerciseAttempt).filter_by(exercise_id=exercise.id)
        total = attempts_query.count()
        correct = attempts_query.filter_by(is_correct=True).count()
        avg_score = attempts_query.with_entities(func.avg(ExerciseAttempt.score)).scalar()
        avg_time = attempts_query.with_entities(func.avg(ExerciseAttempt.time_spent)).scalar()
        result.append({
            'exercise': exercise.to_dict(),
            'stats': {
                'total_attempts': total,
                'correct_attempts': correct,
                'success_rate': round(correct / total * 100, 2) if total > 0 else 0,
                'avg_score': round(avg_score, 2) if avg_score else 0,
                'avg_time': round(avg_time, 2) if avg_time else 0
            }
        })
    return {'exercises': result}

@router.get("/scenarios")
def get_scenario_stats(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """Get scenario usage statistics"""
    scenarios = db.query(Scenario).filter_by(created_by=teacher.id).all()
    return {'scenarios': [s.to_dict() for s in scenarios]}