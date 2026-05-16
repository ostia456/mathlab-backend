"""
Exercises API Routes - FastAPI
Génération procédurale d'exercices avec LaTeX et étapes de résolution
4 modules × 2 types × 5 niveaux
"""
import random
import heapq
import traceback
import numpy as np
from sympy import (
    symbols, integrate, latex, sympify, N, exp, sin, cos,
    Rational, Function, Matrix, diff, dsolve, Eq, solve, roots,
    Float, Integer, simplify, factor, expand
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
    module: str = Field(default='dynamical_systems')
    type: str = Field(default='ode')
    difficulty: int = Field(default=1, ge=1, le=5)
    mode: str = Field(default='manual')  # 'manual' ou 'auto'

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
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _make_json_safe(obj):
    """Convertit récursivement les objets sympy en types Python natifs."""
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, (Rational, Float, Integer)):
        return float(obj)
    if hasattr(obj, 'evalf'):
        return float(obj.evalf())
    return obj

# ═════════════════════════════════════════════════════════════════════════════
# MODULE 1 : SYSTÈMES DYNAMIQUES
# ═════════════════════════════════════════════════════════════════════════════

def generate_ode_exercise(difficulty):
    """Équations différentielles — Ordre 1 et 2."""
    t = symbols('t')
    y = Function('y')
    steps = []

    if difficulty == 1:
        # y' + ay = 0, solution simple
        a = random.randint(1, 5)
        y0 = random.randint(1, 5)
        t_eval = 1
        exact = y0 * exp(-a)
        exact_val = float(N(exact))
        steps = [
            f'Équation : $\\frac{{dy}}{{dt}} + {a}y = 0$',
            f'Solution générale : $y(t) = Ce^{{-{a}t}}$',
            f'Condition $y(0) = {y0} \\Rightarrow C = {y0}$',
            f'Solution : $y(t) = {y0}e^{{-{a}t}}$',
            f'$y({t_eval}) = {y0}e^{{-{a}}} = {latex(exact)} \\approx {exact_val:.4f}$',
        ]
        return {
            'equation': f'\\frac{{dy}}{{dt}} + {a}y = 0',
            'initial_condition': [0, y0],
            'question': f'Résoudre $y\' + {a}y = 0$, $y(0) = {y0}$ et calculer $y({t_eval})$',
            'answer': exact_val,
            'answer_latex': latex(exact),
            'solution_latex': f'y({t_eval}) = {y0}e^{{-{a}}} = {latex(exact)}',
            'steps': steps,
        }

    elif difficulty == 2:
        # y' + ay = f(t) avec second membre simple
        a = random.randint(1, 4)
        b = random.randint(1, 3)
        y0 = random.randint(1, 4)
        t_eval = 1
        f_t = f'{b}t'
        exact_expr = (y0 + b/a**2) * exp(-a) + (b/a) - b/a**2
        exact_val = float(N(exact_expr))
        steps = [
            f'Équation : $\\frac{{dy}}{{dt}} + {a}y = {b}t$',
            f'Solution homogène : $y_h(t) = Ce^{{-{a}t}}$',
            f'Solution particulière (variation de la constante) : $y_p(t) = \\frac{{{b}}}{{{a}}}t - \\frac{{{b}}}{{{a}^2}}$',
            f'Solution générale : $y(t) = Ce^{{-{a}t}} + \\frac{{{b}}}{{{a}}}t - \\frac{{{b}}}{{{a}^2}}$',
            f'Avec $y(0) = {y0}$ : $C = {y0} + \\frac{{{b}}}{{{a}^2}} = {latex(y0 + b/a**2)}$',
            f'$y({t_eval}) = {latex(exact_expr)} \\approx {exact_val:.4f}$',
        ]
        return {
            'equation': f'\\frac{{dy}}{{dt}} + {a}y = {b}t',
            'initial_condition': [0, y0],
            'question': f'Résoudre $y\' + {a}y = {b}t$, $y(0) = {y0}$ et calculer $y({t_eval})$',
            'answer': exact_val,
            'answer_latex': latex(exact_expr),
            'solution_latex': f'y({t_eval}) = {latex(exact_expr)} \\approx {exact_val:.4f}',
            'steps': steps,
        }

    elif difficulty == 3:
        # y'' + ay' + by = 0 (homogène ordre 2)
        a = random.randint(2, 5)
        b = random.randint(1, 5)
        y0 = random.randint(1, 3)
        y0_prime = random.randint(0, 3)
        t_eval = 1
        discriminant = a**2 - 4*b
        if discriminant > 0:
            r1 = (-a + np.sqrt(discriminant)) / 2
            r2 = (-a - np.sqrt(discriminant)) / 2
            sol_type = "racines réelles distinctes"
            steps = [
                f'Équation : $y\'\' + {a}y\' + {b}y = 0$',
                f'Équation caractéristique : $r^2 + {a}r + {b} = 0$',
                f'Discriminant : $\\Delta = {discriminant} > 0$',
                f'Racines : $r_1 = {latex(Rational(int(r1*2), 2))}, r_2 = {latex(Rational(int(r2*2), 2))}$',
                f'Solution : $y(t) = C_1 e^{{r_1 t}} + C_2 e^{{r_2 t}}$',
            ]
        elif discriminant == 0:
            r = -a/2
            sol_type = "racine double"
            steps = [
                f'Équation : $y\'\' + {a}y\' + {b}y = 0$',
                f'Équation caractéristique : $r^2 + {a}r + {b} = 0$',
                f'Discriminant : $\\Delta = 0$',
                f'Racine double : $r = {latex(Rational(-a, 2))}$',
                f'Solution : $y(t) = (C_1 + C_2 t) e^{{rt}}$',
            ]
        else:
            alpha = -a/2
            beta = np.sqrt(4*b - a**2)/2
            sol_type = "racines complexes conjuguées"
            steps = [
                f'Équation : $y\'\' + {a}y\' + {b}y = 0$',
                f'Équation caractéristique : $r^2 + {a}r + {b} = 0$',
                f'Discriminant : $\\Delta = {discriminant} < 0$',
                f'Racines : $r = {latex(Rational(-a, 2))} \\pm i\\sqrt{{{4*b-a**2}}}/2$',
                f'Solution : $y(t) = e^{{{latex(Rational(-a,2))}t}} (C_1 \\cos(\\beta t) + C_2 \\sin(\\beta t))$',
            ]
        steps.append(f'Avec conditions $y(0) = {y0}, y\'(0) = {y0_prime}$, déterminer $C_1, C_2$')
        steps.append(f'$y({t_eval}) = \\ldots$ (calcul numérique)')
        return {
            'equation': f'y\'\' + {a}y\' + {b}y = 0',
            'initial_condition': [y0, y0_prime],
            'question': f'Résoudre $y\'\' + {a}y\' + {b}y = 0$, $y(0) = {y0}$, $y\'(0) = {y0_prime}$',
            'answer': 0.0,  # placeholder — le vrai calcul est trop complexe pour ce niveau
            'answer_latex': '\\text{Voir étapes}',
            'solution_latex': f'\\text{{Solution de type : {sol_type}}}',
            'steps': steps,
        }

    elif difficulty == 4:
        # y'' + ay' + by = g(t) non homogène ordre 2
        a = random.randint(2, 4)
        b = random.randint(1, 4)
        y0 = random.randint(1, 3)
        y0_prime = random.randint(0, 2)
        g_type = random.choice(['sin', 'cos', 'exp'])
        if g_type == 'sin':
            g_t = f'\\sin(t)'
        elif g_type == 'cos':
            g_t = f'\\cos(t)'
        else:
            g_t = f'e^{{t}}'
        steps = [
            f'Équation : $y\'\' + {a}y\' + {b}y = {g_t}$',
            f'1. Résoudre l\'équation homogène $y\'\' + {a}y\' + {b}y = 0$',
            f'2. Trouver une solution particulière par la méthode des coefficients indéterminés',
            f'3. Appliquer les conditions initiales $y(0) = {y0}, y\'(0) = {y0_prime}$',
        ]
        return {
            'equation': f'y\'\' + {a}y\' + {b}y = {g_t}',
            'initial_condition': [y0, y0_prime],
            'question': f'Résoudre $y\'\' + {a}y\' + {b}y = {g_t}$, $y(0) = {y0}$, $y\'(0) = {y0_prime}$',
            'answer': 0.0,
            'answer_latex': '\\text{Voir étapes}',
            'solution_latex': '\\text{Solution complète dans les étapes}',
            'steps': steps,
        }

    else:  # difficulty == 5
        # Système différentiel 2×2
        A = np.random.randint(-3, 4, (2, 2))
        x0, y0 = random.randint(1, 3), random.randint(1, 3)
        M = Matrix(A.tolist())
        eigenvalues = M.eigenvals()
        eigenvectors = M.eigenvects()
        steps = [
            f'Système : $\\dot{{X}} = AX$ avec $A = {latex(M)}$',
            f'Valeurs propres : ${latex(eigenvalues)}$',
            f'Vecteurs propres : ${latex(eigenvectors)}$',
            f'Solution générale : $X(t) = c_1 e^{{\\lambda_1 t}} v_1 + c_2 e^{{\\lambda_2 t}} v_2$',
            f'Avec $X(0) = ({x0}, {y0})$, déterminer $c_1, c_2$',
        ]
        return {
            'equation': f'\\dot{{X}} = {latex(M)} X',
            'initial_condition': [x0, y0],
            'question': f'Résoudre le système $\\dot{{X}} = {latex(M)}X$, $X(0) = ({x0}, {y0})$',
            'answer': 0.0,
            'answer_latex': '\\text{Voir étapes}',
            'solution_latex': '\\text{Solution complète dans les étapes}',
            'steps': steps,
        }


def generate_stability_exercise(difficulty):
    """Stabilité des systèmes dynamiques."""
    steps = []
    if difficulty <= 2:
        x, y = symbols('x y')
        a, b, c, d = random.randint(-3, 3), random.randint(-3, 3), random.randint(-3, 3), random.randint(-3, 3)
        eq_x = f'{a}x + {b}y'
        eq_y = f'{c}x + {d}y'
        J = Matrix([[a, b], [c, d]])
        trace_J = a + d
        det_J = a*d - b*c
        discriminant = trace_J**2 - 4*det_J
        eigenvalues = list(J.eigenvals().keys())
        if det_J == 0:
            stability = 'dégénéré (det = 0)'
        elif trace_J < 0 and det_J > 0:
            stability = 'asymptotiquement stable'
        elif trace_J > 0 and det_J > 0:
            stability = 'instable (nœud ou foyer)'
        elif det_J < 0:
            stability = 'point selle (instable)'
        else:
            stability = 'centre (stable)'
        steps = [
            f'Système : $\\dot{{x}} = {eq_x}$, $\\dot{{y}} = {eq_y}$',
            f'Point d\'équilibre : $(0, 0)$',
            f'Jacobienne : $J = {latex(J)}$',
            f'Trace : $\\operatorname{{tr}}(J) = {trace_J}$, Déterminant : $\\det(J) = {det_J}$',
            f'Valeurs propres : ${latex(eigenvalues)}$',
            f'Classification : **{stability}**',
        ]
        return {
            'question': f'Étudier la stabilité du système $\\dot{{x}} = {eq_x}, \\dot{{y}} = {eq_y}$',
            'answer': 0,
            'answer_latex': stability,
            'solution_latex': stability,
            'steps': steps,
        }
    elif difficulty <= 4:
        a, b, c, d = random.randint(-2, 3), random.randint(-2, 3), random.randint(-2, 3), random.randint(-2, 3)
        J = Matrix([[a, b], [c, d]])
        eigenvalues = list(J.eigenvals().keys())
        ev_str = [f'\\lambda_{{{i+1}}} = {latex(ev)}' for i, ev in enumerate(eigenvalues)]
        steps = [
            f'Jacobienne : $J = {latex(J)}$',
            f'Polynôme caractéristique : $\\det(J - \\lambda I) = {latex(J.charpoly().as_expr())}$',
            f'Valeurs propres : {", ".join(ev_str)}',
            'Classification selon trace, déterminant et discriminant',
        ]
        return {
            'question': f'Classer la stabilité de l\'équilibre pour $J = {latex(J)}$',
            'answer': 0,
            'answer_latex': '\\text{Voir étapes}',
            'solution_latex': '\\text{Classification dans les étapes}',
            'steps': steps,
        }
    else:
        steps = [
            'Méthode de Lyapunov :',
            '1. Choisir $V(x,y) = x^2 + y^2$',
            '2. Calculer $\\dot{V} = \\frac{\\partial V}{\\partial x}\\dot{x} + \\frac{\\partial V}{\\partial y}\\dot{y}$',
            '3. Si $\\dot{V} \\leq 0$, l\'équilibre est stable',
            '4. Si $\\dot{V} < 0$, l\'équilibre est asymptotiquement stable',
        ]
        return {
            'question': 'Expliquer la méthode de Lyapunov pour étudier la stabilité d\'un système non linéaire',
            'answer': 0,
            'answer_latex': '\\text{Voir étapes}',
            'solution_latex': '\\text{Méthode de Lyapunov}',
            'steps': steps,
        }

# ═════════════════════════════════════════════════════════════════════════════
# MODULE 2 : MÉTHODES NUMÉRIQUES
# ═════════════════════════════════════════════════════════════════════════════

def generate_numerical_methods_exercise(difficulty):
    """EDO par méthodes numériques (Euler, RK)."""
    t, y = symbols('t y')
    steps = []
    if difficulty == 1:
        a, y0, h = random.randint(1, 3), random.randint(1, 4), Rational(1, random.choice([2, 4, 5]))
        f_expr = f'-{a}*y + t' if random.random() > 0.5 else f'-{a}*y'
        f = sympify(f_expr)
        y1 = y0 + float(h) * float(f.subs({t: 0, y: y0}))
        steps = [
            f'Méthode d\'Euler explicite : $y_{{n+1}} = y_n + h f(t_n, y_n)$',
            f'$f(t,y) = {latex(f)}$, $y_0 = {y0}$, $h = {latex(h)}$',
            f'$y_1 = y_0 + h f(t_0, y_0) = {y0} + {latex(h)} \\times {latex(f.subs({t: 0, y: y0}))}$',
            f'$y_1 = {y1:.4f}$',
        ]
        return {
            'question': f'Appliquer Euler explicite pour $y\' = {f_expr}$, $y(0) = {y0}$, $h = {latex(h)}$',
            'answer': round(y1, 4),
            'answer_latex': f'{y1:.4f}',
            'solution_latex': f'y_1 = {y1:.4f}',
            'steps': steps,
        }
    elif difficulty == 2:
        a, y0, h = random.randint(1, 3), random.randint(1, 4), Rational(1, random.choice([2, 4, 5]))
        f_expr = f'-{a}*y + t'
        f = sympify(f_expr)
        k1 = float(h) * float(f.subs({t: 0, y: y0}))
        k2 = float(h) * float(f.subs({t: float(h/2), y: y0 + k1/2}))
        y1 = y0 + k2
        steps = [
            f'Méthode d\'Euler modifié (point milieu)',
            f'$k_1 = h f(t_n, y_n) = {k1:.4f}$',
            f'$k_2 = h f(t_n + h/2, y_n + k_1/2) = {k2:.4f}$',
            f'$y_{{n+1}} = y_n + k_2 = {y1:.4f}$',
        ]
        return {
            'question': f'Appliquer Euler modifié pour $y\' = {f_expr}$, $y(0) = {y0}$, $h = {latex(h)}$',
            'answer': round(y1, 4),
            'answer_latex': f'{y1:.4f}',
            'solution_latex': f'y_1 = {y1:.4f}',
            'steps': steps,
        }
    elif difficulty == 3:
        a, y0, h = random.randint(1, 3), random.randint(1, 4), Rational(1, random.choice([2, 4]))
        f_expr = f'-{a}*y + t'
        f = sympify(f_expr)
        k1 = float(h) * float(f.subs({t: 0, y: y0}))
        k2 = float(h) * float(f.subs({t: float(h/2), y: y0 + k1/2}))
        k3 = float(h) * float(f.subs({t: float(h/2), y: y0 + k2/2}))
        k4 = float(h) * float(f.subs({t: float(h), y: y0 + k3}))
        y1 = y0 + (k1 + 2*k2 + 2*k3 + k4)/6
        steps = [
            f'Méthode de Runge-Kutta d\'ordre 4 (RK4)',
            f'$k_1 = h f(t_n, y_n) = {k1:.4f}$',
            f'$k_2 = h f(t_n + h/2, y_n + k_1/2) = {k2:.4f}$',
            f'$k_3 = h f(t_n + h/2, y_n + k_2/2) = {k3:.4f}$',
            f'$k_4 = h f(t_n + h, y_n + k_3) = {k4:.4f}$',
            f'$y_{{n+1}} = y_n + \\frac{{1}}{{6}}(k_1 + 2k_2 + 2k_3 + k_4) = {y1:.4f}$',
        ]
        return {
            'question': f'Appliquer RK4 pour $y\' = {f_expr}$, $y(0) = {y0}$, $h = {latex(h)}$',
            'answer': round(y1, 4),
            'answer_latex': f'{y1:.4f}',
            'solution_latex': f'y_1 = {y1:.4f}',
            'steps': steps,
        }
    elif difficulty == 4:
        steps = [
            'Comparaison Euler / RK2 / RK4 :',
            'Euler explicite : erreur $\\mathcal{O}(h)$',
            'RK2 : erreur $\\mathcal{O}(h^2)$',
            'RK4 : erreur $\\mathcal{O}(h^4)$',
            'RK4 est beaucoup plus précis pour un même pas $h$',
        ]
        return {
            'question': 'Comparer la précision des méthodes d\'Euler, RK2 et RK4',
            'answer': 0,
            'answer_latex': '\\mathcal{O}(h) \\text{ vs } \\mathcal{O}(h^2) \\text{ vs } \\mathcal{O}(h^4)',
            'solution_latex': '\\text{RK4} \\gg \\text{RK2} \\gg \\text{Euler}',
            'steps': steps,
        }
    else:
        steps = [
            'Méthode d\'Adams-Bashforth à 2 pas :',
            '$y_{n+2} = y_{n+1} + \\frac{h}{2}[3f(t_{n+1}, y_{n+1}) - f(t_n, y_n)]$',
            'Issue de l\'interpolation de Newton',
            'Erreur locale : $\\mathcal{O}(h^3)$',
        ]
        return {
            'question': 'Décrire la méthode d\'Adams-Bashforth à 2 pas et son ordre',
            'answer': 0,
            'answer_latex': '\\mathcal{O}(h^3)',
            'solution_latex': 'y_{n+2} = y_{n+1} + \\frac{h}{2}[3f_{n+1} - f_n]',
            'steps': steps,
        }

# ═════════════════════════════════════════════════════════════════════════════
# MODULE 3 : ALGÈBRE LINÉAIRE
# ═════════════════════════════════════════════════════════════════════════════

def generate_matrix_exercise(difficulty):
    """Matrices : déterminant et inverse."""
    steps = []
    if difficulty <= 2:
        size = 2 if difficulty == 1 else 3
        A = np.random.randint(-5, 6, (size, size))
        while abs(np.linalg.det(A)) < 0.5:
            A = np.random.randint(-5, 6, (size, size))
        sympy_A = Matrix(A.tolist())
        det_A = sympy_A.det()
        answer = float(N(det_A))
        if size == 2:
            steps = [
                f'Matrice : $A = {latex(sympy_A)}$',
                f'Déterminant : $\\det(A) = ({A[0,0]})\\cdot({A[1,1]}) - ({A[0,1]})\\cdot({A[1,0]})$',
                f'$\\det(A) = {A[0,0]*A[1,1]} - {A[0,1]*A[1,0]} = {answer}$',
            ]
        else:
            steps = [
                f'Matrice : $A = {latex(sympy_A)}$',
                f'Déterminant (Sarrus) : $\\det(A) = {latex(det_A)} = {answer}$',
            ]
        return {
            'matrix': A.tolist(),
            'question': f'Calculer le déterminant de $A = {latex(sympy_A)}$',
            'answer': answer,
            'answer_latex': latex(det_A),
            'solution_latex': f'\\det(A) = {latex(det_A)} = {answer}',
            'steps': steps,
        }
    elif difficulty <= 4:
        size = 2 if difficulty == 3 else 3
        A = np.random.randint(-3, 4, (size, size))
        while abs(np.linalg.det(A)) < 0.5:
            A = np.random.randint(-3, 4, (size, size))
        sympy_A = Matrix(A.tolist())
        inv_A = sympy_A.inv()
        det_A = sympy_A.det()
        adj_A = sympy_A.adjugate()
        answer = inv_A.tolist()
        steps = [
            f'Matrice : $A = {latex(sympy_A)}$',
            f'Déterminant : $\\det(A) = {latex(det_A)}$',
            f'Comatrice : $\\operatorname{{adj}}(A) = {latex(adj_A)}$',
            f'Inverse : $A^{{-1}} = \\frac{{1}}{{\\det(A)}} \\operatorname{{adj}}(A) = {latex(inv_A)}$',
        ]
        return {
            'matrix': A.tolist(),
            'question': f'Calculer l\'inverse de $A = {latex(sympy_A)}$',
            'answer': answer,
            'answer_latex': latex(inv_A),
            'solution_latex': f'A^{{-1}} = {latex(inv_A)}',
            'steps': steps,
        }
    else:
        a, b = symbols('a b')
        A = Matrix([[a, 1], [2, b]])
        det_A = A.det()
        steps = [
            f'Matrice avec paramètres : $A = {latex(A)}$',
            f'Déterminant : $\\det(A) = {latex(det_A)}$',
            f'A est inversible si $\\det(A) \\neq 0 \\Rightarrow {latex(det_A)} \\neq 0$',
        ]
        return {
            'matrix': [[1, 1], [2, 1]],
            'question': f'Pour quelles valeurs de $a,b$ la matrice $A = {latex(A)}$ est-elle inversible ?',
            'answer': 0,
            'answer_latex': f'{latex(det_A)} \\neq 0',
            'solution_latex': f'\\det(A) = {latex(det_A)} \\neq 0',
            'steps': steps,
        }


def generate_eigenvalue_exercise(difficulty):
    """Valeurs propres, diagonalisation, trigonalisation."""
    steps = []
    if difficulty <= 2:
        A = Matrix([[random.randint(1, 4), random.randint(0, 2)], [random.randint(0, 2), random.randint(1, 4)]])
        eigenvalues = list(A.eigenvals().keys())
        ev_list = ', '.join([latex(ev) for ev in eigenvalues])
        steps = [
            f'Matrice : $A = {latex(A)}$',
            f'Polynôme caractéristique : $\\det(A - \\lambda I) = {latex(A.charpoly().as_expr())}$',
            f'Valeurs propres : ${ev_list}$',
        ]
        return {
            'question': f'Trouver les valeurs propres de $A = {latex(A)}$',
            'answer': [float(N(ev)) for ev in eigenvalues],
            'answer_latex': ev_list,
            'solution_latex': f'\\lambda \\in \\{{{ev_list}\\}}',
            'steps': steps,
        }
    elif difficulty <= 3:
        A = Matrix([[random.randint(1, 3), random.randint(1, 3)], [random.randint(0, 2), random.randint(1, 3)]])
        if A.eigenvals():
            P, D = A.diagonalize()
            steps = [
                f'Diagonalisation de $A = {latex(A)}$',
                f'Matrice de passage $P = {latex(P)}$',
                f'Matrice diagonale $D = {latex(D)}$',
                f'Vérification : $A = PDP^{{-1}}$',
            ]
            return {
                'question': f'Diagonaliser $A = {latex(A)}$',
                'answer': [[float(N(x)) for x in row] for row in D.tolist()],
                'answer_latex': latex(D),
                'solution_latex': f'D = {latex(D)}',
                'steps': steps,
            }
    elif difficulty <= 4:
        A = Matrix([[random.randint(1, 3), random.randint(1, 2), 0], [0, random.randint(1, 3), random.randint(1, 2)], [0, 0, random.randint(1, 3)]])
        eigenvalues = list(A.eigenvals().keys())
        steps = [
            f'Matrice triangulaire : $A = {latex(A)}$',
            f'Les valeurs propres sont les éléments diagonaux : ${latex(eigenvalues)}$',
            f'Sous-espaces propres : $E_{{\\lambda_i}} = \\ker(A - \\lambda_i I)$',
        ]
        return {
            'question': f'Déterminer les sous-espaces propres de $A = {latex(A)}$',
            'answer': 0,
            'answer_latex': latex(eigenvalues),
            'solution_latex': f'\\lambda = {latex(eigenvalues)}',
            'steps': steps,
        }
    else:
        A = Matrix([[2, 1], [0, 2]])
        steps = [
            f'Matrice non diagonalisable : $A = {latex(A)}$',
            f'Valeur propre double $\\lambda = 2$, $\\dim E_2 = 1 < 2$',
            f'Trigonalisation : chercher $P$ tel que $P^{{-1}}AP = T$ triangulaire',
            f'Polynôme minimal : $(X - 2)^2$ (Cayley-Hamilton)',
        ]
        return {
            'question': f'Trigonaliser $A = {latex(A)}$ et donner son polynôme minimal',
            'answer': 0,
            'answer_latex': '(X-2)^2',
            'solution_latex': '\\text{Polynôme minimal} = (X-2)^2',
            'steps': steps,
        }

# ═════════════════════════════════════════════════════════════════════════════
# MODULE 4 : THÉORIE DES GRAPHES
# ═════════════════════════════════════════════════════════════════════════════

def generate_graph_exercise(difficulty, preferred_type=None):
    """Graphes : Dijkstra et Kruskal."""
    n = 4 + difficulty  # 5 à 9 nœuds selon difficulté
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
        steps.append(f'Algorithme de Dijkstra de {start} à {end}')
        while pq:
            d, u = heapq.heappop(pq)
            if d != dist[u]:
                continue
            steps.append(f'Extraire {u} (distance = {d:.1f})')
            if u == end:
                break
            for vv, ww in adj[u]:
                nd = d + ww
                if nd < dist[vv]:
                    dist[vv] = nd
                    prev[vv] = u
                    heapq.heappush(pq, (nd, vv))
                    steps.append(f'Relaxation {u}→{vv} : $d({vv}) = {nd:.1f}$')
        answer = float(dist[end]) if dist[end] != float('inf') else float('inf')
        path = []
        cur = end
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        steps.append(f'Chemin : {" → ".join(map(str, path))}')
        steps.append(f'Distance : $d({start},{end}) = {answer}$')
        return {
            'num_nodes': n,
            'edges': edges,
            'start': start,       
            'end': end,
            'question': f'Déterminer le plus court chemin de {start} à {end} par Dijkstra',
            'answer': answer,
            'answer_latex': str(int(answer)) if answer != float('inf') else '\\infty',
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
        steps = [f'Algorithme de Kruskal — {n} nœuds, {len(edges)} arêtes']
        steps.append('Tri des arêtes par poids croissant :')
        for u, v, w in sorted_edges:
            if union(u, v):
                total += w
                mst_edges.append((u, v, w))
                steps.append(f'Arête {u}—{v} (poids {w}) : **ajoutée** ✅')
            else:
                steps.append(f'Arête {u}—{v} (poids {w}) : rejetée (cycle) ❌')
        steps.append(f'Arêtes du MST : {mst_edges}')
        steps.append(f'Poids total : **{total}**')
        steps.append(f'Vérification : $m = n-1 = {len(mst_edges)}$ arêtes ✅')
        return {
            'type': 'mst',
            'num_nodes': n,
            'edges': edges,
            'question': "Déterminer l'arbre couvrant minimal (MST) par Kruskal",
            'answer': float(total),
            'answer_latex': str(total),
            'solution_latex': f'\\text{{Poids total}} = {total}',
            'steps': steps,
        }

# ═════════════════════════════════════════════════════════════════════════════
# Mappings
# ═════════════════════════════════════════════════════════════════════════════

EXERCISE_GENERATORS = {
    # Systèmes Dynamiques
    'ode': generate_ode_exercise,
    'stability': generate_stability_exercise,
    # Méthodes Numériques
    'numerical_methods': generate_numerical_methods_exercise,
    'convergence': generate_numerical_methods_exercise,  # même générateur, type géré par le frontend
    # Algèbre Linéaire
    'matrix': generate_matrix_exercise,
    'eigenvalues': generate_eigenvalue_exercise,
    # Théorie des Graphes
    'shortest_path': generate_graph_exercise,
    'mst': generate_graph_exercise,
}

# ═════════════════════════════════════════════════════════════════════════════
# Routes
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/generate")
def generate_exercise(
    data: GenerateExerciseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new exercise procedurally"""
    type_mapping = {
        'stability': 'stability',
        'convergence': 'convergence',
        'eigenvalues': 'eigenvalues',
        'shortest_path': 'shortest_path',
        'mst': 'mst',
        'ode': 'ode',
        'numerical_integration': 'numerical_methods',
        'numerical_methods': 'numerical_methods',
        'matrix': 'matrix',
        'graph': 'shortest_path',
    }
    exercise_type = type_mapping.get(data.type, data.type)

    progress = db.query(UserProgress).filter_by(
        user_id=current_user.id, module=data.module
    ).first()
    mode = data.mode if hasattr(data, 'mode') else 'manual'
    difficulty = data.difficulty
    if progress and mode == 'auto':
        difficulty = progress.current_difficulty

    generator = EXERCISE_GENERATORS.get(exercise_type)
    if not generator:
        raise HTTPException(status_code=400, detail=f"Unknown exercise type: {exercise_type}")

    try:
        if exercise_type in ('shortest_path', 'mst', 'graph'):
            problem_data = generator(difficulty, preferred_type=exercise_type)
        else:
            problem_data = generator(difficulty)

        raw_answer_latex = problem_data.get('answer_latex', '')
        raw_solution_latex = problem_data.get('solution_latex', '')
        raw_steps = problem_data.get('steps', [])
        raw_answer = problem_data.get('answer') or problem_data.get('exact_value')

        problem_data = _make_json_safe(problem_data)
        db_answer = _make_json_safe(raw_answer)
        db_steps = [_make_json_safe(s) for s in raw_steps]

        exercise = Exercise(
            title=f"Exercice {exercise_type} — Niveau {difficulty}",
            description=f"Résoudre le problème de {exercise_type}",
            module=data.module,
            difficulty=difficulty,
            problem_data=problem_data,
            solution_data={
                'answer': db_answer,
                'answer_latex': raw_answer_latex,
                'solution_latex': raw_solution_latex,
                'steps': db_steps,
            },
            points=difficulty * 10
        )
        db.add(exercise)
        db.commit()
        db.refresh(exercise)

        exercise_dict = exercise.to_dict()
        exercise_dict['solution_data']['answer_latex'] = raw_answer_latex
        exercise_dict['solution_data']['solution_latex'] = raw_solution_latex
        exercise_dict['solution_data']['steps'] = raw_steps

        return {
            'exercise': exercise_dict,
            'difficulty_adjusted': progress is not None
        }
    except Exception as e:
        print("ERROR in generate_exercise:")
        print(traceback.format_exc())
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
    correct_answer_latex = exercise.solution_data.get('answer_latex', '')

    is_correct = False
    score = 0
    feedback = ""

    if isinstance(correct_answer, (int, float)):
        try:
            if isinstance(user_answer, str) and '/' in user_answer:
                user_val = float(N(sympify(user_answer)))
            else:
                user_val = float(user_answer)
            correct_val = float(correct_answer)
            error = abs(user_val - correct_val)
            rel_error = error / abs(correct_val) if correct_val != 0 else error

            if rel_error < 0.01:
                is_correct = True
                score = 100
                feedback = f"Correct ! $= {correct_answer_latex}$" if correct_answer_latex else "Correct !"
            elif rel_error < 0.05:
                is_correct = True
                score = 80
                feedback = "Presque correct ! Vérifiez vos calculs."
            else:
                is_correct = False
                score = max(0, 100 - int(rel_error * 100))
                latex_str = correct_answer_latex or str(correct_val)
                feedback = f"Incorrect. La réponse est ${latex_str}$"
        except Exception:
            feedback = "Format invalide. Utilisez un nombre ou une fraction (ex: 2/3)."

    elif isinstance(correct_answer, list):
        try:
            user_array = np.array(user_answer)
            correct_array = np.array(correct_answer)
            if user_array.shape == correct_array.shape:
                error = np.linalg.norm(user_array - correct_array)
                if error < 0.01:
                    is_correct = True
                    score = 100
                    feedback = f"Correct ! $= {correct_answer_latex}$" if correct_answer_latex else "Correct !"
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
        'correct_answer_latex': correct_answer_latex if not is_correct else None,
        'progress': progress.to_dict()
    }


@router.get("/history")
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    attempts = db.query(ExerciseAttempt).filter_by(
        user_id=current_user.id
    ).order_by(ExerciseAttempt.created_at.desc()).limit(50).all()
    return {'attempts': [a.to_dict() for a in attempts]}


@router.get("/progress")
def get_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    progress = db.query(UserProgress).filter_by(user_id=current_user.id).all()
    return {'progress': [p.to_dict() for p in progress]}