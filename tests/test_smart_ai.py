""" SMART enemy AI: path around steel, through bricks, aiming, no stuck tanks """

import harness


def setup_field(ctx, tiles):
	""" Empty map with given tiles (x, y, type), one enemy at the top going to castle, players away """
	g, game = ctx.g, ctx.game
	g["ENEMY_AI"] = "SMART"
	level, myRect = game.level, g["myRect"]
	level.mapr = [myRect(x, y, 16, 16, tile_type) for x, y, tile_type in tiles]
	level.updateObstacleRects()
	level.updateRemovableRects()
	del g["enemies"][:]
	game.level.enemies_left[:] = [g["Enemy"].TYPE_BASIC]
	enemy = g["Enemy"](game.level, 1, [0, 0])
	del game.level.enemies_left[:]
	enemy.state = enemy.STATE_ALIVE
	enemy.aquired_position = True
	enemy.bonus = None
	enemy.smart_role = "castle"
	enemy.health = 100000
	g["enemies"].append(enemy)
	# players stay in spawn animation: AI doesn't see them, they don't block
	for p in g["players"]:
		p.shielded = True
		p.rect.topleft = [384, 0]
		p.startSpawning(10 ** 9)
	return enemy


def maze(ctx):
	""" Steel wall with a gap at the right side: enemy drives around it """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		level = game.level
		wall = [(x, 160, level.TILE_STEEL) for x in range(0, 352, 16)] + [(x, 176, level.TILE_STEEL) for x in range(0, 352, 16)]
		d["enemy"] = setup_field(ctx, wall)
		d["max_y"] = 0
	enemy = d["enemy"]
	d["max_y"] = max(d["max_y"], enemy.rect.top)
	# below steel wall (it can stop there: castle is in line of fire)
	if enemy.rect.top >= 192 or ctx.frame == 1500:
		ctx.check("enemy found way around steel wall (lowest y %d, frame %d)" % (d["max_y"], ctx.frame), enemy.rect.top >= 192)
		ctx.finish()


def bricks(ctx):
	""" Brick wall across the whole map: enemy shoots through it """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		level = game.level
		wall = [(x, 160, level.TILE_BRICK) for x in range(0, 416, 16)]
		d["enemy"] = setup_field(ctx, wall)
		d["bricks"] = len(level.mapr)
		# bricks are stored as quarters
		level.mapr = []
		for x in range(0, 416, 16):
			level.addBrick(x, 160)
		level.updateObstacleRects()
		d["bricks"] = len(level.mapr)
	enemy = d["enemy"]
	# passed brick wall row (it can stop there: castle is in line of fire)
	if enemy.rect.top >= 176 or ctx.frame == 1500:
		ctx.check("enemy shot through brick wall (y %d, frame %d, %d of %d quarters left)" % (enemy.rect.top, ctx.frame, len(game.level.mapr), d["bricks"]),
			enemy.rect.top >= 176 and len(game.level.mapr) < d["bricks"])
		ctx.finish()


def aim(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	level = game.level
	enemy = setup_field(ctx, [])
	p = g["players"][0]
	enemy.rect.topleft = [192, 64]
	p.rect.topleft = [192, 256]
	p.state = p.STATE_ALIVE
	enemy.rotate(enemy.DIR_LEFT, False)
	ctx.check("player below in clear line: aim down", enemy.smartAim() == enemy.DIR_DOWN)
	enemy.rotate(enemy.DIR_DOWN, False)
	ctx.check("facing player: wants to fire", enemy.smartWantsFire())
	level.mapr = [g["myRect"](192, 160, 16, 16, level.TILE_STEEL)]
	level.updateObstacleRects()
	enemy.smart_role = "player"
	ctx.check("steel between: doesn't aim", enemy.smartAim() == None and not enemy.smartWantsFire())
	# reaction time
	level.mapr = []
	level.updateObstacleRects()
	g["castle"].active = False
	fired = [enemy.wantsFire() for i in range(g["SMART_REACTION_FRAMES"] + 1)]
	ctx.check("fires only after reaction time (%s)" % fired, fired[-1] and not any(fired[:-1]))
	ctx.finish()


def deadlock(ctx):
	""" Enemies blocking each other in a row (one of them between cells) drive apart """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		first = setup_field(ctx, [])
		del g["enemies"][:]
		Enemy = g["Enemy"]
		d["tanks"] = []
		for x, direction, role in ((112, Enemy.DIR_RIGHT, "castle"), (132, Enemy.DIR_RIGHT, "player"), (160, Enemy.DIR_LEFT, "player")):
			game.level.enemies_left[:] = [Enemy.TYPE_BASIC]
			enemy = Enemy(game.level, 1, [x, 0])
			enemy.state = enemy.STATE_ALIVE
			enemy.aquired_position = True
			enemy.bonus = None
			enemy.smart_role = role
			enemy.rotate(direction, False)
			g["enemies"].append(enemy)
			d["tanks"].append((enemy, enemy.rect.topleft))
		del game.level.enemies_left[:]
	if ctx.frame == 250:
		moved = [enemy.rect.topleft != start for enemy, start in d["tanks"]]
		ctx.check("tanks blocking each other drive apart (%s)" % [enemy.rect.topleft for enemy, start in d["tanks"]], all(moved))
		ctx.finish()


def behind_obstacle(ctx, kind):
	""" Enemy above a wall, player under it: enemy doesn't drive back and forth, it finds a place and hits the player """
	g, game, d = ctx.g, ctx.game, ctx.data
	p = g["players"][0]
	if ctx.frame == 1:
		level = game.level
		if kind == "brick":
			tiles = []
		else:
			tiles = [(x, 160, level.TILE_STEEL) for x in range(128, 304, 16)]
		enemy = setup_field(ctx, tiles)
		if kind == "brick":
			for x in range(128, 304, 16):
				level.addBrick(x, 160)
			level.updateObstacleRects()
		# castle away from enemy's way
		g["castle"].rect.topleft = (384, 384)
		level.updateObstacleRects()
		enemy.rect.topleft = [192, 64]
		enemy.smart_role = "player"
		p.state = p.STATE_ALIVE
		p.rect.topleft = [192, 240]
		d["enemy"] = enemy
		d["hit"] = None
		original = p.bulletImpact
		def bulletImpact(friendly_fire = False, damage = 100, tank = None, direction = 0):
			if tank is enemy and d["hit"] == None:
				d["hit"] = ctx.frame
			return original(friendly_fire, damage, tank, direction)
		p.bulletImpact = bulletImpact
	p.shielded = True
	if d["hit"] != None or ctx.frame == 900:
		ctx.check("enemy behind %s hits player (frame %s)" % (kind, d["hit"]), d["hit"] != None)
		ctx.finish()


def dodge(ctx, chance):
	""" Player shoots at enemy from afar: enemy dodges the bullet (SMART_DODGE_CHANCE 100) or is hit (0) """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		enemy = setup_field(ctx, [])
		# single tank mechanics: no team orders (a hiding tank would leave the bullet's way anyway)
		g["SMART_TEAM"] = False
		g["castle"].rect.topleft = (384, 384)
		game.level.updateObstacleRects()
		g["SMART_DODGE_CHANCE"] = chance
		g["SMART_FEINT_CHANCE"] = 0
		g["SMART_JUKE_CHANCE"] = 0
		enemy.rect.topleft = [192, 64]
		enemy.rotate(enemy.DIR_RIGHT, False)
		# enemy is busy: it goes to the castle far away, doesn't turn to the player
		enemy.smart_role = "castle"
		enemy.health = 100
		p = g["players"][0]
		p.state = p.STATE_ALIVE
		p.shielded = True
		p.rect.topleft = [192, 320]
		p.rotate(p.DIR_UP, False)
		p.fire()
		d["enemy"] = enemy
	enemy = d["enemy"]
	if enemy.state != enemy.STATE_ALIVE or ctx.frame == 120:
		if chance:
			ctx.check("enemy dodges player's bullet (%s)" % (enemy.rect.topleft,), enemy.state == enemy.STATE_ALIVE)
		else:
			ctx.check("enemy that doesn't dodge is hit", enemy.state != enemy.STATE_ALIVE)
		ctx.finish()


def juke(ctx):
	""" Player aims at enemy and enemy's bullet isn't ready: enemy steps out of the line of fire """
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	enemy = setup_field(ctx, [])
	g["SMART_JUKE_CHANCE"] = 100
	enemy.rect.topleft = [192, 64]
	enemy.smart_role = "player"
	p = g["players"][0]
	p.state = p.STATE_ALIVE
	p.rect.topleft = [192, 320]
	p.rotate(p.DIR_UP, False)
	ctx.check("bullet ready: no juke", not enemy.smartJuke(enemy.DIR_DOWN))
	Bullet = g["Bullet"]
	bullet = Bullet(game.level, [0, 0], Bullet.DIR_RIGHT)
	bullet.owner, bullet.owner_class = Bullet.OWNER_ENEMY, enemy
	g["bullets"].append(bullet)
	ctx.check("player aims, bullet not ready: steps aside", enemy.smartJuke(enemy.DIR_DOWN) and enemy.direction in (enemy.DIR_LEFT, enemy.DIR_RIGHT))
	ctx.finish()


def playing(ctx):
	""" Real level with SMART AI: enemies drive, don't get into walls, don't stay stuck """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		g["ENEMY_AI"] = "SMART"
		d["start"] = {}
		d["moved"] = set()
		d["in_wall"] = 0
		d["last_move"] = {}
		d["longest_stop"] = 0
	for p in g["players"]:
		p.shielded = True
	g["castle"].active = True
	# SMART enemies can destroy the castle: nobody moves during game over
	if game.game_over or not game.running:
		d["last_move"] = {}
	for enemy in g["enemies"]:
		if enemy.state != enemy.STATE_ALIVE or game.game_over or not game.running:
			continue
		key = id(enemy)
		start = d["start"].setdefault(key, enemy.rect.topleft)
		if abs(enemy.rect.left - start[0]) + abs(enemy.rect.top - start[1]) > 64:
			d["moved"].add(key)
		last = d["last_move"].get(key)
		# standing and shooting at a target is fine, waiting in a hiding spot on commander's order too
		if last == None or last[0] != enemy.rect.topleft or enemy.smartWantsFire() or (enemy.smart_waiting and enemy.smart_order == "hide"):
			d["last_move"][key] = (enemy.rect.topleft, ctx.frame)
		else:
			d["longest_stop"] = max(d["longest_stop"], ctx.frame - last[1])
		if enemy.aquired_position and enemy.rect.collidelist(game.level.obstacleRectsFor(enemy.canSwim())) != -1:
			d["in_wall"] += 1
	if ctx.frame == 1200:
		ctx.check("enemies drive (%d moved far)" % len(d["moved"]), len(d["moved"]) >= 2)
		ctx.check("no enemy inside walls (%d)" % d["in_wall"], d["in_wall"] == 0)
		ctx.check("no enemy stands still without target for 10 s (longest %d frames)" % d["longest_stop"], d["longest_stop"] < 500)
		ctx.finish()


SCENARIOS = {
	"maze": {"fn": maze},
	"bricks": {"fn": bricks},
	"aim": {"fn": aim},
	"deadlock": {"fn": deadlock},
	"behind_bricks": {"fn": lambda ctx: behind_obstacle(ctx, "brick")},
	"behind_steel": {"fn": lambda ctx: behind_obstacle(ctx, "steel")},
	"dodge": {"fn": lambda ctx: dodge(ctx, 100)},
	"no_dodge": {"fn": lambda ctx: dodge(ctx, 0)},
	"juke": {"fn": juke},
	"playing": {"fn": playing},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
