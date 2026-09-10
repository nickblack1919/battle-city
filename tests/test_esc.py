""" ESC quits the game on every screen """

import harness


def gameover_animation(ctx):
	if ctx.frame == 20:
		ctx.g["castle"].destroy()
	if ctx.frame == 30:
		ctx.check("game over animation is running", ctx.game.game_over and ctx.in_function("nextLevel"))
		return ctx.expect_exit("ESC quits during game over animation")


def gameover_screen(ctx):
	if ctx.frame == 20:
		ctx.g["castle"].destroy()
	if ctx.frame > 30 and ctx.in_function("gameOverScreen") and not ctx.expecting_exit:
		return ctx.expect_exit("ESC quits on game over screen")


def scores(ctx):
	enemies = ctx.g["enemies"]
	# level finishes when last enemy is removed, so wait for first spawn
	if ctx.frame == 100:
		ctx.check("enemy spawned before finishing level", len(enemies) > 0)
		del ctx.game.level.enemies_left[:]
		for enemy in enemies:
			enemy.state = enemy.STATE_DEAD
	if ctx.frame > 100 and ctx.in_function("showScores") and not ctx.expecting_exit:
		return ctx.expect_exit("ESC quits on scores screen")


def menu_esc(ctx):
	pass


def menu(ctx):
	if ctx.menu_frame == 1:
		return [ctx.key(harness.pygame.K_RETURN)]
	if ctx.menu_frame == 3:
		return ctx.expect_exit("ESC quits in menu")
	return []


SCENARIOS = {
	"gameover_animation": {"fn": gameover_animation},
	"gameover_screen": {"fn": gameover_screen},
	"scores": {"fn": scores},
	"menu": {"fn": menu_esc, "menu": menu},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
