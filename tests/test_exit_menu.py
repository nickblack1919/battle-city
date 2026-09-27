""" ESC in game asks before leaving to the main menu """

import os
import pygame
import harness


def prepare(ctx):
	del ctx.game.level.enemies_left[:]
	del ctx.g["enemies"][:]
	for p in ctx.g["players"]:
		p.shielded = True


def no_and_yes(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 5:
		prepare(ctx)
		d["level"] = game.level
		with open(g["dataFile"](g["SAVEGAME_FILE"]), "w") as f:
			f.write("{}")
		return [ctx.key(pygame.K_ESCAPE)]
	if ctx.frame == 7:
		ctx.check("ESC asks before exit", ctx.in_function("confirmExitToMenu"))
		return [ctx.key(pygame.K_n)]
	if ctx.frame == 9:
		ctx.check("N: back to the game", not ctx.in_function("confirmExitToMenu") and game.running)
		return [ctx.key(pygame.K_ESCAPE)]
	if ctx.frame == 11:
		ctx.check("ESC asks again", ctx.in_function("confirmExitToMenu"))
		return [ctx.key(pygame.K_y)]
	if ctx.frame > 11 and ctx.in_function("showMenu"):
		ctx.check("Y: main menu, game stopped", not game.running and game.level is d["level"])
		ctx.check("exit doesn't delete saved game", os.path.isfile(g["dataFile"](g["SAVEGAME_FILE"])))
		ctx.finish()
	if ctx.frame > 60:
		ctx.check("Y returns to menu", False)
		ctx.finish()


def paused(ctx):
	""" ESC works while the game is paused """
	g, game = ctx.g, ctx.game
	if ctx.frame == 5:
		prepare(ctx)
		game.pause()
		return [ctx.key(pygame.K_ESCAPE)]
	if ctx.frame == 7:
		ctx.check("ESC in pause asks too", ctx.in_function("confirmExitToMenu"))
		return [ctx.key(pygame.K_RETURN)]
	if ctx.frame > 7 and ctx.in_function("showMenu"):
		ctx.check("Enter also means yes", not game.running)
		ctx.finish()
	if ctx.frame > 60:
		ctx.check("Enter also means yes", False)
		ctx.finish()


SCENARIOS = {
	"no_and_yes": {"fn": no_and_yes},
	"paused": {"fn": paused},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
