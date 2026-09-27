""" Core mechanics exactly like on NES: D-pad priority, turning back, ice cell, bullets of two players,
spawning tanks block, enemies move on every other frame """

import pygame
import harness


def clear(ctx):
	del ctx.game.level.enemies_left[:]
	del ctx.g["enemies"][:]
	ctx.game.level.mapr = []
	ctx.game.level.updateObstacleRects()
	for p in ctx.g["players"]:
		p.shielded = True


def dpad_priority(ctx):
	""" NES reads the D-pad as right, left, down, up """
	g, d = ctx.g, ctx.data
	p = g["players"][0]
	if ctx.frame == 5:
		clear(ctx)
		p.rect.topleft = [192, 192]
		# up and right
		p.pressed = [True, True, False, False]
	if ctx.frame == 7:
		ctx.check("up + right: goes right", p.direction == p.DIR_RIGHT)
		# down and left
		p.pressed = [False, False, True, True]
	if ctx.frame == 9:
		ctx.check("down + left: goes left", p.direction == p.DIR_LEFT)
		# up and down
		p.pressed = [True, False, True, False]
	if ctx.frame == 11:
		ctx.check("up + down: goes down", p.direction == p.DIR_DOWN)
		p.pressed = [False] * 4
		ctx.finish()


def turning_back(ctx):
	""" NES puts the tank on the grid only on a 90 degrees turn """
	g = ctx.g
	if ctx.frame != 5:
		return
	clear(ctx)
	p = g["players"][0]
	p.rect.topleft = [44, 192]
	p.rotate(p.DIR_RIGHT, False)
	p.move(p.DIR_LEFT, 0)
	ctx.check("turning back keeps the position (%d)" % p.rect.left, p.direction == p.DIR_LEFT and p.rect.left == 44)
	p.move(p.DIR_UP, 0)
	ctx.check("90 degrees turn puts the tank on the grid (%d)" % p.rect.left, p.rect.left % 16 == 0)
	ctx.finish()


def ice_cell(ctx):
	""" NES checks only the cell the tank marks as occupied (its middle one) """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	clear(ctx)
	level, myRect = game.level, g["myRect"]
	p = g["players"][0]
	p.rect.topleft = [192, 192]
	# middle cell of the tank is (13, 13) = 208, 208
	level.mapr = [myRect(208, 208, 16, 16, level.TILE_FROZE)]
	level.updateObstacleRects()
	ctx.check("ice under the marked cell: sliding", p.onIce())
	level.mapr = [myRect(192, 192, 16, 16, level.TILE_FROZE)]
	level.updateObstacleRects()
	ctx.check("ice under another cell only: no sliding", not p.onIce())
	ctx.finish()


def two_players_bullets(ctx):
	""" NES: bullets of two players cancel each other """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	clear(ctx)
	p1, p2 = g["players"][0], g["players"][1]
	del g["bullets"][:]
	p1.rect.topleft = [192, 192]
	p2.rect.topleft = [192, 288]
	p1.rotate(p1.DIR_DOWN, False)
	p2.rotate(p2.DIR_UP, False)
	ctx.check("both players fired", p1.fire() and p2.fire())
	bullets = list(g["bullets"])
	for i in range(20):
		for bullet in list(g["bullets"]):
			bullet.update()
		if all([bullet.state == bullet.STATE_REMOVED for bullet in bullets]):
			break
	ctx.check("bullets of two players cancel each other (%s)" % [bullet.state for bullet in bullets],
		all([bullet.state == bullet.STATE_REMOVED for bullet in bullets]))
	ctx.check("nobody is hit", p1.state == p1.STATE_ALIVE and p2.state == p2.STATE_ALIVE)
	ctx.finish()


def spawning_blocks(ctx):
	""" NES marks cells of a tank in its spawn animation: other tanks can't drive through it """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	clear(ctx)
	Enemy = g["Enemy"]
	game.level.enemies_left[:] = [Enemy.TYPE_BASIC]
	enemy = Enemy(game.level, 1, [192, 160])
	del game.level.enemies_left[:]
	enemy.aquired_position = True
	enemy.startSpawning(10 ** 9)
	g["enemies"].append(enemy)

	p = g["players"][0]
	p.rect.topleft = [192, 192]
	p.aquired_position = True
	p.rotate(p.DIR_UP, False)
	moved = p.move(p.DIR_UP, 1)
	ctx.check("spawning tank blocks (%s)" % (p.rect.topleft,), not moved and p.rect.top == 192)
	enemy.state = enemy.STATE_EXPLODING
	ctx.check("exploding tank doesn't block", p.move(p.DIR_UP, 1))
	ctx.finish()


def enemy_frames(ctx):
	""" NES: normal tanks move on every other frame, fast ones on every frame """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	clear(ctx)
	g["ENEMY_GRID_PAUSE_CHANCE"] = 0
	Enemy = g["Enemy"]
	moves = {}
	for enemy_type in (Enemy.TYPE_BASIC, Enemy.TYPE_FAST):
		game.level.enemies_left[:] = [enemy_type]
		enemy = Enemy(game.level, 1, [0, 0])
		del game.level.enemies_left[:]
		enemy.state = enemy.STATE_ALIVE
		enemy.aquired_position = True
		enemy.rotate(enemy.DIR_DOWN, False)
		enemy.path = [[0, y] for y in range(1, 100)]
		steps = []
		for frame in range(6):
			before = enemy.rect.top
			enemy.move()
			steps.append(enemy.rect.top - before)
		moves[enemy_type] = steps
	ctx.check("normal tank: 2 px every other frame (%s)" % moves[Enemy.TYPE_BASIC],
		moves[Enemy.TYPE_BASIC].count(0) == 3 and moves[Enemy.TYPE_BASIC].count(2) == 3)
	ctx.check("fast tank: 2 px every frame (%s)" % moves[Enemy.TYPE_FAST], moves[Enemy.TYPE_FAST] == [2] * 6)
	ctx.finish()


SCENARIOS = {
	"dpad_priority": {"fn": dpad_priority},
	"turning_back": {"fn": turning_back},
	"ice_cell": {"fn": ice_cell},
	"two_players_bullets": {"fn": two_players_bullets, "players": 2},
	"spawning_blocks": {"fn": spawning_blocks},
	"enemy_frames": {"fn": enemy_frames},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
