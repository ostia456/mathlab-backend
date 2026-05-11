"""
Numerical Methods API Routes
Méthodes Numériques - Euler, Runge-Kutta, etc.
"""
from flask import Blueprint, request, jsonify
import numpy as np
from sympy import symbols, sympify, lambdify, integrate, exp, sin, cos, log, sqrt, pi, E

nm_bp = Blueprint('numerical_methods', __name__)

# Available methods
METHODS = {
    'euler_explicit': {
        'name': 'Euler Explicite',
        'order': 1,
        'description': 'Méthode d\'Euler explicite (avant)'
    },
    'euler_implicit': {
        'name': 'Euler Implicite',
        'order': 1,
        'description': 'Méthode d\'Euler implicite (arrière)'
    },
    'euler_modified': {
        'name': 'Euler Modifié',
        'order': 2,
        'description': 'Méthode d\'Euler modifiée (point milieu)'
    },
    'runge_kutta_2': {
        'name': 'Runge-Kutta ordre 2',
        'order': 2,
        'description': 'Méthode de Runge-Kutta d\'ordre 2'
    },
    'runge_kutta_4': {
        'name': 'Runge-Kutta ordre 4',
        'order': 4,
        'description': 'Méthode de Runge-Kutta classique d\'ordre 4'
    },
    'adams_bashforth_2': {
        'name': 'Adams-Bashforth ordre 2',
        'order': 2,
        'description': 'Méthode d\'Adams-Bashforth à 2 pas'
    },
    'adams_moulton_2': {
        'name': 'Adams-Moulton ordre 2',
        'order': 2,
        'description': 'Méthode d\'Adams-Moulton (trapèzes)'
    }
}

def parse_function(func_str):
    """Parse a mathematical function string to a callable"""
    x = symbols('x')
    y = symbols('y')
    t = symbols('t')
    
    # Replace common functions
    func_str = func_str.replace('^', '**')
    
    try:
        expr = sympify(func_str)
        return lambdify((t, y), expr, modules=['numpy'])
    except:
        return None

def euler_explicit(f, y0, t0, tf, h):
    """Explicit Euler method"""
    n = int((tf - t0) / h)
    t = np.linspace(t0, tf, n + 1)
    y = np.zeros(n + 1)
    y[0] = y0
    
    for i in range(n):
        y[i + 1] = y[i] + h * f(t[i], y[i])
    
    return t, y

def euler_modified(f, y0, t0, tf, h):
    """Modified Euler method (midpoint)"""
    n = int((tf - t0) / h)
    t = np.linspace(t0, tf, n + 1)
    y = np.zeros(n + 1)
    y[0] = y0
    
    for i in range(n):
        k1 = f(t[i], y[i])
        k2 = f(t[i] + h/2, y[i] + h*k1/2)
        y[i + 1] = y[i] + h * k2
    
    return t, y

def runge_kutta_2(f, y0, t0, tf, h):
    """Runge-Kutta order 2 (Heun's method)"""
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
    """Classical Runge-Kutta order 4"""
    n = int((tf - t0) / h)
    t = np.linspace(t0, tf, n + 1)
    y = np.zeros(n + 1)
    y[0] = y0
    
    for i in range(n):
        k1 = f(t[i], y[i])
        k2 = f(t[i] + h/2, y[i] + h*k1/2)
        k3 = f(t[i] + h/2, y[i] + h*k2/2)
        k4 = f(t[i] + h, y[i] + h*k3)
        y[i + 1] = y[i] + h * (k1 + 2*k2 + 2*k3 + k4) / 6
    
    return t, y

def adams_bashforth_2(f, y0, t0, tf, h):
    """Adams-Bashforth 2-step method"""
    n = int((tf - t0) / h)
    t = np.linspace(t0, tf, n + 1)
    y = np.zeros(n + 1)
    y[0] = y0
    
    # Use RK4 for first step
    k1 = f(t[0], y[0])
    k2 = f(t[0] + h/2, y[0] + h*k1/2)
    k3 = f(t[0] + h/2, y[0] + h*k2/2)
    k4 = f(t[0] + h, y[0] + h*k3)
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

@nm_bp.route('/methods', methods=['GET'])
def get_methods():
    """Get list of available numerical methods"""
    return jsonify({'methods': [{'id': k, **v} for k, v in METHODS.items()]})

@nm_bp.route('/solve', methods=['POST'])
def solve_ode():
    """Solve ODE using specified numerical method"""
    data = request.get_json()
    
    method_id = data.get('method', 'runge_kutta_4')
    func_str = data.get('function', '-y + sin(t)')
    y0 = data.get('y0', 1.0)
    t0 = data.get('t0', 0.0)
    tf = data.get('tf', 10.0)
    h = data.get('h', 0.1)
    
    if method_id not in METHOD_FUNCTIONS:
        return jsonify({'error': f'Unknown method: {method_id}'}), 400
    
    # Parse function
    f = parse_function(func_str)
    if f is None:
        return jsonify({'error': 'Invalid function expression'}), 400
    
    try:
        method_func = METHOD_FUNCTIONS[method_id]
        t, y = method_func(f, y0, t0, tf, h)
        
        return jsonify({
            'method': method_id,
            't': t.tolist(),
            'y': y.tolist(),
            'steps': len(t),
            'step_size': h
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@nm_bp.route('/compare', methods=['POST'])
def compare_methods():
    """Compare multiple numerical methods on the same problem"""
    data = request.get_json()
    
    methods = data.get('methods', ['euler_explicit', 'runge_kutta_4'])
    func_str = data.get('function', '-y + sin(t)')
    y0 = data.get('y0', 1.0)
    t0 = data.get('t0', 0.0)
    tf = data.get('tf', 10.0)
    h = data.get('h', 0.1)
    exact_solution = data.get('exact_solution')  # Optional exact solution string
    
    # Parse function
    f = parse_function(func_str)
    if f is None:
        return jsonify({'error': 'Invalid function expression'}), 400
    
    results = {}
    errors = {}
    
    # Compute exact solution if provided
    t_exact = None
    y_exact = None
    if exact_solution:
        try:
            t_sym = symbols('t')
            exact_expr = sympify(exact_solution)
            exact_func = lambdify(t_sym, exact_expr, modules=['numpy'])
            t_exact = np.linspace(t0, tf, 1000)
            y_exact = exact_func(t_exact)
        except:
            pass
    
    for method_id in methods:
        if method_id not in METHOD_FUNCTIONS:
            continue
        
        try:
            method_func = METHOD_FUNCTIONS[method_id]
            t, y = method_func(f, y0, t0, tf, h)
            
            results[method_id] = {
                't': t.tolist(),
                'y': y.tolist()
            }
            
            # Calculate error if exact solution available
            if y_exact is not None:
                y_exact_interp = np.interp(t, t_exact, y_exact)
                error = np.abs(y - y_exact_interp)
                results[method_id]['error'] = error.tolist()
                results[method_id]['max_error'] = float(np.max(error))
                results[method_id]['rms_error'] = float(np.sqrt(np.mean(error**2)))
        
        except Exception as e:
            results[method_id] = {'error': str(e)}
    
    response = {
        'results': results,
        'methods_compared': methods,
        'step_size': h
    }
    
    if y_exact is not None:
        response['exact'] = {
            't': t_exact.tolist(),
            'y': y_exact.tolist()
        }
    
    return jsonify(response)

@nm_bp.route('/convergence', methods=['POST'])
def convergence_study():
    """Study convergence order by varying step size"""
    data = request.get_json()
    
    method_id = data.get('method', 'runge_kutta_4')
    func_str = data.get('function', '-y + sin(t)')
    y0 = data.get('y0', 1.0)
    t0 = data.get('t0', 0.0)
    tf = data.get('tf', 10.0)
    exact_solution = data.get('exact_solution')
    
    if not exact_solution:
        return jsonify({'error': 'Exact solution required for convergence study'}), 400
    
    # Step sizes to test
    h_values = [0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625]
    
    f = parse_function(func_str)
    if f is None:
        return jsonify({'error': 'Invalid function expression'}), 400
    
    # Parse exact solution
    try:
        t_sym = symbols('t')
        exact_expr = sympify(exact_solution)
        exact_func = lambdify(t_sym, exact_expr, modules=['numpy'])
    except:
        return jsonify({'error': 'Invalid exact solution expression'}), 400
    
    errors = []
    method_func = METHOD_FUNCTIONS.get(method_id)
    
    if not method_func:
        return jsonify({'error': f'Unknown method: {method_id}'}), 400
    
    for h in h_values:
        try:
            t, y = method_func(f, y0, t0, tf, h)
            y_exact = exact_func(t)
            max_error = np.max(np.abs(y - y_exact))
            errors.append({
                'h': h,
                'error': float(max_error),
                'steps': len(t)
            })
        except:
            pass
    
    # Estimate convergence order
    if len(errors) >= 2:
        # Use last two points
        log_h = np.log([e['h'] for e in errors[-2:]])
        log_err = np.log([e['error'] for e in errors[-2:]])
        slope = (log_err[1] - log_err[0]) / (log_h[1] - log_h[0])
        estimated_order = -slope
    else:
        estimated_order = None
    
    return jsonify({
        'method': method_id,
        'theoretical_order': METHODS[method_id]['order'],
        'estimated_order': estimated_order,
        'convergence_data': errors
    })

@nm_bp.route('/stability', methods=['POST'])
def stability_analysis():
    """Analyze stability region for a method"""
    data = request.get_json()
    
    method_id = data.get('method', 'euler_explicit')
    
    # Stability regions for common methods
    stability_info = {
        'euler_explicit': {
            'region': 'Disk |1 + z| < 1',
            'stable_region': 'Re(z) < 0 and |1 + z| < 1',
            'description': 'Conditionnellement stable, pas limité'
        },
        'euler_implicit': {
            'region': 'Tout le plan gauche',
            'stable_region': 'A-stable',
            'description': 'Inconditionnellement stable'
        },
        'runge_kutta_4': {
            'region': 'Région complexe autour de l\'origine',
            'stable_region': 'Conditionnellement stable',
            'description': 'Stabilité limitée sur l\'axe imaginaire'
        }
    }
    
    return jsonify({
        'method': method_id,
        'stability': stability_info.get(method_id, {'description': 'Information non disponible'})
    })
