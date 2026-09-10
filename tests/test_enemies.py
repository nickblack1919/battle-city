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


SCENARIOS = {
	"overlap": {"fn": overlap},
	"spawn_free": {"fn": spawn_free},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
