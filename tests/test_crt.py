""" CRT filter: setting, saved setting, filter drawn on display only """

import os, json
import harness
import pygame


def settings_file():
	return os.path.join(harness.DATA_DIR, ".settings.json")


def brightness(surface, pos):
	color = surface.get_at(pos)
	return color.r + color.g + color.b


def setting(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	items = game.settingsItems()
	labels = [item["label"] for item in items]
	ctx.check("CRT FILTER on settings screen after LANGUAGE", labels.index("CRT FILTER") == labels.index("LANGUAGE") + 1)
	ctx.check("OFF by default", g["CRT_FILTER"] == "OFF")
	values = []
	for i in range(3):
		game.changeSetting("crt", 1)
		values.append(g["CRT_FILTER"])
	ctx.check("cycles SOFT, STRONG, OFF: %s" % values, values == ["SOFT", "STRONG", "OFF"])
	game.changeSetting("crt", -1)
	ctx.check("left arrow goes back to STRONG", g["CRT_FILTER"] == "STRONG")
	with open(settings_file()) as f:
		ctx.check("saved in settings", json.load(f).get("crt") == "STRONG")
	g["CRT_FILTER"] = "OFF"
	g["loadSettings"]()
	ctx.check("loaded from settings", g["CRT_FILTER"] == "STRONG")

	# Russian label and values fit on settings screen
	g["LANGUAGE"] = "RU"
	label = game.text("CRT FILTER", False, (255, 255, 255))
	ctx.check("RU label fits before value column (%d px)" % label.get_width(), 40 + label.get_width() < 288)
	for value in ("OFF", "SOFT", "STRONG"):
		surface = game.text(value, False, (255, 255, 255))
		ctx.check("RU value %s fits screen" % value, 288 + surface.get_width() <= 480)
	items = game.settingsItems()
	game.drawSettings(items, labels.index("CRT FILTER"), False)
	g["LANGUAGE"] = "EN"
	g["CRT_FILTER"] = "OFF"
	ctx.finish()


def display_pixels(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	screen = g["screen"]
	game.shake_frames = 0

	# picture with details and flat gray area
	screen.fill((128, 128, 128))
	for x in range(0, 480, 24):
		pygame.draw.rect(screen, ((x * 7) % 256, 200, (x * 3) % 256), (x, 10, 12, 30))
	before = pygame.image.tostring(screen, "RGB")

	g["CRT_FILTER"] = "OFF"
	game.flip()
	display = pygame.display.get_surface()
	ctx.check("display is 480x416", display.get_size() == (480, 416))
	ctx.check("filter OFF: display equals screen", pygame.image.tostring(display, "RGB") == before)

	for mode in ("SOFT", "STRONG"):
		g["CRT_FILTER"] = mode
		game.shake_frames = 0
		game.flip()
		display = pygame.display.get_surface()
		center = (240, 208)
		ctx.check("%s: scanline row darker than row above and below" % mode,
			brightness(display, (240, 209)) < brightness(display, (240, 208)) and brightness(display, (240, 209)) < brightness(display, (240, 210)))
		ctx.check("%s: corners darker than center" % mode,
			all([brightness(display, corner) < brightness(display, center) for corner in ((1, 1), (478, 1), (1, 414), (478, 414))]))
		ctx.check("%s: edges darker than center" % mode,
			brightness(display, (240, 2)) < brightness(display, center) and brightness(display, (2, 208)) < brightness(display, center))
		ctx.check("%s: center not too dark (%d)" % (mode, brightness(display, center)), brightness(display, center) >= 3 * 110)
		ctx.check("%s: game screen unchanged" % mode, pygame.image.tostring(screen, "RGB") == before)

	# screen shake still works with filter
	g["CRT_FILTER"] = "STRONG"
	game.shake_frames = 5
	game.flip()
	ctx.check("shake with filter: frame counted", game.shake_frames == 4)
	ctx.check("shake with filter: game screen unchanged", pygame.image.tostring(screen, "RGB") == before)
	g["CRT_FILTER"] = "OFF"
	ctx.finish()


def bad_settings_file():
	with open(settings_file(), "w") as f:
		json.dump({"crt": "ULTRA", "language": "RU"}, f)


def bad_setting(ctx):
	g = ctx.g
	if ctx.frame == 1:
		ctx.check("bad crt value ignored", g["CRT_FILTER"] == "OFF")
		ctx.check("other settings still loaded", g["LANGUAGE"] == "RU")
		ctx.finish()


def good_settings_file():
	with open(settings_file(), "w") as f:
		json.dump({"crt": "SOFT"}, f)


def good_setting(ctx):
	if ctx.frame == 1:
		ctx.check("saved crt value applied at start", ctx.g["CRT_FILTER"] == "SOFT")
		ctx.finish()


SCENARIOS = {
	"setting": {"fn": setting},
	"display_pixels": {"fn": display_pixels},
	"bad_setting": {"fn": bad_setting, "setup": bad_settings_file},
	"good_setting": {"fn": good_setting, "setup": good_settings_file},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
