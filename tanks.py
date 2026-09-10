#!/usr/bin/python
# coding=utf-8

import os, pygame, time, random, uuid, sys, argparse, json
from pygame.locals import *

# SDL game controller API: standard button layout for known gamepads
try:
	from pygame._sdl2 import controller as sdl_controller
except ImportError:
	sdl_controller = None

# MODE (presets at the end of settings override values below)
CLASSIC_MODE = False
EXTREME_MODE = False
GOOD_MODE = True
DEBUG_MODE = False

# CHEATS
START_LEVEL = 1
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
BONUS_SHIP_TIMEOUT = 20000	# ship bonus: tank can drive over water
VERSUS_BONUS_TIMEOUT = 15000	# versus mode: new random bonus every n ms
ICE_SLIDE_DISTANCE = 16	# px tank slides on ice after movement button is released
BRICK_QUARTERS = True	# brick tiles consist of 4 parts, bullet destroys nearest half (like on NES)
CHANCE_OF_FIRE = 50
ENEMY_FIRE_TIMER = 500
HEAD_SHIELD_WHEN_PROTECTED = True	# protected player tank isn't hurt by bullets hitting its front
ENABLE_PLAYER_PROTECTION = True	# player gets frontal armor at superpower 5

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
PLAYER_AUTO_FIRE_DELAY = 100	# min ms between shots while fire button is held

# CONTROLS: fire, up, right, down, left for players 1 and 2 (player 3 uses gamepad only)
# can be changed on settings screen
DEFAULT_PLAYER_CONTROLS = [
	[pygame.K_j, pygame.K_w, pygame.K_d, pygame.K_s, pygame.K_a],
	[pygame.K_RSHIFT, pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT],
]
PLAYER_CONTROLS = [list(controls) for controls in DEFAULT_PLAYER_CONTROLS]
START_FULLSCREEN = False

# DEBUG
DEBUG_UNFREEZE_PLAYERS_ON_PAUSE = DEBUG_MODE
DEBUG_SPRITES = DEBUG_MODE
DEBUG_DRAW_MESH = DEBUG_MODE
DEBUG_COORDINATES = DEBUG_MODE
DISABLE_LABELS = False	# score popups ("100", "500")

# EFFECTS
BONUS_BLINK_TIME = 5000	# bonus blinks during last ms before it disappears
SCREEN_SHAKE = True	# shake screen on big explosions
STAGE_SCREEN_TIME = 1500	# grey "STAGE N" screen before level, 0 - don't show
SHOW_EFFECT_TIMERS = True	# bars showing time left for shield, freeze and fortress walls

# CONSTANTS
S_SIZE = 4
T_SIZE = 32

# NES LIKE RULES
EXTRA_LIFE_SCORE = 20000	# extra life every n points, 0 - disabled
TWO_PLAYER_KILLS_BONUS = 1000	# 2+ players: player who destroyed most tanks on stage gets these points
ENEMY_AI_BASE_CHANCE = 30	# % chance enemy prefers directions towards player's castle

# NEW ENEMIES (disabled in CLASSIC preset)
ENABLE_NEW_ENEMIES = True
NEW_ENEMIES_FROM_STAGE = 5	# stealth and mortar tanks appear from this stage (wave)
BOSS_EVERY_STAGES = 5	# boss is the last enemy of every n-th stage (wave)
BOSS_HEALTH = 2000
BOSS_BONUS_EVERY = 500	# boss drops a bonus every n damage
STEALTH_ALPHA = 40	# stealth tank transparency (0-255) while hidden
STEALTH_REVEAL_FRAMES = 30	# stealth tank is visible for n frames after firing or being hit

# enemy types: basic, fast, power, armor, stealth, mortar, boss
ENEMY_POINTS = [100, 200, 300, 400, 300, 400, 2000]
# new types reuse sprites of original types with color tint
ENEMY_SPRITE_TYPES = [0, 1, 2, 3, 1, 2, 3]
ENEMY_TINTS = {4: (150, 150, 255), 5: (255, 110, 110), 6: (255, 215, 90)}

def emptyTrophies():
	""" Player's stage statistics: bonuses and destroyed tanks of every type """
	trophies = {"bonus": 0}
	for enemy_type in range(len(ENEMY_POINTS)):
		trophies["enemy" + str(enemy_type)] = 0
	return trophies

# DIFFICULTY PRESETS: every preset sets all these values, so presets can be switched at runtime
PRESETS = {
	# close to original NES game
	"CLASSIC": {
		"ALLOW_MULTI_BONUS": False,
		"ENEMY_PICKUP_BONUSES": False,
		"BONUS_FREQ": 5,
		"PLAYER_START_SUPERPOWER": 0,
		"DEFAULT_ENEMY_ARMOR_HEALTH": 400,
		"DEFAULT_ENEMY_SPEED_FAST": 1,
		"MAX_ACTIVE_ENEMIES": 4,
		"MAX_ACTIVE_ENEMIES_2_PLAYERS": 8,
		"MAX_ACTIVE_ENEMIES_3_PLAYERS": 10,
		"ENEMY_SPAWN_TIMEOUT": 2000,
		"ENABLE_PLAYER_PROTECTION": False,
		"ENEMY_AI_BASE_CHANCE": 50,
		"ENABLE_NEW_ENEMIES": False,
	},
	"GOOD": {
		"ALLOW_MULTI_BONUS": True,
		"ENEMY_PICKUP_BONUSES": True,
		"BONUS_FREQ": 4,
		"PLAYER_START_SUPERPOWER": 1,
		"DEFAULT_ENEMY_ARMOR_HEALTH": 600,
		"DEFAULT_ENEMY_SPEED_FAST": 2,
		"MAX_ACTIVE_ENEMIES": 5,
		"MAX_ACTIVE_ENEMIES_2_PLAYERS": 8,
		"MAX_ACTIVE_ENEMIES_3_PLAYERS": 12,
		"ENEMY_SPAWN_TIMEOUT": 1000,
		"ENABLE_PLAYER_PROTECTION": True,
		"ENEMY_AI_BASE_CHANCE": 30,
		"ENABLE_NEW_ENEMIES": True,
	},
	"EXTREME": {
		"ALLOW_MULTI_BONUS": True,
		"ENEMY_PICKUP_BONUSES": True,
		"BONUS_FREQ": 4,
		"PLAYER_START_SUPERPOWER": 1,
		"DEFAULT_ENEMY_ARMOR_HEALTH": 600,
		"DEFAULT_ENEMY_SPEED_FAST": 2,
		"MAX_ACTIVE_ENEMIES": 4,
		"MAX_ACTIVE_ENEMIES_2_PLAYERS": 14,
		"MAX_ACTIVE_ENEMIES_3_PLAYERS": 16,
		"ENEMY_SPAWN_TIMEOUT": 1000,
		"ENABLE_PLAYER_PROTECTION": True,
		"ENEMY_AI_BASE_CHANCE": 30,
		"ENABLE_NEW_ENEMIES": True,
	},
}

CURRENT_PRESET = None

def applyPreset(name):
	""" Set game settings from difficulty preset: CLASSIC, GOOD or EXTREME """
	global CURRENT_PRESET
	globals().update(PRESETS[name])
	CURRENT_PRESET = name

if CLASSIC_MODE:
	applyPreset("CLASSIC")
elif EXTREME_MODE:
	applyPreset("EXTREME")
elif GOOD_MODE:
	applyPreset("GOOD")

# command line arguments
ap = argparse.ArgumentParser()
ap.add_argument("-l", "--level", default=None, required=False, help="start level")
ap.add_argument("-f", "--fullscreen", action="store_true", help="start in full screen mode")
args = vars(ap.parse_args())

if args['level'] != None:
	START_LEVEL = int(args['level'])

SETTINGS_FILE = ".settings.json"
SAVEGAME_FILE = ".savegame"
HISCORES_FILE = ".hiscores.json"
CUSTOM_LEVELS_DIR = "custom_levels"	# levels made in editor (in data directory)
HISCORES_COUNT = 10	# entries in hiscore table

def dataFile(name):
	""" Path to file with saved data: hiscore, settings, saved game
	BATTLE_CITY_DATA_DIR environment variable changes the directory (used by tests)
	"""
	return os.path.join(os.environ.get("BATTLE_CITY_DATA_DIR", ""), name)

def levelFile(level_nr):
	""" Level map file: custom level made in editor or original one """
	custom = dataFile(os.path.join(CUSTOM_LEVELS_DIR, str(level_nr)))
	if os.path.isfile(custom):
		return custom
	return os.path.join("levels", str(level_nr))

def loadSettings():
	""" Apply settings saved on settings screen """
	global play_sounds, START_LEVEL, START_FULLSCREEN, PLAYER_CONTROLS

	try:
		with open(dataFile(SETTINGS_FILE), "r") as f:
			settings = json.load(f)
	except (IOError, ValueError):
		return

	try:
		if settings.get("preset") in PRESETS:
			applyPreset(settings["preset"])
		play_sounds = bool(settings.get("sound", play_sounds))
		START_FULLSCREEN = bool(settings.get("fullscreen", START_FULLSCREEN))
		# command line argument has priority
		start_level = int(settings.get("start_level", START_LEVEL))
		if args['level'] == None and 1 <= start_level <= 35:
			START_LEVEL = start_level
		controls = settings.get("controls")
		if isinstance(controls, list) and len(controls) == len(PLAYER_CONTROLS) and all([isinstance(c, list) and len(c) == 5 for c in controls]):
			PLAYER_CONTROLS = [[int(key) for key in c] for c in controls]
	except (TypeError, ValueError, AttributeError):
		print("Can't read settings")

def saveSettings(fullscreen):
	""" Save settings changed on settings screen """
	settings = {
		"preset": CURRENT_PRESET,
		"sound": play_sounds,
		"fullscreen": fullscreen,
		"start_level": START_LEVEL,
		"controls": PLAYER_CONTROLS,
	}
	try:
		with open(dataFile(SETTINGS_FILE), "w") as f:
			json.dump(settings, f, indent=1)
	except IOError:
		print("Can't save settings")


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

	def remaining(self, uuid_nr):
		""" Time left until timer fires
		@return [remaining ms, interval ms] or None if there is no such timer
		"""
		for timer in self.timers:
			if timer["uuid"] == uuid_nr:
				return [timer["interval"] - timer["time"], timer["interval"]]
		return None

	def update(self, time_passed):
		# iterate over a copy: callbacks may add or remove timers
		for timer in self.timers[:]:
			if timer not in self.timers:
				continue
			timer["time"] += time_passed
			if timer["time"] > timer["interval"]:
				timer["time"] -= timer["interval"]
				timer["times"] += 1
				if timer["repeat"] > -1 and timer["times"] == timer["repeat"]:
					self.timers.remove(timer)
				try:
					timer["callback"]()
				except Exception:
					if timer in self.timers:
						self.timers.remove(timer)

class Castle():
	""" Player's castle/fortress """

	(STATE_STANDING, STATE_DESTROYED, STATE_EXPLODING) = range(3)

	def __init__(self):

		global sprites

		# images
		self.img_undamaged = sprites.subsurface(0, 15*2, 16*2, 16*2)
		self.img_destroyed = sprites.subsurface(16*2, 15*2, 16*2, 16*2)

		# protection (player superpower 9): absorbs one enemy hit
		self.protected = False
		self.img_protected = sprites2.subsurface((10+5)*32+4, 9*32, 16*2, 16*2)

		# init position
		self.rect = pygame.Rect(12*16, 24*16, 32, 32)

		# index of player owning the castle (versus mode has castle for each player)
		self.owner = 0

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

		game.shake(25)

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

		# blinking state (blinks only before disappearing)
		self.visible = True
		self.blinking = False
		self.blink_timer = None

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
			self.BONUS_PISTOL,
			self.BONUS_SHIP
		])

		#self.bonus = self.BONUS_GRENADE

		# self.image = sprites.subsurface(16*2*self.bonus, 32*2, 16*2, 15*2)
		self.image = sprites2.subsurface((7*S_SIZE+2)*T_SIZE, 32*(self.bonus+1), 32, 32)

	def draw(self):
		""" draw bonus """
		global screen
		if self.visible:
			screen.blit(self.image, self.rect.topleft)

	def setType(self, bonus_type):
		""" Change bonus type and image """
		self.bonus = bonus_type
		self.image = sprites2.subsurface((7*S_SIZE+2)*T_SIZE, 32*(self.bonus+1), 32, 32)

	def startBlinking(self):
		""" Start blinking: bonus is about to disappear """
		self.blinking = True
		self.blink_timer = gtimer.add(150, lambda :self.toggleVisibility())

	def toggleVisibility(self):
		""" Toggle bonus visibility """
		if self not in bonuses:
			gtimer.destroy(self.blink_timer)
			return
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

		# mortar shells fly over walls
		self.over_walls = False

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
							break

		# check for collisions with walls. one bullet can destroy several (1 or 2)
		# tiles but explosion remains 1
		rects = self.level.obstacle_rects
		collisions = [] if self.over_walls else self.nearestCollisions(rects, self.rect.collidelistall(rects))
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
				# versus: other player's bullet is hostile
				friendly_fire = self.owner == self.OWNER_PLAYER and (game.mode != "versus" or self.owner_class is player)
				if player.bulletImpact(friendly_fire, self.damage, self.owner_class, self.direction):
					self.destroy()
					return

		# check for collisions with enemies
		for enemy in enemies:
			if enemy.state == enemy.STATE_ALIVE and self.rect.colliderect(enemy.rect):
				if enemy.bulletImpact(self.owner == self.OWNER_ENEMY, self.damage, self.owner_class, self.direction):
					self.destroy()
					return

		# protected castle: protection absorbs the hit, enemy shooter explodes,
		# fortress walls temporarily become steel
		if castle.active and castle.protected and self.rect.colliderect(castle.rect):
			castle.protected = False
			self.destroy()
			if self.owner == self.OWNER_ENEMY and self.owner_class.state == self.owner_class.STATE_ALIVE:
				self.owner_class.explode()
			game.level.buildFortress(game.level.TILE_STEEL)
			if not FORTRESS_FOREVER:
				game.destroyTimer(game.fortress_end_timer)
				game.fortress_end_timer = gtimer.add(BONUS_FORTRESS_WALLS_TIMEOUT, lambda :game.level.buildFortress(game.level.TILE_BRICK), 1)
			return

		# check for collision with castles (versus mode has two)
		for target in game.castles():
			if target.active and self.rect.colliderect(target.rect):
				target.destroy()
				self.destroy()
				return

	def nearestCollisions(self, rects, collisions):
		""" Keep only tiles in the row (column) nearest to the bullet
		Fast bullet can overlap two rows of brick quarters, but should destroy only one
		"""
		if len(collisions) < 2:
			return collisions

		if self.direction == self.DIR_UP:
			key, best = (lambda rect: rect.bottom), max
		elif self.direction == self.DIR_DOWN:
			key, best = (lambda rect: rect.top), min
		elif self.direction == self.DIR_LEFT:
			key, best = (lambda rect: rect.right), max
		else:
			key, best = (lambda rect: rect.left), min

		nearest = best([key(rects[i]) for i in collisions])
		return [i for i in collisions if key(rects[i]) == nearest]

	def explode(self):
		""" start bullets's explosion """
		global screen
		if self.state != self.STATE_REMOVED:
			self.state = self.STATE_EXPLODING
			self.explosion = Explosion([self.rect.left-16, self.rect.top-16], None, self.explosion_images)

	def destroy(self):
		self.state = self.STATE_REMOVED

class Label():

	# shared font: loading font for every label is slow
	font = None

	@staticmethod
	def getFont():
		if Label.font == None:
			Label.font = pygame.font.Font("fonts/prstart.ttf", 8)
		return Label.font

	def __init__(self, position, text = "", duration = None):

		self.position = position

		self.active = True

		self.text = text


		if duration != None:
			gtimer.add(duration, lambda :self.destroy(), 1)

	def draw(self):
		""" draw label """
		global screen
		if not DISABLE_LABELS: 
			screen.blit(Label.getFont().render(self.text, False, (255,255,255)), [self.position[0]+4, self.position[1]+12])

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

		# named levels (e.g. "versus") are loaded as is
		if not isinstance(level_nr, str):
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
		filename = levelFile(level_nr)
		if (not os.path.isfile(filename)):
			return False
		with open(filename, "r") as f:
			data = f.read().split("\n")
		return self.loadRows(data)

	def loadRows(self, data):
		""" Build map tiles from rows of level characters: . empty, # brick, @ steel, ~ water, % grass, - ice """
		self.mapr = []
		x, y = 0, 0
		for row in data:
			for ch in row:
				if ch == "#":
					self.addBrick(x, y)
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


	def addBrick(self, x, y):
		""" Add brick tile: 4 quarters 8x8 (BRICK_QUARTERS) or one 16x16 tile """
		if BRICK_QUARTERS:
			half = self.TILE_SIZE // 2
			for dx in (0, half):
				for dy in (0, half):
					self.mapr.append(myRect(x + dx, y + dy, half, half, self.TILE_BRICK))
		else:
			self.mapr.append(myRect(x, y, self.TILE_SIZE, self.TILE_SIZE, self.TILE_BRICK))

	def obstacleRectsFor(self, can_swim = False):
		""" Tiles tank can't drive through: water isn't an obstacle for tank with ship """
		return self.land_obstacle_rects if can_swim else self.obstacle_rects

	def draw(self, tiles = None):
		""" Draw specified map on top of existing surface """

		global screen

		if tiles == None:
			tiles = [self.TILE_BRICK, self.TILE_STEEL, self.TILE_WATER, self.TILE_GRASS, self.TILE_FROZE]

		for tile in self.mapr:
			if tile.type in tiles:
				if tile.type == self.TILE_BRICK:
					# brick quarter: draw matching part of brick image
					screen.blit(self.tile_brick, tile.topleft, [tile.left % self.TILE_SIZE, tile.top % self.TILE_SIZE, tile.width, tile.height])
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

		self.removable_rects = game.castleRects()

		for tile in self.mapr:
			if tile.type == self.TILE_GRASS:
				self.removable_rects.append(tile)

	def updateObstacleRects(self):
		""" Set self.obstacle_rects to all tiles' rects that players can destroy
		with bullets """

		global castle

		self.obstacle_rects = game.castleRects()

		# same without water (for tanks with ship)
		self.land_obstacle_rects = game.castleRects()

		self.water_rects = []
		self.ice_rects = []

		for tile in self.mapr:
			if tile.type in (self.TILE_BRICK, self.TILE_STEEL):
				self.obstacle_rects.append(tile)
				self.land_obstacle_rects.append(tile)
			elif tile.type == self.TILE_WATER:
				self.obstacle_rects.append(tile)
				self.water_rects.append(tile)
			elif tile.type == self.TILE_FROZE:
				self.ice_rects.append(tile)

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

		cells = [pygame.Rect(pos, (self.TILE_SIZE, self.TILE_SIZE)) for pos in positions]

		# remove whole tiles and brick quarters in fortress cells
		self.mapr = [rect for rect in self.mapr if rect.collidelist(cells) == -1]

		# don't wall in tanks standing on fortress tiles
		tank_rects = [tank.rect for tank in players + enemies if tank.state == tank.STATE_ALIVE]

		for cell in cells:
			if tile == self.TILE_EMPTY or cell.collidelist(tank_rects) != -1:
				continue
			if tile == self.TILE_BRICK:
				self.addBrick(cell.left, cell.top)
			else:
				self.mapr.append(myRect(cell.left, cell.top, self.TILE_SIZE, self.TILE_SIZE, tile))

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

		# fire button is held (auto fire)
		self.fire_pressed = False
		self.last_fire_time = 0

		# gamepad assigned to this tank and its state: up, right, down, left / fire
		self.gamepad = None
		self.pad_pressed = [False] * 4
		self.pad_fire = False

		# visibility state
		self.visible = True

		# ship bonus: can drive over water
		self.ship = False
		self.ship_timer = None

		# px left to slide on ice
		self.slide = 0

		# frames stealth tank stays visible
		self.reveal_frames = 0

		# frontal armor (player superpower 5+)
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
			self.direction = random.choice([self.DIR_UP, self.DIR_RIGHT, self.DIR_DOWN, self.DIR_LEFT])
		else:
			self.direction = direction

		self.state = self.STATE_SPAWNING

		# spawning animation
		self.timer_uuid_spawn = gtimer.add(100, lambda :self.toggleSpawnImage())

		# duration of spawning
		self.timer_uuid_spawn_end = gtimer.add(1000, lambda :self.endSpawning())

		self.visibility_timer = None

		self.shield_end_timer = None

		self.timer_uuid_shield = None

		self.dbg_label = Label(self.rect.bottomleft, str(self.rect.topleft))

	def toggleVisibility(self):
		""" Toggle tank visibility """
		self.visible = not self.visible

	def hideTank(self, duration = None):
		if self.visibility_timer:
			gtimer.destroy(self.visibility_timer)

		self.setVisibility(False)
		self.visibility_timer = gtimer.add(duration, lambda: self.setVisibility(True), 1)


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
			if self.ship:
				pygame.draw.rect(screen, (60, 140, 255), self.rect, 1)
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
			self.protected = False

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
			# frontal armor (players only)
			if ENABLE_PLAYER_PROTECTION and self.side == self.SIDE_PLAYER:
				self.protected = True
		
		# 6- can clear trees, bricks and steel in 1 shot
		if self.superpowers >= 6:
			self.bullet_power = 4

		# 9 - castle protection (players only)
		if self.superpowers >= 9 and self.side == self.SIDE_PLAYER and game.mode != "versus":
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

		# enemy specials: mortar shells fly over walls, stealth tank shows itself when firing
		if self.side == self.SIDE_ENEMY:
			if self.type == Enemy.TYPE_MORTAR:
				bullet.over_walls = True
				bullet.image = bullet.image.copy()
				bullet.image.fill((255, 90, 90), special_flags=pygame.BLEND_RGB_MULT)
			elif self.type == Enemy.TYPE_STEALTH:
				self.reveal_frames = STEALTH_REVEAL_FRAMES

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
			if new_rect.collidelist(self.level.obstacleRectsFor(self.canSwim())) != -1:
				collision = True
			for enemy in enemies:
				if enemy != self and new_rect.colliderect(enemy.rect):
					collision = True
			for player in players:
				if player != self and player.state == player.STATE_ALIVE and new_rect.colliderect(player.rect):
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
		ship = self.ship if self.side == self.SIDE_PLAYER else game.enemies_ship
		return ship or self.rect.collidelist(self.level.water_rects) != -1

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

		global play_sounds, sounds

		if self.shielded and not friendly_fire:
			return True

		# frontal armor: bullet flying against tank's direction hits its front and doesn't hurt
		if self.protected and not friendly_fire:
			if play_sounds:
				sounds["armor"].play()
			if HEAD_SHIELD_WHEN_PROTECTED and bulletDirection == self.getOppositeDirection(self.direction):
				return True

		if not friendly_fire:
			if not INFINITE_HEALTH_FOR_ALL:
				self.health -= damage
				self.updateSprites()
				self.reveal_frames = STEALTH_REVEAL_FRAMES
				# boss drops a bonus every BOSS_BONUS_EVERY damage
				if self.side == self.SIDE_ENEMY and self.type == Enemy.TYPE_BOSS and 0 < self.health and self.health % BOSS_BONUS_EVERY == 0:
					self.spawnBonus()

			# restore health if infinite armor
			if PLAYER_INFINITE_ARMOR > 0 and self.side == self.SIDE_PLAYER:
				self.health += damage	

			# if enemy tank carries a bonus display it
			if self.side == self.SIDE_ENEMY and self.bonus:
				if not INFINITE_BONUSES:
					self.removeBonusLoad()

				# If bonus already exit on screen, remove it
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
					points = ENEMY_POINTS[self.type]
					tank.score += points
					if play_sounds:
						sounds["explosion"].play()

					labels.append(Label(self.rect.topleft, str(points), 500))

					# big explosion
					if self.type == self.TYPE_ARMOR:
						game.shake(8)
					elif self.type == self.TYPE_BOSS:
						game.shake(25)

				# versus: count kills of the other player
				if self.side == self.SIDE_PLAYER and tank != None and tank is not self and tank.side == self.SIDE_PLAYER:
					tank.versus_kills += 1

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

	(TYPE_BASIC, TYPE_FAST, TYPE_POWER, TYPE_ARMOR, TYPE_STEALTH, TYPE_MORTAR, TYPE_BOSS) = range(7)
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)
	(FLASHING_YES, FLASHING_NO) = range(2)

	def __init__(self, level, type, position = None, direction = None, filename = None):

		Tank.__init__(self, level, type, position = None, direction = None, filename = None)

		global enemies, sprites

		# if true, do not fire
		self.bullet_queued = False

		# how many times tank keeps pushing into obstacle before turning
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
			self.superpowers = 1
			self.updateSuperpowers()
		elif self.type == self.TYPE_ARMOR:
			self.speed = DEFAULT_ENEMY_SPEED
			self.health = DEFAULT_ENEMY_ARMOR_HEALTH
		elif self.type == self.TYPE_STEALTH:
			self.speed = DEFAULT_ENEMY_SPEED
		elif self.type == self.TYPE_MORTAR:
			self.speed = 1
			self.health = 200
		elif self.type == self.TYPE_BOSS:
			self.speed = 1
			self.health = BOSS_HEALTH
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
			position = game.getFreeSpawningPosition() or [0, 0]
		self.rect.topleft = position
				
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
		""" Sprite for enemy type, direction and health; new types are tinted sprites of original types """
		sprite_type = ENEMY_SPRITE_TYPES[type]
		health = max(0, min(int(health), 400))
		if flashing == self.FLASHING_NO:
			image = sprites2.subsurface(((health // 100) * S_SIZE + direction) * T_SIZE, sprite_type * 2 * T_SIZE, 32, 32)
		else:
			image = sprites2.subsurface(direction * T_SIZE, sprite_type * 2 * T_SIZE, 32, 32)
		tint = ENEMY_TINTS.get(type)
		if tint:
			image = image.copy()
			image.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
		return image

	def draw(self):
		""" Stealth tank is almost invisible until it fires or gets hit, boss has health bar """
		global screen

		if self.type == self.TYPE_STEALTH and self.state == self.STATE_ALIVE and not self.bonus and self.reveal_frames <= 0:
			if self.visible:
				image = self.image.copy()
				image.set_alpha(STEALTH_ALPHA)
				screen.blit(image, self.rect.topleft)
			return

		Tank.draw(self)

		if self.type == self.TYPE_BOSS and self.state == self.STATE_ALIVE:
			width = int(32 * max(self.health, 0) / float(BOSS_HEALTH))
			pygame.draw.rect(screen, (255, 60, 60), [self.rect.left, self.rect.top - 4, max(width, 1), 3])

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
		# bonus blinks during last seconds before it disappears
		gtimer.add(max(BONUS_SPAWN_TIMEOUT - BONUS_BLINK_TIME, 1), lambda :bonus.startBlinking(), 1)
		gtimer.add(BONUS_SPAWN_TIMEOUT, lambda :bonuses.remove(bonus), 1)

		# pickup the bonus immediately it it was placed on a player
		for player in players:
			if player.state == player.STATE_ALIVE and player.rect.colliderect(bonus.rect) == True:
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
			
		del bonuses[:]

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
		if new_rect.collidelist(self.level.obstacleRectsFor(self.canSwim())) != -1:
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
			for enemy in enemies:
				if enemy != self and enemy.state != enemy.STATE_DEAD and new_rect.colliderect(enemy.rect):
					collision = True
					# overlapping tanks: positioned or older tank drives away first,
					# otherwise both would move together and never separate
					if enemy.aquired_position or enemies.index(enemy) < enemies.index(self):
						must_wait = True
			for player in players:
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
			for enemy in enemies:
				if enemy != self and (enemy.aquired_position or enemy.state == enemy.STATE_SPAWNING) and new_rect.colliderect(enemy.rect):
					self.turnRandom()
					self.path = self.generatePath(self.direction)
					return

			# collisions with players
			for player in players:
				if player.state == player.STATE_ALIVE and new_rect.colliderect(player.rect):
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

		# sometimes prefer directions towards player's castle
		if random.randint(1, 100) <= ENEMY_AI_BASE_CHANCE:
			towards = []
			if castle.rect.centery > self.rect.centery:
				towards.append(self.DIR_DOWN)
			if castle.rect.centerx > self.rect.centerx + 16:
				towards.append(self.DIR_RIGHT)
			elif castle.rect.centerx < self.rect.centerx - 16:
				towards.append(self.DIR_LEFT)
			random.shuffle(towards)
			directions = towards + [d for d in directions if d not in towards]

		# at first, work with general units (steps) not px
		x = int(round(self.rect.left / 16))
		y = int(round(self.rect.top / 16))

		new_direction = None

		for direction in directions:
			if direction == self.DIR_UP and y > 1:
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
			elif direction == self.DIR_LEFT and x > 1:
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
		steps = list(range(self.speed, pixels, self.speed)) + [pixels]

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

		global sprites, sprites2

		if filename == None:
			filename = (0, 0, 16*2, 16*2)

		self.start_position = position
		self.start_direction = direction

		self.speed = PLAYER_DEFAULT_SPEED
		self.lives = PLAYER_START_LIFE
		self.superpowers = PLAYER_START_SUPERPOWER
		self.score = PLAYER_START_SCORE

		# score for next extra life
		self.next_extra_life = EXTRA_LIFE_SCORE

		# versus: how many times this player destroyed the other one
		self.versus_kills = 0

		# store how many bonuses in this stage this player has collected
		self.trophies = emptyTrophies()

		if player_nr == 1:
			player_sprite_nr = 5
		else:
			player_sprite_nr = 6

		self.images2 = [
			sprites2.subsurface(player_sprite_nr*S_SIZE*T_SIZE, 0, 32, 32),
			sprites2.subsurface(player_sprite_nr*S_SIZE*T_SIZE, 2*T_SIZE, 32, 32),
			sprites2.subsurface(player_sprite_nr*S_SIZE*T_SIZE, 4*T_SIZE, 32, 32),
			sprites2.subsurface(player_sprite_nr*S_SIZE*T_SIZE, 6*T_SIZE, 32, 32)
		]

		self.protected = False
		self.protected_image = sprites2.subsurface((10+player_sprite_nr)*32+4, 9*32, 16*2, 16*2)

		# until player moves out of other tanks after respawn, they don't block him
		self.aquired_position = False

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
		if player_rect.collidelist(self.level.obstacleRectsFor(self.canSwim())) != -1:
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

		return True


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
		self.fire_pressed = False
		self.aquired_position = False
		self.slide = 0
		self.ship = False
		gtimer.destroy(self.ship_timer)
		self.ship_timer = None
		self.visible = True
		self.visibility_timer = None
		self.state = self.STATE_ALIVE

class Gamepad():
	""" Gamepad state reader
	Known gamepads are read through SDL game controller API (d-pad, left stick, A/B/X/Y, Start),
	other devices as plain joystick (hat 0, axes 0-1, buttons 0-3 fire, 7 or 9 start)
	"""

	# stick deflection needed to move
	AXIS_THRESHOLD = 0.5

	def __init__(self, index = None):
		""" index None creates gamepad without device (used by tests) """
		self.controller = None
		self.joystick = None
		self.state = {}
		self.prev = {}

		if index == None:
			return
		if sdl_controller != None and sdl_controller.is_controller(index):
			self.controller = sdl_controller.Controller(index)
		else:
			self.joystick = pygame.joystick.Joystick(index)
			self.joystick.init()

	def read(self):
		""" Read raw device state
		@return dict with booleans: up, right, down, left, fire, start
		"""
		up = right = down = left = fire = start = False
		x = y = 0.0

		if self.controller != None:
			c = self.controller
			up = c.get_button(pygame.CONTROLLER_BUTTON_DPAD_UP)
			right = c.get_button(pygame.CONTROLLER_BUTTON_DPAD_RIGHT)
			down = c.get_button(pygame.CONTROLLER_BUTTON_DPAD_DOWN)
			left = c.get_button(pygame.CONTROLLER_BUTTON_DPAD_LEFT)
			x = c.get_axis(pygame.CONTROLLER_AXIS_LEFTX) / 32768.0
			y = c.get_axis(pygame.CONTROLLER_AXIS_LEFTY) / 32768.0
			fire_buttons = (pygame.CONTROLLER_BUTTON_A, pygame.CONTROLLER_BUTTON_B, pygame.CONTROLLER_BUTTON_X, pygame.CONTROLLER_BUTTON_Y)
			fire = any([c.get_button(button) for button in fire_buttons])
			start = c.get_button(pygame.CONTROLLER_BUTTON_START)
		elif self.joystick != None:
			j = self.joystick
			if j.get_numhats() > 0:
				hat_x, hat_y = j.get_hat(0)
				up, down = hat_y > 0, hat_y < 0
				right, left = hat_x > 0, hat_x < 0
			if j.get_numaxes() >= 2:
				x, y = j.get_axis(0), j.get_axis(1)
			buttons = j.get_numbuttons()
			fire = any([j.get_button(button) for button in range(min(buttons, 4))])
			start = any([j.get_button(button) for button in (7, 9) if button < buttons])

		# left stick: only dominant axis counts (tanks can't move diagonally)
		if abs(x) > abs(y):
			right = right or x > self.AXIS_THRESHOLD
			left = left or x < -self.AXIS_THRESHOLD
		else:
			down = down or y > self.AXIS_THRESHOLD
			up = up or y < -self.AXIS_THRESHOLD

		return {
			"up": bool(up), "right": bool(right), "down": bool(down), "left": bool(left),
			"fire": bool(fire), "start": bool(start)
		}

	def update(self):
		""" Read new state, remember previous one (call once per frame) """
		self.prev = self.state
		try:
			self.state = self.read()
		except pygame.error:
			# device was disconnected
			self.state = {}

	def held(self, name):
		return self.state.get(name, False)

	def pressed(self, name):
		""" True only on the frame button was pressed """
		return self.held(name) and not self.prev.get(name, False)

	def directions(self):
		""" @return [up, right, down, left] """
		return [self.held("up"), self.held("right"), self.held("down"), self.held("left")]

class Game():

	# direction constants
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)

	TILE_SIZE = 16

	def __init__(self):

		global screen, sprites, sprites2, play_sounds, sounds, enemy_spawn_pos_index

		# center window
		os.environ['SDL_VIDEO_WINDOW_POS'] = 'center'

		pygame.mixer.pre_init(44100, -16, 1, 512)

		pygame.init()

		pygame.display.set_caption("Battle City")

		if args['fullscreen'] or START_FULLSCREEN:
			self.is_fullscreen = True
		else:
			self.is_fullscreen = False

		self.display = self.setFullScreen(self.is_fullscreen)

		# game is always drawn on this surface, then shown on display (scaled in full screen)
		screen = pygame.Surface((480, 416)).convert()

		self.clock = pygame.time.Clock()

		# load sprites (funky version)
		# sprites = pygame.transform.scale2x(pygame.image.load("images/sprites.gif"))
		# load sprites (pixely version)
		sprites = pygame.transform.scale(pygame.image.load("images/sprites.gif"), [192, 224])
		#screen.set_colorkey((0,138,104))
		sprites2 = pygame.transform.scale(pygame.image.load("images/sprites2.png"), [1024, 512])


		pygame.display.set_icon(sprites.subsurface(0, 0, 13*2, 13*2))

		# load sounds (always: sound can be switched on in settings)
		try:
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
		except pygame.error:
			print("Can't load sounds")
			play_sounds = False
			sounds.clear()

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

		# selected main menu item
		self.menu_index = 0

		# game mode: campaign (stages with score screens) or endless (waves until game over)
		self.mode = "campaign"
		self.first_stage = 1

		# versus: index of winning player
		self.versus_winner = None

		# players' score, lives and superpowers from saved game (applied when players are created)
		self.loaded_players_stats = None

		enemy_spawn_pos_index = 2

		# fortress timer
		self.fortress_end_timer = None

		# clock timers (enemies frozen by player bonus, players frozen by enemy bonus)
		self.enemy_freeze_end_timer = None
		self.players_freeze_end_timer = None
		self.players_frozen = False

		# what to show after main game loop stops
		self.next_action = None

		#debug mode
		self.debug_mode = False

		# enemies picked up ship bonus: they can drive over water
		self.enemies_ship = False
		self.enemies_ship_timer = None

		# frames left to shake the screen
		self.shake_frames = 0

		# True while "STAGE N" screen is shown
		self.stage_screen = False

		# connected gamepads (opened in updateGamepads)
		self.gamepads = []
		self.gamepad_count = 0

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


	def updateGamepads(self):
		""" Open newly connected gamepads, read state of all gamepads (call once per frame) """
		count = pygame.joystick.get_count()
		if count != self.gamepad_count:
			self.gamepad_count = count
			self.gamepads = []
			if sdl_controller != None:
				sdl_controller.init()
			for index in range(count):
				try:
					self.gamepads.append(Gamepad(index))
				except pygame.error:
					pass
			self.assignGamepads()

		for gamepad in self.gamepads:
			gamepad.update()

	def assignGamepads(self):
		""" Give gamepads to players: players without keyboard controls (P3) first, then P1, P2 """
		for player in players:
			player.gamepad = None
		ordered = [player for player in players if not player.controls] + [player for player in players if player.controls]
		for gamepad, player in zip(self.gamepads, ordered):
			player.gamepad = gamepad

	def applyGamepads(self):
		""" Gamepad controls in game: movement, fire (auto fire while held), Start - pause """
		for gamepad in self.gamepads:
			if gamepad.pressed("start") and not self.game_over and self.active:
				self.pause()
				break

		for player in players:
			if player.gamepad == None:
				player.pad_pressed = [False] * 4
				player.pad_fire = False
				continue
			player.pad_pressed = player.gamepad.directions()
			player.pad_fire = player.gamepad.held("fire")
			if player.gamepad.pressed("fire") and player.state == player.STATE_ALIVE and not self.game_over and self.active:
				self.playerFire(player)

	def destroyTimer(self, timer):
		if timer:	
			gtimer.destroy(timer)
	
	def isFullScreenKey(self, event):
		""" Ctrl+F / Cmd+F / Alt+Enter toggle full screen """
		if event.key == pygame.K_f and event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META):
			return True
		if event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT:
			return True
		return False

	def toggleFullScreen(self):
		self.is_fullscreen = not self.is_fullscreen
		try:
			pygame.display.toggle_fullscreen()
		except pygame.error:
			# some video drivers don't support toggling, recreate display instead
			try:
				self.setFullScreen(self.is_fullscreen)
			except pygame.error:
				# requested mode isn't available: stay in current mode
				self.is_fullscreen = not self.is_fullscreen
		self.flip()

	def flip(self):
		""" Show game screen on display
		Display works in SCALED mode: SDL scales it to window / full screen size,
		keeps proportions and centers the picture
		"""
		global screen

		self.display = pygame.display.get_surface()

		if self.shake_frames > 0:
			self.shake_frames -= 1
			offset = [random.randint(-3, 3), random.randint(-3, 3)]
			self.display.fill([0, 0, 0])
			self.display.blit(screen, offset)
		else:
			self.display.blit(screen, [0, 0])

		pygame.display.update()

	def endShip(self, player):
		""" Ship bonus time is over (player still on water can drive out) """
		player.ship = False
		player.ship_timer = None

	def setEnemiesShip(self, ship):
		self.enemies_ship = ship
		if not ship:
			self.enemies_ship_timer = None

	def shake(self, frames):
		""" Shake screen for some frames """
		if SCREEN_SHAKE:
			self.shake_frames = max(self.shake_frames, frames)

	def drawEffectTimers(self):
		""" Bars with time left: shield above players, enemy freeze (top edge, blue),
		players freeze (bottom edge, red), steel fortress walls (above castle) """

		global screen

		if not SHOW_EFFECT_TIMERS:
			return

		def bar(timer_uuid, rect, color):
			remaining = gtimer.remaining(timer_uuid) if timer_uuid else None
			if remaining == None:
				return
			width = int(rect[2] * float(remaining[0]) / remaining[1])
			pygame.draw.rect(screen, color, [rect[0], rect[1], max(width, 1), rect[3]])

		for player in players:
			if player.state == player.STATE_ALIVE and player.shielded:
				bar(player.shield_end_timer, [player.rect.left, player.rect.top - 4, 32, 2], (120, 200, 255))
			if player.state == player.STATE_ALIVE and player.ship:
				bar(player.ship_timer, [player.rect.left, player.rect.top - 7, 32, 2], (60, 140, 255))

		if self.timefreeze:
			bar(self.enemy_freeze_end_timer, [0, 0, 416, 3], (80, 160, 255))
		if self.players_frozen:
			bar(self.players_freeze_end_timer, [0, 413, 416, 3], (255, 80, 80))
		bar(self.fortress_end_timer, [176, 362, 64, 2], (200, 200, 200))

	def showStageScreen(self):
		""" Grey "STAGE N" screen before level starts, like on NES """

		global screen

		if STAGE_SCREEN_TIME <= 0:
			return

		self.stage_screen = True
		screen.fill([99, 99, 99])
		if self.mode == "endless":
			title = "WAVE " + str(self.stage - self.first_stage + 1)
		elif self.mode == "versus":
			title = "VERSUS"
		else:
			title = "STAGE " + str(self.stage)
		text = self.font.render(title, False, pygame.Color("black"))
		screen.blit(text, [(416 - text.get_width()) // 2, (416 - text.get_height()) // 2])

		for i in range(STAGE_SCREEN_TIME // 20):
			self.flip()
			self.delay(50)

		self.stage_screen = False

	def setFullScreen(self, fullScreen):
		size = width, height = 480, 416

		if fullScreen:
			screen = pygame.display.set_mode(size, SCALED | FULLSCREEN)
		else:
			screen = pygame.display.set_mode(size, SCALED)
			
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
		# all enemies can drive over water for some time
		elif bonus.bonus == bonus.BONUS_SHIP:
			self.setEnemiesShip(True)
			self.destroyTimer(self.enemies_ship_timer)
			self.enemies_ship_timer = gtimer.add(BONUS_SHIP_TIMEOUT, lambda :self.setEnemiesShip(False), 1)
		elif bonus.bonus == bonus.BONUS_HELMET:
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
					enemy.speed = DEFAULT_ENEMY_SPEED + DEFAULT_ENEMY_SPEED_FAST
				enemy.updateSuperpowers()
		# increase all enemy health by 200
		elif bonus.bonus == bonus.BONUS_TANK:
			for enemy in enemies:
				enemy.health += 200
				enemy.updateSprites()
		# freeze players for 10 seconds
		elif bonus.bonus == bonus.BONUS_TIMER:
			self.setPlayersFrozen(True)
			self.destroyTimer(self.players_freeze_end_timer)
			self.players_freeze_end_timer = gtimer.add(BONUS_TIMER_FREEZE_TIMEOUT, lambda :self.setPlayersFrozen(False), 1)
		
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
			self.shake(12)
			for enemy in enemies:
				if enemy.state not in (enemy.STATE_ALIVE, enemy.STATE_SPAWNING):
					continue
				explode_count += 1
				enemy.explode()
				if explode_count == 12:
					explode_count = 0
					break
		# shield player for 10 seconds
		# player can drive over water for some time
		elif bonus.bonus == bonus.BONUS_SHIP:
			if play_sounds:
				sounds["bonus"].play()
			player.ship = True
			self.destroyTimer(player.ship_timer)
			player.ship_timer = gtimer.add(BONUS_SHIP_TIMEOUT, lambda :self.endShip(player), 1)
		elif bonus.bonus == bonus.BONUS_HELMET:
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
			self.destroyTimer(self.enemy_freeze_end_timer)
			self.enemy_freeze_end_timer = gtimer.add(BONUS_TIMER_FREEZE_TIMEOUT, lambda :self.toggleEnemyFreeze(False), 1)
		
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
		# only one shield animation timer per player
		self.destroyTimer(player.timer_uuid_shield)
		player.timer_uuid_shield = None
		if shield:
			player.timer_uuid_shield = gtimer.add(100, lambda :player.toggleShieldImage())

		if shield and duration != None:
			if player.shield_end_timer:
				gtimer.destroy(player.shield_end_timer)
			player.shield_end_timer = gtimer.add(duration, lambda :self.shieldPlayer(player, False), 1)


	def delay(self, fps):
		""" Wait like clock.tick(fps), but keep handling quit and full screen keys
		Used on screens without their own event loop (scores)
		"""
		self.clock.tick(fps)
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				quit()
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					quit()
				elif self.isFullScreenKey(event):
					self.toggleFullScreen()

	def getFreeSpawningPosition(self):
		""" Next enemy spawning position not occupied by any tank
		@return list [x, y] or None if all positions are occupied
		"""
		global players, enemies, enemy_spawn_pos_index

		available_positions = [
			[0, 0],
			[12 * self.TILE_SIZE, 0],
			[24 * self.TILE_SIZE, 0]
		]

		for i in range(len(available_positions)):
			enemy_spawn_pos_index += 1
			enemy_spawn_pos_index %= len(available_positions)
			position = available_positions[enemy_spawn_pos_index]
			spawn_rect = pygame.Rect(position, [32, 32])

			occupied = False
			for tank in enemies + players:
				if tank.state != tank.STATE_DEAD and spawn_rect.colliderect(tank.rect):
					occupied = True
					break
			if not occupied:
				return position

		return None

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
		# don't spawn on top of other tanks, try again on next spawn timer
		position = self.getFreeSpawningPosition()
		if position == None:
			return
		enemy = Enemy(self.level, 1, position)

		if self.timefreeze:
			enemy.paused = True

		enemies.append(enemy)


	def respawnPlayer(self, player, clear_scores = False, superpowers = None):
		""" Respawn player """
		player.reset()
		player.paralised = self.players_frozen

		# default is read at call time: preset can change it
		player.superpowers = PLAYER_START_SUPERPOWER if superpowers == None else superpowers
		player.updateSuperpowers()

		if clear_scores:
			player.trophies = emptyTrophies()

		self.shieldPlayer(player, True, PLAYER_START_SHIELD_TIMEOUT)

	def gameOver(self):
		""" End game and return to menu """

		global play_sounds, sounds

		print("Game Over")
		self.deleteSavedGame()
		if play_sounds:
			for sound in sounds:
				sounds[sound].stop()
			sounds["gameover"].play()

		self.game_over_y = 416+40

		self.game_over = True
		gtimer.add(3000, lambda :self.endLevel(self.showScores), 1)

	def gameOverScreen(self):
		""" Show game over screen """

		global screen

		# stop game main loop (if any)
		self.running = False

		screen.fill([0, 0, 0])

		self.recordHiscores()

		screen.fill([0, 0, 0])
		self.writeInBricks("game", [125, 140])
		self.writeInBricks("over", [125, 220])
		self.flip()

		while 1:
			time_passed = self.clock.tick(50)
			self.flip()

			# gamepad A / Start returns to menu
			self.updateGamepads()
			for gamepad in self.gamepads:
				if gamepad.pressed("fire") or gamepad.pressed("start"):
					return self.showMenu
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						quit()
					if event.key == pygame.K_RETURN:
						return self.showMenu

	def showMenu(self):
		""" Show game menu
		Up / down selects menu item, Enter (gamepad A / Start) activates it
		"""

		global players, screen

		# stop game main loop (if any)
		self.running = False

		# clear all timers
		del gtimer.timers[:]

		# set current stage to 0
		self.stage = START_LEVEL - 1

		self.animateIntroScreen()

		while True:
			time_passed = self.clock.tick(50)

			# redraw every frame, otherwise menu stays invisible if display wasn't ready
			# during intro animation (happens when switching to full screen)
			self.flip()

			move = 0
			activate = False

			self.updateGamepads()
			for gamepad in self.gamepads:
				if gamepad.pressed("down"):
					move = 1
				elif gamepad.pressed("up"):
					move = -1
				elif gamepad.pressed("fire") or gamepad.pressed("start"):
					activate = True

			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						quit()
					elif self.isFullScreenKey(event):
						self.toggleFullScreen()
						self.drawIntroScreen()
					elif event.key == pygame.K_DOWN:
						move = 1
					elif event.key == pygame.K_UP:
						move = -1
					elif event.key == pygame.K_RETURN:
						activate = True

			items = self.menuItems()

			if move != 0:
				self.menu_index = (self.menu_index + move) % len(items)
				if items[self.menu_index][1] == "play":
					self.nr_of_players = items[self.menu_index][2]
				self.drawIntroScreen()

			if activate:
				label, action, argument = items[self.menu_index]
				if action == "play":
					self.mode = "campaign"
					self.nr_of_players = argument
					self.stage = START_LEVEL - 1
					del players[:]
					return self.nextLevel
				elif action == "editor":
					castle.rebuild()
					if self.showEditor() == "play":
						# play edited level
						self.mode = "campaign"
						self.nr_of_players = 1
						del players[:]
						return self.nextLevel
					self.drawIntroScreen()
				elif action == "versus":
					self.mode = "versus"
					self.nr_of_players = 2
					self.stage = 0
					self.versus_winner = None
					del players[:]
					return self.nextLevel
				elif action == "endless":
					self.mode = "endless"
					self.nr_of_players = argument
					self.stage = START_LEVEL - 1
					self.first_stage = START_LEVEL
					del players[:]
					return self.nextLevel
				elif action == "continue":
					if self.loadGame():
						del players[:]
						return self.nextLevel
					self.drawIntroScreen()
				elif action == "settings":
					self.showSettings()
					self.drawIntroScreen()

	# editor tiles: level character and name
	EDITOR_TILES = [(".", "ERASE"), ("#", "BRICK"), ("@", "STEEL"), ("~", "WATER"), ("%", "GRASS"), ("-", "ICE")]

	# 2x2 cells where tiles can't be placed: castle, enemy spawn points, players' start positions
	EDITOR_PROTECTED = [(12, 24), (0, 0), (12, 0), (24, 0), (8, 24), (16, 24), (12, 21)]

	def editorReadRows(self, level_nr):
		""" Level as 26 x 26 list of characters """
		try:
			with open(levelFile(level_nr), "r") as f:
				rows = f.read().split("\n")
		except IOError:
			rows = []
		rows = [(row + "." * 26)[:26] for row in rows[:26]]
		rows += ["." * 26] * (26 - len(rows))
		return [list(row) for row in rows]

	def editorProtected(self, col, row):
		for area_col, area_row in self.EDITOR_PROTECTED:
			if area_col <= col < area_col + 2 and area_row <= row < area_row + 2:
				return True
		return False

	def editorSave(self, level_nr, rows):
		""" Save edited level to custom levels directory """
		directory = dataFile(CUSTOM_LEVELS_DIR)
		try:
			if not os.path.isdir(directory):
				os.makedirs(directory)
			with open(os.path.join(directory, str(level_nr)), "w") as f:
				f.write("\n".join(["".join(row) for row in rows]))
		except (IOError, OSError):
			print("Can't save level")

	def editorDeleteCustom(self, level_nr):
		""" Remove custom level: original level is used again """
		try:
			os.remove(os.path.join(dataFile(CUSTOM_LEVELS_DIR), str(level_nr)))
		except OSError:
			pass

	def showEditor(self):
		""" Level editor
		arrows / mouse / gamepad - cursor, 1-5 - tile, 0 - eraser, space / left mouse / gamepad A - draw,
		right mouse / backspace - erase, [ ] - previous / next level, S - save,
		D - delete custom level (back to original), T - save and play, ESC - back to menu
		@return "play" to play edited level (self.stage is set), None to return to menu
		"""

		level_nr = 1
		rows = self.editorReadRows(level_nr)
		level = Level(level_nr)
		cursor = [2, 2]
		brush = 1
		modified = False
		changed = True

		while True:
			self.clock.tick(50)
			paint = None

			self.updateGamepads()
			for gamepad in self.gamepads:
				for name, dx, dy in (("up", 0, -1), ("down", 0, 1), ("left", -1, 0), ("right", 1, 0)):
					if gamepad.pressed(name):
						cursor = [max(0, min(25, cursor[0] + dx)), max(0, min(25, cursor[1] + dy))]
				if gamepad.held("fire"):
					paint = self.EDITOR_TILES[brush][0]
				if gamepad.pressed("start"):
					brush = (brush + 1) % len(self.EDITOR_TILES)

			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()

				elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
					x, y = event.pos
					if 0 <= x < 416 and 0 <= y < 416:
						cursor = [x // 16, y // 16]
						if event.type == pygame.MOUSEBUTTONDOWN:
							left, right = event.button == 1, event.button == 3
						else:
							left, right = event.buttons[0], event.buttons[2]
						if left:
							paint = self.EDITOR_TILES[brush][0]
						elif right:
							paint = "."

				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						return None
					elif self.isFullScreenKey(event):
						self.toggleFullScreen()
					elif event.key == pygame.K_UP:
						cursor[1] = max(0, cursor[1] - 1)
					elif event.key == pygame.K_DOWN:
						cursor[1] = min(25, cursor[1] + 1)
					elif event.key == pygame.K_LEFT:
						cursor[0] = max(0, cursor[0] - 1)
					elif event.key == pygame.K_RIGHT:
						cursor[0] = min(25, cursor[0] + 1)
					elif event.key == pygame.K_SPACE:
						paint = self.EDITOR_TILES[brush][0]
					elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
						paint = "."
					elif pygame.K_0 <= event.key <= pygame.K_5:
						brush = event.key - pygame.K_0
					elif event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
						# other level, unsaved changes are lost
						level_nr += 1 if event.key == pygame.K_RIGHTBRACKET else -1
						level_nr = (level_nr - 1) % 35 + 1
						rows = self.editorReadRows(level_nr)
						level = Level(level_nr)
						modified = False
						changed = True
					elif event.key == pygame.K_s:
						self.editorSave(level_nr, rows)
						modified = False
					elif event.key == pygame.K_d:
						self.editorDeleteCustom(level_nr)
						rows = self.editorReadRows(level_nr)
						modified = False
						changed = True
					elif event.key == pygame.K_t:
						self.editorSave(level_nr, rows)
						self.stage = level_nr - 1
						return "play"

			col, row = cursor
			if paint != None and not self.editorProtected(col, row) and rows[row][col] != paint:
				rows[row][col] = paint
				modified = True
				changed = True

			if changed:
				level.loadRows(["".join(r) for r in rows])
				level.updateObstacleRects()
				changed = False

			self.editorDraw(level, level_nr, cursor, brush, modified)

	def editorDraw(self, level, level_nr, cursor, brush, modified):
		global screen

		screen.fill([0, 0, 0])
		level.draw()
		castle.draw()

		grid_color = (40, 40, 40)
		for i in range(27):
			pygame.draw.line(screen, grid_color, [i * 16, 0], [i * 16, 416])
			pygame.draw.line(screen, grid_color, [0, i * 16], [416, i * 16])

		for col, row in self.EDITOR_PROTECTED:
			pygame.draw.rect(screen, (120, 30, 30), [col * 16, row * 16, 32, 32], 1)

		pygame.draw.rect(screen, (255, 200, 0), [cursor[0] * 16, cursor[1] * 16, 16, 16], 1)

		# sidebar: level, brush, hints
		screen.fill([100, 100, 100], pygame.Rect([416, 0], [64, 416]))
		font = Label.getFont()
		black = pygame.Color("black")

		screen.blit(font.render("EDITOR", False, black), [420, 8])
		screen.blit(font.render("LVL %d%s" % (level_nr, "*" if modified else ""), False, black), [420, 24])

		tile_images = {"#": level.tile_brick, "@": level.tile_steel, "~": level.tile_water, "%": level.tile_grass, "-": level.tile_froze}
		char, name = self.EDITOR_TILES[brush]
		if char in tile_images:
			screen.blit(tile_images[char], [440, 44])
		else:
			pygame.draw.rect(screen, black, [440, 44, 16, 16], 1)
		screen.blit(font.render(name, False, black), [420, 66])

		hints = ["1-5 TILE", "0 ERASE", "SPC DRAW", "S SAVE", "D RESET", "[ ] LVL", "T TEST", "ESC MENU"]
		for i, hint in enumerate(hints):
			screen.blit(font.render(hint, False, black), [418, 100 + i * 14])

		self.flip()

	def castles(self):
		""" Player's castle, in versus mode also castle of player 2 """
		return [target for target in (castle, castle2) if target != None]

	def castleRects(self):
		return [target.rect for target in self.castles()]

	def spawnVersusBonus(self):
		""" Versus: random bonus useful in players' duel """
		if self.game_paused or self.game_over:
			return
		bonus = Bonus(self.level)
		bonus.setType(random.choice([bonus.BONUS_STAR, bonus.BONUS_HELMET, bonus.BONUS_TANK, bonus.BONUS_SHIP]))
		bonuses.append(bonus)
		if play_sounds:
			sounds["bonusnew"].play()
		gtimer.add(max(BONUS_SPAWN_TIMEOUT - BONUS_BLINK_TIME, 1), lambda :bonus.startBlinking(), 1)
		gtimer.add(BONUS_SPAWN_TIMEOUT, lambda :bonuses.remove(bonus), 1)

	def versusOver(self, winner):
		""" Versus match is over: show "game over", then result """
		if self.game_over:
			return
		if play_sounds:
			for sound in sounds:
				sounds[sound].stop()
			sounds["gameover"].play()
		self.versus_winner = winner
		self.game_over_y = 416+40
		self.game_over = True
		gtimer.add(3000, lambda :self.endLevel(self.showVersusResult), 1)

	def showVersusResult(self):
		""" Versus result screen: winner and kills. Any key / gamepad button returns to menu """
		global screen

		self.running = False
		del gtimer.timers[:]

		screen.fill([0, 0, 0])
		white = pygame.Color("white")
		yellow = pygame.Color(255, 200, 0)

		def center(text, y, color):
			surface = self.font.render(text, False, color)
			screen.blit(surface, [(480 - surface.get_width()) // 2, y])

		center(["I", "II"][self.versus_winner] + "-PLAYER WINS", 150, yellow)
		center("KILLS  I: %d  II: %d" % (players[0].versus_kills, players[1].versus_kills), 200, white)
		center("ENTER - MENU", 300, white)

		for frame in range(10000 // 20):
			self.flip()
			self.clock.tick(50)
			self.updateGamepads()
			for gamepad in self.gamepads:
				if gamepad.pressed("fire") or gamepad.pressed("start"):
					return self.showMenu
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						quit()
					return self.showMenu

		return self.showMenu

	def loadHiscores(self):
		""" Hiscore tables with names
		@return {"campaign": [[name, score], ...], "endless": [...]}, best score first
		"""
		tables = {"campaign": [], "endless": []}
		try:
			with open(dataFile(HISCORES_FILE), "r") as f:
				data = json.load(f)
			for mode in tables:
				tables[mode] = [[str(entry[0])[:3], int(entry[1])] for entry in data.get(mode, [])][:HISCORES_COUNT]
		except (IOError, ValueError, TypeError, AttributeError, IndexError):
			pass
		return tables

	def saveHiscores(self, tables):
		try:
			with open(dataFile(HISCORES_FILE), "w") as f:
				json.dump(tables, f, indent=1)
		except IOError:
			print("Can't save hiscores")

	def qualifiesForHiscores(self, table, score):
		return score > 0 and (len(table) < HISCORES_COUNT or score > table[-1][1])

	def recordHiscores(self):
		""" After game over players with good score enter their names, then hiscore table is shown """
		tables = self.loadHiscores()
		if self.mode not in tables:
			return
		table = tables[self.mode]

		entered = False
		for player_nr, player in enumerate(players):
			if self.qualifiesForHiscores(table, player.score):
				table.append([self.enterName(player_nr, player.score), player.score])
				# stable sort: earlier entry with the same score stays higher
				table.sort(key=lambda entry: -entry[1])
				del table[HISCORES_COUNT:]
				entered = True

		if entered:
			self.saveHiscores(tables)
			self.showHiscores(self.mode, 5000)

	def enterName(self, player_nr, score):
		""" Arcade style name entry
		up / down - change letter, left / right - move cursor, letter keys - type, Enter / fire - done
		@return string 3 characters
		"""
		letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
		name = [0, 0, 0]
		position = 0

		while True:
			self.clock.tick(50)
			self.drawNameEntry(player_nr, score, "".join([letters[i] for i in name]), position)

			change = 0
			move = 0
			done = False

			self.updateGamepads()
			for gamepad in self.gamepads:
				if gamepad.pressed("up"):
					change = 1
				elif gamepad.pressed("down"):
					change = -1
				elif gamepad.pressed("right"):
					move = 1
				elif gamepad.pressed("left"):
					move = -1
				elif gamepad.pressed("fire") or gamepad.pressed("start"):
					done = True

			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()
				if event.type != pygame.KEYDOWN:
					continue
				if event.key == pygame.K_ESCAPE:
					quit()
				elif self.isFullScreenKey(event):
					self.toggleFullScreen()
				elif event.key == pygame.K_RETURN:
					done = True
				elif event.key == pygame.K_UP:
					change = 1
				elif event.key == pygame.K_DOWN:
					change = -1
				elif event.key == pygame.K_RIGHT:
					move = 1
				elif event.key in (pygame.K_LEFT, pygame.K_BACKSPACE):
					move = -1
				elif event.unicode and event.unicode.upper() in letters:
					name[position] = letters.index(event.unicode.upper())
					move = 1

			name[position] = (name[position] + change) % len(letters)
			position = max(0, min(len(name) - 1, position + move))

			if done:
				return "".join([letters[i] for i in name])

	def drawNameEntry(self, player_nr, score, name, position):
		global screen

		screen.fill([0, 0, 0])
		white = pygame.Color("white")
		yellow = pygame.Color(255, 200, 0)

		def center(text, y, color):
			surface = self.font.render(text, False, color)
			screen.blit(surface, [(480 - surface.get_width()) // 2, y])

		center("NEW HIGH SCORE", 80, yellow)
		center(["I", "II", "III"][player_nr] + "-PLAYER  " + str(score), 120, white)
		center("ENTER YOUR NAME", 180, white)

		# big letters with cursor under current one
		x = (480 - 3 * 40) // 2
		for i, letter in enumerate(name):
			surface = pygame.transform.scale(self.font.render(letter, False, white), [32, 32])
			screen.blit(surface, [x + i * 40, 220])
			if i == position:
				pygame.draw.rect(screen, yellow, [x + i * 40, 256, 32, 4])

		center("ENTER - DONE", 320, white)
		self.flip()

	def showHiscores(self, mode, duration):
		""" Show hiscore table for duration ms or until key / gamepad button is pressed """
		global screen

		table = self.loadHiscores().get(mode, [])
		screen.fill([0, 0, 0])
		white = pygame.Color("white")
		yellow = pygame.Color(255, 200, 0)

		title = self.font.render("HIGH SCORES - " + mode.upper(), False, yellow)
		screen.blit(title, [(480 - title.get_width()) // 2, 40])
		for i, entry in enumerate(table):
			row = "%2d. %-3s %8d" % (i + 1, entry[0], entry[1])
			screen.blit(self.font.render(row, False, white), [96, 90 + i * 28])

		for frame in range(duration // 20):
			self.flip()
			self.clock.tick(50)
			self.updateGamepads()
			for gamepad in self.gamepads:
				if gamepad.pressed("fire") or gamepad.pressed("start"):
					return
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						quit()
					return

	def saveGame(self):
		""" Save progress after completed stage: stage, number of players, preset,
		players' score, lives and superpowers
		"""
		data = {
			"stage": self.stage,
			"nr_of_players": self.nr_of_players,
			"preset": CURRENT_PRESET,
			"players": [{
				"score": player.score,
				"lives": player.lives,
				"superpowers": player.superpowers,
				"next_extra_life": player.next_extra_life
			} for player in players],
		}
		try:
			with open(dataFile(SAVEGAME_FILE), "w") as f:
				json.dump(data, f, indent=1)
		except IOError:
			print("Can't save game")

	def loadGame(self):
		""" Load saved progress, game continues from the stage after saved one
		@return boolean Whether game was loaded
		"""
		try:
			with open(dataFile(SAVEGAME_FILE), "r") as f:
				data = json.load(f)
			stage = int(data["stage"])
			nr_of_players = int(data["nr_of_players"])
			stats = [{
				"score": int(player["score"]),
				"lives": int(player["lives"]),
				"superpowers": int(player["superpowers"]),
				"next_extra_life": int(player.get("next_extra_life", EXTRA_LIFE_SCORE))
			} for player in data["players"]]
		except (IOError, ValueError, KeyError, TypeError, AttributeError):
			print("Can't load saved game")
			return False

		if nr_of_players not in (1, 2, 3) or len(stats) != nr_of_players or stage < 0:
			print("Saved game is broken")
			return False

		if data.get("preset") in PRESETS:
			applyPreset(data["preset"])
		self.mode = "campaign"
		self.stage = stage
		self.nr_of_players = nr_of_players
		self.loaded_players_stats = stats
		return True

	def deleteSavedGame(self):
		""" Saved game is useless after game over """
		try:
			os.remove(dataFile(SAVEGAME_FILE))
		except OSError:
			pass

	def menuItems(self):
		""" Main menu items: [label, action, argument] """
		items = [
			["1 PLAYER", "play", 1],
			["2 PLAYERS", "play", 2],
			["3 PLAYERS", "play", 3],
		]
		# game saved after completed stage
		if os.path.isfile(dataFile(SAVEGAME_FILE)):
			items.append(["CONTINUE", "continue", None])
		items.append(["ENDLESS 1P", "endless", 1])
		items.append(["ENDLESS 2P", "endless", 2])
		items.append(["VERSUS", "versus", 2])
		items.append(["LEVEL EDITOR", "editor", None])
		items.append(["SETTINGS", "settings", None])
		return items

	def settingsItems(self):
		""" Settings screen items: dicts with label, value, type (and player / control for controls) """
		items = [
			{"label": "DIFFICULTY", "value": CURRENT_PRESET or "CUSTOM", "type": "preset"},
			{"label": "SOUND", "value": "ON" if play_sounds else "OFF", "type": "sound"},
			{"label": "FULL SCREEN", "value": "ON" if self.is_fullscreen else "OFF", "type": "fullscreen"},
			{"label": "START LEVEL", "value": str(START_LEVEL), "type": "level"},
		]
		control_names = ["FIRE", "UP", "RIGHT", "DOWN", "LEFT"]
		for player_nr in range(len(PLAYER_CONTROLS)):
			for control in range(5):
				items.append({
					"label": "P%d %s" % (player_nr + 1, control_names[control]),
					"value": pygame.key.name(PLAYER_CONTROLS[player_nr][control]).upper(),
					"type": "control", "player": player_nr, "control": control
				})
		items.append({"label": "RESET CONTROLS", "value": "", "type": "reset"})
		items.append({"label": "BACK", "value": "", "type": "back"})
		return items

	def showSettings(self):
		""" Settings screen
		Up / down - select, left / right / Enter - change value, Enter on control - press new key
		(ESC cancels), ESC or BACK - return to menu. Settings are saved immediately.
		"""

		selected = 0
		waiting_key = False

		while True:
			self.clock.tick(50)
			items = self.settingsItems()
			self.drawSettings(items, selected, waiting_key)

			move = 0
			change = 0

			self.updateGamepads()
			if not waiting_key:
				for gamepad in self.gamepads:
					if gamepad.pressed("down"):
						move = 1
					elif gamepad.pressed("up"):
						move = -1
					elif gamepad.pressed("right") or gamepad.pressed("fire"):
						change = 1
					elif gamepad.pressed("left"):
						change = -1
					elif gamepad.pressed("start"):
						return

			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()
				if event.type != pygame.KEYDOWN:
					continue
				if waiting_key:
					# ESC cancels, Enter is reserved for pause
					if event.key not in (pygame.K_ESCAPE, pygame.K_RETURN):
						self.setControl(items[selected]["player"], items[selected]["control"], event.key)
					waiting_key = False
				elif event.key == pygame.K_ESCAPE:
					return
				elif self.isFullScreenKey(event):
					self.toggleFullScreen()
					saveSettings(self.is_fullscreen)
				elif event.key == pygame.K_DOWN:
					move = 1
				elif event.key == pygame.K_UP:
					move = -1
				elif event.key == pygame.K_RIGHT:
					change = 1
				elif event.key == pygame.K_LEFT:
					change = -1
				elif event.key == pygame.K_RETURN:
					change = 1

			if move != 0:
				selected = (selected + move) % len(items)
			elif change != 0:
				kind = items[selected]["type"]
				if kind == "back":
					return
				elif kind == "control":
					waiting_key = True
				else:
					self.changeSetting(kind, change)

	def changeSetting(self, kind, change):
		""" Change setting value and save settings """

		global play_sounds, START_LEVEL, PLAYER_CONTROLS

		if kind == "preset":
			names = ["CLASSIC", "GOOD", "EXTREME"]
			index = names.index(CURRENT_PRESET) if CURRENT_PRESET in names else -change
			applyPreset(names[(index + change) % len(names)])
		elif kind == "sound":
			# sounds couldn't be loaded: nothing to switch on
			if sounds:
				play_sounds = not play_sounds
				if not play_sounds:
					pygame.mixer.stop()
		elif kind == "fullscreen":
			self.toggleFullScreen()
		elif kind == "level":
			START_LEVEL = (START_LEVEL - 1 + change) % 35 + 1
			self.stage = START_LEVEL - 1
		elif kind == "reset":
			PLAYER_CONTROLS = [list(controls) for controls in DEFAULT_PLAYER_CONTROLS]

		saveSettings(self.is_fullscreen)

	def setControl(self, player_nr, control, key):
		""" Assign key to player's control. Control already using this key gets the old key (swap) """
		old_key = PLAYER_CONTROLS[player_nr][control]
		for controls in PLAYER_CONTROLS:
			for i in range(len(controls)):
				if controls[i] == key:
					controls[i] = old_key
		PLAYER_CONTROLS[player_nr][control] = key
		saveSettings(self.is_fullscreen)

	def drawSettings(self, items, selected, waiting_key):
		""" Draw settings screen """

		global screen

		screen.fill([0, 0, 0])
		white = pygame.Color("white")
		yellow = pygame.Color(255, 200, 0)

		title = self.font.render("SETTINGS", False, white)
		screen.blit(title, [(480 - title.get_width()) // 2, 16])

		for i, item in enumerate(items):
			y = 52 + i * 20
			color = yellow if i == selected else white
			if i == selected:
				screen.blit(self.font.render(">", False, yellow), [16, y])
			screen.blit(self.font.render(item["label"], False, color), [40, y])
			value = "PRESS KEY" if i == selected and waiting_key else item["value"]
			if value:
				screen.blit(self.font.render(value[:10], False, color), [288, y])

		self.flip()

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
			player.controls = list(PLAYER_CONTROLS[0])
			players.append(player)

			# second player
			if self.nr_of_players >= 2:
				x = 16 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
				y = 24 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
				direction = self.DIR_UP
				# versus: player 2 starts at the top, next to own castle
				if self.mode == "versus":
					y = 0
					direction = self.DIR_DOWN
				player = Player(
					self.level, 0, [x, y], direction, (6*S_SIZE*T_SIZE, 0, 16*2, 16*2), 2
				)
				player.controls = list(PLAYER_CONTROLS[1])
				players.append(player)

			# third player
			if self.nr_of_players == 3:
				x = 12 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
				y = 21 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
				player = Player(
					self.level, 0, [x, y], self.DIR_UP, (16*2, 0, 16*2, 16*2), 3
				)
				# third player uses gamepad only
				player.controls = []
				players.append(player)

		# continue saved game
		if self.loaded_players_stats:
			for player, stats in zip(players, self.loaded_players_stats):
				player.score = stats["score"]
				player.lives = stats["lives"]
				player.superpowers = stats["superpowers"]
				player.next_extra_life = stats["next_extra_life"]
			self.loaded_players_stats = None

		for player in players:
			player.level = self.level
			self.respawnPlayer(player, True, player.superpowers)

		self.assignGamepads()

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

		# 2+ players: player who destroyed most tanks on this stage gets bonus points (like on NES)
		kills_bonus_player = None
		if self.nr_of_players >= 2 and TWO_PLAYER_KILLS_BONUS > 0 and not self.game_over:
			kills = [sum(player.trophies.values()) - player.trophies["bonus"] for player in players]
			best_kills = max(kills)
			if best_kills > 0 and kills.count(best_kills) == 1:
				kills_bonus_player = kills.index(best_kills)
				players[kills_bonus_player].score += TWO_PLAYER_KILLS_BONUS

		hiscore = self.loadHiscore()

		# update hiscore if needed
		best_score = max([player.score for player in players])
		if best_score > hiscore:
			hiscore = best_score
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

		if self.nr_of_players >= 2:
			screen.blit(self.font.render("II-PLAYER", False, purple), [310, 95])

			#player 2 global score
			screen.blit(self.font.render(str(players[1].score).rjust(8), False, pink), [325, 125])

		# tanks and arrows
		for i in range(4):
			screen.blit(img_tanks[i], [226, 160+(i*45)])
			screen.blit(img_arrows[0], [206, 168+(i*45)])
			if self.nr_of_players >= 2:
				screen.blit(img_arrows[1], [258, 168+(i*45)])

		screen.blit(self.font.render("TOTAL", False, white), [70, 335])

		# total underline
		pygame.draw.line(screen, white, [170, 330], [307, 330], 4)

		self.flip()

		self.delay(2)

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
				self.flip()
				self.delay(interval)

			if self.nr_of_players >= 2:
				tanks = players[1].trophies["enemy"+str(i)]

				for n in range(tanks+1):

					if n > 0 and play_sounds:
						sounds["score"].play()

					screen.blit(self.font.render(str(n-1).rjust(2), False, black), [277, 168+(i*45)])
					screen.blit(self.font.render(str(n).rjust(2), False, white), [277, 168+(i*45)])

					screen.blit(self.font.render(str((n-1) * (i+1) * 100).rjust(4)+" PTS", False, black), [325, 168+(i*45)])
					screen.blit(self.font.render(str(n * (i+1) * 100).rjust(4)+" PTS", False, white), [325, 168+(i*45)])

					self.flip()
					self.delay(interval)

			self.delay(interval-2)

		# total tanks
		tanks = sum([i for i in players[0].trophies.values()]) - players[0].trophies["bonus"]
		screen.blit(self.font.render(str(tanks).rjust(2), False, white), [170, 335])
		if self.nr_of_players >= 2:
			tanks = sum([i for i in players[1].trophies.values()]) - players[1].trophies["bonus"]
			screen.blit(self.font.render(str(tanks).rjust(2), False, white), [277, 335])

		# third player: short table, there is no room for detailed one
		if self.nr_of_players == 3:
			screen.blit(self.font.render("III-PLAYER", False, purple), [25, 375])
			screen.blit(self.font.render(str(players[2].score).rjust(8), False, pink), [325, 375])
			kills = [players[2].trophies["enemy" + str(i)] for i in range(4)]
			kills_text = "KILLS " + " ".join([str(k) for k in kills]) + " = " + str(sum(kills))
			screen.blit(self.font.render(kills_text, False, white), [25, 395])

		if kills_bonus_player != None:
			player_names = ["I", "II", "III"]
			bonus_text = self.font.render(player_names[kills_bonus_player] + "-PLAYER BONUS " + str(TWO_PLAYER_KILLS_BONUS), False, white)
			screen.blit(bonus_text, [(480 - bonus_text.get_width()) // 2, 355])

		self.flip()

		# do nothing for 2 seconds
		self.delay(1)
		self.delay(1)

		if self.game_over:
			return self.gameOverScreen
		else:
			self.saveGame()
			return self.nextLevel


	def draw(self):
		global screen, castle, players, enemies, bullets, bonuses

		screen.fill([0, 0, 0])

		self.level.draw([self.level.TILE_EMPTY, self.level.TILE_BRICK, self.level.TILE_STEEL, self.level.TILE_FROZE, self.level.TILE_WATER])

		for target in self.castles():
			target.draw()

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

		self.drawEffectTimers()

		if self.game_paused:
			screen.blit(self.im_pause, [176, 188])

		if self.game_over:
			if self.game_over_y > 188:
				self.game_over_y -= 4
			screen.blit(self.im_game_over, [176, self.game_over_y]) # 176=(416-64)/2

		self.drawSidebar()

		if DEBUG_DRAW_MESH:
			self.drawMesh()

		self.flip()

	def drawSidebar(self):

		global screen, players, enemies

		x = 416
		y = 0
		screen.fill([100, 100, 100], pygame.Rect([416, 0], [64, 416]))

		xpos = x + 16
		ypos = y + 16

		# draw enemy lives (limited so icons don't overlap players' lives)
		max_icons = 20
		for n in range(min(len(self.level.enemies_left), max_icons)):
			screen.blit(self.enemy_life_image, [xpos, ypos])
			if n % 2 == 1:
				xpos = x + 16
				ypos+= 17
			else:
				xpos += 17

		hidden_enemies = len(self.level.enemies_left) - max_icons
		if hidden_enemies > 0 and pygame.font.get_init():
			screen.blit(self.font.render("+"+str(hidden_enemies), False, pygame.Color('black')), [x+4, ypos])

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

		items = self.menuItems()
		self.menu_index = min(self.menu_index, len(items) - 1)

		if pygame.font.get_init():

			hiscore = self.loadHiscore()

			screen.blit(self.font.render("HI- "+str(hiscore), True, pygame.Color('white')), [170, 35])

			for i, item in enumerate(items):
				screen.blit(self.font.render(item[0], True, pygame.Color('white')), [165, 228 + i * 20])

		# selected item marker
		marker = self.player_image if self.menu_index == 0 else self.player_image_green
		screen.blit(marker, [125, 223 + self.menu_index * 20])

		self.writeInBricks("battle", [65, 80])
		self.writeInBricks("city", [129, 160])

		if put_on_surface:
			self.flip()

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
			self.flip()
			y -= 5

		screen.blit(screen_cp, [0, 0])
		self.flip()


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
		filename = dataFile(".hiscore")
		if (not os.path.isfile(filename)):
			return 20000

		try:
			with open(filename, "r") as f:
				hiscore = int(f.read())
		except (IOError, ValueError):
			print("Can't read hi-score")
			return 20000

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
			f = open(dataFile(".hiscore"), "w")
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

		gtimer.add(LEVEL_FINISH_TIMEOUT, lambda :self.endLevel(self.nextLevel if self.mode == "endless" else self.showScores), 1)

		print("Stage "+str(self.stage)+" completed")

	def endLevel(self, next_action):
		""" Stop main game loop and schedule next screen
		Screens are switched from main loop (not from timer callbacks) to avoid recursion
		"""
		self.next_action = next_action
		self.running = False

	def playerFire(self, player):
		""" Fire player's bullet if bullet quota allows it """
		if player.fire():
			player.last_fire_time = pygame.time.get_ticks()
			if play_sounds:
				sounds["fire"].play()

	def setPlayersFrozen(self, freeze = True):
		""" Freeze/defreeze players by enemy timer bonus """
		self.players_frozen = freeze
		if not self.game_paused:
			self.togglePlayersFreeze(freeze)

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
			# keep players frozen if enemy timer bonus is still active
			self.togglePlayersFreeze(self.players_frozen)
			# keys could be pressed/released during pause
			keys = pygame.key.get_pressed()
			for player in players:
				if player.controls:
					player.fire_pressed = bool(keys[player.controls[0]])
					player.pressed = [bool(keys[key]) for key in player.controls[1:]]
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

		level_enemies = [0]*enemies_l[0] + [1]*enemies_l[1] + [2]*enemies_l[2] + [3]*enemies_l[3]

		# versus: players fight each other, no enemies
		if self.mode == "versus":
			level_enemies = []

		# endless mode: every wave has more fast and armor tanks
		if self.mode == "endless":
			wave = self.stage - self.first_stage
			level_enemies += [1] * (wave // 2) + [3] * (wave // 3)
		# new enemies: some basic tanks become stealth tanks, some power tanks become mortars
		level_number = self.stage - self.first_stage + 1 if self.mode == "endless" else self.stage
		new_enemies = ENABLE_NEW_ENEMIES and self.mode != "versus"
		if new_enemies and level_number >= NEW_ENEMIES_FROM_STAGE:
			for old_type, new_type, count in ((Enemy.TYPE_BASIC, Enemy.TYPE_STEALTH, 3), (Enemy.TYPE_POWER, Enemy.TYPE_MORTAR, 2)):
				for i in range(len(level_enemies)):
					if count > 0 and level_enemies[i] == old_type:
						level_enemies[i] = new_type
						count -= 1

		if add:
			self.level.enemies_left += level_enemies
		else:
			self.level.enemies_left = level_enemies
		random.shuffle(self.level.enemies_left)

		# enemies are taken from the end of the list: boss comes last
		if new_enemies and not add and level_number % BOSS_EVERY_STAGES == 0:
			self.level.enemies_left.insert(0, Enemy.TYPE_BOSS)


	def nextLevel(self):
		""" Start next level """

		global castle, castle2, players, bullets, bonuses, play_sounds, sounds

		del bullets[:]
		del enemies[:]
		del bonuses[:]
		del labels[:]
		castle.rebuild()

		# versus: second castle at the top for player 2
		castle2 = None
		if self.mode == "versus":
			castle2 = Castle()
			castle2.rect.topleft = (12 * self.TILE_SIZE, 0)
			castle2.owner = 1
		del gtimer.timers[:]

		# load level
		self.stage += 1
		self.level = Level("versus" if self.mode == "versus" else self.stage)

		self.showStageScreen()
		self.timefreeze = False
		self.enemy_freeze_end_timer = None
		self.players_freeze_end_timer = None
		self.fortress_end_timer = None
		self.players_frozen = False
		self.enemies_ship = False
		self.enemies_ship_timer = None
		self.next_action = None

		# set number of enemies by types (basic, fast, power, armor) according to level
		self.loadLevelEnemies(False)

		if play_sounds:
			sounds["start"].play()
			gtimer.add(4330, lambda :sounds["bg"].play(-1), 1)

		self.reloadPlayers()

		gtimer.add(ENEMY_SPAWN_TIMEOUT, lambda :self.spawnEnemy())
		if self.mode == "versus":
			gtimer.add(VERSUS_BONUS_TIMEOUT, lambda :self.spawnVersusBonus())

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
			self.updateGamepads()

			if self.game_paused and not DEBUG_UNFREEZE_PLAYERS_ON_PAUSE:
				for event in pygame.event.get():
					if event.type == pygame.QUIT:
						quit()
					elif event.type == pygame.KEYDOWN and not self.game_over and self.active:
						if event.key == pygame.K_ESCAPE:
							quit()
						if self.isFullScreenKey(event):
							self.toggleFullScreen()
						elif event.key == pygame.K_RETURN:
							self.pause()
						if event.key == pygame.K_v:
							self.toggleDebugMode()
				
				# gamepad Start unpauses
				for gamepad in self.gamepads:
					if gamepad.pressed("start"):
						self.pause()
						break

				self.draw()
				continue

			for event in pygame.event.get():
				if event.type == pygame.MOUSEBUTTONDOWN:
					pass
				elif event.type == pygame.QUIT:
					quit()
				# ESC works always, also during "game over" animation
				elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					quit()
				elif event.type == pygame.KEYDOWN and not self.game_over and self.active:

					# Controls: ESC - quit, Enter - pause, p - debug enemy freeze, v - debug mesh,
					# ctrl+f / cmd+f / alt+enter - full screen, m  - mute sounds, b - borrow life from active player
					# toggle game quit
					if event.key == pygame.K_ESCAPE:
						quit()
					# toggle full screen
					if self.isFullScreenKey(event):
						self.toggleFullScreen()
					# toggle pause
					elif event.key == pygame.K_RETURN:
						self.pause()
					# toggle debug freeze
					if event.key == pygame.K_p:
						self.toggleEnemyFreeze(not self.timefreeze)
					# toggle debug mesh
					if event.key == pygame.K_v:
						self.toggleDebugMode()
					# toggle sounds
					if event.key == pygame.K_m:
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
									break

					for player in players:
						if player.state == player.STATE_ALIVE:
							try:
								index = player.controls.index(event.key)
							except:
								pass
							else:
								if index == 0:
									player.fire_pressed = True
									self.playerFire(player)
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
								if index == 0:
									player.fire_pressed = False
								elif index == 1:
									player.pressed[0] = False
								elif index == 2:
									player.pressed[1] = False
								elif index == 3:
									player.pressed[2] = False
								elif index == 4:
									player.pressed[3] = False

			self.applyGamepads()

			for player in players:
				if player.state == player.STATE_ALIVE and not self.game_over and self.active:
					# keyboard or gamepad
					pressed = [player.pressed[i] or player.pad_pressed[i] for i in range(4)]
					fire_pressed = player.fire_pressed or player.pad_fire

					# auto fire while fire button is held: shoot as soon as a bullet slot is free
					if fire_pressed and pygame.time.get_ticks() - player.last_fire_time >= PLAYER_AUTO_FIRE_DELAY:
						self.playerFire(player)

					if True in pressed:
						# first pressed in order: up, right, down, left
						direction = [self.DIR_UP, self.DIR_RIGHT, self.DIR_DOWN, self.DIR_LEFT][pressed.index(True)]
						player.move(direction)
						# on ice tank keeps sliding after button is released
						player.slide = ICE_SLIDE_DISTANCE if player.onIce() else 0
					elif player.slide > 0:
						if player.slide == ICE_SLIDE_DISTANCE and play_sounds:
							sounds["ice"].play()
						if player.move(player.direction):
							player.slide -= player.speed
						else:
							player.slide = 0
				player.update(time_passed)

			for enemy in enemies[:]:
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
					# extra life every EXTRA_LIFE_SCORE points
					if EXTRA_LIFE_SCORE > 0:
						while player.score >= player.next_extra_life:
							player.lives += 1
							player.next_extra_life += EXTRA_LIFE_SCORE
							if play_sounds:
								sounds["life"].play()

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
						elif self.mode == "versus":
							# versus: player without lives loses
							self.versusOver(1 - players.index(player))
						else:
							total_lives = 0
							for plr in players:
								total_lives += plr.lives
							if total_lives <= 0:
									self.gameOver()

			for bullet in bullets[:]:
				if bullet.state == bullet.STATE_REMOVED:
					bullets.remove(bullet)
				else:
					bullet.update()

			for bonus in bonuses[:]:
				if bonus.active == False:
					bonuses.remove(bonus)

			for label in labels[:]:
				if not label.active:
					labels.remove(label)

			if not self.game_over:
				if self.mode == "versus":
					# destroyed castle loses
					for target in self.castles():
						if not target.active:
							self.versusOver(1 - target.owner)
							break
				elif not castle.active:
					self.gameOver()

			gtimer.update(time_passed)

			self.draw()

		return self.next_action

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

	loadSettings()

	game = Game()
	castle = Castle()
	castle2 = None

	# each screen returns the next one to show
	action = game.showMenu
	while action:
		action = action()
