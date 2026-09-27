""" NES sound effects synthesized from the disassembly (tools/nes_sfx.py): 1000 points bonus jingle """

import os
import pygame
import harness


class FakeSound(object):
	""" Stands in for pygame.mixer.Sound to count play() calls """

	def __init__(self):
		self.played = 0

	def play(self, *args):
		self.played += 1

	def stop(self):
		pass


def prepareScores(ctx):
	""" Two players, player 2 destroyed more tanks: scores screen shows the bonus under his column """
	g, game = ctx.g, ctx.game
	del game.level.enemies_left[:]
	del g["enemies"][:]
	del g["bonuses"][:]
	g["players"][0].trophies["enemy0"] = 1
	g["players"][1].trophies["enemy0"] = 5
	for p in g["players"]:
		p.lives = 3
	game.endLevel(game.showScores)


def loaded(ctx):
	g = ctx.g
	sounds = g["sounds"]
	if ctx.frame != 1:
		return
	ctx.check("generated file sounds/bonus1000.wav is in the repo", os.path.exists(os.path.join(harness.GAME_DIR, "sounds", "bonus1000.wav")))
	ctx.check("bonus1000 sound is loaded", "bonus1000" in sounds)
	length = sounds["bonus1000"].get_length() if "bonus1000" in sounds else 0
	# 28 NES frames at 60 fps = 0.467 s
	ctx.check("length matches the note durations (%.3f s)" % length, 0.4 < length < 0.55)

	ctx.check("generated file sounds/bonus1000_pal.wav is in the repo", os.path.exists(os.path.join(harness.GAME_DIR, "sounds", "bonus1000_pal.wav")))
	ctx.check("PAL (DENDY) version is loaded", "bonus1000_pal" in sounds)
	pal = sounds["bonus1000_pal"].get_length() if "bonus1000_pal" in sounds else 0
	# 28 frames at 50 fps = 0.56 s, lower and slower than NTSC
	ctx.check("PAL version is longer (%.3f s)" % pal, 0.5 < pal < 0.62 and pal > length)
	ctx.finish()


def played(ctx, version):
	""" showScores plays the jingle of the chosen console when the bonus text appears """
	g, d = ctx.g, ctx.data
	if ctx.frame == 1:
		g["play_sounds"] = True
		g["applyNesVersion"](version)
		d["ntsc"], d["pal"] = FakeSound(), FakeSound()
		g["sounds"]["bonus1000"] = d["ntsc"]
		g["sounds"]["bonus1000_pal"] = d["pal"]
		prepareScores(ctx)
		return
	if ctx.in_function("showScores"):
		d["seen"] = True
	if d.get("seen") and (not ctx.in_function("showScores") or ctx.frame > 500):
		played_pal, played_ntsc = d["pal"].played, d["ntsc"].played
		if version == "DENDY":
			ctx.check("DENDY: PAL jingle played (pal %d, ntsc %d)" % (played_pal, played_ntsc), played_pal == 1 and played_ntsc == 0)
		else:
			ctx.check("NTSC: NTSC jingle played (pal %d, ntsc %d)" % (played_pal, played_ntsc), played_ntsc == 1 and played_pal == 0)
		ctx.finish()
	if ctx.frame > 700:
		ctx.check("scores screen reached", False)
		ctx.finish()


def fallback(ctx):
	""" Without the generated file the old bonus sound is used and nothing crashes """
	g, d = ctx.g, ctx.data
	if ctx.frame == 1:
		g["play_sounds"] = True
		d["sound"] = FakeSound()
		g["sounds"].pop("bonus1000", None)
		g["sounds"].pop("bonus1000_pal", None)
		g["sounds"]["bonus"] = d["sound"]
		prepareScores(ctx)
		return
	if ctx.in_function("showScores"):
		d["seen"] = True
	if d.get("seen") and (not ctx.in_function("showScores") or ctx.frame > 500):
		ctx.check("old bonus sound is played instead (%d times)" % d["sound"].played, d["sound"].played == 1)
		ctx.finish()
	if ctx.frame > 700:
		ctx.check("scores screen reached", False)
		ctx.finish()


def no_sounds(ctx):
	""" Sounds could not be loaded at all: the scores screen still works """
	g, d = ctx.g, ctx.data
	if ctx.frame == 1:
		g["play_sounds"] = False
		g["sounds"].clear()
		prepareScores(ctx)
		return
	if ctx.in_function("showScores"):
		d["seen"] = True
	if d.get("seen") and (not ctx.in_function("showScores") or ctx.frame > 500):
		ctx.check("scores screen with the bonus drawn without any sounds", True)
		ctx.finish()
	if ctx.frame > 700:
		ctx.check("scores screen reached", False)
		ctx.finish()


SCENARIOS = {
	"loaded": {"fn": loaded},
	"played": {"fn": lambda ctx: played(ctx, "DENDY"), "players": 2},
	"played_ntsc": {"fn": lambda ctx: played(ctx, "NTSC"), "players": 2},
	"fallback": {"fn": fallback, "players": 2},
	"no_sounds": {"fn": no_sounds, "players": 2},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
