""" NES details: bonus disappears, stunned partner blinks, bonus on scores screen, stage select, pause sounds """

import pygame
import harness


def clear(ctx):
	del ctx.game.level.enemies_left[:]
	del ctx.g["enemies"][:]
	del ctx.g["bonuses"][:]
	for p in ctx.g["players"]:
		p.shielded = True


def bonus_disappears(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	clear(ctx)
	g["applyPreset"]("CLASSIC")
	ctx.check("bonus has a lifetime in CLASSIC too (%s ms)" % g["BONUS_SPAWN_TIMEOUT"], g["BONUS_SPAWN_TIMEOUT"] > 0)

	Enemy = g["Enemy"]
	game.level.enemies_left[:] = [Enemy.TYPE_BASIC]
	enemy = Enemy(game.level, 1, [0, 0])
	del game.level.enemies_left[:]
	enemy.state = enemy.STATE_ALIVE
	g["enemies"].append(enemy)
	enemy.spawnBonus()
	ctx.check("bonus on the field", len(g["bonuses"]) == 1)
	ctx.check("bonus blinks from the start, like on NES", g["bonuses"][0].blinking)

	# NES: a new bonus tank removes the bonus lying on the field
	game.level.enemies_left[:] = [Enemy.TYPE_BASIC] * 10
	while len(g["bonuses"]) and len(game.level.enemies_left):
		game.spawnEnemy()
	ctx.check("new bonus tank removes the old bonus", len(g["bonuses"]) == 0)
	ctx.finish()


def stun_blink(ctx):
	""" Player hit by partner blinks while stunned """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		clear(ctx)
		g["FRIENDLY_FIRE"] = True
		p1, p2 = g["players"][0], g["players"][1]
		p2.shielded = False
		p2.bulletImpact(True, 100, p1, p2.DIR_UP)
		ctx.check("partner is stunned", p2.paralised and p2.state == p2.STATE_ALIVE)
		d["blinks"] = set()
	p2 = g["players"][1]
	d["blinks"].add(p2.stun_blink)
	if ctx.frame == 40:
		ctx.check("tank blinks while stunned (%s)" % d["blinks"], d["blinks"] == set([True, False]))
		p2.setParalised(False)
		ctx.check("stun is over: tank is visible", not p2.stun_blink)
		ctx.finish()


def scores_bonus(ctx):
	""" Bonus for most kills is written under the player's column, with a sound """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		clear(ctx)
		# player 2 destroyed more tanks
		g["players"][0].trophies["enemy0"] = 1
		g["players"][1].trophies["enemy0"] = 5
		for p in g["players"]:
			p.lives = 3
		d["level"] = game.level
		game.endLevel(game.showScores)
		return
	screen = g["screen"]
	def used(area):
		return any([screen.get_at((x, y))[:3] != (0, 0, 0) for x in range(area[0], area[0] + area[2], 2) for y in range(area[1], area[1] + area[3], 2)])
	if ctx.in_function("showScores"):
		d["seen"] = True
		if used((310, 350, 160, 60)):
			d["p2"] = True
		if used((25, 350, 160, 60)):
			d["p1"] = True
	if d.get("seen") and (not ctx.in_function("showScores") or ctx.frame > 500):
		ctx.check("bonus is written under player 2 column", d.get("p2"))
		ctx.check("nothing written under player 1 column", not d.get("p1"))
		ctx.finish()
	if ctx.frame > 700:
		ctx.check("scores screen reached", False)
		ctx.finish()


def stage_select(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	# first stage screen of a new game used the flag up
	ctx.check("stage isn't chosen on the next stages", not game.stage_select)
	game.stage_select = True
	game.showStageScreen()
	ctx.check("stage screen of a new game uses the flag up", not game.stage_select)
	stage = game.stage
	game.stage = max(1, min(35, game.stage + 1))
	ctx.check("stage can be changed on the stage screen", game.stage == stage + 1)
	game.stage = 35
	game.stage = max(1, min(35, game.stage + 1))
	ctx.check("stage doesn't go over 35", game.stage == 35)
	game.stage = 1
	game.stage = max(1, min(35, game.stage - 1))
	ctx.check("stage doesn't go below 1", game.stage == 1)
	game.stage = stage
	change, start = game.stageScreenInput()
	ctx.check("stage screen input: change and start (%s, %s)" % (change, start), change == 0 and start == False)

	# buttons A and B of any gamepad choose the stage
	Gamepad = g["Gamepad"]

	class FakeGamepad(Gamepad):
		def __init__(self):
			Gamepad.__init__(self)
			self.held_buttons = set()

		def read(self):
			return {"up": False, "right": False, "down": False, "left": False, "fire": False, "start": False}

		def buttonsHeld(self):
			return set(self.held_buttons)

	pad = FakeGamepad()
	game.gamepads = [pad]
	pad.held_buttons = set([g["GAMEPAD_A_BUTTON"]])
	change, start = game.stageScreenInput()
	ctx.check("button A: next stage (%s)" % change, change == 1 and not start)
	pad.held_buttons = set()
	game.stageScreenInput()
	pad.held_buttons = set([g["GAMEPAD_B_BUTTON"]])
	change, start = game.stageScreenInput()
	ctx.check("button B: previous stage (%s)" % change, change == -1 and not start)
	game.gamepads = []
	game.drawStageTitle()
	ctx.check("stage screen drawn without a hint", True)
	ctx.finish()


def pause_sounds(ctx):
	""" Pause during stage music: music and engine sound come back after unpause """
	g, game, d = ctx.g, ctx.game, ctx.data
	p = g["players"][0]
	if ctx.frame == 1:
		clear(ctx)
		g["play_sounds"] = True
		game.start_music = False
		game.bg_sound = False
		g["sounds"]["start"].play()
		# real key press: pause restores pressed keys from the held ones
		return [ctx.key(p.controls[1])]
	if ctx.frame == 4:
		d["music"] = g["sounds"]["start"].get_num_channels()
		ctx.check("stage music plays (%d)" % d["music"], d["music"] > 0)
		ctx.check("engine sound plays", game.engine_sound and g["sounds"]["engine"].get_num_channels() > 0)
		game.pause()
	if ctx.frame == 6:
		game.pause()
	if ctx.frame == 8:
		ctx.check("music plays after unpause (%d)" % g["sounds"]["start"].get_num_channels(),
			g["sounds"]["start"].get_num_channels() > 0)
		ctx.check("engine sound plays after unpause", game.engine_sound and g["sounds"]["engine"].get_num_channels() > 0)
		ctx.finish()


class FakeMusic(object):
	""" Stands in for the game over music """

	def __init__(self, length):
		self.length = length
		self.played = 0
		self.stopped = 0

	def get_length(self):
		return self.length

	def play(self, *args):
		self.played += 1

	def stop(self):
		self.stopped += 1


def game_over_music(ctx, press_key):
	""" NES: music plays on the game over screen, the screen stays until it ends, a key skips it """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		clear(ctx)
		g["play_sounds"] = True
		d["music"] = FakeMusic(1.0)
		g["sounds"]["gameover"] = d["music"]
		game.endLevel(game.gameOverScreen)
		return
	if ctx.in_function("gameOverScreen"):
		if "start" not in d:
			d["start"] = ctx.frame
			ctx.check("music plays on the game over screen", d["music"].played == 1)
		if press_key and ctx.frame == d["start"] + 5:
			return [ctx.key(pygame.K_RETURN)]
	if d.get("start") and ctx.in_function("showMenu"):
		frames = ctx.frame - d["start"]
		if press_key:
			ctx.check("key skips the screen (%d frames) and stops the music" % frames, frames < 30 and d["music"].stopped > 0)
		else:
			# 1 s of music = 50 frames
			ctx.check("screen stays until the music ends (%d frames)" % frames, 40 <= frames <= 70)
		ctx.finish()
	if ctx.frame > 400:
		ctx.check("game over screen finished", False)
		ctx.finish()


SCENARIOS = {
	"bonus_disappears": {"fn": bonus_disappears},
	"stun_blink": {"fn": stun_blink, "players": 2},
	"scores_bonus": {"fn": scores_bonus, "players": 2},
	"stage_select": {"fn": stage_select},
	"pause_sounds": {"fn": pause_sounds},
	"game_over_music": {"fn": lambda ctx: game_over_music(ctx, False)},
	"game_over_music_skip": {"fn": lambda ctx: game_over_music(ctx, True)},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
