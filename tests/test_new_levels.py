""" Settings instead of menu items: WAVES, BOT, NEW LEVELS (30 new maps) """

import os
import pygame
import harness


def select_menu_item(label):
	""" Menu: skip intro, select item by label, activate it """
	def menu(ctx):
		game = ctx.game
		if ctx.menu_frame == 1:
			return [ctx.key(pygame.K_RETURN)]
		if ctx.menu_frame == 2:
			labels = [item[0] for item in game.menuItems()]
			ctx.check("menu has %s: %s" % (label, labels), label in labels)
			ctx.data["menu_target"] = labels.index(label)
		if 2 <= ctx.menu_frame < 2 + ctx.data.get("menu_target", 0):
			return [ctx.key(pygame.K_DOWN)]
		if ctx.menu_frame == 2 + ctx.data.get("menu_target", 0):
			return [ctx.key(pygame.K_RETURN)]
		return []
	return menu


def settings(ctx):
	""" Three new settings switch what the menu items start """
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	labels = [item["label"] for item in game.settingsItems()]
	for label in ("WAVES", "BOT", "NEW LEVELS"):
		ctx.check("settings screen has %s" % label, label in labels)

	def item(label):
		return [i for i in game.settingsItems() if i["label"] == label][0]

	for label, name in (("WAVES", "WAVES_MODE"), ("BOT", "BOT_PLAYER"), ("NEW LEVELS", "NEW_LEVELS")):
		before = g[name]
		ctx.check("%s is %s" % (label, item(label)["value"]), item(label)["value"] == ("ON" if before else "OFF"))
		game.changeSetting(item(label)["type"], 1, item(label))
		ctx.check("%s switched" % label, g[name] == (not before) and item(label)["value"] == ("OFF" if before else "ON"))

	# they are saved and read back
	g["loadSettings"]()
	ctx.check("settings saved and loaded (%s %s %s)" % (g["WAVES_MODE"], g["BOT_PLAYER"], g["NEW_LEVELS"]),
		g["WAVES_MODE"] and g["BOT_PLAYER"] and g["NEW_LEVELS"])

	# number of levels and their files come from the chosen set
	ctx.check("30 new levels", g["levelCount"]() == 30 and g["levelFile"](7) == os.path.join("levels", "new", "7"))
	g["NEW_LEVELS"] = False
	ctx.check("35 original levels", g["levelCount"]() == 35 and g["levelFile"](7) == os.path.join("levels", "7"))
	ctx.finish()


def bot_setting(ctx):
	""" BOT setting: the computer plays one more tank than the chosen number of players """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	players = g["players"]
	ctx.check("1 PLAYER with BOT gives two tanks", game.nr_of_players == 2 and len(players) == 2)
	ctx.check("second tank is the computer partner", players[1].bot != None and not players[1].bot.guard)
	ctx.check("first tank is the human", players[0].bot == None)
	ctx.check("menu item number of players and bot (%d, %d)" % game.playersWithBot(1), game.playersWithBot(1) == (2, 2))
	ctx.check("two players get a guard", game.playersWithBot(2) == (3, 3))
	ctx.check("three players leave no room for the bot", game.playersWithBot(3) == (3, 0))
	ctx.finish()


def waves_setting(ctx):
	""" WAVES setting: menu items start endless waves """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	ctx.check("endless mode started from 1 PLAYER", game.mode == "endless")
	ctx.check("waves are counted from the first stage", game.first_stage == g["START_LEVEL"])
	ctx.check("hiscore table of waves", game.hiscoreKey("endless") == "endless " + g["CURRENT_PRESET"])
	ctx.finish()


def new_levels_game(ctx):
	""" NEW LEVELS setting: the campaign is played on the new maps """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	ctx.check("new level set is on", g["NEW_LEVELS"] and g["levelCount"]() == 30)
	rows = open(os.path.join("levels", "new", str(game.stage))).read().split("\n")
	tiles = set([(tile.left, tile.top, tile.type) for tile in game.level.mapr])
	expected = set()
	types = {"#": game.level.TILE_BRICK, "@": game.level.TILE_STEEL, "~": game.level.TILE_WATER,
		"%": game.level.TILE_GRASS, "-": game.level.TILE_FROZE}
	for y, row in enumerate(rows):
		for x, ch in enumerate(row):
			if ch in types and ch != "#":
				expected.add((x * 16, y * 16, types[ch]))
	ctx.check("level of the new set is loaded (stage %d)" % game.stage, expected and expected <= tiles)
	ctx.check("hiscore table of new levels (%s)" % game.hiscoreKey("campaign"), game.hiscoreKey("campaign").startswith("campaign NEW"))
	ctx.finish()


def new_levels_files(ctx):
	""" All 30 new levels are there and playable """
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	import sys
	sys.path.insert(0, "tools")
	import make_levels
	problems = []
	for number in range(1, 31):
		path = os.path.join("levels", "new", str(number))
		if not os.path.isfile(path):
			problems.append("%d missing" % number)
			continue
		rows = open(path).read().split("\n")
		found = make_levels.check(number, rows)
		if found:
			problems.append("%d: %s" % (number, ", ".join(found)))
	ctx.check("30 new levels are playable (%s)" % "; ".join(problems), not problems)
	# they are different maps, not copies
	maps = set([open(os.path.join("levels", "new", str(n))).read() for n in range(1, 31)])
	ctx.check("all 30 maps are different (%d)" % len(maps), len(maps) == 30)
	originals = set([open(os.path.join("levels", str(n))).read() for n in range(1, 36)])
	ctx.check("new maps are not the original ones", not (maps & originals))
	ctx.finish()


SCENARIOS = {
	"settings": {"fn": settings},
	"bot_setting": {"fn": bot_setting, "menu": select_menu_item("1 PLAYER"), "setup": harness.settingsSetup(bot=True)},
	"waves_setting": {"fn": waves_setting, "menu": select_menu_item("1 PLAYER"), "setup": harness.settingsSetup(waves=True)},
	"new_levels_game": {"fn": new_levels_game, "menu": select_menu_item("1 PLAYER"), "setup": harness.settingsSetup(new_levels=True)},
	"new_levels_files": {"fn": new_levels_files},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
