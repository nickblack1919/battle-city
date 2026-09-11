# coding=utf-8
""" Battle City: tanks: player and enemies """

import os, random, uuid, sys, json, heapq
import pygame
from pygame.locals import *

from battlecity import config, state, commander
from battlecity.bonus import Bonus
from battlecity.bullet import Bullet
from battlecity.effects import Explosion, Label

# tank collisions like on NES: tanks mark map cells (8 NES px = 16 px here) they occupy,
# moving tank checks only 2 corner points of its new front edge against these cells

CELL = 16

def tankCells(tank):
	""" Map cells marked as occupied by tank (NES sub_E181): bottom right cell of tank's
	top left 2x2 cells, plus bottom left one if tank is aligned to the cell grid horizontally
	and top right one if aligned vertically. Top left cell is never marked, and a tank between
	cells marks only its middle column / row, so a small overlap of tanks doesn't block them
	"""
	cx, cy = tank.rect.left // CELL, tank.rect.top // CELL
	cells = set([(cx + 1, cy + 1)])
	if tank.rect.left % CELL == 0:
		cells.add((cx, cy + 1))
	if tank.rect.top % CELL == 0:
		cells.add((cx + 1, cy))
	return cells

def frontCells(new_rect, direction):
	""" Cells under 2 corner points of the front edge of tank moved to new_rect """
	left, top, right, bottom = new_rect.left, new_rect.top, new_rect.right - 1, new_rect.bottom - 1
	if direction == Tank.DIR_UP:
		points = [(left, top), (right, top)]
	elif direction == Tank.DIR_DOWN:
		points = [(left, bottom), (right, bottom)]
	elif direction == Tank.DIR_LEFT:
		points = [(left, top), (left, bottom)]
	else:
		points = [(right, top), (right, bottom)]
	return set([(x // CELL, y // CELL) for x, y in points])

def tankBlocks(new_rect, direction, other):
	""" Other tank blocks move to new_rect in direction (NES rule) """
	return len(frontCells(new_rect, direction) & tankCells(other)) > 0

def frontEdgeCells(new_rect, direction):
	""" All cells under the front edge of tank moved to new_rect: 2 corner cells like on NES,
	and the middle one for a tank between cells (otherwise it would drive into a 1 cell wide wall) """
	left, top, right, bottom = new_rect.left, new_rect.top, new_rect.right - 1, new_rect.bottom - 1
	if direction in (Tank.DIR_UP, Tank.DIR_DOWN):
		y = top if direction == Tank.DIR_UP else bottom
		return set([(x // CELL, y // CELL) for x in list(range(left, right, CELL)) + [right]])
	x = left if direction == Tank.DIR_LEFT else right
	return set([(x // CELL, y // CELL) for y in list(range(top, bottom, CELL)) + [bottom]])

def tilesBlock(level, new_rect, direction, can_swim):
	""" Walls block move to new_rect (NES rule): cells under the front edge are checked,
	a cell with any part of a wall (even one brick quarter) blocks the tank """
	obstacles = level.obstacleRectsFor(can_swim)
	for cx, cy in frontEdgeCells(new_rect, direction):
		if pygame.Rect(cx * CELL, cy * CELL, CELL, CELL).collidelist(obstacles) != -1:
			return True
	return False

class Tank():

	# possible directions
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)

	# states
	(STATE_SPAWNING, STATE_DEAD, STATE_ALIVE, STATE_EXPLODING) = range(4)

	# sides
	(SIDE_PLAYER, SIDE_ENEMY) = range(2)

	def __init__(self, level, side, position = None, direction = None, filename = None):


		# health. 0 health means dead
		self.health = 100

		# tank can't move but can rotate and shoot
		self.paralised = False
		# reasons: stunned by partner's bullet, frozen by enemy clock bonus or pause
		self.stunned = False
		self.frozen = False

		# tank can't do anything
		self.paused = False

		# tank is protected from bullets
		self.shielded = False

		# px per move
		self.speed = config.DEFAULT_ENEMY_SPEED

		# friend or foe
		self.side = side

		# flashing state. 0-off, 1-on
		self.flash = 0
		
		self.bullet_speed = config.DEFAULT_BULLET_SPEED
		self.bullet_power = 1
		# how many bullets can tank fire simultaneously
		self.max_active_bullets = config.PLAYER_START_MAX_ACTIVE_BULLETS

		self.superpowers = 0
		# self.updateSuperpowers()

		# each tank can pick up 1 bonus
		self.bonus = None

		# navigation keys: fire, up, right, down, left
		self.controls = [pygame.K_j, pygame.K_w, pygame.K_d, pygame.K_s, pygame.K_a]

		# currently pressed buttons (navigation only)
		self.pressed = [False] * 4

		# fire button is held (auto fire)
		self.fire_pressed = False
		# first shot doesn't wait for auto fire delay
		self.last_fire_time = -10 ** 9

		# gamepad assigned to this tank and its state: up, right, down, left / fire
		self.gamepad = None
		self.pad_pressed = [False] * 4
		self.pad_fire = False

		# visibility state
		self.visible = True

		# ship bonus: can drive over water
		self.ship = False
		self.ship_timer = None
		# ship ended while tank was on water
		self.drive_out = False

		# px left to slide on ice
		self.slide = 0

		# fractional part of movement (speed can be fractional, tanks move by whole px)
		self.move_credit = 0.0

		# frames stealth tank stays visible
		self.reveal_frames = 0

		# frontal armor (player superpower 5+)
		self.protected = False
		self.protected_image = state.sprites2.subsurface((10+5)*32+4, 9*32, 16*2, 16*2)

		self.shield_images = [
			# sprites.subsurface(0, 48*2, 16*2, 16*2),
			# sprites.subsurface(16*2, 48*2, 16*2, 16*2)
			state.sprites2.subsurface(7*32+4, 9*32, 16*2, 16*2),
			state.sprites2.subsurface(8*32+4, 9*32, 16*2, 16*2)
		]
		self.shield_image = self.shield_images[0]
		self.shield_index = 0

		self.spawn_images = [
			state.sprites.subsurface(32*2, 48*2, 16*2, 16*2),
			state.sprites.subsurface(48*2, 48*2, 16*2, 16*2)
		]
		self.spawn_image = self.spawn_images[0]
		self.spawn_index = 0

		self.level = level

		if position != None:
			self.rect = pygame.Rect(position, (32, 32))
		else:
			self.rect = pygame.Rect(0, 0, 32, 32)

		if direction == None:
			self.direction = random.choice([self.DIR_UP, self.DIR_RIGHT, self.DIR_DOWN, self.DIR_LEFT])
		else:
			self.direction = direction

		self.state = self.STATE_SPAWNING

		# spawning animation
		self.timer_uuid_spawn = state.gtimer.add(100, lambda :self.toggleSpawnImage())

		# duration of spawning
		self.timer_uuid_spawn_end = state.gtimer.add(config.ENEMY_SPAWN_ANIMATION_TIME, lambda :self.endSpawning())

		self.visibility_timer = None

		self.shield_end_timer = None

		self.timer_uuid_shield = None

		self.dbg_label = Label(self.rect.bottomleft, str(self.rect.topleft))

	def toggleVisibility(self):
		""" Toggle tank visibility """
		self.visible = not self.visible

	def hideTank(self, duration = None):
		if self.visibility_timer:
			state.gtimer.destroy(self.visibility_timer)

		self.setVisibility(False)
		self.visibility_timer = state.gtimer.add(duration, lambda: self.setVisibility(True), 1)


	def setVisibility(self, visible):
		""" Set tank visibility """
		self.visible = visible

	def endSpawning(self):
		""" End spawning
		Player becomes operational
		"""
		self.state = self.STATE_ALIVE
		state.gtimer.destroy(self.timer_uuid_spawn_end)

	def startSpawning(self, duration):
		""" Show flashing star for duration ms, then tank becomes operational """
		state.gtimer.destroy(self.timer_uuid_spawn)
		state.gtimer.destroy(self.timer_uuid_spawn_end)
		self.state = self.STATE_SPAWNING
		self.timer_uuid_spawn = state.gtimer.add(100, lambda :self.toggleSpawnImage())
		self.timer_uuid_spawn_end = state.gtimer.add(duration, lambda :self.endSpawning())


	def toggleSpawnImage(self):
		""" advance to the next spawn image """
		if self.state != self.STATE_SPAWNING:
			state.gtimer.destroy(self.timer_uuid_spawn)
			return
		self.spawn_index += 1
		if self.spawn_index >= len(self.spawn_images):
			self.spawn_index = 0
		self.spawn_image = self.spawn_images[self.spawn_index]

	def toggleShieldImage(self):
		""" advance to the next shield image """
		# shield is given when player starts to spawn
		if self.state not in (self.STATE_ALIVE, self.STATE_SPAWNING):
			state.gtimer.destroy(self.timer_uuid_shield)
			return
		if self.shielded:
			self.shield_index += 1
			if self.shield_index >= len(self.shield_images):
				self.shield_index = 0
			self.shield_image = self.shield_images[self.shield_index]

	def draw(self):
		""" draw tank """

		if self.state == self.STATE_ALIVE:
			# hidden state
			if not self.visible:
				return
			state.screen.blit(self.image, self.rect.topleft)
			if self.shielded:
				state.screen.blit(self.shield_image, [self.rect.left, self.rect.top])
			if self.protected:
				state.screen.blit(self.protected_image, [self.rect.left, self.rect.top])
			if self.ship:
				pygame.draw.rect(state.screen, (60, 140, 255), self.rect, 1)
		elif self.state == self.STATE_EXPLODING:
			self.explosion.draw()
		elif self.state == self.STATE_SPAWNING:
			state.screen.blit(self.spawn_image, self.rect.topleft)

		# debug sprites
		if config.DEBUG_SPRITES:
			green = (0,255,0)
			pygame.draw.rect(state.screen, green, self.rect, 1)
			self.dbg_label.position = self.rect.bottomleft
			self.dbg_label.text = str(self.rect.topleft) + " " + str(self.rect.size)
			self.dbg_label.draw()

	def explode(self):
		""" start tanks's explosion """
		if self.state != self.STATE_DEAD:
			self.state = self.STATE_EXPLODING
			# NES durations, explosion has 3 images
			if self.side == self.SIDE_PLAYER:
				duration = config.PLAYER_EXPLOSION_TIME
			elif self.type == Enemy.TYPE_FAST:
				duration = config.FAST_ENEMY_EXPLOSION_TIME
			else:
				duration = config.ENEMY_EXPLOSION_TIME
			self.explosion = Explosion(self.rect.topleft, max(1, duration // 3))
			

	def updateSuperpowers(self):
		""" update player super powers """

		self.updateSprites()

		# 0 - no superpowers
		if self.superpowers >= 0:
			self.bullet_speed = config.DEFAULT_BULLET_SPEED

			self.bullet_power = 1
			self.max_active_bullets = config.PLAYER_START_MAX_ACTIVE_BULLETS
			self.protected = False

		# 1 - faster bullets
		if self.superpowers >= 1:
			self.bullet_speed = config.FAST_BULLET_SPEED

		# 2 - can fire 2 bullets
		if self.superpowers >= 2:
			self.max_active_bullets = 2

		# NES stars: 3rd star - bullets destroy steel, nothing more
		if config.NES_STARS and self.side == self.SIDE_PLAYER:
			if self.superpowers >= 3:
				self.bullet_power = 3
			return

		# 3 - can clear trees
		if self.superpowers >= 3:
			self.bullet_power = 2
			
		# 4 - can destroy steel
		if self.superpowers >= 4:
			self.bullet_power = 3
			
		# 5 - can fire 3 bullets
		if self.superpowers >= 5:
			self.max_active_bullets = 3
			# frontal armor (players only)
			if config.ENABLE_PLAYER_PROTECTION and self.side == self.SIDE_PLAYER:
				self.protected = True
		
		# 6- can clear trees, bricks and steel in 1 shot
		if self.superpowers >= 6:
			self.bullet_power = 4

		# 9 - castle protection (players only)
		if self.superpowers >= 9 and self.side == self.SIDE_PLAYER and state.game.mode != "versus":
			state.castle.protected = True
			
			
	def fire(self, forced = False):
		""" Shoot a bullet
		@param boolean forced. If false, check whether tank has exceeded his bullet quota. Default: True
		@return boolean True if bullet was fired, false otherwise
		"""


		if self.state == self.STATE_SPAWNING:
			return False

		if self.state not in (self.STATE_ALIVE, self.STATE_SPAWNING):
			state.gtimer.destroy(self.timer_uuid_fire)
			return False

		if self.paused:
			return False

		if self.side == self.SIDE_ENEMY and not self.wantsFire():
			return False

		if not forced:
			active_bullets = 0
			for bullet in state.bullets:
				# NES: bullet slot is busy while bullet flies and while it explodes
				if bullet.owner_class == self and (bullet.state == bullet.STATE_ACTIVE or (bullet.state == bullet.STATE_EXPLODING and bullet.slot_busy)):
					active_bullets += 1
			if active_bullets >= self.max_active_bullets:
				return False

		bullet = Bullet(self.level, self.rect.topleft, self.direction)
		bullet.speed = self.bullet_speed
		bullet.power = self.bullet_power

		if self.side == self.SIDE_PLAYER:
			bullet.owner = self.SIDE_PLAYER
		else:
			bullet.owner = self.SIDE_ENEMY
			self.bullet_queued = False

		bullet.owner_class = self
		state.bullets.append(bullet)

		# enemy specials: mortar shells fly over walls, stealth tank shows itself when firing
		if self.side == self.SIDE_ENEMY:
			if self.type == Enemy.TYPE_MORTAR:
				bullet.over_walls = True
				bullet.image = bullet.image.copy()
				bullet.image.fill((255, 90, 90), special_flags=pygame.BLEND_RGB_MULT)
			elif self.type == Enemy.TYPE_STEALTH:
				self.reveal_frames = config.STEALTH_REVEAL_FRAMES

		return True

	def rotate(self, direction, fix_position = True):
		""" Rotate tank
		rotate, update image and correct position
		"""
		self.direction = direction

		if direction == self.DIR_UP:
			self.image = self.image_up
		elif direction == self.DIR_RIGHT:
			self.image = self.image_right
		elif direction == self.DIR_DOWN:
			self.image = self.image_down
		elif direction == self.DIR_LEFT:
			self.image = self.image_left
			
		if fix_position:
			#print "Fixing position"
			#print "Before fixing: " + str(self.rect.left) + ", " + str(self.rect.top)
				
			# snap to 16 px grid: nearest grid line, or the other one if a wall or tank is in the way
			for new_x in self.gridCandidates(self.rect.left):
				for new_y in self.gridCandidates(self.rect.top):
					new_rect = pygame.Rect([new_x, new_y], [32, 32])

					collision = False
					if new_rect.collidelist(self.level.obstacleRectsFor(self.canSwim())) != -1:
						collision = True
					for enemy in state.enemies:
						if enemy != self and new_rect.colliderect(enemy.rect):
							collision = True
					for player in state.players:
						if player != self and player.state == player.STATE_ALIVE and new_rect.colliderect(player.rect):
							collision = True
					if collision:
						continue

					self.rect.left = new_x
					self.rect.top = new_y
					if config.DEBUG_COORDINATES:
						print("After fixing: " + str(self.rect.center))
					return

	def gridCandidates(self, value):
		""" 16 px grid lines to snap coordinate to: nearest first, then the other neighbour """
		nearest = self.nearest(value, 16)
		if value % 16 == 0:
			return [nearest]
		lower = value // 16 * 16
		return [nearest, lower + 16 if nearest == lower else lower]

			
	def turnRandom(self):
		""" Turn tank into random direction """
		self.direction = random.choice([self.DIR_UP, self.DIR_RIGHT, self.DIR_DOWN, self.DIR_LEFT])

	def turnAround(self):
		""" Turn tank into opposite direction """
		if self.direction in (self.DIR_UP, self.DIR_RIGHT):
			self.rotate(self.direction + 2, False)
		else:
			self.rotate(self.direction - 2, False)

	def update(self, time_passed):
		""" Update timer and explosion (if any) """
		if self.state == self.STATE_EXPLODING:
			if not self.explosion.active:
				self.state = self.STATE_DEAD
				del self.explosion

	def nearest(self, num, base):
		""" Round number to nearest divisible """
		return int(round(float(num) / (base * 1.0)) * base)

	def canSwim(self):
		""" Tank can drive over water: ship bonus is active or tank is still on water
		(ship ended while on water - let the tank drive out) """
		ship = self.ship if self.side == self.SIDE_PLAYER else state.game.enemies_ship
		if ship:
			return True
		# ship ended on water: tank can drive out of water, not across it
		on_water = self.rect.collidelist(self.level.water_rects) != -1
		if not on_water:
			self.drive_out = False
		return on_water and self.drive_out

	def onIce(self):
		return self.rect.collidelist(self.level.ice_rects) != -1

	def getOppositeDirection(self, direction):
		""" Get direction opposite to specified one """
		if direction == self.DIR_UP:
			return self.DIR_DOWN
		if direction == self.DIR_DOWN:
			return self.DIR_UP
		if direction == self.DIR_LEFT:
			return self.DIR_RIGHT
		if direction == self.DIR_RIGHT:
			return self.DIR_LEFT

	def bulletImpact(self, friendly_fire = False, damage = 100, tank = None, bulletDirection = DIR_UP):
		""" Bullet impact
		Return True if bullet should be destroyed on impact. Only enemy friendly-fire
		doesn't trigger bullet explosion
		"""


		if self.shielded and not friendly_fire:
			return True

		# frontal armor: bullet flying against tank's direction hits its front and doesn't hurt
		if self.protected and not friendly_fire:
			if config.play_sounds:
				state.sounds["armor"].play()
			if config.HEAD_SHIELD_WHEN_PROTECTED and bulletDirection == self.getOppositeDirection(self.direction):
				return True

		if not friendly_fire:
			if not config.INFINITE_HEALTH_FOR_ALL:
				self.health -= damage
				self.updateSprites()
				self.reveal_frames = config.STEALTH_REVEAL_FRAMES
				# boss drops a bonus every BOSS_BONUS_EVERY damage
				if self.side == self.SIDE_ENEMY and self.type == Enemy.TYPE_BOSS and 0 < self.health and self.health % config.BOSS_BONUS_EVERY == 0:
					self.spawnBonus()

			# restore health if infinite armor
			if config.PLAYER_INFINITE_ARMOR > 0 and self.side == self.SIDE_PLAYER:
				self.health += damage	

			# if enemy tank carries a bonus display it
			if self.side == self.SIDE_ENEMY and self.bonus:
				if not config.INFINITE_BONUSES:
					self.removeBonusLoad()

				# If bonus already exit on screen, remove it
				if len(state.bonuses) > 0 and not config.ALLOW_MULTI_BONUS:
					self.clearAllBonuses()
				
				# Show new bonus
				self.spawnBonus()

			if self.health > 99:
				if config.play_sounds:
						state.sounds["armor"].play()

			elif self.health < 1:
				if self.side == self.SIDE_ENEMY:
					tank.trophies["enemy" + str(self.type)] += 1
					points = config.ENEMY_POINTS[self.type]
					tank.score += points
					if config.play_sounds:
						state.sounds["explosion"].play()

					state.labels.append(Label(self.rect.topleft, str(points), 500))

					# big explosion
					if self.type == self.TYPE_ARMOR:
						state.game.shake(8)
					elif self.type == self.TYPE_BOSS:
						state.game.shake(25)

				# versus: count kills of the other player
				if self.side == self.SIDE_PLAYER and tank != None and tank is not self and tank.side == self.SIDE_PLAYER:
					tank.versus_kills += 1

				self.explode()
				if self.side == self.SIDE_PLAYER:
					if config.play_sounds:
						state.sounds["boom"].play()
			return True

		if self.side == self.SIDE_ENEMY:
			return False
		elif self.side == self.SIDE_PLAYER:
			if not config.FRIENDLY_FIRE:
				return False
			# NES: helmet protects from partner's bullet too
			if self.shielded:
				return True
			if not self.stunned:
				self.setParalised(True)
				self.timer_uuid_paralise = state.gtimer.add(config.FRIENDLY_FIRE_STUN_TIME, lambda :self.setParalised(False), 1)
			return True

	def setParalised(self, paralised = True):
		""" Stun tank (partner's bullet): it can't move, but stays frozen if enemy clock or pause froze it
		@param boolean paralised
		@return None
		"""
		if self.state != self.STATE_ALIVE:
			state.gtimer.destroy(self.timer_uuid_paralise)
			return
		self.stunned = paralised
		self.paralised = self.stunned or self.frozen

	def setFrozen(self, frozen = True):
		""" Freeze tank (enemy clock bonus, pause): stun from partner's bullet stays """
		self.frozen = frozen
		self.paralised = self.stunned or self.frozen


class Enemy(Tank):

	(TYPE_BASIC, TYPE_FAST, TYPE_POWER, TYPE_ARMOR, TYPE_STEALTH, TYPE_MORTAR, TYPE_BOSS) = range(7)
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)
	(FLASHING_YES, FLASHING_NO) = range(2)

	def __init__(self, level, type, position = None, direction = None, filename = None):

		Tank.__init__(self, level, type, position = None, direction = None, filename = None)


		# if true, do not fire
		self.bullet_queued = False

		# how many times tank keeps pushing into obstacle before turning
		self.persistance = 0

		if len(self.level.enemies_left) % config.BONUS_FREQ == config.BONUS_TANK_OFFSET % config.BONUS_FREQ:
			self.bonus = True

		# chose type on random
		if len(level.enemies_left) > 0:
			self.type = level.enemies_left.pop()
		else:
			self.state = self.STATE_DEAD
			return

		if self.type == self.TYPE_BASIC:
			self.speed = config.DEFAULT_ENEMY_SPEED
		elif self.type == self.TYPE_FAST:
			self.speed = config.DEFAULT_ENEMY_SPEED + config.DEFAULT_ENEMY_SPEED_FAST
		elif self.type == self.TYPE_POWER:
			self.speed = config.DEFAULT_ENEMY_SPEED
			self.superpowers = 1
			self.updateSuperpowers()
		elif self.type == self.TYPE_ARMOR:
			self.speed = config.DEFAULT_ENEMY_SPEED
			self.health = config.DEFAULT_ENEMY_ARMOR_HEALTH
		elif self.type == self.TYPE_STEALTH:
			self.speed = config.DEFAULT_ENEMY_SPEED
		elif self.type == self.TYPE_MORTAR:
			self.speed = config.DEFAULT_ENEMY_SPEED
			self.health = 200
		elif self.type == self.TYPE_BOSS:
			self.speed = config.DEFAULT_ENEMY_SPEED
			self.health = config.BOSS_HEALTH
			self.superpowers = 4
			self.updateSuperpowers()
			self.max_active_bullets = 3

		self.image_up = self.getEnemyImage(self.DIR_UP, self.type, self.health, self.FLASHING_NO)
		self.image_left = self.getEnemyImage(self.DIR_LEFT, self.type, self.health, self.FLASHING_NO)
		self.image_down = self.getEnemyImage(self.DIR_DOWN, self.type, self.health, self.FLASHING_NO)
		self.image_right = self.getEnemyImage(self.DIR_RIGHT, self.type, self.health, self.FLASHING_NO)
		self.image = self.image_up

		if self.bonus:
			self.image1_up = self.image_up
			self.image1_left = self.image_left
			self.image1_down = self.image_down
			self.image1_right = self.image_right

			self.image2_up = self.getEnemyImage(self.DIR_UP, self.type, self.health, self.FLASHING_YES)
			self.image2_left = self.getEnemyImage(self.DIR_LEFT, self.type, self.health, self.FLASHING_YES)
			self.image2_down = self.getEnemyImage(self.DIR_DOWN, self.type, self.health, self.FLASHING_YES)
			self.image2_right = self.getEnemyImage(self.DIR_RIGHT, self.type, self.health, self.FLASHING_YES)
			self.image2 = self.image2_up

		self.rotate(self.direction, False)

		if position == None:
			position = state.game.getFreeSpawningPosition() or [0, 0]
		self.rect.topleft = position
				
		# when enemies are spawned they don't aquire poisiton until they find available tile
		# until than the don't collide with other tanks
		self.aquired_position = False

		# list of map coords where tank should go next
		self.path = self.generatePath(self.direction)

		# NES AI: px moved but not used yet (AI works with NES px = 2 px), waiting moves, turn on next move
		self.nes_px = 0
		self.nes_wait = 0
		self.nes_turn = False
		# SMART AI: path (cells), moves to next path update, moves blocked by tank, moves driving at random, frames target seen
		self.smart_path = None
		self.smart_timer = 0
		self.smart_blocked = 0
		self.smart_wander = 0
		self.smart_seen = 0
		self.smart_role = None
		self.smart_blocked_by = None
		# SMART AI: chosen place to shoot from, tank is there, px left to dodge a bullet, player bullets seen: id -> [ms, will dodge]
		self.smart_goal = None
		self.smart_at_goal = False
		self.smart_dodge_px = 0
		self.smart_bullets = {}
		# SMART AI team tactics: order of commander ("hide", "attack", "hunt", "castle"), attack side (direction from
		# player), tank takes player's front, tank waits in hiding spot
		self.smart_order = None
		self.smart_side = None
		self.smart_front = False
		self.smart_waiting = False
		if config.ENEMY_AI in ("NES", "SMART"):
			# NES: new enemy drives down
			self.rotate(self.DIR_DOWN, False)

		# 100ms - 1000ms is duration between shots
		self.timer_uuid_fire = state.gtimer.add(config.ENEMY_FIRE_TIMER, lambda :self.fire())

		# if enemy tank picked up a bonus
		self.bonus_aquired = None

		# turn on flashing
		if self.bonus:
			self.timer_uuid_flash = state.gtimer.add(200, lambda :self.toggleFlash())

	# direction 0-up, 1-right, 2-down, 3-left
	# type 0-basic, 1-fast, 2-power, 3-armor
	def getEnemyImage(self, direction, type, health, flashing):
		""" Sprite for enemy type, direction and health; new types are tinted sprites of original types """
		sprite_type = config.ENEMY_SPRITE_TYPES[type]
		health = max(0, min(int(health), 400))
		if flashing == self.FLASHING_NO:
			image = state.sprites2.subsurface(((health // 100) * config.S_SIZE + direction) * config.T_SIZE, sprite_type * 2 * config.T_SIZE, 32, 32)
		else:
			image = state.sprites2.subsurface(direction * config.T_SIZE, sprite_type * 2 * config.T_SIZE, 32, 32)
		tint = config.ENEMY_TINTS.get(type)
		if tint:
			image = image.copy()
			image.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
		return image

	def draw(self):
		""" Stealth tank is almost invisible until it fires or gets hit, boss has health bar """

		if self.type == self.TYPE_STEALTH and self.state == self.STATE_ALIVE and not self.bonus and self.reveal_frames <= 0:
			if self.visible:
				image = self.image.copy()
				image.set_alpha(config.STEALTH_ALPHA)
				state.screen.blit(image, self.rect.topleft)
			return

		Tank.draw(self)

		if self.type == self.TYPE_BOSS and self.state == self.STATE_ALIVE:
			width = int(32 * max(self.health, 0) / float(config.BOSS_HEALTH))
			pygame.draw.rect(state.screen, (255, 60, 60), [self.rect.left, self.rect.top - 4, max(width, 1), 3])

	def updateSprites(self):
		self.image_up = self.getEnemyImage(self.DIR_UP, self.type, self.health, self.FLASHING_NO)
		self.image_left = self.getEnemyImage(self.DIR_LEFT, self.type, self.health, self.FLASHING_NO)
		self.image_down = self.getEnemyImage(self.DIR_DOWN, self.type, self.health, self.FLASHING_NO)
		self.image_right = self.getEnemyImage(self.DIR_RIGHT, self.type, self.health, self.FLASHING_NO)
		dir_oriented_image = [self.image_up, self.image_right, self.image_down, self.image_left]
		self.image = dir_oriented_image[self.direction]

		if self.bonus:
			self.image1_up = self.image_up
			self.image1_left = self.image_left
			self.image1_down = self.image_down
			self.image1_right = self.image_right

			self.image2_up = self.getEnemyImage(self.DIR_UP, self.type, self.health, self.FLASHING_YES)
			self.image2_left = self.getEnemyImage(self.DIR_LEFT, self.type, self.health, self.FLASHING_YES)
			self.image2_down = self.getEnemyImage(self.DIR_DOWN, self.type, self.health, self.FLASHING_YES)
			self.image2_right = self.getEnemyImage(self.DIR_RIGHT, self.type, self.health, self.FLASHING_YES)
			self.image2 = [self.image2_up, self.image2_right, self.image2_down, self.image2_left][self.direction]
			
	def removeBonusLoad(self):
		""" Remove bonus from enemy tank and stop flashing """
		self.bonus = None
		state.gtimer.destroy(self.timer_uuid_flash)

		self.updateSprites()
		self.rotate(self.direction, False)

	def toggleFlash(self):
		""" Toggle flash state """
		if self.state not in (self.STATE_ALIVE, self.STATE_SPAWNING):
			state.gtimer.destroy(self.timer_uuid_flash)
			return
		self.flash = not self.flash
		if self.flash:
			self.image_up = self.image2_up
			self.image_right = self.image2_right
			self.image_down = self.image2_down
			self.image_left = self.image2_left
		else:
			self.image_up = self.image1_up
			self.image_right = self.image1_right
			self.image_down = self.image1_down
			self.image_left = self.image1_left
		self.rotate(self.direction, False)

	def spawnBonus(self):
		""" Create new bonus if needed """


		if config.play_sounds:
			state.sounds["bonusnew"].play()
		
		bonus = Bonus(self.level)

		state.bonuses.append(bonus)
		# bonus blinks during last seconds before it disappears
		if config.BONUS_SPAWN_TIMEOUT > 0:
			state.gtimer.add(max(config.BONUS_SPAWN_TIMEOUT - config.BONUS_BLINK_TIME, 1), lambda :bonus.startBlinking(), 1)
			state.gtimer.add(config.BONUS_SPAWN_TIMEOUT, lambda :bonus in state.bonuses and state.bonuses.remove(bonus), 1)
		else:
			# NES: bonus stays until picked up, always blinking
			bonus.startBlinking()

		# pickup the bonus immediately it it was placed on a player
		for player in state.players:
			if player.state == player.STATE_ALIVE and player.rect.colliderect(bonus.rect) == True:
				player.bonus = bonus
				return

		if config.ENEMY_PICKUP_BONUSES:
			for enemy in state.enemies:
				if enemy.state == enemy.STATE_ALIVE and enemy.rect.colliderect(bonus.rect) == True:
					enemy.bonus_aquired = bonus

	def clearAllBonuses(self):

		for player in state.players:
			if player.state == player.STATE_ALIVE:
				if player.bonus != None and player.side == player.SIDE_PLAYER:
					player.bonus = None
			
		del state.bonuses[:]

	def move(self):
		""" Move enemy with its speed: speed can be fractional, whole px steps are made,
		the rest is kept for next frame """
		self.move_credit += self.speed
		steps = int(self.move_credit + 1e-9)
		self.move_credit -= steps
		if config.ENEMY_AI in ("NES", "SMART"):
			self.nes_px += steps
			while self.nes_px >= 2:
				self.nes_px -= 2
				if config.ENEMY_AI == "SMART":
					self.moveStepSmart()
				else:
					self.moveStepNes()
			return
		for step in range(steps):
			# NES: tank on 8 px grid sometimes spends a move choosing direction
			if self.rect.left % 16 == 0 and self.rect.top % 16 == 0 and random.random() < config.ENEMY_GRID_PAUSE_CHANCE:
				continue
			self.moveStep()

	def moveStep(self):
		""" move enemy 1 px along its path if possible """


		if self.state != self.STATE_ALIVE or self.paused or self.paralised:
			return

		if self.path == []:
			self.path = self.generatePath(None, True)

		new_position = self.path.pop(0)

		# move enemy
		if self.direction == self.DIR_UP:
			if new_position[1] < 0:
				self.path = self.generatePath(self.direction, True)
				return
		elif self.direction == self.DIR_RIGHT:
			if new_position[0] > (416 - 32):
				self.path = self.generatePath(self.direction, True)
				return
		elif self.direction == self.DIR_DOWN:
			if new_position[1] > (416 - 32):
				self.path = self.generatePath(self.direction, True)
				return
		elif self.direction == self.DIR_LEFT:
			if new_position[0] < 0:
				self.path = self.generatePath(self.direction, True)
				return

		new_rect = pygame.Rect(new_position, [32, 32])

		# collisions with tiles
		if tilesBlock(self.level, new_rect, self.direction, self.canSwim()):
			if self.persistance < 3:
				self.persistance += 1
				rotate = False
			else:
				rotate = True
				self.persistance = 0

			self.path = self.generatePath(self.direction, rotate)
			return
			
		if not self.aquired_position:
			collision = False
			must_wait = False
			for enemy in state.enemies:
				if enemy != self and enemy.state != enemy.STATE_DEAD and new_rect.colliderect(enemy.rect):
					collision = True
					# overlapping tanks: positioned or older tank drives away first,
					# otherwise both would move together and never separate
					if enemy.aquired_position or state.enemies.index(enemy) < state.enemies.index(self):
						must_wait = True
			for player in state.players:
				if player.state == player.STATE_ALIVE and new_rect.colliderect(player.rect):
					collision = True
			if must_wait:
				# stay in place, keep this step for next frame
				self.path.insert(0, new_position)
			elif collision:
				self.rect.topleft = new_rect.topleft
			else:
				self.aquired_position = True
		else:
			# collisions with other enemies (spawning enemies are obstacles too)
			for enemy in state.enemies:
				# like on NES: only alive tanks mark cells, spawning and exploding ones don't block
				if enemy != self and enemy.aquired_position and enemy.state == enemy.STATE_ALIVE and tankBlocks(new_rect, self.direction, enemy):
					self.turnRandom()
					self.path = self.generatePath(self.direction)
					return

			# collisions with players
			for player in state.players:
				if player.state == player.STATE_ALIVE and tankBlocks(new_rect, self.direction, player):
					self.turnRandom()
					self.path = self.generatePath(self.direction)
					return

			# collisions with bonuses
			if config.ENEMY_PICKUP_BONUSES:
				for bonus in state.bonuses:
					if new_rect.colliderect(bonus.rect):
						self.bonus_aquired = bonus

			# if no collision, move enemy
			self.rect.topleft = new_rect.topleft
			if config.DEBUG_COORDINATES:
				print("Move center: " + str(self.rect.center))


	# NES direction numbers (0 up, 1 left, 2 down, 3 right) to ours
	NES_DIRECTIONS = [0, 3, 2, 1]
	# NES direction to destination by [sign of dy + 1][sign of dx + 1]: vertical move first / horizontal first
	NES_VERTICAL_FIRST = [[0, 0, 0], [1, 0, 3], [2, 2, 2]]
	NES_HORIZONTAL_FIRST = [[1, 0, 3], [1, 0, 3], [1, 2, 3]]

	def chooseNesGoal(self):
		""" NES AI goal by time since stage start (64 NES frames ticks) and enemy spawn interval:
		first random direction, then chase player, then go to castle """
		game = state.game
		interval = game.enemySpawnInterval() // config.nesFrames(1)
		ticks = getattr(game, "level_time", 0) // config.nesFrames(64)

		if interval // 8 >= ticks:
			self.rotate(random.randint(0, 3), False)
			return

		target = state.castle.rect.center
		if interval // 4 >= ticks:
			players = [player for player in state.players if player.state == player.STATE_ALIVE]
			if players:
				# NES: odd enemies chase player 2 if they are alive
				odd = self in state.enemies and state.enemies.index(self) % 2 == 1
				target = players[1 if odd and len(players) > 1 else 0].rect.center
		self.rotate(self.directionTo(target), False)

	def directionTo(self, target):
		""" NES: direction towards point, randomly vertical or horizontal first """
		def sign(v):
			# compare in NES px (2 px)
			v = int(v / 2.0)
			return (v > 0) - (v < 0)
		sx = sign(target[0] - self.rect.centerx) + 1
		sy = sign(target[1] - self.rect.centery) + 1
		table = self.NES_HORIZONTAL_FIRST if random.randint(0, 1) else self.NES_VERTICAL_FIRST
		return self.NES_DIRECTIONS[table[sy][sx]]

	def moveStepNes(self):
		""" NES AI: move 2 px (one NES px). On 8 NES px grid new goal with 1/16 chance.
		Blocked tank: 3/4 waits 2 moves, 1/4 turns (on grid) or turns around """
		if self.state != self.STATE_ALIVE or self.paused or self.paralised:
			return

		if self.nes_wait > 0:
			self.nes_wait -= 1
			return

		aligned = self.rect.left % 16 == 0 and self.rect.top % 16 == 0
		if self.nes_turn:
			self.nes_turn = False
			if random.randint(0, 1):
				self.rotate((self.direction + random.choice((1, -1))) % 4, False)
			else:
				self.chooseNesGoal()
			return

		if aligned and random.randint(0, 15) == 0:
			self.chooseNesGoal()
			return

		if self.stepForward() in ("edge", "wall", "brick", "tank"):
			if random.randint(0, 3):
				self.nes_wait = 2
			elif aligned:
				self.nes_turn = True
			else:
				self.rotate((self.direction + 2) % 4, False)

	def stepForward(self):
		""" Move 2 px (one NES px) in current direction
		@return "moved", "waiting" (just spawned tank waits for older one), or what blocks: "edge", "wall", "brick", "tank"
		"""
		dx, dy = [(0, -2), (2, 0), (0, 2), (-2, 0)][self.direction]
		new_rect = self.rect.move(dx, dy)

		if not pygame.Rect(0, 0, 416, 416).contains(new_rect):
			return "edge"
		if tilesBlock(self.level, new_rect, self.direction, self.canSwim()):
			bricks = [tile for tile in self.level.mapr if tile.type == self.level.TILE_BRICK]
			for cx, cy in frontEdgeCells(new_rect, self.direction):
				if pygame.Rect(cx * CELL, cy * CELL, CELL, CELL).collidelist(bricks) != -1:
					return "brick"
			return "wall"

		if not self.aquired_position:
			# just spawned: drive through tanks until free
			collision = False
			for enemy in state.enemies:
				if enemy != self and enemy.state != enemy.STATE_DEAD and new_rect.colliderect(enemy.rect):
					collision = True
					# overlapping tanks: positioned or older tank drives away first
					if enemy.aquired_position or state.enemies.index(enemy) < state.enemies.index(self):
						return "waiting"
			for player in state.players:
				if player.state == player.STATE_ALIVE and new_rect.colliderect(player.rect):
					collision = True
			if not collision:
				self.aquired_position = True
		else:
			for tank in state.enemies + state.players:
				if tank != self and tank.state == tank.STATE_ALIVE and getattr(tank, "aquired_position", True) and tankBlocks(new_rect, self.direction, tank):
					return "tank"

		if config.ENEMY_PICKUP_BONUSES:
			for bonus in state.bonuses:
				if new_rect.colliderect(bonus.rect):
					self.bonus_aquired = bonus

		self.rect.topleft = new_rect.topleft
		return "moved"

	def wantsFire(self):
		""" Enemy decides to fire: CLASSIC and NES AI at random, SMART AI when target or brick on its way is ahead """
		if config.ENEMY_AI == "SMART":
			if self.smartWantsFire():
				# reaction time: target must be seen for a while
				self.smart_seen += 1
				return self.smart_seen > config.SMART_REACTION_FRAMES
			self.smart_seen = 0
			# hiding tank doesn't give itself away
			if self.smart_order == "hide" and commander.enabled():
				return False
			return random.random() * 100 < config.CHANCE_OF_FIRE / 2
		return random.random() * 100 < config.CHANCE_OF_FIRE

	def lineTo(self, direction, target):
		""" Bullet line from tank in direction
		@return (target rect is on the line, steel between, bricks between)
		"""
		r = self.rect
		if direction == self.DIR_UP:
			ray, dist = pygame.Rect(r.centerx - 4, 0, 8, r.top), lambda t: r.top - t.bottom
		elif direction == self.DIR_DOWN:
			ray, dist = pygame.Rect(r.centerx - 4, r.bottom, 8, max(0, 416 - r.bottom)), lambda t: t.top - r.bottom
		elif direction == self.DIR_LEFT:
			ray, dist = pygame.Rect(0, r.centery - 4, r.left, 8), lambda t: r.left - t.right
		else:
			ray, dist = pygame.Rect(r.right, r.centery - 4, max(0, 416 - r.right), 8), lambda t: t.left - r.right
		if not ray.colliderect(target):
			return False, False, False
		target_dist = dist(target)
		steel = brick = False
		for tile in self.level.mapr:
			if tile.type in (self.level.TILE_BRICK, self.level.TILE_STEEL) and ray.colliderect(tile) and dist(tile) < target_dist:
				if tile.type == self.level.TILE_STEEL:
					steel = True
				else:
					brick = True
		return True, steel, brick

	def smartTarget(self):
		""" SMART AI target rect: armor tank goes to castle, fast tank hunts nearest player, others by turns """
		if self.smart_role == None:
			if self.type == self.TYPE_ARMOR:
				self.smart_role = "castle"
			elif self.type == self.TYPE_FAST:
				self.smart_role = "player"
			else:
				Enemy.smart_roles_given = getattr(Enemy, "smart_roles_given", 0) + 1
				self.smart_role = "castle" if Enemy.smart_roles_given % 2 else "player"
		if self.smart_order != None and commander.enabled():
			# team tactics: player chosen by commander
			target = commander.get().target
			if self.smart_order != "castle" and target != None and target.state == target.STATE_ALIVE:
				return target.rect
			return state.castle.rect
		players = [player for player in state.players if player.state == player.STATE_ALIVE]
		if self.smart_role == "player" and players:
			return min(players, key=lambda p: abs(p.rect.centerx - self.rect.centerx) + abs(p.rect.centery - self.rect.centery)).rect
		return state.castle.rect

	def smartSlotBusy(self):
		""" Tank can't fire now: all its bullets fly or explode """
		busy = [bullet for bullet in state.bullets if bullet.owner_class is self and
			(bullet.state == bullet.STATE_ACTIVE or (bullet.state == bullet.STATE_EXPLODING and bullet.slot_busy))]
		return len(busy) >= self.max_active_bullets

	def smartAim(self):
		""" Direction to shoot: player in clear line (at chosen place also behind bricks) or castle behind bricks,
		None if no target in line. Hiding tank shoots only a player in clear line (doesn't shoot walls open) """
		hiding = self.smart_order == "hide"
		for direction in range(4):
			for player in state.players:
				if player.state == player.STATE_ALIVE:
					in_line, steel, brick = self.lineTo(direction, player.rect)
					if in_line and not steel and (not brick or (self.smart_at_goal and not hiding)):
						return direction
			if state.castle.active and self.smart_role == "castle":
				in_line, steel, brick = self.lineTo(direction, state.castle.rect)
				if in_line and not steel:
					return direction
		return None

	def smartWantsFire(self):
		""" Target ahead: player in clear line (from chosen place also behind bricks), castle (bricks can be shot through)
		or brick on the way. Hiding tank: only player in clear line or brick on its way """
		hiding = self.smart_order == "hide"
		for player in state.players:
			if player.state == player.STATE_ALIVE:
				in_line, steel, brick = self.lineTo(self.direction, player.rect)
				if in_line and not steel and (not brick or (self.smart_at_goal and not hiding)):
					return True
		if state.castle.active and not hiding:
			in_line, steel, brick = self.lineTo(self.direction, state.castle.rect)
			if in_line and not steel:
				return True
		return self.smart_blocked_by == "brick"

	def smartCommander(self):
		""" Team commander (up to date, this tank has an order), None if SMART AI doesn't use team tactics """
		if not commander.enabled():
			return None
		cmd = commander.get()
		if self.smart_order == None and self.state == self.STATE_ALIVE:
			cmd.update()
		return cmd

	def smartLead(self, cmd, player, cells):
		""" Rect of the place player drives to: up to n cells ahead while the way is free, player's rect if he stands """
		moving = cmd.movingDirection(player)
		if moving == None or cells <= 0:
			return player.rect
		places = cmd.placeCosts(player.canSwim())
		x, y = commander.place(player.rect)
		dx, dy = commander.STEPS[moving]
		moved = False
		for i in range(cells):
			if not (0 <= x + dx <= 24 and 0 <= y + dy <= 24) or places[y + dy][x + dx] != 1:
				break
			x, y, moved = x + dx, y + dy, True
		return pygame.Rect(x * CELL, y * CELL, 32, 32) if moved else player.rect

	def smartPath(self, target = None, order = None):
		""" Cheapest path of 16 px steps to the best place for tank's order (Dijkstra on 25x25 tank places).
		Place to shoot target from: way there (bricks on the way cost more, steel and water can't be passed), bricks
		between place and target, player looking at the place (tank prefers coming from a side), other enemies going
		to nearby places; team tactics: attack side given by commander, hunting tank aims ahead of the player and
		likes places behind him. Hiding tank: best hiding spot (commander.hide). Danger of places on the way costs
		more for hiding tanks, less for attacking ones.
		Chosen place is kept while it is not much worse than the best one (no running back and forth).
		Player who can't be shot from anywhere: castle is attacked instead.
		@return list of cells (tank's top left 16 px cell) without current one, None if there is no way
		"""
		cmd = self.smartCommander()
		target_player = None
		if cmd != None and target == None:
			if order == None:
				order = self.smart_order
			if order in ("hide", "attack", "hunt") and cmd.target == None:
				order = "castle"
		if cmd != None and target == None and order in ("hide", "attack", "hunt"):
			target_player = cmd.target
			target = self.smartLead(cmd, target_player, config.SMART_HUNT_LEAD if order == "hunt" else config.SMART_ATTACK_LEAD)
			attack_player = True
		else:
			attack_player = target == None and self.smart_role == "player"
		if target == None:
			target = self.smartTarget()
		level = self.level
		can_swim = self.canSwim()
		if cmd != None:
			# costs cached by commander, danger on the way
			places = cmd.placeCosts(can_swim)
			place_danger = cmd.place_danger
			weight = {"hide": config.SMART_DANGER_WEIGHT_HIDE, "hunt": config.SMART_DANGER_WEIGHT_HUNT,
				"castle": config.SMART_DANGER_WEIGHT_CASTLE}.get(order, config.SMART_DANGER_WEIGHT_ATTACK)

			def placeCost(x, y):
				cost = places[y][x]
				return None if cost == None else cost + weight * place_danger[y][x]
			steel, bricks = cmd.steel, cmd.bricks
		else:
			# cost of 16 px map cell, None - impassable
			costs = [[1] * 26 for i in range(26)]
			for tile in level.mapr:
				if tile.type == level.TILE_BRICK:
					cost = config.SMART_BRICK_COST
				elif tile.type == level.TILE_STEEL:
					cost = None
				elif tile.type == level.TILE_WATER and not can_swim:
					cost = None
				else:
					continue
				for cy in range(tile.top // CELL, (tile.bottom - 1) // CELL + 1):
					for cx in range(tile.left // CELL, (tile.right - 1) // CELL + 1):
						if 0 <= cx < 26 and 0 <= cy < 26 and costs[cy][cx] != None:
							costs[cy][cx] = None if cost == None else max(costs[cy][cx], cost)
			for castle in state.game.castles():
				for cy in range(castle.rect.top // CELL, (castle.rect.bottom - 1) // CELL + 1):
					for cx in range(castle.rect.left // CELL, (castle.rect.right - 1) // CELL + 1):
						costs[cy][cx] = None

			def placeCost(x, y):
				cells = [costs[y][x], costs[y][x + 1], costs[y + 1][x], costs[y + 1][x + 1]]
				return None if None in cells else max(cells)
			steel = set([(tile.left // CELL, tile.top // CELL) for tile in level.mapr if tile.type == level.TILE_STEEL])
			bricks = set([(tile.left // CELL, tile.top // CELL) for tile in level.mapr if tile.type == level.TILE_BRICK])

		# ways to all places
		start = (self.rect.left // CELL, self.rect.top // CELL)
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

		target_x0, target_x1 = target.left // CELL, (target.right - 1) // CELL
		target_y0, target_y1 = target.top // CELL, (target.bottom - 1) // CELL
		if target_player == None:
			for player in state.players:
				if player.state == player.STATE_ALIVE and player.rect == target:
					target_player = player
		other_goals = [enemy.smart_goal for enemy in state.enemies if enemy is not self and enemy.state == enemy.STATE_ALIVE and getattr(enemy, "smart_goal", None)]

		def shotCost(x, y):
			""" Extra cost of shooting target from place, None - target can't be shot from there """
			cx, cy = x * CELL + CELL, y * CELL + CELL
			if abs(cx - target.centerx) < CELL // 2:
				if y + 1 < target_y0:
					cells = [(col, row) for col in (x, x + 1) for row in range(y + 2, target_y0)]
					looking = Tank.DIR_UP
				elif y > target_y1:
					cells = [(col, row) for col in (x, x + 1) for row in range(target_y1 + 1, y)]
					looking = Tank.DIR_DOWN
				else:
					return None
				distance = len(cells) // 2
			elif abs(cy - target.centery) < CELL // 2:
				if x + 1 < target_x0:
					cells = [(col, row) for row in (y, y + 1) for col in range(x + 2, target_x0)]
					looking = Tank.DIR_LEFT
				elif x > target_x1:
					cells = [(col, row) for row in (y, y + 1) for col in range(target_x1 + 1, x)]
					looking = Tank.DIR_RIGHT
				else:
					return None
				distance = len(cells) // 2
			else:
				return None
			if any([cell in steel for cell in cells]):
				return None
			cost = len([cell for cell in cells if cell in bricks]) * config.SMART_BRICK_SHOT_COST + distance * 0.2
			# player looks this way: he'd shoot first (tank taking the player's front in team attack doesn't mind)
			if target_player != None and target_player.direction == looking and not self.smart_front:
				cost += config.SMART_DANGER_COST
			# team attack from given side, hunter likes the player's back
			if order == "attack" and self.smart_side != None and looking != self.smart_side:
				cost += config.SMART_SIDE_COST
			if order == "hunt" and target_player != None and looking == (target_player.direction + 2) % 4:
				cost -= config.SMART_BEHIND_BONUS
			for goal in other_goals:
				if abs(goal[0] - x) + abs(goal[1] - y) <= 2:
					cost += config.SMART_CROWD_COST
			return cost

		hiding = cmd != None and order == "hide" and cmd.hide != None

		def hideCost(x, y):
			""" Cost of hiding spot, spots near other enemies' places cost more """
			cost = cmd.hide[y][x]
			if cost == None:
				return None
			for goal in other_goals:
				if abs(goal[0] - x) + abs(goal[1] - y) <= config.SMART_HIDE_SPREAD:
					cost += config.SMART_CROWD_COST
			return cost

		extraCost = hideCost if hiding else shotCost
		way = config.SMART_HIDE_WAY_WEIGHT if hiding else 1
		candidates = []
		for place in best:
			extra = extraCost(*place)
			if extra != None:
				candidates.append((best[place] * way + extra, place))
		if not candidates:
			if hiding:
				return self.smartPath(None, "attack")
			if attack_player and state.castle.active:
				return self.smartPath(state.castle.rect, "castle")
			self.smart_goal = None
			return None
		total, goal = min(candidates)

		# keep chosen place if it's still good enough
		old = self.smart_goal
		if old in best and old != goal:
			extra = extraCost(*old)
			if extra != None and best[old] * way + extra <= total + config.SMART_GOAL_STICKINESS:
				goal = old
		self.smart_goal = goal

		path = []
		while goal != start:
			path.append(goal)
			goal = previous[goal]
		path.reverse()
		return path

	def canMoveFree(self, direction, px):
		""" Tank could move px in direction (nothing blocks it on the way) """
		rect = self.rect.copy()
		dx, dy = [(0, -2), (2, 0), (0, 2), (-2, 0)][direction]
		free = True
		for step in range(0, px, 2):
			if self.stepBlock(direction) != None:
				free = False
				break
			self.rect.move_ip(dx, dy)
		self.rect = rect
		return free

	def smartDodge(self):
		""" Player's bullet flies at this tank: sharp turn aside if there is time
		(after reaction time and with SMART_DODGE_CHANCE for every bullet). Bullet behind a wall is ignored;
		with team tactics side out of players' lines of fire is preferred
		@return True if tank started to dodge
		"""
		cmd = commander.get() if commander.enabled() else None
		now = getattr(state.game, "level_time", 0)
		active = [bullet for bullet in state.bullets if bullet.state == bullet.STATE_ACTIVE and bullet.owner == bullet.OWNER_PLAYER]
		self.smart_bullets = dict([(id(bullet), self.smart_bullets.get(id(bullet), [now, random.random() * 100 < config.SMART_DODGE_CHANCE])) for bullet in active])
		r = self.rect
		for bullet in active:
			seen, will_dodge = self.smart_bullets[id(bullet)]
			if not will_dodge or now - seen < config.nesFrames(config.SMART_DODGE_REACTION_FRAMES):
				continue
			b = bullet.rect
			if bullet.direction in (bullet.DIR_UP, bullet.DIR_DOWN):
				if b.right <= r.left or b.left >= r.right:
					continue
				distance = b.top - r.bottom if bullet.direction == bullet.DIR_UP else r.top - b.bottom
				options = [(self.DIR_LEFT, r.right - b.left), (self.DIR_RIGHT, b.right - r.left)]
			else:
				if b.bottom <= r.top or b.top >= r.bottom:
					continue
				distance = b.left - r.right if bullet.direction == bullet.DIR_LEFT else r.left - b.right
				options = [(self.DIR_UP, r.bottom - b.top), (self.DIR_DOWN, b.bottom - r.top)]
			if distance < 0:
				continue
			# wall between stops the bullet
			if distance > 0 and not bullet.over_walls:
				if bullet.direction == bullet.DIR_UP:
					between = pygame.Rect(b.left, r.bottom, b.width, distance)
				elif bullet.direction == bullet.DIR_DOWN:
					between = pygame.Rect(b.left, b.bottom, b.width, distance)
				elif bullet.direction == bullet.DIR_LEFT:
					between = pygame.Rect(r.right, b.top, distance, b.height)
				else:
					between = pygame.Rect(b.right, b.top, distance, b.height)
				if between.collidelist(self.level.land_obstacle_rects) != -1:
					continue
			frames_left = distance / max(bullet.speed, 0.1)

			def dangerAfter(option):
				if cmd == None:
					return False
				dx, dy = [(0, -1), (1, 0), (0, 1), (-1, 0)][option[0]]
				return cmd.rectDanger(r.move(dx * (option[1] + CELL // 2), dy * (option[1] + CELL // 2)), False) > 0
			options.sort(key=lambda option: (dangerAfter(option), option[1]))
			for direction, px in options:
				px += px % 2
				if px / max(self.speed, 0.1) < frames_left and self.canMoveFree(direction, px):
					self.rotate(direction, False)
					self.smart_dodge_px = px
					return True
		return False

	def smartJuke(self, aim):
		""" Player aims at this tank and it can't shoot back now: step out of the line of fire (SMART_JUKE_CHANCE) """
		if random.random() * 100 >= config.SMART_JUKE_CHANCE or not self.smartSlotBusy():
			return False
		for player in state.players:
			if player.state != player.STATE_ALIVE or player.direction != (aim + 2) % 4:
				continue
			in_line, steel, brick = self.lineTo(aim, player.rect)
			if in_line and not steel and not brick:
				sides = [(aim + 1) % 4, (aim + 3) % 4]
				random.shuffle(sides)
				for side in sides:
					if self.canMoveFree(side, CELL):
						self.rotate(side, False)
						self.smart_wander = 1
						return True
		return False

	def smartFeint(self, direction):
		""" Sometimes (SMART_FEINT_CHANCE) sharp turn aside from the way for one cell, so tank is hard to predict """
		if random.random() * 100 >= config.SMART_FEINT_CHANCE:
			return False
		sides = [(direction + 1) % 4, (direction + 3) % 4]
		random.shuffle(sides)
		for side in sides:
			if self.canMoveFree(side, CELL):
				self.rotate(side, False)
				self.smart_wander = 1
				return True
		return False

	def moveStepSmart(self):
		""" SMART AI: move 2 px. Dodge player's bullets; on 16 px grid: shoot at target in line of fire (step out of
		player's line of fire when own bullet isn't ready), stay at chosen place shooting through bricks,
		otherwise follow cheapest path with feints; shoot bricks on the way, wait for tanks, drive aside when stuck """
		if self.state != self.STATE_ALIVE or self.paused or self.paralised:
			return

		if self.smart_dodge_px <= 0 and self.smartDodge():
			self.nes_wait = 0
			self.smart_waiting = False
		if self.smart_dodge_px > 0:
			result = self.stepForward()
			self.smart_dodge_px = self.smart_dodge_px - 2 if result == "moved" else 0
			if self.smart_dodge_px <= 0:
				self.smart_timer = 0
			return

		if self.nes_wait > 0:
			self.nes_wait -= 1
			return

		if self.rect.left % CELL == 0 and self.rect.top % CELL == 0:
			place = (self.rect.left // CELL, self.rect.top // CELL)
			cmd = self.smartCommander()
			hiding = cmd != None and self.smart_order == "hide"
			self.smart_at_goal = place == self.smart_goal
			self.smart_waiting = hiding and self.smart_at_goal
			aim = self.smartAim()
			# hiding tank on its way doesn't stop in the line of fire of a player looking at it
			if aim != None and hiding and not self.smart_at_goal and self.smartSeenBy(aim):
				aim = None
			if self.smart_wander > 0:
				self.smart_wander -= 1
				self.smart_waiting = False
			elif aim != None:
				self.rotate(aim, False)
				self.smart_blocked_by = None
				if self.smartJuke(aim):
					self.smart_waiting = False
				elif self.smart_at_goal or hiding:
					# stay at chosen place and shoot (hiding tank: ambush shot)
					self.nes_wait = 2
					return
			elif self.smart_waiting:
				# hiding spot: wait watching the lane where the player may appear, look for a better spot now and then
				# (at once when the spot becomes dangerous)
				self.smart_timer -= 1
				dangerous = cmd.place_danger[place[1]][place[0]] > 0 and self.smart_timer % 3 == 0
				if self.smart_timer <= 0 or dangerous:
					self.smart_timer = config.SMART_WAIT_REPLAN
					self.smart_path = self.smartPath()
				if not self.smart_path or self.smart_goal == place:
					watch = cmd.watchDirection(place)
					if watch != None:
						self.rotate(watch, False)
					# don't shoot own cover
					self.smart_blocked_by = None
					self.nes_wait = 2
					return
				self.smart_waiting = False
				self.smartFollow(place)
			else:
				self.smartFollow(place)
		elif self.smart_wander == 0 and not self.canStep(self.direction):
			# between cells and blocked: turn to a target in line of fire (e.g. player right next to it) and shoot
			aim = self.smartAim()
			if aim != None:
				self.rotate(aim, False)

		result = self.stepForward()
		self.smart_blocked_by = result if result in ("brick", "tank") else None
		if result == "moved":
			self.smart_blocked = 0
		elif result == "brick":
			# shoot through
			self.nes_wait = 2
		elif result in ("tank", "edge", "wall"):
			self.smart_blocked += 1
			self.nes_wait = 2
			self.smart_timer = 0
			if self.smart_blocked > config.SMART_STUCK_MOVES or result != "tank":
				self.smart_blocked = 0
				self.smartSidestep()

	def smartSeenBy(self, direction):
		""" Player in clear line in direction looks at this tank """
		for player in state.players:
			if player.state == player.STATE_ALIVE and player.direction == (direction + 2) % 4:
				in_line, steel, brick = self.lineTo(direction, player.rect)
				if in_line and not steel and not brick:
					return True
		return False

	def smartFollow(self, place):
		""" On 16 px grid: turn along the path to chosen place (find it again every SMART_PATH_CELLS cells), with feints """
		self.smart_timer -= 1
		if self.smart_path and self.smart_path[0] == place:
			self.smart_path.pop(0)
		if self.smart_timer <= 0 or not self.smart_path:
			self.smart_path = self.smartPath()
			self.smart_timer = config.SMART_PATH_CELLS
		steps = [(0, -1), (1, 0), (0, 1), (-1, 0)]
		if self.smart_path:
			x, y = self.smart_path[0]
			if (x - place[0], y - place[1]) not in steps:
				# path from other place: find again
				self.smart_path = self.smartPath()
			if self.smart_path:
				x, y = self.smart_path[0]
				if (x - place[0], y - place[1]) in steps:
					direction = steps.index((x - place[0], y - place[1]))
					if len(self.smart_path) < 3 or not self.smartFeint(direction):
						self.rotate(direction, False)
		elif self.smart_path == None:
			# no way: drive somewhere else for a while
			self.rotate(random.randint(0, 3), False)
			self.smart_wander = 4

	def stepBlock(self, direction):
		""" What blocks 2 px move in direction: None (free), "edge", "wall", "brick" or "tank" """
		dx, dy = [(0, -2), (2, 0), (0, 2), (-2, 0)][direction]
		new_rect = self.rect.move(dx, dy)
		if not pygame.Rect(0, 0, 416, 416).contains(new_rect):
			return "edge"
		if tilesBlock(self.level, new_rect, direction, self.canSwim()):
			bricks = [tile for tile in self.level.mapr if tile.type == self.level.TILE_BRICK]
			for cx, cy in frontEdgeCells(new_rect, direction):
				if pygame.Rect(cx * CELL, cy * CELL, CELL, CELL).collidelist(bricks) != -1:
					return "brick"
			return "wall"
		for tank in state.enemies + state.players:
			if tank != self and tank.state == tank.STATE_ALIVE and getattr(tank, "aquired_position", True) and tankBlocks(new_rect, direction, tank):
				return "tank"
		return None

	def canStep(self, direction):
		""" Tank could move 2 px in direction: no screen edge, wall or tank in front """
		return self.stepBlock(direction) == None

	def smartSidestep(self):
		""" Blocked tank drives aside for a while: to a free side (onto 16 px grid first if tank is between cells),
		else back; boxed in tank shoots through bricks """
		horizontal = [self.DIR_RIGHT, self.DIR_LEFT]
		vertical = [self.DIR_UP, self.DIR_DOWN]
		random.shuffle(horizontal)
		random.shuffle(vertical)
		# between cells: towards nearest cell first
		if self.rect.left % CELL:
			horizontal.sort(key=lambda d: 0 if (d == self.DIR_RIGHT) == (self.rect.left % CELL >= CELL // 2) else 1)
		if self.rect.top % CELL:
			vertical.sort(key=lambda d: 0 if (d == self.DIR_DOWN) == (self.rect.top % CELL >= CELL // 2) else 1)
		back = (self.direction + 2) % 4
		choices = (horizontal if self.direction in vertical else vertical) + [back]
		if self.rect.left % CELL:
			choices = horizontal + [d for d in choices if d not in horizontal]
		elif self.rect.top % CELL:
			choices = vertical + [d for d in choices if d not in vertical]
		blocks = dict([(direction, self.stepBlock(direction)) for direction in set(choices + [self.direction])])
		free = [direction for direction in choices if blocks[direction] == None]
		bricks = [direction for direction in [self.direction] + choices if blocks[direction] == "brick"]
		if free:
			self.rotate(free[0], False)
			self.smart_wander = 2
		elif bricks:
			# shoot through
			self.rotate(bricks[0], False)
			self.smart_blocked_by = "brick"
		else:
			self.rotate(random.choice(choices), False)
			self.smart_wander = 2

	def update(self, time_passed):
		Tank.update(self, time_passed)
		if self.reveal_frames > 0:
			self.reveal_frames -= 1
		if self.state == self.STATE_ALIVE and not self.paused:
			self.move()

	def generatePath(self, direction = None, fix_direction = False):
		""" If direction is specified, try continue that way, otherwise choose at random
		"""

		all_directions = [self.DIR_UP, self.DIR_RIGHT, self.DIR_DOWN, self.DIR_LEFT]

		if direction == None:
			if self.direction in [self.DIR_UP, self.DIR_RIGHT]:
				opposite_direction = self.direction + 2
			else:
				opposite_direction = self.direction - 2
			directions = all_directions
			random.shuffle(directions)
			directions.remove(opposite_direction)
			directions.append(opposite_direction)
		else:
			if direction in [self.DIR_UP, self.DIR_RIGHT]:
				opposite_direction = direction + 2
			else:
				opposite_direction = direction - 2

			if direction in [self.DIR_UP, self.DIR_RIGHT]:
				opposite_direction = direction + 2
			else:
				opposite_direction = direction - 2
			directions = all_directions
			random.shuffle(directions)
			directions.remove(opposite_direction)
			directions.remove(direction)
			directions.insert(0, direction)
			directions.append(opposite_direction)

		# on top of a player (e.g. player respawned on enemy): drive away from the player first
		for player in state.players:
			if player.state == player.STATE_ALIVE and self.rect.colliderect(player.rect):
				dx = self.rect.centerx - player.rect.centerx
				dy = self.rect.centery - player.rect.centery
				horizontal = self.DIR_RIGHT if dx > 0 else self.DIR_LEFT
				vertical = self.DIR_DOWN if dy > 0 else self.DIR_UP
				away = [horizontal, vertical] if abs(dx) >= abs(dy) else [vertical, horizontal]
				directions = away + [d for d in directions if d not in away]
				# don't keep pushing into a wall
				self.persistance = 0
				break

		# sometimes prefer directions towards player's castle
		if random.randint(1, 100) <= config.ENEMY_AI_BASE_CHANCE:
			towards = []
			if state.castle.rect.centery > self.rect.centery:
				towards.append(self.DIR_DOWN)
			if state.castle.rect.centerx > self.rect.centerx + 16:
				towards.append(self.DIR_RIGHT)
			elif state.castle.rect.centerx < self.rect.centerx - 16:
				towards.append(self.DIR_LEFT)
			random.shuffle(towards)
			directions = towards + [d for d in directions if d not in towards]

		# at first, work with general units (steps) not px
		x = int(round(self.rect.left / 16))
		y = int(round(self.rect.top / 16))

		new_direction = None

		for direction in directions:
			if direction == self.DIR_UP and y > 0:
				new_pos_rect = self.rect.move(0, -8)
				if new_pos_rect.collidelist(self.level.obstacleRectsFor(self.canSwim())) == -1:
					new_direction = direction
					break
			elif direction == self.DIR_RIGHT and x < 24:
				new_pos_rect = self.rect.move(8, 0)
				if new_pos_rect.collidelist(self.level.obstacleRectsFor(self.canSwim())) == -1:
					new_direction = direction
					break
			elif direction == self.DIR_DOWN and y < 24:
				new_pos_rect = self.rect.move(0, 8)
				if new_pos_rect.collidelist(self.level.obstacleRectsFor(self.canSwim())) == -1:
					new_direction = direction
					break
			elif direction == self.DIR_LEFT and x > 0:
				new_pos_rect = self.rect.move(-8, 0)
				if new_pos_rect.collidelist(self.level.obstacleRectsFor(self.canSwim())) == -1:
					new_direction = direction
					break

		# if we can't go anywhere else, do a random turn
		if new_direction == None:
			new_direction = random.choice([self.DIR_UP, self.DIR_DOWN, self.DIR_RIGHT, self.DIR_LEFT])

		# fix tanks position
		if fix_direction and new_direction == self.direction:
			fix_direction = False

		# keep pushing into obstacle for a while (shoot it through) before turning
		if self.persistance > 1:
			new_direction = self.direction

		self.rotate(new_direction, fix_direction)

		positions = []

		x = self.rect.left
		y = self.rect.top

		if new_direction in (self.DIR_RIGHT, self.DIR_LEFT):
			axis_fix = self.nearest(y, 16) - y
		else:
			axis_fix = self.nearest(x, 16) - x
		axis_fix = 0

		pixels = self.nearest(random.randint(1, 4) * 32, 32) + axis_fix # + 3

		# always end exactly on the target so the tank stays aligned with the grid,
		# even if speed doesn't divide the distance
		steps = list(range(1, pixels + 1))

		if new_direction == self.DIR_UP:
			for px in steps:
				positions.append([x, y-px])
		elif new_direction == self.DIR_RIGHT:
			for px in steps:
				positions.append([x+px, y])
		elif new_direction == self.DIR_DOWN:
			for px in steps:
				positions.append([x, y+px])
		elif new_direction == self.DIR_LEFT:
			for px in steps:
				positions.append([x-px, y])

		return positions


class Player(Tank):

	def __init__(self, level, type, position = None, direction = None, filename = None, player_nr=1):

		Tank.__init__(self, level, type, position = None, direction = None, filename = None)


		if filename == None:
			filename = (0, 0, 16*2, 16*2)

		self.start_position = position
		self.start_direction = direction

		self.speed = config.PLAYER_DEFAULT_SPEED
		self.lives = config.PLAYER_START_LIFE
		self.superpowers = config.PLAYER_START_SUPERPOWER
		self.score = config.PLAYER_START_SCORE

		# score for next extra life
		self.next_extra_life = config.EXTRA_LIFE_SCORE

		# versus: how many times this player destroyed the other one
		self.versus_kills = 0

		# computer partner driving this tank (bot.Bot), None - human player
		self.bot = None

		# store how many bonuses in this stage this player has collected
		self.trophies = config.emptyTrophies()

		if player_nr == 1:
			player_sprite_nr = 5
		else:
			player_sprite_nr = 6

		self.images2 = [
			state.sprites2.subsurface(player_sprite_nr*config.S_SIZE*config.T_SIZE, 0, 32, 32),
			state.sprites2.subsurface(player_sprite_nr*config.S_SIZE*config.T_SIZE, 2*config.T_SIZE, 32, 32),
			state.sprites2.subsurface(player_sprite_nr*config.S_SIZE*config.T_SIZE, 4*config.T_SIZE, 32, 32),
			state.sprites2.subsurface(player_sprite_nr*config.S_SIZE*config.T_SIZE, 6*config.T_SIZE, 32, 32)
		]

		self.protected = False
		self.protected_image = state.sprites2.subsurface((10+player_sprite_nr)*32+4, 9*32, 16*2, 16*2)

		# until player moves out of other tanks after respawn, they don't block him
		self.aquired_position = False

		self.image = state.sprites2.subsurface(filename)
		self.image_up = self.image
		self.image_left = pygame.transform.rotate(self.image, 90)
		self.image_down = pygame.transform.rotate(self.image, 180)
		self.image_right = pygame.transform.rotate(self.image, 270)

		if direction == None:
			self.rotate(self.DIR_UP, False)
		else:
			self.rotate(direction, False)

	def updateSprites(self):
		sprite_id = self.superpowers
		if sprite_id > len(self.images2) - 1:
			sprite_id = len(self.images2) - 1
		self.image = self.images2[sprite_id]
		self.image_up = self.image
		self.image_left = pygame.transform.rotate(self.image, 90)
		self.image_down = pygame.transform.rotate(self.image, 180)
		self.image_right = pygame.transform.rotate(self.image, 270)
		self.rotate(self.direction)

	def move(self, direction, px = None):
		""" Move player if possible
		px None: move with player's speed - speed can be fractional, whole px are moved,
		the rest is kept for next frame
		@return True if tank moved
		"""
		if px == None:
			self.move_credit += self.speed
			steps = int(self.move_credit + 1e-9)
			self.move_credit -= steps
			# turn even if there is no whole px to move
			self.move(direction, 0)
			moved = False
			for step in range(steps):
				if not self.move(direction, 1):
					break
				moved = True
			return moved



		if self.state == self.STATE_EXPLODING:
			if not self.explosion.active:
				self.state = self.STATE_DEAD
				del self.explosion

		if self.state != self.STATE_ALIVE:
			return

		# rotate player
		if self.direction != direction:
			self.rotate(direction)

		if self.paralised or px == 0:
			return

		# move player
		if direction == self.DIR_UP:
			new_position = [self.rect.left, self.rect.top - px]
			if new_position[1] < 0:
				return
		elif direction == self.DIR_RIGHT:
			new_position = [self.rect.left + px, self.rect.top]
			if new_position[0] > (416 - 32):
				return
		elif direction == self.DIR_DOWN:
			new_position = [self.rect.left, self.rect.top + px]
			if new_position[1] > (416 - 32):
				return
		elif direction == self.DIR_LEFT:
			new_position = [self.rect.left - px, self.rect.top]
			if new_position[0] < 0:
				return

		player_rect = pygame.Rect(new_position, [32, 32])

		# collisions with tiles
		if tilesBlock(self.level, player_rect, direction, self.canSwim()):
			return

		# collisions with other players
		for player in state.players:
			if player != self and player.state == player.STATE_ALIVE and player_rect.colliderect(player.rect) == True:
				if player.aquired_position and tankBlocks(player_rect, direction, player):
					return

		# collisions with enemies (exploding and spawning tanks don't block, like on NES)
		for enemy in state.enemies:
			if enemy.state == enemy.STATE_ALIVE and player_rect.colliderect(enemy.rect) == True:
				if enemy.aquired_position and self.aquired_position and tankBlocks(player_rect, direction, enemy):
					return

		# collisions with bonuses
		for bonus in state.bonuses:
			if player_rect.colliderect(bonus.rect) == True:
				self.bonus = bonus

		#if no collision, move player
		self.rect.topleft = (new_position[0], new_position[1])
		self.aquired_position = True
		if config.DEBUG_COORDINATES:
			print("Move center: " + str(self.rect.center))

		return True


	def reset(self):
		""" reset player """
		self.rotate(self.start_direction, False)
		self.rect.topleft = self.start_position
		self.max_active_bullets = config.PLAYER_START_MAX_ACTIVE_BULLETS
		self.superpowers = 0
		self.updateSuperpowers()
		self.health = config.PLAYER_START_HEALTH
		self.stunned = False
		self.paralised = self.frozen
		self.paused = False
		self.pressed = [False] * 4
		self.fire_pressed = False
		self.aquired_position = False
		self.slide = 0
		self.ship = False
		state.gtimer.destroy(self.ship_timer)
		self.ship_timer = None
		self.visible = True
		self.visibility_timer = None
		self.startSpawning(config.PLAYER_SPAWN_ANIMATION_TIME)
