""" Enemy spawning and overlapping """

import harness


def overlap(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	enemies, players, Enemy = g["enemies"], g["players"], g["Enemy"]

	if ctx.frame == 20:
		del enemies[:]
		game.level.enemies_left[:] = [0, 0]
		e1 = Enemy(game.level, 1, [192, 0])
		e2 = Enemy(game.level, 1, [192, 0])
		del game.level.enemies_left[:]
		# both alive, not positioned, same direction and path
		for e in (e1, e2):
			e.state = e.STATE_ALIVE
			e.aquired_position = False
		e2.rotate(e1.direction, False)
		e2.path = [list(p) for p in e1.path]
		enemies.extend([e1, e2])
		for p in players:
			p.rect.topleft = [0, 384]
			p.shielded = True
		d["pair"] = (e1, e2)
		ctx.check("tanks start overlapped", e1.rect.colliderect(e2.rect))

	if ctx.frame > 20:
		e1, e2 = d["pair"]
		if "separated" not in d and not e1.rect.colliderect(e2.rect):
			d["separated"] = ctx.frame - 20
		if ctx.frame == 520:
			ctx.check("overlapped tanks separate (%s frames)" % d.get("separated"), "separated" in d)
			ctx.check("tanks don't overlap at the end", not e1.rect.colliderect(e2.rect))
			ctx.check("both tanks positioned", e1.aquired_position and e2.aquired_position)
			ctx.finish()


def spawn_free(ctx):
	g, game = ctx.g, ctx.game
	enemies, Enemy = g["enemies"], g["Enemy"]

	if ctx.frame == 20:
		del enemies[:]
		game.level.enemies_left[:] = [0, 0, 0, 0]
		blockers = []
		for pos in ([0, 0], [192, 0], [384, 0]):
			e = Enemy(game.level, 1, pos)
			e.state = e.STATE_ALIVE
			blockers.append(e)
		enemies.extend(blockers)
		ctx.check("all spawn points occupied -> no position", game.getFreeSpawningPosition() == None)
		n = len(enemies)
		game.spawnEnemy()
		ctx.check("no spawn on occupied points", len(enemies) == n)
		blockers[1].rect.topleft = [192, 200]
		ctx.check("free point is chosen", game.getFreeSpawningPosition() == [192, 0])
		game.spawnEnemy()
		ctx.check("enemy spawns on free point", len(enemies) == n + 1 and enemies[-1].rect.topleft == (192, 0))
		ctx.finish()


def enemy_on_player(ctx, enemy_frozen):
	""" Player respawned on top of enemy: they must be able to drive apart """
	g, game, d = ctx.g, ctx.game, ctx.data
	enemies, Enemy = g["enemies"], g["Enemy"]
	p = g["players"][0]

	if ctx.frame == 5:
		del enemies[:]
		# level 1, columns 20-21: free up and down (at player's start the enemy can be walled in
		# by fortress bricks and screen edge; then only player can drive away)
		p.rect.topleft = [320, 64]
		game.level.enemies_left[:] = [0]
		enemy = Enemy(game.level, 1, list(p.rect.topleft))
		del game.level.enemies_left[:]
		enemy.state = enemy.STATE_ALIVE
		enemy.aquired_position = True
		enemy.path = []
		enemies.append(enemy)
		p.aquired_position = True
		p.shielded = True
		d["enemy"] = enemy
		ctx.check("player and enemy on top of each other", p.rect.colliderect(enemy.rect))
		if enemy_frozen:
			game.toggleEnemyFreeze(True)
			# player drives up out of enemy
			p.pressed = [True, False, False, False]

	if ctx.frame == 5 + 150:
		enemy = d["enemy"]
		p.pressed = [False] * 4
		if enemy_frozen:
			ctx.check("player drove out of frozen enemy (player top %d)" % p.rect.top, not p.rect.colliderect(enemy.rect))
		else:
			ctx.check("enemy drove away from player (enemy %s, player %s)" % (enemy.rect.topleft, p.rect.topleft), not p.rect.colliderect(enemy.rect))
		ctx.finish()


SCENARIOS = {
	"player_leaves_enemy": {"fn": lambda ctx: enemy_on_player(ctx, True)},
	"enemy_leaves_player": {"fn": lambda ctx: enemy_on_player(ctx, False)},
	"overlap": {"fn": overlap},
	"spawn_free": {"fn": spawn_free},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
