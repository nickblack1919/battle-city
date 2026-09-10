""" Level editor and custom levels """

import os
import harness
import pygame


def custom_level_file(level_nr):
	return os.path.join(harness.DATA_DIR, "custom_levels", str(level_nr))


def read_rows(level_nr):
	with open(custom_level_file(level_nr)) as f:
		return f.read().split("\n")


def open_editor(ctx):
	""" Menu frames 1-3: skip intro, select LEVEL EDITOR, open it. Returns True when done """
	game = ctx.game
	if ctx.menu_frame == 1:
		return [ctx.key(pygame.K_RETURN)]
	if ctx.menu_frame == 2:
		labels = [item[0] for item in game.menuItems()]
		ctx.check("menu has LEVEL EDITOR: %s" % labels, "LEVEL EDITOR" in labels)
		game.menu_index = labels.index("LEVEL EDITOR") - 1
		return [ctx.key(pygame.K_DOWN)]
	if ctx.menu_frame == 3:
		return [ctx.key(pygame.K_RETURN)]
	return None


def mouse_click(x, y, button=1):
	return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=button)


def edit_menu(ctx):
	events = open_editor(ctx)
	if events != None:
		return events

	K = pygame
	f = ctx.menu_frame
	steps = {
		# cursor starts at column 2, row 2: go to column 2, row 0
		5: [K.K_UP], 6: [K.K_UP],
		7: [K.K_2],		# steel
		8: [K.K_SPACE],	# draw
		9: [K.K_s],		# save
		# protected cell: enemy spawn point at column 0, row 0
		11: [K.K_LEFT], 12: [K.K_LEFT],
		13: [K.K_SPACE],
		14: [K.K_s],
		# mouse: column 5, row 2
		16: [mouse_click(5 * 16 + 4, 2 * 16 + 4)],
		17: [K.K_s],
		# right mouse button erases
		19: [mouse_click(5 * 16 + 4, 2 * 16 + 4, 3)],
		20: [mouse_click(6 * 16 + 4, 2 * 16 + 4)],
		21: [K.K_t],	# save and play
	}

	if f == 4:
		ctx.check("editor opened", ctx.in_function("showEditor"))
	if f == 10:
		ctx.check("custom level saved", os.path.isfile(custom_level_file(1)))
		ctx.check("steel drawn at column 2 row 0", read_rows(1)[0][2] == "@")
		ctx.check("rest of level 1 kept", read_rows(1)[2] == "..##..##..##..##..##..##..")
	if f == 15:
		ctx.check("can't draw on enemy spawn point", read_rows(1)[0][0] == ".")
	if f == 18:
		ctx.check("left mouse button draws", read_rows(1)[2][5] == "@")

	return [ctx.key(k) if isinstance(k, int) else k for k in steps.get(f, [])]


def edit_game(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 1:
		level = game.level
		steel = [(tile.left, tile.top) for tile in level.mapr if tile.type == level.TILE_STEEL]
		ctx.check("T starts edited level 1", game.stage == 1 and game.mode == "campaign" and len(g["players"]) == 1)
		ctx.check("game uses custom level (steel at column 2 row 0)", (32, 0) in steel)
		ctx.check("right mouse erased tile at column 5 row 2", (80, 32) not in steel)
		ctx.check("tile drawn at column 6 row 2 before test play was saved", (96, 32) in steel)
		ctx.finish()


def write_custom_level_2():
	directory = os.path.join(harness.DATA_DIR, "custom_levels")
	os.makedirs(directory)
	with open(os.path.join(directory, "2"), "w") as f:
		f.write("\n".join(["@" * 26] + ["." * 26] * 25))


def reset_menu(ctx):
	events = open_editor(ctx)
	if events != None:
		return events

	f = ctx.menu_frame
	g = ctx.g
	if f == 4:
		ctx.check("custom level used instead of original", g["levelFile"](2) == custom_level_file(2))
		return [ctx.key(pygame.K_RIGHTBRACKET)]	# level 2
	if f == 5:
		return [ctx.key(pygame.K_d)]	# delete custom level 2
	if f == 6:
		ctx.check("D deletes custom level", not os.path.isfile(custom_level_file(2)))
		ctx.check("original level used again", g["levelFile"](2) == os.path.join("levels", "2"))
		return [ctx.key(pygame.K_ESCAPE)]
	if f == 8:
		ctx.check("ESC returns from editor to menu", ctx.in_function("showMenu") and not ctx.in_function("showEditor"))
		# start 1 player game to finish the test
		ctx.game.menu_index = 0
		return [ctx.key(pygame.K_RETURN)]
	return []


def reset_game(ctx):
	ctx.finish()


SCENARIOS = {
	"edit_and_play": {"fn": edit_game, "menu": edit_menu},
	"reset_custom_level": {"fn": reset_game, "menu": reset_menu, "setup": write_custom_level_2},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
