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
	ctx.finish()


def played(ctx):
	""" showScores plays the new jingle when the bonus text appears """
	g, d = ctx.g, ctx.data
	if ctx.frame == 1:
		g["play_sounds"] = True
		d["sound"] = FakeSound()
		g["sounds"]["bonus1000"] = d["sound"]
		prepareScores(ctx)
		return
	if ctx.in_function("showScores"):
		d["seen"] = True
	if d.get("seen") and (not ctx.in_function("showScores") or ctx.frame > 500):
		ctx.check("bonus1000 played on the scores screen (%d times)" % d["sound"].played, d["sound"].played == 1)
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
	"played": {"fn": played, "players": 2},
	"fallback": {"fn": fallback, "players": 2},
	"no_sounds": {"fn": no_sounds, "players": 2},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
