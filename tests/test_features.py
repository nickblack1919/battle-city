""" Start level argument, controls, presets, frontal armor, castle protection """

import harness
import pygame


def features(ctx):
	if ctx.frame != 20:
		return

	g, game = ctx.g, ctx.game
	players, castle = g["players"], g["castle"]
	Enemy, Bullet = g["Enemy"], g["Bullet"]
	p1, p2 = players[0], players[1]

	ctx.check("started on level from -l argument", game.stage == 3)
	ctx.check("P1 controls: WASD + J", p1.controls == [pygame.K_j, pygame.K_w, pygame.K_d, pygame.K_s, pygame.K_a])
	ctx.check("P2 controls: arrows + right Shift", p2.controls == [pygame.K_RSHIFT, pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT])

	# frontal armor at superpower 5
	p1.shielded = False
	p1.superpowers = 5
	p1.updateSuperpowers()
	ctx.check("player protected at superpower 5", p1.protected)
	p1.rotate(p1.DIR_UP, False)
	p1.health = 100
	p1.bulletImpact(False, 100, None, Bullet.DIR_DOWN)
	ctx.check("front hit doesn't hurt protected player", p1.health == 100 and p1.state == p1.STATE_ALIVE)
	p1.superpowers = 1
	p1.updateSuperpowers()
	ctx.check("protection removed when superpowers reset", not p1.protected)

	# enemies never get protection
	game.level.enemies_left[:] = [0]
	enemy = Enemy(game.level, 1, [0, 0])
	enemy.superpowers = 9
	enemy.updateSuperpowers()
	ctx.check("enemy doesn't get frontal armor", not enemy.protected)
	ctx.check("enemy doesn't protect castle", not castle.protected)

	# castle protection at superpower 9
	p1.superpowers = 9
	p1.updateSuperpowers()
	ctx.check("castle protected at player superpower 9", castle.protected)
	enemy.state = enemy.STATE_ALIVE
	bullet = Bullet(game.level, [castle.rect.left, castle.rect.top - 32], Bullet.DIR_DOWN)
	bullet.owner = Bullet.OWNER_ENEMY
	bullet.owner_class = enemy
	bullet.rect.topleft = [castle.rect.left + 12, castle.rect.top + 4]
	g["bullets"].append(bullet)
	bullet.update()
	ctx.check("protected castle survives enemy hit", castle.active and not castle.protected)
	ctx.check("enemy shooter explodes", enemy.state == enemy.STATE_EXPLODING)

	# players overlapping right after respawn
	game.respawnPlayer(p2)
	p2.rect.topleft = p1.rect.topleft
	p1.move(p1.DIR_UP)
	p2.move(p2.DIR_UP)
	ctx.check("players overlapping after respawn don't crash", True)
	ctx.finish()


SCENARIOS = {
	"features": {"fn": features, "players": 2, "argv": ["-l", "3"]},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
