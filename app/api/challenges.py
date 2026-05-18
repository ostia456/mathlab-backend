"""Challenges API"""
from datetime import date, timedelta
import random as pyrandom
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel, Field

from app import SessionLocal
from app.models.user import User
from app.models.exercise import Exercise
from app.models.challenge import Challenge, ChallengeExercise, ChallengeSubmission
from app.api.auth import get_current_user
from sqlalchemy.sql.expression import func as sqlfunc

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Schémas ──────────────────────────────────────────────────────────────────
class CreateChallengeRequest(BaseModel):
    template_id: str = Field(default='weekly_all')
    title: str
    description: str = ''
    module: str = Field(default='all')
    period: str = Field(default='weekly')
    duration_days: float = Field(default=7)
    exercise_count: int = Field(default=5, ge=1, le=20)
    difficulty: int = Field(default=1, ge=1, le=5)


class SubmitChallengeRequest(BaseModel):
    exercise_id: int
    score: float
    is_correct: bool
    time_spent: int = 0


# ── Routes ───────────────────────────────────────────────────────────────────
@router.get("/")
def list_challenges(db: Session = Depends(get_db)):
    """Liste tous les challenges."""
    challenges = db.query(Challenge).order_by(desc(Challenge.start_date)).limit(10).all()
    return {"challenges": [c.to_dict() for c in challenges]}


@router.get("/active")
def get_active_challenge(db: Session = Depends(get_db)):
    """Retourne le challenge en cours."""
    today = date.today()
    challenge = db.query(Challenge).filter(
        Challenge.start_date <= today,
        Challenge.end_date >= today,
        Challenge.is_active == True
    ).first()
    if not challenge:
        return {"challenge": None, "message": "Aucun challenge en cours."}
    return {"challenge": challenge.to_dict()}


@router.get("/{challenge_id}")
def get_challenge(challenge_id: int, db: Session = Depends(get_db)):
    """Détail d'un challenge."""
    challenge = db.query(Challenge).get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge introuvable.")
    return {"challenge": challenge.to_dict()}


@router.get("/{challenge_id}/leaderboard")
def get_leaderboard(challenge_id: int, db: Session = Depends(get_db)):
    """Classement d'un challenge."""
    results = db.query(
        User.first_name,
        User.last_name,
        func.sum(ChallengeSubmission.score).label('total_score')
    ).join(ChallengeSubmission).filter(
        ChallengeSubmission.challenge_id == challenge_id
    ).group_by(User.id).order_by(desc('total_score')).limit(20).all()

    return {
        "leaderboard": [
            {"name": f"{r[0]} {r[1]}", "score": float(r[2] or 0)} for r in results
        ]
    }


@router.get("/{challenge_id}/exercises")
def get_challenge_exercises(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retourne les exercices d'un challenge avec les soumissions de l'utilisateur."""
    challenge = db.query(Challenge).get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge introuvable.")

    exercises = db.query(ChallengeExercise).filter_by(
        challenge_id=challenge_id
    ).order_by(ChallengeExercise.order_num).all()

    submissions = db.query(ChallengeSubmission).filter_by(
        challenge_id=challenge_id, user_id=current_user.id
    ).all()

    return {
        "exercises": [
            {
                "id": e.id,
                "exercise_id": e.exercise_id,
                "points": e.points,
                "order_num": e.order_num,
                "problem_data": db.query(Exercise).get(e.exercise_id).problem_data,
                "solution_data": db.query(Exercise).get(e.exercise_id).solution_data,
            } for e in exercises
        ],
        "submissions": [s.to_dict() for s in submissions],
    }


@router.post("/create")
def create_challenge(
    data: CreateChallengeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée un challenge (admin/super_admin seulement)."""
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs.")

    today = date.today()
    if data.duration_days >= 1:
        end_date = today + timedelta(days=int(data.duration_days))
    else:
        end_date = today + timedelta(hours=int(data.duration_days * 24))

    challenge = Challenge(
        title=data.title,
        description=data.description,
        module=data.module,
        period=data.period,
        start_date=today,
        end_date=end_date,
        is_active=True,
    )
    db.add(challenge)
    db.flush()

    modules = ['dynamical_systems', 'numerical_methods', 'linear_algebra', 'graph_theory']
    if data.module != 'all':
        modules = [data.module]

    selected_exercises = []
    used_ids = set()

    for i in range(data.exercise_count):
        module = modules[i % len(modules)]
        available = db.query(Exercise).filter(
            Exercise.module == module,
            Exercise.difficulty == data.difficulty,
            ~Exercise.id.in_(used_ids)
        ).all()

        if available:
            exercise = pyrandom.choice(available)
        else:
            exercise = db.query(Exercise).filter(
                Exercise.module == module,
                Exercise.difficulty == data.difficulty
            ).order_by(sqlfunc.random()).first()

        if exercise and exercise.id not in used_ids:
            used_ids.add(exercise.id)
            selected_exercises.append(exercise)

    for i, exercise in enumerate(selected_exercises):
        ce = ChallengeExercise(
            challenge_id=challenge.id,
            exercise_id=exercise.id,
            points=10 + (i * 2),
            order_num=i + 1,
        )
        db.add(ce)

    db.commit()
    return {"message": "Challenge créé.", "challenge": challenge.to_dict()}


@router.post("/{challenge_id}/submit")
def submit_challenge(
    challenge_id: int,
    data: SubmitChallengeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soumettre une réponse à un challenge."""
    submission = ChallengeSubmission(
        challenge_id=challenge_id,
        user_id=current_user.id,
        exercise_id=data.exercise_id,
        score=data.score,
        is_correct=data.is_correct,
        time_spent=data.time_spent,
    )
    db.add(submission)
    db.commit()
    return {"message": "Réponse soumise.", "submission": submission.to_dict()}


@router.delete("/{challenge_id}")
def delete_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime un challenge (admin/super_admin seulement)."""
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs.")

    db.query(ChallengeSubmission).filter_by(challenge_id=challenge_id).delete()
    db.query(ChallengeExercise).filter_by(challenge_id=challenge_id).delete()
    db.query(Challenge).filter_by(id=challenge_id).delete()
    db.commit()
    return {"message": "Challenge supprimé."}