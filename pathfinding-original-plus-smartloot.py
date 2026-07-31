import json
import re
from collections import deque

CELL_POINTS = {"c7": 250}
COLLECTIBLE_COINS = {"c7"}
DIRECTIONS = [(-1, 0, "up"), (1, 0, "down"), (0, -1, "left"), (0, 1, "right")]

TARGET_VALUES = {"c4": 800, "c2": 600, "c3": 550, "c5": 250, "c1": 400, "c7": 250, "c17": 50, "c18": 500, "c40": 50, "c41": 50, "c30": 1000, "c31": 1000}

# Cells we KNOW are safe to walk through
KNOWN_SAFE_CELLS = frozenset([
    'normal', 'start', 'treasure',
    'c1', 'c2', 'c3', 'c4', 'c5', 'c7',
    'c17', 'c18', 'c30', 'c31', 'c40', 'c41'
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


def _bfs(game_map, rows, cols, start, goal):
    """Standard BFS avoiding walls only. Simple and reliable.
    Spike avoidance is handled by post-processing, not here."""
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
                if cell != 'wall':
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
    3. Only replaces small segments (max 6 moves detour)
    4. Never replaces the full path
    
    A cell is a "transit" if:
    - We enter it AND leave it (not the final move to a target/destination)
    - The path continues past it
    
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

    # Find "turning points" - positions where direction changes or we stop/reverse
    # These are intentional destinations (targets). Cells between turning points are transit.
    # Simple heuristic: a cell is a DESTINATION if the path reverses direction after it
    # or if it's a target cell type (challenge, key, door, coin).
    # For our purposes: any suspicious cell that has BOTH a predecessor AND successor 
    # in the path is a transit cell (we're just passing through).
    
    # Find dangerous TRANSIT cells only
    dangerous_indices = []
    for i in range(1, len(positions) - 1):  # skip first and last positions
        pr, pc = positions[i]
        if 0 <= pr < rows and 0 <= pc < cols:
            cell = game_map[pr][pc]
            if _is_suspicious(cell):
                # Check if this is a transit (passing through) or destination
                # If the NEXT move takes us AWAY from this cell, it's transit
                # If we stay here or the path ends here, it's a destination
                # Simple: if there's a move after this position, it's transit
                dangerous_indices.append(i)

    if not dangerous_indices:
        return full_path  # Path is clean

    # Collect all dangerous TRANSIT positions
    avoid_cells = set()
    for i in dangerous_indices:
        avoid_cells.add(positions[i])

    # Process each dangerous transit cell - reroute the segment around it
    # Work from last to first to maintain indices
    result_path = list(full_path)
    result_positions = list(positions)

    for danger_idx in sorted(dangerous_indices, reverse=True):
        # Recalculate positions (they may have shifted from previous fixes)
        result_positions = [start_pos]
        tr, tc = start_pos
        for move in result_path:
            dr, dc = move_map[move]
            tr, tc = tr + dr, tc + dc
            result_positions.append((tr, tc))

        if danger_idx >= len(result_positions) - 1:
            continue

        # The dangerous cell is at result_positions[danger_idx]
        # Reroute from cell BEFORE it to cell AFTER it
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
            move_start = seg_start_idx  # = danger_idx - 1
            move_end = seg_end_idx      # = danger_idx + 1 (exclusive in moves)

            result_path = result_path[:move_start] + alt_segment + result_path[move_end:]

    return result_path


def swift_path(game_map, rows, cols, start, treasure):
    return _bfs(game_map, rows, cols, start, treasure) or []


def smart_loot_path(game_map, rows, cols, start, treasure):
    """Keys first, then nearest-neighbor sweep. NEVER modifies game_map."""
    r, c = start
    full_path = []
    visited_targets = set()

    red_key = green_key = red_door = green_door = None
    all_targets = []
    for row in range(rows):
        for col in range(cols):
            cell = game_map[row][col]
            if cell == 'c40': red_key = (row, col)
            elif cell == 'c41': green_key = (row, col)
            elif cell == 'c30': red_door = (row, col)
            elif cell == 'c31': green_door = (row, col)
            elif cell in ('treasure', 'wall', 'normal', 'start', 'c8'): continue
            elif cell.startswith('c'):
                all_targets.append((row, col, cell, TARGET_VALUES.get(cell, 250)))

    # Phase 1: Go STRAIGHT to Red Key
    red_key_collected = False
    if red_key:
        path_to_key = _bfs(game_map, rows, cols, (r, c), red_key)
        if path_to_key:
            full_path.extend(path_to_key)
            r, c = red_key
            red_key_collected = True
            visited_targets.add(red_key)

    # Phase 2: Go STRAIGHT to Green Key
    green_key_collected = False
    if green_key:
        path_to_key = _bfs(game_map, rows, cols, (r, c), green_key)
        if path_to_key:
            full_path.extend(path_to_key)
            r, c = green_key
            green_key_collected = True
            visited_targets.add(green_key)

    # Phase 3: Visit ALL remaining targets by nearest-neighbor
    remaining = [(tr, tc, cell, val) for tr, tc, cell, val in all_targets if (tr, tc) not in visited_targets]
    while remaining:
        best_path = None
        best_dist = float('inf')
        best_idx = -1
        for i, (tr, tc, cell, value) in enumerate(remaining):
            tp = _bfs(game_map, rows, cols, (r, c), (tr, tc))
            if tp and len(tp) < best_dist:
                best_path = tp
                best_dist = len(tp)
                best_idx = i
        if best_path is None: break
        full_path.extend(best_path)
        tr, tc, _, _ = remaining[best_idx]
        r, c = tr, tc
        remaining.pop(best_idx)

    # Phase 4: Go to treasure
    path_end = _bfs(game_map, rows, cols, (r, c), treasure)
    if path_end:
        full_path.extend(path_end)
    else:
        return swift_path(game_map, rows, cols, start, treasure)

    # Phase 5: POST-PROCESS - reroute around spikes/suspicious cells
    full_path = _post_process_avoid_spikes(game_map, rows, cols, full_path, start)

    return full_path


def lambda_handler(event, context):
    try:
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        game_map = body.get('game_map', [])

        if game_map:
            max_cols = max(len(row) for row in game_map)
            game_map = [row + ['normal'] * (max_cols - len(row)) for row in game_map]

        map_config = body.get('map_config', {})
        player_start = map_config.get('playerStart') or body.get('playerStart') or {}
        if isinstance(player_start, str):
            start_pos = _parse_start(player_start)
        elif isinstance(player_start, dict) and player_start:
            start_pos = (player_start.get('row', 0), player_start.get('col', 0))
        else:
            raw = body.get('start_pos') or body.get('start') or body.get('position') or [0, 0]
            start_pos = _parse_start(raw)

        if game_map and (start_pos[0] < 0 or start_pos[1] < 0 or start_pos[0] >= len(game_map) or start_pos[1] >= len(game_map[0])):
            start_pos = (0, 0)

        # Auto-detect start from map if defaulted to (0,0)
        rows_check = len(game_map) if game_map else 0
        cols_check = len(game_map[0]) if game_map and game_map[0] else 0
        if start_pos == (0, 0) and rows_check > 0 and cols_check > 0:
            if game_map[0][0] != 'start':
                for sr in range(rows_check):
                    for sc in range(cols_check):
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

        if not game_map:
            return _err(400, 'Missing game_map')

        rows, cols = len(game_map), len(game_map[0])
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

        result = {'path': path, 'steps': len(path), 'start_position': list(start_pos)}
        return {'statusCode': 200, 'body': json.dumps(result)}

    except Exception as e:
        return _err(500, str(e))


def _err(code, msg):
    return {'statusCode': code, 'body': json.dumps({'error': msg})}
