"""
Exercises API Routes
Génération procédurale d'exercices et correction automatique
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import numpy as np
import random
from sympy import symbols, expand, factor, integrate, diff, Rational, latex, sympify
from app import db
from app.models.exercise import Exercise, ExerciseAttempt
from app.models.progress import UserProgress

ex_bp = Blueprint('exercises', __name__)

def generate_numerical_integration_exercise(difficulty):
    """Generate numerical integration exercise"""
    x = symbols('x')
    
    # Generate polynomial based on difficulty
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
        # Include trig functions
        a, b = random.randint(1, 3), random.randint(1, 3)
        f = a * x**2 + b * sympify('sin(x)')
    
    a, b = 0, random.randint(1, 5)
    exact = integrate(f, (x, a, b))
    exact_val = float(exact.evalf())
    
    return {
        'function': str(f),
        'a': a,
        'b': b,
        'exact_value': exact_val,
        'question': f"Calculer l'intégrale ∫[{a},{b}] f(x) dx (valeur numérique)",
        'answer': exact_val,
        'latex': latex(f)
    }

def generate_matrix_exercise(difficulty):
    """Generate matrix operation exercise"""
    size = 2 if difficulty <= 2 else 3
    
    # Generate random matrix
    A = np.random.randint(-5, 6, (size, size))
    
    # Ensure it's invertible
    while abs(np.linalg.det(A)) < 0.1:
        A = np.random.randint(-5, 6, (size, size))
    
    # For now, only generate exercises with real-valued answers
    # because the UI expects a single numeric input
    operation = random.choice(['determinant', 'inverse'])
    
    if operation == 'determinant':
        answer = float(np.linalg.det(A))
    elif operation == 'inverse':
        answer = np.linalg.inv(A).tolist()
    
    return {
        'matrix': A.tolist(),
        'operation': operation,
        'answer': answer,
        'size': size
    }

def generate_ode_exercise(difficulty):
    """Generate ODE exercise"""
    if difficulty <= 2:
        # Simple separable equation
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
        # Linear ODE
        a, b = random.randint(1, 3), random.randint(1, 3)
        t_eval = 1.0
        # Exact solution for y' = -a y + sin(t), y(0)=b:
        # y(t) = e^{-a t} b + (a sin t - cos t)/(a^2+1) + e^{-a t}/(a^2+1)
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
    """Generate graph theory exercise"""
    n = random.randint(4, 6)
    
    # Generate random graph
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            if random.random() < 0.5:
                weight = random.randint(1, 10)
                edges.append([i, j, weight])
    
    exercise_type = preferred_type or random.choice(['shortest_path', 'mst'])
    
    if exercise_type == 'shortest_path':
        start, end = 0, n - 1
        # Compute shortest path distance (undirected graph)
        adj = {i: [] for i in range(n)}
        for u, v, w in edges:
            adj[u].append((v, w))
            adj[v].append((u, w))
        import heapq
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
        # MST total weight (Kruskal, undirected)
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

@ex_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_exercise():
    """Generate a new exercise procedurally"""
    data = request.get_json()
    
    module = data.get('module', 'numerical_methods')
    requested_type = data.get('type', 'numerical_integration')
    difficulty = data.get('difficulty', 1)

    # Map frontend exercise type labels to internal generator keys
    type_mapping = {
        # Dynamical systems
        'stability': 'ode',
        # Numerical methods
        'convergence': 'numerical_integration',
        # Linear algebra
        'eigenvalues': 'matrix',
        # Graph theory
        'shortest_path': 'graph',
        'mst': 'graph',
    }

    exercise_type = type_mapping.get(requested_type, requested_type)
    
    # Get user for adaptive difficulty
    user_id = int(get_jwt_identity())
    progress = UserProgress.query.filter_by(user_id=user_id, module=module).first()
    
    if progress:
        difficulty = progress.current_difficulty
    
    generator = EXERCISE_GENERATORS.get(exercise_type)
    if not generator:
        return jsonify({'error': f'Unknown exercise type: {exercise_type}'}), 400
    
    try:
        if exercise_type == 'graph' and requested_type in ('shortest_path', 'mst'):
            problem_data = generator(difficulty, preferred_type=requested_type)
        else:
            problem_data = generator(difficulty)
        
        exercise = Exercise(
            title=f"Exercice {exercise_type} - Niveau {difficulty}",
            description=f"Résoudre le problème de {exercise_type}",
            module=module,
            difficulty=difficulty,
            problem_data=problem_data,
            solution_data={'answer': problem_data.get('answer') or problem_data.get('exact_value')},
            points=difficulty * 10
        )
        
        db.session.add(exercise)
        db.session.commit()
        
        return jsonify({
            'exercise': exercise.to_dict(),
            'difficulty_adjusted': progress is not None
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ex_bp.route('/<int:exercise_id>/submit', methods=['POST'])
@jwt_required()
def submit_answer(exercise_id):
    """Submit answer for an exercise"""
    data = request.get_json()
    
    exercise = Exercise.query.get(exercise_id)
    if not exercise:
        return jsonify({'error': 'Exercise not found'}), 404
    
    user_id = int(get_jwt_identity())
    user_answer = data.get('answer')
    time_spent = data.get('time_spent', 0)
    
    # Get correct answer
    correct_answer = exercise.solution_data.get('answer')
    
    # Evaluate answer
    is_correct = False
    score = 0
    feedback = ""
    
    if isinstance(correct_answer, (int, float)):
        # Numerical answer with tolerance
        try:
            user_val = float(user_answer)
            correct_val = float(correct_answer)
            error = abs(user_val - correct_val)
            rel_error = error / abs(correct_val) if correct_val != 0 else error
            
            if rel_error < 0.01:  # 1% tolerance
                is_correct = True
                score = 100
                feedback = "Correct!"
            elif rel_error < 0.05:  # 5% tolerance
                is_correct = True
                score = 80
                feedback = "Presque correct! Vérifiez vos calculs."
            else:
                is_correct = False
                score = max(0, 100 - int(rel_error * 100))
                feedback = f"Incorrect. La réponse attendue était {correct_val:.4f}"
        except:
            feedback = "Format de réponse invalide"
    
    elif isinstance(correct_answer, list):
        # Matrix or vector answer
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
        except:
            feedback = "Format de réponse invalide"
    
    # Record attempt
    attempt = ExerciseAttempt(
        user_id=user_id,
        exercise_id=exercise_id,
        answer_data={'answer': user_answer},
        is_correct=is_correct,
        score=score,
        feedback=feedback,
        time_spent=time_spent
    )
    
    db.session.add(attempt)
    
    # Update progress
    progress = UserProgress.query.filter_by(user_id=user_id, module=exercise.module).first()
    if not progress:
        progress = UserProgress(
            user_id=user_id,
            module=exercise.module,
            exercises_completed=0,
            exercises_attempted=0,
            total_points=0,
            time_spent=0,
            current_difficulty=1,
            success_rate=0.0,
            topic_progress={},
        )
        db.session.add(progress)
    
    progress.exercises_attempted += 1
    if is_correct:
        progress.exercises_completed += 1
        progress.total_points += exercise.points
    
    progress.update_success_rate()
    progress.adjust_difficulty()
    
    db.session.commit()
    
    return jsonify({
        'is_correct': is_correct,
        'score': score,
        'feedback': feedback,
        'correct_answer': correct_answer if not is_correct else None,
        'progress': progress.to_dict()
    })

@ex_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    """Get user's exercise history"""
    user_id = int(get_jwt_identity())
    
    attempts = ExerciseAttempt.query.filter_by(user_id=user_id).order_by(
        ExerciseAttempt.created_at.desc()
    ).limit(50).all()
    
    return jsonify({
        'attempts': [a.to_dict() for a in attempts]
    })

@ex_bp.route('/progress', methods=['GET'])
@jwt_required()
def get_progress():
    """Get user's progress across all modules"""
    user_id = int(get_jwt_identity())
    
    progress = UserProgress.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'progress': [p.to_dict() for p in progress]
    })
