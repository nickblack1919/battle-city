""" Bonus timers, pause, visibility, shield timers, level transition, ESC on nested level """

import harness


def bugfixes(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	phase = d.get("phase", "level1")

	if phase == "level1" and ctx.frame == 80:
		players = g["players"]
		enemies = g["enemies"]
		p = players[0]
		b = g["Bonus"](game.level)

		# enemy TIMER freezes players, then player TIMER freezes enemies
		b.bonus = b.BONUS_TIMER
		game.triggerEnemyBonus(b, None)
		game.triggerBonus(b, p)
		ctx.check("player timer keeps players frozen", p.paralised and game.players_freeze_end_timer)
		game.pause()
		game.pause()
		ctx.check("unpause keeps players frozen", p.paralised)

		b.bonus = b.BONUS_HELMET
		game.triggerEnemyBonus(b, None)
		ctx.check("enemy helmet hides players", not p.visible)

		timers_before = len(g["gtimer"].timers)
		for i in range(5):
			game.shieldPlayer(p, True, 1000)
		ctx.check("no shield timer leak", len(g["gtimer"].timers) - timers_before <= 2)

		p.bonus = b
		p.shielded = False
		p.bulletImpact(False, 0, None)
		ctx.check("player hit while carrying bonus doesn't crash", True)

		# finish level
		del game.level.enemies_left[:]
		for enemy in enemies:
			enemy.state = enemy.STATE_DEAD
		d["phase"] = "wait_level2"

	elif phase == "wait_level2" and game.stage == 2 and game.running:
		p = g["players"][0]
		ctx.check("level 2 reached", True)
		ctx.check("player visible on level 2", p.visible)
		ctx.check("players not frozen on level 2", not p.paralised)
		d["phase"] = "esc"
		d["esc_frame"] = ctx.total_frames

	elif phase == "esc" and ctx.total_frames > d["esc_frame"] + 20:
		d["phase"] = "done"
		return ctx.expect_exit("ESC quits on level 2")


SCENARIOS = {
	"bugfixes": {"fn": bugfixes},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
