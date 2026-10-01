""" Settings instead of menu items: WAVES, BOT, RANDOM LEVELS, CUSTOM LEVELS (30 maps of the editor) """

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
	for label in ("WAVES", "BOT", "RANDOM LEVELS", "VERSUS", "LEVEL EDITOR", "CUSTOM LEVELS"):
		ctx.check("settings screen has %s" % label, label in labels)

	def item(label):
		return [i for i in game.settingsItems() if i["label"] == label][0]

	for label, name in (("WAVES", "WAVES_MODE"), ("BOT", "BOT_PLAYER"), ("RANDOM LEVELS", "RANDOM_LEVELS"), ("VERSUS", "VERSUS_MODE"), ("CUSTOM LEVELS", "CUSTOM_LEVELS")):
		before = g[name]
		ctx.check("%s is %s" % (label, item(label)["value"]), item(label)["value"] == ("ON" if before else "OFF"))
		game.changeSetting(item(label)["type"], 1, item(label))
		ctx.check("%s switched" % label, g[name] == (not before) and item(label)["value"] == ("OFF" if before else "ON"))

	# they are saved and read back
	g["loadSettings"]()
	ctx.check("settings saved and loaded (%s %s %s %s)" % (g["WAVES_MODE"], g["BOT_PLAYER"], g["RANDOM_LEVELS"], g["CUSTOM_LEVELS"]),
		g["WAVES_MODE"] and g["BOT_PLAYER"] and g["RANDOM_LEVELS"] and g["CUSTOM_LEVELS"])

	# number of levels and their files come from the chosen set
	ctx.check("30 custom levels", g["levelCount"]() == 30 and g["levelFile"](7) == os.path.join("levels", "new", "7"))
	g["CUSTOM_LEVELS"] = False
	ctx.check("35 standard levels", g["levelCount"]() == 35 and g["levelFile"](7) == os.path.join("levels", "7"))
	ctx.check("editor always edits the custom set", g["levelCount"](custom = True) == 30 and g["levelFile"](7, custom = True) == os.path.join("levels", "new", "7"))
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


def custom_levels_game(ctx):
	""" CUSTOM LEVELS setting: the campaign is played on the levels of the editor """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	ctx.check("custom level set is on", g["CUSTOM_LEVELS"] and g["levelCount"]() == 30)
	rows = open(os.path.join("levels", "new", str(game.stage))).read().split("\n")
	tiles = set([(tile.left, tile.top, tile.type) for tile in game.level.mapr])
	expected = set()
	types = {"#": game.level.TILE_BRICK, "@": game.level.TILE_STEEL, "~": game.level.TILE_WATER,
		"%": game.level.TILE_GRASS, "-": game.level.TILE_FROZE}
	for y, row in enumerate(rows):
		for x, ch in enumerate(row):
			if ch in types and ch != "#":
				expected.add((x * 16, y * 16, types[ch]))
	ctx.check("level of the custom set is loaded (stage %d)" % game.stage, expected and expected <= tiles)
	ctx.check("hiscore table of custom levels (%s)" % game.hiscoreKey("campaign"), game.hiscoreKey("campaign").startswith("campaign CUSTOM"))
	ctx.finish()


def start_stars(ctx):
	""" START STARS setting: stars every player starts a life with """
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return

	def item():
		return [i for i in game.settingsItems() if i["label"] == "START STARS"][0]

	ctx.check("settings screen has START STARS", item()["value"] == "PRESET" and g["START_SUPERPOWER"] == None)
	preset_stars = g["PLAYER_START_SUPERPOWER"]

	game.changeSetting("stars", 1, item())
	ctx.check("first value is 0 stars (%s)" % item()["value"], g["START_SUPERPOWER"] == 0 and item()["value"] == "0")
	for stars in range(1, g["MAX_START_SUPERPOWER"] + 1):
		game.changeSetting("stars", 1, item())
		ctx.check("%d stars chosen" % stars, g["START_SUPERPOWER"] == stars and g["PLAYER_START_SUPERPOWER"] == stars)
	game.changeSetting("stars", 1, item())
	ctx.check("after the last one comes PRESET again (%s)" % item()["value"],
		g["START_SUPERPOWER"] == None and g["PLAYER_START_SUPERPOWER"] == preset_stars)

	# chosen stars stay when the difficulty preset changes, and are saved
	game.changeSetting("stars", -1, item())
	ctx.check("left arrow takes the last value (%d)" % g["START_SUPERPOWER"], g["START_SUPERPOWER"] == g["MAX_START_SUPERPOWER"])
	g["applyPreset"]("NES")
	ctx.check("preset doesn't reset chosen stars", g["PLAYER_START_SUPERPOWER"] == g["MAX_START_SUPERPOWER"])
	g["applyPreset"]("GOOD")
	g["START_SUPERPOWER"] = None
	g["loadSettings"]()
	ctx.check("stars saved and loaded (%s)" % g["START_SUPERPOWER"], g["START_SUPERPOWER"] == g["MAX_START_SUPERPOWER"])

	# players really start a life with them
	for player in g["players"]:
		game.respawnPlayer(player)
		ctx.check("player starts with %d stars" % g["MAX_START_SUPERPOWER"],
			player.superpowers == g["MAX_START_SUPERPOWER"] and player.max_active_bullets == 3)
	ctx.finish()


def random_setting(ctx):
	""" RANDOM LEVELS setting: every stage is a new generated map, never symmetric """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	levelgen = g["levelgen"]
	ctx.check("RANDOM LEVELS is a setting", "RANDOM LEVELS" in [item["label"] for item in game.settingsItems()])
	ctx.check("game generates its levels", game.random_levels and game.mode == "random" and game.level_seed != None)

	def cells(rows):
		return set([(c, r, ch) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != "."])

	maps = []
	for stage in range(1, 11):
		rows = levelgen.generateLevel(game.level_seed, stage, "none")
		maps.append("\n".join(rows))
		left_right = set([(25 - c, r, ch) for c, r, ch in cells(rows)])
		up_down = set([(c, 25 - r, ch) for c, r, ch in cells(rows)])
		ctx.check("stage %d map is not symmetric" % stage, cells(rows) != left_right and cells(rows) != up_down)
	ctx.check("every stage gets its own map (%d of 10)" % len(set(maps)), len(set(maps)) == 10)

	# the map on screen is the generated one, and the next stage brings another
	rows = levelgen.generateLevel(game.level_seed, game.stage, "none")
	tiles = set([(tile.left // 16, tile.top // 16) for tile in game.level.mapr])
	expected = set([(c, r) for c, r, ch in cells(rows)])
	ctx.check("stage %d of the game uses its generated map" % game.stage, tiles == expected)
	ctx.check("generated games have their own hiscore table (%s)" % game.hiscoreKey(game.hiscoreMode()),
		game.hiscoreMode() == "random")
	ctx.finish()


def new_levels_files(ctx):
	""" All 30 maps the custom levels start from are there and playable """
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
	ctx.check("30 maps of the custom set are playable (%s)" % "; ".join(problems), not problems)
	# they are different maps, not copies
	maps = set([open(os.path.join("levels", "new", str(n))).read() for n in range(1, 31)])
	ctx.check("all 30 maps are different (%d)" % len(maps), len(maps) == 30)
	originals = set([open(os.path.join("levels", str(n))).read() for n in range(1, 36)])
	ctx.check("they are not the standard maps", not (maps & originals))
	ctx.finish()


SCENARIOS = {
	"settings": {"fn": settings},
	"start_stars": {"fn": start_stars},
	"bot_setting": {"fn": bot_setting, "menu": select_menu_item("1 PLAYER"), "setup": harness.settingsSetup(bot=True)},
	"waves_setting": {"fn": waves_setting, "menu": select_menu_item("1 PLAYER"), "setup": harness.settingsSetup(waves=True)},
	"custom_levels_game": {"fn": custom_levels_game, "menu": select_menu_item("1 PLAYER"), "setup": harness.settingsSetup(custom_levels=True)},
	"random_setting": {"fn": random_setting, "menu": select_menu_item("1 PLAYER"), "setup": harness.settingsSetup(random_levels=True)},
	"new_levels_files": {"fn": new_levels_files},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
