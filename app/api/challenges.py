"""Challenges API"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app import SessionLocal
from app.models.challenge import Challenge, ChallengeSubmission
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
        User.full_name,
        func.sum(ChallengeSubmission.score).label('total_score')
    ).join(ChallengeSubmission).filter(
        ChallengeSubmission.challenge_id == challenge_id
    ).group_by(User.id).order_by(desc('total_score')).limit(20).all()

    return {
        "leaderboard": [
            {"name": r[0], "score": float(r[1] or 0)} for r in results
        ]
    }

@router.post("/{challenge_id}/submit")
def submit_challenge(
    challenge_id: int,
    exercise_id: int,
    score: float,
    is_correct: bool,
    time_spent: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soumettre une réponse à un challenge."""
    submission = ChallengeSubmission(
        challenge_id=challenge_id,
        user_id=current_user.id,
        exercise_id=exercise_id,
        score=score,
        is_correct=is_correct,
        time_spent=time_spent,
    )
    db.add(submission)
    db.commit()
    return {"message": "Réponse soumise.", "submission": submission.to_dict()}