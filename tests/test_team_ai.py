""" SMART AI team tactics (commander): hiding and gathering, group attack from different sides, attack on a
stunned or frozen player, ambush from grass, hunting ahead of a moving player, regroup after losses,
max wait, dodging ignores bullets behind walls, frame time """

import time
import harness


def team_field(ctx, tiles, enemies, player_pos, reinforcements = 0):
	""" Map with tiles (x, y, type), basic enemies at positions, player standing at player_pos looking up.
	Player can't be destroyed; reinforcements: tanks the stage still has (they never spawn) """
	g, game = ctx.g, ctx.game
	g["ENEMY_AI"] = "SMART"
	g["SMART_TEAM"] = True
	g["SMART_FEINT_CHANCE"] = 0
	g["INFINITE_HEALTH_FOR_ALL"] = True
	level, myRect = game.level, g["myRect"]
	level.mapr = [myRect(x, y, 16, 16, tile_type) for x, y, tile_type in tiles]
	level.updateObstacleRects()
	level.updateRemovableRects()
	del g["enemies"][:]
	del g["bullets"][:]
	Enemy = g["Enemy"]
	result = []
	for position, enemy_type in enemies:
		level.enemies_left[:] = [enemy_type]
		enemy = Enemy(level, 1, position)
		enemy.state = enemy.STATE_ALIVE
		enemy.aquired_position = True
		enemy.bonus = None
		enemy.rect.topleft = position
		g["enemies"].append(enemy)
		result.append(enemy)
	level.enemies_left[:] = [Enemy.TYPE_BASIC] * reinforcements
	level.max_active_enemies = len(result) + reinforcements
	game.smart_commander = None
	p = g["players"][0]
	p.rect.topleft = player_pos
	p.rotate(p.DIR_UP, False)
	p.shielded = False
	return result, p


def keep_still(ctx):
	""" Every frame: no enemy spawns, player unshielded """
	g, game = ctx.g, ctx.game
	game.spawn_timer = 10 ** 9
	g["players"][0].shielded = False


def enemy_bullets(ctx):
	return [bullet for bullet in ctx.g["bullets"] if bullet.owner == bullet.OWNER_ENEMY]


def side(p, enemy):
	dx, dy = enemy.rect.centerx - p.rect.centerx, enemy.rect.centery - p.rect.centery
	if abs(dx) > abs(dy):
		return 1 if dx > 0 else 3
	return 2 if dy > 0 else 0


def gather_attack(ctx):
	""" Three enemies hide out of player's lines of fire without shooting, then attack together from 2+ sides """
	g, game, d = ctx.g, ctx.game, ctx.data
	commander = g["battlecity.commander"] if "battlecity.commander" in g else None
	if ctx.frame == 1:
		level = game.level
		tiles = []
		# brick blocks: cover
		for bx, by in ((64, 96), (176, 112), (304, 96), (96, 192), (288, 192)):
			for dx in (0, 16):
				for dy in (0, 16):
					tiles.append((bx + dx, by + dy, level.TILE_BRICK))
		Enemy = g["Enemy"]
		d["enemies"], d["p"] = team_field(ctx, tiles, [([0, 0], Enemy.TYPE_BASIC), ([96, 0], Enemy.TYPE_BASIC), ([384, 0], Enemy.TYPE_BASIC)], [192, 272])
		g["SMART_GROUP_SIZE"] = 3
		g["SMART_MAX_WAIT"] = 10 ** 6
		g["SMART_SMALL_GROUP_WAIT"] = 10 ** 6
		d["attack"] = None
		d["sides"] = set()
		d["bad_spots"] = []
	keep_still(ctx)
	p, enemies = d["p"], d["enemies"]
	cmd = game.smart_commander
	if cmd == None:
		return
	if d["attack"] == None:
		if cmd.phase == "ATTACK":
			d["attack"] = ctx.frame
			d["log"] = cmd.log[-1]
			for enemy, spot in d.get("spots", {}).items():
				# player can't shoot the tank there (his bullet would hit a wall first)
				danger = cmd.place_danger[spot[1]][spot[0]]
				far = abs(spot[0] - p.rect.left // 16) + abs(spot[1] - p.rect.top // 16)
				if danger > 0 or far < g["SMART_HIDE_MIN_DIST"]:
					d["bad_spots"].append((spot, danger, far))
		else:
			# spots where tanks wait; shots only at a player in clear line (ambush), not at random or at walls
			d["spots"] = dict([(enemy, (enemy.rect.left // 16, enemy.rect.top // 16)) for enemy in enemies if enemy.smart_waiting])
			seen = d.setdefault("bullets", set())
			for bullet in enemy_bullets(ctx):
				if id(bullet) not in seen:
					seen.add(id(bullet))
					in_line, steel, brick = bullet.owner_class.lineTo(bullet.direction, p.rect)
					if not in_line or steel or brick:
						d["shot_while_hiding"] = (ctx.frame, bullet.owner_class.rect.topleft)
			if ctx.frame == 1200:
				ctx.check("attack started when group was ready (orders %s, waiting %s)" % ([e.smart_order for e in enemies], [e.smart_waiting for e in enemies]), False)
				ctx.finish()
		return
	if ctx.frame % 5 == 0:
		near = [enemy for enemy in enemies if abs(enemy.rect.centerx - p.rect.centerx) + abs(enemy.rect.centery - p.rect.centery) <= 8 * 16]
		if len(near) >= 2:
			d["sides"] |= set([side(p, enemy) for enemy in near])
	if len(d["sides"]) >= 2 or ctx.frame == d["attack"] + 500:
		ctx.check("no enemy shot while hiding except at player in clear line (%s)" % (d.get("shot_while_hiding"),), d.get("shot_while_hiding") == None)
		ctx.check("%d tanks waited in spots out of player's lines of fire, %d+ cells away (bad: %s)" % (len(d["spots"]), g["SMART_HIDE_MIN_DIST"], d["bad_spots"]),
			len(d["spots"]) == 3 and d["bad_spots"] == [])
		ctx.check("attack started when group was ready (%s at frame %d)" % (d["log"], d["attack"]), d["log"]["trigger"] == "group ready" and d["log"]["tanks"] == 3)
		ctx.check("attack sides given: %s" % d["log"].get("sides"), d["log"].get("sides", 0) >= 2)
		ctx.check("enemies came from 2+ sides (%s, frame %d)" % (sorted(d["sides"]), ctx.frame), len(d["sides"]) >= 2)
		ctx.finish()


def paralised(ctx, how):
	""" Enemies gathering: stunned / frozen player is attacked at once """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		Enemy = g["Enemy"]
		d["enemies"], d["p"] = team_field(ctx, [], [([0, 0], Enemy.TYPE_BASIC), ([384, 0], Enemy.TYPE_BASIC)], [192, 272], reinforcements = 5)
		g["SMART_MAX_WAIT"] = 10 ** 6
	keep_still(ctx)
	p = d["p"]
	cmd = game.smart_commander
	if ctx.frame == 20:
		ctx.check("gathering before (%s)" % (cmd and cmd.phase), cmd != None and cmd.phase == "GATHER")
		if how == "stunned":
			p.setParalised(True)
		else:
			p.setFrozen(True)
	if ctx.frame == 32:
		ctx.check("%s player: attack at once (%s, %s)" % (how, cmd.phase, cmd.log), cmd.phase == "ATTACK" and cmd.log[-1]["trigger"] == how)
		ctx.check("enemies attack (%s)" % [e.smart_order for e in d["enemies"]], all([e.smart_order == "attack" for e in d["enemies"]]))
		ctx.finish()


def ambush(ctx):
	""" Enemy in grass pocket with a lane: waits without shooting, fires when player drives into the lane """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		level = game.level
		STEEL, GRASS = level.TILE_STEEL, level.TILE_GRASS
		tiles = [(x * 16, 7 * 16, STEEL) for x in range(1, 12)] + [(x * 16, 10 * 16, STEEL) for x in range(1, 12)]
		tiles += [(16, 8 * 16, STEEL), (16, 9 * 16, STEEL)]
		tiles += [(x * 16, y * 16, GRASS) for x in (2, 3) for y in (8, 9)]
		Enemy = g["Enemy"]
		enemies, p = team_field(ctx, tiles, [([32, 128], Enemy.TYPE_BASIC)], [192, 176], reinforcements = 5)
		d["enemy"], d["p"] = enemies[0], p
		g["SMART_MAX_WAIT"] = 10 ** 6
		g["SMART_SMALL_GROUP_WAIT"] = 10 ** 6
		g["SMART_GRASS_BONUS"] = 12
		d["fired"] = None
	keep_still(ctx)
	enemy, p = d["enemy"], d["p"]
	cmd = game.smart_commander
	if ctx.frame < 200:
		if enemy_bullets(ctx):
			d["early"] = ctx.frame
		return
	if ctx.frame == 200:
		ctx.check("enemy waits in grass spot (%s, order %s, waiting %s, phase %s)" % (enemy.rect.topleft, enemy.smart_order, enemy.smart_waiting, cmd.phase),
			enemy.rect.topleft == (32, 128) and enemy.smart_waiting and cmd.phase == "GATHER")
		ctx.check("no shot before player is in line (%s)" % d.get("early"), d.get("early") == None)
	# player drives up into the lane
	if p.rect.top > 128:
		p.rect.top -= 2
	elif d.get("in_line") == None:
		d["in_line"] = ctx.frame
	if d.get("in_line") != None and enemy_bullets(ctx) and d["fired"] == None:
		d["fired"] = ctx.frame
	if d["fired"] != None or ctx.frame == 400:
		ctx.check("ambush shot after player entered the lane (in line at %s, fired at %s)" % (d.get("in_line"), d["fired"]),
			d["fired"] != None and d["fired"] - d["in_line"] <= 60)
		ctx.check("shot from the spot (%s)" % (enemy.rect.topleft,), abs(enemy.rect.left - 32) <= 16 and enemy.rect.top == 128)
		ctx.finish()


def hunter(ctx):
	""" Attack phase: fast tank hunts a player driving right - place ahead of him or behind him, not in front """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		Enemy = g["Enemy"]
		enemies, p = team_field(ctx, [], [([256, 32], Enemy.TYPE_FAST), ([0, 0], Enemy.TYPE_BASIC)], [32, 208])
		d["enemy"], d["p"] = enemies[0], p
		g["SMART_MAX_WAIT"] = 0
	keep_still(ctx)
	p, enemy = d["p"], d["enemy"]
	p.pressed = [False, True, False, False]
	if ctx.frame == 40:
		cmd = game.smart_commander
		cmd.update()
		ctx.check("attack phase, fast tank hunts (%s, %s)" % (cmd.phase, enemy.smart_order), cmd.phase == "ATTACK" and enemy.smart_order == "hunt")
		lead = enemy.smartLead(cmd, p, g["SMART_HUNT_LEAD"])
		ctx.check("player's place predicted ahead (%s -> %s)" % (p.rect.topleft, lead.topleft), lead.centerx >= p.rect.centerx + 48)
		enemy.smart_goal = None
		enemy.smartPath()
		gx, gy = enemy.smart_goal
		px, py = p.rect.left // 16, p.rect.top // 16
		in_front = abs(gy - py) <= 1 and gx > px
		ahead = gx >= px + 3
		behind = gx + 1 < px
		ctx.check("hunter goal %s ahead of or behind player at %s, not in front of him" % ((gx, gy), (px, py)), (ahead or behind) and not in_front)
		ctx.finish()


def regroup(ctx):
	""" Attack of 4 tanks loses 2: survivors regroup in hiding spots """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		Enemy = g["Enemy"]
		d["enemies"], d["p"] = team_field(ctx, [], [([0, 0], 0), ([96, 0], 0), ([288, 0], 0), ([384, 0], 0)], [192, 272])
		g["SMART_MAX_WAIT"] = 0
	keep_still(ctx)
	cmd = game.smart_commander
	if ctx.frame == 5:
		g["SMART_MAX_WAIT"] = 10 ** 6
		ctx.check("attack of 4 tanks (%s, %d)" % (cmd.phase, cmd.attack_size), cmd.phase == "ATTACK" and cmd.attack_size == 4)
	if ctx.frame == 10:
		for enemy in d["enemies"][:2]:
			enemy.state = enemy.STATE_DEAD
	if ctx.frame == 20:
		cmd.update()
		ctx.check("half of attackers lost: regroup (%s, %s)" % (cmd.phase, cmd.trigger), cmd.phase == "REGROUP" and cmd.trigger == "losses")
		ctx.check("survivors hide (%s)" % [e.smart_order for e in d["enemies"][2:]], all([e.smart_order == "hide" for e in d["enemies"][2:]]))
		ctx.finish()


def max_wait(ctx):
	""" Group never gets ready: attack after SMART_MAX_WAIT anyway """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		Enemy = g["Enemy"]
		d["enemies"], d["p"] = team_field(ctx, [], [([0, 0], Enemy.TYPE_BASIC)], [192, 272], reinforcements = 5)
		g["SMART_MAX_WAIT"] = 3000
		g["SMART_SMALL_GROUP_WAIT"] = 10 ** 6
		d["attack"] = None
	keep_still(ctx)
	cmd = game.smart_commander
	if cmd == None:
		return
	if cmd.phase == "ATTACK" and d["attack"] == None:
		d["attack"] = game.level_time - cmd.log[-1]["start"] + cmd.log[-1]["waited"]
		ctx.check("attack after max wait (waited %d ms, trigger %s)" % (cmd.log[-1]["waited"], cmd.log[-1]["trigger"]),
			cmd.log[-1]["trigger"] == "timeout" and 3000 <= cmd.log[-1]["waited"] <= 3300)
		ctx.check("enemy attacks (%s)" % d["enemies"][0].smart_order, d["enemies"][0].smart_order == "attack")
		ctx.finish()
	if ctx.frame == 400:
		ctx.check("attack after max wait (phase %s)" % cmd.phase, False)
		ctx.finish()


def dodge_wall(ctx):
	""" Player's bullet flies at enemy: wall between - no dodge, no wall - dodge """
	g, game = ctx.g, ctx.game
	if ctx.frame != 1:
		return
	level = game.level
	Enemy, Bullet = g["Enemy"], g["Bullet"]
	enemies, p = team_field(ctx, [(x, 192, level.TILE_STEEL) for x in range(160, 256, 16)], [([192, 64], Enemy.TYPE_BASIC)], [352, 352])
	enemy = enemies[0]
	g["SMART_DODGE_CHANCE"] = 100
	bullet = Bullet(level, [192, 320], Bullet.DIR_UP)
	bullet.owner, bullet.owner_class = Bullet.OWNER_PLAYER, p
	g["bullets"].append(bullet)
	enemy.smartDodge()
	game.level_time += 1000
	ctx.check("bullet behind steel: no dodge", not enemy.smartDodge())
	level.mapr = []
	level.updateObstacleRects()
	game.level_time += 20
	ctx.check("no wall: dodge", enemy.smartDodge() and enemy.direction in (enemy.DIR_LEFT, enemy.DIR_RIGHT))
	ctx.finish()


def performance(ctx):
	""" Real stage, bot plays player 1, 8 SMART enemies: frame time stays low """
	g, game, d = ctx.g, ctx.game, ctx.data
	now = time.perf_counter()
	if ctx.frame == 1:
		g["ENEMY_AI"] = "SMART"
		g["SMART_TEAM"] = True
		g["PLAYER_INFINITE_LIVES"] = True
		g["INFINITE_HEALTH_FOR_ALL"] = True
		game.level.max_active_enemies = 8
		p = g["players"][0]
		p.controls = []
		p.bot = g["Bot"](game, p)
		d["times"] = []
		d["last"] = None
	game.spawn_timer = min(game.spawn_timer, 200)
	alive = len([e for e in g["enemies"] if e.state == e.STATE_ALIVE])
	if d["last"] != None and alive >= 6:
		d["times"].append((now - d["last"]) * 1000)
	d["last"] = now
	if len(d["times"]) >= 500 or ctx.frame == 1800:
		times = d["times"]
		mean = sum(times) / max(1, len(times))
		ctx.check("frames with 6+ SMART enemies: %d, mean %.2f ms, max %.1f ms" % (len(times), mean, max(times or [0])), len(times) >= 200 and mean < 20)
		ctx.finish()


SCENARIOS = {
	"gather_attack": {"fn": gather_attack, "max_frames": 3000},
	"stunned": {"fn": lambda ctx: paralised(ctx, "stunned")},
	"frozen": {"fn": lambda ctx: paralised(ctx, "frozen")},
	"ambush": {"fn": ambush},
	"hunter": {"fn": hunter},
	"regroup": {"fn": regroup},
	"max_wait": {"fn": max_wait},
	"dodge_wall": {"fn": dodge_wall},
	"performance": {"fn": performance, "argv": ["-l", "5"], "max_frames": 4000},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
