# coding=utf-8
""" Battle City: procedural level generator and level of the day

Map is 26 x 26 cells, structures are made of 2x2 cell blocks (13 x 13 block grid), so tanks (2x2 cells)
fit between them. Level looks like original ones: usually left-right mirror symmetry, brick walls,
steel pieces, water pools, grass patches and ice fields. Stage (1..35) makes map denser, with more steel
and water. Generated map is checked with BFS over 2x2 tank positions (steel and water block, bricks
can be shot): enemy spawns reach the castle, player starts reach every enemy spawn. Failed map is
generated again from (seed, stage, attempt), so result depends only on seed and stage.
"""

import datetime, random
from collections import deque

SIZE = 26
BLOCKS = 13

# 2x2 cell areas which stay free: enemy spawns, players' starts, castle, third player's start
PROTECTED = [(0, 0), (12, 0), (24, 0), (8, 24), (16, 24), (12, 24), (12, 21)]
ENEMY_SPAWNS = [(0, 0), (12, 0), (24, 0)]
PLAYER_STARTS = [(8, 24), (16, 24), (12, 21)]
CASTLE = (12, 24)

# fortress bricks around the castle (like original levels and Level.buildFortress)
FORTRESS = [(11, 23), (11, 24), (11, 25), (14, 23), (14, 24), (14, 25), (12, 23), (13, 23)]

# cells kept empty around the fortress (fortress row 23 isn't on 2-cell grid)
FORTRESS_AREA = [(col, row) for col in range(10, 16) for row in range(20, 26)]

BLOCKING = "@~"

MAX_ATTEMPTS = 60

# shapes on block grid: list of (block column, block row)
SHAPES = [
	[(0, 0)],
	[(0, 0), (0, 1)],
	[(0, 0), (0, 1), (0, 2)],
	[(0, 0), (0, 1), (0, 2), (0, 3)],
	[(0, 0), (1, 0)],
	[(0, 0), (1, 0), (2, 0)],
	[(0, 0), (1, 0), (0, 1), (1, 1)],
	[(0, 0), (0, 1), (1, 1)],
	[(0, 0), (1, 0), (2, 0), (1, 1)],
	[(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)],
	[(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)],
]


def dailyDate():
	""" Today's local date (tests replace this function) """
	return datetime.date.today()


def dailySeed(date = None):
	""" Seed of level of the day: YYYYMMDD """
	date = date or dailyDate()
	return int(date.strftime("%Y%m%d"))


def dailyStage(date = None):
	""" Stage number (difficulty) of level of the day """
	return random.Random(dailySeed(date)).randint(5, 30)


def dailyKey(date = None):
	""" Hiscore mode name of level of the day, e.g. "daily 2026-09-11" """
	date = date or dailyDate()
	return "daily " + date.strftime("%Y-%m-%d")


def generateLevel(seed, stage):
	""" Level rows (26 strings, same format as level files) for seed and stage """
	return generateLevelInfo(seed, stage)["rows"]


def generateLevelInfo(seed, stage):
	""" Generated level with details: rows, symmetry ("mirror", "4way", "none"), attempt """
	stage = max(1, min(35, int(stage)))
	for attempt in range(MAX_ATTEMPTS):
		rng = random.Random("battlecity-%s-%d-%d" % (seed, stage, attempt))
		grid, symmetry = buildMap(rng, stage)
		if isPlayable(grid):
			fillPockets(grid)
			return {"rows": ["".join(row) for row in grid], "symmetry": symmetry, "attempt": attempt}
	# fallback: same map without steel and water is always connected
	rng = random.Random("battlecity-%s-%d-fallback" % (seed, stage))
	grid, symmetry = buildMap(rng, stage, allow_blocking = False)
	return {"rows": ["".join(row) for row in grid], "symmetry": symmetry, "attempt": MAX_ATTEMPTS}


def stageParams(stage):
	""" Difficulty grows with stage: share of blocks with walls, steel and water probabilities """
	t = (stage - 1) / 34.0
	return {
		"density": 0.26 + 0.18 * t,
		"steel": 0.06 + 0.20 * t,
		"water": 0.04 + 0.14 * t,
		"grass_patches": 1 + int(3 * t),
		"ice_fields": 0 if stage < 4 else 1 + int(2 * t),
	}


def buildMap(rng, stage, allow_blocking = True):
	params = stageParams(stage)
	roll = rng.random()
	symmetry = "mirror" if roll < 0.8 else ("4way" if roll < 0.92 else "none")

	# block grid: None - empty, otherwise level character
	blocks = [[None] * BLOCKS for i in range(BLOCKS)]
	# block width generated before mirroring
	width = BLOCKS if symmetry == "none" else 7
	height = 7 if symmetry == "4way" else BLOCKS

	reserved = set()
	for col, row in PROTECTED + FORTRESS_AREA:
		reserved.add((col // 2, row // 2))
		reserved.add(((col + 1) // 2, (row + 1) // 2))

	def mirrored(bx, by):
		positions = set([(bx, by)])
		if symmetry != "none":
			positions |= set([(BLOCKS - 1 - x, y) for x, y in positions])
		if symmetry == "4way":
			positions |= set([(x, BLOCKS - 1 - y) for x, y in positions])
		return positions

	# walls
	total = BLOCKS * BLOCKS
	target = int(total * params["density"])
	filled = 0
	tries = 0
	while filled < target and tries < 400:
		tries += 1
		shape = rng.choice(SHAPES)
		if rng.random() < 0.5:
			shape = [(y, x) for x, y in shape]
		ox, oy = rng.randrange(width), rng.randrange(height)
		roll = rng.random()
		if allow_blocking and roll < params["steel"]:
			tile = "@"
		elif allow_blocking and roll < params["steel"] + params["water"]:
			tile = "~"
		else:
			tile = "#"
		cells = set()
		for dx, dy in shape:
			bx, by = ox + dx, oy + dy
			if bx >= BLOCKS or by >= BLOCKS:
				continue
			cells |= mirrored(bx, by)
		cells = [c for c in cells if c not in reserved and blocks[c[1]][c[0]] == None]
		for bx, by in cells:
			blocks[by][bx] = tile
			filled += 1

	# grass patches and ice fields on free blocks
	for tile, count, size in (("%", params["grass_patches"], 3), ("-", params["ice_fields"], 4)):
		for i in range(count):
			ox, oy = rng.randrange(width), rng.randrange(1, height)
			w, h = rng.randint(1, size), rng.randint(1, size)
			for bx in range(ox, min(ox + w, BLOCKS)):
				for by in range(oy, min(oy + h, BLOCKS)):
					for x, y in mirrored(bx, by):
						if (x, y) not in reserved and blocks[y][x] == None:
							blocks[y][x] = tile

	# cells
	grid = [["."] * SIZE for i in range(SIZE)]
	for by in range(BLOCKS):
		for bx in range(BLOCKS):
			tile = blocks[by][bx]
			if tile == None:
				continue
			pattern = [(0, 0), (1, 0), (0, 1), (1, 1)]
			# thin brick walls like on original maps: half of the block
			if tile == "#" and rng.random() < 0.18:
				pattern = rng.choice([[(0, 0), (1, 0)], [(0, 1), (1, 1)], [(0, 0), (0, 1)], [(1, 0), (1, 1)]])
			for dx, dy in pattern:
				grid[by * 2 + dy][bx * 2 + dx] = tile

	# thin patterns can break symmetry: copy generated half again
	if symmetry != "none":
		for row in grid:
			for col in range(SIZE // 2):
				row[SIZE - 1 - col] = row[col]
	if symmetry == "4way":
		for row in range(SIZE // 2):
			grid[SIZE - 1 - row] = list(grid[row])

	# protected areas and fortress
	for col, row in PROTECTED:
		for dx in (0, 1):
			for dy in (0, 1):
				grid[row + dy][col + dx] = "."
	for col, row in FORTRESS_AREA:
		grid[row][col] = "."
	for col, row in FORTRESS:
		grid[row][col] = "#"

	return grid, symmetry


def passable(grid, col, row):
	""" 2x2 tank with top left cell (col, row) can be there: no steel, water or castle """
	if not (0 <= col <= SIZE - 2 and 0 <= row <= SIZE - 2):
		return False
	for dx in (0, 1):
		for dy in (0, 1):
			x, y = col + dx, row + dy
			if grid[y][x] in BLOCKING:
				return False
			if CASTLE[0] <= x < CASTLE[0] + 2 and CASTLE[1] <= y < CASTLE[1] + 2:
				return False
	return True


def reachable(grid, starts):
	""" Tank positions reachable from start positions (moving cell by cell, bricks can be shot) """
	seen = set([start for start in starts if passable(grid, *start)])
	queue = deque(seen)
	while queue:
		col, row = queue.popleft()
		for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
			position = (col + dx, row + dy)
			if position not in seen and passable(grid, *position):
				seen.add(position)
				queue.append(position)
	return seen


def castleGoals(grid):
	""" Tank positions touching the fortress: next to the castle """
	fortress = set(FORTRESS)
	goals = set()
	for col in range(SIZE - 1):
		for row in range(SIZE - 1):
			if passable(grid, col, row) and any([(col + dx, row + dy) in fortress for dx in (0, 1) for dy in (0, 1)]):
				goals.add((col, row))
	return goals


def isPlayable(grid):
	""" Every enemy spawn reaches the castle, every player start reaches every enemy spawn """
	goals = castleGoals(grid)
	for spawn in ENEMY_SPAWNS:
		if not reachable(grid, [spawn]) & goals:
			return False
	for start in PLAYER_STARTS:
		area = reachable(grid, [start])
		if any([spawn not in area for spawn in ENEMY_SPAWNS]):
			return False
	return True


def coveredCells(grid, positions):
	return set([(col + dx, row + dy) for col, row in positions for dx in (0, 1) for dy in (0, 1)])


def fillPockets(grid):
	""" Cells no tank can reach (closed by steel / water) become steel or water like walls around them """
	covered = coveredCells(grid, reachable(grid, ENEMY_SPAWNS + PLAYER_STARTS))
	castle = [(CASTLE[0] + dx, CASTLE[1] + dy) for dx in (0, 1) for dy in (0, 1)]
	# decide all cells from unchanged map first, so filling keeps symmetry
	fills = []
	for row in range(SIZE):
		for col in range(SIZE):
			if grid[row][col] in BLOCKING or (col, row) in covered or (col, row) in castle:
				continue
			around = [grid[y][x] for x, y in ((col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)) if 0 <= x < SIZE and 0 <= y < SIZE]
			fills.append((col, row, "~" if around.count("~") > around.count("@") else "@"))
	for col, row, tile in fills:
		grid[row][col] = tile
