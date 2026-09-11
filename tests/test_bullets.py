""" Bullets like on NES: spawn on tank's edge, bullet slot busy while bullet explodes, auto fire switch """

import harness
import pygame


def player_bullets(ctx):
	return [b for b in ctx.g["bullets"] if b.owner_class is ctx.g["players"][0]]


def prepare(ctx):
	g = ctx.g
	del ctx.game.level.enemies_left[:]
	del g["enemies"][:]
	p = g["players"][0]
	p.shielded = True
	return p


def spawn_position(ctx):
	g = ctx.g
	if ctx.frame != 1:
		return
	p = prepare(ctx)
	Bullet = g["Bullet"]
	x, y = 192, 192
	centers = {}
	for direction in (Bullet.DIR_UP, Bullet.DIR_RIGHT, Bullet.DIR_DOWN, Bullet.DIR_LEFT):
		centers[direction] = Bullet(ctx.game.level, [x, y], direction).rect.center
	ctx.check("bullet center appears on tank's edge: %s" % centers, centers == {
		Bullet.DIR_UP: (x + 16, y), Bullet.DIR_RIGHT: (x + 32, y + 16),
		Bullet.DIR_DOWN: (x + 16, y + 32), Bullet.DIR_LEFT: (x, y + 16)})
	ctx.finish()


def slot_busy_while_exploding(ctx):
	g, d = ctx.g, ctx.data
	p = prepare(ctx) if ctx.frame == 1 else g["players"][0]
	if ctx.frame == 1:
		# level 1: brick right above player 1 start (column 8-9, row 22 is free, fire left into bricks at columns 6-7)
		p.rotate(p.DIR_LEFT, False)
		ctx.check("bullet fired", p.fire())
	if ctx.frame == 2:
		bullets = player_bullets(ctx)
		d["bullet"] = bullets[0] if bullets else None
	if ctx.frame > 2 and "exploding_frame" not in d and d["bullet"] and d["bullet"].state == d["bullet"].STATE_EXPLODING:
		d["exploding_frame"] = ctx.frame
		ctx.check("can't fire while own bullet explodes", not p.fire())
	if "exploding_frame" in d and d["bullet"].state == d["bullet"].STATE_REMOVED and "removed_frame" not in d:
		d["removed_frame"] = ctx.frame
		frames = d["removed_frame"] - d["exploding_frame"]
		expected = g["BULLET_EXPLOSION_TIME"] // 20
		ctx.check("explosion lasts 9 NES frames (%d frames, expected about %d)" % (frames, expected), abs(frames - expected) <= 2)
	if "removed_frame" in d and ctx.frame == d["removed_frame"] + 1:
		ctx.check("can fire again after explosion", p.fire())
		ctx.finish()
	if ctx.frame > 200:
		ctx.check("bullet exploded on bricks", False)
		ctx.finish()


def auto_fire_off(ctx):
	g, d = ctx.g, ctx.data
	if ctx.frame == 1:
		p = prepare(ctx)
		p.rotate(p.DIR_UP, False)
		g["AUTO_FIRE"] = False
		d["seen"] = set()
		return [ctx.key(p.controls[0])]
	p = g["players"][0]
	for bullet in player_bullets(ctx):
		d["seen"].add(id(bullet))
	if ctx.frame == 150:
		ctx.check("auto fire off: holding fire shoots once (%d)" % len(d["seen"]), len(d["seen"]) == 1)
		ctx.finish()


def point_blank_tank(ctx):
	""" Auto fire at enemy right next to player: bullet explodes on the tank, next shot waits for explosion """
	g, d = ctx.g, ctx.data
	if ctx.frame == 1:
		p = prepare(ctx)
		Enemy = g["Enemy"]
		ctx.game.level.enemies_left[:] = [Enemy.TYPE_ARMOR]
		# level 1, row 24: free cells left of player 1
		enemy = Enemy(ctx.game.level, 1, [p.rect.left - 32, p.rect.top])
		enemy.state = enemy.STATE_ALIVE
		enemy.aquired_position = True
		enemy.paused = True
		enemy.bonus = None
		enemy.health = 100000
		g["enemies"].append(enemy)
		g["AUTO_FIRE"] = True
		p.rotate(p.DIR_LEFT, False)
		d["enemy"] = enemy
		d["hits"] = 0
		d["health"] = enemy.health
		return [ctx.key(p.controls[0])]

	enemy = d["enemy"]
	if enemy.health < d["health"]:
		d["hits"] += (d["health"] - enemy.health) // 100
		d["health"] = enemy.health
		if "first_hit" not in d:
			d["first_hit"] = True
			bullets = player_bullets(ctx)
			ctx.check("bullet explodes on the tank", bullets and bullets[0].state == bullets[0].STATE_EXPLODING)
	if ctx.frame == 61:
		# slot of bullet exploded on a tank is free after 5 NES frames: about 7 frames per hit
		# (whole NES explosion gave about 11 frames, no slot rule gave 5)
		ctx.check("point blank auto fire: %d hits in 60 frames (7-11)" % d["hits"], 7 <= d["hits"] <= 11)
		ctx.finish()


def head_on_duel(ctx):
	""" Player shooting first at point blank kills armor tank even if the tank fires all the time """
	g, d = ctx.g, ctx.data
	if ctx.frame == 1:
		p = prepare(ctx)
		p.shielded = False
		Enemy = g["Enemy"]
		ctx.game.level.enemies_left[:] = [Enemy.TYPE_ARMOR]
		enemy = Enemy(ctx.game.level, 1, [p.rect.left - 32, p.rect.top])
		enemy.state = enemy.STATE_ALIVE
		enemy.aquired_position = True
		enemy.bonus = None
		enemy.health = 400
		enemy.rotate(enemy.DIR_RIGHT, False)
		# enemy stands and faces player
		enemy.paused = False
		enemy.speed = 0
		g["enemies"].append(enemy)
		g["AUTO_FIRE"] = True
		p.rotate(p.DIR_LEFT, False)
		d["enemy"] = enemy
		return [ctx.key(p.controls[0])]
	if ctx.frame == 3:
		# after player's first shot enemy fires whenever its bullet slot is free
		g["CHANCE_OF_FIRE"] = 100
	enemy, p = d["enemy"], g["players"][0]
	if ctx.frame == 150 or enemy.state != enemy.STATE_ALIVE or p.state != p.STATE_ALIVE:
		ctx.check("head-on: armor tank destroyed (%s), player alive (%s)" % (enemy.state, p.state),
			enemy.state != enemy.STATE_ALIVE and p.state == p.STATE_ALIVE)
		ctx.finish()


def helmet_absorbs(ctx):
	g = ctx.g
	if ctx.frame != 1:
		return
	p = prepare(ctx)
	Enemy, Bullet = g["Enemy"], g["Bullet"]
	ctx.game.level.enemies_left[:] = [Enemy.TYPE_BASIC]
	enemy = Enemy(ctx.game.level, 1, [0, 0])
	bullet = Bullet(ctx.game.level, [p.rect.left, p.rect.top], Bullet.DIR_DOWN)
	bullet.owner = Bullet.OWNER_ENEMY
	bullet.owner_class = enemy
	bullet.rect.topleft = [p.rect.left + 12, p.rect.top + 12]
	g["bullets"].append(bullet)
	bullet.update()
	ctx.check("bullet vanishes on helmet (no explosion)", bullet.state == bullet.STATE_REMOVED and p.state == p.STATE_ALIVE)
	ctx.finish()


SCENARIOS = {
	# auto fire delay uses real time
	"point_blank_tank": {"fn": point_blank_tank, "real_time": True},
	"head_on_duel": {"fn": head_on_duel, "real_time": True},
	"helmet_absorbs": {"fn": helmet_absorbs},
	"spawn_position": {"fn": spawn_position},
	"slot_busy_while_exploding": {"fn": slot_busy_while_exploding},
	"auto_fire_off": {"fn": auto_fire_off},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
