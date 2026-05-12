"""
Dynamical Systems API Routes - FastAPI
Systèmes Dynamiques - EDO, portraits de phase, stabilité
"""
import numpy as np
from scipy.integrate import odeint
from scipy.optimize import fsolve
from typing import Optional, List, Union
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic
# ─────────────────────────────────────────────────────────────────────────────
class SimulateRequest(BaseModel):
    system: str = Field(default='harmonic_oscillator')
    params: dict = Field(default_factory=dict)
    initial_state: List[float] = Field(default=[1.0, 0.0])
    t_span: List[float] = Field(default=[0, 20])
    dt: float = Field(default=0.01)

class PhasePortraitRequest(BaseModel):
    system: str = Field(default='harmonic_oscillator')
    params: dict = Field(default_factory=dict)
    x_range: List[float] = Field(default=[-3, 3])
    y_range: List[float] = Field(default=[-3, 3])
    grid_size: int = Field(default=20, ge=5, le=100)

class EquilibriumRequest(BaseModel):
    system: str = Field(default='harmonic_oscillator')
    params: dict = Field(default_factory=dict)
    guesses: List[List[float]] = Field(default=[[0, 0], [1, 1], [-1, -1]])

class BifurcationRequest(BaseModel):
    system: str = Field(default='harmonic_oscillator')
    param_name: str = Field(default='mu')
    param_range: List[float] = Field(default=[0, 2])
    num_points: int = Field(default=50, ge=10, le=500)

# ─────────────────────────────────────────────────────────────────────────────
# Systèmes prédéfinis (inchangés)
# ─────────────────────────────────────────────────────────────────────────────
SYSTEMS = {
    'harmonic_oscillator': {
        'name': 'Oscillateur Harmonique',
        'params': {'omega': 1.0, 'gamma': 0.1},
        'equations': ['dx/dt = v', 'dv/dt = -omega²*x - gamma*v'],
        'description': 'Oscillateur harmonique amorti'
    },
    'lotka_volterra': {
        'name': 'Lotka-Volterra',
        'params': {'alpha': 1.0, 'beta': 0.1, 'gamma': 1.5, 'delta': 0.075},
        'equations': ['dx/dt = αx - βxy', 'dy/dt = δxy - γy'],
        'description': 'Modèle proie-prédateur'
    },
    'lorenz': {
        'name': 'Système de Lorenz',
        'params': {'sigma': 10.0, 'rho': 28.0, 'beta': 8.0/3.0},
        'equations': ['dx/dt = σ(y-x)', 'dy/dt = x(ρ-z) - y', 'dz/dt = xy - βz'],
        'description': 'Système chaotique de Lorenz'
    },
    'pendulum': {
        'name': 'Pendule Simple',
        'params': {'g': 9.81, 'L': 1.0, 'damping': 0.1},
        'equations': ['dθ/dt = ω', 'dω/dt = -(g/L)sin(θ) - damping*ω'],
        'description': 'Pendule simple avec amortissement'
    },
    'double_pendulum': {
        'name': 'Pendule Double',
        'params': {'m1': 1.0, 'm2': 1.0, 'L1': 1.0, 'L2': 1.0, 'g': 9.81},
        'equations': ['Système couplé non-linéaire'],
        'description': 'Pendule double chaotique'
    },
    'van_der_pol': {
        'name': 'Oscillateur de Van der Pol',
        'params': {'mu': 1.0, 'omega': 1.0},
        'equations': ['dx/dt = y', 'dy/dt = μ(1-x²)y - ω²x'],
        'description': 'Oscillateur à cycle limite'
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# Fonctions système (inchangées)
# ─────────────────────────────────────────────────────────────────────────────
def harmonic_oscillator(state, t, omega, gamma):
    x, v = state
    return [v, -omega**2 * x - gamma * v]

def lotka_volterra(state, t, alpha, beta, gamma, delta):
    x, y = state
    return [alpha * x - beta * x * y, delta * x * y - gamma * y]

def lorenz_system(state, t, sigma, rho, beta):
    x, y, z = state
    return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

def pendulum(state, t, g, L, damping):
    theta, omega = state
    return [omega, -(g / L) * np.sin(theta) - damping * omega]

def van_der_pol(state, t, mu, omega):
    x, y = state
    return [y, mu * (1 - x**2) * y - omega**2 * x]

SYSTEM_FUNCTIONS = {
    'harmonic_oscillator': harmonic_oscillator,
    'lotka_volterra': lotka_volterra,
    'lorenz': lorenz_system,
    'pendulum': pendulum,
    'van_der_pol': van_der_pol
}

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/systems")
def get_systems():
    """Get list of available dynamical systems"""
    return {
        'systems': [{'id': k, **v} for k, v in SYSTEMS.items()]
    }

@router.post("/simulate")
def simulate(data: SimulateRequest):
    """Simulate a dynamical system"""
    if data.system not in SYSTEM_FUNCTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown system: {data.system}")
    
    system_func = SYSTEM_FUNCTIONS[data.system]
    default_params = SYSTEMS[data.system]['params']
    merged_params = {**default_params, **data.params}
    param_values = list(merged_params.values())
    
    t = np.arange(data.t_span[0], data.t_span[1], data.dt)
    
    try:
        solution = odeint(system_func, data.initial_state, t, args=tuple(param_values))
        return {
            't': t.tolist(),
            'solution': solution.tolist(),
            'dimensions': len(data.initial_state),
            'params': merged_params,
            'system': data.system
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/phase-portrait")
def phase_portrait(data: PhasePortraitRequest):
    """Generate phase portrait data"""
    if data.system not in SYSTEM_FUNCTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown system: {data.system}")
    
    system_func = SYSTEM_FUNCTIONS[data.system]
    default_params = SYSTEMS[data.system]['params']
    merged_params = {**default_params, **data.params}
    param_values = list(merged_params.values())
    
    x = np.linspace(data.x_range[0], data.x_range[1], data.grid_size)
    y = np.linspace(data.y_range[0], data.y_range[1], data.grid_size)
    X, Y = np.meshgrid(x, y)
    
    U = np.zeros_like(X)
    V = np.zeros_like(Y)
    
    for i in range(data.grid_size):
        for j in range(data.grid_size):
            derivatives = system_func([X[i, j], Y[i, j]], 0, *param_values)
            U[i, j] = derivatives[0]
            V[i, j] = derivatives[1]
    
    magnitude = np.sqrt(U**2 + V**2)
    U_norm = U / (magnitude + 1e-10)
    V_norm = V / (magnitude + 1e-10)
    
    return {
        'X': X.tolist(),
        'Y': Y.tolist(),
        'U': U.tolist(),
        'V': V.tolist(),
        'U_norm': U_norm.tolist(),
        'V_norm': V_norm.tolist(),
        'magnitude': magnitude.tolist()
    }

@router.post("/equilibrium")
def find_equilibrium(data: EquilibriumRequest):
    """Find equilibrium points and analyze stability"""
    if data.system not in SYSTEM_FUNCTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown system: {data.system}")
    
    system_func = SYSTEM_FUNCTIONS[data.system]
    default_params = SYSTEMS[data.system]['params']
    merged_params = {**default_params, **data.params}
    param_values = list(merged_params.values())
    
    equilibria = []
    found_points = set()
    
    for guess in data.guesses:
        try:
            eq = fsolve(lambda s: system_func(s, 0, *param_values), guess, full_output=False)
            eq_rounded = tuple(np.round(eq, 6))
            if eq_rounded not in found_points:
                found_points.add(eq_rounded)
                
                eps = 1e-8
                n = len(eq)
                J = np.zeros((n, n))
                for i in range(n):
                    d = np.zeros(n)
                    d[i] = eps
                    J[:, i] = (np.array(system_func(eq + d, 0, *param_values)) - 
                               np.array(system_func(eq - d, 0, *param_values))) / (2 * eps)
                
                eigenvalues = np.linalg.eigvals(J)
                eigenvalues_json = []
                for ev in eigenvalues:
                    if np.isreal(ev):
                        eigenvalues_json.append(float(np.real(ev)))
                    else:
                        eigenvalues_json.append({
                            'real': float(np.real(ev)),
                            'imag': float(np.imag(ev)),
                        })
                
                real_parts = np.real(eigenvalues)
                if all(r < 0 for r in real_parts):
                    stability = 'stable'
                elif any(r > 0 for r in real_parts):
                    stability = 'unstable'
                else:
                    stability = 'center'
                
                equilibria.append({
                    'point': eq.tolist(),
                    'eigenvalues': eigenvalues_json,
                    'stability': stability,
                    'jacobian': J.tolist()
                })
        except Exception:
            pass
    
    return {'equilibria': equilibria, 'count': len(equilibria)}

@router.post("/bifurcation")
def bifurcation_analysis(data: BifurcationRequest):
    """Simple bifurcation analysis by varying a parameter"""
    param_values = np.linspace(data.param_range[0], data.param_range[1], data.num_points)
    return {
        'param_name': data.param_name,
        'param_values': param_values.tolist(),
        'note': 'Bifurcation analysis requires specialized tools. Consider using PyDSTool or AUTO.'
    }