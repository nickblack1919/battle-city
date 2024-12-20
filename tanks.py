#!/usr/bin/python
# coding=utf-8

import os, pygame, time, random, uuid, sys, argparse
from pygame.locals import *

# MODE
CLASSIC_MODE = False
EXTREME_MODE = False
GOOD_MODE = True
DEBUG_MODE = False

# CHEATS
START_LEVEL = 27
FORTRESS_FOREVER = 0
PLAYER_INFINITE_ARMOR = 0
PLAYER_INFINITE_LIVES = False
INFINITE_HEALTH_FOR_ALL = False	# if True overrides PLAYER_INFINITE_ARMOR
INFINITE_BONUSES = False

# GAME MECHANICS
BONUS_FREQ = 4 # every n-th enemy tank will carry a bonus
ALLOW_MULTI_BONUS = True
ENEMY_PICKUP_BONUSES = True
FRIENDLY_FIRE = False
MAX_ACTIVE_ENEMIES = 4
MAX_ACTIVE_ENEMIES_2_PLAYERS = 10
MAX_ACTIVE_ENEMIES_3_PLAYERS = 12
ENEMY_SPAWN_TIMEOUT = 1000
LEVEL_FINISH_TIMEOUT = 4000
BONUS_TIMER_FREEZE_TIMEOUT = 15000
BONUS_FORTRESS_WALLS_TIMEOUT = 15000
BONUS_PLAYER_SHIELD_TIMEOUT = 20000
BONUS_PLAYER_HIDDEN_TIMEOUT = 10000
BONUS_SPAWN_TIMEOUT = 20000
CHANCE_OF_FIRE = 50
ENEMY_FIRE_TIMER = 500
HEAD_SHIELD_WHEN_PROTECTED = True
ENABLE_PLAYER_PROTECTION = True

# GAME SPEED
GAME_FRAME_TIMING = 50
DEFAULT_BULLET_SPEED = 4
PLAYER_DEFAULT_SPEED = 2
DEFAULT_ENEMY_SPEED = 1
DEFAULT_ENEMY_SPEED_FAST = 1

# ENEMY
DEFAULT_ENEMY_ARMOR_HEALTH = 600

# PLAYER
PLAYER_START_SUPERPOWER = 1
PLAYER_START_LIFE = 4
PLAYER_START_HEALTH = 100
PLAYER_START_SCORE = 0
PLAYER_START_MAX_ACTIVE_BULLETS = 1
PLAYER_START_SHIELD_TIMEOUT = 4000

# DEBUG
DEBUG_UNFREEZE_PLAYERS_ON_PAUSE = DEBUG_MODE
DEBUG_SPRITES = DEBUG_MODE
DEBUG_DRAW_MESH = DEBUG_MODE
DEBUG_COORDINATES = DEBUG_MODE
DISABLE_LABELS = not DEBUG_MODE	# to avoid bug with delayed font loading

# CONSTANTS
S_SIZE = 4
T_SIZE = 32

if CLASSIC_MODE:
	ALLOW_MULTI_BONUS = False
	ENEMY_PICKUP_BONUSES = False
	BONUS_FREQ = 5
	PLAYER_START_SUPERPOWER = 0
	DEFAULT_ENEMY_ARMOR_HEALTH = 400
	DEFAULT_ENEMY_SPEED_FAST = 1
	MAX_ACTIVE_ENEMIES_2_PLAYERS = 8
	ENEMY_SPAWN_TIMEOUT = 2000
	ENABLE_PLAYER_PROTECTION = False

if EXTREME_MODE:
	ALLOW_MULTI_BONUS = True
	ENEMY_PICKUP_BONUSES = True
	BONUS_FREQ = 4
	PLAYER_START_SUPERPOWER = 1
	DEFAULT_ENEMY_ARMOR_HEALTH = 600
	DEFAULT_ENEMY_SPEED_FAST = 2
	MAX_ACTIVE_ENEMIES_2_PLAYERS = 14
	ENEMY_SPAWN_TIMEOUT = 1000
	ENABLE_PLAYER_PROTECTION = True

if GOOD_MODE:
	ALLOW_MULTI_BONUS = True
	ENEMY_PICKUP_BONUSES = True
	BONUS_FREQ = 4
	PLAYER_START_SUPERPOWER = 1
	DEFAULT_ENEMY_ARMOR_HEALTH = 600
	DEFAULT_ENEMY_SPEED_FAST = 2
	MAX_ACTIVE_ENEMIES = 5
	MAX_ACTIVE_ENEMIES_2_PLAYERS = 8
	ENEMY_SPAWN_TIMEOUT = 1000
	ENABLE_PLAYER_PROTECTION = True

# Construct the argument parser
ap = argparse.ArgumentParser()

# Add the arguments to the parser
ap.add_argument("-l", "--level", default=START_LEVEL, required=False, help="start level")
args = vars(ap.parse_args())

START_LEVEL = int(args['level'])

class myRect(pygame.Rect):
	""" Add type property """
	def __init__(self, left, top, width, height, type):
		pygame.Rect.__init__(self, left, top, width, height)
		self.type = type

class Timer(object):
	def __init__(self):
		self.timers = []

	def add(self, interval, f, repeat = -1):
		options = {
			"interval"	: interval,
			"callback"	: f,
			"repeat"		: repeat,
			"times"			: 0,
			"time"			: 0,
			"uuid"			: uuid.uuid4()
		}
		self.timers.append(options)

		return options["uuid"]

	def destroy(self, uuid_nr):
		for timer in self.timers:
			if timer["uuid"] == uuid_nr:
				self.timers.remove(timer)
				return

	def update(self, time_passed):
		for timer in self.timers:
			timer["time"] += time_passed
			if timer["time"] > timer["interval"]:
				timer["time"] -= timer["interval"]
				timer["times"] += 1
				if timer["repeat"] > -1 and timer["times"] == timer["repeat"]:
					self.timers.remove(timer)
				try:
					timer["callback"]()
				except:
					try:
						self.timers.remove(timer)
					except:
						pass

class Castle():
	""" Player's castle/fortress """

	(STATE_STANDING, STATE_DESTROYED, STATE_EXPLODING) = range(3)

	def __init__(self):

		global sprites

		self.protected = False

		# images
		self.img_undamaged = sprites.subsurface(0, 15*2, 16*2, 16*2)
		self.img_destroyed = sprites.subsurface(16*2, 15*2, 16*2, 16*2)
		self.img_protected = sprites2.subsurface((10+5)*32+4, 9*32, 16*2, 16*2)

		# init position
		self.rect = pygame.Rect(12*16, 24*16, 32, 32)

		# start w/ undamaged and shiny castle
		self.rebuild()

	def draw(self):
		""" Draw castle """
		global screen

		screen.blit(self.image, self.rect.topleft)

		if self.protected:
			screen.blit(self.img_protected, self.rect.topleft)

		if self.state == self.STATE_EXPLODING:
			if not self.explosion.active:
				self.state = self.STATE_DESTROYED
				del self.explosion
			else:
				self.explosion.draw()

	def rebuild(self):
		""" Reset castle """
		self.state = self.STATE_STANDING
		self.image = self.img_undamaged
		self.active = True

	def destroy(self):
		""" Destroy castle """

		if play_sounds:
			sounds["boom"].play()

		self.state = self.STATE_EXPLODING
		self.explosion = Explosion(self.rect.topleft)
		self.image = self.img_destroyed
		self.active = False

class Bonus():
	""" Various power-ups
	When bonus is spawned, it begins flashing and after some time dissapears

	Available bonusses:
		grenade	: Picking up the grenade power up instantly wipes out ever enemy presently on the screen, including Armor Tanks regardless of how many times you've hit them. You do not, however, get credit for destroying them during the end-stage bonus points.
		helmet	: The helmet power up grants you a temporary force field that makes you invulnerable to enemy shots, just like the one you begin every stage with.
		shovel	: The shovel power up turns the walls around your fortress from brick to stone. This makes it impossible for the enemy to penetrate the wall and destroy your fortress, ending the game prematurely. The effect, however, is only temporary, and will wear off eventually.
		star		: The star power up grants your tank with new offensive power each time you pick one up, up to three times. The first star allows you to fire your bullets as fast as the power tanks can. The second star allows you to fire up to two bullets on the screen at one time. And the third star allows your bullets to destroy the otherwise unbreakable steel walls. You carry this power with you to each new stage until you lose a life.
		tank		: The tank power up grants you one extra life. The only other way to get an extra life is to score 20000 points.
		timer		: The timer power up temporarily freezes time, allowing you to harmlessly approach every tank and destroy them until the time freeze wears off.
	"""

	# bonus types
	(BONUS_GRENADE, BONUS_HELMET, BONUS_TIMER, BONUS_SHOVEL, BONUS_TANK, BONUS_STAR, BONUS_PISTOL, BONUS_SHIP) = range(8)

	def __init__(self, level):

		global sprites

		# to know where to place
		self.level = level

		# bonus lives only for a limited period of time
		self.active = True

		# blinking state
		self.visible = True

		self.rect = pygame.Rect(random.randint(0, 416-32), random.randint(0, 416-32), 32, 32)

		self.bonus = random.choice([
			self.BONUS_STAR,
			self.BONUS_STAR,
			self.BONUS_GRENADE,
			self.BONUS_GRENADE,
			self.BONUS_HELMET,
			self.BONUS_SHOVEL,
			self.BONUS_SHOVEL,
			self.BONUS_TANK,
			self.BONUS_TIMER,
			self.BONUS_PISTOL
#			self.BONUS_SHIP
		])

		#self.bonus = self.BONUS_GRENADE

		# self.image = sprites.subsurface(16*2*self.bonus, 32*2, 16*2, 15*2)
		self.image = sprites2.subsurface((7*S_SIZE+2)*T_SIZE, 32*(self.bonus+1), 32, 32)

	def draw(self):
		""" draw bonus """
		global screen
		if self.visible:
			screen.blit(self.image, self.rect.topleft)

	def toggleVisibility(self):
		""" Toggle bonus visibility """
		self.visible = not self.visible

class Bullet():
	# direction constants
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)

	# bullet's stated
	(STATE_REMOVED, STATE_ACTIVE, STATE_EXPLODING) = range(3)

	(OWNER_PLAYER, OWNER_ENEMY) = range(2)

	def __init__(self, level, position, direction, damage = 100, speed = DEFAULT_BULLET_SPEED, power = 1):

		global sprites

		self.level = level
		self.direction = direction
		self.damage = damage
		self.owner = None
		self.owner_class = None

		# 1-regular everyday normal bullet
		# 2-can destroy steel
		self.power = power

		self.image = sprites.subsurface(75*2, 74*2, 3*2, 4*2)

		# position is player's top left corner, so we'll need to
		# recalculate a bit. also rotate image itself.
		if direction == self.DIR_UP:
			self.rect = pygame.Rect(position[0] + 12, position[1], 8, 8)
		elif direction == self.DIR_RIGHT:
			self.image = pygame.transform.rotate(self.image, 270)
			self.rect = pygame.Rect(position[0] + 32 - 8, position[1] + 12, 8, 8)
		elif direction == self.DIR_DOWN:
			self.image = pygame.transform.rotate(self.image, 180)
			self.rect = pygame.Rect(position[0] + 12, position[1] + 32 - 8, 8, 8)
		elif direction == self.DIR_LEFT:
			self.image = pygame.transform.rotate(self.image, 90)
			self.rect = pygame.Rect(position[0] + 4 , position[1] + 12, 8, 8)

		self.explosion_images = [
			sprites.subsurface(0, 80*2, 32*2, 32*2),
			sprites.subsurface(32*2, 80*2, 32*2, 32*2),
		]

		self.speed = speed

		self.state = self.STATE_ACTIVE

		self.dbg_label = Label(self.rect.bottomleft, str(self.rect.topleft))


	def draw(self):
		""" draw bullet """
		global screen
		if self.state == self.STATE_ACTIVE:
			screen.blit(self.image, self.rect.topleft)
		elif self.state == self.STATE_EXPLODING:
			self.explosion.draw()

		# debug sprites
		if DEBUG_SPRITES:
			red = (255,0,0)
			pygame.draw.rect(screen, red, self.rect, 1)
			self.dbg_label.position = self.rect.bottomleft
			self.dbg_label.text = str(self.rect.topleft) + " " + str(self.rect.size)
			self.dbg_label.draw()

	def update(self):
		global castle, players, enemies, bullets, sounds

		if self.state == self.STATE_EXPLODING:
			if not self.explosion.active:
				self.destroy()
				del self.explosion

		if self.state != self.STATE_ACTIVE:
			return

		""" move bullet """
		if self.direction == self.DIR_UP:
			self.rect.topleft = [self.rect.left, self.rect.top - self.speed]
			if self.rect.top < 0:
				if play_sounds and self.owner == self.OWNER_PLAYER:
					sounds["steel"].play()
				self.explode()
				return
		elif self.direction == self.DIR_RIGHT:
			self.rect.topleft = [self.rect.left + self.speed, self.rect.top]
			if self.rect.left > (416 - self.rect.width):
				if play_sounds and self.owner == self.OWNER_PLAYER:
					sounds["steel"].play()
				self.explode()
				return
		elif self.direction == self.DIR_DOWN:
			self.rect.topleft = [self.rect.left, self.rect.top + self.speed]
			if self.rect.top > (416 - self.rect.height):
				if play_sounds and self.owner == self.OWNER_PLAYER:
					sounds["steel"].play()
				self.explode()
				return
		elif self.direction == self.DIR_LEFT:
			self.rect.topleft = [self.rect.left - self.speed, self.rect.top]
			if self.rect.left < 0:
				if play_sounds and self.owner == self.OWNER_PLAYER:
					sounds["steel"].play()
				self.explode()
				return

		has_collided = False
		
		# check for removable tiles
		# if bullet is powerfull enough it can clear those tiles
		if self.power >= 2:
			
			rects = self.level.removable_rects
			removable = self.rect.collidelistall(rects)
			if removable != []:
				for i in removable:
					for tile in self.level.mapr:
						if tile.topleft == rects[i].topleft:
							if play_sounds:
								sounds["brick"].play()
							self.level.mapr.remove(tile)

		# check for collisions with walls. one bullet can destroy several (1 or 2)
		# tiles but explosion remains 1
		rects = self.level.obstacle_rects
		collisions = self.rect.collidelistall(rects)
		if collisions != []:
			for i in collisions:
				if self.level.hitTile(rects[i].topleft, self.power, self.owner == self.OWNER_PLAYER):
					has_collided = True
		if has_collided:
			self.explode()
			return

		# check for collisions with other bullets
		for bullet in bullets:
			if self.state == self.STATE_ACTIVE and bullet.owner != self.owner and bullet != self and self.rect.colliderect(bullet.rect):
				self.destroy()
				self.explode()
				return

		# check for collisions with players
		for player in players:
			if player.state == player.STATE_ALIVE and self.rect.colliderect(player.rect):
				if player.bulletImpact(self.owner == self.OWNER_PLAYER, self.damage, self.owner_class, self.direction):
					self.destroy()
					return

		# check for collisions with enemies
		for enemy in enemies:
			if enemy.state == enemy.STATE_ALIVE and self.rect.colliderect(enemy.rect):
				if enemy.bulletImpact(self.owner == self.OWNER_ENEMY, self.damage, self.owner_class, self.direction):
					self.destroy()
					return

		if castle.active and castle.protected and self.rect.colliderect(castle.rect):
			castle.protected = False
			self.destroy()
			castle.rebuild()
			self.owner_class.explode()
			game.level.buildFortress(game.level.TILE_STEEL)
			if not FORTRESS_FOREVER:
				game.destroyTimer(game.fortress_end_timer)
				game.fortress_end_timer = gtimer.add(BONUS_FORTRESS_WALLS_TIMEOUT, lambda :game.level.buildFortress(self.level.TILE_BRICK), 1)
			return
			
		# check for collision with castle
		if castle.active and self.rect.colliderect(castle.rect):
			castle.destroy()
			self.destroy()
			return

	def explode(self):
		""" start bullets's explosion """
		global screen
		if self.state != self.STATE_REMOVED:
			self.state = self.STATE_EXPLODING
			self.explosion = Explosion([self.rect.left-16, self.rect.top-16], None, self.explosion_images)

	def destroy(self):
		self.state = self.STATE_REMOVED

class Label():
	def __init__(self, position, text = "", duration = None):

		self.position = position

		self.active = True

		self.text = text

		if not DISABLE_LABELS:
			self.font = pygame.font.SysFont("Arial", 10)

		if duration != None:
			gtimer.add(duration, lambda :self.destroy(), 1)

	def draw(self):
		""" draw label """
		global screen
		if not DISABLE_LABELS: 
			screen.blit(self.font.render(self.text, False, (200,200,200)), [self.position[0]+4, self.position[1]+8])

	def destroy(self):
		self.active = False

class Explosion():
	def __init__(self, position, interval = None, images = None):

		global sprites

		self.position = [position[0]-16, position[1]-16]
		self.active = True

		if interval == None:
			interval = 100

		if images == None:
			images = [
				sprites.subsurface(0, 80*2, 32*2, 32*2),
				sprites.subsurface(32*2, 80*2, 32*2, 32*2),
				sprites.subsurface(64*2, 80*2, 32*2, 32*2)
			]

		images.reverse()

		self.images = [] + images

		self.image = self.images.pop()

		gtimer.add(interval, lambda :self.update(), len(self.images) + 1)

	def draw(self):
		global screen
		""" draw current explosion frame """
		screen.blit(self.image, self.position)

	def update(self):
		""" Advace to the next image """
		if len(self.images) > 0:
			self.image = self.images.pop()
		else:
			self.active = False

class Level():

	# tile constants
	(TILE_EMPTY, TILE_BRICK, TILE_STEEL, TILE_WATER, TILE_GRASS, TILE_FROZE) = range(6)

	# tile width/height in px
	TILE_SIZE = 16

	def __init__(self, level_nr = None):
		""" There are total 35 different levels. If level_nr is larger than 35, loop over
		to next according level so, for example, if level_nr ir 37, then load level 2 """

		global sprites, game

		# max number of enemies simultaneously  being on map
		self.max_active_enemies = MAX_ACTIVE_ENEMIES

		if game.nr_of_players == 1:
			self.max_active_enemies = MAX_ACTIVE_ENEMIES
		elif game.nr_of_players == 2:
			self.max_active_enemies = MAX_ACTIVE_ENEMIES_2_PLAYERS
		elif game.nr_of_players == 3:
			self.max_active_enemies = MAX_ACTIVE_ENEMIES_3_PLAYERS

		tile_images = [
			pygame.Surface((8*2, 8*2)),
			sprites.subsurface(48*2, 64*2, 8*2, 8*2),
			sprites.subsurface(48*2, 72*2, 8*2, 8*2),
			sprites.subsurface(56*2, 72*2, 8*2, 8*2),
			sprites.subsurface(64*2, 64*2, 8*2, 8*2),
			sprites.subsurface(72*2, 64*2, 8*2, 8*2),
			sprites.subsurface(64*2, 72*2, 8*2, 8*2)
		]
		self.tile_empty = tile_images[0]
		self.tile_brick = tile_images[1]
		self.tile_steel = tile_images[2]
		self.tile_grass = tile_images[3]
		self.tile_water = tile_images[4]
		self.tile_water1= tile_images[4]
		self.tile_water2= tile_images[5]
		self.tile_froze = tile_images[6]

		self.obstacle_rects = []

		level_nr = 1 if level_nr == None else level_nr%35
		if level_nr == 0:
			level_nr = 35

		self.loadLevel(level_nr)

		# tiles' rects on map, tanks cannot move over
		self.obstacle_rects = []
		
		# tiles' rects on map which can be removed by bullets
		self.removable_rects = []

		# update these tiles
		self.updateObstacleRects()
		self.updateRemovableRects()

		gtimer.add(600, lambda :self.toggleWaves())

	def hitTile(self, pos, power = 1, sound = False):
		"""
			Hit the tile
			@param pos Tile's x, y in px
			@return True if bullet was stopped, False otherwise
		"""

		global play_sounds, sounds

		for tile in self.mapr:
			if tile.topleft == pos:
				if tile.type == self.TILE_BRICK:
					if play_sounds and sound:
						sounds["brick"].play()
					self.mapr.remove(tile)
					self.updateObstacleRects()
					if power >= 4:
						return False
					return True
				elif tile.type == self.TILE_STEEL:
					if play_sounds and sound:
						sounds["steel"].play()
					if power >= 3:
						self.mapr.remove(tile)
						self.updateObstacleRects()
					if power >= 4:
						return False
					return True
				else:
					return False

	def toggleWaves(self):
		""" Toggle water image """
		if self.tile_water == self.tile_water1:
			self.tile_water = self.tile_water2
		else:
			self.tile_water = self.tile_water1


	def loadLevel(self, level_nr = 1):
		""" Load specified level
		@return boolean Whether level was loaded
		"""
		filename = "levels/"+str(level_nr)
		if (not os.path.isfile(filename)):
			return False
		level = []
		f = open(filename, "r")
		data = f.read().split("\n")
		self.mapr = []
		x, y = 0, 0
		for row in data:
			for ch in row:
				if ch == "#":
					self.mapr.append(myRect(x, y, self.TILE_SIZE, self.TILE_SIZE, self.TILE_BRICK))
				elif ch == "@":
					self.mapr.append(myRect(x, y, self.TILE_SIZE, self.TILE_SIZE, self.TILE_STEEL))
				elif ch == "~":
					self.mapr.append(myRect(x, y, self.TILE_SIZE, self.TILE_SIZE, self.TILE_WATER))
				elif ch == "%":
					self.mapr.append(myRect(x, y, self.TILE_SIZE, self.TILE_SIZE, self.TILE_GRASS))
				elif ch == "-":
					self.mapr.append(myRect(x, y, self.TILE_SIZE, self.TILE_SIZE, self.TILE_FROZE))
				x += self.TILE_SIZE
			x = 0
			y += self.TILE_SIZE
		return True


	def draw(self, tiles = None):
		""" Draw specified map on top of existing surface """

		global screen

		if tiles == None:
			tiles = [self.TILE_BRICK, self.TILE_STEEL, self.TILE_WATER, self.TILE_GRASS, self.TILE_FROZE]

		for tile in self.mapr:
			if tile.type in tiles:
				if tile.type == self.TILE_BRICK:
					screen.blit(self.tile_brick, tile.topleft)
				elif tile.type == self.TILE_STEEL:
					screen.blit(self.tile_steel, tile.topleft)
				elif tile.type == self.TILE_WATER:
					screen.blit(self.tile_water, tile.topleft)
				elif tile.type == self.TILE_FROZE:
					screen.blit(self.tile_froze, tile.topleft)
				elif tile.type == self.TILE_GRASS:
					screen.blit(self.tile_grass, tile.topleft)
					
	def updateRemovableRects(self):
		""" Set self.removable_rects to all tiles' rects that players can drive through and clear
		with bullets having enough power """

		global castle

		self.removable_rects = [castle.rect]

		for tile in self.mapr:
			if tile.type == self.TILE_GRASS:
				self.removable_rects.append(tile)

	def updateObstacleRects(self):
		""" Set self.obstacle_rects to all tiles' rects that players can destroy
		with bullets """

		global castle

		self.obstacle_rects = [castle.rect]

		for tile in self.mapr:
			if tile.type in (self.TILE_BRICK, self.TILE_STEEL, self.TILE_WATER):
				self.obstacle_rects.append(tile)

	def buildFortress(self, tile):
		""" Build walls around castle made from tile """

		positions = [
			(11*self.TILE_SIZE, 23*self.TILE_SIZE),
			(11*self.TILE_SIZE, 24*self.TILE_SIZE),
			(11*self.TILE_SIZE, 25*self.TILE_SIZE),
			(14*self.TILE_SIZE, 23*self.TILE_SIZE),
			(14*self.TILE_SIZE, 24*self.TILE_SIZE),
			(14*self.TILE_SIZE, 25*self.TILE_SIZE),
			(12*self.TILE_SIZE, 23*self.TILE_SIZE),
			(13*self.TILE_SIZE, 23*self.TILE_SIZE)
		]

		obsolete = []

		for i, rect in enumerate(self.mapr):
			if rect.topleft in positions:
				obsolete.append(rect)
		for rect in obsolete:
			self.mapr.remove(rect)

		for pos in positions:
			self.mapr.append(myRect(pos[0], pos[1], self.TILE_SIZE, self.TILE_SIZE, tile))

		self.updateObstacleRects()

class Tank():

	# possible directions
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)

	# states
	(STATE_SPAWNING, STATE_DEAD, STATE_ALIVE, STATE_EXPLODING) = range(4)

	# sides
	(SIDE_PLAYER, SIDE_ENEMY) = range(2)

	def __init__(self, level, side, position = None, direction = None, filename = None):

		global sprites

		# health. 0 health means dead
		self.health = 100

		# tank can't move but can rotate and shoot
		self.paralised = False

		# tank can't do anything
		self.paused = False

		# tank is protected from bullets
		self.shielded = False

		# px per move
		self.speed = DEFAULT_ENEMY_SPEED

		# friend or foe
		self.side = side

		# flashing state. 0-off, 1-on
		self.flash = 0
		
		self.bullet_speed = DEFAULT_BULLET_SPEED
		self.bullet_power = 1
		# how many bullets can tank fire simultaneously
		self.max_active_bullets = PLAYER_START_MAX_ACTIVE_BULLETS

		self.superpowers = 0
		# self.updateSuperpowers()

		# each tank can pick up 1 bonus
		self.bonus = None

		# navigation keys: fire, up, right, down, left
		self.controls = [pygame.K_j, pygame.K_w, pygame.K_d, pygame.K_s, pygame.K_a]

		# currently pressed buttons (navigation only)
		self.pressed = [False] * 4

		# visibility state
		self.visible = True

		# protected state
		self.protected = False
		self.protected_image = sprites2.subsurface((10+5)*32+4, 9*32, 16*2, 16*2)
		
		self.shield_images = [
			# sprites.subsurface(0, 48*2, 16*2, 16*2),
			# sprites.subsurface(16*2, 48*2, 16*2, 16*2)
			sprites2.subsurface(7*32+4, 9*32, 16*2, 16*2),
			sprites2.subsurface(8*32+4, 9*32, 16*2, 16*2)
		]
		self.shield_image = self.shield_images[0]
		self.shield_index = 0

		self.spawn_images = [
			sprites.subsurface(32*2, 48*2, 16*2, 16*2),
			sprites.subsurface(48*2, 48*2, 16*2, 16*2)
		]
		self.spawn_image = self.spawn_images[0]
		self.spawn_index = 0

		self.level = level

		if position != None:
			self.rect = pygame.Rect(position, (32, 32))
		else:
			self.rect = pygame.Rect(0, 0, 32, 32)

		if direction == None:
			self.direction = random.choice([self.DIR_RIGHT, self.DIR_DOWN, self.DIR_UP, self.DIR_LEFT])
		else:
			self.direction = direction

		self.state = self.STATE_SPAWNING

		# spawning animation
		self.timer_uuid_spawn = gtimer.add(100, lambda :self.toggleSpawnImage())

		# duration of spawning
		self.timer_uuid_spawn_end = gtimer.add(1000, lambda :self.endSpawning())

		self.visibility_timer = None

		self.shield_end_timer = None

		self.dbg_label = Label(self.rect.bottomleft, str(self.rect.topleft))

	def toggleVisibility(self):
		""" Toggle tank visibility """
		self.visible = not self.visible

	def hideTank(self, duration = None):
		if self.visibility_timer:
			gtimer.destroy(self.visibility_timer)

		self.setVisibility(False)
		self.visibility_timer = gtimer.add(duration, lambda: self.setVisibility(True))


	def setVisibility(self, visible):
		""" Set tank visibility """
		self.visible = visible

	def endSpawning(self):
		""" End spawning
		Player becomes operational
		"""
		self.state = self.STATE_ALIVE
		gtimer.destroy(self.timer_uuid_spawn_end)


	def toggleSpawnImage(self):
		""" advance to the next spawn image """
		if self.state != self.STATE_SPAWNING:
			gtimer.destroy(self.timer_uuid_spawn)
			return
		self.spawn_index += 1
		if self.spawn_index >= len(self.spawn_images):
			self.spawn_index = 0
		self.spawn_image = self.spawn_images[self.spawn_index]

	def toggleShieldImage(self):
		""" advance to the next shield image """
		if self.state != self.STATE_ALIVE:
			gtimer.destroy(self.timer_uuid_shield)
			return
		if self.shielded:
			self.shield_index += 1
			if self.shield_index >= len(self.shield_images):
				self.shield_index = 0
			self.shield_image = self.shield_images[self.shield_index]

	def draw(self):
		""" draw tank """
		global screen

		if self.state == self.STATE_ALIVE:
			# hidden state
			if not self.visible:
				return
			screen.blit(self.image, self.rect.topleft)
			if self.shielded:
				screen.blit(self.shield_image, [self.rect.left, self.rect.top])
			if self.protected:
				screen.blit(self.protected_image, [self.rect.left, self.rect.top])
		elif self.state == self.STATE_EXPLODING:
			self.explosion.draw()
		elif self.state == self.STATE_SPAWNING:
			screen.blit(self.spawn_image, self.rect.topleft)

		# debug sprites
		if DEBUG_SPRITES:
			green = (0,255,0)
			pygame.draw.rect(screen, green, self.rect, 1)
			self.dbg_label.position = self.rect.bottomleft
			self.dbg_label.text = str(self.rect.topleft) + " " + str(self.rect.size)
			self.dbg_label.draw()

	def explode(self):
		""" start tanks's explosion """
		if self.state != self.STATE_DEAD:
			self.state = self.STATE_EXPLODING
			self.explosion = Explosion(self.rect.topleft)
			

	def updateSuperpowers(self):
		""" update player super powers """

		self.updateSprites()

		# 0 - no superpowers
		if self.superpowers >= 0:
			self.bullet_speed = DEFAULT_BULLET_SPEED

			self.bullet_power = 1
			self.max_active_bullets = PLAYER_START_MAX_ACTIVE_BULLETS

		# 1 - faster bullets
		if self.superpowers >= 1:
			self.bullet_speed = 8

		# 2 - can fire 2 bullets
		if self.superpowers >= 2:
			self.max_active_bullets = 2
			
		# 3 - can clear trees
		if self.superpowers >= 3:
			self.bullet_power = 2
			
		# 4 - can destroy steel
		if self.superpowers >= 4:
			self.bullet_power = 3
			
		# 5 - can fire 3 bullets
		if self.superpowers >= 5:
			self.max_active_bullets = 3
			if ENABLE_PLAYER_PROTECTION:
				self.protected = True
		
		# 6- can clear trees, bricks and steel in 1 shot
		if self.superpowers >= 6:
			self.bullet_power = 4
			
		if self.superpowers >= 9:
			castle.protected = True
			
	def fire(self, forced = False):
		""" Shoot a bullet
		@param boolean forced. If false, check whether tank has exceeded his bullet quota. Default: True
		@return boolean True if bullet was fired, false otherwise
		"""

		global bullets, labels

		if self.state == self.STATE_SPAWNING:
			return False

		if self.state not in (self.STATE_ALIVE, self.STATE_SPAWNING):
			gtimer.destroy(self.timer_uuid_fire)
			return False

		if self.paused:
			return False

		if self.side == self.SIDE_ENEMY and random.randint(1, 100) < 100 - CHANCE_OF_FIRE:
			return False

		if not forced:
			active_bullets = 0
			for bullet in bullets:
				if bullet.owner_class == self and bullet.state == bullet.STATE_ACTIVE:
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
		bullets.append(bullet)
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
				
			SPRITES_FIX = 0

			new_x = self.nearest(self.rect.left - SPRITES_FIX, 16) + SPRITES_FIX
			new_y = self.nearest(self.rect.top - SPRITES_FIX, 16) + SPRITES_FIX
			new_rect = pygame.Rect([new_x, new_y], [32, 32])

			collision = False
			if new_rect.collidelist(self.level.obstacle_rects) != -1:
				collision = True
			for enemy in enemies:
				if enemy != self and new_rect.colliderect(enemy.rect):
					collision = True
			for player in players:
				if player != self and new_rect.colliderect(player.rect):
					collision = True
			if collision:
				#print "Collision!"
				return
				
			self.rect.left = new_x
			self.rect.top = new_y
			if DEBUG_COORDINATES:
				print("After fixing: " + str(self.rect.center))

			
	def turnRandom(self):
		""" Turn tank into random direction """
		self.direction = random.choice([self.DIR_UP, self.DIR_DOWN, self.DIR_RIGHT, self.DIR_LEFT])

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
	
	def getOppositeDirection(self, direction):
		""" Round number to nearest divisible """
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

		global play_sounds, sounds

		if self.shielded and not friendly_fire:
			return True

		if self.protected:
			if play_sounds:
				sounds["armor"].play()

			# if head collision don't do anything
			if HEAD_SHIELD_WHEN_PROTECTED:
				if bulletDirection == self.getOppositeDirection(self.direction):
					return True
			
			#self.protected = False
			#return True

		if not friendly_fire:
			if not INFINITE_HEALTH_FOR_ALL:
				self.health -= damage
				self.updateSprites()

			# restore health if infinite armor
			if PLAYER_INFINITE_ARMOR > 0 and self.side == self.SIDE_PLAYER:
				self.health += damage	

			# if Tank has a bonus display it
			if self.bonus:
				if not INFINITE_BONUSES:
					self.removeBonusLoad()

				# If bonus already exist on screen, remove it
				if len(bonuses) > 0 and not ALLOW_MULTI_BONUS:
					self.clearAllBonuses()
				
				# Show new bonus
				self.spawnBonus()

			if self.health > 99:
				if play_sounds:
						sounds["armor"].play()

			elif self.health < 1:
				if self.side == self.SIDE_ENEMY:
					tank.trophies["enemy" + str(self.type)] += 1
					points = (self.type + 1) * 100
					tank.score += points
					if play_sounds:
						sounds["explosion"].play()

					labels.append(Label(self.rect.topleft, str(points), 500))

				self.explode()
				if self.side == self.SIDE_PLAYER:
					if play_sounds:
						sounds["boom"].play()
			return True

		if self.side == self.SIDE_ENEMY:
			return False
		elif self.side == self.SIDE_PLAYER:
			if not FRIENDLY_FIRE:
				return False
			if not self.paralised:
				self.setParalised(True)
				self.timer_uuid_paralise = gtimer.add(10000, lambda :self.setParalised(False), 1)
			return True

	def setParalised(self, paralised = True):
		""" set tank paralise state
		@param boolean paralised
		@return None
		"""
		if self.state != self.STATE_ALIVE:
			gtimer.destroy(self.timer_uuid_paralise)
			return
		self.paralised = paralised

class Enemy(Tank):

	(TYPE_BASIC, TYPE_FAST, TYPE_POWER, TYPE_ARMOR) = range(4)
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)
	(FLASHING_YES, FLASHING_NO) = range(2)

	def __init__(self, level, type, position = None, direction = None, filename = None):

		Tank.__init__(self, level, type, position = None, direction = None, filename = None)

		global enemies, sprites

		# if true, do not fire
		self.bullet_queued = False

		self.persistance = 0

		if len(self.level.enemies_left) % BONUS_FREQ == (BONUS_FREQ - 1):
			self.bonus = True

		# chose type on random
		if len(level.enemies_left) > 0:
			self.type = level.enemies_left.pop()
		else:
			self.state = self.STATE_DEAD
			return

		if self.type == self.TYPE_BASIC:
			self.speed = DEFAULT_ENEMY_SPEED
		elif self.type == self.TYPE_FAST:
			self.speed = DEFAULT_ENEMY_SPEED + DEFAULT_ENEMY_SPEED_FAST
		elif self.type == self.TYPE_POWER:
			self.speed = 1
			self.superpowers = DEFAULT_ENEMY_SPEED
			self.updateSuperpowers()
		elif self.type == self.TYPE_ARMOR:
			self.speed = DEFAULT_ENEMY_SPEED
			self.health = DEFAULT_ENEMY_ARMOR_HEALTH

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
			self.rect.topleft = self.getFreeSpawningPosition()
			if not self.rect.topleft:
				self.state = self.STATE_DEAD
				return
				
		# when enemies are spawned they don't aquire poisiton until they find available tile
		# until than the don't collide with other tanks
		self.aquired_position = False

		# list of map coords where tank should go next
		self.path = self.generatePath(self.direction)

		# 100ms - 1000ms is duration between shots
		self.timer_uuid_fire = gtimer.add(ENEMY_FIRE_TIMER, lambda :self.fire())

		# if enemy tank picked up a bonus
		self.bonus_aquired = None

		# turn on flashing
		if self.bonus:
			self.timer_uuid_flash = gtimer.add(200, lambda :self.toggleFlash())

	# direction 0-up, 1-right, 2-down, 3-left
	# type 0-basic, 1-fast, 2-power, 3-armor
	def getEnemyImage(self, direction, type, health, flashing):
		if health > 400:
			health = 400
		if flashing == self.FLASHING_NO:
			return sprites2.subsurface((((health)/100)*S_SIZE+direction)*T_SIZE, type*2*T_SIZE, 32, 32)
		else:
			return sprites2.subsurface((0+direction)*T_SIZE, type*2*T_SIZE, 32, 32)

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
			self.image2 = dir_oriented_image[self.direction]
			
	def removeBonusLoad(self):
		""" Remove bonus from enemy tank and stop flashing """
		self.bonus = None
		gtimer.destroy(self.timer_uuid_flash)

		self.updateSprites()
		self.rotate(self.direction, False)

	def toggleFlash(self):
		""" Toggle flash state """
		if self.state not in (self.STATE_ALIVE, self.STATE_SPAWNING):
			gtimer.destroy(self.timer_uuid_flash)
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

		global bonuses, players, enemies

		if play_sounds:
			sounds["bonusnew"].play()
		
		bonus = Bonus(self.level)

		bonuses.append(bonus)
		gtimer.add(300, lambda :bonus.toggleVisibility())
		gtimer.add(BONUS_SPAWN_TIMEOUT, lambda :bonuses.remove(bonus), 1)

		# pickup the bonus immediately it it was placed on a player
		for player in players:
			if player.rect.colliderect(bonus.rect) == True:
				player.bonus = bonus
				return

		if ENEMY_PICKUP_BONUSES:
			for enemy in enemies:
				if enemy.rect.colliderect(bonus.rect) == True:
					enemy.bonus_aquired = bonus

	def clearAllBonuses(self):
		global bonuses, players

		for player in players:
			if player.state == player.STATE_ALIVE:
				if player.bonus != None and player.side == player.SIDE_PLAYER:
					player.bonus = None
			
		for bonus in bonuses:
			bonuses.remove(bonus)

	def getFreeSpawningPosition(self):
		global players, enemies, enemy_spawn_pos_index

		available_positions = [
			[(self.level.TILE_SIZE * 2 - self.rect.width) / 2, (self.level.TILE_SIZE * 2 - self.rect.height) / 2],
			[12 * self.level.TILE_SIZE + (self.level.TILE_SIZE * 2 - self.rect.width) / 2, (self.level.TILE_SIZE * 2 - self.rect.height) / 2],
			[24 * self.level.TILE_SIZE + (self.level.TILE_SIZE * 2 - self.rect.width) / 2,  (self.level.TILE_SIZE * 2 - self.rect.height) / 2]
		]
		enemy_spawn_pos_index += 1
		enemy_spawn_pos_index %= 3 

		return available_positions[enemy_spawn_pos_index]

	def move(self):
		""" move enemy if possible """

		global players, enemies, bonuses

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
		if new_rect.collidelist(self.level.obstacle_rects) != -1:
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
			for enemy in enemies:
				if enemy != self and new_rect.colliderect(enemy.rect):
					collision = True
			for player in players:
				if new_rect.colliderect(player.rect):
					collision = True
			if collision:
				self.rect.topleft = new_rect.topleft
			else:
				self.aquired_position = True
		else:
			# collisions with other enemies
			for enemy in enemies:
				if enemy != self and enemy.aquired_position and new_rect.colliderect(enemy.rect):
					self.turnRandom()
					self.path = self.generatePath(self.direction)
					return

			# collisions with players
			for player in players:
				if new_rect.colliderect(player.rect):
					self.turnRandom()
					self.path = self.generatePath(self.direction)
					return

			# collisions with bonuses
			if ENEMY_PICKUP_BONUSES:
				for bonus in bonuses:
					if new_rect.colliderect(bonus.rect):
						self.bonus_aquired = bonus

			# if no collision, move enemy
			self.rect.topleft = new_rect.topleft
			if DEBUG_COORDINATES:
				print("Move center: " + str(self.rect.center))


	def update(self, time_passed):
		Tank.update(self, time_passed)
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

		# at first, work with general units (steps) not px
		x = int(round(self.rect.left / 16))
		y = int(round(self.rect.top / 16))

		new_direction = None
		possible_directions = []

		for direction in directions:
			if direction == self.DIR_UP and y > 1:
				new_pos_rect = self.rect.move(0, -8)
				if new_pos_rect.collidelist(self.level.obstacle_rects) == -1:
					#new_direction = direction
					possible_directions.append(self.DIR_UP)
					break
			elif direction == self.DIR_RIGHT and x < 24:
				new_pos_rect = self.rect.move(8, 0)
				if new_pos_rect.collidelist(self.level.obstacle_rects) == -1:
					#new_direction = direction
					possible_directions.append(self.DIR_RIGHT)
					break
			elif direction == self.DIR_DOWN and y < 24:
				new_pos_rect = self.rect.move(0, 8)
				if new_pos_rect.collidelist(self.level.obstacle_rects) == -1:
					#new_direction = direction
					possible_directions.append(self.DIR_DOWN)
					break
			elif direction == self.DIR_LEFT and x > 1:
				new_pos_rect = self.rect.move(-8, 0)
				if new_pos_rect.collidelist(self.level.obstacle_rects) == -1:
					#new_direction = direction
					possible_directions.append(self.DIR_LEFT)
					break

		#if len(possible_directions) > 0:
			#new_direction = random.choice(possible_directions)

		# if we can go anywhere else, do a random turn
		if new_direction == None:
			new_direction = random.choice([self.DIR_UP, self.DIR_DOWN, self.DIR_RIGHT, self.DIR_LEFT])
			#print("nav izejas. griezhamies")

		# fix tanks position
		if fix_direction and new_direction == self.direction:
			fix_direction = False

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

		if new_direction == self.DIR_UP:
			for px in range(0, pixels, self.speed):
				positions.append([x, y-px])
		elif new_direction == self.DIR_RIGHT:
			for px in range(0, pixels, self.speed):
				positions.append([x+px, y])
		elif new_direction == self.DIR_DOWN:
			for px in range(0, pixels, self.speed):
				positions.append([x, y+px])
		elif new_direction == self.DIR_LEFT:
			for px in range(0, pixels, self.speed):
				positions.append([x-px, y])

		return positions

class Player(Tank):

	def __init__(self, level, type, position = None, direction = None, filename = None, player_nr=1):

		Tank.__init__(self, level, type, position = None, direction = None, filename = None)

		global sprites, sprites2

		if filename == None:
			filename = (0, 0, 16*2, 16*2)

		self.start_position = position
		self.start_direction = direction

		self.speed = PLAYER_DEFAULT_SPEED
		self.lives = PLAYER_START_LIFE
		self.superpowers = PLAYER_START_SUPERPOWER
		self.score = PLAYER_START_SCORE

		# store how many bonuses in this stage this player has collected
		self.trophies = {
			"bonus" : 0,
			"enemy0" : 0,
			"enemy1" : 0,
			"enemy2" : 0,
			"enemy3" : 0
		}

		if player_nr == 1:
			player_sprite_nr = 5
		else:
			player_sprite_nr = 6

		self.protected = False
		self.protected_image = sprites2.subsurface((10+player_sprite_nr)*32+4, 9*32, 16*2, 16*2)

		self.images2 = [
			sprites2.subsurface(player_sprite_nr*S_SIZE*T_SIZE, 0, 32, 32),
			sprites2.subsurface(player_sprite_nr*S_SIZE*T_SIZE, 2*T_SIZE, 32, 32),
			sprites2.subsurface(player_sprite_nr*S_SIZE*T_SIZE, 4*T_SIZE, 32, 32),
			sprites2.subsurface(player_sprite_nr*S_SIZE*T_SIZE, 6*T_SIZE, 32, 32)
		]

		self.image = sprites2.subsurface(filename)
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

	def move(self, direction):
		""" move player if possible """

		global players, enemies, bonuses

		if self.state == self.STATE_EXPLODING:
			if not self.explosion.active:
				self.state = self.STATE_DEAD
				del self.explosion

		if self.state != self.STATE_ALIVE:
			return

		# rotate player
		if self.direction != direction:
			self.rotate(direction)

		if self.paralised:
			return

		# move player
		if direction == self.DIR_UP:
			new_position = [self.rect.left, self.rect.top - self.speed]
			if new_position[1] < 0:
				return
		elif direction == self.DIR_RIGHT:
			new_position = [self.rect.left + self.speed, self.rect.top]
			if new_position[0] > (416 - 32):
				return
		elif direction == self.DIR_DOWN:
			new_position = [self.rect.left, self.rect.top + self.speed]
			if new_position[1] > (416 - 32):
				return
		elif direction == self.DIR_LEFT:
			new_position = [self.rect.left - self.speed, self.rect.top]
			if new_position[0] < 0:
				return

		player_rect = pygame.Rect(new_position, [32, 32])

		# collisions with tiles
		if player_rect.collidelist(self.level.obstacle_rects) != -1:
			return

		# collisions with other players
		for player in players:
			if player != self and player.state == player.STATE_ALIVE and player_rect.colliderect(player.rect) == True:
				if player.aquired_position:
					return

		# collisions with enemies
		for enemy in enemies:
			if player_rect.colliderect(enemy.rect) == True:
				if enemy.aquired_position and self.aquired_position:
					return

		# collisions with bonuses
		for bonus in bonuses:
			if player_rect.colliderect(bonus.rect) == True:
				self.bonus = bonus

		#if no collision, move player
		self.rect.topleft = (new_position[0], new_position[1])
		self.aquired_position = True

		if DEBUG_COORDINATES:
			print("Move center: " + str(self.rect.center))


	def reset(self):
		""" reset player """
		self.rotate(self.start_direction, False)
		self.rect.topleft = self.start_position
		self.max_active_bullets = PLAYER_START_MAX_ACTIVE_BULLETS
		self.superpowers = 0
		self.updateSuperpowers()
		self.health = PLAYER_START_HEALTH
		self.paralised = False
		self.paused = False
		self.pressed = [False] * 4
		self.state = self.STATE_ALIVE

class Game():

	# direction constants
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)

	TILE_SIZE = 16

	def __init__(self):

		global screen, sprites, sprites2, play_sounds, sounds, enemy_spawn_pos_index

		# center window
		os.environ['SDL_VIDEO_WINDOW_POS'] = 'center'

		if play_sounds:
			pygame.mixer.pre_init(44100, -16, 1, 512)

		pygame.init()

		pygame.display.set_caption("Battle City")

		if "-f" in sys.argv[1:]:
			self.is_fullscreen = True
		else:
			self.is_fullscreen = False

		screen = self.setFullScreen(self.is_fullscreen)

		self.clock = pygame.time.Clock()

		# load sprites (funky version)
		# sprites = pygame.transform.scale2x(pygame.image.load("images/sprites.gif"))
		# load sprites (pixely version)
		sprites = pygame.transform.scale(pygame.image.load("images/sprites.gif"), [192, 224])
		#screen.set_colorkey((0,138,104))
		sprites2 = pygame.transform.scale(pygame.image.load("images/sprites2.png"), [1024, 512])


		pygame.display.set_icon(sprites.subsurface(0, 0, 13*2, 13*2))

		# load sounds
		if play_sounds:
			pygame.mixer.init(44100, -16, 1, 512)

			sounds["start"] = pygame.mixer.Sound("sounds/gamestart.ogg")
			sounds["gameover"] = pygame.mixer.Sound("sounds/gameover.ogg")
			sounds["score"] = pygame.mixer.Sound("sounds/score.ogg")
			sounds["bg"] = pygame.mixer.Sound("sounds/background.ogg")
			sounds["fire"] = pygame.mixer.Sound("sounds/fire.ogg")
			sounds["bonus"] = pygame.mixer.Sound("sounds/bonus.ogg")
			sounds["bonusnew"] = pygame.mixer.Sound("sounds/bonusnew.ogg")
			sounds["explosion"] = pygame.mixer.Sound("sounds/explosion.ogg")
			sounds["boom"] = pygame.mixer.Sound("sounds/boom.ogg")
			sounds["brick"] = pygame.mixer.Sound("sounds/brick.ogg")
			sounds["steel"] = pygame.mixer.Sound("sounds/steel.ogg")
			sounds["armor"] = pygame.mixer.Sound("sounds/armor.ogg")
			sounds["ice"] = pygame.mixer.Sound("sounds/ice.ogg")
			sounds["life"] = pygame.mixer.Sound("sounds/life.ogg")
			sounds["pause"] = pygame.mixer.Sound("sounds/pause.ogg")

		self.enemy_life_image = sprites.subsurface(81*2, 57*2, 7*2, 7*2)
		self.player_life_image = sprites.subsurface(89*2, 56*2, 7*2, 8*2)
		self.flag_image = sprites.subsurface(64*2, 49*2, 16*2, 15*2)

		# this is used in intro screen
		self.player_image = pygame.transform.rotate(sprites.subsurface(0, 0, 13*2, 13*2), 270)
		
		self.player_image_green = pygame.transform.rotate(sprites.subsurface(16*2, 0, 13*2, 13*2), 270)


		# if true, no new enemies will be spawn during this time
		self.timefreeze = False
		
		self.game_paused = False

		# load custom font
		self.font = pygame.font.Font("fonts/prstart.ttf", 16)

		# pre-render game over text
		self.im_game_over = pygame.Surface((64, 40))
		self.im_game_over.set_colorkey((0,0,0))
		self.im_game_over.blit(self.font.render("GAME", False, (127, 64, 64)), [0, 0])
		self.im_game_over.blit(self.font.render("OVER", False, (127, 64, 64)), [0, 20])
		self.game_over_y = 416+40
		
		# pre-render pause text
		self.im_pause = pygame.Surface((80, 120))
		self.im_pause.set_colorkey((0,0,0))
		self.im_pause.blit(self.font.render("PAUSE", False, (127, 64, 64)), [0, 0])

		# number of players. here is defined preselected menu value
		self.nr_of_players = 1

		enemy_spawn_pos_index = 2

		# fortress timer
		self.fortress_end_timer = None

		# clock timer
		self.freeze_end_timer = None

		#debug mode
		self.debug_mode = False

		del players[:]
		del bullets[:]
		del enemies[:]
		del bonuses[:]

	def toggleDebugMode(self): 
		global DEBUG_SPRITES, DEBUG_DRAW_MESH
		self.debug_mode = not self.debug_mode
		DEBUG_SPRITES = DEBUG_DRAW_MESH = self.debug_mode

	def drawMesh(self):
		""" Draw 32 x 32 mesh on screen for debugging """
		global screen
		blue = pygame.Color(0,0,255)

		size = width, height = 416, 416
		H_STEP, V_STEP = 32, 32
		V_LINES = int(width / V_STEP) + 1
		H_LINES = int(width / H_STEP + 1)

		for i in range(H_LINES):
			pygame.draw.line(screen, blue, [0, i*H_STEP], [width, i*H_STEP], 1)

		for i in range(V_LINES):
			pygame.draw.line(screen, blue, [i*V_STEP, 0], [i*V_STEP, height], 1)


	def destroyTimer(self, timer):
		if timer:	
			gtimer.destroy(timer)
	
	def toggleFullScreen(self):
		self.is_fullscreen = not self.is_fullscreen
		self.setFullScreen(self.is_fullscreen)

	def setFullScreen(self, fullScreen):
		size = width, height = 480, 416

		if fullScreen:
			screen = pygame.display.set_mode(size, FULLSCREEN | DOUBLEBUF)
		else:
			screen = pygame.display.set_mode(size, DOUBLEBUF)
			
		return screen

	def triggerEnemyBonus(self, bonus, enemy):
		""" Execute enemy bonus powers """

		global enemies, labels, play_sounds, sounds

		if play_sounds:
			sounds["ice"].play()

		# destory all players
		if bonus.bonus == bonus.BONUS_GRENADE:
			# for player in players:
			# 	player.explode()
			self.loadLevelEnemies(True)
			if play_sounds:
				sounds["start"].play()

		# hide all players for 10 seconds
		elif bonus.bonus == bonus.BONUS_HELMET or bonus.bonus == bonus.BONUS_SHIP:
			for player in players:
				player.hideTank(BONUS_PLAYER_HIDDEN_TIMEOUT)
		# remove walls from fortress for 10 seconds
		elif bonus.bonus == bonus.BONUS_SHOVEL:
			if not FORTRESS_FOREVER:
				self.level.buildFortress(self.level.TILE_EMPTY)
				self.destroyTimer(self.fortress_end_timer)
				self.fortress_end_timer = gtimer.add(BONUS_FORTRESS_WALLS_TIMEOUT, lambda :self.level.buildFortress(self.level.TILE_BRICK), 1)
		# increase 1 enemy superpower by 2
		elif bonus.bonus == bonus.BONUS_STAR:
			for enemy in enemies:
				enemy.superpowers += 2
				enemy.updateSuperpowers()
		# increase 1 enemy superpower by 2
		elif bonus.bonus == bonus.BONUS_PISTOL:
			for enemy in enemies:
				enemy.superpowers += 2
				enemy.type += 2
				if enemy.type >= 3:
					enemy.health = 400
					enemy.type = 3
					enemy.speed = DEFAULT_ENEMY_SPEED_FAST
				enemy.updateSuperpowers()
		# increase all enemy health by 200
		elif bonus.bonus == bonus.BONUS_TANK:
			for enemy in enemies:
				enemy.health += 200
				enemy.updateSprites()
		# freeze players for 10 seconds
		elif bonus.bonus == bonus.BONUS_TIMER:
			self.togglePlayersFreeze(True)
			self.destroyTimer(self.freeze_end_timer)
			self.freeze_end_timer = gtimer.add(BONUS_TIMER_FREEZE_TIMEOUT, lambda :self.togglePlayersFreeze(False), 1)
		
		if bonus in bonuses:
			bonuses.remove(bonus)

	def triggerBonus(self, bonus, player):
		""" Execute bonus powers """

		global enemies, labels, play_sounds, sounds

		player.trophies["bonus"] += 1
		player.score += 500

		explode_count = 0
		# destroy all on screen enemies
		if bonus.bonus == bonus.BONUS_GRENADE:
			if play_sounds:
				sounds["explosion"].play()
			for enemy in enemies:
				explode_count += 1
				enemy.explode()
				if explode_count == 12:
					explode_count = 0
					break
		# shield player for 10 seconds
		elif bonus.bonus == bonus.BONUS_HELMET or bonus.bonus == bonus.BONUS_SHIP:
			if play_sounds:
				sounds["bonus"].play()
			self.shieldPlayer(player, True, BONUS_PLAYER_SHIELD_TIMEOUT)
		# upgrade fortress walls tp steel
		elif bonus.bonus == bonus.BONUS_SHOVEL:
			if play_sounds:
				sounds["bonus"].play()
			self.level.buildFortress(self.level.TILE_STEEL)
			if not FORTRESS_FOREVER:
				self.destroyTimer(self.fortress_end_timer)
				self.fortress_end_timer = gtimer.add(BONUS_FORTRESS_WALLS_TIMEOUT, lambda :self.level.buildFortress(self.level.TILE_BRICK), 1)
		# upgrade superpower
		elif bonus.bonus == bonus.BONUS_STAR:
			if play_sounds:
				sounds["bonus"].play()
			player.superpowers += 1
			player.updateSuperpowers()
		# upgrade superpower by 3
		elif bonus.bonus == bonus.BONUS_PISTOL:
			if play_sounds:
				sounds["bonus"].play()
			player.superpowers += 3
			player.updateSuperpowers()
		# add 1 life
		elif bonus.bonus == bonus.BONUS_TANK:
			if play_sounds:
				sounds["life"].play()
			player.lives += 1
		# stop all enemies for 10 seconds
		elif bonus.bonus == bonus.BONUS_TIMER:
			if play_sounds:
				sounds["bonus"].play()
			self.toggleEnemyFreeze(True)
			self.destroyTimer(self.freeze_end_timer)
			self.freeze_end_timer = gtimer.add(BONUS_TIMER_FREEZE_TIMEOUT, lambda :self.toggleEnemyFreeze(False), 1)
		
		if bonus in bonuses:
			bonuses.remove(bonus)

		labels.append(Label(bonus.rect.topleft, "500", 500))

	def shieldPlayer(self, player, shield = True, duration = None):
		""" Add/remove shield
		player: player (not enemy)
		shield: true/false
		duration: in ms. if none, do not remove shield automatically
		"""
		player.shielded = shield
		if shield:
			player.timer_uuid_shield = gtimer.add(100, lambda :player.toggleShieldImage())
		else:
			gtimer.destroy(player.timer_uuid_shield)

		if shield and duration != None:
			if player.shield_end_timer:
				gtimer.destroy(player.shield_end_timer)
			player.shield_end_timer = gtimer.add(duration, lambda :self.shieldPlayer(player, False), 1)


	def spawnEnemy(self):
		""" Spawn new enemy if needed
		Only add enemy if:
			- there are at least one in queue
			- map capacity hasn't exceeded its quota
			- now isn't timefreeze
		"""

		global enemies

		if self.game_paused:
			return
		if len(enemies) >= self.level.max_active_enemies:
			return
		if len(self.level.enemies_left) < 1:
			return
		enemy = Enemy(self.level, 1)

		if self.timefreeze:
			enemy.paused = True

		enemies.append(enemy)


	def respawnPlayer(self, player, clear_scores = False, superpowers = PLAYER_START_SUPERPOWER):
		""" Respawn player """
		player.reset()
		
		player.superpowers = superpowers
		player.updateSuperpowers()

		if clear_scores:
			player.trophies = {
				"bonus" : 0, "enemy0" : 0, "enemy1" : 0, "enemy2" : 0, "enemy3" : 0
			}

		self.aquired_position = False
		self.shieldPlayer(player, True, PLAYER_START_SHIELD_TIMEOUT)

	def gameOver(self):
		""" End game and return to menu """

		global play_sounds, sounds

		print("Game Over")
		if play_sounds:
			for sound in sounds:
				sounds[sound].stop()
			sounds["gameover"].play()

		self.game_over_y = 416+40

		self.game_over = True
		gtimer.add(3000, lambda :self.showScores(), 1)

	def gameOverScreen(self):
		""" Show game over screen """

		global screen

		# stop game main loop (if any)
		self.running = False

		screen.fill([0, 0, 0])

		self.writeInBricks("game", [125, 140])
		self.writeInBricks("over", [125, 220])
		pygame.display.flip()

		while 1:
			time_passed = self.clock.tick(50)
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						quit()
					if event.key == pygame.K_RETURN:
						self.showMenu()
						return

	def showMenu(self):
		""" Show game menu
		Redraw screen only when up or down key is pressed. When enter is pressed,
		exit from this screen and start the game with selected number of players
		"""

		global players, screen

		# stop game main loop (if any)
		self.running = False

		# clear all timers
		del gtimer.timers[:]

		# set current stage to 0
		self.stage = START_LEVEL - 1
		
		self.animateIntroScreen()

		main_loop = True
		while main_loop:
			time_passed = self.clock.tick(50)

			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						quit()
					elif event.key == pygame.K_DOWN:
						self.nr_of_players += 1
						if self.nr_of_players > 3:
							self.nr_of_players = 1
						self.drawIntroScreen()
					elif event.key == pygame.K_UP:
						self.nr_of_players -= 1
						if self.nr_of_players < 1:
							self.nr_of_players = 3
						self.drawIntroScreen()
					
					elif event.key == pygame.K_RETURN:
						main_loop = False
					
					elif event.key == pygame.K_f and pygame.key.get_mods() & pygame.KMOD_CTRL:
						self.toggleFullScreen()

		del players[:]
		self.nextLevel()

	def reloadPlayers(self):
		""" Init players
		If players already exist, just reset them
		"""

		global players

		

		if len(players) == 0:
			# first player
			x = 8 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
			y = 24 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2

			player = Player(
				self.level, 0, [x, y], self.DIR_UP, (5*S_SIZE*T_SIZE, 0, T_SIZE, T_SIZE), 1
			)
			players.append(player)

			# second player
			if self.nr_of_players >= 2:
				x = 16 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
				y = 24 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
				player = Player(
					self.level, 0, [x, y], self.DIR_UP, (6*S_SIZE*T_SIZE, 0, 16*2, 16*2), 2
				)
				player.controls = [pygame.K_l, pygame.K_w, pygame.K_d, pygame.K_s, pygame.K_a]
				players.append(player)

			# third player
			if self.nr_of_players == 3:
				x = 12 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
				y = 21 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
				player = Player(
					self.level, 0, [x, y], self.DIR_UP, (16*2, 0, 16*2, 16*2), 3
				)
				player.controls = [pygame.K_k, pygame.K_y, pygame.K_j, pygame.K_h, pygame.K_g]
				players.append(player)

		for player in players:
			player.level = self.level
			self.respawnPlayer(player, True, player.superpowers)

	def showScores(self):
		""" Show level scores """

		global screen, sprites, players, play_sounds, sounds

		# stop game main loop (if any)
		self.running = False

		# clear all timers
		del gtimer.timers[:]

		if play_sounds:
			for sound in sounds:
				sounds[sound].stop()

		hiscore = self.loadHiscore()

		# update hiscore if needed
		if players[0].score > hiscore:
			hiscore = players[0].score
			self.saveHiscore(hiscore)
		if self.nr_of_players == 2 and players[1].score > hiscore:
			hiscore = players[1].score
			self.saveHiscore(hiscore)

		img_tanks = [
			sprites.subsurface(32*2, 0, 13*2, 15*2),
			sprites.subsurface(48*2, 0, 13*2, 15*2),
			sprites.subsurface(64*2, 0, 13*2, 15*2),
			sprites.subsurface(80*2, 0, 13*2, 15*2)
		]

		img_arrows = [
			sprites.subsurface(81*2, 48*2, 7*2, 7*2),
			sprites.subsurface(88*2, 48*2, 7*2, 7*2)
		]

		screen.fill([0, 0, 0])

		# colors
		black = pygame.Color("black")
		white = pygame.Color("white")
		purple = pygame.Color(127, 64, 64)
		pink = pygame.Color(191, 160, 128)

		screen.blit(self.font.render("HI-SCORE", False, purple), [105, 35])
		screen.blit(self.font.render(str(hiscore), False, pink), [295, 35])

		screen.blit(self.font.render("STAGE"+str(self.stage).rjust(3), False, white), [170, 65])

		screen.blit(self.font.render("I-PLAYER", False, purple), [25, 95])

		#player 1 global score
		screen.blit(self.font.render(str(players[0].score).rjust(8), False, pink), [25, 125])

		if self.nr_of_players == 2:
			screen.blit(self.font.render("II-PLAYER", False, purple), [310, 95])

			#player 2 global score
			screen.blit(self.font.render(str(players[1].score).rjust(8), False, pink), [325, 125])

		# tanks and arrows
		for i in range(4):
			screen.blit(img_tanks[i], [226, 160+(i*45)])
			screen.blit(img_arrows[0], [206, 168+(i*45)])
			if self.nr_of_players == 2:
				screen.blit(img_arrows[1], [258, 168+(i*45)])

		screen.blit(self.font.render("TOTAL", False, white), [70, 335])

		# total underline
		pygame.draw.line(screen, white, [170, 330], [307, 330], 4)

		pygame.display.flip()

		self.clock.tick(2)

		interval = 6

		# points and kills
		for i in range(4):

			# total specific tanks
			tanks = players[0].trophies["enemy"+str(i)]

			for n in range(tanks+1):
				if n > 0 and play_sounds:
					sounds["score"].play()

				# erase previous text
				screen.blit(self.font.render(str(n-1).rjust(2), False, black), [170, 168+(i*45)])
				# print new number of enemies
				screen.blit(self.font.render(str(n).rjust(2), False, white), [170, 168+(i*45)])
				# erase previous text
				screen.blit(self.font.render(str((n-1) * (i+1) * 100).rjust(4)+" PTS", False, black), [25, 168+(i*45)])
				# print new total points per enemy
				screen.blit(self.font.render(str(n * (i+1) * 100).rjust(4)+" PTS", False, white), [25, 168+(i*45)])
				pygame.display.flip()
				self.clock.tick(interval)

			if self.nr_of_players == 2:
				tanks = players[1].trophies["enemy"+str(i)]

				for n in range(tanks+1):

					if n > 0 and play_sounds:
						sounds["score"].play()

					screen.blit(self.font.render(str(n-1).rjust(2), False, black), [277, 168+(i*45)])
					screen.blit(self.font.render(str(n).rjust(2), False, white), [277, 168+(i*45)])

					screen.blit(self.font.render(str((n-1) * (i+1) * 100).rjust(4)+" PTS", False, black), [325, 168+(i*45)])
					screen.blit(self.font.render(str(n * (i+1) * 100).rjust(4)+" PTS", False, white), [325, 168+(i*45)])

					pygame.display.flip()
					self.clock.tick(interval)

			self.clock.tick(interval-2)

		# total tanks
		tanks = sum([i for i in players[0].trophies.values()]) - players[0].trophies["bonus"]
		screen.blit(self.font.render(str(tanks).rjust(2), False, white), [170, 335])
		if self.nr_of_players == 2:
			tanks = sum([i for i in players[1].trophies.values()]) - players[1].trophies["bonus"]
			screen.blit(self.font.render(str(tanks).rjust(2), False, white), [277, 335])

		pygame.display.flip()

		# do nothing for 2 seconds
		self.clock.tick(1)
		self.clock.tick(1)

		if self.game_over:
			self.gameOverScreen()
		else:
			self.nextLevel()


	def draw(self):
		global screen, castle, players, enemies, bullets, bonuses

		screen.fill([0, 0, 0])

		self.level.draw([self.level.TILE_EMPTY, self.level.TILE_BRICK, self.level.TILE_STEEL, self.level.TILE_FROZE, self.level.TILE_WATER])

		castle.draw()

		for enemy in enemies:
			enemy.draw()

		for label in labels:
			label.draw()

		for player in players:
			player.draw()

		for bullet in bullets:
			bullet.draw()

		for bonus in bonuses:
			bonus.draw()

		self.level.draw([self.level.TILE_GRASS])
		
		if self.game_paused:
			screen.blit(self.im_pause, [176, 188])

		if self.game_over:
			if self.game_over_y > 188:
				self.game_over_y -= 4
			screen.blit(self.im_game_over, [176, self.game_over_y]) # 176=(416-64)/2

		self.drawSidebar()

		if DEBUG_DRAW_MESH:
			self.drawMesh()

		pygame.display.flip()

	def drawSidebar(self):

		global screen, players, enemies

		x = 416
		y = 0
		screen.fill([100, 100, 100], pygame.Rect([416, 0], [64, 416]))

		xpos = x + 16
		ypos = y + 16

		# draw enemy lives
		for n in range(len(self.level.enemies_left)):
			screen.blit(self.enemy_life_image, [xpos, ypos])
			if n % 2 == 1:
				xpos = x + 16
				ypos+= 17
			else:
				xpos += 17

		# players' lives
		if pygame.font.get_init():
			text_color = pygame.Color('black')
			for n in range(len(players)):
				lives_left = players[n].lives - 1
				if lives_left < 0:
					lives_left = 0 
				screen.blit(self.font.render(str(n+1)+"P", False, text_color), [x+20, y+210+n*42])
				screen.blit(self.font.render(str(lives_left), False, text_color), [x+35, y+227+n*42])
				screen.blit(self.player_life_image, [x+18, y+227+n*42])

			screen.blit(self.flag_image, [x+17, y+280+75])
			screen.blit(self.font.render(str(self.stage), False, text_color), [x+35, y+312+75])


	def drawIntroScreen(self, put_on_surface = True):
		""" Draw intro (menu) screen
		@param boolean put_on_surface If True, flip display after drawing
		@return None
		"""

		global screen

		screen.fill([0, 0, 0])

		if pygame.font.get_init():

			hiscore = self.loadHiscore()

			screen.blit(self.font.render("HI- "+str(hiscore), True, pygame.Color('white')), [170, 35])

			screen.blit(self.font.render("1 PLAYER", True, pygame.Color('white')), [165, 250])
			screen.blit(self.font.render("2 PLAYERS", True, pygame.Color('white')), [165, 275])
			screen.blit(self.font.render("3 PLAYERS", True, pygame.Color('white')), [165, 300])

			screen.blit(self.font.render("(c) 1980 1985 NAMCO LTD.", True, pygame.Color('white')), [50, 350])
			screen.blit(self.font.render("ALL RIGHTS RESERVED", True, pygame.Color('white')), [85, 380])


		if self.nr_of_players == 1:
			screen.blit(self.player_image, [125, 245])
		elif self.nr_of_players == 2:
			screen.blit(self.player_image_green, [125, 270])
		elif self.nr_of_players == 3:
			screen.blit(self.player_image_green, [125, 295])

		self.writeInBricks("battle", [65, 80])
		self.writeInBricks("city", [129, 160])

		if put_on_surface:
			pygame.display.flip()

	def animateIntroScreen(self):
		""" Slide intro (menu) screen from bottom to top
		If Enter key is pressed, finish animation immediately
		@return None
		"""

		global screen

		self.drawIntroScreen(False)
		screen_cp = screen.copy()

		screen.fill([0, 0, 0])

		y = 416
		while (y > 0):
			time_passed = self.clock.tick(50)
			for event in pygame.event.get():
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_RETURN or event.key == pygame.K_DOWN:
						y = 0
						break

			screen.blit(screen_cp, [0, y])
			pygame.display.flip()
			y -= 5

		screen.blit(screen_cp, [0, 0])
		pygame.display.flip()


	def chunks(self, l, n):
		""" Split text string in chunks of specified size
		@param string l Input string
		@param int n Size (number of characters) of each chunk
		@return list
		"""
		return [l[i:i+n] for i in range(0, len(l), n)]

	def writeInBricks(self, text, pos):
		""" Write specified text in "brick font"
		Only those letters are available that form words "Battle City" and "Game Over"
		Both lowercase and uppercase are valid input, but output is always uppercase
		Each letter consists of 7x7 bricks which is converted into 49 character long string
		of 1's and 0's which in turn is then converted into hex to save some bytes
		@return None
		"""

		global screen, sprites

		bricks = sprites.subsurface(56*2, 64*2, 8*2, 8*2)
		brick1 = bricks.subsurface((0, 0, 8, 8))
		brick2 = bricks.subsurface((8, 0, 8, 8))
		brick3 = bricks.subsurface((8, 8, 8, 8))
		brick4 = bricks.subsurface((0, 8, 8, 8))

		alphabet = {
			"a" : "0071b63c7ff1e3",
			"b" : "01fb1e3fd8f1fe",
			"c" : "00799e0c18199e",
			"e" : "01fb060f98307e",
			"g" : "007d860cf8d99f",
			"i" : "01f8c183060c7e",
			"l" : "0183060c18307e",
			"m" : "018fbffffaf1e3",
			"o" : "00fb1e3c78f1be",
			"r" : "01fb1e3cff3767",
			"t" : "01f8c183060c18",
			"v" : "018f1e3eef8e08",
			"y" : "019b3667860c18"
		}

		abs_x, abs_y = pos

		for letter in text.lower():

			binstr = ""
			for h in self.chunks(alphabet[letter], 2):
				binstr += str(bin(int(h, 16)))[2:].rjust(8, "0")
			binstr = binstr[7:]

			x, y = 0, 0
			letter_w = 0
			surf_letter = pygame.Surface((56, 56))
			for j, row in enumerate(self.chunks(binstr, 7)):
				for i, bit in enumerate(row):
					if bit == "1":
						if i%2 == 0 and j%2 == 0:
							surf_letter.blit(brick1, [x, y])
						elif i%2 == 1 and j%2 == 0:
							surf_letter.blit(brick2, [x, y])
						elif i%2 == 1 and j%2 == 1:
							surf_letter.blit(brick3, [x, y])
						elif i%2 == 0 and j%2 == 1:
							surf_letter.blit(brick4, [x, y])
						if x > letter_w:
							letter_w = x
					x += 8
				x = 0
				y += 8
			screen.blit(surf_letter, [abs_x, abs_y])
			abs_x += letter_w + 16

	def toggleEnemyFreeze(self, freeze = True):
		""" Freeze/defreeze all enemies """

		global enemies

		for enemy in enemies:
			enemy.paused = freeze
		self.timefreeze = freeze

	# def togglePlayersFreeze(self, freeze = True):
	# 	""" Freeze/defreeze all players """

	# 	global players

	# 	for player in players:
	# 		player.paralised = freeze

	def loadHiscore(self):
		""" Load hiscore
		Really primitive version =] If for some reason hiscore cannot be loaded, return 20000
		@return int
		"""
		filename = ".hiscore"
		if (not os.path.isfile(filename)):
			return 20000

		f = open(filename, "r")
		hiscore = int(f.read())

		if hiscore > 19999 and hiscore < 1000000:
			return hiscore
		else:
			print("cheater =[")
			return 20000

	def saveHiscore(self, hiscore):
		""" Save hiscore
		@return boolean
		"""
		try:
			f = open(".hiscore", "w")
		except:
			print("Can't save hi-score")
			return False
		f.write(str(hiscore))
		f.close()
		return True


	def finishLevel(self):
		""" Finish current level
		Show earned scores and advance to the next stage
		"""

		global play_sounds, sounds

		if play_sounds:
			sounds["bg"].stop()

		gtimer.add(LEVEL_FINISH_TIMEOUT, lambda :self.showScores(), 1)

		print("Stage "+str(self.stage)+" completed")
		
	def togglePlayersFreeze(self, freeze = True):
		""" Freeze/defreeze all players """
		global players
		
		for player in players:
			player.paralised = freeze
			# player.paused = freeze

	def pause(self):
		""" Pause the game """
		global sounds
		
		if not self.game_paused:
			#print "Game paused"
			self.game_paused = True
			# self.toggleEnemyFreeze(True)
			pygame.mixer.stop()
			if not DEBUG_UNFREEZE_PLAYERS_ON_PAUSE:
				self.togglePlayersFreeze(True)
			if play_sounds:
				sounds["pause"].play()
							
		else:
			#print "Game unpaused"
			self.game_paused = False
			# self.toggleEnemyFreeze(False)
			self.togglePlayersFreeze(False)
			if play_sounds:
				sounds["bg"].play(-1)

	def loadLevelEnemies(self, add):
		levels_enemies = (
			(18,2,0,0), (14,4,0,2), (14,4,0,2), (2,5,10,3), (8,5,5,2),
			(9,2,7,2), (7,4,6,3), (7,4,7,2), (6,4,7,3), (12,2,4,2),
			(5,5,4,6), (0,6,8,6), (0,8,8,4), (0,4,10,6), (0,2,10,8),
			(16,2,0,2), (8,2,8,2), (2,8,6,4), (4,4,4,8), (2,8,2,8),
			(6,2,8,4), (6,8,2,4), (0,10,4,6), (10,4,4,2), (0,8,2,10),
			(4,6,4,6), (2,8,2,8), (15,2,2,1), (0,4,10,6), (4,8,4,4),
			(3,8,3,6), (6,4,2,8), (4,4,4,8), (0,10,4,6), (0,6,4,10)
		)

		if self.stage <= 35:
			enemies_l = levels_enemies[self.stage - 1]
		else:
			enemies_l = levels_enemies[34]

		rand = random.randint(0, self.stage)

		# if EXTREME_MODE:
		# 	if add:
		# 		self.level.enemies_left += [0]*enemies_l[0] + [1]*(enemies_l[1] + rand) + [2]*enemies_l[2] + [3]*(enemies_l[3] + rand)
		# 	else:
		# 		self.level.enemies_left = [0]*enemies_l[0] + [1]*(enemies_l[1] + rand)+ [2]*enemies_l[2] + [3]*(enemies_l[3] + rand)

		# if CLASSIC_MODE:
		self.level.enemies_left = [0]*enemies_l[0] + [1]*enemies_l[1] + [2]*enemies_l[2] + [3]*enemies_l[3]

		random.shuffle(self.level.enemies_left)



	def nextLevel(self):
		""" Start next level """

		global castle, players, bullets, bonuses, play_sounds, sounds

		del bullets[:]
		del enemies[:]
		del bonuses[:]
		castle.rebuild()
		del gtimer.timers[:]

		# load level
		self.stage += 1
		self.level = Level(self.stage)
		self.timefreeze = False

		# set number of enemies by types (basic, fast, power, armor) according to level
		self.loadLevelEnemies(False)

		if play_sounds:
			sounds["start"].play()
			gtimer.add(4330, lambda :sounds["bg"].play(-1), 1)

		self.reloadPlayers()

		gtimer.add(ENEMY_SPAWN_TIMEOUT, lambda :self.spawnEnemy())

		# if True, start "game over" animation
		self.game_over = False

		# if False, game will end w/o "game over" bussiness
		self.running = True

		# if False, players won't be able to do anything
		self.active = True

		if FORTRESS_FOREVER > 0:
			self.level.buildFortress(self.level.TILE_STEEL)

		self.draw()

		while self.running:

			time_passed = self.clock.tick(GAME_FRAME_TIMING)

			if self.game_paused and not DEBUG_UNFREEZE_PLAYERS_ON_PAUSE:
				for event in pygame.event.get():
					if event.type == pygame.QUIT:
						quit()
					elif event.type == pygame.KEYDOWN and not self.game_over and self.active:
						if event.key == pygame.K_ESCAPE:
							quit()
						if event.key == pygame.K_RETURN:
							self.pause()
						if event.key == pygame.K_v:
							self.toggleDebugMode()
						if event.key == pygame.K_f and pygame.key.get_mods() & pygame.KMOD_CTRL:
							self.toggleFullScreen()
				
				self.draw()
				continue

			for event in pygame.event.get():
				if event.type == pygame.MOUSEBUTTONDOWN:
					pass
				elif event.type == pygame.QUIT:
					quit()
				elif event.type == pygame.KEYDOWN and not self.game_over and self.active:

					# Controls: ESC - quit, Enter - pause, p - debug enemy freeze, v - debug mesh,
					# ctrl+f - full screen, m  - mute sounds, b - borrow life from active player
					# toggle game quit
					if event.key == pygame.K_ESCAPE:
						quit()
					# toggle pause
					if event.key == pygame.K_RETURN:
						self.pause()
					# toggle debug freeze
					if event.key == pygame.K_p:
						self.toggleEnemyFreeze(not self.timefreeze)
					# toggle debug mesh
					if event.key == pygame.K_v:
						self.toggleDebugMode()
					# toggle full screen 	
					if event.key == pygame.K_f and pygame.key.get_mods() & pygame.KMOD_CTRL:
						self.toggleFullScreen()
					# toggle sounds
					elif event.key == pygame.K_m:
						play_sounds = not play_sounds
						if not play_sounds:
							pygame.mixer.stop()
						else:
							sounds["bg"].play(-1)

					if self.game_paused and not DEBUG_UNFREEZE_PLAYERS_ON_PAUSE:
						continue

					# borrow life from active players
					if event.key == pygame.K_b:
						dead_player = None
						for player in players:
							if player.state == player.STATE_DEAD:
								dead_player = player
						
						if dead_player:
							for plr in players:
								if plr.state == plr.STATE_ALIVE and plr.lives >= 2:
									plr.lives -= 1
									dead_player.lives += 1
									dead_player.superpowers = PLAYER_START_SUPERPOWER
									self.respawnPlayer(dead_player)

					for player in players:
						if player.state == player.STATE_ALIVE:
							try:
								index = player.controls.index(event.key)
							except:
								pass
							else:
								if index == 0:
									if player.fire() and play_sounds:
										sounds["fire"].play()
								elif index == 1:
									player.pressed[0] = True
								elif index == 2:
									player.pressed[1] = True
								elif index == 3:
									player.pressed[2] = True
								elif index == 4:
									player.pressed[3] = True
				elif event.type == pygame.KEYUP and not self.game_over and self.active:
					for player in players:
						if player.state == player.STATE_ALIVE:
							try:
								index = player.controls.index(event.key)
							except:
								pass
							else:
								if index == 1:
									player.pressed[0] = False
								elif index == 2:
									player.pressed[1] = False
								elif index == 3:
									player.pressed[2] = False
								elif index == 4:
									player.pressed[3] = False

			for player in players:
				if player.state == player.STATE_ALIVE and not self.game_over and self.active:
					if player.pressed[0] == True:
						player.move(self.DIR_UP)
					elif player.pressed[1] == True:
						player.move(self.DIR_RIGHT)
					elif player.pressed[2] == True:
						player.move(self.DIR_DOWN)
					elif player.pressed[3] == True:
						player.move(self.DIR_LEFT)
				player.update(time_passed)

			for enemy in enemies:
				if enemy.state == enemy.STATE_ALIVE:
						if enemy.bonus_aquired != None:
							self.triggerEnemyBonus(enemy.bonus_aquired, enemy)
							enemy.bonus_aquired = None
				if enemy.state == enemy.STATE_DEAD and not self.game_over and self.active:
					enemies.remove(enemy)
					if len(self.level.enemies_left) == 0 and len(enemies) == 0:
						self.finishLevel()
				else:
					enemy.update(time_passed)

			if not self.game_over and self.active:
				for player in players:
					if player.state == player.STATE_ALIVE:
						if player.bonus != None and player.side == player.SIDE_PLAYER:
							self.triggerBonus(player.bonus, player)
							player.bonus = None
					elif player.state == player.STATE_DEAD:
						if not PLAYER_INFINITE_LIVES and player.lives > 0:
							player.lives -= 1
						if player.lives > 0:
							player.superpowers = PLAYER_START_SUPERPOWER
							self.respawnPlayer(player)
						else:
							total_lives = 0
							for plr in players:
								total_lives += plr.lives
							if total_lives <= 0:
									self.gameOver()

			for bullet in bullets:
				if bullet.state == bullet.STATE_REMOVED:
					bullets.remove(bullet)
				else:
					bullet.update()

			for bonus in bonuses:
				if bonus.active == False:
					bonuses.remove(bonus)

			for label in labels:
				if not label.active:
					labels.remove(label)

			if not self.game_over:
				if not castle.active:
					self.gameOver()

			gtimer.update(time_passed)

			self.draw()

if __name__ == "__main__":

	gtimer = Timer()

	sprites = None
	sprites2 = None
	screen = None
	players = []
	enemies = []
	bullets = []
	bonuses = []
	labels = []

	play_sounds = True
	sounds = {}

	game = Game()
	castle = Castle()
	game.showMenu()
