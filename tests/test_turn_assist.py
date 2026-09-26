""" Turning into a narrow passage: tank is put on the grid line where the passage is open """

import harness


def corridor(ctx):
	""" Horizontal corridor (rows 6-7) with a passage up at cells 3-4 (x 48..79) """
	g, game = ctx.g, ctx.game
	level, myRect = game.level, g["myRect"]
	del game.level.enemies_left[:]
	del g["enemies"][:]
	level.mapr = []
	for cx in range(26):
		for cy in range(6):
			if cy == 5 and cx in (3, 4):
				continue
			if cy in (0, 1, 2, 3, 4) and cx in (3, 4):
				continue
			level.mapr.append(myRect(cx * 16, cy * 16, 16, 16, level.TILE_STEEL))
		level.mapr.append(myRect(cx * 16, 8 * 16, 16, 16, level.TILE_STEEL))
	level.updateObstacleRects()
	p = g["players"][0]
	p.shielded = True
	return p


def into_passage(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	p = corridor(ctx)
	stuck = []
	for offset in range(16):
		p.rect.topleft = [48 + offset, 96]
		p.rotate(p.DIR_RIGHT, False)
		p.move_credit = 0
		for i in range(40):
			p.move(p.DIR_UP)
		if p.rect.top >= 96 or p.rect.left != 48:
			stuck.append((offset, p.rect.topleft))
	ctx.check("tank turns into 2 cells wide passage from any offset (stuck: %s)" % stuck, stuck == [])
	ctx.finish()


def no_passage(ctx):
	""" Wall without a passage: tank doesn't slide sideways and doesn't get into the wall """
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	p = corridor(ctx)
	# close the passage
	level, myRect = game.level, g["myRect"]
	for cx in (3, 4):
		for cy in range(6):
			level.mapr.append(myRect(cx * 16, cy * 16, 16, 16, level.TILE_STEEL))
	level.updateObstacleRects()
	positions = []
	for offset in (4, 10):
		p.rect.topleft = [48 + offset, 96]
		p.rotate(p.DIR_RIGHT, False)
		p.move_credit = 0
		for i in range(40):
			p.move(p.DIR_UP)
		positions.append(p.rect.topleft)
		ctx.check("tank stays out of walls (%s)" % (p.rect.topleft,), p.rect.collidelist(level.obstacle_rects) == -1)
	ctx.check("no passage: tank doesn't go up (%s)" % positions, all([position[1] == 96 for position in positions]))
	ctx.finish()


def assist_off(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	p = corridor(ctx)
	g["PLAYER_TURN_ASSIST"] = False
	p.rect.topleft = [50, 96]
	p.rotate(p.DIR_RIGHT, False)
	# rotate without grid fix: tank stays between cells
	p.rotate(p.DIR_UP, False)
	p.move_credit = 0
	for i in range(10):
		p.move(p.DIR_UP, 1)
	ctx.check("without assist tank between cells stays (%s)" % (p.rect.topleft,), p.rect.topleft == (50, 96))
	g["PLAYER_TURN_ASSIST"] = True
	for i in range(10):
		p.move(p.DIR_UP, 1)
	ctx.check("with assist tank slides to the passage (%s)" % (p.rect.topleft,), p.rect.left == 48)
	ctx.finish()


SCENARIOS = {
	"into_passage": {"fn": into_passage},
	"no_passage": {"fn": no_passage},
	"assist_off": {"fn": assist_off},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
