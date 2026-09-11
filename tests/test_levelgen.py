""" Procedural level generator, RANDOM LEVELS and LEVEL OF THE DAY modes, editor G key """

import os, json, datetime
from collections import deque
import harness
import pygame

from test_endless import select_menu_item, hiscores_file
from test_savegame import savegame_file, continue_menu, finish_level
from test_editor import open_editor, custom_level_file, read_rows

STAGES = (1, 12, 24, 35)
SEEDS = 200


# independent checks (not using generator's own BFS)

def blocked(rows, col, row):
	""" 2x2 tank at (col, row) hits steel, water, castle or map edge """
	if not (0 <= col <= 24 and 0 <= row <= 24):
		return True
	for x in (col, col + 1):
		for y in (row, row + 1):
			if rows[y][x] in "@~" or (12 <= x <= 13 and 24 <= y <= 25):
				return True
	return False


def tank_bfs(rows, start):
	seen = set()
	if blocked(rows, *start):
		return seen
	seen.add(start)
	queue = deque([start])
	while queue:
		col, row = queue.popleft()
		for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
			p = (col + dx, row + dy)
			if p not in seen and not blocked(rows, *p):
				seen.add(p)
				queue.append(p)
	return seen


FORTRESS = [(11, 23), (11, 24), (11, 25), (14, 23), (14, 24), (14, 25), (12, 23), (13, 23)]
PROTECTED = [(0, 0), (12, 0), (24, 0), (8, 24), (16, 24), (12, 24), (12, 21)]
SPAWNS = [(0, 0), (12, 0), (24, 0)]
STARTS = [(8, 24), (16, 24), (12, 21)]


def check_map(rows, symmetry):
	""" List of problems of generated map """
	problems = []
	if len(rows) != 26 or any(len(row) != 26 for row in rows):
		return ["size"]
	if any(ch not in ".#@~%-" for row in rows for ch in row):
		problems.append("characters")
	for col, row in PROTECTED:
		if any(rows[row + dy][col + dx] != "." for dx in (0, 1) for dy in (0, 1)):
			problems.append("protected %s" % ((col, row),))
	if any(rows[row][col] != "#" for col, row in FORTRESS):
		problems.append("fortress")
	if symmetry in ("mirror", "4way") and any(row != row[::-1] for row in rows):
		problems.append("symmetry")
	fortress = set(FORTRESS)
	for spawn in SPAWNS:
		area = tank_bfs(rows, spawn)
		if not any((c + dx, r + dy) in fortress for c, r in area for dx in (0, 1) for dy in (0, 1)):
			problems.append("spawn %s can't reach castle" % (spawn,))
	for start in STARTS:
		area = tank_bfs(rows, start)
		if any(spawn not in area for spawn in SPAWNS):
			problems.append("start %s can't reach spawns" % (start,))
	# no closed pockets: every cell without steel / water is reachable by a tank
	covered = set()
	for start in SPAWNS + STARTS:
		covered |= set((c + dx, r + dy) for c, r in tank_bfs(rows, start) for dx in (0, 1) for dy in (0, 1))
	for r in range(26):
		for c in range(26):
			if rows[r][c] not in "@~" and (c, r) not in covered and not (12 <= c <= 13 and 24 <= r <= 25):
				problems.append("pocket %s" % ((c, r),))
				break
	return problems


def generator(ctx):
	g = ctx.g
	if ctx.frame != 1:
		return
	levelgen = g["levelgen"]

	ctx.check("same seed gives same map", levelgen.generateLevel(42, 7) == levelgen.generateLevel(42, 7))
	ctx.check("different seeds give different maps", len(set(tuple(levelgen.generateLevel(seed, 7)) for seed in range(20))) >= 19)
	ctx.check("different stages give different maps", levelgen.generateLevel(42, 7) != levelgen.generateLevel(42, 8))

	problems = []
	symmetries = {}
	walls = {}
	hard = {}
	for stage in STAGES:
		walls[stage] = hard[stage] = 0
		for seed in range(SEEDS):
			info = levelgen.generateLevelInfo(seed, stage)
			rows = info["rows"]
			symmetries[info["symmetry"]] = symmetries.get(info["symmetry"], 0) + 1
			for problem in check_map(rows, info["symmetry"]):
				problems.append("seed %d stage %d: %s" % (seed, stage, problem))
			text = "".join(rows)
			walls[stage] += sum(text.count(ch) for ch in "#@~")
			hard[stage] += sum(text.count(ch) for ch in "@~")
	ctx.check("%d maps: protected cells, fortress, symmetry, connectivity, no pockets %s" % (SEEDS * len(STAGES), problems[:5]), not problems)
	ctx.check("mostly mirror symmetry, sometimes other (%s)" % symmetries, symmetries.get("mirror", 0) > SEEDS * len(STAGES) // 2 and len(symmetries) == 3)
	ctx.check("walls grow with stage (%s)" % walls, all(walls[a] < walls[b] for a, b in zip(STAGES, STAGES[1:])))
	ctx.check("steel and water grow with stage (%s)" % hard, all(hard[a] < hard[b] for a, b in zip(STAGES, STAGES[1:])))
	ctx.check("stage 35 still has open space", walls[35] / float(SEEDS) < 26 * 26 * 0.6)

	date = datetime.date(2026, 9, 11)
	ctx.check("daily seed from date", levelgen.dailySeed(date) == 20260911)
	ctx.check("daily seed changes next day", levelgen.dailySeed(datetime.date(2026, 9, 12)) != levelgen.dailySeed(date))
	ctx.check("daily hiscore mode", levelgen.dailyKey(date) == "daily 2026-09-11")
	ctx.finish()


def level_cells(level):
	""" (col, row) -> level character of loaded level """
	chars = {level.TILE_BRICK: "#", level.TILE_STEEL: "@", level.TILE_WATER: "~", level.TILE_GRASS: "%", level.TILE_FROZE: "-"}
	return set((tile.left // 16, tile.top // 16, chars[tile.type]) for tile in level.mapr)


def rows_cells(rows):
	return set((c, r, ch) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != ".")


def random_levels(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	levelgen = g["levelgen"]
	if ctx.frame == 1:
		ctx.check("random levels started", game.mode == "random" and game.level_seed != None and len(g["players"]) == 1)
		d["seed"] = game.level_seed
		rows = levelgen.generateLevel(game.level_seed, 1)
		ctx.check("stage 1 uses generated map", level_cells(game.level) == rows_cells(rows))
		ctx.check("enemies from stage 1 table", len([t for t in game.level.enemies_left if t in (0, 1, 2, 3, 4, 5)]) == 20)
	if ctx.frame == 100:
		finish_level(ctx)
	if ctx.frame > 100 and game.stage == 2 and game.running:
		rows = levelgen.generateLevel(d["seed"], 2)
		ctx.check("stage 2 uses next generated map", level_cells(game.level) == rows_cells(rows) and rows != levelgen.generateLevel(d["seed"], 1))
		with open(savegame_file()) as f:
			data = json.load(f)
		ctx.check("saved game has mode and seed (%s)" % data, data.get("mode") == "random" and data.get("seed") == d["seed"] and data["stage"] == 1)
		ctx.finish()


def write_random_savegame():
	data = {
		"mode": "random", "seed": 12345, "stage": 3, "nr_of_players": 1, "preset": "GOOD",
		"players": [{"score": 800, "lives": 2, "superpowers": 1, "next_extra_life": 20000}],
	}
	with open(savegame_file(), "w") as f:
		json.dump(data, f)


def continue_random(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	rows = g["levelgen"].generateLevel(12345, 4)
	ctx.check("continue: random levels mode with saved seed", game.mode == "random" and game.level_seed == 12345 and game.stage == 4)
	ctx.check("continue: same generated map", level_cells(game.level) == rows_cells(rows))
	ctx.check("continue: score restored", g["players"][0].score == 800)
	ctx.finish()


def daily_menu(ctx):
	if ctx.menu_frame == 1:
		ctx.g["dailyDate"] = lambda: datetime.date(2026, 9, 11)
	return select_menu_item("LEVEL OF THE DAY")(ctx)


def daily(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	levelgen = g["levelgen"]
	phase = d.get("phase", "start")
	if phase == "start":
		date = datetime.date(2026, 9, 11)
		stage = levelgen.dailyStage(date)
		ctx.check("level of the day started with 1 player", game.mode == "daily" and len(g["players"]) == 1)
		ctx.check("seed from (patched) date", game.level_seed == 20260911)
		ctx.check("stage from date (%d)" % game.stage, game.stage == stage and 1 <= stage <= 35)
		ctx.check("generated map of the day", level_cells(game.level) == rows_cells(levelgen.generateLevel(20260911, stage)))
		ctx.check("hiscore key per date and preset", game.hiscoreKey(game.hiscoreMode()) == "daily 2026-09-11 GOOD")
		d["phase"] = "play"
	elif phase == "play" and ctx.frame == 100:
		g["players"][0].score = 700
		finish_level(ctx)
		d["phase"] = "wait_entry"
	elif phase == "wait_entry":
		if ctx.in_function("nextLevel") and game.stage != d.get("stage", game.stage) or (game.running and game.level_time > 60000):
			ctx.check("no next stage after level of the day", False)
			ctx.finish()
		if ctx.in_function("enterName"):
			d["phase"] = "table"
			return [ctx.key(pygame.K_RETURN)]
	elif phase == "table" and ctx.in_function("showHiscores"):
		with open(hiscores_file()) as f:
			tables = json.load(f)
		ctx.check("score in daily table (%s)" % tables, tables.get("daily 2026-09-11 GOOD") == [["AAA", 700]])
		d["phase"] = "menu"
		return [ctx.key(pygame.K_SPACE)]
	elif phase == "menu" and ctx.in_function("showMenu"):
		ctx.check("back to menu after level of the day", not ctx.in_function("nextLevel"))
		ctx.check("level of the day doesn't save game", not os.path.isfile(savegame_file()))
		ctx.finish()


def menu_fits(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	items = game.menuItems()
	labels = [item[0] for item in items]
	ctx.check("new items after ENDLESS 2P, before VERSUS (%s)" % labels,
		labels.index("RANDOM LEVELS") == labels.index("ENDLESS 2P") + 1 and labels.index("LEVEL OF THE DAY") + 1 == labels.index("VERSUS"))
	ctx.check("CONTINUE still 4th item", labels[3] == "CONTINUE")
	visible = True
	for i in range(len(items)):
		game.menu_index = i
		game.drawIntroScreen()
		first = game.menu_first
		if not (0 <= i - first < game.MENU_VISIBLE_ITEMS and 228 + (i - first) * 20 + 16 <= 416):
			visible = False
	ctx.check("every selected item is on screen (%d items)" % len(items), visible)
	ctx.check("drawn rows fit screen", 228 + (game.MENU_VISIBLE_ITEMS - 1) * 20 + 16 <= 416)
	for language in ("EN", "RU"):
		g["LANGUAGE"] = language
		widths = [game.text(label, False, (255, 255, 255)).get_width() for label in labels]
		ctx.check("%s labels fit screen width (%s)" % (language, max(widths)), 165 + max(widths) <= 480)
		title = game.text(g["lang"].tr("LEVEL OF THE DAY"), False, (0, 0, 0), False)
		ctx.check("%s stage screen title fits (%d)" % (language, title.get_width()), title.get_width() <= 416)
		game.showHiscores("daily 2026-09-11", 20)
		game.showHiscores("random", 20)
	g["LANGUAGE"] = "EN"
	ctx.check("RU translations", g["lang"].PHRASES["RANDOM LEVELS"] == u"СЛУЧАЙНЫЕ УРОВНИ" and g["lang"].PHRASES["LEVEL OF THE DAY"] == u"УРОВЕНЬ ДНЯ")
	ctx.finish()


def write_campaign_savegame():
	with open(savegame_file(), "w") as f:
		json.dump({"stage": 1, "nr_of_players": 1, "preset": "GOOD", "players": [{"score": 0, "lives": 3, "superpowers": 1}]}, f)


def editor_menu(ctx):
	events = open_editor(ctx)
	if events != None:
		return events
	f = ctx.menu_frame
	if f == 5:
		return [ctx.key(pygame.K_g)]
	if f == 7:
		return [ctx.key(pygame.K_t)]
	return []


def editor_generate(ctx):
	if ctx.frame != 1:
		return
	rows = read_rows(1)
	with open(os.path.join(harness.GAME_DIR, "levels", "1")) as f:
		original = f.read().split("\n")[:26]
	ctx.check("G fills level with generated map", rows != original)
	ctx.check("generated map is valid (%s)" % check_map(rows, None), not check_map(rows, None))
	ctx.check("test play uses it", level_cells(ctx.game.level) >= set(c for c in rows_cells(rows) if c[2] != "#"))
	ctx.finish()


SCENARIOS = {
	"generator": {"fn": generator},
	"random_levels": {"fn": random_levels, "menu": select_menu_item("RANDOM LEVELS")},
	"continue_random": {"fn": continue_random, "menu": continue_menu, "setup": write_random_savegame},
	"daily": {"fn": daily, "menu": daily_menu, "max_frames": 20000},
	"menu_fits": {"fn": menu_fits, "setup": write_campaign_savegame},
	"editor_generate": {"fn": editor_generate, "menu": editor_menu},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
