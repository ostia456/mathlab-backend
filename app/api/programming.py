"""
Programming Challenges API
"""
import subprocess
import tempfile
import os
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app import SessionLocal
from app.models.user import User
from app.models.programming import ProgrammingChallenge, ProgrammingSubmission
from app.api.auth import get_current_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Schémas ──────────────────────────────────────────────────────────────────
class SubmitCodeRequest(BaseModel):
    code: str
    language: str = 'python'


# ── Exécution sécurisée ─────────────────────────────────────────────────────
def execute_python_code(code: str) -> dict:
    """Exécute le code Python dans un processus séparé avec timeout."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            filepath = f.name

        start_time = time.time()
        result = subprocess.run(
            ['python3', filepath],
            capture_output=True,
            text=True,
            timeout=10,
        )
        execution_time = (time.time() - start_time) * 1000

        os.unlink(filepath)

        if result.returncode == 0:
            return {
                'status': 'success',
                'score': 100,
                'execution_time': round(execution_time, 2),
                'output': result.stdout.strip(),
            }
        else:
            return {
                'status': 'error',
                'score': 0,
                'execution_time': round(execution_time, 2),
                'error': result.stderr.strip() or result.stdout.strip(),
            }

    except subprocess.TimeoutExpired:
        return {'status': 'timeout', 'score': 0, 'error': 'Temps limite dépassé (10s).'}
    except Exception as e:
        return {'status': 'error', 'score': 0, 'error': str(e)}


# ── Routes ───────────────────────────────────────────────────────────────────
@router.get("/")
def list_challenges(db: Session = Depends(get_db)):
    """Liste tous les défis de programmation."""
    challenges = db.query(ProgrammingChallenge).filter_by(is_active=True).order_by(
        ProgrammingChallenge.created_at.desc()
    ).all()
    return {"challenges": [c.to_dict() for c in challenges]}
@router.get("/leaderboard")
def get_global_leaderboard(db: Session = Depends(get_db)):
    """Classement global programmation."""
    from sqlalchemy import func, desc
    results = db.query(
        User.first_name,
        User.last_name,
        func.sum(ProgrammingSubmission.score).label('total_score'),
        func.min(ProgrammingSubmission.execution_time).label('best_time'),
    ).join(ProgrammingSubmission).filter(
        ProgrammingSubmission.status == 'success'
    ).group_by(User.id).order_by(desc('total_score')).limit(20).all()

    return {
        "leaderboard": [
            {
                "name": f"{r[0]} {r[1]}",
                "score": float(r[2] or 0),
                "time": float(r[3] or 0) if r[3] else None,
            } for r in results
        ]
    }

@router.get("/{challenge_id}")
def get_challenge(challenge_id: int, db: Session = Depends(get_db)):
    """Détail d'un défi (sans solution)."""
    challenge = db.query(ProgrammingChallenge).get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Défi introuvable.")
    return {"challenge": challenge.to_dict(include_solution=False)}


@router.post("/{challenge_id}/submit")
def submit_code(
    challenge_id: int,
    data: SubmitCodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soumettre du code pour un défi."""
    challenge = db.query(ProgrammingChallenge).get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Défi introuvable.")

    result = execute_python_code(data.code)

    submission = ProgrammingSubmission(
        challenge_id=challenge_id,
        user_id=current_user.id,
        code=data.code,
        language=data.language,
        status=result['status'],
        score=result['score'],
        execution_time=result.get('execution_time'),
        output=result.get('output'),
        error_message=result.get('error'),
    )
    db.add(submission)
    db.commit()

    return {"submission": submission.to_dict(), "result": result}

class CreateProgrammingRequest(BaseModel):
    title: str
    description: str
    difficulty: str = 'Facile'
    points: int = 100
    example_input: str = ''
    example_output: str = ''
    starter_code: str = ''
    test_cases: list = []

@router.post("/create")
def create_programming_challenge(
    data: CreateProgrammingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée un défi de programmation (admin seulement)."""
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs.")
    
    challenge = ProgrammingChallenge(
        title=data.title,
        description=data.description,
        difficulty=data.difficulty,
        points=data.points,
        example_input=data.example_input,
        example_output=data.example_output,
        starter_code=data.starter_code,
        test_cases=data.test_cases,
        is_active=True,
    )
    db.add(challenge)
    db.commit()
    return {"message": "Défi créé.", "challenge": challenge.to_dict()}

