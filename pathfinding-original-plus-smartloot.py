import json
import re
from collections import deque

CELL_POINTS = {"c7": 250}
COLLECTIBLE_COINS = {"c7"}
DIRECTIONS = [(-1, 0, "up"), (1, 0, "down"), (0, -1, "left"), (0, 1, "right")]

TARGET_VALUES = {"c4": 800, "c2": 600, "c3": 550, "c5": 250, "c1": 400, "c7": 250, "c17": 50, "c18": 500, "c40": 50, "c41": 50, "c30": 1000, "c31": 1000}


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
    """Check if a cell is a spike trap (various possible labels)."""
    c = cell.lower()
    return c == 'c8' or 'spike' in c or 'trap' in c


def _bfs(game_map, rows, cols, start, goal):
    """BFS - tries to avoid spikes first, falls back to allowing them."""
    queue = deque([(start[0], start[1], [])])
    visited = {(start[0], start[1])}
    while queue:
        r, c, path = queue.popleft()
        if (r, c) == goal:
            return path
        for dr, dc, move in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and game_map[nr][nc] != 'wall' and not _is_spike(game_map[nr][nc]) and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append((nr, nc, path + [move]))

    queue = deque([(start[0], start[1], [])])
    visited = {(start[0], start[1])}
    while queue:
        r, c, path = queue.popleft()
        if (r, c) == goal:
            return path
        for dr, dc, move in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and game_map[nr][nc] != 'wall' and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append((nr, nc, path + [move]))
    return None


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
        return full_path

    return swift_path(game_map, rows, cols, start, treasure)


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
