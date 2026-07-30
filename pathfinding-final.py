"""
AWS Lambda - Pathfinding tool for Bedrock Agent Game.
Based on ORIGINAL default Lambda format (proven to work with game input).
Added: smart_loot strategy, green key/door support, spike walkability.

Strategies:
  swift       - BFS shortest path to treasure (default)
  smart_loot  - Value-weighted target collection then treasure
  get_coins   - Greedily collect c7 coins on the way to treasure
"""

import json
import re
from collections import deque

CELL_POINTS = {"c7": 250, "c4": 800, "c2": 600, "c3": 550, "c5": 250, "c1": 400, "c17": 50, "c18": 500, "c40": 50, "c41": 50, "c30": 1000, "c31": 1000}
COLLECTIBLE_COINS = {"c7"}
DIRECTIONS = [(-1, 0, "up"), (1, 0, "down"), (0, -1, "left"), (0, 1, "right")]


def _parse_start(pos):
    """Parse start position from any format."""
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


def _bfs(game_map, rows, cols, start, goal):
    """BFS shortest path between two points. Walls are impassable."""
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
    """Greedily BFS to nearest c7 cell, then BFS to treasure."""
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
    """Value-weighted pathfinding: collect keys, challenges, coins, then treasure."""
    board = [row[:] for row in game_map]
    r, c = start
    full_path = []

    # Find special positions
    red_key = None
    green_key = None
    red_door = None
    green_door = None
    targets = []  # (row, col, cell_type, value)

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
            elif cell == 'treasure' or cell == 'wall' or cell == 'normal' or cell == 'start':
                continue
            elif cell.startswith('c'):
                value = CELL_POINTS.get(cell, 250)
                targets.append((row, col, cell, value))

    # Phase 1: Get Red Key (block doors)
    red_key_collected = False
    if red_key:
        # Block doors temporarily
        if red_door:
            board[red_door[0]][red_door[1]] = 'wall'
        if green_door:
            board[green_door[0]][green_door[1]] = 'wall'
        # Block treasure
        orig_treasure = board[treasure[0]][treasure[1]]
        board[treasure[0]][treasure[1]] = 'wall'

        # Visit targets on the way to red key using value/distance
        while (r, c) != red_key:
            best_path = None
            best_score = float('inf')
            best_dest = None

            # Consider red key
            kp = _bfs(board, rows, cols, (r, c), red_key)
            if kp:
                best_path = kp
                best_score = len(kp)
                best_dest = red_key

            # Consider nearby high-value targets
            for tr, tc, cell, value in list(targets):
                tp = _bfs(board, rows, cols, (r, c), (tr, tc))
                if tp:
                    dist = len(tp)
                    score = -(value / max(dist, 1))
                    if score < best_score:
                        best_path = tp
                        best_score = score
                        best_dest = (tr, tc)

            if best_path is None:
                break

            full_path.extend(best_path)
            r, c = best_dest
            # Remove visited target
            targets = [(tr, tc, cell, v) for tr, tc, cell, v in targets if (tr, tc) != (r, c)]
            board[r][c] = 'normal'

        if (r, c) == red_key:
            red_key_collected = True
            board[r][c] = 'normal'

        # Unblock red door
        if red_door:
            board[red_door[0]][red_door[1]] = 'c30'
        # Keep green door blocked and treasure blocked for now

    # Phase 2: Get Green Key (red door now open)
    green_key_collected = False
    if green_key:
        if not red_key_collected and red_door:
            board[red_door[0]][red_door[1]] = 'wall'
        if green_door:
            board[green_door[0]][green_door[1]] = 'wall'

        while (r, c) != green_key:
            best_path = None
            best_score = float('inf')
            best_dest = None

            kp = _bfs(board, rows, cols, (r, c), green_key)
            if kp:
                best_path = kp
                best_score = len(kp)
                best_dest = green_key

            for tr, tc, cell, value in list(targets):
                tp = _bfs(board, rows, cols, (r, c), (tr, tc))
                if tp:
                    dist = len(tp)
                    score = -(value / max(dist, 1))
                    if score < best_score:
                        best_path = tp
                        best_score = score
                        best_dest = (tr, tc)

            if best_path is None:
                break

            full_path.extend(best_path)
            r, c = best_dest
            targets = [(tr, tc, cell, v) for tr, tc, cell, v in targets if (tr, tc) != (r, c)]
            board[r][c] = 'normal'

        if (r, c) == green_key:
            green_key_collected = True
            board[r][c] = 'normal'

        # Unblock green door
        if green_door:
            board[green_door[0]][green_door[1]] = 'c31'

    # Unblock treasure
    board[treasure[0]][treasure[1]] = orig_treasure if 'orig_treasure' in dir() else 'treasure'

    # Phase 3: Visit all remaining targets (value/distance ordering)
    # Block treasure still
    board[treasure[0]][treasure[1]] = 'wall'

    while targets:
        best_path = None
        best_score = float('inf')
        best_idx = -1

        for i, (tr, tc, cell, value) in enumerate(targets):
            tp = _bfs(board, rows, cols, (r, c), (tr, tc))
            if tp:
                dist = len(tp)
                score = -(value / max(dist, 1))
                if score < best_score:
                    best_path = tp
                    best_score = score
                    best_idx = i

        if best_path is None or best_idx == -1:
            break

        full_path.extend(best_path)
        tr, tc, _, _ = targets[best_idx]
        r, c = tr, tc
        targets.pop(best_idx)
        board[r][c] = 'normal'

    # Phase 4: Go to treasure
    board[treasure[0]][treasure[1]] = 'treasure'
    path_end = _bfs(board, rows, cols, (r, c), treasure)
    if path_end:
        full_path.extend(path_end)
        return full_path

    # Fallback
    return swift_path(game_map, rows, cols, start, treasure)


def lambda_handler(event, context):
    try:
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        game_map = body.get('game_map', body.get('map_grid', []))

        # Fix jagged rows
        if game_map:
            max_cols = max(len(row) for row in game_map)
            game_map = [row + ['normal'] * (max_cols - len(row)) for row in game_map]

        # Parse start position
        map_config = body.get('map_config', {})
        player_start = map_config.get('playerStart') or body.get('playerStart') or {}
        if isinstance(player_start, str):
            start_pos = _parse_start(player_start)
        elif isinstance(player_start, dict) and player_start:
            start_pos = (player_start.get('row', 0), player_start.get('col', 0))
        else:
            raw = body.get('start_pos') or body.get('current_pos') or body.get('start') or body.get('position') or [0, 0]
            start_pos = _parse_start(raw)

        # Validate start
        if game_map and (start_pos[0] < 0 or start_pos[1] < 0 or start_pos[0] >= len(game_map) or start_pos[1] >= len(game_map[0])):
            start_pos = (0, 0)

        # Normalize strategy
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
