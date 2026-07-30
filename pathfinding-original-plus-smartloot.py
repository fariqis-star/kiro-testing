import json
import re
from collections import deque

CELL_POINTS = {"c7": 250}
COLLECTIBLE_COINS = {"c7"}
DIRECTIONS = [(-1, 0, "up"), (1, 0, "down"), (0, -1, "left"), (0, 1, "right")]

# Value per challenge type for smart_loot
TARGET_VALUES = {"c4": 800, "c2": 600, "c3": 550, "c5": 250, "c1": 400, "c7": 250, "c17": 50, "c18": 500, "c40": 50, "c41": 50, "c30": 1000, "c31": 1000}


def _parse_start(pos):
    """Parse start position from any format Nova might send."""
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


def lambda_handler(event, context):
    """
    AWS Lambda function for pathfinding.
    Based on original default code with added smart_loot strategy.

    Strategies:
      swift      - BFS shortest path to treasure (default)
      get_coins  - Greedily collect c7 coins on the way to treasure
      smart_loot - Value-weighted collection of all targets then treasure
    """
    try:
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        game_map = body.get('game_map', [])

        # Fix jagged rows (model sometimes drops elements)
        if game_map:
            max_cols = max(len(row) for row in game_map)
            game_map = [row + ['normal'] * (max_cols - len(row)) for row in game_map]

        # Parse start position from any format
        map_config = body.get('map_config', {})
        player_start = map_config.get('playerStart') or body.get('playerStart') or {}
        if isinstance(player_start, str):
            start_pos = _parse_start(player_start)
        elif isinstance(player_start, dict) and player_start:
            start_pos = (player_start.get('row', 0), player_start.get('col', 0))
        else:
            raw = body.get('start_pos') or body.get('start') or body.get('position') or [0, 0]
            start_pos = _parse_start(raw)

        # Validate start is within map bounds
        if game_map and (start_pos[0] < 0 or start_pos[1] < 0 or start_pos[0] >= len(game_map) or start_pos[1] >= len(game_map[0])):
            start_pos = (0, 0)

        # Normalize strategy name
        strategy = str(body.get('strategy', 'smart_loot')).lower().strip()
        if 'coin' in strategy:
            strategy = 'get_coins'
        elif 'swift' in strategy or 'fast' in strategy or 'quick' in strategy:
            strategy = 'swift'
        elif 'smart' in strategy or 'loot' in strategy or 'value' in strategy:
            strategy = 'smart_loot'
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

        if strategy == 'get_coins':
            path = get_coins_path(game_map, rows, cols, start_pos, treasure)
        elif strategy == 'smart_loot':
            path = smart_loot_path(game_map, rows, cols, start_pos, treasure)
        else:
            path = swift_path(game_map, rows, cols, start_pos, treasure)

        result = {'path': path, 'steps': len(path), 'start_position': list(start_pos)}
        return {'statusCode': 200, 'body': json.dumps(result)}

    except Exception as e:
        return _err(500, str(e))


def _err(code, msg):
    return {'statusCode': code, 'body': json.dumps({'error': msg})}


def _bfs(game_map, rows, cols, start, goal):
    """BFS shortest path between two points."""
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
    """BFS shortest path to treasure."""
    return _bfs(game_map, rows, cols, start, treasure) or []


def get_coins_path(game_map, rows, cols, start, treasure):
    """Greedily BFS to best coins-per-step c7 cell, then BFS to treasure."""
    board = [row[:] for row in game_map]
    r, c = start
    full_path = []

    for _ in range(50):
        queue = deque([(r, c, [])])
        visited = {(r, c)}
        targets = []
        while queue:
            cr, cc, p = queue.popleft()
            if board[cr][cc] in COLLECTIBLE_COINS and (cr, cc) != (r, c):
                dist = max(len(p), 1)
                targets.append((dist, p, cr, cc))
            for dr, dc, move in DIRECTIONS:
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != 'wall' and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    queue.append((nr, nc, p + [move]))

        if not targets:
            break
        targets.sort()
        _, path_to, r, c = targets[0]
        full_path.extend(path_to)
        board[r][c] = 'normal'

    path_end = _bfs(board, rows, cols, (r, c), treasure)
    if path_end is not None:
        full_path.extend(path_end)
        return full_path
    return swift_path(game_map, rows, cols, start, treasure)


def smart_loot_path(game_map, rows, cols, start, treasure):
    """Value-weighted: get keys, visit all challenges/coins by value, then treasure."""
    board = [row[:] for row in game_map]
    r, c = start
    full_path = []

    # Find keys, doors, and all targets
    red_key = None
    green_key = None
    red_door = None
    green_door = None
    all_targets = []

    for row in range(rows):
        for col in range(cols):
            cell = board[row][col]
            if cell == 'c40':
                red_key = (row, col)
            elif cell == 'c41':
                green_key = (row, col)
            elif cell == 'c30':
                red_door = (row, col)
            elif cell == 'c31':
                green_door = (row, col)
            elif cell in ('treasure', 'wall', 'normal', 'start', 'c8'):
                continue
            elif cell.startswith('c'):
                value = TARGET_VALUES.get(cell, 250)
                all_targets.append((row, col, cell, value))

    # Phase 1: Get Red Key (doors + treasure blocked)
    red_key_collected = False
    orig_cells = {}

    if red_key:
        if red_door:
            orig_cells[red_door] = board[red_door[0]][red_door[1]]
            board[red_door[0]][red_door[1]] = 'wall'
        if green_door:
            orig_cells[green_door] = board[green_door[0]][green_door[1]]
            board[green_door[0]][green_door[1]] = 'wall'
        orig_cells[treasure] = board[treasure[0]][treasure[1]]
        board[treasure[0]][treasure[1]] = 'wall'

        # Go to red key, picking up targets along the way
        while (r, c) != red_key:
            best_path = None
            best_score = len(_bfs(board, rows, cols, (r, c), red_key) or []) or 9999
            best_dest = red_key
            kp = _bfs(board, rows, cols, (r, c), red_key)
            if kp:
                best_path = kp
                best_dest = red_key

            for i, (tr, tc, cell, value) in enumerate(all_targets):
                tp = _bfs(board, rows, cols, (r, c), (tr, tc))
                if tp and -(value / max(len(tp), 1)) < -(TARGET_VALUES.get('c40', 50) / max(best_score, 1)):
                    best_path = tp
                    best_dest = (tr, tc)
                    best_score = -(value / max(len(tp), 1))

            if best_path is None:
                break
            full_path.extend(best_path)
            r, c = best_dest
            all_targets = [(tr, tc, ce, v) for tr, tc, ce, v in all_targets if (tr, tc) != (r, c)]
            if board[r][c] not in ('wall', 'treasure'):
                board[r][c] = 'normal'

        if (r, c) == red_key:
            red_key_collected = True
            board[r][c] = 'normal'

        # Unblock red door
        if red_door and red_door in orig_cells:
            board[red_door[0]][red_door[1]] = orig_cells[red_door]

    # Phase 2: Get Green Key (red door open, green door + treasure blocked)
    green_key_collected = False
    if green_key:
        if not red_key_collected and red_door:
            board[red_door[0]][red_door[1]] = 'wall'
        if green_door and green_door not in orig_cells:
            orig_cells[green_door] = board[green_door[0]][green_door[1]]
            board[green_door[0]][green_door[1]] = 'wall'

        while (r, c) != green_key:
            kp = _bfs(board, rows, cols, (r, c), green_key)
            if not kp:
                break

            best_path = kp
            best_dest = green_key

            for i, (tr, tc, cell, value) in enumerate(all_targets):
                tp = _bfs(board, rows, cols, (r, c), (tr, tc))
                if tp and len(tp) < len(kp) and value >= 250:
                    best_path = tp
                    best_dest = (tr, tc)

            full_path.extend(best_path)
            r, c = best_dest
            all_targets = [(tr, tc, ce, v) for tr, tc, ce, v in all_targets if (tr, tc) != (r, c)]
            if board[r][c] not in ('wall', 'treasure'):
                board[r][c] = 'normal'

        if (r, c) == green_key:
            green_key_collected = True
            board[r][c] = 'normal'

        # Unblock green door
        if green_door and green_door in orig_cells:
            board[green_door[0]][green_door[1]] = orig_cells[green_door]

    # Phase 3: Visit remaining targets by value/distance
    # Keep treasure blocked
    if treasure in orig_cells:
        board[treasure[0]][treasure[1]] = 'wall'

    while all_targets:
        best_path = None
        best_score = float('inf')
        best_idx = -1

        for i, (tr, tc, cell, value) in enumerate(all_targets):
            tp = _bfs(board, rows, cols, (r, c), (tr, tc))
            if tp:
                score = -(value / max(len(tp), 1))
                if score < best_score:
                    best_path = tp
                    best_score = score
                    best_idx = i

        if best_path is None:
            break

        full_path.extend(best_path)
        tr, tc, _, _ = all_targets[best_idx]
        r, c = tr, tc
        all_targets.pop(best_idx)
        if board[r][c] not in ('wall', 'treasure'):
            board[r][c] = 'normal'

    # Phase 4: Go to treasure
    board[treasure[0]][treasure[1]] = 'treasure'
    path_end = _bfs(board, rows, cols, (r, c), treasure)
    if path_end:
        full_path.extend(path_end)
        return full_path

    return swift_path(game_map, rows, cols, start, treasure)
