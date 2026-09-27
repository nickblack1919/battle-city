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
	ctx.check("stage screen reads input", hasattr(game, "stageScreenInput") and hasattr(game, "drawStageTitle"))
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


SCENARIOS = {
	"bonus_disappears": {"fn": bonus_disappears},
	"stun_blink": {"fn": stun_blink, "players": 2},
	"scores_bonus": {"fn": scores_bonus, "players": 2},
	"stage_select": {"fn": stage_select},
	"pause_sounds": {"fn": pause_sounds},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
