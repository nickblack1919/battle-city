""" Tank speeds like on NES: player 0.75, fast enemy 1, other enemies 0.5 NES px per NES frame """

import harness


FRAMES = 50


def player_speed(ctx):
	g, d = ctx.g, ctx.data
	p = g["players"][0]
	if ctx.frame == 5:
		del ctx.game.level.enemies_left[:]
		del g["enemies"][:]
		p.shielded = True
		d["x"] = p.rect.left
		# level 1, row 24: free to the left of player 1
		p.pressed = [False, False, False, True]
	if ctx.frame == 5 + FRAMES:
		p.pressed = [False] * 4
		distance = d["x"] - p.rect.left
		expected = FRAMES * g["PLAYER_DEFAULT_SPEED"]
		ctx.check("player speed %.1f px per frame" % g["PLAYER_DEFAULT_SPEED"], abs(g["PLAYER_DEFAULT_SPEED"] - 1.8) < 0.01)
		ctx.check("player moved %d px in %d frames (expected %d)" % (distance, FRAMES, expected), abs(distance - expected) <= 2)
		ctx.finish()


def enemy_distance(ctx, enemy_type):
	""" Enemy drives down along column 0 of level 1 for FRAMES frames """
	g, game = ctx.g, ctx.game
	Enemy = g["Enemy"]
	game.level.enemies_left[:] = [enemy_type]
	enemy = Enemy(game.level, 1, [0, 0])
	enemy.state = enemy.STATE_ALIVE
	enemy.aquired_position = True
	enemy.rotate(enemy.DIR_DOWN, False)
	enemy.path = [[0, y] for y in range(1, 200)]
	for frame in range(FRAMES):
		enemy.move()
	return enemy.rect.top


def enemy_speeds(ctx):
	g = ctx.g
	if ctx.frame != 5:
		return
	del g["enemies"][:]
	for player in g["players"]:
		player.rect.topleft = [384, 384]
	Enemy = g["Enemy"]

	basic = enemy_distance(ctx, Enemy.TYPE_BASIC)
	fast = enemy_distance(ctx, Enemy.TYPE_FAST)
	power = enemy_distance(ctx, Enemy.TYPE_POWER)
	armor = enemy_distance(ctx, Enemy.TYPE_ARMOR)

	ctx.check("basic tank: %d px in %d frames (expected 60)" % (basic, FRAMES), abs(basic - 60) <= 2)
	ctx.check("fast tank: %d px in %d frames (expected 120)" % (fast, FRAMES), abs(fast - 120) <= 2)
	ctx.check("power and armor tanks as slow as basic (%d, %d)" % (power, armor), abs(power - basic) <= 1 and abs(armor - basic) <= 1)
	ctx.check("fast tank is 2x faster than basic, like on NES", abs(float(fast) / basic - 2) < 0.1)
	ctx.check("player is 1.5x faster than basic, like on NES", abs(g["PLAYER_DEFAULT_SPEED"] / g["DEFAULT_ENEMY_SPEED"] - 1.5) < 0.01)
	ctx.finish()


SCENARIOS = {
	"player_speed": {"fn": player_speed},
	"enemy_speeds": {"fn": enemy_speeds},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
