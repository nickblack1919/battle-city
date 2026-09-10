""" Saving progress after stage, CONTINUE menu item, saved game removed after game over """

import os, json
import harness
import pygame


def savegame_file():
	return os.path.join(harness.DATA_DIR, ".savegame")


def write_savegame():
	data = {
		"stage": 4,
		"nr_of_players": 2,
		"preset": "EXTREME",
		"players": [
			{"score": 12300, "lives": 2, "superpowers": 3, "next_extra_life": 20000},
			{"score": 4500, "lives": 5, "superpowers": 1, "next_extra_life": 20000},
		],
	}
	with open(savegame_file(), "w") as f:
		json.dump(data, f)


def finish_level(ctx):
	del ctx.game.level.enemies_left[:]
	for enemy in ctx.g["enemies"]:
		enemy.state = enemy.STATE_DEAD


def continue_menu(ctx):
	game = ctx.game
	f = ctx.menu_frame
	if f == 1:
		return [ctx.key(pygame.K_RETURN)]
	if f == 2:
		labels = [item[0] for item in game.menuItems()]
		ctx.check("menu has CONTINUE when game is saved: %s" % labels, labels[3] == "CONTINUE")
	if f in (2, 3, 4):
		return [ctx.key(pygame.K_DOWN)]
	if f == 5:
		return [ctx.key(pygame.K_RETURN)]
	return []


def continue_game(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	players = g["players"]
	ctx.check("continues from stage after saved one", game.stage == 5)
	ctx.check("saved number of players", len(players) == 2)
	ctx.check("saved preset", g["CURRENT_PRESET"] == "EXTREME")
	ctx.check("P1 score, lives, superpowers restored",
		(players[0].score, players[0].lives, players[0].superpowers) == (12300, 2, 3))
	ctx.check("P2 score, lives, superpowers restored",
		(players[1].score, players[1].lives, players[1].superpowers) == (4500, 5, 1))
	ctx.finish()


def no_savegame(ctx):
	if ctx.frame == 1:
		labels = [item[0] for item in ctx.game.menuItems()]
		ctx.check("no CONTINUE without saved game: %s" % labels, "CONTINUE" not in labels)
		ctx.finish()


def save_after_stage(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	p = g["players"][0]
	# level finishes when last enemy is removed, so wait for first spawn
	if ctx.frame == 100:
		p.score = 3400
		p.superpowers = 2
		finish_level(ctx)
	if ctx.frame > 100 and game.stage == 2 and game.running:
		ctx.check("game saved after stage", os.path.isfile(savegame_file()))
		with open(savegame_file()) as f:
			data = json.load(f)
		ctx.check("saved stage 1", data["stage"] == 1)
		ctx.check("saved player score", data["players"][0]["score"] == 3400)
		ctx.finish()


def delete_after_game_over(ctx):
	if ctx.frame == 1:
		ctx.check("saved game exists before game over", os.path.isfile(savegame_file()))
	if ctx.frame == 20:
		ctx.g["castle"].destroy()
	if ctx.frame == 30:
		ctx.check("saved game removed after game over", not os.path.isfile(savegame_file()))
		ctx.finish()


def broken_savegame():
	with open(savegame_file(), "w") as f:
		f.write('{"stage": "x"}')


def broken_menu(ctx):
	f = ctx.menu_frame
	if f == 1:
		return [ctx.key(pygame.K_RETURN)]
	if f in (2, 3, 4):
		return [ctx.key(pygame.K_DOWN)]
	if f == 5:
		# CONTINUE with broken file: stays in menu
		return [ctx.key(pygame.K_RETURN)]
	if f == 7:
		ctx.check("broken saved game doesn't start the game", ctx.in_function("showMenu"))
		return [ctx.key(pygame.K_UP), ctx.key(pygame.K_UP), ctx.key(pygame.K_UP)]
	if f == 9:
		return [ctx.key(pygame.K_RETURN)]
	return []


def broken_game(ctx):
	if ctx.frame == 1:
		ctx.check("new game starts from stage 1 after broken continue", ctx.game.stage == 1)
		ctx.finish()


SCENARIOS = {
	"continue": {"fn": continue_game, "menu": continue_menu, "setup": write_savegame},
	"no_savegame": {"fn": no_savegame},
	"save_after_stage": {"fn": save_after_stage},
	"delete_after_game_over": {"fn": delete_after_game_over, "setup": write_savegame},
	"broken_savegame": {"fn": broken_game, "menu": broken_menu, "setup": broken_savegame},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
