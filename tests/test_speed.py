""" Tank speeds like on NES: player 0.75, fast enemy 1, other enemies 0.5 NES px per NES frame
(converted for selected NES version: DENDY 50 fps or NTSC 60 fps) """

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
		expected = FRAMES * 0.75 * g["NES_PX_PER_FRAME"]
		ctx.check("default NES version is NTSC (60 fps, like the original NES)", g["NES_VERSION"] == "NTSC")
		ctx.check("player speed 1.5 px per frame (%.2f)" % g["PLAYER_DEFAULT_SPEED"], abs(g["PLAYER_DEFAULT_SPEED"] - 1.5) < 0.01)
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
	# random pause on grid would make distances random
	g["ENEMY_GRID_PAUSE_CHANCE"] = 0
	Enemy = g["Enemy"]

	slow = FRAMES * 0.5 * g["NES_PX_PER_FRAME"]
	basic = enemy_distance(ctx, Enemy.TYPE_BASIC)
	fast = enemy_distance(ctx, Enemy.TYPE_FAST)
	power = enemy_distance(ctx, Enemy.TYPE_POWER)
	armor = enemy_distance(ctx, Enemy.TYPE_ARMOR)

	ctx.check("basic tank: %d px in %d frames (expected %d)" % (basic, FRAMES, slow), abs(basic - slow) <= 2)
	ctx.check("fast tank: %d px in %d frames (expected %d)" % (fast, FRAMES, 2 * slow), abs(fast - 2 * slow) <= 2)
	ctx.check("power and armor tanks as slow as basic (%d, %d)" % (power, armor), abs(power - basic) <= 1 and abs(armor - basic) <= 1)
	ctx.check("fast tank is 2x faster than basic, like on NES", abs(float(fast) / basic - 2) < 0.1)
	ctx.check("player is 1.5x faster than basic, like on NES", abs(g["PLAYER_DEFAULT_SPEED"] / g["DEFAULT_ENEMY_SPEED"] - 1.5) < 0.01)
	ctx.finish()


def grid_pause(ctx):
	""" Enemy on grid sometimes pauses: a bit slower on average, never faster """
	g = ctx.g
	if ctx.frame != 5:
		return
	del g["enemies"][:]
	g["ENEMY_GRID_PAUSE_CHANCE"] = 1.0
	distance = enemy_distance(ctx, g["Enemy"].TYPE_BASIC)
	ctx.check("enemy on grid always pausing doesn't move (%d px)" % distance, distance == 0)
	ctx.finish()


def nes_version_switch(ctx):
	g = ctx.g
	if ctx.frame != 1:
		return
	# one game frame is one NES frame: speeds per frame are the same, the console changes the frame rate
	g["applyNesVersion"]("NTSC")
	ctx.check("NTSC: game runs 60 frames per second", g["GAME_FRAME_TIMING"] == 60 and g["NES_FPS"] == 60)
	ctx.check("NTSC: player 1.5, fast enemy 2, bullet 4 px per frame",
		abs(g["PLAYER_DEFAULT_SPEED"] - 1.5) < 0.01 and abs(g["DEFAULT_ENEMY_SPEED"] + g["DEFAULT_ENEMY_SPEED_FAST"] - 2.0) < 0.01 and abs(g["DEFAULT_BULLET_SPEED"] - 4) < 0.01)
	ctx.check("NTSC: helmet 10.7 s", g["BONUS_PLAYER_SHIELD_TIMEOUT"] == 10667)
	g["applyNesVersion"]("DENDY")
	ctx.check("DENDY: game runs 50 frames per second", g["GAME_FRAME_TIMING"] == 50 and g["NES_FPS"] == 50)
	ctx.check("DENDY: same speeds per frame, so everything is 1.2x slower in a second",
		abs(g["PLAYER_DEFAULT_SPEED"] - 1.5) < 0.01 and abs(g["DEFAULT_ENEMY_SPEED"] + g["DEFAULT_ENEMY_SPEED_FAST"] - 2.0) < 0.01 and abs(g["DEFAULT_BULLET_SPEED"] - 4) < 0.01)
	ctx.check("DENDY: helmet 12.8 s", g["BONUS_PLAYER_SHIELD_TIMEOUT"] == 12800)
	g["applyPreset"]("NES+")
	ctx.check("preset doesn't reset NES speeds", abs(g["DEFAULT_ENEMY_SPEED_FAST"] - 1.0) < 0.01)
	ctx.finish()


def frame_clock(ctx):
	""" The game really runs 50 frames per second (pygame's Clock.tick oversleeps on macOS, which made
	everything slower than on NES); a late frame is caught up by the next ones """
	import time
	from battlecity.frameclock import FrameClock
	clock = FrameClock(real=True)
	clock.tick(50)
	start = time.perf_counter()
	for i in range(100):
		busy = time.perf_counter()
		while time.perf_counter() - busy < (0.035 if i == 50 else 0.004):
			pass
		clock.tick(50)
	period = (time.perf_counter() - start) * 1000 / 100
	ctx.check("frame clock keeps 20 ms per frame (%.2f ms), a 35 ms frame is caught up" % period, abs(period - 20) < 0.6)
	ctx.finish()


SCENARIOS = {
	"player_speed": {"fn": player_speed},
	"enemy_speeds": {"fn": enemy_speeds},
	"grid_pause": {"fn": grid_pause},
	"nes_version_switch": {"fn": nes_version_switch},
	"frame_clock": {"fn": frame_clock},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
