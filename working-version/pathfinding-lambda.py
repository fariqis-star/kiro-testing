import json
import re
import os
from collections import deque

COLLECTIBLE_COINS = {"c7"}
CHALLENGE_TILES = {"c1", "c2", "c3", "c4", "c5", "c6", "c17", "c18", "c30", "c31"}
BLOCKED_TILES = {"wall", "c8"}
BLOCKED_TILES_NO_SPIKES = {"wall"}
DIRECTIONS = [(-1, 0, "up"), (1, 0, "down"), (0, -1, "left"), (0, 1, "right")]
MAP_STORAGE = "/tmp/game_map.json"


def _parse_start(pos):
    try:
        if isinstance(pos, (list, tuple)):
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


def _extract_params(event):
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



def _bfs(game_map, rows, cols, start, goal, extra_blocked=None, allow_cells=None, allow_spikes=False):
    """BFS with spike awareness. Blocks c8 unless allow_spikes=True or cell in allow_cells."""
    blocked = extra_blocked or set()
    allowed = allow_cells or set()
    block_set = BLOCKED_TILES_NO_SPIKES if allow_spikes else BLOCKED_TILES
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
                if (nr, nc) in allowed:
                    visited.add((nr, nc))
                    queue.append((nr, nc, path + [move]))
                elif cell not in block_set and (nr, nc) not in blocked:
                    visited.add((nr, nc))
                    queue.append((nr, nc, path + [move]))
    return None


def _bfs_spike_aware(game_map, rows, cols, start, goal, extra_blocked=None, allow_cells=None):
    """Try avoiding spikes first, fallback to allowing them."""
    path = _bfs(game_map, rows, cols, start, goal, extra_blocked=extra_blocked, allow_cells=allow_cells, allow_spikes=False)
    if path is not None:
        return path
    return _bfs(game_map, rows, cols, start, goal, extra_blocked=extra_blocked, allow_cells=allow_cells, allow_spikes=True)


def _find_start_exit(game_map, rows, cols, start_pos):
    """Detect forced spike exits from start position."""
    r, c = start_pos
    allow = set()
    has_free_exit = False
    for dr, dc, _ in DIRECTIONS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            cell = game_map[nr][nc]
            if cell not in BLOCKED_TILES:
                has_free_exit = True
                break
    if not has_free_exit:
        for dr, dc, _ in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if game_map[nr][nc] == 'c8':
                    allow.add((nr, nc))
    return allow



def _pathfind(game_map, start_pos):
    """Full pathfinding: sweep coins, handle keys/doors, avoid spikes, reach treasure."""
    rows = len(game_map)
    cols = len(game_map[0])
    board = [row[:] for row in game_map]
    r, c = start_pos
    full_path = []

    allowed_spikes = _find_start_exit(game_map, rows, cols, start_pos)

    # Find special positions
    treasure = None
    red_key_pos = None
    red_door_pos = None
    green_key_pos = None
    green_door_pos = None
    for row in range(rows):
        for col in range(cols):
            cell = board[row][col]
            if cell == 'treasure':
                treasure = (row, col)
            elif cell == 'c40':
                red_key_pos = (row, col)
            elif cell == 'c30':
                red_door_pos = (row, col)
            elif cell == 'c41':
                green_key_pos = (row, col)
            elif cell == 'c31':
                green_door_pos = (row, col)

    if not treasure:
        return []

    # Block doors initially
    blocked_doors = set()
    if red_door_pos:
        blocked_doors.add(red_door_pos)
    if green_door_pos:
        blocked_doors.add(green_door_pos)

    def get_targets(board, blocked):
        targets = set()
        for row in range(rows):
            for col in range(cols):
                cell = board[row][col]
                if cell in COLLECTIBLE_COINS or cell in CHALLENGE_TILES:
                    if (row, col) not in blocked:
                        targets.add((row, col))
        return targets

    def sweep(board, cur_r, cur_c, blocked):
        """Greedy nearest-first sweep avoiding spikes."""
        path = []
        r, c = cur_r, cur_c
        for _ in range(80):
            targets = get_targets(board, blocked)
            best_dist = float('inf')
            best_path = None
            best_target = None
            for target in list(targets):
                if target == (r, c):
                    board[r][c] = 'normal'
                    continue
                tp = _bfs_spike_aware(board, rows, cols, (r, c), target, extra_blocked=blocked, allow_cells=allowed_spikes)
                if tp and len(tp) < best_dist:
                    best_dist = len(tp)
                    best_path = tp
                    best_target = target
            if best_target:
                path.extend(best_path)
                r, c = best_target
                board[r][c] = 'normal'
            else:
                break
        return path, r, c

    # PHASE 1: Sweep accessible targets (doors blocked)
    path_segment, r, c = sweep(board, r, c, blocked_doors)
    full_path.extend(path_segment)

    # PHASE 2: Get RED key
    if red_key_pos and red_door_pos:
        if board[red_key_pos[0]][red_key_pos[1]] != 'normal':
            path_to_key = _bfs_spike_aware(board, rows, cols, (r, c), red_key_pos, extra_blocked=blocked_doors, allow_cells=allowed_spikes)
            if path_to_key:
                full_path.extend(path_to_key)
                r, c = red_key_pos
                board[r][c] = 'normal'
        blocked_doors.discard(red_door_pos)

    # PHASE 3: Get GREEN key
    if green_key_pos and green_door_pos:
        if board[green_key_pos[0]][green_key_pos[1]] != 'normal':
            path_to_key = _bfs_spike_aware(board, rows, cols, (r, c), green_key_pos, extra_blocked=blocked_doors, allow_cells=allowed_spikes)
            if path_to_key:
                full_path.extend(path_to_key)
                r, c = green_key_pos
                board[r][c] = 'normal'
        blocked_doors.discard(green_door_pos)

    # PHASE 4: Sweep ALL remaining targets (doors open)
    path_segment, r, c = sweep(board, r, c, blocked_doors)
    full_path.extend(path_segment)

    # PHASE 5: Go to treasure
    path_to_treasure = _bfs_spike_aware(board, rows, cols, (r, c), treasure, extra_blocked=blocked_doors, allow_cells=allowed_spikes)
    if path_to_treasure:
        full_path.extend(path_to_treasure)
        return full_path

    # Fallback: direct path allowing all spikes
    all_spikes = set()
    for row in range(rows):
        for col in range(cols):
            if game_map[row][col] == 'c8':
                all_spikes.add((row, col))
    direct = _bfs(game_map, rows, cols, start_pos, treasure, allow_cells=all_spikes, allow_spikes=True)
    return direct or []



def _validate_path(game_map, rows, cols, start_pos, path):
    """Validate path - stop if a move goes into a wall."""
    validated = []
    r, c = start_pos
    move_map = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
    for move in path:
        dr, dc = move_map.get(move, (0, 0))
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and game_map[nr][nc] != "wall":
            validated.append(move)
            r, c = nr, nc
        else:
            break
    return validated


def lambda_handler(event, context):
    try:
        params = _extract_params(event)

        game_map = (params.get('game_map') or params.get('map') or
                   params.get('maze') or params.get('grid') or [])

        if isinstance(game_map, str):
            try:
                game_map = json.loads(game_map)
            except (json.JSONDecodeError, TypeError):
                game_map = []

        if game_map:
            max_cols = max(len(row) for row in game_map)
            game_map = [row + ['normal'] * (max_cols - len(row)) for row in game_map]

        # Determine action
        strategy = str(params.get('strategy', params.get('action', 'smart_loot'))).lower().strip()

        # === COUNT MODE ===
        if 'count' in strategy or params.get('count_type') or params.get('tile'):
            count_type = str(params.get('count_type', params.get('tile', params.get('count', '')))).strip().lower()

            # Try stored map first
            stored_map = None
            if not game_map:
                try:
                    if os.path.exists(MAP_STORAGE):
                        with open(MAP_STORAGE, 'r') as f:
                            stored_map = json.loads(f.read())
                except:
                    pass
            else:
                stored_map = game_map

            if not stored_map:
                return {'statusCode': 200, 'body': json.dumps({'count': 0, 'answer': '0', 'error': 'No map'})}

            # Handle addition: "c1+c2" or "c1 and c2"
            count_type = count_type.replace(' and ', '+').replace(',', '+')
            if '+' in count_type:
                types_to_count = [t.strip() for t in count_type.split('+') if t.strip()]
            else:
                types_to_count = [count_type]

            total = 0
            for row in stored_map:
                for cell in row:
                    if cell.lower() in types_to_count:
                        total += 1

            return {'statusCode': 200, 'body': json.dumps({'count': total, 'answer': str(total)})}

        # === PATHFIND MODE ===
        if not game_map:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Missing game_map'})}

        # Store map for later counting
        try:
            with open(MAP_STORAGE, 'w') as f:
                f.write(json.dumps(game_map))
        except:
            pass

        # Parse start position
        raw_start = (params.get('start_pos') or params.get('start') or
                    params.get('position') or params.get('playerStart') or [0, 0])
        if isinstance(raw_start, str):
            start_pos = _parse_start(raw_start)
        elif isinstance(raw_start, dict):
            start_pos = (raw_start.get('row', 0), raw_start.get('col', 0))
        else:
            start_pos = _parse_start(raw_start)

        rows, cols = len(game_map), len(game_map[0])
        if start_pos[0] >= rows or start_pos[1] >= cols:
            start_pos = (0, 0)

        # Auto-detect start
        if start_pos == (0, 0) and game_map[0][0] != 'start':
            for sr in range(rows):
                for sc in range(cols):
                    if game_map[sr][sc] == 'start':
                        start_pos = (sr, sc)
                        break
                if start_pos != (0, 0):
                    break

        # Run pathfinding
        if 'swift' in strategy or 'fast' in strategy or 'quick' in strategy:
            treasure = None
            for r in range(rows):
                for c in range(cols):
                    if game_map[r][c] == 'treasure':
                        treasure = (r, c)
                        break
            path = _bfs(game_map, rows, cols, start_pos, treasure, allow_spikes=True) or []
        else:
            path = _pathfind(game_map, start_pos)

        # Validate path (prevent wall crashes)
        path = _validate_path(game_map, rows, cols, start_pos, path)

        # Count ALL tiles for memory challenges
        tile_counts = {}
        for row in game_map:
            for cell in row:
                if cell not in ('normal', 'wall', 'start', 'treasure'):
                    tile_counts[cell] = tile_counts.get(cell, 0) + 1

        # Find treasure position
        treasure_pos = [0, 0]
        for r in range(len(game_map)):
            for c in range(len(game_map[0])):
                if game_map[r][c] == 'treasure':
                    treasure_pos = [r, c]
                    break

        result = {'path': path, 'steps': len(path), 'start_position': list(start_pos), 'tile_counts': tile_counts, 'treasure_position': treasure_pos}
        return {'statusCode': 200, 'body': json.dumps(result)}

    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
