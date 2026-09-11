""" NES enemy AI setting: goals by time since stage start, blocked tank behavior, settings """

import json
import harness


def make_enemy(ctx, position):
	g, game = ctx.g, ctx.game
	Enemy = g["Enemy"]
	game.level.enemies_left[:] = [0]
	enemy = Enemy(game.level, 1, position)
	del game.level.enemies_left[:]
	enemy.state = enemy.STATE_ALIVE
	enemy.aquired_position = True
	return enemy


def goals(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	g["ENEMY_AI"] = "NES"
	# NES spawn interval formula
	g["ENEMY_SPAWN_TIMEOUT"] = None
	del g["enemies"][:]
	Enemy = g["Enemy"]
	enemy = make_enemy(ctx, [0, 0])
	g["enemies"].append(enemy)
	p = g["players"][0]
	p.rect.topleft = [384, 0]
	# stage 1, 1 player: interval 187 NES frames -> random up to 23 ticks, chase up to 46 ticks
	tick = g["nesFrames"](64)

	game.level_time = 0
	seen = set()
	for i in range(200):
		enemy.chooseNesGoal()
		seen.add(enemy.direction)
	ctx.check("stage start: random directions (%s)" % seen, len(seen) == 4)

	game.level_time = 30 * tick
	seen = set()
	for i in range(100):
		enemy.chooseNesGoal()
		seen.add(enemy.direction)
	ctx.check("later: chase player on the right (%s)" % seen, seen == {Enemy.DIR_RIGHT})

	game.level_time = 100 * tick
	seen = set()
	for i in range(100):
		enemy.chooseNesGoal()
		seen.add(enemy.direction)
	ctx.check("at last: go to castle down right (%s)" % seen, seen == {Enemy.DIR_RIGHT, Enemy.DIR_DOWN})
	ctx.finish()


def blocked(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	g["ENEMY_AI"] = "NES"
	del g["enemies"][:]
	Enemy = g["Enemy"]
	enemy = make_enemy(ctx, [0, 0])
	g["enemies"].append(enemy)
	waits = turns = 0
	for i in range(400):
		enemy.rect.topleft = [0, 0]
		enemy.rotate(Enemy.DIR_UP, False)
		enemy.nes_wait = 0
		enemy.nes_turn = False
		enemy.moveStepNes()
		if enemy.nes_wait == 2:
			waits += 1
		elif enemy.nes_turn:
			turns += 1
	# on grid 1/16 of moves choose new goal instead
	ctx.check("blocked by screen edge: waits about 3/4 (%d), turns about 1/4 (%d)" % (waits, turns),
		waits + turns >= 340 and 0.65 <= waits / float(waits + turns) <= 0.85)

	# not aligned to grid: turns around
	turned_around = False
	for i in range(100):
		enemy.rect.topleft = [2, 0]
		enemy.rotate(Enemy.DIR_UP, False)
		enemy.nes_wait = 0
		enemy.moveStepNes()
		if enemy.direction == Enemy.DIR_DOWN:
			turned_around = True
	ctx.check("blocked off grid: sometimes turns around", turned_around)
	ctx.finish()


def playing(ctx):
	""" Enemies with NES AI drive over the map without entering walls """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		g["ENEMY_AI"] = "NES"
		for p in g["players"]:
			p.shielded = True
		d["start"] = {}
		d["moved"] = set()
		d["in_wall"] = 0
	for p in g["players"]:
		p.shielded = True
	g["castle"].active = True
	for enemy in g["enemies"]:
		if enemy.state != enemy.STATE_ALIVE:
			continue
		start = d["start"].setdefault(id(enemy), enemy.rect.topleft)
		if abs(enemy.rect.left - start[0]) + abs(enemy.rect.top - start[1]) > 64:
			d["moved"].add(id(enemy))
		if enemy.aquired_position and enemy.rect.collidelist(game.level.obstacleRectsFor(enemy.canSwim())) != -1:
			d["in_wall"] += 1
	if ctx.frame == 1200:
		ctx.check("enemies drive (%d moved far)" % len(d["moved"]), len(d["moved"]) >= 2)
		ctx.check("no enemy inside walls (%d)" % d["in_wall"], d["in_wall"] == 0)
		ctx.finish()


def setting(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	labels = [item["label"] for item in game.settingsItems()]
	ctx.check("ENEMY AI on settings screen", "ENEMY AI" in labels)
	ctx.check("CLASSIC AI by default", g["ENEMY_AI"] == "CLASSIC")
	game.changeSetting("ai", 1)
	ctx.check("changed to NES", g["ENEMY_AI"] == "NES")
	with open(g["dataFile"](g["SETTINGS_FILE"])) as f:
		ctx.check("saved in settings", json.load(f).get("enemy_ai") == "NES")
	g["ENEMY_AI"] = "CLASSIC"
	g["loadSettings"]()
	ctx.check("loaded from settings", g["ENEMY_AI"] == "NES")
	ctx.finish()


SCENARIOS = {
	"goals": {"fn": goals},
	"blocked": {"fn": blocked},
	"playing": {"fn": playing},
	"setting": {"fn": setting},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
