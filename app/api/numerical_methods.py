"""
Numerical Methods API Routes - FastAPI
Méthodes Numériques - Euler, Runge-Kutta, etc.
"""
import numpy as np
from sympy import symbols, sympify, lambdify
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic
# ─────────────────────────────────────────────────────────────────────────────
class SolveRequest(BaseModel):
    method: str = Field(default='runge_kutta_4')
    function: str = Field(default='-y + sin(t)')
    y0: float = Field(default=1.0)
    t0: float = Field(default=0.0)
    tf: float = Field(default=10.0)
    h: float = Field(default=0.1, gt=0)

class CompareRequest(BaseModel):
    methods: List[str] = Field(default=['euler_explicit', 'runge_kutta_4'])
    function: str = Field(default='-y + sin(t)')
    y0: float = Field(default=1.0)
    t0: float = Field(default=0.0)
    tf: float = Field(default=10.0)
    h: float = Field(default=0.1, gt=0)
    exact_solution: Optional[str] = None

class ConvergenceRequest(BaseModel):
    method: str = Field(default='runge_kutta_4')
    function: str = Field(default='-y + sin(t)')
    y0: float = Field(default=1.0)
    t0: float = Field(default=0.0)
    tf: float = Field(default=10.0)
    exact_solution: str

class StabilityRequest(BaseModel):
    method: str = Field(default='euler_explicit')

# ─────────────────────────────────────────────────────────────────────────────
# Méthodes
# ─────────────────────────────────────────────────────────────────────────────
METHODS = {
    'euler_explicit': {'name': 'Euler Explicite', 'order': 1, 'description': "Méthode d'Euler explicite (avant)"},
    'euler_implicit': {'name': 'Euler Implicite', 'order': 1, 'description': "Méthode d'Euler implicite (arrière)"},
    'euler_modified': {'name': 'Euler Modifié', 'order': 2, 'description': "Méthode d'Euler modifiée (point milieu)"},
    'runge_kutta_2': {'name': 'Runge-Kutta ordre 2', 'order': 2, 'description': "Méthode de Runge-Kutta d'ordre 2"},
    'runge_kutta_4': {'name': 'Runge-Kutta ordre 4', 'order': 4, 'description': 'Méthode de Runge-Kutta classique ordre 4'},
    'adams_bashforth_2': {'name': 'Adams-Bashforth ordre 2', 'order': 2, 'description': "Méthode d'Adams-Bashforth à 2 pas"},
    'adams_moulton_2': {'name': 'Adams-Moulton ordre 2', 'order': 2, 'description': "Méthode d'Adams-Moulton (trapèzes)"}
}

# ─────────────────────────────────────────────────────────────────────────────
# Fonctions utilitaires
# ─────────────────────────────────────────────────────────────────────────────
def parse_function(func_str):
    x, y, t = symbols('x y t')
    func_str = func_str.replace('^', '**')
    try:
        expr = sympify(func_str)
        return lambdify((t, y), expr, modules=['numpy'])
    except Exception:
        return None

def euler_explicit(f, y0, t0, tf, h):
    n = int((tf - t0) / h)
    t = np.linspace(t0, tf, n + 1)
    y = np.zeros(n + 1)
    y[0] = y0
    for i in range(n):
        y[i + 1] = y[i] + h * f(t[i], y[i])
    return t, y

def euler_modified(f, y0, t0, tf, h):
    n = int((tf - t0) / h)
    t = np.linspace(t0, tf, n + 1)
    y = np.zeros(n + 1)
    y[0] = y0
    for i in range(n):
        k1 = f(t[i], y[i])
        k2 = f(t[i] + h / 2, y[i] + h * k1 / 2)
        y[i + 1] = y[i] + h * k2
    return t, y

def runge_kutta_2(f, y0, t0, tf, h):
    n = int((tf - t0) / h)
    t = np.linspace(t0, tf, n + 1)
    y = np.zeros(n + 1)
    y[0] = y0
    for i in range(n):
        k1 = f(t[i], y[i])
        k2 = f(t[i] + h, y[i] + h * k1)
        y[i + 1] = y[i] + h * (k1 + k2) / 2
    return t, y

def runge_kutta_4(f, y0, t0, tf, h):
    n = int((tf - t0) / h)
    t = np.linspace(t0, tf, n + 1)
    y = np.zeros(n + 1)
    y[0] = y0
    for i in range(n):
        k1 = f(t[i], y[i])
        k2 = f(t[i] + h / 2, y[i] + h * k1 / 2)
        k3 = f(t[i] + h / 2, y[i] + h * k2 / 2)
        k4 = f(t[i] + h, y[i] + h * k3)
        y[i + 1] = y[i] + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
    return t, y

def adams_bashforth_2(f, y0, t0, tf, h):
    n = int((tf - t0) / h)
    t = np.linspace(t0, tf, n + 1)
    y = np.zeros(n + 1)
    y[0] = y0
    k1, k2, k3, k4 = f(t[0], y[0]), f(t[0] + h/2, y[0] + h*k1/2), f(t[0] + h/2, y[0] + h*k2/2), f(t[0] + h, y[0] + h*k3)
    y[1] = y[0] + h * (k1 + 2*k2 + 2*k3 + k4) / 6
    for i in range(1, n):
        y[i + 1] = y[i] + h * (3*f(t[i], y[i]) - f(t[i-1], y[i-1])) / 2
    return t, y

METHOD_FUNCTIONS = {
    'euler_explicit': euler_explicit,
    'euler_modified': euler_modified,
    'runge_kutta_2': runge_kutta_2,
    'runge_kutta_4': runge_kutta_4,
    'adams_bashforth_2': adams_bashforth_2
}

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/methods")
def get_methods():
    return {'methods': [{'id': k, **v} for k, v in METHODS.items()]}

@router.post("/solve")
def solve_ode(data: SolveRequest):
    if data.method not in METHOD_FUNCTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown method: {data.method}")
    f = parse_function(data.function)
    if f is None:
        raise HTTPException(status_code=400, detail="Invalid function expression")
    try:
        method_func = METHOD_FUNCTIONS[data.method]
        t, y = method_func(f, data.y0, data.t0, data.tf, data.h)
        return {'method': data.method, 't': t.tolist(), 'y': y.tolist(), 'steps': len(t), 'step_size': data.h}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare")
def compare_methods(data: CompareRequest):
    f = parse_function(data.function)
    if f is None:
        raise HTTPException(status_code=400, detail="Invalid function expression")

    results = {}
    t_exact = y_exact = None
    if data.exact_solution:
        try:
            t_sym = symbols('t')
            exact_expr = sympify(data.exact_solution)
            exact_func = lambdify(t_sym, exact_expr, modules=['numpy'])
            t_exact = np.linspace(data.t0, data.tf, 1000)
            y_exact = exact_func(t_exact)
        except Exception:
            pass

    for method_id in data.methods:
        if method_id not in METHOD_FUNCTIONS:
            continue
        try:
            method_func = METHOD_FUNCTIONS[method_id]
            t, y = method_func(f, data.y0, data.t0, data.tf, data.h)
            result = {'t': t.tolist(), 'y': y.tolist()}
            if y_exact is not None:
                y_exact_interp = np.interp(t, t_exact, y_exact)
                error = np.abs(y - y_exact_interp)
                result['error'] = error.tolist()
                result['max_error'] = float(np.max(error))
                result['rms_error'] = float(np.sqrt(np.mean(error**2)))
            results[method_id] = result
        except Exception as e:
            results[method_id] = {'error': str(e)}

    response = {'results': results, 'methods_compared': data.methods, 'step_size': data.h}
    if y_exact is not None:
        response['exact'] = {'t': t_exact.tolist(), 'y': y_exact.tolist()}
    return response

@router.post("/convergence")
def convergence_study(data: ConvergenceRequest):
    if data.method not in METHOD_FUNCTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown method: {data.method}")
    f = parse_function(data.function)
    if f is None:
        raise HTTPException(status_code=400, detail="Invalid function expression")

    try:
        t_sym = symbols('t')
        exact_expr = sympify(data.exact_solution)
        exact_func = lambdify(t_sym, exact_expr, modules=['numpy'])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid exact solution expression")

    h_values = [0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625]
    errors = []
    method_func = METHOD_FUNCTIONS[data.method]

    for h in h_values:
        try:
            t, y = method_func(f, data.y0, data.t0, data.tf, h)
            y_exact = exact_func(t)
            errors.append({'h': h, 'error': float(np.max(np.abs(y - y_exact))), 'steps': len(t)})
        except Exception:
            pass

    estimated_order = None
    if len(errors) >= 2:
        log_h = np.log([e['h'] for e in errors[-2:]])
        log_err = np.log([e['error'] for e in errors[-2:]])
        estimated_order = -(log_err[1] - log_err[0]) / (log_h[1] - log_h[0])

    return {
        'method': data.method,
        'theoretical_order': METHODS[data.method]['order'],
        'estimated_order': estimated_order,
        'convergence_data': errors
    }

@router.post("/stability")
def stability_analysis(data: StabilityRequest):
    stability_info = {
        'euler_explicit': {'region': 'Disk |1 + z| < 1', 'stable_region': 'Re(z) < 0 and |1 + z| < 1', 'description': 'Conditionnellement stable'},
        'euler_implicit': {'region': 'Tout le plan gauche', 'stable_region': 'A-stable', 'description': 'Inconditionnellement stable'},
        'runge_kutta_4': {'region': "Région complexe autour de l'origine", 'stable_region': 'Conditionnellement stable', 'description': "Stabilité limitée sur l'axe imaginaire"}
    }
    return {'method': data.method, 'stability': stability_info.get(data.method, {'description': 'Information non disponible'})}