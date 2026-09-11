""" NES rules: walls checked by front corner cells, ice, NES stars, tank explosions, bonus places """

import harness


def clear(ctx):
	g, game = ctx.g, ctx.game
	del game.level.enemies_left[:]
	del g["enemies"][:]
	for p in g["players"]:
		p.shielded = True


def wall_cell(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	clear(ctx)
	p = g["players"][0]
	level, myRect = game.level, g["myRect"]
	level.mapr = []
	# one brick quarter in top right corner of cell (13, 11), right above the tank
	level.mapr.append(myRect(216, 176, 8, 8, level.TILE_BRICK))
	level.updateObstacleRects()
	p.rect.topleft = [192, 192]
	p.rotate(p.DIR_UP, False)
	ctx.check("tank doesn't overlap brick quarter", p.rect.collidelist(level.obstacle_rects) == -1)
	ctx.check("cell with one brick quarter blocks tank", not p.move(p.DIR_UP, 1) and p.rect.topleft == (192, 192))
	# quarter behind the front corners doesn't matter: cell (14, 11) isn't under the front edge
	level.mapr = [myRect(224, 176, 8, 8, level.TILE_BRICK)]
	level.updateObstacleRects()
	ctx.check("brick next to front edge doesn't block", p.move(p.DIR_UP, 1) and p.rect.topleft == (192, 191))
	ctx.finish()


def stars(ctx):
	g = ctx.g
	if ctx.frame != 1:
		return
	clear(ctx)
	g["applyPreset"]("CLASSIC")
	p = g["players"][0]
	result = []
	for superpowers in range(6):
		p.superpowers = superpowers
		p.updateSuperpowers()
		result.append((p.bullet_speed == g["FAST_BULLET_SPEED"], p.max_active_bullets, p.bullet_power, p.protected))
	fast, slow = True, False
	ctx.check("NES stars: %s" % result, result == [
		(slow, 1, 1, False), (fast, 1, 1, False), (fast, 2, 1, False),
		(fast, 2, 3, False), (fast, 2, 3, False), (fast, 2, 3, False)])

	# 3rd star bullet: whole brick cell, grass stays
	game, Bullet, myRect = ctx.game, g["Bullet"], g["myRect"]
	level = game.level
	level.mapr = []
	for x in (192, 200, 208, 216):
		for y in (160, 168):
			level.mapr.append(myRect(x, y, 8, 8, level.TILE_BRICK))
	level.mapr.append(myRect(192, 128, 16, 16, level.TILE_GRASS))
	level.updateObstacleRects()
	level.updateRemovableRects()
	bullet = Bullet(level, [192, 192], Bullet.DIR_UP)
	bullet.owner, bullet.owner_class, bullet.power = Bullet.OWNER_PLAYER, p, 3
	g["bullets"].append(bullet)
	for i in range(20):
		bullet.update()
	bricks = [t for t in level.mapr if t.type == level.TILE_BRICK]
	ctx.check("3rd star bullet destroys whole brick cells (%d quarters left)" % len(bricks), len(bricks) == 0)
	ctx.check("3rd star bullet doesn't clear grass", any(t.type == level.TILE_GRASS for t in level.mapr))
	ctx.finish()


def explosions(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	Enemy = g["Enemy"]
	if ctx.frame == 1:
		clear(ctx)
		d["tanks"] = {}
		for enemy_type, x in ((Enemy.TYPE_BASIC, 0), (Enemy.TYPE_FAST, 384)):
			game.level.enemies_left[:] = [enemy_type]
			enemy = Enemy(game.level, 1, [x, 0])
			enemy.state = enemy.STATE_ALIVE
			enemy.bonus = None
			g["enemies"].append(enemy)
			enemy.explode()
			d["tanks"][enemy_type] = enemy
		d["frames"] = {}
		return
	for enemy_type, enemy in d["tanks"].items():
		if enemy_type not in d["frames"] and not enemy.explosion.active:
			d["frames"][enemy_type] = ctx.frame - 1
	if len(d["frames"]) == 2 or ctx.frame > 100:
		basic, fast = d["frames"].get(Enemy.TYPE_BASIC), d["frames"].get(Enemy.TYPE_FAST)
		ctx.check("enemy explosion 48 NES frames (%s)" % basic, basic != None and abs(basic - 48) <= 3)
		ctx.check("fast enemy explosion 24 NES frames (%s)" % fast, fast != None and abs(fast - 24) <= 3)
		ctx.check("player explosion 32 NES frames", g["PLAYER_EXPLOSION_TIME"] == g["nesFrames"](32))
		ctx.finish()


def bonus_places(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	clear(ctx)
	p = g["players"][0]
	p.rect.center = (160, 160)
	centers = set()
	near = 0
	for i in range(300):
		bonus = g["Bonus"](game.level)
		centers.add(bonus.rect.center)
		if bonus.rect.center == p.rect.center:
			near += 1
	grid = set((x, y) for x in (64, 160, 256, 352) for y in (64, 160, 256, 352))
	ctx.check("bonus appears on NES grid (%d places)" % len(centers), centers <= grid and len(centers) >= 12)
	ctx.check("bonus doesn't appear under player (%d)" % near, near == 0)
	ctx.finish()


def ice(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	p = g["players"][0]
	if ctx.frame == 1:
		clear(ctx)
		level, myRect = game.level, g["myRect"]
		level.mapr = [myRect(x, y, 16, 16, level.TILE_FROZE) for x in range(0, 416, 16) for y in range(0, 416, 16)]
		level.updateObstacleRects()
		p.rect.topleft = [192, 320]
		p.rotate(p.DIR_UP, False)
		p.pressed = [True, False, False, False]
	if ctx.frame == 2:
		# turn left: ignored while tank slides
		p.pressed = [False, False, False, True]
		d["start"] = p.rect.topleft
	if ctx.frame == 6:
		ctx.check("buttons ignored at start of slide (%s -> %s)" % (d["start"], p.rect.topleft),
			p.direction == p.DIR_UP and p.rect.left == d["start"][0] and p.rect.top < d["start"][1])
		p.pressed = [False] * 4
	if ctx.frame == 80:
		distance = 320 - p.rect.top
		ctx.check("slide stops after NES distance (%d px)" % distance, distance <= g["ICE_SLIDE_DISTANCE"] + 2 * p.speed)
		ctx.finish()


SCENARIOS = {
	"wall_cell": {"fn": wall_cell},
	"stars": {"fn": stars},
	"explosions": {"fn": explosions},
	"bonus_places": {"fn": bonus_places},
	"ice": {"fn": ice},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
