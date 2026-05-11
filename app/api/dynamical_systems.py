"""
Dynamical Systems API Routes
Systèmes Dynamiques - EDO, portraits de phase, stabilité
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import numpy as np
from scipy.integrate import odeint, solve_ivp
from scipy.optimize import fsolve
import json

ds_bp = Blueprint('dynamical_systems', __name__)

# Predefined systems
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

def harmonic_oscillator(state, t, omega, gamma):
    """Oscillateur harmonique amorti"""
    x, v = state
    dxdt = v
    dvdt = -omega**2 * x - gamma * v
    return [dxdt, dvdt]

def lotka_volterra(state, t, alpha, beta, gamma, delta):
    """Modèle Lotka-Volterra"""
    x, y = state
    dxdt = alpha * x - beta * x * y
    dydt = delta * x * y - gamma * y
    return [dxdt, dydt]

def lorenz_system(state, t, sigma, rho, beta):
    """Système de Lorenz"""
    x, y, z = state
    dxdt = sigma * (y - x)
    dydt = x * (rho - z) - y
    dzdt = x * y - beta * z
    return [dxdt, dydt, dzdt]

def pendulum(state, t, g, L, damping):
    """Pendule simple"""
    theta, omega = state
    dthetadt = omega
    domegadt = -(g / L) * np.sin(theta) - damping * omega
    return [dthetadt, domegadt]

def van_der_pol(state, t, mu, omega):
    """Oscillateur de Van der Pol"""
    x, y = state
    dxdt = y
    dydt = mu * (1 - x**2) * y - omega**2 * x
    return [dxdt, dydt]

SYSTEM_FUNCTIONS = {
    'harmonic_oscillator': harmonic_oscillator,
    'lotka_volterra': lotka_volterra,
    'lorenz': lorenz_system,
    'pendulum': pendulum,
    'van_der_pol': van_der_pol
}

@ds_bp.route('/systems', methods=['GET'])
def get_systems():
    """Get list of available dynamical systems"""
    return jsonify({
        'systems': [
            {'id': k, **v} for k, v in SYSTEMS.items()
        ]
    })

@ds_bp.route('/simulate', methods=['POST'])
def simulate():
    """Simulate a dynamical system"""
    data = request.get_json()
    
    system_id = data.get('system', 'harmonic_oscillator')
    params = data.get('params', {})
    initial_state = data.get('initial_state', [1.0, 0.0])
    t_span = data.get('t_span', [0, 20])
    dt = data.get('dt', 0.01)
    
    if system_id not in SYSTEM_FUNCTIONS:
        return jsonify({'error': f'Unknown system: {system_id}'}), 400
    
    # Get system function and default params
    system_func = SYSTEM_FUNCTIONS[system_id]
    default_params = SYSTEMS[system_id]['params']
    
    # Merge with user params
    merged_params = {**default_params, **params}
    param_values = list(merged_params.values())
    
    # Time array
    t = np.arange(t_span[0], t_span[1], dt)
    
    # Solve ODE
    try:
        solution = odeint(system_func, initial_state, t, args=tuple(param_values))
        
        # Convert to lists for JSON
        result = {
            't': t.tolist(),
            'solution': solution.tolist(),
            'dimensions': len(initial_state),
            'params': merged_params,
            'system': system_id
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ds_bp.route('/phase-portrait', methods=['POST'])
def phase_portrait():
    """Generate phase portrait data"""
    data = request.get_json()
    
    system_id = data.get('system', 'harmonic_oscillator')
    params = data.get('params', {})
    x_range = data.get('x_range', [-3, 3])
    y_range = data.get('y_range', [-3, 3])
    grid_size = data.get('grid_size', 20)
    
    if system_id not in SYSTEM_FUNCTIONS:
        return jsonify({'error': f'Unknown system: {system_id}'}), 400
    
    system_func = SYSTEM_FUNCTIONS[system_id]
    default_params = SYSTEMS[system_id]['params']
    merged_params = {**default_params, **params}
    param_values = list(merged_params.values())
    
    # Create grid
    x = np.linspace(x_range[0], x_range[1], grid_size)
    y = np.linspace(y_range[0], y_range[1], grid_size)
    X, Y = np.meshgrid(x, y)
    
    # Compute vector field
    U = np.zeros_like(X)
    V = np.zeros_like(Y)
    
    for i in range(grid_size):
        for j in range(grid_size):
            derivatives = system_func([X[i, j], Y[i, j]], 0, *param_values)
            U[i, j] = derivatives[0]
            V[i, j] = derivatives[1]
    
    # Normalize for better visualization
    magnitude = np.sqrt(U**2 + V**2)
    U_norm = U / (magnitude + 1e-10)
    V_norm = V / (magnitude + 1e-10)
    
    return jsonify({
        'X': X.tolist(),
        'Y': Y.tolist(),
        'U': U.tolist(),
        'V': V.tolist(),
        'U_norm': U_norm.tolist(),
        'V_norm': V_norm.tolist(),
        'magnitude': magnitude.tolist()
    })

@ds_bp.route('/equilibrium', methods=['POST'])
def find_equilibrium():
    """Find equilibrium points and analyze stability"""
    data = request.get_json()
    
    system_id = data.get('system', 'harmonic_oscillator')
    params = data.get('params', {})
    guesses = data.get('guesses', [[0, 0], [1, 1], [-1, -1]])
    
    if system_id not in SYSTEM_FUNCTIONS:
        return jsonify({'error': f'Unknown system: {system_id}'}), 400
    
    system_func = SYSTEM_FUNCTIONS[system_id]
    default_params = SYSTEMS[system_id]['params']
    merged_params = {**default_params, **params}
    param_values = list(merged_params.values())
    
    # Find equilibrium points
    equilibria = []
    found_points = set()
    
    for guess in guesses:
        try:
            eq = fsolve(lambda s: system_func(s, 0, *param_values), guess, full_output=False)
            # Round to avoid duplicates
            eq_rounded = tuple(np.round(eq, 6))
            if eq_rounded not in found_points:
                found_points.add(eq_rounded)
                
                # Compute Jacobian numerically for stability analysis
                eps = 1e-8
                n = len(eq)
                J = np.zeros((n, n))
                for i in range(n):
                    d = np.zeros(n)
                    d[i] = eps
                    J[:, i] = (np.array(system_func(eq + d, 0, *param_values)) - 
                               np.array(system_func(eq - d, 0, *param_values))) / (2 * eps)
                
                # Eigenvalues
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
                
                # Stability classification
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
        except:
            pass
    
    return jsonify({
        'equilibria': equilibria,
        'count': len(equilibria)
    })

@ds_bp.route('/bifurcation', methods=['POST'])
def bifurcation_analysis():
    """Simple bifurcation analysis by varying a parameter"""
    data = request.get_json()
    
    system_id = data.get('system', 'harmonic_oscillator')
    param_name = data.get('param_name', 'mu')
    param_range = data.get('param_range', [0, 2])
    num_points = data.get('num_points', 50)
    
    # This is a simplified bifurcation diagram
    # For more complex analysis, dedicated libraries like PyDSTool would be better
    
    param_values = np.linspace(param_range[0], param_range[1], num_points)
    
    return jsonify({
        'param_name': param_name,
        'param_values': param_values.tolist(),
        'note': 'Bifurcation analysis requires specialized tools. Consider using PyDSTool or AUTO.'
    })
