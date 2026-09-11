# coding=utf-8
""" Battle City: team tactics of SMART enemy AI

One commander is shared by all SMART enemies of a stage (config.SMART_TEAM). Every SMART_COMMAND_INTERVAL ms
it updates what the team knows about the field and gives every alive enemy an order (enemy.smart_order):

- danger map: cells players can shoot now or soon - 2 cells wide bullet bands from every player in 4 directions
  until bricks, steel or screen edge (much stronger in the direction the player looks, also from the place the
  player drives to) and paths of flying player bullets. Enemies pay for danger on their way (a lot while hiding,
  a little while attacking), so they come through cover;
- GATHER (REGROUP after a failed attack): "hide" - go to a hiding spot out of the player's lines of fire, some
  cells away from him, preferably in grass or behind walls, spread apart, with a lane the player may drive
  into; wait there and shoot only a player who appears in the line of fire (ambush);
- ATTACK starts when the group is ready (SMART_GROUP_SIZE tanks wait, or all of them waited a while), when the
  player is vulnerable (stunned or frozen, his bullets are busy next to a waiting tank, he turned away from
  the group) or waiting took SMART_MAX_WAIT. "attack" - every tank gets a side around the player (not his
  front, only a tough tank takes the front to draw fire), all go at once;
- "hunt" - fast tanks attack a moving player from places ahead of him or behind him (in GATHER only when
  the player is far from the castle);
- attack loses half of its tanks or lasts SMART_ATTACK_TIME: REGROUP;
- "castle" - one tank rushes the castle while the player is far from it, one tank of a big attack goes for
  the castle meanwhile (player has to choose what to defend); every enemy attacks the castle when no player
  is alive.
"""

from battlecity import config, state

CELL = 16
GRID = 26
PLACES = 25
STEPS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)
GATHER, ATTACK, REGROUP, CASTLE = "GATHER", "ATTACK", "REGROUP", "CASTLE"
# enemy types (tank.Enemy)
TYPE_FAST, TYPE_ARMOR, TYPE_BOSS = 1, 3, 6
# enemy spawn places: nobody hides there
SPAWN_PLACES = [(12, 0), (24, 0), (0, 0)]


def enabled():
	""" Team tactics are used: SMART AI with SMART_TEAM """
	return config.ENEMY_AI == "SMART" and config.SMART_TEAM


def get():
	""" Commander of the current stage (new stage - new commander), updated when it's time """
	game = state.game
	level = getattr(game, "level", None)
	now = getattr(game, "level_time", 0)
	commander = getattr(game, "smart_commander", None)
	if commander is None or commander.level is not level or now < commander.now:
		commander = Commander(level, now)
		game.smart_commander = commander
	commander.tick(now)
	return commander


def alive(tank):
	return tank.state == tank.STATE_ALIVE


def place(rect):
	""" Nearest tank place (cell of top left corner) """
	return (min(max(int(round(rect.left / float(CELL))), 0), PLACES - 1), min(max(int(round(rect.top / float(CELL))), 0), PLACES - 1))


def distance(a, b):
	return abs(a[0] - b[0]) + abs(a[1] - b[1])


def slotBusy(tank):
	""" Tank can't fire now: all its bullets fly or explode """
	busy = [bullet for bullet in state.bullets if bullet.owner_class is tank and
		(bullet.state == bullet.STATE_ACTIVE or (bullet.state == bullet.STATE_EXPLODING and bullet.slot_busy))]
	return len(busy) >= tank.max_active_bullets


def sideOf(center, point):
	""" Direction from center place to point place along the longer axis """
	dx, dy = point[0] - center[0], point[1] - center[1]
	if abs(dx) > abs(dy):
		return DIR_RIGHT if dx > 0 else DIR_LEFT
	return DIR_DOWN if dy > 0 else DIR_UP


class Commander():

	def __init__(self, level, now = 0):
		self.level = level
		self.now = now
		self.updated = None
		self.phase = GATHER
		self.phase_start = now
		self.trigger = None
		# focus player of the team
		self.target = None
		self.attack_target = None
		# ids of tanks in current attack, tanks at its start
		self.attackers = set()
		self.attack_size = 0
		self.rusher = None
		# tank attacking the castle during a big attack
		self.diversion = None
		# id(player) -> [topleft, moving direction, ms of last move, facing, facing since, stable facing]
		self.tracks = {}
		# started attacks: {"start", "waited", "trigger", "tanks", "sides"} (statistics, tests)
		self.log = []
		self.place_costs = {}
		self.danger = [[0.0] * GRID for i in range(GRID)]
		self.place_danger = [[0.0] * PLACES for i in range(PLACES)]
		self.hide = None
		self.watch = None
		self.bricks = self.steel = self.water = self.grass = self.walls = set()

	def tick(self, now):
		self.now = now
		if self.updated == None or now - self.updated >= config.SMART_COMMAND_INTERVAL:
			self.update()

	def update(self):
		""" Read field, danger, phase and orders """
		self.updated = self.now
		players = [player for player in state.players if alive(player)]
		enemies = [enemy for enemy in state.enemies if alive(enemy)]
		self.readMap()
		self.trackPlayers(players)
		self.updateDanger(players)
		self.chooseTarget(players, enemies)
		self.updatePhase(enemies)
		self.giveOrders(players, enemies)
		if self.target != None:
			self.updateHide()

	# ---------------------------------------------------------------- field

	def readMap(self):
		level = self.level
		self.bricks, self.steel, self.water, self.grass = set(), set(), set(), set()
		kinds = {level.TILE_BRICK: self.bricks, level.TILE_STEEL: self.steel, level.TILE_WATER: self.water, level.TILE_GRASS: self.grass}
		for tile in level.mapr:
			cells = kinds.get(tile.type)
			if cells != None:
				cells.add((tile.left // CELL, tile.top // CELL))
		self.castle_cells = set()
		for castle in state.game.castles():
			r = castle.rect
			for cy in range(r.top // CELL, (r.bottom - 1) // CELL + 1):
				for cx in range(r.left // CELL, (r.right - 1) // CELL + 1):
					self.castle_cells.add((cx, cy))
		# cells stopping bullets
		self.walls = self.bricks | self.steel | self.castle_cells
		self.place_costs = {}

	def placeCosts(self, can_swim):
		""" Way cost of tank places: 1 empty, SMART_BRICK_COST with bricks, None - steel, water, castle """
		if can_swim not in self.place_costs:
			costs = [[1] * GRID for i in range(GRID)]
			for cx, cy in self.bricks:
				if 0 <= cx < GRID and 0 <= cy < GRID:
					costs[cy][cx] = max(1, config.SMART_BRICK_COST)
			blocked = self.steel | self.castle_cells | (set() if can_swim else self.water)
			for cx, cy in blocked:
				if 0 <= cx < GRID and 0 <= cy < GRID:
					costs[cy][cx] = None
			places = [[None] * PLACES for i in range(PLACES)]
			for y in range(PLACES):
				row, below = costs[y], costs[y + 1]
				for x in range(PLACES):
					cells = (row[x], row[x + 1], below[x], below[x + 1])
					if None not in cells:
						places[y][x] = max(cells)
			self.place_costs[can_swim] = places
		return self.place_costs[can_swim]

	def trackPlayers(self, players):
		tracks = {}
		for player in players:
			old = self.tracks.get(id(player))
			if old == None:
				track = [player.rect.topleft, None, -10 ** 9, player.direction, self.now, player.direction]
			else:
				track = list(old)
				dx, dy = player.rect.left - old[0][0], player.rect.top - old[0][1]
				if (dx or dy) and abs(dx) + abs(dy) <= 2 * CELL:
					track[1] = (DIR_RIGHT if dx > 0 else DIR_LEFT) if abs(dx) > abs(dy) else (DIR_DOWN if dy > 0 else DIR_UP)
					track[2] = self.now
				elif dx or dy:
					# respawned
					track[1] = None
				track[0] = player.rect.topleft
				if player.direction != track[3]:
					track[3], track[4] = player.direction, self.now
				if self.now - track[4] >= config.SMART_STABLE_FACING:
					track[5] = track[3]
			tracks[id(player)] = track
		self.tracks = tracks

	def movingDirection(self, player):
		""" Direction the player drives now, None if he stands """
		track = self.tracks.get(id(player))
		if track and track[1] != None and self.now - track[2] <= config.SMART_COMMAND_INTERVAL * 2:
			return track[1]
		return None

	def stableFacing(self, player):
		""" Direction the player looks for a while (turning back and forth doesn't change attack sides) """
		track = self.tracks.get(id(player))
		return track[5] if track else player.direction

	def addLine(self, danger, rect, direction, weight, from_inside = False):
		""" Danger along 2 cells wide bullet band from rect in direction until a wall """
		if direction in (DIR_UP, DIR_DOWN):
			band = sorted(set([(rect.centerx - 4) // CELL, (rect.centerx + 3) // CELL]))
			if direction == DIR_UP:
				start = (rect.bottom - 1) // CELL if from_inside else (rect.top - 1) // CELL
				lines = range(start, -1, -1)
			else:
				start = rect.top // CELL if from_inside else rect.bottom // CELL
				lines = range(start, GRID)
			cells = lambda line: [(col, line) for col in band]
		else:
			band = sorted(set([(rect.centery - 4) // CELL, (rect.centery + 3) // CELL]))
			if direction == DIR_LEFT:
				start = (rect.right - 1) // CELL if from_inside else (rect.left - 1) // CELL
				lines = range(start, -1, -1)
			else:
				start = rect.left // CELL if from_inside else rect.right // CELL
				lines = range(start, GRID)
			cells = lambda line: [(line, row) for row in band]
		walls = self.walls
		for k, line in enumerate(lines):
			line_cells = [(cx, cy) for cx, cy in cells(line) if 0 <= cx < GRID and 0 <= cy < GRID]
			if not line_cells or any([cell in walls for cell in line_cells]):
				return
			value = weight * (1.0 - 0.5 * k / GRID)
			for cx, cy in line_cells:
				if danger[cy][cx] < value:
					danger[cy][cx] = value

	def updateDanger(self, players):
		danger = [[0.0] * GRID for i in range(GRID)]
		for player in players:
			for direction in range(4):
				weight = config.SMART_DANGER_FACING if direction == player.direction else config.SMART_DANGER_SIDE
				self.addLine(danger, player.rect, direction, weight)
			# soon: from the place the player drives to
			moving = self.movingDirection(player)
			if moving != None:
				ahead = player.rect.move(STEPS[moving][0] * 2 * CELL, STEPS[moving][1] * 2 * CELL)
				if 0 <= ahead.left and ahead.right <= GRID * CELL and 0 <= ahead.top and ahead.bottom <= GRID * CELL:
					for direction in range(4):
						weight = config.SMART_DANGER_FACING * 0.5 if direction == player.direction else config.SMART_DANGER_SIDE * 0.5
						self.addLine(danger, ahead, direction, weight)
		# players' lines only (dodging tank leaves the bullet's way anyway)
		self.player_danger = [list(row) for row in danger]
		for bullet in state.bullets:
			if bullet.state == bullet.STATE_ACTIVE and bullet.owner == bullet.OWNER_PLAYER:
				self.addLine(danger, bullet.rect, bullet.direction, config.SMART_DANGER_BULLET, True)
		self.danger = danger
		place_danger = [[0.0] * PLACES for i in range(PLACES)]
		for y in range(PLACES):
			row, below, out = danger[y], danger[y + 1], place_danger[y]
			for x in range(PLACES):
				out[x] = max(row[x], row[x + 1], below[x], below[x + 1])
		self.place_danger = place_danger

	def rectDanger(self, rect, bullets = True):
		""" Danger of cells under rect (bullets False: players' lines of fire only) """
		danger = self.danger if bullets else self.player_danger
		value = 0.0
		for cy in range(max(rect.top, 0) // CELL, min((rect.bottom - 1) // CELL, GRID - 1) + 1):
			for cx in range(max(rect.left, 0) // CELL, min((rect.right - 1) // CELL, GRID - 1) + 1):
				value = max(value, danger[cy][cx])
		return value

	# ---------------------------------------------------------------- team

	def chooseTarget(self, players, enemies):
		if not players:
			self.target = None
			return
		if self.target in players:
			return
		if enemies:
			cx = sum([enemy.rect.centerx for enemy in enemies]) / float(len(enemies))
			cy = sum([enemy.rect.centery for enemy in enemies]) / float(len(enemies))
		else:
			cx, cy = state.castle.rect.center
		self.target = min(players, key=lambda p: abs(p.rect.centerx - cx) + abs(p.rect.centery - cy))

	def setPhase(self, phase, reason):
		self.phase = phase
		self.phase_start = self.now
		self.trigger = reason

	def reinforcements(self):
		""" Tanks which can still appear soon """
		level = self.level
		free = max(0, getattr(level, "max_active_enemies", 4) - len(state.enemies))
		return min(len(getattr(level, "enemies_left", [])), free)

	def team(self, enemies):
		""" Tanks gathering / attacking the player (not the ones sent to the castle) """
		return [enemy for enemy in enemies if enemy is not self.rusher and (enemy is not self.diversion or self.phase == ATTACK)]

	def updatePhase(self, enemies):
		if self.target == None:
			if self.phase != CASTLE:
				self.setPhase(CASTLE, "no players")
			return
		if self.phase == CASTLE:
			self.setPhase(GATHER, "player appeared")
		team = self.team(enemies)
		if self.phase in (GATHER, REGROUP):
			trigger = self.attackTrigger(team)
			if trigger:
				self.startAttack(team, trigger)
			return
		ids = set([id(enemy) for enemy in enemies])
		left = len([i for i in self.attackers if i in ids])
		lost = self.attack_size - min(left, self.attack_size)
		if self.target is not self.attack_target:
			self.setPhase(GATHER, "target changed")
		elif left == 0:
			self.setPhase(GATHER, "attackers destroyed")
		elif self.attack_size >= 2 and lost * 2 >= self.attack_size:
			self.setPhase(REGROUP, "losses")
		elif self.now - self.phase_start >= config.SMART_ATTACK_TIME:
			self.setPhase(REGROUP, "attack too long")

	def attackTrigger(self, team):
		""" Reason to attack now or None """
		if not team:
			return None
		player = self.target
		waited = self.now - self.phase_start
		if player.paralised:
			return "stunned" if player.stunned else "frozen"
		if waited >= config.SMART_MAX_WAIT:
			return "timeout"
		if player.shielded or waited < config.SMART_MIN_GATHER:
			return None
		ready = [enemy for enemy in team if getattr(enemy, "smart_waiting", False)]
		if not ready:
			return None
		spawning = len([enemy for enemy in state.enemies if enemy.state == enemy.STATE_SPAWNING])
		need = max(1, min(config.SMART_GROUP_SIZE, len(team) + spawning + self.reinforcements()))
		if len(ready) >= need:
			return "group ready"
		if len(ready) == len(team) and waited >= config.SMART_SMALL_GROUP_WAIT:
			return "all ready"
		target_place = place(player.rect)
		near = min([distance(place(enemy.rect), target_place) for enemy in ready])
		if slotBusy(player) and near <= config.SMART_PUNISH_DIST:
			return "player reloading"
		if len(ready) >= 2:
			cx = sum([enemy.rect.centerx for enemy in ready]) / float(len(ready))
			cy = sum([enemy.rect.centery for enemy in ready]) / float(len(ready))
			towards = sideOf(target_place, place(player.rect.move(int(cx - player.rect.centerx), int(cy - player.rect.centery))))
			moving = self.movingDirection(player)
			if player.direction == (towards + 2) % 4 and moving in (None, player.direction):
				return "player turned away"
		return None

	def startAttack(self, team, trigger):
		self.attackers = set([id(enemy) for enemy in team])
		self.attack_size = len(team)
		self.attack_target = self.target
		self.log.append({"start": self.now, "waited": self.now - self.phase_start, "trigger": trigger, "tanks": len(team), "from": self.phase})
		self.setPhase(ATTACK, trigger)
		for enemy in team:
			enemy.smart_side = None

	def isolated(self, player, players):
		""" Player far from the castle and from his partners """
		here = place(player.rect)
		if distance(here, place(state.castle.rect)) < config.SMART_ISOLATED_DIST:
			return False
		return all([distance(here, place(other.rect)) >= config.SMART_ISOLATED_DIST for other in players if other is not player])

	def order(self, enemy, order):
		if getattr(enemy, "smart_order", None) != order:
			enemy.smart_timer = 0
			enemy.smart_waiting = False
			if order != "attack":
				enemy.smart_side = None
				enemy.smart_front = False
		enemy.smart_order = order
		enemy.smart_role = "castle" if order == "castle" else "player"

	def giveOrders(self, players, enemies):
		if self.target == None:
			self.rusher = None
			for enemy in enemies:
				self.order(enemy, "castle")
			return
		player = self.target
		here = place(player.rect)
		castle = state.castle
		castle_distance = distance(here, place(castle.rect))
		if self.rusher not in enemies or castle_distance <= config.SMART_CASTLE_RUSH_DIST - 3 or not castle.active:
			self.rusher = None
		if self.rusher == None and castle.active and len(enemies) >= 2 and castle_distance >= config.SMART_CASTLE_RUSH_DIST:
			# armor tank first, fast tanks are hunters
			self.rusher = min(enemies, key=lambda e: (0 if e.type == TYPE_ARMOR else (2 if e.type == TYPE_FAST else 1), distance(place(e.rect), place(castle.rect))))
		# big attack (or big group gathering): one tank goes for the castle meanwhile, player has to choose what to defend
		big = self.attack_size >= config.SMART_DIVERSION_MIN_TANKS if self.phase == ATTACK else len(enemies) > config.SMART_DIVERSION_MIN_TANKS
		if not big or not castle.active or self.rusher != None or self.diversion not in enemies:
			self.diversion = None
		if big and castle.active and self.rusher == None and self.diversion == None:
			others = [enemy for enemy in enemies if enemy.type != TYPE_FAST and not enemy.smart_front]
			if others:
				self.diversion = min(others, key=lambda e: distance(place(e.rect), place(castle.rect)))
		isolated = self.isolated(player, players)
		attack = []
		for enemy in enemies:
			if enemy is self.rusher or enemy is self.diversion:
				self.order(enemy, "castle")
			elif self.phase == ATTACK:
				self.attackers.add(id(enemy))
				if enemy.type == TYPE_FAST:
					self.order(enemy, "hunt")
				else:
					self.order(enemy, "attack")
					attack.append(enemy)
			elif enemy.type == TYPE_FAST and isolated:
				self.order(enemy, "hunt")
			else:
				self.order(enemy, "hide")
		if attack:
			self.assignSides(player, here, attack)

	def assignSides(self, player, here, attack):
		""" Attack sides around the player: every side at most as crowded as others, not the player's front;
		a tough tank takes the front when there are 3+ attackers """
		facing = self.stableFacing(player)
		front = None
		if len(attack) >= 3:
			tough = [enemy for enemy in attack if enemy.type in (TYPE_ARMOR, TYPE_BOSS) or enemy.health >= 300]
			if tough:
				front = max(tough, key=lambda enemy: enemy.health)
		sides = [direction for direction in range(4) if direction != facing]
		counts = dict([(direction, 0) for direction in sides])

		def sideDistance(enemy, direction):
			dx, dy = STEPS[direction]
			point = (min(max(here[0] + dx * 6, 0), PLACES - 1), min(max(here[1] + dy * 6, 0), PLACES - 1))
			return distance(place(enemy.rect), point)

		for enemy in sorted(attack, key=lambda enemy: distance(place(enemy.rect), here)):
			if enemy is front:
				enemy.smart_side, enemy.smart_front = facing, True
				continue
			enemy.smart_front = False
			fewest = min(counts.values())
			if getattr(enemy, "smart_side", None) not in counts or counts[enemy.smart_side] > fewest:
				enemy.smart_side = min(sides, key=lambda direction: (counts[direction], sideDistance(enemy, direction)))
			counts[enemy.smart_side] += 1
		if self.log and "sides" not in self.log[-1]:
			self.log[-1]["sides"] = len(set([enemy.smart_side for enemy in attack]))

	# ---------------------------------------------------------------- hiding spots

	def updateHide(self):
		""" Cost of every place as a hiding spot from the target player and direction to watch from there """
		player = self.target
		tx, ty = place(player.rect)
		extra = 2 if self.phase == REGROUP else 0
		near, far = config.SMART_HIDE_MIN_DIST + extra, config.SMART_HIDE_MAX_DIST + extra
		walls = self.walls
		standing = self.placeCosts(False)

		# free cells of 2 cells wide lanes next to every place: up, right, down, left
		def rowBlocked(x, row):
			return (x, row) in walls or (x + 1, row) in walls

		def colBlocked(col, y):
			return (col, y) in walls or (col, y + 1) in walls

		up = [[0] * PLACES for i in range(PLACES)]
		down = [[0] * PLACES for i in range(PLACES)]
		left = [[0] * PLACES for i in range(PLACES)]
		right = [[0] * PLACES for i in range(PLACES)]
		for x in range(PLACES):
			for y in range(1, PLACES):
				up[y][x] = 0 if rowBlocked(x, y - 1) else up[y - 1][x] + 1
			for y in range(PLACES - 2, -1, -1):
				down[y][x] = 0 if rowBlocked(x, y + 2) else down[y + 1][x] + 1
		for y in range(PLACES):
			for x in range(1, PLACES):
				left[y][x] = 0 if colBlocked(x - 1, y) else left[y][x - 1] + 1
			for x in range(PLACES - 2, -1, -1):
				right[y][x] = 0 if colBlocked(x + 2, y) else right[y][x + 1] + 1

		grass = self.grass
		danger = self.place_danger
		hide = [[None] * PLACES for i in range(PLACES)]
		watch = [[None] * PLACES for i in range(PLACES)]
		for y in range(PLACES):
			for x in range(PLACES):
				if standing[y][x] != 1:
					continue
				d = abs(x - tx) + abs(y - ty)
				cost = danger[y][x] * config.SMART_HIDE_DANGER_COST
				if d < near:
					cost += (near - d) * config.SMART_HIDE_NEAR_COST
				elif d > far:
					cost += (d - far) * config.SMART_HIDE_FAR_COST
				# tank fully in grass is hidden, partly - partly
				cost -= config.SMART_GRASS_BONUS * (((x, y) in grass) + ((x + 1, y) in grass) + ((x, y + 1) in grass) + ((x + 1, y + 1) in grass)) / 4.0
				dx, dy = tx - x, ty - y
				options = []
				if dx:
					lane = right[y][x] if dx > 0 else left[y][x]
					options.append((lane >= abs(dx) - 1, lane, DIR_RIGHT if dx > 0 else DIR_LEFT))
				if dy:
					lane = down[y][x] if dy > 0 else up[y][x]
					options.append((lane >= abs(dy) - 1, lane, DIR_DOWN if dy > 0 else DIR_UP))
				if options:
					best = max(options)
					watch[y][x] = best[2]
					# lane crosses the player's row / column: he drives into the line of fire
					if best[0]:
						cost -= config.SMART_AMBUSH_BONUS
					# wall right next to the tank between it and the player
					if min([option[1] for option in options]) <= 1:
						cost -= config.SMART_COVER_BONUS
				for sx, sy in SPAWN_PLACES:
					if abs(x - sx) < 2 and abs(y - sy) < 2:
						cost += config.SMART_HIDE_NEAR_COST * 4
				hide[y][x] = cost
		self.hide = hide
		self.watch = watch

	def watchDirection(self, spot):
		if self.watch == None:
			return None
		return self.watch[spot[1]][spot[0]]
