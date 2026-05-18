"""
Endpoints pour les challenges de programmation
À ajouter au fichier app/api/challenges.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import subprocess
import tempfile
import os
import json
import time
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import User, Challenge, ChallengeSubmission
from app.security import get_current_user

router = APIRouter(prefix="/challenges", tags=["challenges"])

# ============ Models Pydantic ============

class TestResultSchema(BaseModel):
    testId: int
    input: str
    expected: str
    actual: str
    passed: bool
    error: Optional[str] = None

class ExecuteCodeRequest(BaseModel):
    challengeId: str
    code: str
    language: str  # 'python', 'javascript', 'cpp', 'java'

class ExecuteCodeResponse(BaseModel):
    success: bool
    testResults: List[TestResultSchema]
    executionTime: float  # ms
    memoryUsed: float  # KB
    score: int  # 0-300
    error: Optional[str] = None

class SubmissionRequest(BaseModel):
    code: str
    language: str
    score: int
    executionTime: float
    memoryUsed: float
    testResults: List[TestResultSchema]

class LeaderboardEntrySchema(BaseModel):
    rank: int
    username: str
    score: int
    executionTime: float
    memoryUsed: float
    submittedAt: str

# ============ Utilitaires ============

def execute_code_sandbox(
    code: str,
    language: str,
    test_inputs: List[dict],
    time_limit: int = 1,
    memory_limit: int = 128,
) -> tuple[List[dict], float, float, Optional[str]]:
    """
    Exécute le code dans un sandbox et teste contre les cas de test
    Retourne: (test_results, execution_time_ms, memory_used_kb, error_msg)
    """
    test_results = []
    total_time = 0
    total_memory = 0
    error_msg = None

    try:
        # Créer un fichier temporaire pour le code
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=get_file_extension(language),
            delete=False,
            dir='/tmp'
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Pour chaque cas de test
            for test in test_inputs:
                test_id = test['id']
                test_input = test['input']
                expected_output = test['expected']

                start_time = time.time()

                # Exécuter le code
                try:
                    if language == 'python':
                        result = subprocess.run(
                            ['python3', temp_file],
                            input=test_input,
                            capture_output=True,
                            text=True,
                            timeout=time_limit,
                            env={**os.environ, 'PYTHONUNBUFFERED': '1'},
                        )
                    elif language == 'javascript':
                        result = subprocess.run(
                            ['node', temp_file],
                            input=test_input,
                            capture_output=True,
                            text=True,
                            timeout=time_limit,
                        )
                    elif language == 'cpp':
                        # Compiler d'abord
                        compile_result = subprocess.run(
                            ['g++', '-o', temp_file + '.out', temp_file],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        if compile_result.returncode != 0:
                            raise Exception(f"Erreur de compilation: {compile_result.stderr}")

                        result = subprocess.run(
                            [temp_file + '.out'],
                            input=test_input,
                            capture_output=True,
                            text=True,
                            timeout=time_limit,
                        )
                    elif language == 'java':
                        # Compiler et exécuter Java
                        # Supposer que le code a une classe "Solution"
                        compile_result = subprocess.run(
                            ['javac', temp_file],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        if compile_result.returncode != 0:
                            raise Exception(f"Erreur de compilation: {compile_result.stderr}")

                        result = subprocess.run(
                            ['java', '-cp', os.path.dirname(temp_file), 'Solution'],
                            input=test_input,
                            capture_output=True,
                            text=True,
                            timeout=time_limit,
                        )
                    else:
                        raise Exception(f"Langage non supporté: {language}")

                    elapsed_time = (time.time() - start_time) * 1000  # ms
                    total_time += elapsed_time

                    actual_output = result.stdout.strip()
                    expected_clean = expected_output.strip()

                    passed = actual_output == expected_clean
                    error = None

                    if result.returncode != 0 and not passed:
                        error = result.stderr[:200]  # Limiter la taille du message d'erreur

                    test_results.append({
                        'testId': test_id,
                        'input': test_input,
                        'expected': expected_clean,
                        'actual': actual_output,
                        'passed': passed,
                        'error': error,
                    })

                except subprocess.TimeoutExpired:
                    test_results.append({
                        'testId': test_id,
                        'input': test_input,
                        'expected': expected_output,
                        'actual': '',
                        'passed': False,
                        'error': f'Dépassement de temps limite ({time_limit}s)',
                    })
                except Exception as e:
                    test_results.append({
                        'testId': test_id,
                        'input': test_input,
                        'expected': expected_output,
                        'actual': '',
                        'passed': False,
                        'error': str(e)[:200],
                    })

        finally:
            # Nettoyer les fichiers temporaires
            try:
                os.unlink(temp_file)
                if language == 'cpp' and os.path.exists(temp_file + '.out'):
                    os.unlink(temp_file + '.out')
                if language == 'java':
                    class_file = temp_file.replace('.java', '.class')
                    if os.path.exists(class_file):
                        os.unlink(class_file)
            except:
                pass

    except Exception as e:
        error_msg = str(e)

    avg_time = total_time / len(test_inputs) if test_inputs else 0
    # Approximation de la mémoire (en production, utiliser psutil ou /proc)
    memory_used = 5.0  # KB approximatif

    return test_results, avg_time, memory_used, error_msg


def get_file_extension(language: str) -> str:
    """Retourne l'extension de fichier pour un langage"""
    extensions = {
        'python': '.py',
        'javascript': '.js',
        'cpp': '.cpp',
        'java': '.java',
    }
    return extensions.get(language, '.txt')


def calculate_score(test_results: List[dict], execution_time: float) -> int:
    """
    Calcule le score final
    - 100 points de base pour 100% des tests
    - Pénalité mineure pour le temps (-10% si > 1s)
    """
    if not test_results:
        return 0

    passed_count = sum(1 for t in test_results if t['passed'])
    total_count = len(test_results)

    # Pénalité si au moins un test échoue : 0 points
    if passed_count != total_count:
        return 0

    # Points pour tests réussis
    test_score = 100

    # Pénalité pour le temps (mineur)
    time_penalty = 0
    if execution_time > 1000:  # > 1s
        time_penalty = min(10, (execution_time - 1000) / 100)

    # Score final (max 300 points : 100 tests + 100 temps + 100 mémoire)
    # Ici on simplifie : 300 = tous les tests réussis + bonus temps
    score = int(test_score * 3 - time_penalty)
    return max(0, min(300, score))


# ============ Endpoints ============

@router.post("/execute", response_model=ExecuteCodeResponse)
async def execute_code(
    request: ExecuteCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exécute le code de l'utilisateur contre les cas de test
    """
    try:
        # Récupérer le challenge
        challenge = db.query(Challenge).filter(
            Challenge.id == request.challengeId
        ).first()

        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge non trouvé",
            )

        # Récupérer les tests (depuis la BDD)
        # Supposer qu'ils sont stockés en JSON dans Challenge.test_cases
        tests = json.loads(challenge.test_cases) if challenge.test_cases else []

        # Exécuter le code
        test_results, exec_time, mem_used, error = execute_code_sandbox(
            code=request.code,
            language=request.language,
            test_inputs=tests,
            time_limit=challenge.time_limit or 1,
            memory_limit=challenge.memory_limit or 128,
        )

        # Calculer le score
        score = calculate_score(test_results, exec_time)
        success = all(t['passed'] for t in test_results) and error is None

        return ExecuteCodeResponse(
            success=success,
            testResults=[TestResultSchema(**t) for t in test_results],
            executionTime=exec_time,
            memoryUsed=mem_used,
            score=score,
            error=error,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'exécution: {str(e)}",
        )


@router.post("/{challenge_id}/submit")
async def submit_challenge(
    challenge_id: str,
    request: SubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soumet une solution et l'enregistre
    """
    try:
        # Vérifier que le challenge existe
        challenge = db.query(Challenge).filter(
            Challenge.id == challenge_id
        ).first()

        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge non trouvé",
            )

        # Créer une nouvelle soumission
        submission = ChallengeSubmission(
            user_id=current_user.id,
            challenge_id=challenge_id,
            code=request.code,
            language=request.language,
            score=request.score,
            execution_time=request.executionTime,
            memory_used=request.memoryUsed,
            test_results=json.dumps([t.dict() for t in request.testResults]),
            submitted_at=datetime.utcnow(),
        )

        db.add(submission)
        db.commit()
        db.refresh(submission)

        return {
            "success": True,
            "message": "Soumission enregistrée",
            "submissionId": submission.id,
            "score": request.score,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la soumission: {str(e)}",
        )


@router.get("/{challenge_id}/leaderboard", response_model=List[LeaderboardEntrySchema])
async def get_leaderboard(
    challenge_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """
    Récupère le classement d'un challenge
    """
    try:
        # Récupérer les meilleures soumissions pour ce challenge
        submissions = db.query(ChallengeSubmission).filter(
            ChallengeSubmission.challenge_id == challenge_id
        ).order_by(
            ChallengeSubmission.score.desc(),
            ChallengeSubmission.execution_time.asc(),
        ).limit(limit).all()

        leaderboard = []
        for rank, submission in enumerate(submissions, start=1):
            leaderboard.append(LeaderboardEntrySchema(
                rank=rank,
                username=submission.user.username,
                score=submission.score,
                executionTime=submission.execution_time,
                memoryUsed=submission.memory_used,
                submittedAt=submission.submitted_at.isoformat(),
            ))

        return leaderboard

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du classement: {str(e)}",
        )


@router.get("/{challenge_id}/my-submissions")
async def get_my_submissions(
    challenge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère l'historique des soumissions de l'utilisateur
    """
    try:
        submissions = db.query(ChallengeSubmission).filter(
            ChallengeSubmission.challenge_id == challenge_id,
            ChallengeSubmission.user_id == current_user.id,
        ).order_by(
            ChallengeSubmission.submitted_at.desc(),
        ).all()

        return [{
            "id": s.id,
            "code": s.code,
            "language": s.language,
            "score": s.score,
            "executionTime": s.execution_time,
            "memoryUsed": s.memory_used,
            "submittedAt": s.submitted_at.isoformat(),
        } for s in submissions]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}",
        )


@router.get("/{challenge_id}")
async def get_challenge(
    challenge_id: str,
    db: Session = Depends(get_db),
):
    """
    Récupère les détails d'un challenge
    """
    try:
        challenge = db.query(Challenge).filter(
            Challenge.id == challenge_id
        ).first()

        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge non trouvé",
            )

        # Parser les tests depuis JSON
        tests = json.loads(challenge.test_cases) if challenge.test_cases else []

        return {
            "id": challenge.id,
            "title": challenge.title,
            "difficulty": challenge.difficulty,
            "points": challenge.points,
            "timeLimit": challenge.time_limit or 1,
            "memoryLimit": challenge.memory_limit or 128,
            "description": challenge.description,
            "explanation": challenge.explanation or "",
            "exampleInput": challenge.example_input or "",
            "exampleOutput": challenge.example_output or "",
            "defaultCode": challenge.default_code or "",
            "language": challenge.language or "python",
            "tests": tests,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}",
        )