"""
Linear Algebra API Routes
Algèbre Linéaire - Transformations, SVD, valeurs propres
"""
from flask import Blueprint, request, jsonify
import numpy as np
from scipy import linalg
from scipy.sparse import diags
from scipy.sparse.linalg import eigsh, eigs

la_bp = Blueprint('linear_algebra', __name__)

@la_bp.route('/transform', methods=['POST'])
def transform_matrix():
    """Apply linear transformation to points"""
    data = request.get_json()
    
    matrix = np.array(data.get('matrix', [[1, 0], [0, 1]]))
    points = np.array(data.get('points', [[1, 0], [0, 1], [-1, 0], [0, -1]]))
    
    try:
        # Apply transformation
        transformed = np.dot(points, matrix.T)
        
        # Compute transformation properties
        det = np.linalg.det(matrix)
        rank = np.linalg.matrix_rank(matrix)
        
        # Singular values
        singular_values = np.linalg.svd(matrix, compute_uv=False)
        
        # Condition number
        cond = np.linalg.cond(matrix)
        
        return jsonify({
            'original': points.tolist(),
            'transformed': transformed.tolist(),
            'matrix': matrix.tolist(),
            'properties': {
                'determinant': float(det),
                'rank': int(rank),
                'singular_values': singular_values.tolist(),
                'condition_number': float(cond),
                'is_invertible': abs(det) > 1e-10
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@la_bp.route('/svd', methods=['POST'])
def svd_decomposition():
    """Compute SVD decomposition with step-by-step visualization"""
    data = request.get_json()
    
    matrix = np.array(data.get('matrix', [[3, 0], [0, 1]]))
    
    try:
        # Full SVD
        U, S, Vt = np.linalg.svd(matrix, full_matrices=True)
        
        # Create Sigma matrix
        m, n = matrix.shape
        Sigma = np.zeros((m, n))
        Sigma[:min(m, n), :min(m, n)] = np.diag(S)
        
        # Step-by-step transformation
        # Step 1: V^T * x (rotation/reflection)
        # Step 2: Sigma * (V^T * x) (scaling)
        # Step 3: U * (Sigma * V^T * x) (rotation/reflection)
        
        # Use unit circle for visualization
        theta = np.linspace(0, 2*np.pi, 100)
        unit_circle = np.array([np.cos(theta), np.sin(theta)])
        
        step1 = Vt @ unit_circle
        step2 = Sigma[:2, :2] @ step1 if m >= 2 and n >= 2 else Sigma @ step1
        step3 = U[:2, :2] @ step2 if m >= 2 and n >= 2 else U @ step2
        
        return jsonify({
            'matrix': matrix.tolist(),
            'U': U.tolist(),
            'Sigma': Sigma.tolist(),
            'singular_values': S.tolist(),
            'Vt': Vt.tolist(),
            'steps': {
                'original': unit_circle.tolist(),
                'after_Vt': step1.tolist(),
                'after_Sigma': step2.tolist(),
                'after_U': step3.tolist()
            },
            'properties': {
                'rank': int(np.sum(S > 1e-10)),
                'nullity': min(matrix.shape) - int(np.sum(S > 1e-10)),
                'condition_number': float(S[0] / S[-1]) if S[-1] > 1e-10 else float('inf'),
                'frobenius_norm': float(np.sqrt(np.sum(S**2)))
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@la_bp.route('/eigen', methods=['POST'])
def eigen_decomposition():
    """Compute eigenvalues and eigenvectors"""
    data = request.get_json()
    
    matrix = np.array(data.get('matrix', [[4, 2], [1, 3]]))
    
    try:
        # Compute eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eig(matrix)
        
        # Sort by absolute value
        idx = np.argsort(np.abs(eigenvalues))[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        # Determine stability
        stability = []
        for ev in eigenvalues:
            if np.isreal(ev):
                if ev < 0:
                    stability.append('stable')
                elif ev > 0:
                    stability.append('unstable')
                else:
                    stability.append('center')
            else:
                if np.real(ev) < 0:
                    stability.append('stable spiral')
                elif np.real(ev) > 0:
                    stability.append('unstable spiral')
                else:
                    stability.append('center')
        
        # Check if diagonalizable (by algebraic vs geometric multiplicity)
        unique, counts = np.unique(eigenvalues, return_counts=True)
        is_diagonalizable = len(eigenvalues) == matrix.shape[0]

        eigen_list = []
        for ev, s in zip(eigenvalues, stability):
            if np.isreal(ev):
                value = float(np.real(ev))
            else:
                value = {
                    'real': float(np.real(ev)),
                    'imag': float(np.imag(ev)),
                }
            eigen_list.append({'value': value, 'stability': s})
        
        return jsonify({
            'matrix': matrix.tolist(),
            'eigenvalues': eigen_list,
            'eigenvectors': eigenvectors.tolist(),
            'is_diagonalizable': is_diagonalizable,
            'trace': float(np.trace(matrix)),
            'determinant': float(np.linalg.det(matrix))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@la_bp.route('/iterative', methods=['POST'])
def iterative_methods():
    """Jacobi and Gauss-Seidel iterative methods"""
    data = request.get_json()
    
    A = np.array(data.get('A', [[4, 1], [2, 3]]))
    b = np.array(data.get('b', [1, 2]))
    x0 = np.array(data.get('x0', [0, 0]))
    method = data.get('method', 'jacobi')
    max_iter = data.get('max_iter', 50)
    tol = data.get('tol', 1e-6)
    
    try:
        n = len(b)
        x = x0.copy()
        history = [x.tolist()]
        residuals = []
        
        for iteration in range(max_iter):
            x_new = np.zeros(n)
            
            if method == 'jacobi':
                for i in range(n):
                    sigma = sum(A[i, j] * x[j] for j in range(n) if j != i)
                    x_new[i] = (b[i] - sigma) / A[i, i]
            
            elif method == 'gauss_seidel':
                x_new = x.copy()
                for i in range(n):
                    sigma = sum(A[i, j] * x_new[j] for j in range(i))
                    sigma += sum(A[i, j] * x[j] for j in range(i + 1, n))
                    x_new[i] = (b[i] - sigma) / A[i, i]
            
            residual = np.linalg.norm(A @ x_new - b)
            residuals.append(float(residual))
            history.append(x_new.tolist())
            
            if np.linalg.norm(x_new - x) < tol:
                return jsonify({
                    'method': method,
                    'solution': x_new.tolist(),
                    'iterations': iteration + 1,
                    'converged': True,
                    'history': history,
                    'residuals': residuals,
                    'final_residual': float(residual)
                })
            
            x = x_new
        
        return jsonify({
            'method': method,
            'solution': x.tolist(),
            'iterations': max_iter,
            'converged': False,
            'history': history,
            'residuals': residuals,
            'final_residual': float(residuals[-1]) if residuals else None
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@la_bp.route('/lu', methods=['POST'])
def lu_decomposition():
    """LU decomposition with partial pivoting"""
    data = request.get_json()
    
    matrix = np.array(data.get('matrix', [[2, 1, 1], [4, 3, 3], [8, 7, 9]]))
    
    try:
        P, L, U = linalg.lu(matrix)
        
        return jsonify({
            'matrix': matrix.tolist(),
            'P': P.tolist(),
            'L': L.tolist(),
            'U': U.tolist(),
            'verification': (P @ L @ U).tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@la_bp.route('/qr', methods=['POST'])
def qr_decomposition():
    """QR decomposition using Gram-Schmidt"""
    data = request.get_json()
    
    matrix = np.array(data.get('matrix', [[1, 1], [1, 2], [1, 3]]))
    
    try:
        Q, R = np.linalg.qr(matrix)
        
        return jsonify({
            'matrix': matrix.tolist(),
            'Q': Q.tolist(),
            'R': R.tolist(),
            'is_orthogonal': np.allclose(Q.T @ Q, np.eye(Q.shape[1])),
            'verification': (Q @ R).tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@la_bp.route('/visualize-grid', methods=['POST'])
def visualize_grid():
    """Generate grid for linear transformation visualization"""
    data = request.get_json()
    
    matrix = np.array(data.get('matrix', [[2, 1], [1, 2]]))
    grid_size = data.get('grid_size', 10)
    
    try:
        # Create grid
        x = np.linspace(-grid_size, grid_size, 21)
        y = np.linspace(-grid_size, grid_size, 21)
        
        # Horizontal lines
        h_lines_orig = []
        h_lines_trans = []
        for yi in y:
            line = np.array([[x[0], yi], [x[-1], yi]])
            h_lines_orig.append(line.tolist())
            trans_line = np.dot(line, matrix.T)
            h_lines_trans.append(trans_line.tolist())
        
        # Vertical lines
        v_lines_orig = []
        v_lines_trans = []
        for xi in x:
            line = np.array([[xi, y[0]], [xi, y[-1]]])
            v_lines_orig.append(line.tolist())
            trans_line = np.dot(line, matrix.T)
            v_lines_trans.append(trans_line.tolist())
        
        # Unit vectors
        unit_vectors = np.array([[1, 0], [0, 1]])
        transformed_vectors = np.dot(unit_vectors, matrix.T)
        
        return jsonify({
            'matrix': matrix.tolist(),
            'horizontal_lines_original': h_lines_orig,
            'horizontal_lines_transformed': h_lines_trans,
            'vertical_lines_original': v_lines_orig,
            'vertical_lines_transformed': v_lines_trans,
            'unit_vectors_original': unit_vectors.tolist(),
            'unit_vectors_transformed': transformed_vectors.tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
