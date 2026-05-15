"""
Exercises API Routes - FastAPI
Génération procédurale d'exercices avec LaTeX et étapes de résolution
"""
import random
import heapq
import numpy as np
from sympy import (
    symbols, integrate, latex, sympify, exp, sin, cos,
    Rational, Function, Matrix, factorial, pretty, limit, oo
)
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
# Générateurs d'exercices avec LaTeX et étapes
# ─────────────────────────────────────────────────────────────────────────────

def generate_numerical_integration_exercise(difficulty):
    """Intégration numérique avec formules et étapes."""
    x = symbols('x')
    if difficulty == 1:
        coeffs = [random.randint(1, 5) for _ in range(2)]
        f = sum(c * x**i for i, c in enumerate(coeffs))
        method = random.choice(['Trapèzes', 'Rectangle gauche'])
    elif difficulty == 2:
        coeffs = [random.randint(1, 5) for _ in range(3)]
        f = sum(c * x**i for i, c in enumerate(coeffs))
        method = random.choice(['Simpson', 'Trapèzes'])
    elif difficulty == 3:
        coeffs = [random.randint(-5, 5) for _ in range(4)]
        f = sum(c * x**i for i, c in enumerate(coeffs))
        method = 'Simpson'
    else:
        a_coef, b_coef = random.randint(1, 3), random.randint(1, 3)
        f = a_coef * x**2 + b_coef * sin(x)
        method = 'Simpson'
    
    a, b = 0, random.randint(1, 5)
    exact = integrate(f, (x, a, b))
    exact_val = float(exact.evalf())
    n = 4 * difficulty
    h = (b - a) / n

    # Étapes de résolution
    steps = [
        f'Fonction : $f(x) = {latex(f)}$',
        f'Intervalle : $[{a}, {b}]$',
        f'Nombre de sous-intervalles : $n = {n}$',
        f'Pas : $h = \\frac{{{b}-{a}}}{{{n}}} = {latex(Rational(b-a, n))}$',
        f'Valeur exacte : $\\int_{{{a}}}^{{{b}}} f(x)\\,dx = {latex(exact)} \\approx {exact_val:.4f}$',
    ]

    return {
        'function': str(f),
        'a': a, 'b': b,
        'exact_value': exact_val,
        'question': f"Calculer l'intégrale $\\int_{{{a}}}^{{{b}}} f(x)\\,dx$ par la méthode de {method} avec $n={n}$",
        'answer': exact_val,
        'method': method,
        'n': n,
        'h': float(h),
        'solution_latex': f'\\int_{{{a}}}^{{{b}}} {latex(f)}\\,dx = {latex(exact)} \\approx {exact_val:.4f}',
        'steps': steps,
    }


def generate_matrix_exercise(difficulty):
    """Matrices : déterminant et inverse avec étapes en LaTeX."""
    size = 2 if difficulty <= 2 else 3
    A = np.random.randint(-5, 6, (size, size))
    while abs(np.linalg.det(A)) < 0.1:
        A = np.random.randint(-5, 6, (size, size))
    
    operation = random.choice(['determinant', 'inverse'])
    sympy_A = Matrix(A.tolist())
    det_A = sympy_A.det()
    steps = []
    solution_latex = ""

    if operation == 'determinant':
        answer = float(det_A)
        if size == 2:
            steps = [
                f'Matrice : $A = {latex(sympy_A)}$',
                f'Déterminant : $\\det(A) = ({A[0,0]})({A[1,1]}) - ({A[0,1]})({A[1,0]})$',
                f'$\\det(A) = {A[0,0]*A[1,1]} - {A[0,1]*A[1,0]} = {answer}$',
            ]
        else:
            steps = [
                f'Matrice : $A = {latex(sympy_A)}$',
                f'Déterminant (Sarrus) : $\\det(A) = {latex(det_A)}$',
                f'$\\det(A) = {answer}$',
            ]
        solution_latex = f'\\det(A) = {latex(det_A)} = {answer}'
    else:
        inv_A = sympy_A.inv()
        answer = inv_A.tolist()
        det_val = float(det_A)
        adj_A = sympy_A.adjugate()
        steps = [
            f'Matrice : $A = {latex(sympy_A)}$',
            f'Déterminant : $\\det(A) = {latex(det_A)} = {det_val:.4f}$',
            f'Comatrice (transposée de la matrice des cofacteurs) : $\\operatorname{{adj}}(A) = {latex(adj_A)}$',
            f'Inverse : $A^{{-1}} = \\frac{{1}}{{\\det(A)}} \\operatorname{{adj}}(A) = \\frac{{1}}{{{latex(det_A)}}} {latex(adj_A)}$',
            f'$A^{{-1}} = {latex(inv_A)}$',
        ]
        solution_latex = f'A^{{-1}} = \\frac{{1}}{{{latex(det_A)}}} {latex(adj_A)} = {latex(inv_A)}'

    return {
        'matrix': A.tolist(),
        'operation': operation,
        'answer': answer,
        'size': size,
        'question': f'Calculer le {operation} de la matrice $A$' if operation == 'determinant' else f'Calculer l\'inverse de la matrice $A$',
        'solution_latex': solution_latex,
        'steps': steps,
    }


def generate_ode_exercise(difficulty):
    """ODE avec valeurs exactes, LaTeX et étapes."""
    t = symbols('t')
    y = Function('y')
    
    if difficulty <= 2:
        a = random.randint(1, 5)
        y0 = random.randint(1, 5)
        t_eval = Rational(1, 1)
        
        exact_expr = y0 * exp(-a * t_eval)
        exact_val = float(exact_expr.evalf())
        
        return {
            'type': 'separable',
            'equation': f'\\frac{{dy}}{{dt}} = -{a}y',
            'equation_plain': f'dy/dt = -{a}*y',
            'initial_condition': [0, y0],
            't_eval': float(t_eval),
            'question': f'Calculer $y({float(t_eval)})$',
            'answer': exact_val,
            'solution_latex': f'y(t) = {y0}e^{{-{a}t}} \\Rightarrow y({float(t_eval)}) = {y0}e^{{-{a}}} = {latex(exact_expr)} \\approx {exact_val:.4f}',
            'steps': [
                f'Équation : $\\frac{{dy}}{{dt}} = -{a}y$',
                f'Séparable : $\\frac{{dy}}{{y}} = -{a}\\,dt$',
                f'Solution générale : $y(t) = Ce^{{-{a}t}}$',
                f'Condition $y(0) = {y0} \\Rightarrow C = {y0}$',
                f'Solution : $y(t) = {y0}e^{{-{a}t}}$',
                f'$y({float(t_eval)}) = {y0}e^{{-{a}}} = {latex(exact_expr)} \\approx {exact_val:.4f}$',
            ],
        }
    else:
        a, b = random.randint(1, 3), random.randint(1, 3)
        t_eval = Rational(1, 1)
        
        exact_expr = (b * exp(-a * t_eval)
                      + (a * sin(t_eval) - cos(t_eval)) / (a**2 + 1)
                      + exp(-a * t_eval) / (a**2 + 1))
        exact_val = float(exact_expr.evalf())
        
        return {
            'type': 'linear',
            'equation': f'\\frac{{dy}}{{dt}} + {a}y = \\sin(t)',
            'equation_plain': f'dy/dt = -{a}*y + sin(t)',
            'initial_condition': [0, b],
            't_eval': float(t_eval),
            'question': f'Calculer $y({float(t_eval)})$',
            'answer': exact_val,
            'solution_latex': f'y(t) = {latex(exact_expr)} \\approx {exact_val:.4f}',
            'steps': [
                f'Équation : $\\frac{{dy}}{{dt}} + {a}y = \\sin(t)$',
                f'Facteur intégrant : $\\mu(t) = e^{{\\int {a}\\,dt}} = e^{{{a}t}}$',
                f'Multiplication : $\\frac{{d}}{{dt}}\\left[e^{{{a}t}} y\\right] = e^{{{a}t}}\\sin(t)$',
                f'Solution : $y(t) = {latex(exact_expr)}$',
                f'$y({float(t_eval)}) \\approx {exact_val:.4f}$',
            ],
        }


def generate_graph_exercise(difficulty, preferred_type=None):
    """Graphes : Dijkstra et MST avec étapes."""
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
        prev = [None] * n
        pq = [(0.0, start)]
        steps = [f'Graphe à {n} nœuds, {len(edges)} arêtes']
        steps.append(f'Dijkstra de {start} à {end}')
        
        while pq:
            d, u = heapq.heappop(pq)
            if d != dist[u]:
                continue
            steps.append(f'Nœud {u} extrait (distance = {d:.1f})')
            if u == end:
                break
            for vv, ww in adj[u]:
                nd = d + ww
                if nd < dist[vv]:
                    dist[vv] = nd
                    prev[vv] = u
                    heapq.heappush(pq, (nd, vv))
                    steps.append(f'  Relaxation {u}→{vv} : dist[{vv}] = {nd:.1f}')
        
        answer = float(dist[end]) if dist[end] != float('inf') else float('inf')
        # Chemin
        path = []
        cur = end
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        steps.append(f'Chemin : {" → ".join(map(str, path))}')
        steps.append(f'Distance totale : {answer}')
        
        return {
            'type': 'shortest_path',
            'num_nodes': n,
            'edges': edges,
            'start': start,
            'end': end,
            'question': f"Donner la distance du plus court chemin de {start} à {end}",
            'answer': answer,
            'solution_latex': f'd({start},{end}) = {answer}',
            'steps': steps,
        }
    else:
        # MST – Kruskal
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
        
        sorted_edges = sorted(edges, key=lambda e: e[2])
        total = 0
        mst_edges = []
        steps = ['Kruskal : tri des arêtes par poids croissant']
        for u, v, w in sorted_edges:
            if union(u, v):
                total += w
                mst_edges.append((u, v, w))
                steps.append(f'Arête {u}-{v} (poids {w}) : ajoutée ✅')
            else:
                steps.append(f'Arête {u}-{v} (poids {w}) : rejetée (cycle) ❌')
        steps.append(f'MST : {mst_edges}')
        steps.append(f'Poids total : {total}')
        
        return {
            'type': 'mst',
            'num_nodes': n,
            'edges': edges,
            'question': "Donner le poids total d'un arbre couvrant minimal (MST)",
            'answer': float(total),
            'solution_latex': f'\\text{{Poids total}} = {total}',
            'steps': steps,
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
            solution_data={
                'answer': problem_data.get('answer') or problem_data.get('exact_value'),
                'solution_latex': problem_data.get('solution_latex', ''),
                'steps': problem_data.get('steps', []),
            },
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
                feedback = "Correct !"
            elif rel_error < 0.05:
                is_correct = True
                score = 80
                feedback = "Presque correct ! Vérifiez vos calculs."
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
                    feedback = "Correct !"
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