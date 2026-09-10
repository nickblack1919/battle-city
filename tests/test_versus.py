""" Versus mode: two castles, players hurt each other, winner screen """

import harness
import pygame


def versus_menu(ctx):
	game = ctx.game
	if ctx.menu_frame == 1:
		return [ctx.key(pygame.K_RETURN)]
	if ctx.menu_frame == 2:
		labels = [item[0] for item in game.menuItems()]
		ctx.check("menu has VERSUS: %s" % labels, "VERSUS" in labels)
		# 1 press down to VERSUS
		game.menu_index = labels.index("VERSUS") - 1
		return [ctx.key(pygame.K_DOWN)]
	if ctx.menu_frame == 3:
		return [ctx.key(pygame.K_RETURN)]
	return []


def setup_match(ctx):
	g, game = ctx.g, ctx.game
	players, castle2 = g["players"], g["castle2"]
	p1, p2 = players
	ctx.check("versus mode with 2 players", game.mode == "versus" and len(players) == 2)
	ctx.check("second castle at the top", castle2 != None and castle2.rect.topleft == (192, 0) and castle2.owner == 1)
	ctx.check("player 2 starts at the top facing down", p2.rect.top == 0 and p2.direction == p2.DIR_DOWN)
	for p in players:
		p.shielded = False
	return p1, p2, castle2


def bullet_at(ctx, owner, target_rect, direction):
	Bullet = ctx.g["Bullet"]
	bullet = Bullet(ctx.game.level, [target_rect.left, target_rect.top], direction)
	bullet.owner = Bullet.OWNER_PLAYER
	bullet.owner_class = owner
	bullet.rect.topleft = [target_rect.left + 12, target_rect.top + 12]
	ctx.g["bullets"].append(bullet)
	return bullet


def castle_destroyed(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 10:
		p1, p2, castle2 = setup_match(ctx)

		# own bullet doesn't hurt own tank
		bullet = bullet_at(ctx, p1, p1.rect, p1.DIR_UP)
		bullet.update()
		ctx.check("own bullet doesn't hurt own tank", p1.state == p1.STATE_ALIVE)

		# player 1 destroys castle of player 2
		bullet = bullet_at(ctx, p1, castle2.rect, p1.DIR_UP)
		bullet.update()
		ctx.check("castle 2 destroyed by player 1 bullet", not castle2.active)

	if ctx.frame == 100:
		ctx.check("no enemies in versus", len(g["enemies"]) == 0 and len(game.level.enemies_left) == 0)

	if ctx.frame > 10 and ctx.in_function("showVersusResult") and "result" not in d:
		d["result"] = True
		ctx.check("player 1 wins when castle 2 is destroyed", game.versus_winner == 0)
		return [ctx.key(pygame.K_RETURN)]

	if "result" in d and ctx.in_function("showMenu"):
		ctx.check("result screen returns to menu", True)
		ctx.finish()


def menu_after_result(ctx):
	# game.level stays set after versus, so menu frames come to scenario function
	return castle_destroyed(ctx)


def kill_and_lives(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 10:
		p1, p2, castle2 = setup_match(ctx)
		p2.lives = 1
		bullet = bullet_at(ctx, p1, p2.rect, p1.DIR_UP)
		bullet.update()
		ctx.check("player 1 bullet destroys player 2", p2.state == p2.STATE_EXPLODING)
		ctx.check("kill counted", p1.versus_kills == 1)

	if ctx.frame > 10 and game.game_over and "over" not in d:
		d["over"] = True
		ctx.check("player 2 without lives loses", game.versus_winner == 0)
		ctx.finish()


def bonus(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 10:
		setup_match(ctx)
		game.spawnVersusBonus()
		bonuses = g["bonuses"]
		Bonus = g["Bonus"]
		ctx.check("versus bonus spawned", len(bonuses) == 1)
		ctx.check("versus bonus is useful in duel", bonuses[0].bonus in (Bonus.BONUS_STAR, Bonus.BONUS_HELMET, Bonus.BONUS_TANK, Bonus.BONUS_SHIP))
		ctx.finish()


SCENARIOS = {
	"castle_destroyed": {"fn": menu_after_result, "menu": versus_menu},
	"kill_and_lives": {"fn": kill_and_lives, "menu": versus_menu},
	"bonus": {"fn": bonus, "menu": versus_menu},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
