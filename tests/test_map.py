""" Map mechanics: brick quarters, fortress, ice sliding, ship bonus """

import harness


def clear_enemies(ctx):
	del ctx.game.level.enemies_left[:]
	del ctx.g["enemies"][:]


def bricks_in(level, rect, tile_type):
	return [tile for tile in level.mapr if tile.type == tile_type and tile.colliderect(rect)]


def brick_quarters(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 10:
		return
	clear_enemies(ctx)
	level, Bullet, pygame = game.level, g["Bullet"], harness.pygame

	all_bricks = [tile for tile in level.mapr if tile.type == level.TILE_BRICK]
	ctx.check("bricks are 8x8 quarters", all_bricks and all([tile.width == 8 and tile.height == 8 for tile in all_bricks]))

	# level 1, columns 2-3, row 23: bricks; shoot up from below
	area = pygame.Rect(32, 368, 32, 16)
	before = len(bricks_in(level, area, level.TILE_BRICK))
	bullet = Bullet(level, [32, 392], Bullet.DIR_UP)
	for i in range(20):
		bullet.update()
		if bullet.state != bullet.STATE_ACTIVE:
			break
	after = len(bricks_in(level, area, level.TILE_BRICK))
	ctx.check("brick row under bullet exists (%d quarters)" % before, before == 8)
	ctx.check("bullet destroys only nearest half of bricks (%d -> %d)" % (before, after), after == 6)

	# fortress: steel, then bricks again - no overlapping tiles
	level.buildFortress(level.TILE_STEEL)
	level.buildFortress(level.TILE_BRICK)
	fortress_area = pygame.Rect(176, 368, 64, 48)
	tiles = [tile for tile in level.mapr if tile.colliderect(fortress_area)]
	overlapping = [1 for a in tiles for b in tiles if a is not b and a.colliderect(b)]
	ctx.check("fortress tiles don't overlap", not overlapping)
	ctx.check("fortress rebuilt from brick quarters (%d)" % len(bricks_in(level, fortress_area, level.TILE_BRICK)),
		len(bricks_in(level, fortress_area, level.TILE_BRICK)) == 32)
	ctx.finish()


def add_tiles(ctx, tile_type, x_range, y_range):
	level, myRect = ctx.game.level, ctx.g["myRect"]
	for x in x_range:
		for y in y_range:
			level.mapr.append(myRect(x, y, 16, 16, tile_type))
	level.updateObstacleRects()
	level.updateRemovableRects()


def ice_slide(ctx, with_ice):
	g, d = ctx.g, ctx.data
	p = g["players"][0]
	if ctx.frame == 5:
		clear_enemies(ctx)
		p.shielded = True
		if with_ice:
			add_tiles(ctx, ctx.game.level.TILE_FROZE, (128, 144), range(320, 416, 16))
		p.pressed = [True, False, False, False]
	if ctx.frame == 10:
		p.pressed = [False] * 4
		d["y"] = p.rect.top
	if ctx.frame == 30:
		distance = d["y"] - p.rect.top
		if with_ice:
			ctx.check("tank slides on ice after release (%d px)" % distance, 0 < distance <= g["ICE_SLIDE_DISTANCE"] + p.speed)
		else:
			ctx.check("tank stops immediately without ice (%d px)" % distance, distance == 0)
		ctx.finish()


def ship(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	p = g["players"][0]
	Bonus = g["Bonus"]

	if ctx.frame == 5:
		clear_enemies(ctx)
		p.shielded = True
		# water in front of player 1 (row 22, columns 8-9)
		add_tiles(ctx, game.level.TILE_WATER, (128, 144), (352,))
		p.pressed = [True, False, False, False]
	if ctx.frame == 30:
		p.pressed = [False] * 4
		ctx.check("water blocks tank without ship (top %d)" % p.rect.top, p.rect.top >= 368)
		bonus = Bonus(game.level)
		bonus.bonus = bonus.BONUS_SHIP
		ctx.check("ship bonus has sprite", len([1 for x in range(32) for y in range(32) if bonus.image.get_at((x, y))[:3] != (0, 0, 0)]) > 20)
		game.triggerBonus(bonus, p)
		ctx.check("ship bonus active", p.ship and p.ship_timer)
		p.pressed = [True, False, False, False]
	if ctx.frame == 60:
		p.pressed = [False] * 4
		ctx.check("tank with ship drives over water (top %d)" % p.rect.top, p.rect.top < 352)
		# ship ends while tank is on water
		p.rect.topleft = [128, 344]
		game.endShip(p)
		ctx.check("tank still on water can move after ship ended", p.canSwim())
		p.pressed = [False, False, True, False]
	if ctx.frame == 80:
		p.pressed = [False] * 4
		ctx.check("tank drove out of water", p.rect.top >= 368 and not p.canSwim())

		# enemies ship
		bonus = Bonus(game.level)
		bonus.bonus = bonus.BONUS_SHIP
		game.triggerEnemyBonus(bonus, None)
		game.level.enemies_left[:] = [0]
		enemy = g["Enemy"](game.level, 1, [0, 0])
		ctx.check("enemies with ship bonus can swim", game.enemies_ship and enemy.canSwim())
		game.setEnemiesShip(False)
		ctx.check("enemies ship ends", not enemy.canSwim())
		ctx.finish()


SCENARIOS = {
	"brick_quarters": {"fn": brick_quarters},
	"ice_slide": {"fn": lambda ctx: ice_slide(ctx, True)},
	"no_ice_no_slide": {"fn": lambda ctx: ice_slide(ctx, False)},
	"ship": {"fn": ship},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
