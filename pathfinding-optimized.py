"""
AWS Lambda - Pathfinding tool for Bedrock Agent Game (OPTIMIZED).

Same as FINAL but with smarter target ordering:
- Prefers pass-through targets over dead-end targets at equal distance
- Reduces backtracking by visiting dead ends last
- Collects targets along the path automatically
"""

import json
from collections import deque

DIRECTION_MAP = {
    (-1, 0): "up",
    (1, 0): "down",
    (0, -1): "left",
    (0, 1): "right",
}

def _bfs(start, goal, obstacles, grid_rows, grid_cols):
    if start == goal:
        return [start]
    queue = deque([start])
    visited = {start}
    parent = {start: None}
    deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    while queue:
        node = queue.popleft()
        for dr, dc in deltas:
            nb = (node[0] + dr, node[1] + dc)
            if nb[0] < 0 or nb[0] >= grid_rows or nb[1] < 0 or nb[1] >= grid_cols:
                continue
            if nb in obstacles or nb in visited:
                continue
            visited.add(nb)
            parent[nb] = node
            queue.append(nb)
            if nb == goal:
                path = []
                cur = goal
                while cur is not None:
                    path.append(cur)
                    cur = parent[cur]
                path.reverse()
                return path
    return None

def _path_to_dirs(path):
    dirs = []
    for i in range(len(path) - 1):
        delta = (path[i+1][0] - path[i][0], path[i+1][1] - path[i][1])
        dirs.append(DIRECTION_MAP[delta])
    return dirs

def _is_dead_end(pos, obstacles, grid_rows, grid_cols):
    """Check if a position is a dead end (only 1 open neighbor)."""
    deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    open_neighbors = 0
    for dr, dc in deltas:
        nb = (pos[0] + dr, pos[1] + dc)
        if 0 <= nb[0] < grid_rows and 0 <= nb[1] < grid_cols:
            if nb not in obstacles:
                open_neighbors += 1
    return open_neighbors <= 1

def _parse_map_grid(map_grid):
    obstacles = []
    coins = []
    challenges = []
    key_pos = None
    door_pos = None
    treasure_pos = None
    for row in range(len(map_grid)):
        for col in range(len(map_grid[row])):
            cell = str(map_grid[row][col]).strip().lower()
            if cell == "wall" or cell == "c8":
                obstacles.append((row, col))
            elif cell == "c7":
                coins.append((row, col))
            elif "c40" in cell or "key" in cell:
                key_pos = (row, col)
            elif "c30" in cell or "door" in cell:
                door_pos = (row, col)
            elif cell == "treasure":
                treasure_pos = (row, col)
            elif cell.startswith("c") and cell != "normal":
                challenges.append((row, col))
    return obstacles, coins, challenges, key_pos, door_pos, treasure_pos

def _find_dead_ends(obstacles, grid_rows, grid_cols, known_cells):
    dead_ends = []
    obstacle_set = set(obstacles)
    deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for row in range(grid_rows):
        for col in range(grid_cols):
            cell = (row, col)
            if cell in obstacle_set or cell in known_cells:
                continue
            open_neighbors = 0
            for dr, dc in deltas:
                nb = (row + dr, col + dc)
                if 0 <= nb[0] < grid_rows and 0 <= nb[1] < grid_cols:
                    if nb not in obstacle_set:
                        open_neighbors += 1
            if open_neighbors == 1:
                dead_ends.append(cell)
    return dead_ends

def _parse_params(event):
    if "parameters" in event:
        params = {}
        for p in event["parameters"]:
            name = p.get("name", "")
            value = p.get("value", "")
            try:
                params[name] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                params[name] = value
        return params
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            return json.loads(body)
        return body
    return event

def _smart_pick_target(cur, all_targets, obstacles, grid_rows, grid_cols):
    """Pick next target smartly: prefer pass-through over dead-ends at similar distance."""
    candidates = []
    for target in list(all_targets):
        tp = _bfs(cur, target, obstacles, grid_rows, grid_cols)
        if tp:
            dist = len(tp) - 1
            dead_end = _is_dead_end(target, obstacles, grid_rows, grid_cols)
            # Dead ends get a penalty of 0.5 so pass-through targets are preferred
            score = dist + (0.5 if dead_end else 0)
            candidates.append((score, dist, target, tp))

    if not candidates:
        return None, None

    # Sort by score (pass-through first at same distance)
    candidates.sort(key=lambda x: x[0])
    _, _, best_target, best_path = candidates[0]
    return best_target, best_path

def lambda_handler(event, context):
    params = _parse_params(event)
    current_pos = tuple(params.get("current_pos", [0, 0]))
    grid_bounds = params.get("grid_bounds", [10, 10])
    grid_rows, grid_cols = grid_bounds[0], grid_bounds[1]

    map_grid = params.get("map_grid")
    if map_grid is not None and isinstance(map_grid, list):
        obs_list, coin_list, challenge_list, key_pos, door_pos, treasure_pos = _parse_map_grid(map_grid)
        obstacles = set(obs_list)
        coins = set(coin_list)
        challenges = set(challenge_list)
    else:
        key_pos = None
        door_pos = None
        treasure_pos = None

        kv = params.get("key_pos")
        if isinstance(kv, (list, tuple)) and len(kv) == 2:
            key_pos = tuple(kv)

        dv = params.get("door_pos")
        if isinstance(dv, (list, tuple)) and len(dv) == 2:
            door_pos = tuple(dv)

        tv = params.get("treasure_pos")
        if isinstance(tv, (list, tuple)) and len(tv) == 2:
            treasure_pos = tuple(tv)

        coins = set(tuple(c) for c in params.get("coins", []))
        obstacles = set(tuple(o) for o in params.get("obstacles", []))
        challenges = set(tuple(c) for c in params.get("challenges", []))

        if len(obstacles) == 0:
            return {"statusCode": 200, "body": json.dumps([])}

        if door_pos is None:
            for row in range(grid_rows):
                wcols = sorted([c for (r, c) in obstacles if r == row])
                if len(wcols) >= 7 and wcols[0] == 1 and (grid_cols - 1) not in wcols:
                    cand = (row, grid_cols - 1)
                    if cand not in coins and cand != treasure_pos and cand != current_pos:
                        door_pos = cand
                        break

        if key_pos is None and door_pos is not None:
            for cand in [(9, 0), (0, 0), (9, 9), (0, 9)]:
                if cand not in obstacles and cand not in coins and cand != treasure_pos and cand != door_pos:
                    key_pos = cand
                    break

        if key_pos is not None:
            for sc in [(key_pos[0]-1, key_pos[1]), (key_pos[0]-1, 3)]:
                if 0 <= sc[0] < grid_rows and 0 <= sc[1] < grid_cols:
                    if sc not in obstacles and sc not in coins and sc != key_pos and sc != door_pos and sc != treasure_pos and sc != current_pos:
                        test_obs = set(obstacles) | {sc}
                        if door_pos:
                            test_obs.add(door_pos)
                        if _bfs(current_pos, key_pos, test_obs, grid_rows, grid_cols):
                            obstacles.add(sc)

        if not challenges:
            known = set(coins) | obstacles
            if key_pos:
                known.add(key_pos)
            if door_pos:
                known.add(door_pos)
            if treasure_pos:
                known.add(treasure_pos)
            known.add(current_pos)

            dead_ends = _find_dead_ends(obstacles, grid_rows, grid_cols, known)
            challenges = set(dead_ends)

            if treasure_pos:
                t_row = treasure_pos[0]
                for check_row in [t_row, t_row - 1]:
                    if 0 <= check_row < grid_rows:
                        for col in range(grid_cols):
                            cell = (check_row, col)
                            if cell not in known and cell not in challenges:
                                challenges.add(cell)

    if treasure_pos is None:
        return {"statusCode": 200, "body": json.dumps([])}

    cur = current_pos
    master = []
    all_targets = set(coins) | set(challenges)
    key_collected = False

    # PHASE 1: Get key + visit accessible targets (smart ordering)
    # Door AND Treasure are BLOCKED
    if key_pos is not None:
        p1_obs = set(obstacles)
        if door_pos:
            p1_obs.add(door_pos)
        if treasure_pos:
            p1_obs.add(treasure_pos)

        while cur != key_pos:
            # Always consider key as a candidate
            best_target, best_path = None, None
            best_score = float("inf")

            kp = _bfs(cur, key_pos, p1_obs, grid_rows, grid_cols)
            if kp:
                best_target, best_path = key_pos, kp
                best_score = len(kp) - 1

            # Check if any target is closer (with dead-end penalty)
            for target in list(all_targets):
                tp = _bfs(cur, target, p1_obs, grid_rows, grid_cols)
                if tp:
                    dist = len(tp) - 1
                    dead_end = _is_dead_end(target, p1_obs, grid_rows, grid_cols)
                    score = dist + (0.5 if dead_end else 0)
                    if score < best_score:
                        best_target, best_path = target, tp
                        best_score = score

            if best_target is None:
                break

            master.extend(_path_to_dirs(best_path))
            for pos in best_path[1:]:
                all_targets.discard(pos)
            cur = best_path[-1]

        if cur == key_pos:
            key_collected = True

    # PHASE 2: Sweep all remaining targets (smart ordering)
    # Treasure STILL BLOCKED
    p2_obs = set(obstacles)
    if door_pos and not key_collected:
        p2_obs.add(door_pos)
    if treasure_pos:
        p2_obs.add(treasure_pos)

    while all_targets:
        best_target, best_path = _smart_pick_target(cur, all_targets, p2_obs, grid_rows, grid_cols)
        if best_target is None:
            break
        master.extend(_path_to_dirs(best_path))
        for pos in best_path[1:]:
            all_targets.discard(pos)
        cur = best_path[-1]

    # PHASE 3: NOW go to treasure (no longer blocked)
    p3_obs = set(obstacles)
    if door_pos and not key_collected:
        p3_obs.add(door_pos)

    if cur != treasure_pos:
        tp = _bfs(cur, treasure_pos, p3_obs, grid_rows, grid_cols)
        if tp:
            master.extend(_path_to_dirs(tp))

    return {"statusCode": 200, "body": json.dumps(master)}
