""" Interface language: translations, Russian text rendering, language setting """

import json
import pygame
import harness


def translations(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	lang = g["lang"]
	ctx.check("English by default", g["LANGUAGE"] == "EN" and lang.tr("SETTINGS") == "SETTINGS")
	g["LANGUAGE"] = "RU"
	ctx.check("phrase", lang.tr("1 PLAYER") == u"1 ИГРОК")
	ctx.check("words, numbers stay: %s" % lang.tr("STAGE 12"), lang.tr("STAGE 12") == u"УРОВЕНЬ 12")
	ctx.check("spaces kept: %s" % lang.tr("  500 PTS"), lang.tr("  500 PTS") == u"  500 ОЧК")
	ctx.check("unknown text stays", lang.tr("P1") == "P1")

	# Cyrillic text is drawn with default font about as high as game font
	surface = game.text("SETTINGS", False, (255, 255, 255))
	ctx.check("Russian text rendered (%s)" % (surface.get_size(),), 10 <= surface.get_height() <= 24 and surface.get_width() > 0)
	digits = game.text("12345", False, (255, 255, 255))
	ctx.check("numbers keep game font", digits.get_size() == game.font.size("12345"))

	# screens with texts are drawn without errors
	items = game.settingsItems()
	for selected in (0, len(items) - 1):
		game.drawSettings(items, selected, False)
	game.drawIntroScreen()
	game.drawNameEntry(0, 5500, ["A", "B", "C"], 1)
	ctx.check("screens drawn in Russian", True)

	# internal labels stay English
	ctx.check("menu labels stay English", "SETTINGS" in [item[0] for item in game.menuItems()])
	ctx.finish()


def setting(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	labels = [item["label"] for item in game.settingsItems()]
	ctx.check("LANGUAGE on settings screen", "LANGUAGE" in labels)
	game.changeSetting("lang", 1)
	ctx.check("changed to RU", g["LANGUAGE"] == "RU")
	with open(g["dataFile"](g["SETTINGS_FILE"])) as f:
		ctx.check("saved in settings", json.load(f).get("language") == "RU")
	g["LANGUAGE"] = "EN"
	g["loadSettings"]()
	ctx.check("loaded from settings", g["LANGUAGE"] == "RU")
	game.changeSetting("lang", 1)
	ctx.check("back to EN", g["LANGUAGE"] == "EN")
	ctx.finish()


SCENARIOS = {
	"translations": {"fn": translations},
	"setting": {"fn": setting},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
