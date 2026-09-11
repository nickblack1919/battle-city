""" NES stage curtain and engine sound of moving player tank """

import pygame
import harness


def curtain(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	grey = pygame.Color(*game.CURTAIN_COLOR)
	background = pygame.Surface((480, 416))
	background.fill((0, 0, 0))
	game.drawCurtain(background, 0.5)
	screen = g["screen"]
	ctx.check("half closed curtain: grey at top and bottom, stage in the middle",
		screen.get_at((10, 10)) == grey and screen.get_at((470, 405)) == grey and screen.get_at((10, 208)) != grey)
	game.drawCurtain(background, 1)
	ctx.check("closed curtain covers whole screen", screen.get_at((240, 207)) == grey and screen.get_at((240, 208)) == grey)
	game.drawCurtain(background, 0)
	ctx.check("open curtain shows stage", screen.get_at((10, 10)) != grey and screen.get_at((10, 405)) != grey)
	game.openCurtain()
	ctx.check("curtain opened, level runs", not game.stage_screen and game.running)
	ctx.finish()


def engine(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	p = g["players"][0]
	sounds = g["sounds"]
	if ctx.frame == 1:
		ctx.check("engine sound made from engine hum (higher: shorter)",
			"engine" in sounds and sounds["engine"].get_length() < sounds["bg"].get_length())
		del ctx.game.level.enemies_left[:]
		del g["enemies"][:]
		p.shielded = True
		g["play_sounds"] = True
		# enemy engine hum is heard
		game.playBackgroundSound()
		p.pressed = [True, False, False, False]
	if ctx.frame == 3:
		ctx.check("enemy hum heard: no own engine sound", not game.engine_sound)
		# last enemy destroyed: hum stops, moving tank is heard
		game.bg_sound = False
	if ctx.frame == 5:
		ctx.check("moving tank at the end of stage: engine sound", game.engine_sound)
		p.pressed = [False] * 4
	if ctx.frame == 7:
		ctx.check("tank stopped: no engine sound", not game.engine_sound)
		p.pressed = [False, False, False, True]
	if ctx.frame == 9:
		ctx.check("moving again: engine sound", game.engine_sound)
		game.playBackgroundSound()
		ctx.check("hum starts: own engine sound stops", not game.engine_sound)
		game.bg_sound = False
	if ctx.frame == 11:
		game.pause()
	if ctx.frame == 13:
		ctx.check("no engine sound in pause", not game.engine_sound)
		ctx.finish()


SCENARIOS = {
	"curtain": {"fn": curtain},
	"engine": {"fn": engine},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
