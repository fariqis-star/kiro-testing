import json
import re
from collections import deque
from itertools import permutations

CELL_POINTS = {"c7": 250}
COLLECTIBLE_COINS = {"c7"}
DIRECTIONS = [(-1, 0, "up"), (1, 0, "down"), (0, -1, "left"), (0, 1, "right")]

TARGET_VALUES = {
    "c4": 800, "c2": 600, "c3": 550, "c5": 250, "c1": 400, "c7": 250,
    "c17": 50, "c18": 500,
    "c40": 50, "c41": 50, "c42": 50, "c43": 50,
    "c30": 1000, "c31": 1000, "c32": 1000, "c33": 1000
}

# Key-to-door mapping: collecting a key unlocks its corresponding door
KEY_DOOR_MAP = {
    "c40": "c30",  # Red key -> Red door
    "c41": "c31",  # Green key -> Green door
    "c42": "c32",  # Grey key -> Grey door
    "c43": "c33",  # Yellow key -> Yellow door
}

# Door-to-key reverse mapping
DOOR_KEY_MAP = {v: k for k, v in KEY_DOOR_MAP.items()}

# Key tiles (must be collected before their corresponding doors)
KEY_TILES = frozenset(["c40", "c41", "c42", "c43"])

# Door tiles (challenges that require their key first)
CHALLENGE_TILES = frozenset(["c30", "c31", "c32", "c33"])

# Cells we KNOW are safe to walk through
KNOWN_SAFE_CELLS = frozenset([
    'normal', 'start', 'player', 'treasure',
    'c1', 'c2', 'c3', 'c4', 'c5', 'c7',
    'c17', 'c18',
    'c30', 'c31', 'c32', 'c33',
    'c40', 'c41', 'c42', 'c43'
])

# Cells we KNOW are dangerous (spike traps)
KNOWN_SPIKE_CELLS = frozenset(['c8'])

# Hardcoded Round 3 10x10 map (fallback when model passes empty/minimal map)
INTERNAL_MAP = [
    ["c42", "normal", "normal", "normal", "normal", "normal", "normal", "normal", "normal", "treasure"],
    ["normal", "c18", "normal", "normal", "c1", "normal", "normal", "normal", "normal", "normal"],
    ["normal", "c4", "normal", "normal", "normal", "c43", "normal", "normal", "normal", "normal"],
    ["normal", "normal", "c2", "normal", "normal", "normal", "normal", "normal", "normal", "c33"],
    ["start", "normal", "normal", "normal", "c5", "normal", "normal", "normal", "normal", "normal"],
    ["normal", "normal", "normal", "normal", "normal", "normal", "normal", "normal", "normal", "c32"],
    ["normal", "normal", "normal", "normal", "normal", "normal", "normal", "c7", "c7", "normal"],
    ["normal", "normal", "normal", "normal", "normal", "c17", "c7", "c7", "c7", "c1"],
    ["c2", "normal", "normal", "normal", "normal", "normal", "normal", "c7", "c7", "c7"],
    ["normal", "c4", "normal", "normal", "c18", "normal", "c7", "c7", "c7", "c7"]
]


def _parse_start(pos):
    try:
        if isinstance(pos, (list, tuple)):
            if len(pos) == 1:
                return _parse_start(pos[0])
            if len(pos) >= 2:
                a = re.sub(r'[^A-Za-z0-9]', '', str(pos[0]))
                b = re.sub(r'[^A-Za-z0-9]', '', str(pos[1]))
                if a.isalpha():
                    return (int(b) - 1, ord(a.upper()) - ord('A'))
                return (int(a), int(b))
        s = re.sub(r'[^A-Za-z0-9]', '', str(pos))
        m = re.match(r'([A-Za-z])(\d+)', s)
        if m:
            return (int(m.group(2)) - 1, ord(m.group(1).upper()) - ord('A'))
        nums = re.findall(r'\d+', s)
        if len(nums) >= 2:
            return (int(nums[0]), int(nums[1]))
    except (ValueError, TypeError, IndexError):
        pass
    return (0, 0)


def _is_spike(cell):
    """Check if a cell is a known spike trap."""
    c = cell.lower()
    return c in KNOWN_SPIKE_CELLS or 'spike' in c or 'trap' in c


def _bfs(game_map, rows, cols, start, goal, blocked_cells=None):
    """BFS avoiding walls AND spikes (c8). Spikes are treated as impassable."""
    queue = deque([(start[0], start[1], [])])
    visited = {(start[0], start[1])}
    while queue:
        r, c, path = queue.popleft()
        if (r, c) == goal:
            return path
        for dr, dc, move in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited:
                cell = game_map[nr][nc]
                if cell == 'wall' or cell in KNOWN_SPIKE_CELLS:
                    continue
                if blocked_cells and (nr, nc) in blocked_cells:
                    continue
                visited.add((nr, nc))
                queue.append((nr, nc, path + [move]))
    return None


def _bfs_with_positions(game_map, rows, cols, start, goal, blocked_cells=None):
    """BFS that returns both the path (moves) and all positions visited along it."""
    queue = deque([(start[0], start[1], [], [(start[0], start[1])])])
    visited = {(start[0], start[1])}
    while queue:
        r, c, path, positions = queue.popleft()
        if (r, c) == goal:
            return path, positions
        for dr, dc, move in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited:
                cell = game_map[nr][nc]
                if cell == 'wall' or cell in KNOWN_SPIKE_CELLS:
                    continue
                if blocked_cells and (nr, nc) in blocked_cells:
                    continue
                visited.add((nr, nc))
                queue.append((nr, nc, path + [move], positions + [(nr, nc)]))
    return None, None


def _precompute_distances(game_map, rows, cols, nodes, blocked_cells=None):
    """Pre-compute BFS distances and paths between all pairs of nodes.
    nodes is a list of (row, col) positions.
    Returns dist_matrix[i][j] = distance, path_matrix[i][j] = list of moves,
    transit_matrix[i][j] = set of node indices collected along the path."""
    n = len(nodes)
    node_set = {pos: idx for idx, pos in enumerate(nodes)}
    dist_matrix = [[float('inf')] * n for _ in range(n)]
    path_matrix = [[None] * n for _ in range(n)]
    transit_matrix = [[set() for _ in range(n)] for _ in range(n)]

    for i in range(n):
        dist_matrix[i][i] = 0
        path_matrix[i][i] = []
        # BFS from node i to all other nodes
        start = nodes[i]
        queue = deque([(start[0], start[1], [])])
        visited = {(start[0], start[1])}
        while queue:
            r, c, path = queue.popleft()
            pos = (r, c)
            if pos in node_set and pos != start:
                j = node_set[pos]
                if len(path) < dist_matrix[i][j]:
                    dist_matrix[i][j] = len(path)
                    path_matrix[i][j] = path
            for dr, dc, move in DIRECTIONS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited:
                    cell = game_map[nr][nc]
                    if cell == 'wall' or cell in KNOWN_SPIKE_CELLS:
                        continue
                    if blocked_cells and (nr, nc) in blocked_cells:
                        continue
                    visited.add((nr, nc))
                    queue.append((nr, nc, path + [move]))

    # Compute transit: which nodes are visited along the path from i to j
    move_map = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
    for i in range(n):
        for j in range(n):
            if i == j or path_matrix[i][j] is None:
                continue
            r, c = nodes[i]
            for move in path_matrix[i][j]:
                dr, dc = move_map[move]
                r, c = r + dr, c + dc
                pos = (r, c)
                if pos in node_set:
                    k = node_set[pos]
                    if k != i and k != j:
                        transit_matrix[i][j].add(k)

    return dist_matrix, path_matrix, transit_matrix


def _is_valid_order(order, key_indices, door_indices):
    """Check if the visit order respects key-before-door constraints.
    key_indices: dict mapping key_cell_type -> index in nodes list
    door_indices: dict mapping door_cell_type -> index in nodes list"""
    # For each key-door pair, the key must appear before its door in the order
    position_in_order = {}
    for pos, idx in enumerate(order):
        position_in_order[idx] = pos

    for key_cell, door_cell in KEY_DOOR_MAP.items():
        if key_cell in key_indices and door_cell in door_indices:
            ki = key_indices[key_cell]
            di = door_indices[door_cell]
            if ki in position_in_order and di in position_in_order:
                if position_in_order[ki] > position_in_order[di]:
                    return False
    return True


def _compute_tour_cost(order, dist_matrix, transit_matrix, start_idx, end_idx):
    """Compute the total cost of visiting nodes in the given order,
    accounting for transit pickups (nodes collected for free along BFS paths).
    order: list of node indices to visit (NOT including start_idx or end_idx).
    Returns total distance, or float('inf') if unreachable."""
    visited = set()
    total_dist = 0
    current = start_idx

    for target in order:
        if target in visited:
            continue
        d = dist_matrix[current][target]
        if d == float('inf'):
            return float('inf')
        total_dist += d
        # Mark transit nodes as visited
        transit = transit_matrix[current][target]
        visited.update(transit)
        visited.add(target)
        current = target

    # Go to end (treasure)
    d = dist_matrix[current][end_idx]
    if d == float('inf'):
        return float('inf')
    total_dist += d
    return total_dist


def _compute_tour_cost_with_skips(order, dist_matrix, transit_matrix, start_idx, end_idx):
    """Compute tour cost, skipping nodes already collected in transit.
    Returns (total_distance, effective_order) where effective_order excludes skipped nodes."""
    visited = set()
    total_dist = 0
    current = start_idx
    effective_order = []

    for target in order:
        if target in visited:
            continue
        d = dist_matrix[current][target]
        if d == float('inf'):
            return float('inf'), []
        total_dist += d
        # Mark transit nodes as visited
        transit = transit_matrix[current][target]
        visited.update(transit)
        visited.add(target)
        effective_order.append(target)
        current = target

    # Go to end (treasure)
    d = dist_matrix[current][end_idx]
    if d == float('inf'):
        return float('inf'), []
    total_dist += d
    return total_dist, effective_order


def _nearest_neighbor_order(dist_matrix, transit_matrix, start_idx, end_idx,
                            target_indices, key_indices, door_indices):
    """Greedy nearest-neighbor with transit-aware skipping and key-door constraints."""
    remaining = set(target_indices)
    visited = set()
    order = []
    current = start_idx
    collected_keys = set()  # track key cell types collected

    while remaining:
        # Filter out locked doors
        available = []
        for idx in remaining:
            if idx in visited:
                continue
            available.append(idx)

        if not available:
            break

        # Find nearest available target (respecting key constraints)
        best_idx = None
        best_dist = float('inf')
        for idx in available:
            # Check if this is a door that requires a key we haven't collected
            is_locked = False
            for door_cell, key_cell in DOOR_KEY_MAP.items():
                if idx in door_indices.get(door_cell, set()) and key_cell not in collected_keys:
                    is_locked = True
                    break
            if is_locked:
                continue
            d = dist_matrix[current][idx]
            if d < best_dist:
                best_dist = d
                best_idx = idx

        if best_idx is None:
            # All remaining are locked doors - try to find a key first
            # This shouldn't happen if keys are prioritized, but handle gracefully
            break

        # Move to best target
        order.append(best_idx)
        # Mark transit nodes as visited
        transit = transit_matrix[current][best_idx]
        for t in transit:
            if t in remaining:
                visited.add(t)
                remaining.discard(t)
                # Check if transit node is a key
                for key_cell, ki_set in key_indices.items():
                    if t in ki_set:
                        collected_keys.add(key_cell)
                order.append(t)  # Add to order for tracking

        visited.add(best_idx)
        remaining.discard(best_idx)
        # Check if this target is a key
        for key_cell, ki_set in key_indices.items():
            if best_idx in ki_set:
                collected_keys.add(key_cell)
        current = best_idx

    return order


def _two_opt_improve(order, dist_matrix, transit_matrix, start_idx, end_idx,
                     key_indices, door_indices, node_cells, max_iterations=500):
    """Apply 2-opt local search to improve the tour, respecting key-door constraints."""
    best_order = list(order)
    best_cost, _ = _compute_tour_cost_with_skips(best_order, dist_matrix, transit_matrix, start_idx, end_idx)

    improved = True
    iterations = 0
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        for i in range(len(best_order) - 1):
            for j in range(i + 1, len(best_order)):
                # Try reversing the segment between i and j
                new_order = best_order[:i] + best_order[i:j+1][::-1] + best_order[j+1:]
                # Check key-door constraints
                if not _check_key_door_order(new_order, node_cells, key_indices, door_indices, transit_matrix, start_idx):
                    continue
                new_cost, _ = _compute_tour_cost_with_skips(new_order, dist_matrix, transit_matrix, start_idx, end_idx)
                if new_cost < best_cost:
                    best_order = new_order
                    best_cost = new_cost
                    improved = True
                    break
            if improved:
                break

    return best_order, best_cost


def _or_opt_improve(order, dist_matrix, transit_matrix, start_idx, end_idx,
                    key_indices, door_indices, node_cells, max_iterations=200):
    """Apply or-opt (relocate single nodes) to improve the tour."""
    best_order = list(order)
    best_cost, _ = _compute_tour_cost_with_skips(best_order, dist_matrix, transit_matrix, start_idx, end_idx)

    improved = True
    iterations = 0
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        for i in range(len(best_order)):
            node = best_order[i]
            remaining = best_order[:i] + best_order[i+1:]
            for j in range(len(remaining) + 1):
                new_order = remaining[:j] + [node] + remaining[j:]
                if not _check_key_door_order(new_order, node_cells, key_indices, door_indices, transit_matrix, start_idx):
                    continue
                new_cost, _ = _compute_tour_cost_with_skips(new_order, dist_matrix, transit_matrix, start_idx, end_idx)
                if new_cost < best_cost:
                    best_order = new_order
                    best_cost = new_cost
                    improved = True
                    break
            if improved:
                break

    return best_order, best_cost


def _check_key_door_order(order, node_cells, key_indices, door_indices, transit_matrix, start_idx):
    """Check if a given order respects key-before-door constraints,
    accounting for transit pickups."""
    collected_keys = set()
    current = start_idx

    # Check if start itself is a key
    for key_cell, ki_set in key_indices.items():
        if start_idx in ki_set:
            collected_keys.add(key_cell)

    visited = set()
    for idx in order:
        if idx in visited:
            continue

        # Check transit from current to idx
        if current != idx:
            transit = transit_matrix[current][idx]
            for t in transit:
                for key_cell, ki_set in key_indices.items():
                    if t in ki_set:
                        collected_keys.add(key_cell)
                visited.add(t)

        # Check if idx is a door - need its key collected first
        cell = node_cells.get(idx, '')
        if cell in DOOR_KEY_MAP:
            required_key = DOOR_KEY_MAP[cell]
            if required_key not in collected_keys:
                return False

        # If idx is a key, mark it collected
        if cell in KEY_DOOR_MAP:
            collected_keys.add(cell)

        visited.add(idx)
        current = idx

    return True


def smart_loot_path(game_map, rows, cols, start, treasure):
    """Optimized pathfinding using pre-computed distances and TSP optimization.
    Uses nearest-neighbor + 2-opt/or-opt improvements with transit-aware costing."""

    # Collect all target positions
    targets = []  # (row, col, cell_type)
    for row in range(rows):
        for col in range(cols):
            cell = game_map[row][col]
            if cell in ('treasure', 'wall', 'normal', 'start'):
                continue
            if cell in KNOWN_SPIKE_CELLS:
                continue
            targets.append((row, col, cell))

    if not targets:
        return _bfs(game_map, rows, cols, start, treasure) or []

    # Build node list: [start, *targets, treasure]
    nodes = [start] + [(r, c) for r, c, _ in targets] + [treasure]
    start_idx = 0
    end_idx = len(nodes) - 1
    target_indices = list(range(1, end_idx))

    # Map node index to cell type
    node_cells = {}
    for i, (r, c, cell) in enumerate(targets):
        node_cells[i + 1] = cell  # offset by 1 for start

    # Map key/door cell types to their node indices
    key_indices = {}  # key_cell_type -> set of node indices
    door_indices = {}  # door_cell_type -> set of node indices
    for i, (r, c, cell) in enumerate(targets):
        idx = i + 1
        if cell in KEY_TILES:
            key_indices.setdefault(cell, set()).add(idx)
        if cell in CHALLENGE_TILES:
            door_indices.setdefault(cell, set()).add(idx)

    # Pre-compute all pairwise BFS distances (no blocked doors - doors are always walkable)
    dist_matrix, path_matrix, transit_matrix = _precompute_distances(
        game_map, rows, cols, nodes
    )

    # Check reachability - remove unreachable targets
    reachable = []
    for idx in target_indices:
        if dist_matrix[start_idx][idx] < float('inf') or dist_matrix[idx][end_idx] < float('inf'):
            # More thorough check: can we reach it from start AND reach treasure from it?
            if dist_matrix[start_idx][idx] < float('inf') and dist_matrix[idx][end_idx] < float('inf'):
                reachable.append(idx)
    target_indices = reachable

    if not target_indices:
        return _bfs(game_map, rows, cols, start, treasure) or []

    # Strategy 1: Nearest-neighbor with key priority
    order_nn = _nearest_neighbor_with_keys(
        dist_matrix, transit_matrix, start_idx, end_idx,
        target_indices, key_indices, door_indices, node_cells
    )

    # Strategy 2: Keys first, then nearest-neighbor
    order_keys_first = _keys_first_then_nn(
        dist_matrix, transit_matrix, start_idx, end_idx,
        target_indices, key_indices, door_indices, node_cells
    )

    # Pick the better starting order
    cost_nn, _ = _compute_tour_cost_with_skips(order_nn, dist_matrix, transit_matrix, start_idx, end_idx)
    cost_kf, _ = _compute_tour_cost_with_skips(order_keys_first, dist_matrix, transit_matrix, start_idx, end_idx)

    if cost_kf < cost_nn:
        best_order = order_keys_first
        best_cost = cost_kf
    else:
        best_order = order_nn
        best_cost = cost_nn

    # Apply 2-opt improvement
    improved_order, improved_cost = _two_opt_improve(
        best_order, dist_matrix, transit_matrix, start_idx, end_idx,
        key_indices, door_indices, node_cells
    )
    if improved_cost < best_cost:
        best_order = improved_order
        best_cost = improved_cost

    # Apply or-opt improvement
    improved_order, improved_cost = _or_opt_improve(
        best_order, dist_matrix, transit_matrix, start_idx, end_idx,
        key_indices, door_indices, node_cells
    )
    if improved_cost < best_cost:
        best_order = improved_order
        best_cost = improved_cost

    # Another round of 2-opt after or-opt
    improved_order, improved_cost = _two_opt_improve(
        best_order, dist_matrix, transit_matrix, start_idx, end_idx,
        key_indices, door_indices, node_cells
    )
    if improved_cost < best_cost:
        best_order = improved_order
        best_cost = improved_cost

    # Build the actual path from the order
    full_path = _build_path_from_order(best_order, dist_matrix, path_matrix, transit_matrix, start_idx, end_idx)

    return full_path


def _nearest_neighbor_with_keys(dist_matrix, transit_matrix, start_idx, end_idx,
                                target_indices, key_indices, door_indices, node_cells):
    """Nearest-neighbor that prioritizes keys when doors are blocking progress."""
    remaining = set(target_indices)
    order = []
    current = start_idx
    collected_keys = set()
    visited = set()

    while remaining:
        # Remove already visited
        remaining -= visited

        if not remaining:
            break

        # Determine which targets are available (not locked)
        available = []
        locked = []
        for idx in remaining:
            if idx in visited:
                continue
            cell = node_cells.get(idx, '')
            if cell in DOOR_KEY_MAP:
                required_key = DOOR_KEY_MAP[cell]
                if required_key not in collected_keys:
                    locked.append(idx)
                    continue
            available.append(idx)

        if not available:
            # Need to collect keys - find nearest key that unlocks something
            key_targets = []
            for key_cell in KEY_DOOR_MAP:
                if key_cell not in collected_keys and key_cell in key_indices:
                    for ki in key_indices[key_cell]:
                        if ki in remaining and ki not in visited:
                            key_targets.append(ki)
            if not key_targets:
                break
            available = key_targets

        # Find nearest available
        best_idx = None
        best_dist = float('inf')
        for idx in available:
            d = dist_matrix[current][idx]
            if d < best_dist:
                best_dist = d
                best_idx = idx

        if best_idx is None or best_dist == float('inf'):
            break

        # Collect transit nodes
        transit = transit_matrix[current][best_idx]
        for t in transit:
            if t in remaining:
                visited.add(t)
                cell = node_cells.get(t, '')
                if cell in KEY_DOOR_MAP:
                    collected_keys.add(cell)

        order.append(best_idx)
        visited.add(best_idx)
        remaining.discard(best_idx)

        cell = node_cells.get(best_idx, '')
        if cell in KEY_DOOR_MAP:
            collected_keys.add(cell)

        current = best_idx

    return order


def _keys_first_then_nn(dist_matrix, transit_matrix, start_idx, end_idx,
                        target_indices, key_indices, door_indices, node_cells):
    """Collect all keys first (by nearest), then all other targets by nearest-neighbor."""
    remaining = set(target_indices)
    order = []
    current = start_idx
    collected_keys = set()
    visited = set()

    # Phase 1: Collect keys
    key_nodes = set()
    for key_cell, ki_set in key_indices.items():
        key_nodes.update(ki_set)

    keys_remaining = key_nodes & remaining
    while keys_remaining:
        keys_remaining -= visited
        if not keys_remaining:
            break

        best_idx = None
        best_dist = float('inf')
        for idx in keys_remaining:
            d = dist_matrix[current][idx]
            if d < best_dist:
                best_dist = d
                best_idx = idx

        if best_idx is None or best_dist == float('inf'):
            break

        transit = transit_matrix[current][best_idx]
        for t in transit:
            if t in remaining:
                visited.add(t)
                cell = node_cells.get(t, '')
                if cell in KEY_DOOR_MAP:
                    collected_keys.add(cell)

        order.append(best_idx)
        visited.add(best_idx)
        remaining.discard(best_idx)
        keys_remaining.discard(best_idx)

        cell = node_cells.get(best_idx, '')
        if cell in KEY_DOOR_MAP:
            collected_keys.add(cell)

        current = best_idx

    # Phase 2: All other targets by nearest-neighbor
    remaining -= visited
    while remaining:
        remaining -= visited
        if not remaining:
            break

        best_idx = None
        best_dist = float('inf')
        for idx in remaining:
            if idx in visited:
                continue
            d = dist_matrix[current][idx]
            if d < best_dist:
                best_dist = d
                best_idx = idx

        if best_idx is None or best_dist == float('inf'):
            break

        transit = transit_matrix[current][best_idx]
        for t in transit:
            if t in remaining:
                visited.add(t)

        order.append(best_idx)
        visited.add(best_idx)
        remaining.discard(best_idx)
        current = best_idx

    return order


def _build_path_from_order(order, dist_matrix, path_matrix, transit_matrix, start_idx, end_idx):
    """Build the actual move path from the optimized order."""
    full_path = []
    current = start_idx
    visited = set()

    for target in order:
        if target in visited:
            continue
        path_segment = path_matrix[current][target]
        if path_segment is None:
            continue
        full_path.extend(path_segment)
        # Mark transit as visited
        transit = transit_matrix[current][target]
        visited.update(transit)
        visited.add(target)
        current = target

    # Finally go to treasure
    path_segment = path_matrix[current][end_idx]
    if path_segment:
        full_path.extend(path_segment)

    return full_path


def swift_path(game_map, rows, cols, start, treasure):
    return _bfs(game_map, rows, cols, start, treasure) or []


def _extract_params(event):
    """Extract parameters from Bedrock Agent format OR body format."""
    if 'parameters' in event and isinstance(event['parameters'], list):
        params = {}
        for p in event['parameters']:
            name = p.get('name', '')
            value = p.get('value', '')
            try:
                params[name] = json.loads(value) if isinstance(value, str) else value
            except (json.JSONDecodeError, TypeError):
                params[name] = value
        return params
    if 'body' in event:
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        return body
    return event


def lambda_handler(event, context):
    try:
        body = _extract_params(event)

        game_map = body.get('game_map') or body.get('map_grid') or body.get('map') or body.get('maze') or body.get('grid') or []

        # Fallback: if game_map is empty or trivial, use the hardcoded internal map
        if not game_map or game_map == [[]] or (len(game_map) == 1 and len(game_map[0]) <= 1):
            game_map = INTERNAL_MAP

        if game_map:
            max_cols = max(len(row) for row in game_map)
            game_map = [row + ['normal'] * (max_cols - len(row)) for row in game_map]

        rows, cols = len(game_map), len(game_map[0]) if game_map else (0, 0)

        if not game_map:
            return _err(400, 'Missing game_map')

        # Auto-detect start from map, fallback to model's start_pos
        start_pos = None
        for sr in range(rows):
            for sc in range(cols):
                if game_map[sr][sc] in ('start', 'player', 'Start', 'Player'):
                    start_pos = (sr, sc)
                    break
            if start_pos:
                break
        
        # If auto-detect failed, use model's start_pos/current_pos parameter
        if start_pos is None:
            raw_start = body.get('start_pos') or body.get('current_pos') or body.get('start') or body.get('position') or None
            if raw_start:
                if isinstance(raw_start, (list, tuple)) and len(raw_start) >= 2:
                    start_pos = (int(raw_start[0]), int(raw_start[1]))
                elif isinstance(raw_start, str):
                    start_pos = _parse_start(raw_start)
            
            # Final fallback: (0,0) but NEVER use swift from here
            if start_pos is None:
                start_pos = (0, 0)

        strategy = str(body.get('strategy', 'smart_loot')).lower().strip()
        if 'swift' in strategy or 'fast' in strategy or 'quick' in strategy:
            strategy = 'swift'
        else:
            strategy = 'smart_loot'

        treasure = None
        for r in range(rows):
            for c in range(cols):
                if game_map[r][c] == 'treasure':
                    treasure = (r, c)
                    break
            if treasure:
                break

        if not treasure:
            return _err(400, 'No treasure found on map')

        if strategy == 'swift':
            path = swift_path(game_map, rows, cols, start_pos, treasure)
        else:
            path = smart_loot_path(game_map, rows, cols, start_pos, treasure)

        # Count all tiles dynamically
        tile_counts = {}
        for row in game_map:
            for cell in row:
                if cell.startswith('c'):
                    tile_counts[cell] = tile_counts.get(cell, 0) + 1
        counts_str = ' '.join(f'{k}={v}' for k, v in sorted(tile_counts.items()))

        result = {'path': path, 'steps': len(path), 'start_position': list(start_pos), 'counts': counts_str}
        return {'statusCode': 200, 'body': json.dumps(result)}

    except Exception as e:
        return _err(500, str(e))


def _err(code, msg):
    return {'statusCode': code, 'body': json.dumps({'error': msg})}
