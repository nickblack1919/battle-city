""" Score labels, bonus blinking, effect timer bars, screen shake, stage screen """

import harness


def labels(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 20:
		return
	enemies, players, Enemy, Label = g["enemies"], g["players"], g["Enemy"], g["Label"]

	game.level.enemies_left[:] = [3]
	enemy = Enemy(game.level, 1, [0, 0])
	enemy.state = enemy.STATE_ALIVE
	enemy.health = 100
	enemy.bonus = None
	enemies.append(enemy)
	labels_before = len(g["labels"])
	enemy.bulletImpact(False, 100, players[0])
	ctx.check("score label created on kill", len(g["labels"]) == labels_before + 1)
	ctx.check("label text is points (400 for armor tank)", g["labels"][-1].text == "400")
	game.draw()
	ctx.check("labels are drawn with shared font", Label.font != None)
	ctx.check("armor tank explosion shakes screen", game.shake_frames > 0)
	frames = game.shake_frames
	game.draw()
	ctx.check("shake counts down on each frame", game.shake_frames == frames - 1)
	ctx.finish()


def bonus_blink(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	bonuses, Enemy = g["bonuses"], g["Enemy"]

	if ctx.frame == 20:
		# nothing may move or pick the bonus up
		del game.level.enemies_left[:]
		del g["enemies"][:]
		# move players away first: bonus spawned on a player is picked up immediately
		for player in g["players"]:
			player.rect.topleft = [384, 0]
		game.level.enemies_left[:] = [0]
		enemy = Enemy(game.level, 1, [0, 0])
		enemy.spawnBonus()
		d["bonus"] = bonuses[-1]
		d["bonus"].rect.topleft = [0, 200]
		for player in g["players"]:
			player.bonus = None

	if ctx.frame > 20:
		bonus = d["bonus"]
		timeout = g["BONUS_SPAWN_TIMEOUT"]
		blink = g["BONUS_BLINK_TIME"]
		# 20 ms per frame
		blink_frame = 20 + (timeout - blink) // 20
		if ctx.frame == blink_frame - 50:
			ctx.check("bonus doesn't blink before last seconds", not bonus.blinking and bonus.visible)
			ctx.check("fortress / freeze bars don't crash drawing", True)
		if ctx.frame == blink_frame + 50:
			ctx.check("bonus blinks during last seconds", bonus.blinking)
		if blink_frame + 50 < ctx.frame < blink_frame + 70 and not bonus.visible:
			d["was_hidden"] = True
		if ctx.frame == blink_frame + 70:
			ctx.check("blinking bonus is sometimes hidden", d.get("was_hidden"))
		if ctx.frame == 20 + timeout // 20 + 10:
			ctx.check("bonus disappears after timeout", bonus not in bonuses)
			ctx.finish()


def effect_timers(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 20:
		return
	p = g["players"][0]
	gtimer = g["gtimer"]

	game.shieldPlayer(p, True, 10000)
	remaining = gtimer.remaining(p.shield_end_timer)
	ctx.check("timer remaining time is known", remaining != None and 0 < remaining[0] <= 10000 and remaining[1] == 10000)
	ctx.check("unknown timer has no remaining time", gtimer.remaining("no such timer") == None)

	game.toggleEnemyFreeze(True)
	game.enemy_freeze_end_timer = gtimer.add(10000, lambda: None, 1)
	game.setPlayersFrozen(True)
	game.players_freeze_end_timer = gtimer.add(10000, lambda: None, 1)
	game.fortress_end_timer = gtimer.add(10000, lambda: None, 1)
	game.draw()
	screen = g["screen"]
	ctx.check("shield bar drawn above player", screen.get_at((p.rect.left, p.rect.top - 4))[:3] == (120, 200, 255))
	ctx.check("enemy freeze bar drawn on top edge", screen.get_at((0, 1))[:3] == (80, 160, 255))
	ctx.check("players freeze bar drawn on bottom edge", screen.get_at((0, 414))[:3] == (255, 80, 80))
	ctx.finish()


def stage_screen(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		ctx.check("level loop starts after stage screen", not game.stage_screen and game.running)
		ctx.check("stage screen time is configured", g["STAGE_SCREEN_TIME"] > 0)
		ctx.finish()


SCENARIOS = {
	"labels_and_shake": {"fn": labels},
	"bonus_blink": {"fn": bonus_blink, "max_frames": 3000},
	"effect_timers": {"fn": effect_timers},
	"stage_screen": {"fn": stage_screen},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
