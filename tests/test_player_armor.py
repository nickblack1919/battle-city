""" Armor from superpowers: from the 3rd one player's tank takes one hit more """

import harness


def hit(ctx, tank, enemy):
	tank.bulletImpact(False, 100, enemy, tank.DIR_UP)


def armor(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	del game.level.enemies_left[:]
	del g["enemies"][:]
	Enemy = g["Enemy"]
	game.level.enemies_left[:] = [Enemy.TYPE_BASIC]
	enemy = Enemy(game.level, 1, [0, 0])
	del game.level.enemies_left[:]
	enemy.state = enemy.STATE_ALIVE
	g["enemies"].append(enemy)

	p = g["players"][0]
	p.shielded = False
	p.health = g["PLAYER_START_HEALTH"]
	for superpowers in (0, 1, 2):
		p.superpowers = superpowers
		p.updateSuperpowers()
	ctx.check("no armor below 3rd superpower (%d)" % p.health, p.health == g["PLAYER_START_HEALTH"])

	p.superpowers = 3
	p.updateSuperpowers()
	ctx.check("3rd superpower: armor (%d)" % p.health, p.health == g["PLAYER_START_HEALTH"] * 2)

	hit(ctx, p, enemy)
	ctx.check("survives first hit (%d)" % p.health, p.state == p.STATE_ALIVE and p.health == g["PLAYER_START_HEALTH"])
	p.superpowers = 4
	p.updateSuperpowers()
	ctx.check("more superpowers don't add more armor (%d)" % p.health, p.health == g["PLAYER_START_HEALTH"] * 2)
	hit(ctx, p, enemy)
	hit(ctx, p, enemy)
	ctx.check("second hit destroys tank", p.state != p.STATE_ALIVE)

	# enemies don't get armor from superpowers
	enemy.superpowers = 4
	health = enemy.health
	enemy.updateSuperpowers()
	ctx.check("enemy superpowers give no armor (%d)" % enemy.health, enemy.health == health)
	ctx.finish()


def respawn(ctx):
	""" Armor is gone after respawn (superpowers are reset) """
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	p = g["players"][0]
	p.superpowers = 3
	p.updateSuperpowers()
	p.reset()
	ctx.check("respawned tank without armor (%d, superpowers %d)" % (p.health, p.superpowers),
		p.health == g["PLAYER_START_HEALTH"] and p.superpowers == g["PLAYER_START_SUPERPOWER"])
	ctx.finish()


SCENARIOS = {
	"armor": {"fn": armor},
	"respawn": {"fn": respawn},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
