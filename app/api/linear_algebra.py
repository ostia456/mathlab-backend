"""
Linear Algebra API Routes - FastAPI
Algèbre Linéaire - Transformations, SVD, valeurs propres
"""
import numpy as np
from scipy import linalg
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic
# ─────────────────────────────────────────────────────────────────────────────
class TransformRequest(BaseModel):
    matrix: List[List[float]] = Field(default=[[1, 0], [0, 1]])
    points: List[List[float]] = Field(default=[[1, 0], [0, 1], [-1, 0], [0, -1]])

class SvdRequest(BaseModel):
    matrix: List[List[float]] = Field(default=[[3, 0], [0, 1]])

class EigenRequest(BaseModel):
    matrix: List[List[float]] = Field(default=[[4, 2], [1, 3]])

class IterativeRequest(BaseModel):
    A: List[List[float]] = Field(default=[[4, 1], [2, 3]])
    b: List[float] = Field(default=[1, 2])
    x0: List[float] = Field(default=[0, 0])
    method: str = Field(default='jacobi', pattern='^(jacobi|gauss_seidel)$')
    max_iter: int = Field(default=50, ge=1)
    tol: float = Field(default=1e-6, gt=0)

class LuRequest(BaseModel):
    matrix: List[List[float]] = Field(default=[[2, 1, 1], [4, 3, 3], [8, 7, 9]])

class QrRequest(BaseModel):
    matrix: List[List[float]] = Field(default=[[1, 1], [1, 2], [1, 3]])

class VisualizeGridRequest(BaseModel):
    matrix: List[List[float]] = Field(default=[[2, 1], [1, 2]])
    grid_size: int = Field(default=10, ge=1, le=50)

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/transform")
def transform_matrix(data: TransformRequest):
    """Apply linear transformation to points"""
    try:
        matrix = np.array(data.matrix)
        points = np.array(data.points)
        transformed = np.dot(points, matrix.T)
        det = np.linalg.det(matrix)
        rank = np.linalg.matrix_rank(matrix)
        singular_values = np.linalg.svd(matrix, compute_uv=False)
        cond = np.linalg.cond(matrix)

        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/svd")
def svd_decomposition(data: SvdRequest):
    """Compute SVD decomposition with step-by-step visualization"""
    try:
        matrix = np.array(data.matrix)
        U, S, Vt = np.linalg.svd(matrix, full_matrices=True)
        m, n = matrix.shape
        Sigma = np.zeros((m, n))
        Sigma[:min(m, n), :min(m, n)] = np.diag(S)

        theta = np.linspace(0, 2 * np.pi, 100)
        unit_circle = np.array([np.cos(theta), np.sin(theta)])

        # Cas sans min() pour simplifier
        step1 = Vt @ unit_circle if n >= 2 else Vt @ unit_circle
        Sigma_block = Sigma[:min(m, n), :min(m, n)]
        step2 = Sigma_block @ step1 if m >= 2 and n >= 2 else Sigma @ step1
        step3 = U[:min(m, n), :min(m, n)] @ step2 if m >= 2 and n >= 2 else U @ step2

        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/eigen")
def eigen_decomposition(data: EigenRequest):
    """Compute eigenvalues and eigenvectors"""
    try:
        matrix = np.array(data.matrix)
        eigenvalues, eigenvectors = np.linalg.eig(matrix)
        idx = np.argsort(np.abs(eigenvalues))[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        eigen_list = []
        for ev in eigenvalues:
            if np.isreal(ev):
                value = float(np.real(ev))
                if value < 0:
                    stability = 'stable'
                elif value > 0:
                    stability = 'unstable'
                else:
                    stability = 'center'
            else:
                value = {'real': float(np.real(ev)), 'imag': float(np.imag(ev))}
                if np.real(ev) < 0:
                    stability = 'stable spiral'
                elif np.real(ev) > 0:
                    stability = 'unstable spiral'
                else:
                    stability = 'center'
            eigen_list.append({'value': value, 'stability': stability})

        unique, _ = np.unique(eigenvalues, return_counts=True)
        is_diagonalizable = len(unique) == matrix.shape[0]

        return {
            'matrix': matrix.tolist(),
            'eigenvalues': eigen_list,
            'eigenvectors': eigenvectors.tolist(),
            'is_diagonalizable': is_diagonalizable,
            'trace': float(np.trace(matrix)),
            'determinant': float(np.linalg.det(matrix))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/iterative")
def iterative_methods(data: IterativeRequest):
    """Jacobi and Gauss-Seidel iterative methods"""
    try:
        A = np.array(data.A)
        b = np.array(data.b)
        x = np.array(data.x0)
        n = len(b)
        history = [x.tolist()]
        residuals = []

        for iteration in range(data.max_iter):
            x_new = np.zeros(n)
            if data.method == 'jacobi':
                for i in range(n):
                    sigma = sum(A[i, j] * x[j] for j in range(n) if j != i)
                    x_new[i] = (b[i] - sigma) / A[i, i]
            elif data.method == 'gauss_seidel':
                x_new = x.copy()
                for i in range(n):
                    sigma = sum(A[i, j] * x_new[j] for j in range(i))
                    sigma += sum(A[i, j] * x[j] for j in range(i + 1, n))
                    x_new[i] = (b[i] - sigma) / A[i, i]

            residual = np.linalg.norm(A @ x_new - b)
            residuals.append(float(residual))
            history.append(x_new.tolist())

            if np.linalg.norm(x_new - x) < data.tol:
                return {
                    'method': data.method,
                    'solution': x_new.tolist(),
                    'iterations': iteration + 1,
                    'converged': True,
                    'history': history,
                    'residuals': residuals,
                    'final_residual': float(residual)
                }
            x = x_new

        return {
            'method': data.method,
            'solution': x.tolist(),
            'iterations': data.max_iter,
            'converged': False,
            'history': history,
            'residuals': residuals,
            'final_residual': float(residuals[-1]) if residuals else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/lu")
def lu_decomposition(data: LuRequest):
    """LU decomposition with partial pivoting"""
    try:
        matrix = np.array(data.matrix)
        P, L, U = linalg.lu(matrix)
        return {
            'matrix': matrix.tolist(),
            'P': P.tolist(),
            'L': L.tolist(),
            'U': U.tolist(),
            'verification': (P @ L @ U).tolist()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/qr")
def qr_decomposition(data: QrRequest):
    """QR decomposition using Gram-Schmidt"""
    try:
        matrix = np.array(data.matrix)
        Q, R = np.linalg.qr(matrix)
        return {
            'matrix': matrix.tolist(),
            'Q': Q.tolist(),
            'R': R.tolist(),
            'is_orthogonal': np.allclose(Q.T @ Q, np.eye(Q.shape[1])),
            'verification': (Q @ R).tolist()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/visualize-grid")
def visualize_grid(data: VisualizeGridRequest):
    """Generate grid for linear transformation visualization"""
    try:
        matrix = np.array(data.matrix)
        gs = data.grid_size
        x = np.linspace(-gs, gs, 21)
        y = np.linspace(-gs, gs, 21)

        h_lines_orig, h_lines_trans = [], []
        for yi in y:
            line = np.array([[x[0], yi], [x[-1], yi]])
            h_lines_orig.append(line.tolist())
            h_lines_trans.append(np.dot(line, matrix.T).tolist())

        v_lines_orig, v_lines_trans = [], []
        for xi in x:
            line = np.array([[xi, y[0]], [xi, y[-1]]])
            v_lines_orig.append(line.tolist())
            v_lines_trans.append(np.dot(line, matrix.T).tolist())

        unit_vectors = np.array([[1, 0], [0, 1]])
        transformed_vectors = np.dot(unit_vectors, matrix.T)

        return {
            'matrix': matrix.tolist(),
            'horizontal_lines_original': h_lines_orig,
            'horizontal_lines_transformed': h_lines_trans,
            'vertical_lines_original': v_lines_orig,
            'vertical_lines_transformed': v_lines_trans,
            'unit_vectors_original': unit_vectors.tolist(),
            'unit_vectors_transformed': transformed_vectors.tolist()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))