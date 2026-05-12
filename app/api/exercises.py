"""
Exercises API Routes - FastAPI
Génération procédurale d'exercices et correction automatique
"""
import random
import heapq
import numpy as np
from sympy import symbols, integrate, latex, sympify
from typing import Optional, List, Union, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import SessionLocal
from app.models.exercise import Exercise, ExerciseAttempt
from app.models.progress import UserProgress
from app.api.auth import get_current_user
from app.models.user import User

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic
# ─────────────────────────────────────────────────────────────────────────────
class GenerateExerciseRequest(BaseModel):
    module: str = Field(default='numerical_methods')
    type: str = Field(default='numerical_integration')
    difficulty: int = Field(default=1, ge=1, le=5)

class SubmitAnswerRequest(BaseModel):
    answer: Any
    time_spent: int = Field(default=0, ge=0)

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
# Générateurs d'exercices (inchangés)
# ─────────────────────────────────────────────────────────────────────────────
def generate_numerical_integration_exercise(difficulty):
    x = symbols('x')
    if difficulty == 1:
        coeffs = [random.randint(1, 5) for _ in range(2)]
        f = sum(c * x**i for i, c in enumerate(coeffs))
    elif difficulty == 2:
        coeffs = [random.randint(1, 5) for _ in range(3)]
        f = sum(c * x**i for i, c in enumerate(coeffs))
    elif difficulty == 3:
        coeffs = [random.randint(-5, 5) for _ in range(4)]
        f = sum(c * x**i for i, c in enumerate(coeffs))
    else:
        a_coef, b_coef = random.randint(1, 3), random.randint(1, 3)
        f = a_coef * x**2 + b_coef * sympify('sin(x)')
    
    a, b = 0, random.randint(1, 5)
    exact = integrate(f, (x, a, b))
    exact_val = float(exact.evalf())
    
    return {
        'function': str(f),
        'a': a, 'b': b,
        'exact_value': exact_val,
        'question': f"Calculer l'intégrale ∫[{a},{b}] f(x) dx (valeur numérique)",
        'answer': exact_val,
        'latex': latex(f)
    }

def generate_matrix_exercise(difficulty):
    size = 2 if difficulty <= 2 else 3
    A = np.random.randint(-5, 6, (size, size))
    while abs(np.linalg.det(A)) < 0.1:
        A = np.random.randint(-5, 6, (size, size))
    
    operation = random.choice(['determinant', 'inverse'])
    answer = float(np.linalg.det(A)) if operation == 'determinant' else np.linalg.inv(A).tolist()
    
    return {
        'matrix': A.tolist(),
        'operation': operation,
        'answer': answer,
        'size': size
    }

def generate_ode_exercise(difficulty):
    if difficulty <= 2:
        a = random.randint(1, 5)
        y0 = random.randint(1, 5)
        t_eval = 1.0
        answer = float(y0 * np.exp(-a * t_eval))
        return {
            'type': 'separable',
            'equation': f"dy/dt = -{a}*y",
            'initial_condition': [0, y0],
            'solution_form': 'y(t) = y0 * exp(-a*t)',
            'question': f"Calculer y({t_eval})",
            't_eval': t_eval,
            'answer': answer,
        }
    else:
        a, b = random.randint(1, 3), random.randint(1, 3)
        t_eval = 1.0
        answer = float(
            (np.exp(-a * t_eval) * b)
            + ((a * np.sin(t_eval) - np.cos(t_eval)) / (a**2 + 1))
            + (np.exp(-a * t_eval) / (a**2 + 1))
        )
        return {
            'type': 'linear',
            'equation': f"dy/dt = -{a}*y + sin(t)",
            'initial_condition': [0, b],
            'solution_hint': 'Use integrating factor method',
            'question': f"Calculer y({t_eval})",
            't_eval': t_eval,
            'answer': answer,
        }

def generate_graph_exercise(difficulty, preferred_type=None):
    n = random.randint(4, 6)
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            if random.random() < 0.5:
                weight = random.randint(1, 10)
                edges.append([i, j, weight])
    
    exercise_type = preferred_type or random.choice(['shortest_path', 'mst'])
    
    if exercise_type == 'shortest_path':
        start, end = 0, n - 1
        adj = {i: [] for i in range(n)}
        for u, v, w in edges:
            adj[u].append((v, w))
            adj[v].append((u, w))
        dist = [float('inf')] * n
        dist[start] = 0.0
        pq = [(0.0, start)]
        while pq:
            d, u = heapq.heappop(pq)
            if d != dist[u]:
                continue
            if u == end:
                break
            for vv, ww in adj[u]:
                nd = d + ww
                if nd < dist[vv]:
                    dist[vv] = nd
                    heapq.heappush(pq, (nd, vv))
        answer = float(dist[end]) if dist[end] != float('inf') else float('inf')
        return {
            'type': 'shortest_path',
            'num_nodes': n,
            'edges': edges,
            'start': start,
            'end': end,
            'question': f"Donner la distance du plus court chemin de {start} à {end}",
            'answer': answer,
        }
    else:
        parent = list(range(n))
        rank = [0] * n
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra == rb:
                return False
            if rank[ra] < rank[rb]:
                ra, rb = rb, ra
            parent[rb] = ra
            if rank[ra] == rank[rb]:
                rank[ra] += 1
            return True
        total = 0
        for u, v, w in sorted(edges, key=lambda e: e[2]):
            if union(u, v):
                total += w
        return {
            'type': 'mst',
            'num_nodes': n,
            'edges': edges,
            'question': "Donner le poids total d'un arbre couvrant minimal (MST)",
            'answer': float(total),
        }

EXERCISE_GENERATORS = {
    'numerical_integration': generate_numerical_integration_exercise,
    'matrix': generate_matrix_exercise,
    'ode': generate_ode_exercise,
    'graph': generate_graph_exercise
}

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/generate")
def generate_exercise(
    data: GenerateExerciseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new exercise procedurally"""
    type_mapping = {
        'stability': 'ode',
        'convergence': 'numerical_integration',
        'eigenvalues': 'matrix',
        'shortest_path': 'graph',
        'mst': 'graph',
    }
    exercise_type = type_mapping.get(data.type, data.type)
    
    progress = db.query(UserProgress).filter_by(
        user_id=current_user.id, module=data.module
    ).first()
    difficulty = data.difficulty
    if progress:
        difficulty = progress.current_difficulty
    
    generator = EXERCISE_GENERATORS.get(exercise_type)
    if not generator:
        raise HTTPException(status_code=400, detail=f"Unknown exercise type: {exercise_type}")
    
    try:
        if exercise_type == 'graph' and data.type in ('shortest_path', 'mst'):
            problem_data = generator(difficulty, preferred_type=data.type)
        else:
            problem_data = generator(difficulty)
        
        exercise = Exercise(
            title=f"Exercice {exercise_type} - Niveau {difficulty}",
            description=f"Résoudre le problème de {exercise_type}",
            module=data.module,
            difficulty=difficulty,
            problem_data=problem_data,
            solution_data={'answer': problem_data.get('answer') or problem_data.get('exact_value')},
            points=difficulty * 10
        )
        db.add(exercise)
        db.commit()
        db.refresh(exercise)
        
        return {
            'exercise': exercise.to_dict(),
            'difficulty_adjusted': progress is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{exercise_id}/submit")
def submit_answer(
    exercise_id: int,
    data: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit answer for an exercise"""
    exercise = db.query(Exercise).get(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    user_answer = data.answer
    time_spent = data.time_spent
    correct_answer = exercise.solution_data.get('answer')
    
    is_correct = False
    score = 0
    feedback = ""
    
    if isinstance(correct_answer, (int, float)):
        try:
            user_val = float(user_answer)
            correct_val = float(correct_answer)
            error = abs(user_val - correct_val)
            rel_error = error / abs(correct_val) if correct_val != 0 else error
            
            if rel_error < 0.01:
                is_correct = True
                score = 100
                feedback = "Correct!"
            elif rel_error < 0.05:
                is_correct = True
                score = 80
                feedback = "Presque correct! Vérifiez vos calculs."
            else:
                is_correct = False
                score = max(0, 100 - int(rel_error * 100))
                feedback = f"Incorrect. La réponse attendue était {correct_val:.4f}"
        except Exception:
            feedback = "Format de réponse invalide"
    
    elif isinstance(correct_answer, list):
        try:
            user_array = np.array(user_answer)
            correct_array = np.array(correct_answer)
            if user_array.shape == correct_array.shape:
                error = np.linalg.norm(user_array - correct_array)
                if error < 0.01:
                    is_correct = True
                    score = 100
                    feedback = "Correct!"
                else:
                    feedback = "Incorrect. Vérifiez vos calculs matriciels."
            else:
                feedback = "Dimensions incorrectes"
        except Exception:
            feedback = "Format de réponse invalide"
    
    attempt = ExerciseAttempt(
        user_id=current_user.id,
        exercise_id=exercise_id,
        answer_data={'answer': user_answer},
        is_correct=is_correct,
        score=score,
        feedback=feedback,
        time_spent=time_spent
    )
    db.add(attempt)
    
    progress = db.query(UserProgress).filter_by(
        user_id=current_user.id, module=exercise.module
    ).first()
    if not progress:
        progress = UserProgress(
            user_id=current_user.id,
            module=exercise.module,
            exercises_completed=0,
            exercises_attempted=0,
            total_points=0,
            time_spent=0,
            current_difficulty=1,
            success_rate=0.0,
            topic_progress={},
        )
        db.add(progress)
    
    progress.exercises_attempted += 1
    if is_correct:
        progress.exercises_completed += 1
        progress.total_points += exercise.points
    
    progress.update_success_rate()
    progress.adjust_difficulty()
    db.commit()
    
    return {
        'is_correct': is_correct,
        'score': score,
        'feedback': feedback,
        'correct_answer': correct_answer if not is_correct else None,
        'progress': progress.to_dict()
    }

@router.get("/history")
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's exercise history"""
    attempts = db.query(ExerciseAttempt).filter_by(
        user_id=current_user.id
    ).order_by(ExerciseAttempt.created_at.desc()).limit(50).all()
    return {'attempts': [a.to_dict() for a in attempts]}

@router.get("/progress")
def get_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's progress across all modules"""
    progress = db.query(UserProgress).filter_by(user_id=current_user.id).all()
    return {'progress': [p.to_dict() for p in progress]}