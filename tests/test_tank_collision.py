""" Tank vs tank collisions like on NES: occupied map cells + front corner points """

import harness


def empty_level(ctx):
	""" No tiles: only tanks can block """
	level = ctx.game.level
	del level.mapr[:]
	level.updateObstacleRects()
	level.updateRemovableRects()
	del ctx.game.level.enemies_left[:]
	del ctx.g["enemies"][:]


def still_enemy(ctx, position):
	g, game = ctx.g, ctx.game
	game.level.enemies_left[:] = [0]
	enemy = g["Enemy"](game.level, 1, list(position))
	del game.level.enemies_left[:]
	enemy.state = enemy.STATE_ALIVE
	enemy.aquired_position = True
	enemy.paused = True
	g["enemies"].append(enemy)
	return enemy


def drive(ctx, p, direction, frames):
	for i in range(frames):
		p.move(direction)


def cells(ctx):
	g = ctx.g
	if ctx.frame != 1:
		return
	empty_level(ctx)
	p = g["players"][0]
	p.shielded = True
	p.aquired_position = True
	enemy = still_enemy(ctx, (192, 192))
	tankCells = g["tankCells"]

	ctx.check("aligned tank marks 3 cells (not top left): %s" % sorted(tankCells(enemy)),
		tankCells(enemy) == set([(13, 13), (12, 13), (13, 12)]))
	enemy.rect.topleft = (200, 192)
	ctx.check("tank between cells horizontally marks only middle column: %s" % sorted(tankCells(enemy)),
		tankCells(enemy) == set([(13, 13), (13, 12)]))
	enemy.rect.topleft = (192, 192)

	# corner approach: moving tank's front corners hit only enemy's unmarked top left cell at first
	p.rect.topleft = (144, 176)
	drive(ctx, p, p.DIR_RIGHT, 100)
	overlap = p.rect.clip(enemy.rect)
	ctx.check("corner approach: small overlap doesn't block, stops at left 176 (left %d)" % p.rect.left, p.rect.left == 176)
	ctx.check("corner approach: tanks overlap 16x16 px like on NES (%dx%d)" % (overlap.width, overlap.height), overlap.width == 16 and overlap.height == 16)

	# head-on approach on the grid: stops right before the enemy
	p.rect.topleft = (128, 192)
	drive(ctx, p, p.DIR_RIGHT, 100)
	ctx.check("head-on approach stops next to enemy without overlap (left %d)" % p.rect.left, p.rect.left == 160)

	# tanks on top of each other can drive apart
	p.rect.topleft = (192, 192)
	drive(ctx, p, p.DIR_UP, 40)
	ctx.check("player on top of enemy drives out (top %d)" % p.rect.top, not p.rect.colliderect(enemy.rect))
	ctx.finish()


def enemy_small_overlap(ctx):
	""" Enemy keeps driving when player's square slightly crosses its path """
	g, d = ctx.g, ctx.data
	if ctx.frame == 1:
		empty_level(ctx)
		p = g["players"][0]
		p.shielded = True
		p.aquired_position = True
		# enemy drives down along x 192..223, player stands at x 216..247 (between cells):
		# player's square overlaps enemy's path by 8 px, but marks only column 14
		p.rect.topleft = (216, 256)
		enemy = still_enemy(ctx, (192, 160))
		enemy.paused = False
		g["ENEMY_GRID_PAUSE_CHANCE"] = 0
		enemy.rotate(enemy.DIR_DOWN, False)
		enemy.path = [[192, y] for y in range(161, 400)]
		d["enemy"] = enemy
	if ctx.frame == 120:
		enemy = d["enemy"]
		p = g["players"][0]
		ctx.check("enemy passed player overlapping its path by 8 px (enemy top %d)" % enemy.rect.top, enemy.rect.top > p.rect.top)
		ctx.finish()


SCENARIOS = {
	"cells": {"fn": cells},
	"enemy_small_overlap": {"fn": enemy_small_overlap},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
