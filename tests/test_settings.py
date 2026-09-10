""" Main menu, settings screen, saved settings """

import os, json
import harness
import pygame

K = pygame


def settings_file():
	return os.path.join(harness.DATA_DIR, ".settings.json")


def read_settings():
	with open(settings_file()) as f:
		return json.load(f)


# menu frame -> keys to press (or check function)
def settings_menu(ctx):
	g, game, f = ctx.g, ctx.game, ctx.menu_frame
	d = ctx.data

	steps = {
		1: [K.K_RETURN],			# skip intro animation
		2: [K.K_DOWN], 3: [K.K_DOWN], 4: [K.K_DOWN],	# SETTINGS item
		5: [K.K_RETURN],			# open settings
		7: [K.K_RIGHT],			# DIFFICULTY: GOOD -> EXTREME
		9: [K.K_DOWN], 10: [K.K_DOWN], 11: [K.K_DOWN], 12: [K.K_DOWN],	# P1 FIRE
		13: [K.K_RETURN], 14: [K.K_k],	# remap P1 FIRE to K
		16: [K.K_DOWN], 17: [K.K_RETURN], 18: [K.K_d],	# remap P1 UP to D (was P1 RIGHT) -> swap
		20: [K.K_ESCAPE],			# back to menu (doesn't quit)
		22: [K.K_UP], 23: [K.K_UP], 24: [K.K_UP],	# 1 PLAYER
		25: [K.K_RETURN],			# start game
	}

	if f == 4:
		ctx.check("menu has SETTINGS item", game.menuItems()[3][1] == "settings")
	if f == 6:
		ctx.check("Enter on SETTINGS opens settings screen", ctx.in_function("showSettings"))
		ctx.check("default preset GOOD", g["CURRENT_PRESET"] == "GOOD")
	if f == 8:
		ctx.check("right arrow changes difficulty to EXTREME", g["CURRENT_PRESET"] == "EXTREME")
		ctx.check("settings saved to file", os.path.isfile(settings_file()) and read_settings()["preset"] == "EXTREME")
	if f == 15:
		ctx.check("P1 fire remapped to K", g["PLAYER_CONTROLS"][0][0] == K.K_k)
	if f == 19:
		controls = g["PLAYER_CONTROLS"][0]
		ctx.check("P1 up remapped to D, P1 right got old key W (swap)", controls[1] == K.K_d and controls[2] == K.K_w)
		ctx.check("controls saved to file", read_settings()["controls"][0][:3] == [K.K_k, K.K_d, K.K_w])
	if f == 21:
		ctx.check("ESC on settings returns to menu", not ctx.in_function("showSettings") and ctx.in_function("showMenu"))

	return [ctx.key(k) for k in steps.get(f, [])]


def settings_game(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 1:
		p = g["players"][0]
		ctx.check("game started with 1 player", game.nr_of_players == 1 and len(g["players"]) == 1)
		ctx.check("P1 uses remapped controls", p.controls == [K.K_k, K.K_d, K.K_w, K.K_s, K.K_a])
		ctx.check("EXTREME preset active in game", g["CURRENT_PRESET"] == "EXTREME")
		ctx.finish()


def write_saved_settings():
	settings = {
		"preset": "CLASSIC",
		"sound": False,
		"fullscreen": False,
		"start_level": 5,
		"controls": [
			[K.K_k, K.K_i, K.K_l, K.K_COMMA, K.K_j],
			[K.K_RSHIFT, K.K_UP, K.K_RIGHT, K.K_DOWN, K.K_LEFT],
		],
	}
	with open(settings_file(), "w") as f:
		json.dump(settings, f)


def saved_settings(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 1:
		ctx.check("saved preset applied", g["CURRENT_PRESET"] == "CLASSIC" and g["MAX_ACTIVE_ENEMIES"] == 4)
		ctx.check("saved start level applied", game.stage == 5)
		ctx.check("saved sound setting applied", g["play_sounds"] == False)
		ctx.check("saved controls applied", g["players"][0].controls[0] == K.K_k)
		ctx.check("sounds are loaded even when sound is off", len(g["sounds"]) > 0)
		ctx.finish()


def broken_settings_file():
	with open(settings_file(), "w") as f:
		f.write("{not json")


def broken_settings(ctx):
	if ctx.frame == 1:
		ctx.check("broken settings file is ignored", ctx.g["CURRENT_PRESET"] == "GOOD" and ctx.game.stage == 1)
		ctx.finish()


SCENARIOS = {
	"settings_screen": {"fn": settings_game, "menu": settings_menu},
	"saved_settings": {"fn": saved_settings, "setup": write_saved_settings},
	"broken_settings": {"fn": broken_settings, "setup": broken_settings_file},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
