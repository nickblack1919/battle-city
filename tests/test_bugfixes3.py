""" Fixes: turn next to a tank snaps to grid, stun and freeze don't cancel each other,
preset of continued game isn't kept, debug keys are off in normal game """

import pygame
import harness
from test_savegame import write_savegame, continue_menu


def clear_enemies(ctx):
	del ctx.game.level.enemies_left[:]
	del ctx.g["enemies"][:]
	for p in ctx.g["players"]:
		p.shielded = True


def snap_next_to_tank(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	clear_enemies(ctx)
	game.level.mapr = []
	game.level.updateObstacleRects()
	Enemy = g["Enemy"]
	game.level.enemies_left[:] = [Enemy.TYPE_BASIC]
	enemy = Enemy(game.level, 1, [76, 200])
	del game.level.enemies_left[:]
	enemy.state = enemy.STATE_ALIVE
	enemy.aquired_position = True
	g["enemies"].append(enemy)
	p = g["players"][0]
	p.rect.topleft = [44, 200]
	p.rotate(p.DIR_RIGHT, False)
	p.move(p.DIR_DOWN, 0)
	ctx.check("turn next to a tank snaps to the other grid line (left %d)" % p.rect.left,
		p.rect.left % 16 == 0 and not p.rect.colliderect(enemy.rect))
	ctx.finish()


def stun_and_freeze(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	clear_enemies(ctx)
	p = g["players"][0]
	p.setParalised(True)
	p.setFrozen(True)
	p.setParalised(False)
	ctx.check("stun ends: enemy clock freeze stays", p.paralised)
	p.setFrozen(False)
	ctx.check("freeze ends: player can move", not p.paralised)
	p.setParalised(True)
	game.pause()
	game.pause()
	ctx.check("pause and unpause keep stun", p.paralised)
	p.setParalised(False)
	ctx.check("stun ends after pause", not p.paralised)
	ctx.finish()


def continue_preset(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 1:
		ctx.check("continued game uses saved preset", g["CURRENT_PRESET"] == "EXTREME")
		game.endLevel(game.showMenu)
		return
	if ctx.frame > 1 and ctx.in_function("showMenu"):
		ctx.check("back in menu: player's preset again (%s)" % g["CURRENT_PRESET"], g["CURRENT_PRESET"] == "GOOD")
		ctx.finish()


def debug_keys(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 5:
		clear_enemies(ctx)
		return [ctx.key(pygame.K_p)]
	if ctx.frame == 7:
		ctx.check("P doesn't freeze enemies in normal game", not game.timefreeze)
		return [ctx.key(pygame.K_v)]
	if ctx.frame == 9:
		ctx.check("V doesn't show debug grid in normal game", not game.debug_mode)
		g["DEBUG_KEYS"] = True
		return [ctx.key(pygame.K_p)]
	if ctx.frame == 11:
		ctx.check("P works with DEBUG_KEYS", game.timefreeze)
		ctx.finish()


SCENARIOS = {
	"snap_next_to_tank": {"fn": snap_next_to_tank},
	"stun_and_freeze": {"fn": stun_and_freeze},
	"continue_preset": {"fn": continue_preset, "menu": continue_menu, "setup": write_savegame},
	"debug_keys": {"fn": debug_keys},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
