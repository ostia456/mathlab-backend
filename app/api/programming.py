"""Programming Challenges API"""
from datetime import date, timedelta
import subprocess, tempfile, os, time, resource
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel, Field

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


class SubmitCodeRequest(BaseModel):
    code: str
    language: str = 'python'


# ── Routes ───────────────────────────────────────────────────────────────────
@router.get("/")
def list_challenges(db: Session = Depends(get_db)):
    """Liste tous les défis de programmation."""
    challenges = db.query(ProgrammingChallenge).filter_by(is_active=True).order_by(
        ProgrammingChallenge.created_at.desc()
    ).all()
    return {"challenges": [c.to_dict() for c in challenges]}


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

    # Exécute le code
    result = execute_python_code(data.code, challenge.test_cases or [])

    submission = ProgrammingSubmission(
        challenge_id=challenge_id,
        user_id=current_user.id,
        code=data.code,
        language=data.language,
        status=result['status'],
        score=result['score'],
        execution_time=result.get('execution_time'),
        memory_used=result.get('memory_used'),
        output=result.get('output'),
        error_message=result.get('error'),
    )
    db.add(submission)
    db.commit()

    return {
        "submission": submission.to_dict(),
        "result": result,
    }


@router.get("/{challenge_id}/leaderboard")
def get_leaderboard(challenge_id: int, db: Session = Depends(get_db)):
    """Classement d'un défi."""
    results = db.query(
        User.first_name,
        User.last_name,
        func.max(ProgrammingSubmission.score).label('best_score'),
        func.min(ProgrammingSubmission.execution_time).label('best_time'),
    ).join(ProgrammingSubmission).filter(
        ProgrammingSubmission.challenge_id == challenge_id,
        ProgrammingSubmission.status == 'success'
    ).group_by(User.id).order_by(desc('best_score'), 'best_time').limit(20).all()

    return {
        "leaderboard": [
            {
                "name": f"{r[0]} {r[1]}",
                "score": float(r[2] or 0),
                "time": float(r[3] or 0) if r[3] else None,
            } for r in results
        ]
    }


# ── Exécution sécurisée ─────────────────────────────────────────────────────
def execute_python_code(code: str, test_cases: list) -> dict:
    """Exécute le code Python dans un processus séparé."""
    try:
        # Écrit le code dans un fichier temporaire
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.write('\n\n# Auto-generated tests\n')
            for i, test in enumerate(test_cases):
                f.write(f'# Test {i+1}\n')
                f.write(f'{test["input"]}\n')
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