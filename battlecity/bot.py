# coding=utf-8
""" Battle City: computer partner (bot) of one human player

Bot plays with player 2 tank like a human: it presses direction buttons (player.pressed) and fire
(Game.playerFire), so speed, bullets, ice, water and all rules are the same as for a human.
Every frame it decides in this order: dodge (or shoot down) an enemy bullet, let the human pass,
step out of an enemy's line of fire while own bullet isn't ready, get unstuck, aim at an enemy in line
of fire, follow the way to the chosen place. The place (Dijkstra on 16 px cells) is the best place to
shoot an enemy from (enemies near the castle first) or a near bonus the human isn't closer to.
Bot never fires when own castle, fortress walls or the human are in its line of fire.
"""

import random, heapq
import pygame

from battlecity import config, state
from battlecity.tank import Enemy, CELL, tankBlocks

# cell steps of directions up, right, down, left
STEPS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

# walls around the castle (Level.buildFortress)
FORTRESS_CELLS = set([(11, 23), (11, 24), (11, 25), (14, 23), (14, 24), (14, 25), (12, 23), (13, 23)])
FORTRESS_RECT = pygame.Rect(11 * CELL, 23 * CELL, 4 * CELL, 3 * CELL)

# enemy spawn places (cells): bot waits for enemies there when there are none
SPAWN_PLACES = [(12, 0), (24, 0), (0, 0)]


def opposite(direction):
	return (direction + 2) % 4


def rectCells(rect):
	""" 16 px cells covered by rect """
	return [(cx, cy) for cy in range(max(rect.top, 0) // CELL, min((rect.bottom - 1) // CELL, 25) + 1)
		for cx in range(max(rect.left, 0) // CELL, min((rect.right - 1) // CELL, 25) + 1)]


class Bot():

	def __init__(self, game, player):
		self.game = game
		self.player = player
		# frames since bot was created
		self.frame = 0
		# cell -> [extra way cost, frames left]: human's lane after bot let him pass, cells bot got stuck at
		self.avoid = {}
		self.reset()

	def reset(self):
		""" Forget plans: tank died, respawned or new stage started """
		self.level = None
		self.path = []
		self.goal = None
		self.plan_timer = 0
		# frames target is in line of fire in the direction tank looks
		self.seen = 0
		self.last_fire = -1000
		# enemy bullets: id -> [frame seen, will dodge]
		self.bullets = {}
		self.dodge_dir = None
		# forced move (sidestep, letting human pass, stepping out of line of fire): direction and px left
		self.move_dir = None
		self.move_px = 0
		self.move_stuck = 0
		self.last_pos = None
		self.last_pressed = None
		self.stuck = 0
		# frames without a way to the goal
		self.idle = 0
		self.humans_pos = {}
		self.human_blocked = 0
		self.threat_seen = 0

	# ---------------------------------------------------------------- what bot sees

	def humans(self):
		return [player for player in state.players if player is not self.player and player.state == player.STATE_ALIVE]

	def enemies(self):
		""" Alive enemies bot sees: hidden stealth tank only when it is near (a human hardly sees it either) """
		result = []
		p = self.player
		for enemy in state.enemies:
			if enemy.state != enemy.STATE_ALIVE:
				continue
			if enemy.type == Enemy.TYPE_STEALTH and not enemy.bonus and enemy.reveal_frames <= 0:
				if abs(enemy.rect.centerx - p.rect.centerx) + abs(enemy.rect.centery - p.rect.centery) > 96:
					continue
			result.append(enemy)
		return result

	def ray(self, direction, rect = None):
		""" Line of bullet fired from tank (rect) in direction to screen edge and distance function of rects on it """
		r = rect or self.player.rect
		if direction == 0:
			return pygame.Rect(r.centerx - 4, 0, 8, max(0, r.top)), lambda t: r.top - t.bottom
		if direction == 2:
			return pygame.Rect(r.centerx - 4, r.bottom, 8, max(0, 416 - r.bottom)), lambda t: t.top - r.bottom
		if direction == 3:
			return pygame.Rect(0, r.centery - 4, max(0, r.left), 8), lambda t: r.left - t.right
		return pygame.Rect(r.right, r.centery - 4, max(0, 416 - r.right), 8), lambda t: t.left - r.right

	def shotInfo(self, direction, target):
		""" Bullet from bot in direction at target rect
		@return None if target isn't in line or steel is between, else (distance px, brick rows between) """
		level = self.game.level
		ray, dist = self.ray(direction)
		# target touching the tank is on the line too
		if not ray.inflate(0 if direction % 2 == 0 else 2, 2 if direction % 2 == 0 else 0).colliderect(target):
			return None
		distance = dist(target)
		if distance < -8:
			return None
		rows = set()
		rects = level.obstacle_rects
		for i in ray.collidelistall(rects):
			tile = rects[i]
			tile_type = getattr(tile, "type", None)
			if tile_type not in (level.TILE_BRICK, level.TILE_STEEL) or dist(tile) >= distance:
				continue
			if tile_type == level.TILE_STEEL and self.player.bullet_power < 3:
				return None
			rows.add(dist(tile) // 8)
		return distance, len(rows)

	def safeToFire(self, direction, target_distance = None):
		""" Bullet fired in direction can't hit own castle, fortress walls or the human.
		target_distance: target stops the bullet there - the human or fortress behind a target at point blank don't matter """
		level = self.game.level
		ray, dist = self.ray(direction)
		point_blank = target_distance != None and target_distance <= config.BOT_POINT_BLANK

		def covered(rect):
			return point_blank and dist(rect) >= target_distance

		for castle in self.game.castles():
			if castle.active and ray.colliderect(castle.rect):
				return False
		for human in self.humans():
			if ray.colliderect(human.rect) and not covered(human.rect):
				return False
		if ray.colliderect(FORTRESS_RECT):
			rects = level.obstacle_rects
			for i in ray.collidelistall(rects):
				tile = rects[i]
				if getattr(tile, "type", None) in (level.TILE_BRICK, level.TILE_STEEL) and FORTRESS_RECT.colliderect(tile) and not covered(tile):
					return False
		return True

	def slotBusy(self):
		return Enemy.smartSlotBusy(self.player)

	def canMove(self, direction, px):
		""" Tank could drive px in direction now (nothing blocks it on the way) """
		p = self.player
		rect = p.rect.copy()
		dx, dy = STEPS[direction]
		free = True
		try:
			for step in range(0, px, 2):
				if Enemy.stepBlock(p, direction) != None:
					free = False
					break
				p.rect.move_ip(dx * 2, dy * 2)
		finally:
			p.rect = rect
		return free

	# ---------------------------------------------------------------- actions

	def fire(self):
		""" Press fire (not more often than a human can) """
		if self.frame - self.last_fire < config.BOT_FIRE_INTERVAL or self.slotBusy():
			return False
		self.last_fire = self.frame
		self.game.playerFire(self.player)
		return True

	def force(self, direction, px):
		""" Drive px in direction regardless of plans """
		self.move_dir = direction
		self.move_px = px
		self.move_stuck = 0

	def avoidCells(self, cells, frames):
		for cell in cells:
			self.avoid[cell] = [config.BOT_AVOID_COST, frames]

	# ---------------------------------------------------------------- frame

	def update(self):
		""" Called every game frame instead of human input """
		p, game = self.player, self.game
		self.frame += 1
		p.pressed = [False] * 4
		p.fire_pressed = False
		if p.state != p.STATE_ALIVE or game.game_over or not game.active:
			self.reset()
			return
		if self.level is not game.level:
			self.reset()
			self.level = game.level

		for cell in list(self.avoid):
			self.avoid[cell][1] -= 1
			if self.avoid[cell][1] <= 0:
				del self.avoid[cell]

		position = p.rect.topleft
		moved = self.last_pos != None and position != self.last_pos
		if moved:
			self.stuck = 0
			if self.move_px > 0:
				self.move_px -= abs(position[0] - self.last_pos[0]) + abs(position[1] - self.last_pos[1])
		elif self.last_pressed != None and not p.paralised and p.slide == 0:
			self.stuck += 1
		self.last_pos = position

		direction = self.decide()

		for human in state.players:
			self.humans_pos[id(human)] = human.rect.topleft
		if direction != None:
			p.pressed[direction] = True
		self.last_pressed = direction

	def decide(self):
		""" Direction to press this frame (None - nothing), fires on the way """
		p = self.player

		dodge = self.dodge()
		if dodge != None:
			self.dodge_dir = dodge
			self.move_px = 0
			return dodge
		self.dodge_dir = None

		aim = self.aim()
		if aim != None and aim[0] == p.direction:
			self.seen += 1
			if self.seen > config.BOT_REACTION_FRAMES:
				self.fire()
		else:
			self.seen = 0

		# frozen or stunned: can only turn and shoot
		if p.paralised:
			self.move_px = 0
			return aim[0] if aim != None and aim[0] != p.direction else None

		blocked = self.humanBlocked()
		self.human_blocked = self.human_blocked + 1 if blocked else 0
		if self.human_blocked > config.BOT_YIELD_FRAMES:
			self.human_blocked = 0
			self.letPass(*blocked)

		if self.move_px <= 0 and self.slotBusy():
			self.juke()
		else:
			self.threat_seen = 0

		if self.move_px > 0:
			if self.stuck > 3:
				self.move_px = 0
			else:
				return self.move_dir

		if self.stuck >= config.BOT_STUCK_FRAMES and self.last_pressed != None:
			if Enemy.stepBlock(p, p.direction) == "brick" and self.stuck < config.BOT_STUCK_FRAMES * 5 and self.safeToFire(p.direction):
				# shoot through the brick in front
				self.fire()
				return p.direction
			self.sidestep()
			return self.move_dir

		if aim != None:
			return aim[0] if aim[0] != p.direction else None

		return self.followPath()

	# ---------------------------------------------------------------- dodging

	def incoming(self):
		""" Enemy bullets flying at the bot: [(frames to hit, bullet)], nearest first """
		p, level = self.player, self.game.level
		r = p.rect
		result = []
		for bullet in state.bullets:
			if bullet.state != bullet.STATE_ACTIVE or bullet.owner != bullet.OWNER_ENEMY:
				continue
			b = bullet.rect
			if bullet.direction in (bullet.DIR_UP, bullet.DIR_DOWN):
				if b.right <= r.left or b.left >= r.right:
					continue
				if bullet.direction == bullet.DIR_UP:
					distance = b.top - r.bottom
					between = pygame.Rect(b.left, r.bottom, b.width, max(distance, 0))
				else:
					distance = r.top - b.bottom
					between = pygame.Rect(b.left, b.bottom, b.width, max(distance, 0))
			else:
				if b.bottom <= r.top or b.top >= r.bottom:
					continue
				if bullet.direction == bullet.DIR_LEFT:
					distance = b.left - r.right
					between = pygame.Rect(r.right, b.top, max(distance, 0), b.height)
				else:
					distance = r.left - b.right
					between = pygame.Rect(b.right, b.top, max(distance, 0), b.height)
			if distance < -4:
				continue
			# wall between stops the bullet
			if not bullet.over_walls and distance > 0 and between.collidelist(level.land_obstacle_rects) != -1:
				continue
			result.append((max(distance, 0) / max(bullet.speed, 0.1), bullet))
		result.sort(key=lambda item: item[0])
		return result

	def dodge(self):
		""" Enemy bullet flies at bot (seen for reaction time, BOT_DODGE_CHANCE of bullets): shoot it down if tank looks
		at it, else direction to drive out of its way (or to turn to it and shoot it down if there is no time) """
		p = self.player
		incoming = self.incoming()
		self.bullets = dict([(id(bullet), self.bullets.get(id(bullet), [self.frame, random.random() * 100 < config.BOT_DODGE_CHANCE]))
			for frames, bullet in incoming])
		r = p.rect
		for frames, bullet in incoming:
			seen, will_dodge = self.bullets[id(bullet)]
			if not will_dodge or self.frame - seen < config.BOT_DODGE_REACTION_FRAMES:
				continue
			facing = opposite(bullet.direction)
			if p.direction == facing and not self.slotBusy() and self.safeToFire(facing):
				if self.fire():
					continue
			b = bullet.rect
			if bullet.direction in (bullet.DIR_UP, bullet.DIR_DOWN):
				options = [(p.DIR_LEFT, r.right - b.left), (p.DIR_RIGHT, b.right - r.left)]
			else:
				options = [(p.DIR_UP, r.bottom - b.top), (p.DIR_DOWN, b.bottom - r.top)]
			options.sort(key=lambda option: (option[0] != self.dodge_dir, option[1]))
			for direction, px in options:
				if (p.paralised or px / max(p.speed, 0.1) <= frames + 1) and self.canMove(direction, px):
					return direction
			if p.direction != facing and frames > 2 and not self.slotBusy() and self.safeToFire(facing):
				return facing
		return None

	def juke(self):
		""" Enemy in clear line looks at bot, bot's bullet isn't ready: step aside (BOT_JUKE_CHANCE) """
		p = self.player
		threat = None
		for enemy in self.enemies():
			for direction in range(4):
				if enemy.direction != opposite(direction):
					continue
				info = self.shotInfo(direction, enemy.rect)
				if info != None and info[1] == 0 and info[0] <= config.BOT_JUKE_DISTANCE:
					threat = direction
		if threat == None:
			self.threat_seen = 0
			return
		self.threat_seen += 1
		if self.threat_seen != config.BOT_REACTION_FRAMES or random.random() * 100 >= config.BOT_JUKE_CHANCE:
			return
		sides = [(threat + 1) % 4, (threat + 3) % 4]
		random.shuffle(sides)
		for side in sides:
			if self.canMove(side, 24):
				self.force(side, 24)
				return

	# ---------------------------------------------------------------- human and walls

	def humanBlocked(self):
		""" Human presses a direction and can't move because bot is in the way: (human, direction) or None """
		p = self.player
		for human in self.humans():
			pressed = [human.pressed[i] or human.pad_pressed[i] for i in range(4)]
			if True not in pressed or human.paralised or human.rect.topleft != self.humans_pos.get(id(human)):
				continue
			direction = pressed.index(True)
			dx, dy = STEPS[direction]
			new_rect = human.rect.move(dx * 2, dy * 2)
			if new_rect.colliderect(p.rect) and tankBlocks(new_rect, direction, p):
				return human, direction
		return None

	def letPass(self, human, direction):
		""" Drive out of the human's way and don't come back to his lane for a while """
		sides = [(direction + 1) % 4, (direction + 3) % 4]
		random.shuffle(sides)
		for choice in sides + [direction]:
			if self.canMove(choice, 34):
				self.force(choice, 34)
				break
		else:
			for choice in sides + [direction]:
				if self.canMove(choice, 16):
					self.force(choice, 16)
					break
		hx, hy = human.rect.left // CELL, human.rect.top // CELL
		dx, dy = STEPS[direction]
		lane = []
		for k in range(12):
			for side in range(2):
				if dx == 0:
					lane.append((hx + side, hy + k * dy + (1 if dy > 0 else 0)))
				else:
					lane.append((hx + k * dx + (1 if dx > 0 else 0), hy + side))
		self.avoidCells(lane, config.BOT_YIELD_AVOID_FRAMES)
		self.path = []
		self.plan_timer = 0

	def sidestep(self):
		""" Stuck: drive aside (or back) for a cell and find the way again avoiding the cell in front """
		p = self.player
		self.stuck = 0
		dx, dy = STEPS[p.direction]
		front = p.rect.move(dx * CELL, dy * CELL)
		self.avoidCells(rectCells(front), config.BOT_STUCK_AVOID_FRAMES)
		sides = [(p.direction + 1) % 4, (p.direction + 3) % 4]
		random.shuffle(sides)
		for direction in sides + [opposite(p.direction)]:
			if self.canMove(direction, CELL):
				self.force(direction, CELL)
				break
		else:
			self.force(random.randint(0, 3), CELL)
		self.path = []
		self.plan_timer = 0

	# ---------------------------------------------------------------- aiming

	def aim(self):
		""" Best direction to shoot an enemy: clear line (behind few bricks only at chosen place), safe to fire
		@return (direction, enemy) or None """
		p = self.player
		place = self.place()
		at_goal = place == self.goal
		best = None
		for enemy in self.enemies():
			for direction in range(4):
				info = self.shotInfo(direction, enemy.rect)
				if info == None:
					continue
				distance, bricks = info
				if bricks > (config.BOT_MAX_BRICK_CELLS * 2 if at_goal else 0):
					continue
				if not self.safeToFire(direction, distance):
					continue
				score = distance + bricks * 64 + (0 if direction == p.direction else 40)
				if best == None or score < best[0]:
					best = (score, direction, enemy)
		return None if best == None else (best[1], best[2])

	# ---------------------------------------------------------------- way

	def place(self):
		""" Cell of tank's top left corner (nearest) """
		r = self.player.rect
		return (min(max(int(round(r.left / float(CELL))), 0), 24), min(max(int(round(r.top / float(CELL))), 0), 24))

	def followPath(self):
		""" Direction to next cell of the way, new way every BOT_PLAN_FRAMES """
		p = self.player
		self.plan_timer -= 1
		if self.plan_timer <= 0:
			self.plan()
		on_ice = p.onIce()
		if on_ice and p.slide > 0:
			# let the tank slide, then decide
			return None
		while self.path:
			x, y = self.path[0]
			dx, dy = x * CELL - p.rect.left, y * CELL - p.rect.top
			if abs(dx) <= 2 and abs(dy) <= 2:
				self.path.pop(0)
				continue
			if abs(dx) > CELL + 4 or abs(dy) > CELL + 4:
				# way from other place (tank slid or was pushed aside)
				self.plan()
				if not self.path:
					return None
				x, y = self.path[0]
				dx, dy = x * CELL - p.rect.left, y * CELL - p.rect.top
				if abs(dx) > CELL + 4 or abs(dy) > CELL + 4:
					self.path = []
					return None
			# sliding on ice goes too far: near goal is good enough
			if on_ice and self.goal and abs(self.goal[0] * CELL - p.rect.left) + abs(self.goal[1] * CELL - p.rect.top) < 64:
				self.path = []
				return None
			self.idle = 0
			if abs(dx) >= abs(dy):
				return p.DIR_RIGHT if dx > 0 else p.DIR_LEFT
			return p.DIR_DOWN if dy > 0 else p.DIR_UP
		# no way although goal isn't reached: don't stand, drive aside and look for the way again
		if self.goal != None and self.place() != self.goal:
			self.idle += 1
			if self.idle > config.BOT_STUCK_FRAMES * 3:
				self.idle = 0
				self.sidestep()
				return self.move_dir
		return None

	def plan(self):
		""" Choose goal place and way to it (cheapest way on 16 px cells) """
		self.plan_timer = config.BOT_PLAN_FRAMES
		p, game = self.player, self.game
		level = game.level
		can_swim = p.canSwim()

		# cost of 16 px cells, None - impassable
		costs = [[1] * 26 for i in range(26)]
		steel, bricks = set(), set()
		for tile in level.mapr:
			if tile.type == level.TILE_BRICK:
				cost = config.BOT_BRICK_COST
			elif tile.type == level.TILE_STEEL:
				cost = None
			elif tile.type == level.TILE_WATER and not can_swim:
				cost = None
			else:
				continue
			for cx, cy in rectCells(tile):
				if tile.type == level.TILE_BRICK:
					bricks.add((cx, cy))
				elif tile.type == level.TILE_STEEL:
					steel.add((cx, cy))
				if costs[cy][cx] != None:
					costs[cy][cx] = None if cost == None else max(costs[cy][cx], cost)
		# fortress walls are never shot through
		fortress_walls = set([cell for cell in FORTRESS_CELLS if cell in bricks or cell in steel])
		for cx, cy in fortress_walls:
			costs[cy][cx] = None
		for castle in game.castles():
			for cx, cy in rectCells(castle.rect):
				costs[cy][cx] = None
		for human in self.humans():
			for cx, cy in rectCells(human.rect):
				if costs[cy][cx] != None:
					costs[cy][cx] += config.BOT_HUMAN_COST
		enemies = self.enemies()
		for enemy in enemies:
			for cx, cy in rectCells(enemy.rect):
				if costs[cy][cx] != None:
					costs[cy][cx] += config.BOT_ENEMY_COST
		for (cx, cy), (cost, frames) in self.avoid.items():
			if 0 <= cx < 26 and 0 <= cy < 26 and costs[cy][cx] != None:
				costs[cy][cx] += cost

		def placeCost(x, y):
			cells = [costs[y][x], costs[y][x + 1], costs[y + 1][x], costs[y + 1][x + 1]]
			return None if None in cells else max(cells)

		start = self.place()
		best = {start: 0}
		previous = {}
		queue = [(0, start)]
		while queue:
			cost, place = heapq.heappop(queue)
			if cost > best.get(place, cost):
				continue
			x, y = place
			for nx, ny in ((x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)):
				if 0 <= nx <= 24 and 0 <= ny <= 24:
					step = placeCost(nx, ny)
					if step != None and cost + step < best.get((nx, ny), 10 ** 9):
						best[(nx, ny)] = cost + step
						previous[(nx, ny)] = place
						heapq.heappush(queue, (cost + step, (nx, ny)))

		castle_center = state.castle.rect.center

		def castleDistance(rect):
			return abs(rect.centerx - castle_center[0]) + abs(rect.centery - castle_center[1])

		def shotCost(place, target):
			""" Extra cost of shooting target rect from place, None - it can't be shot from there """
			x, y = place
			cx, cy = x * CELL + CELL, y * CELL + CELL
			tx0, tx1 = target.left // CELL, (target.right - 1) // CELL
			ty0, ty1 = target.top // CELL, (target.bottom - 1) // CELL
			if abs(cx - target.centerx) < 12:
				if y + 1 < ty0:
					cells, direction = [(col, row) for col in (x, x + 1) for row in range(y + 2, ty0)], 2
				elif y > ty1:
					cells, direction = [(col, row) for col in (x, x + 1) for row in range(ty1 + 1, y)], 0
				else:
					return None
			elif abs(cy - target.centery) < 12:
				if x + 1 < tx0:
					cells, direction = [(col, row) for row in (y, y + 1) for col in range(x + 2, tx0)], 1
				elif x > tx1:
					cells, direction = [(col, row) for row in (y, y + 1) for col in range(tx1 + 1, x)], 3
				else:
					return None
			else:
				return None
			if p.bullet_power < 3 and any([cell in steel for cell in cells]):
				return None
			if any([cell in fortress_walls for cell in cells]):
				return None
			# rows (columns) of bricks across the line
			brick_cells = len(set([cell[1] if direction % 2 == 0 else cell[0] for cell in cells if cell in bricks]))
			if brick_cells > config.BOT_MAX_BRICK_CELLS:
				return None
			ray, dist = self.ray(direction, pygame.Rect(x * CELL, y * CELL, 32, 32))
			for castle in game.castles():
				if castle.active and ray.colliderect(castle.rect):
					return None
			return brick_cells * config.BOT_BRICK_SHOT_COST + len(cells) // 2 * 0.2

		candidates = {}

		def add(total, place):
			if place not in candidates or total < candidates[place]:
				candidates[place] = total

		threats = [enemy for enemy in enemies if castleDistance(enemy.rect) <= config.BOT_DEFEND_DISTANCE]
		for enemy in threats or enemies:
			priority = castleDistance(enemy.rect) / float(CELL) * config.BOT_CASTLE_PRIORITY
			for place in best:
				extra = shotCost(place, enemy.rect)
				if extra != None:
					add(best[place] + extra + priority, place)

		if not threats:
			for bonus in state.bonuses:
				if not bonus.active:
					continue
				mine = abs(bonus.rect.centerx - p.rect.centerx) + abs(bonus.rect.centery - p.rect.centery)
				if any([abs(bonus.rect.centerx - h.rect.centerx) + abs(bonus.rect.centery - h.rect.centery) < mine for h in self.humans()]):
					continue
				for place in best:
					if best[place] <= config.BOT_BONUS_DISTANCE and pygame.Rect(place[0] * CELL, place[1] * CELL, 32, 32).colliderect(bonus.rect):
						add(best[place] - config.BOT_BONUS_VALUE, place)

		if not candidates and not enemies:
			# wait for enemies where they appear
			for sx, sy in SPAWN_PLACES:
				spawn = pygame.Rect(sx * CELL, sy * CELL, 32, 32)
				for place in best:
					extra = shotCost(place, spawn)
					if extra != None and abs(place[1] - sy) >= 4:
						add(best[place] + extra, place)

		if not candidates:
			# nowhere to shoot from: get closer to nearest enemy (or to the castle)
			targets = [(enemy.rect.left // CELL, enemy.rect.top // CELL) for enemy in enemies] or [(12, 20)]
			for place in best:
				distance = min([abs(place[0] - tx) + abs(place[1] - ty) for tx, ty in targets])
				if distance >= 2:
					add(best[place] + distance * 2, place)

		if not candidates:
			self.goal = None
			self.path = []
			return

		goal = min(candidates, key=lambda place: candidates[place])
		old = self.goal
		if old in candidates and old != goal and candidates[old] <= candidates[goal] + config.BOT_GOAL_STICKINESS:
			goal = old
		self.goal = goal

		path = []
		while goal != start:
			path.append(goal)
			goal = previous[goal]
		path.reverse()
		# tank between cells: first to its own cell, so every step is at most one cell long
		if p.rect.topleft != (start[0] * CELL, start[1] * CELL):
			path.insert(0, start)
		self.path = path
