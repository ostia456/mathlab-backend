"""
Graph Theory API Routes - FastAPI
Théorie des Graphes - Parcours, plus courts chemins, arbres couvrants
"""
import heapq
import numpy as np
from collections import deque
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic
# ─────────────────────────────────────────────────────────────────────────────
class DijkstraRequest(BaseModel):
    adjacency_list: Dict[int, List[List[float]]] = Field(default_factory=dict)
    start: int = Field(default=0)
    end: Optional[int] = None

class BfsRequest(BaseModel):
    adjacency_list: Dict[int, List[List[float]]] = Field(default_factory=dict)
    start: int = Field(default=0)

class DfsRequest(BaseModel):
    adjacency_list: Dict[int, List[List[float]]] = Field(default_factory=dict)
    start: int = Field(default=0)

class MstRequest(BaseModel):
    method: str = Field(default='prim', pattern='^(prim|kruskal)$')
    num_nodes: int = Field(default=4, ge=2)
    adjacency_matrix: Optional[List[List[float]]] = None
    edges: Optional[List[List[float]]] = None

class GenerateGraphRequest(BaseModel):
    type: str = Field(default='random', pattern='^(random|complete|tree|bipartite)$')
    num_nodes: int = Field(default=5, ge=2, le=50)
    edge_probability: float = Field(default=0.3, ge=0, le=1)
    weighted: bool = Field(default=True)
    min_weight: int = Field(default=1, ge=1)
    max_weight: int = Field(default=10, ge=1)

# ─────────────────────────────────────────────────────────────────────────────
# Algorithmes (inchangés)
# ─────────────────────────────────────────────────────────────────────────────
def dijkstra_algorithm(adj_list, start, end=None):
    n = len(adj_list)
    distances = {i: float('inf') for i in range(n)}
    distances[start] = 0
    predecessors = {i: None for i in range(n)}
    visited = set()
    steps = []
    pq = [(0, start)]

    while pq:
        current_dist, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        step = {
            'current_node': u,
            'current_distance': current_dist,
            'visited': list(visited),
            'distances': {k: (-1 if v == float('inf') else v) for k, v in distances.items()},
            'queue': [x[1] for x in pq]
        }

        if end is not None and u == end:
            step['found'] = True
            steps.append(step)
            break

        for v, weight in adj_list.get(u, []):
            if v not in visited:
                new_dist = current_dist + weight
                if new_dist < distances[v]:
                    distances[v] = new_dist
                    predecessors[v] = u
                    heapq.heappush(pq, (new_dist, v))
        steps.append(step)

    path = []
    if end is not None and distances[end] < float('inf'):
        current = end
        while current is not None:
            path.append(current)
            current = predecessors[current]
        path.reverse()

    return distances, predecessors, path, steps

def bfs_algorithm(adj_list, start):
    n = len(adj_list)
    visited = [False] * n
    distances = [-1] * n
    predecessors = [None] * n
    queue = deque([start])
    visited[start] = True
    distances[start] = 0
    steps = []
    order = []

    while queue:
        u = queue.popleft()
        order.append(u)
        step = {
            'current': u,
            'queue': list(queue),
            'visited': [i for i, v in enumerate(visited) if v],
            'distances': distances.copy()
        }
        for v, _ in adj_list.get(u, []):
            if not visited[v]:
                visited[v] = True
                distances[v] = distances[u] + 1
                predecessors[v] = u
                queue.append(v)
        steps.append(step)

    return order, distances, predecessors, steps

def dfs_algorithm(adj_list, start):
    n = len(adj_list)
    visited = [False] * n
    predecessors = [None] * n
    order = []
    steps = []
    stack = [start]

    while stack:
        u = stack.pop()
        if visited[u]:
            continue
        visited[u] = True
        order.append(u)
        step = {'current': u, 'stack': list(stack), 'visited': [i for i, v in enumerate(visited) if v]}
        neighbors = adj_list.get(u, [])
        for v, _ in reversed(neighbors):
            if not visited[v]:
                predecessors[v] = u
                stack.append(v)
        steps.append(step)

    return order, predecessors, steps

def prim_algorithm(adj_matrix):
    n = len(adj_matrix)
    mst = []
    visited = [False] * n
    key = [float('inf')] * n
    parent = [None] * n
    key[0] = 0
    steps = []

    for _ in range(n):
        u = min((i for i in range(n) if not visited[i]), key=lambda i: key[i], default=None)
        if u is None:
            break
        visited[u] = True
        if parent[u] is not None:
            mst.append((parent[u], u, adj_matrix[parent[u]][u]))
        step = {'current': u, 'key': [(-1 if v == float('inf') else v) for v in key], 'parent': parent.copy(), 'mst': mst.copy()}
        steps.append(step)
        for v in range(n):
            if not visited[v] and adj_matrix[u][v] != float('inf') and adj_matrix[u][v] < key[v]:
                key[v] = adj_matrix[u][v]
                parent[v] = u

    return mst, steps

def kruskal_algorithm(edges, n):
    edges = sorted(edges, key=lambda x: x[2])
    parent = list(range(n))
    rank = [0] * n

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px == py:
            return False
        if rank[px] < rank[py]:
            px, py = py, px
        parent[py] = px
        if rank[px] == rank[py]:
            rank[px] += 1
        return True

    mst = []
    steps = []
    for u, v, w in edges:
        if union(u, v):
            mst.append((u, v, w))
            steps.append({'edge': (u, v, w), 'added': True, 'mst': mst.copy()})
        else:
            steps.append({'edge': (u, v, w), 'added': False, 'reason': 'Cycle detected'})
        if len(mst) == n - 1:
            break

    return mst, steps

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/algorithms")
def get_algorithms():
    return {
        'algorithms': [
            {'id': 'dijkstra', 'name': 'Dijkstra', 'type': 'shortest_path', 'description': 'Plus courts chemins depuis une source'},
            {'id': 'bfs', 'name': 'BFS', 'type': 'traversal', 'description': 'Parcours en largeur'},
            {'id': 'dfs', 'name': 'DFS', 'type': 'traversal', 'description': 'Parcours en profondeur'},
            {'id': 'prim', 'name': 'Prim', 'type': 'mst', 'description': 'Arbre couvrant minimal (Prim)'},
            {'id': 'kruskal', 'name': 'Kruskal', 'type': 'mst', 'description': 'Arbre couvrant minimal (Kruskal)'},
        ]
    }

@router.post("/dijkstra")
def dijkstra(data: DijkstraRequest):
    adj_list = {int(k): [[int(v), w] for v, w in neighbors] for k, neighbors in data.adjacency_list.items()}
    start = data.start
    end = data.end

    distances, predecessors, path, steps = dijkstra_algorithm(adj_list, start, end)
    safe_distances = {int(k): (-1 if v == float('inf') else v) for k, v in distances.items()}

    return {
        'distances': safe_distances,
        'predecessors': {int(k): v for k, v in predecessors.items()},
        'path': path,
        'steps': steps,
    }

@router.post("/bfs")
def bfs(data: BfsRequest):
    adj_list = {int(k): [[int(v), w] for v, w in neighbors] for k, neighbors in data.adjacency_list.items()}
    start = data.start

    order, distances, predecessors, steps = bfs_algorithm(adj_list, start)
    return {'traversal_order': order, 'distances': distances, 'predecessors': predecessors, 'steps': steps}

@router.post("/dfs")
def dfs(data: DfsRequest):
    adj_list = {int(k): [[int(v), w] for v, w in neighbors] for k, neighbors in data.adjacency_list.items()}
    start = data.start

    order, predecessors, steps = dfs_algorithm(adj_list, start)
    return {'traversal_order': order, 'predecessors': predecessors, 'steps': steps}

@router.post("/mst")
def minimum_spanning_tree(data: MstRequest):
    if data.method == 'prim':
        adj_matrix = data.adjacency_matrix or [
            [0, 4, float('inf'), float('inf')],
            [4, 0, 2, 1],
            [float('inf'), 2, 0, 5],
            [float('inf'), 1, 5, 0]
        ]
        mst, steps = prim_algorithm(adj_matrix)
    else:
        edges = data.edges or [[0, 1, 4], [1, 2, 2], [1, 3, 1], [2, 3, 5]]
        mst, steps = kruskal_algorithm(edges, data.num_nodes)

    total_weight = sum(w for _, _, w in mst)
    return {'method': data.method, 'mst': mst, 'total_weight': total_weight, 'steps': steps}

@router.post("/generate")
def generate_graph(data: GenerateGraphRequest):
    n = data.num_nodes
    nodes = list(range(n))
    edges = []
    adj_list = {i: [] for i in range(n)}

    if data.type == 'complete':
        for i in range(n):
            for j in range(i + 1, n):
                weight = int(np.random.randint(data.min_weight, data.max_weight + 1)) if data.weighted else 1
                edges.append([i, j, weight])
                adj_list[i].append([j, weight])
                adj_list[j].append([i, weight])
    elif data.type == 'tree':
        for i in range(1, n):
            parent = int(np.random.randint(0, i))
            weight = int(np.random.randint(data.min_weight, data.max_weight + 1)) if data.weighted else 1
            edges.append([parent, i, weight])
            adj_list[parent].append([i, weight])
            adj_list[i].append([parent, weight])
    elif data.type == 'bipartite':
        n1 = n // 2
        n2 = n - n1
        for i in range(n1):
            for j in range(n2):
                if np.random.random() < data.edge_probability:
                    weight = int(np.random.randint(data.min_weight, data.max_weight + 1)) if data.weighted else 1
                    edges.append([i, n1 + j, weight])
                    adj_list[i].append([n1 + j, weight])
                    adj_list[n1 + j].append([i, weight])
    else:
        for i in range(n):
            for j in range(i + 1, n):
                if np.random.random() < data.edge_probability:
                    weight = int(np.random.randint(data.min_weight, data.max_weight + 1)) if data.weighted else 1
                    edges.append([i, j, weight])
                    adj_list[i].append([j, weight])
                    adj_list[j].append([i, weight])

    return {'type': data.type, 'num_nodes': n, 'nodes': nodes, 'edges': edges, 'adjacency_list': adj_list}