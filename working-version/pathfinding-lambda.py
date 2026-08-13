import json
import re
from collections import deque

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

# Key tiles (must be collected before their corresponding doors)
KEY_TILES = frozenset(["c40", "c41", "c42", "c43"])

# Door tiles (challenges that require their key first)
CHALLENGE_TILES = frozenset(["c30", "c31", "c32", "c33"])

# Cells we KNOW are safe to walk through
KNOWN_SAFE_CELLS = frozenset([
    'normal', 'start', 'treasure',
    'c1', 'c2', 'c3', 'c4', 'c5', 'c7',
    'c17', 'c18',
    'c30', 'c31', 'c32', 'c33',
    'c40', 'c41', 'c42', 'c43'
])

# Cells we KNOW are dangerous (spike traps)
KNOWN_SPIKE_CELLS = frozenset(['c8'])


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


def _is_suspicious(cell):
    """Check if a cell is NOT in our known-safe list and NOT a wall.
    These are cells that MIGHT be dangerous (unknown types like the I3 spike)."""
    c = cell.lower()
    if c == 'wall':
        return False
    if c in KNOWN_SAFE_CELLS:
        return False
    if c in KNOWN_SPIKE_CELLS:
        return True
    # Unknown cell type - suspicious!
    return True


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


def _bfs_avoiding(game_map, rows, cols, start, goal, avoid_cells):
    """BFS that avoids specific cells (by coordinate). Used for rerouting."""
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
                if cell != 'wall' and (nr, nc) not in avoid_cells:
                    visited.add((nr, nc))
                    queue.append((nr, nc, path + [move]))
    return None


def _post_process_avoid_spikes(game_map, rows, cols, full_path, start_pos):
    """After generating a path, scan for suspicious cells we PASS THROUGH and reroute.

    CRITICAL RULES:
    1. Only reroutes TRANSIT cells (cells we pass through on the way somewhere else)
    2. Does NOT avoid cells that are DESTINATIONS (targets we intentionally visit)
    3. Only replaces small segments (max 10 moves detour)
    4. Never replaces the full path

    Returns an improved path (or the original if no improvement possible).
    """
    if not full_path:
        return full_path

    move_map = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}

    # Trace the path to find all positions visited
    positions = [start_pos]
    r, c = start_pos
    for move in full_path:
        dr, dc = move_map[move]
        r, c = r + dr, c + dc
        positions.append((r, c))

    # Find dangerous TRANSIT cells only
    dangerous_indices = []
    for i in range(1, len(positions) - 1):  # skip first and last positions
        pr, pc = positions[i]
        if 0 <= pr < rows and 0 <= pc < cols:
            cell = game_map[pr][pc]
            if _is_suspicious(cell):
                dangerous_indices.append(i)

    if not dangerous_indices:
        return full_path  # Path is clean

    # Collect all dangerous TRANSIT positions
    avoid_cells = set()
    for i in dangerous_indices:
        avoid_cells.add(positions[i])

    # Process each dangerous transit cell - reroute the segment around it
    result_path = list(full_path)

    for danger_idx in sorted(dangerous_indices, reverse=True):
        # Recalculate positions
        result_positions = [start_pos]
        tr, tc = start_pos
        for move in result_path:
            dr, dc = move_map[move]
            tr, tc = tr + dr, tc + dc
            result_positions.append((tr, tc))

        if danger_idx >= len(result_positions) - 1:
            continue

        seg_start_idx = danger_idx - 1
        seg_end_idx = danger_idx + 1

        if seg_start_idx < 0 or seg_end_idx >= len(result_positions):
            continue

        seg_start_pos = result_positions[seg_start_idx]
        seg_end_pos = result_positions[seg_end_idx]

        # BFS from before-spike to after-spike, avoiding all dangerous cells
        alt_segment = _bfs_avoiding(game_map, rows, cols, seg_start_pos, seg_end_pos, avoid_cells)

        if alt_segment and len(alt_segment) <= 10:
            # Replace the 2 original moves with the alternative segment
            move_start = seg_start_idx
            move_end = seg_end_idx

            result_path = result_path[:move_start] + alt_segment + result_path[move_end:]

    return result_path


def swift_path(game_map, rows, cols, start, treasure):
    return _bfs(game_map, rows, cols, start, treasure) or []


def smart_loot_path(game_map, rows, cols, start, treasure):
    """Keys first, then nearest-neighbor with transit marking. NEVER modifies game_map.
    Doors are blocked until their corresponding key is collected."""
    r, c = start
    full_path = []
    visited_targets = set()
    collected_keys = set()  # Track which keys have been collected

    move_map = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}

    # Scan map for keys, doors, and other targets
    key_positions = {}   # cell_type -> (row, col)
    door_positions = {}  # cell_type -> (row, col)
    all_targets = []

    for row in range(rows):
        for col in range(cols):
            cell = game_map[row][col]
            if cell in KEY_TILES:
                key_positions[cell] = (row, col)
            elif cell in CHALLENGE_TILES:
                door_positions[cell] = (row, col)
            elif cell in ('treasure', 'wall', 'normal', 'start', 'c8'):
                continue
            elif cell.startswith('c'):
                all_targets.append((row, col, cell, TARGET_VALUES.get(cell, 250)))

    # Add doors to all_targets too (they are challenge targets)
    for cell, pos in door_positions.items():
        all_targets.append((pos[0], pos[1], cell, TARGET_VALUES.get(cell, 1000)))

    # Helper: find targets the BFS path passes through (free pickups)
    target_positions = {(tr, tc) for tr, tc, _, _ in all_targets}
    # Also include key positions as potential transit pickups
    for kpos in key_positions.values():
        target_positions.add(kpos)

    def mark_transit(path, sr, sc):
        passed = set()
        tr, tc = sr, sc
        for move in path:
            dr, dc = move_map[move]
            tr, tc = tr + dr, tc + dc
            if (tr, tc) in target_positions:
                passed.add((tr, tc))
        return passed

    def get_blocked_doors():
        """Return set of (row, col) for doors whose keys haven't been collected yet."""
        blocked = set()
        for key_cell, door_cell in KEY_DOOR_MAP.items():
            if key_cell not in collected_keys and door_cell in door_positions:
                blocked.add(door_positions[door_cell])
        return blocked

    # Phase 1: Collect ALL keys first (in order: red, green, grey, yellow)
    key_order = ["c40", "c41", "c42", "c43"]
    for key_cell in key_order:
        if key_cell in key_positions:
            key_pos = key_positions[key_cell]
            blocked = get_blocked_doors()
            path_to_key = _bfs(game_map, rows, cols, (r, c), key_pos, blocked)
            if path_to_key:
                transit = mark_transit(path_to_key, r, c)
                visited_targets.update(transit)
                # Check if we passed through any key positions
                for kt, kp in key_positions.items():
                    if kp in transit:
                        collected_keys.add(kt)
                full_path.extend(path_to_key)
                r, c = key_pos
                visited_targets.add(key_pos)
                collected_keys.add(key_cell)

    # Phase 2: Visit ALL remaining targets by nearest-neighbor
    # DEFER cells within 2 moves of treasure (visit them last)
    remaining = [(tr, tc, cell, val) for tr, tc, cell, val in all_targets if (tr, tc) not in visited_targets]

    near_treasure = set()
    blocked = get_blocked_doors()
    for tr, tc, cell, val in remaining:
        tp = _bfs(game_map, rows, cols, (tr, tc), treasure, blocked)
        if tp and len(tp) <= 2:
            near_treasure.add((tr, tc))

    remaining_now = [(tr, tc, cell, val) for tr, tc, cell, val in remaining if (tr, tc) not in near_treasure]
    remaining_last = [(tr, tc, cell, val) for tr, tc, cell, val in remaining if (tr, tc) in near_treasure]

    for target_list in [remaining_now, remaining_last]:
        while target_list:
            # Remove already-visited targets (from transit marking)
            target_list[:] = [(tr, tc, cell, val) for tr, tc, cell, val in target_list if (tr, tc) not in visited_targets]
            if not target_list:
                break

            blocked = get_blocked_doors()

            best_path = None
            best_dist = float('inf')
            best_idx = -1
            for i, (tr, tc, cell, value) in enumerate(target_list):
                # Skip doors that are still locked
                if (tr, tc) in blocked:
                    continue
                tp = _bfs(game_map, rows, cols, (r, c), (tr, tc), blocked)
                if tp and len(tp) < best_dist:
                    best_path = tp
                    best_dist = len(tp)
                    best_idx = i
            if best_path is None:
                # Remove locked doors from list and retry
                target_list[:] = [(tr, tc, cell, val) for tr, tc, cell, val in target_list if (tr, tc) not in blocked]
                if not target_list:
                    break
                # If still stuck, break
                has_reachable = False
                for tr, tc, cell, val in target_list:
                    tp = _bfs(game_map, rows, cols, (r, c), (tr, tc))
                    if tp:
                        has_reachable = True
                        break
                if not has_reachable:
                    break
                continue

            # Mark transit targets (free pickups along the way)
            transit = mark_transit(best_path, r, c)
            visited_targets.update(transit)
            # Check if we passed through any key positions
            for kt, kp in key_positions.items():
                if kp in transit:
                    collected_keys.add(kt)

            full_path.extend(best_path)
            tr, tc, _, _ = target_list[best_idx]
            r, c = tr, tc
            visited_targets.add((tr, tc))
            # If this was a key, mark it collected
            cell_at = game_map[tr][tc]
            if cell_at in KEY_TILES:
                collected_keys.add(cell_at)
            target_list.pop(best_idx)

    # Phase 3: Go to treasure
    blocked = get_blocked_doors()
    path_end = _bfs(game_map, rows, cols, (r, c), treasure, blocked)
    if not path_end:
        # Try without blocked doors as fallback
        path_end = _bfs(game_map, rows, cols, (r, c), treasure)
    if path_end:
        full_path.extend(path_end)
    else:
        return swift_path(game_map, rows, cols, start, treasure)

    # Phase 4: POST-PROCESS - reroute around spikes/suspicious cells
    full_path = _post_process_avoid_spikes(game_map, rows, cols, full_path, start)

    return full_path


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

        game_map = body.get('game_map', [])

        if game_map:
            max_cols = max(len(row) for row in game_map)
            game_map = [row + ['normal'] * (max_cols - len(row)) for row in game_map]

        rows, cols = len(game_map), len(game_map[0]) if game_map else (0, 0)

        if not game_map:
            return _err(400, 'Missing game_map')

        # ALWAYS auto-detect start from map - ignore model's start_pos
        start_pos = (0, 0)
        for sr in range(rows):
            for sc in range(cols):
                if game_map[sr][sc] == 'start':
                    start_pos = (sr, sc)
                    break
            if start_pos != (0, 0):
                break

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
