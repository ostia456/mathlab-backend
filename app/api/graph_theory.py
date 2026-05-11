"""
Graph Theory API Routes
Théorie des Graphes - Parcours, plus courts chemins, arbres couvrants
"""
from flask import Blueprint, request, jsonify
import numpy as np
import heapq
from collections import deque, defaultdict

gt_bp = Blueprint('graph_theory', __name__)


def adjacency_list_to_matrix(adj_list, n):
    """Convert adjacency list to adjacency matrix"""
    matrix = np.full((n, n), np.inf)
    np.fill_diagonal(matrix, 0)
    for u, neighbors in adj_list.items():
        for v, weight in neighbors:
            matrix[u][v] = weight
    return matrix


def dijkstra_algorithm(adj_list, start, end=None):
    """Dijkstra's algorithm with step-by-step tracking"""
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
            # FIX : remplace inf par -1 dans les steps aussi
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

    # Reconstruct path
    path = []
    if end is not None and distances[end] < float('inf'):
        current = end
        while current is not None:
            path.append(current)
            current = predecessors[current]
        path.reverse()

    return distances, predecessors, path, steps


def bfs_algorithm(adj_list, start):
    """Breadth-First Search with step tracking"""
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
    """Depth-First Search with step tracking"""
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

        step = {
            'current': u,
            'stack': list(stack),
            'visited': [i for i, v in enumerate(visited) if v]
        }

        neighbors = adj_list.get(u, [])
        for v, _ in reversed(neighbors):
            if not visited[v]:
                predecessors[v] = u
                stack.append(v)

        steps.append(step)

    return order, predecessors, steps


def prim_algorithm(adj_matrix):
    """Prim's algorithm for Minimum Spanning Tree"""
    n = len(adj_matrix)
    mst = []
    visited = [False] * n
    key = [float('inf')] * n
    parent = [None] * n

    key[0] = 0
    steps = []

    for _ in range(n):
        u = min((i for i in range(n) if not visited[i]),
                key=lambda i: key[i], default=None)

        if u is None:
            break

        visited[u] = True

        if parent[u] is not None:
            mst.append((parent[u], u, adj_matrix[parent[u]][u]))

        step = {
            'current': u,
            'key': [(-1 if v == float('inf') else v) for v in key],
            'parent': parent.copy(),
            'mst': mst.copy()
        }
        steps.append(step)

        for v in range(n):
            if (not visited[v] and adj_matrix[u][v] != float('inf')
                    and adj_matrix[u][v] < key[v]):
                key[v] = adj_matrix[u][v]
                parent[v] = u

    return mst, steps


def kruskal_algorithm(edges, n):
    """Kruskal's algorithm for Minimum Spanning Tree"""
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
            step = {'edge': (u, v, w), 'added': True, 'mst': mst.copy()}
        else:
            step = {'edge': (u, v, w), 'added': False, 'reason': 'Cycle detected'}
        steps.append(step)

        if len(mst) == n - 1:
            break

    return mst, steps


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@gt_bp.route('/algorithms', methods=['GET'])
def get_algorithms():
    return jsonify({
        'algorithms': [
            {'id': 'dijkstra', 'name': 'Dijkstra', 'type': 'shortest_path',
             'description': 'Plus courts chemins depuis une source'},
            {'id': 'bfs', 'name': 'BFS', 'type': 'traversal',
             'description': 'Parcours en largeur'},
            {'id': 'dfs', 'name': 'DFS', 'type': 'traversal',
             'description': 'Parcours en profondeur'},
            {'id': 'prim', 'name': 'Prim', 'type': 'mst',
             'description': 'Arbre couvrant minimal (Prim)'},
            {'id': 'kruskal', 'name': 'Kruskal', 'type': 'mst',
             'description': 'Arbre couvrant minimal (Kruskal)'},
        ]
    })


@gt_bp.route('/dijkstra', methods=['POST'])
def dijkstra():
    """Run Dijkstra algorithm"""
    data = request.get_json()

    adj_list = data.get('adjacency_list', {})
    # FIX : convertit les clés string en int et les voisins en int
    adj_list = {int(k): [[int(v), w] for v, w in neighbors]
                for k, neighbors in adj_list.items()}

    start = int(data.get('start', 0))
    end   = data.get('end')
    if end is not None:
        end = int(end)

    distances, predecessors, path, steps = dijkstra_algorithm(adj_list, start, end)

    # FIX : inf → -1 car JSON ne supporte pas Infinity
    # FIX : clés en int pour matcher result.distances[endNode] côté frontend
    safe_distances = {
        int(k): (-1 if v == float('inf') else v)
        for k, v in distances.items()
    }

    return jsonify({
        'distances':    safe_distances,
        'predecessors': {int(k): v for k, v in predecessors.items()},
        'path':         path,
        'steps':        steps,
    })


@gt_bp.route('/bfs', methods=['POST'])
def bfs():
    """Run BFS algorithm"""
    data = request.get_json()

    adj_list = data.get('adjacency_list', {})
    adj_list = {int(k): [[int(v), w] for v, w in neighbors]
                for k, neighbors in adj_list.items()}

    start = int(data.get('start', 0))

    order, distances, predecessors, steps = bfs_algorithm(adj_list, start)

    return jsonify({
        'traversal_order': order,
        'distances':       distances,
        'predecessors':    predecessors,
        'steps':           steps,
    })


@gt_bp.route('/dfs', methods=['POST'])
def dfs():
    """Run DFS algorithm"""
    data = request.get_json()

    adj_list = data.get('adjacency_list', {})
    adj_list = {int(k): [[int(v), w] for v, w in neighbors]
                for k, neighbors in adj_list.items()}

    start = int(data.get('start', 0))

    order, predecessors, steps = dfs_algorithm(adj_list, start)

    return jsonify({
        'traversal_order': order,
        'predecessors':    predecessors,
        'steps':           steps,
    })


@gt_bp.route('/mst', methods=['POST'])
def minimum_spanning_tree():
    """Compute Minimum Spanning Tree using Prim or Kruskal"""
    data = request.get_json()

    method = data.get('method', 'prim')
    n      = data.get('num_nodes', 4)

    if method == 'prim':
        adj_matrix = data.get('adjacency_matrix', [
            [0, 4, float('inf'), float('inf')],
            [4, 0, 2, 1],
            [float('inf'), 2, 0, 5],
            [float('inf'), 1, 5, 0]
        ])
        mst, steps = prim_algorithm(adj_matrix)
    else:
        edges = data.get('edges', [[0, 1, 4], [1, 2, 2], [1, 3, 1], [2, 3, 5]])
        mst, steps = kruskal_algorithm(edges, n)

    total_weight = sum(w for _, _, w in mst)

    return jsonify({
        'method':       method,
        'mst':          mst,
        'total_weight': total_weight,
        'steps':        steps,
    })


@gt_bp.route('/generate', methods=['POST'])
def generate_graph():
    """Generate random graphs"""
    data = request.get_json()

    graph_type = data.get('type', 'random')
    n          = data.get('num_nodes', 5)
    edge_prob  = data.get('edge_probability', 0.3)
    weighted   = data.get('weighted', True)
    min_weight = data.get('min_weight', 1)
    max_weight = data.get('max_weight', 10)

    nodes    = list(range(n))
    edges    = []
    adj_list = {i: [] for i in range(n)}

    if graph_type == 'complete':
        for i in range(n):
            for j in range(i + 1, n):
                weight = int(np.random.randint(min_weight, max_weight + 1)) if weighted else 1
                edges.append([i, j, weight])
                adj_list[i].append([j, weight])
                adj_list[j].append([i, weight])

    elif graph_type == 'tree':
        for i in range(1, n):
            parent = int(np.random.randint(0, i))
            weight = int(np.random.randint(min_weight, max_weight + 1)) if weighted else 1
            edges.append([parent, i, weight])
            adj_list[parent].append([i, weight])
            adj_list[i].append([parent, weight])

    elif graph_type == 'bipartite':
        n1 = n // 2
        n2 = n - n1
        for i in range(n1):
            for j in range(n2):
                if np.random.random() < edge_prob:
                    weight = int(np.random.randint(min_weight, max_weight + 1)) if weighted else 1
                    edges.append([i, n1 + j, weight])
                    adj_list[i].append([n1 + j, weight])
                    adj_list[n1 + j].append([i, weight])

    else:  # random
        for i in range(n):
            for j in range(i + 1, n):
                if np.random.random() < edge_prob:
                    weight = int(np.random.randint(min_weight, max_weight + 1)) if weighted else 1
                    edges.append([i, j, weight])
                    adj_list[i].append([j, weight])
                    adj_list[j].append([i, weight])

    return jsonify({
        'type':           graph_type,
        'num_nodes':      n,
        'nodes':          nodes,
        'edges':          edges,
        'adjacency_list': adj_list,   # objet avec clés int → frontend normalise déjà
    })
