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


# menu frame -> keys to press (or check function). Frames after the settings list are counted from
# the place of P1 FIRE in it, so new settings above it don't break the test
def settings_menu(ctx):
	g, game, f = ctx.g, ctx.game, ctx.menu_frame
	d = ctx.data

	if f == 1:
		return [ctx.key(K.K_RETURN)]			# skip intro animation
	if f == 2:
		# menu may have more items before SETTINGS: start 3 items above it
		labels = [item[0] for item in game.menuItems()]
		game.menu_index = labels.index("SETTINGS") - 3
	if f in (2, 3, 4):
		return [ctx.key(K.K_DOWN)]			# SETTINGS item
	if f == 5:
		ctx.check("down arrow selects SETTINGS item", game.menuItems()[game.menu_index][1] == "settings")
		return [ctx.key(K.K_RETURN)]			# open settings
	if f == 6:
		ctx.check("Enter on SETTINGS opens settings screen", ctx.in_function("showSettings"))
		ctx.check("default preset GOOD", g["CURRENT_PRESET"] == "GOOD")
		d["downs"] = [item["label"] for item in game.settingsItems()].index("P1 FIRE")
		return []
	if f == 7:
		return [ctx.key(K.K_RIGHT)]			# DIFFICULTY: GOOD -> EXTREME
	if f == 8:
		ctx.check("right arrow changes difficulty to EXTREME", g["CURRENT_PRESET"] == "EXTREME")
		ctx.check("settings saved to file", os.path.isfile(settings_file()) and read_settings()["preset"] == "EXTREME")
		return []

	downs = d.get("downs", 0)
	base = 8 + downs
	if 9 <= f <= base:
		return [ctx.key(K.K_DOWN)]			# down to P1 FIRE
	if f == base + 1:
		return [ctx.key(K.K_RETURN)]			# remap P1 FIRE
	if f == base + 2:
		return [ctx.key(K.K_k)]
	if f == base + 3:
		ctx.check("P1 fire remapped to K", g["PLAYER_CONTROLS"][0][0] == K.K_k)
		return []
	if f == base + 4:
		return [ctx.key(K.K_DOWN)]			# P1 UP
	if f == base + 5:
		return [ctx.key(K.K_RETURN)]
	if f == base + 6:
		return [ctx.key(K.K_d)]			# D was P1 RIGHT -> swap
	if f == base + 7:
		controls = g["PLAYER_CONTROLS"][0]
		ctx.check("P1 up remapped to D, P1 right got old key W (swap)", controls[1] == K.K_d and controls[2] == K.K_w)
		ctx.check("controls saved to file", read_settings()["controls"][0][:3] == [K.K_k, K.K_d, K.K_w])
		return []
	if f == base + 8:
		return [ctx.key(K.K_ESCAPE)]			# back to menu (doesn't quit)
	if f == base + 9:
		ctx.check("ESC on settings returns to menu", not ctx.in_function("showSettings") and ctx.in_function("showMenu"))
		labels = [item[0] for item in game.menuItems()]
		game.menu_index = labels.index("1 PLAYER")
		return []
	if f == base + 10:
		return [ctx.key(K.K_RETURN)]			# start game
	return []


def settings_game(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 1:
		p = g["players"][0]
		ctx.check("game started with 1 player", game.nr_of_players == 1 and len(g["players"]) == 1)
		ctx.check("P1 uses remapped controls", p.controls == [K.K_k, K.K_d, K.K_w, K.K_s, K.K_a])
		ctx.check("EXTREME preset active in game", g["CURRENT_PRESET"] == "EXTREME")
		ctx.finish()


def presets(ctx):
	""" All four presets are on the settings screen, NES also sets AI, auto fire and turn assist """
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	ctx.check("preset names (%s)" % g["PRESET_NAMES"], g["PRESET_NAMES"] == ["NES", "NES+", "GOOD", "EXTREME"])
	seen = []
	for i in range(len(g["PRESET_NAMES"])):
		game.changeSetting("preset", 1)
		seen.append(g["CURRENT_PRESET"])
	ctx.check("difficulty cycles through all presets (%s)" % seen, sorted(seen) == sorted(g["PRESET_NAMES"]))

	g["applyPreset"]("NES")
	ctx.check("NES preset: everything like on NES",
		g["ENEMY_AI"] == "NES" and not g["AUTO_FIRE"] and not g["PLAYER_TURN_ASSIST"] and g["NES_STARS"]
		and not g["ENEMY_PICKUP_BONUSES"] and not g["ENABLE_NEW_ENEMIES"] and g["PLAYER_ARMOR_SUPERPOWERS"] == [])
	g["applyPreset"]("NES+")
	ctx.check("NES+ preset: NES rules with our additions",
		g["MAX_ACTIVE_ENEMIES"] == 4 and g["FRIENDLY_FIRE"] and g["ENABLE_NEW_ENEMIES"] and g["ENABLE_PLAYER_PROTECTION"]
		and g["PLAYER_ARMOR_SUPERPOWERS"] == [3, 6] and len(set(g["BONUS_TYPES"])) == 8 and g["AUTO_FIRE"])
	g["applyPreset"]("GOOD")
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
		ctx.check("old preset name CLASSIC loaded as NES+", g["CURRENT_PRESET"] == "NES+" and g["MAX_ACTIVE_ENEMIES"] == 4)
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
	"presets": {"fn": presets},
	"settings_screen": {"fn": settings_game, "menu": settings_menu},
	"saved_settings": {"fn": saved_settings, "setup": write_saved_settings},
	"broken_settings": {"fn": broken_settings, "setup": broken_settings_file},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
