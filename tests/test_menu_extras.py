""" Hiscore tables per preset, gamepad settings, settings list scrolling, demo mode """

import json
import os
import pygame
import harness


def hiscores_per_preset(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	g["applyPreset"]("CLASSIC")
	# old file without presets
	with open(g["dataFile"](g["HISCORES_FILE"]), "w") as f:
		json.dump({"campaign": [["AAA", 500]]}, f)
	tables = game.loadHiscores()
	ctx.check("old table goes to current preset (%s)" % tables, tables.get("campaign CLASSIC") == [["AAA", 500]] and "campaign" not in tables)
	game.saveHiscores(tables)
	g["applyPreset"]("GOOD")
	ctx.check("other preset has own table", game.loadHiscores().get("campaign GOOD") == None)
	ctx.check("table name: mode and preset", game.hiscoreKey("endless") == "endless GOOD")
	ctx.finish()


class FakeJoystick(object):
	def __init__(self):
		self.held = set()

	def get_numhats(self):
		return 0

	def get_numaxes(self):
		return 0

	def get_numbuttons(self):
		return 12

	def get_button(self, button):
		return button in self.held


def gamepads(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	Gamepad = g["Gamepad"]
	p = g["players"][0]
	pads = [Gamepad(), Gamepad()]
	game.gamepads = pads

	for assign, expected, name in (([1, "AUTO", "AUTO"], pads[1], "gamepad 2"), (["OFF", "AUTO", "AUTO"], None, "no gamepad"), (["AUTO", "AUTO", "AUTO"], pads[0], "first free gamepad")):
		g["GAMEPAD_ASSIGN"] = assign
		game.assignGamepads()
		ctx.check("P1 assigned %s" % name, p.gamepad is expected)

	pad = Gamepad()
	joystick = FakeJoystick()
	pad.joystick = joystick
	joystick.held = set([5])
	ctx.check("button 5 isn't fire by default", not pad.read()["fire"])
	g["GAMEPAD_FIRE_BUTTON"] = 5
	ctx.check("fire button 5 chosen in settings", pad.read()["fire"])
	joystick.held = set([0, 7])
	ctx.check("default fire button doesn't fire then, start still default", not pad.read()["fire"] and pad.read()["start"])
	g["GAMEPAD_START_BUTTON"] = 3
	joystick.held = set([3])
	ctx.check("start button chosen in settings (%s)" % pad.buttonsHeld(), pad.read()["start"] and pad.buttonsHeld() == set([3]))

	# settings screen
	g["GAMEPAD_ASSIGN"] = ["AUTO", "AUTO", "AUTO"]
	items = game.settingsItems()
	labels = [item["label"] for item in items]
	ctx.check("gamepad settings on settings screen", all(label in labels for label in ("P1 GAMEPAD", "P2 GAMEPAD", "P3 GAMEPAD", "PAD FIRE", "PAD START")))
	p2 = items[labels.index("P2 GAMEPAD")]
	game.changeSetting("pad", 1, p2)
	ctx.check("P2 gamepad OFF", g["GAMEPAD_ASSIGN"][1] == "OFF")
	game.changeSetting("pad", 1, p2)
	value = [item["value"] for item in game.settingsItems() if item["label"] == "P2 GAMEPAD"][0]
	ctx.check("P2 gamepad 1 (%s)" % value, g["GAMEPAD_ASSIGN"][1] == 0 and value == "PAD 1")
	game.setPadButton("GAMEPAD_FIRE_BUTTON", 6)
	with open(g["dataFile"](g["SETTINGS_FILE"])) as f:
		saved = json.load(f)
	ctx.check("gamepad settings saved (%s %s)" % (saved.get("gamepads"), saved.get("pad_fire")), saved.get("gamepads") == ["AUTO", 0, "AUTO"] and saved.get("pad_fire") == 6)
	g["GAMEPAD_ASSIGN"] = ["OFF", "OFF", "OFF"]
	g["GAMEPAD_FIRE_BUTTON"] = None
	g["loadSettings"]()
	ctx.check("gamepad settings loaded", g["GAMEPAD_ASSIGN"] == ["AUTO", 0, "AUTO"] and g["GAMEPAD_FIRE_BUTTON"] == 6)
	fire_item = [item for item in game.settingsItems() if item["label"] == "PAD FIRE"][0]
	game.changeSetting("padbutton", -1, fire_item)
	ctx.check("left arrow: default fire buttons", g["GAMEPAD_FIRE_BUTTON"] == None)

	# long list scrolls, last item is drawn without errors
	items = game.settingsItems()
	game.drawSettings(items, len(items) - 1, "PRESS BTN")
	ctx.check("settings list with %d items drawn" % len(items), True)
	ctx.finish()


def idle_menu(ctx):
	""" Nothing is pressed in menu: demo starts soon """
	if ctx.menu_frame == 1:
		ctx.g["DEMO_IDLE_TIME"] = 400
		ctx.g["DEMO_TIME"] = 100000
	return []


def demo(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	players = g["players"]
	if ctx.frame == 1:
		ctx.check("demo started with 2 players", game.demo and len(players) == 2)
		d["start"] = [p.rect.topleft for p in players]
		d["shots"] = False
	if ctx.frame < 150:
		if any(b.owner_class in players for b in g["bullets"]):
			d["shots"] = True
		# players can be destroyed and respawn at start: remember any movement
		if any(p.rect.topleft != start for p, start in zip(players, d["start"])):
			d["moved"] = True
		return
	if ctx.frame == 150:
		ctx.check("computer drives players", d.get("moved"))
		ctx.check("computer fires", d["shots"])
		return [ctx.key(pygame.K_SPACE)]
	if ctx.in_function("showMenu"):
		ctx.check("key returns to menu", not game.demo)
		ctx.check("demo doesn't save game", not os.path.isfile(g["dataFile"](g["SAVEGAME_FILE"])))
		ctx.finish()
	if ctx.frame > 400:
		ctx.check("key returns to menu", False)
		ctx.finish()


def demo_time(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 1:
		g["DEMO_TIME"] = 2000
	if ctx.frame > 1 and ctx.in_function("showMenu"):
		# time since stage start (harness frames skip spawn animation and curtain, their number varies)
		ctx.check("demo ends after DEMO_TIME (%d ms)" % game.level_time, 2000 <= game.level_time <= 2100)
		ctx.finish()
	if ctx.frame > 400:
		ctx.check("demo ends after DEMO_TIME", False)
		ctx.finish()


SCENARIOS = {
	"hiscores_per_preset": {"fn": hiscores_per_preset},
	"gamepads": {"fn": gamepads},
	"demo": {"fn": demo, "menu": idle_menu},
	"demo_time": {"fn": demo_time, "menu": idle_menu},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
