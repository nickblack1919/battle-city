# coding=utf-8
""" Battle City settings

Values can be changed here. Difficulty presets (PRESETS) override some of them,
settings screen changes and saves others (.settings.json).
"""

import os, pygame, time, random, uuid, sys, argparse, json
from pygame.locals import *

# NES TIMING: values below are taken from NES version (disassembly), which runs at 60 fps
NES_FPS = 60
GAME_FRAME_TIMING = 50	# frames per second of this game

def nesFrames(frames):
	""" Duration of n NES frames in ms """
	return int(round(frames * 1000.0 / NES_FPS))

# NES pixels are 2x smaller than here: speed of 1 NES px per NES frame in px per frame of this game
NES_PX_PER_FRAME = 2.0 * NES_FPS / GAME_FRAME_TIMING


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
BONUS_FREQ = 4 # enemy tanks carrying a bonus: every n-th ...
BONUS_TANK_OFFSET = 3	# ... when n enemies left before its spawn % BONUS_FREQ == offset (NES: 7 and 3 = 4th, 11th, 18th tank)
ALLOW_MULTI_BONUS = True
ENEMY_PICKUP_BONUSES = True
FRIENDLY_FIRE = False	# 2 players: hit partner is stunned (can't move) for FRIENDLY_FIRE_STUN_TIME
FRIENDLY_FIRE_STUN_TIME = nesFrames(267)	# NES: 200 counts, 3 of 4 frames = 4.4 s
MAX_ACTIVE_ENEMIES = 4
MAX_ACTIVE_ENEMIES_2_PLAYERS = 10
MAX_ACTIVE_ENEMIES_3_PLAYERS = 12
ENEMY_SPAWN_TIMEOUT = 1000	# ms between enemy spawns, None - NES formula (depends on stage and players)
LEVEL_FINISH_TIMEOUT = nesFrames(128)	# after the last enemy is destroyed, NES: 2.1 s
GAME_OVER_TIMEOUT = nesFrames(256)	# "game over" before scores screen, NES: 4.3 s
BONUS_TIMER_FREEZE_TIMEOUT = nesFrames(640)	# NES: 10 x 64 frames = 10.7 s
BONUS_FORTRESS_WALLS_TIMEOUT = nesFrames(1280)	# NES: 20 x 64 frames = 21.3 s
FORTRESS_BLINK_TIME = nesFrames(192)	# steel walls blink steel / brick during last 3.2 s
FORTRESS_BLINK_INTERVAL = nesFrames(16)
BONUS_PLAYER_SHIELD_TIMEOUT = nesFrames(640)	# helmet, NES: 10.7 s
BONUS_PLAYER_HIDDEN_TIMEOUT = 10000
BONUS_SPAWN_TIMEOUT = 20000	# bonus disappears after n ms, 0 - stays until picked up (NES)
BONUS_BLINK_INTERVAL = nesFrames(8)	# NES: 8 frames visible, 8 hidden
BONUS_PICKUP_LABEL_TIME = nesFrames(50)	# "500" after bonus pickup
BONUS_SHIP_TIMEOUT = 20000	# ship bonus: tank can drive over water
VERSUS_BONUS_TIMEOUT = 15000	# versus mode: new random bonus every n ms
ICE_SLIDE_DISTANCE = 15 * 2	# px tank slides on ice after movement button is released, NES: 15 px
BRICK_QUARTERS = True	# brick tiles consist of 4 parts, bullet destroys nearest half (like on NES)
# enemy fires with CHANCE_OF_FIRE % every ENEMY_FIRE_TIMER ms. NES: 1/32 chance every frame
ENEMY_FIRE_TIMER = 1000 // GAME_FRAME_TIMING
CHANCE_OF_FIRE = 100.0 * NES_FPS / 32 / GAME_FRAME_TIMING
HEAD_SHIELD_WHEN_PROTECTED = True	# protected player tank isn't hurt by bullets hitting its front
ENABLE_PLAYER_PROTECTION = True	# player gets frontal armor at superpower 5

# bonuses which can appear (names of Bonus.BONUS_* types), repeated types are more frequent
BONUS_TYPES = ["STAR", "STAR", "GRENADE", "GRENADE", "HELMET", "SHOVEL", "SHOVEL", "TANK", "TIMER", "PISTOL", "SHIP"]
# NES: star and grenade 2/8, helmet, timer, shovel, tank 1/8
NES_BONUS_TYPES = ["STAR", "STAR", "GRENADE", "GRENADE", "HELMET", "TIMER", "SHOVEL", "TANK"]

# GAME SPEED (px per frame, NES values converted)
DEFAULT_BULLET_SPEED = 2 * NES_PX_PER_FRAME	# 4.8, NES: 2 px per frame
FAST_BULLET_SPEED = 4 * NES_PX_PER_FRAME	# 9.6, NES: 4 px - player with star, power tank
# NES: player moves 0.75 px per frame, fast enemy 1 px, other enemies 0.5 px
PLAYER_DEFAULT_SPEED = 0.75 * NES_PX_PER_FRAME	# 1.8
DEFAULT_ENEMY_SPEED = 0.5 * NES_PX_PER_FRAME	# 1.2: basic, power, armor tanks
DEFAULT_ENEMY_SPEED_FAST = 0.5 * NES_PX_PER_FRAME	# added to DEFAULT_ENEMY_SPEED for fast tank: 2.4
GAME_OVER_TEXT_SPEED = 1 * NES_PX_PER_FRAME	# "game over" text rises 1 NES px per frame
ENEMY_SPAWN_ANIMATION_TIME = nesFrames(56)	# flashing star before enemy appears, NES: 0.93 s
PLAYER_SPAWN_ANIMATION_TIME = nesFrames(38)	# NES: 0.62 s

# ENEMY
DEFAULT_ENEMY_ARMOR_HEALTH = 600

# PLAYER
PLAYER_START_SUPERPOWER = 0	# NES: no stars, normal bullets
PLAYER_START_LIFE = 3	# NES: 3 (sidebar shows lives left: 2)
PLAYER_START_HEALTH = 100
PLAYER_START_SCORE = 0
PLAYER_START_MAX_ACTIVE_BULLETS = 1
PLAYER_START_SHIELD_TIMEOUT = nesFrames(192)	# after (re)spawn, NES: 3 x 64 frames = 3.2 s
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
EXTRA_LIFE_ONCE = False	# NES: extra life only once, at 20000
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
	# rules of original NES game
	"CLASSIC": {
		"ALLOW_MULTI_BONUS": False,
		"ENEMY_PICKUP_BONUSES": False,
		"BONUS_FREQ": 7,
		"BONUS_TANK_OFFSET": 3,
		"BONUS_SPAWN_TIMEOUT": 0,
		"BONUS_TYPES": NES_BONUS_TYPES,
		"FRIENDLY_FIRE": True,
		"EXTRA_LIFE_ONCE": True,
		"PLAYER_START_SUPERPOWER": 0,
		"DEFAULT_ENEMY_ARMOR_HEALTH": 400,
		"DEFAULT_ENEMY_SPEED_FAST": DEFAULT_ENEMY_SPEED_FAST,
		"MAX_ACTIVE_ENEMIES": 4,
		"MAX_ACTIVE_ENEMIES_2_PLAYERS": 6,
		"MAX_ACTIVE_ENEMIES_3_PLAYERS": 8,
		"ENEMY_SPAWN_TIMEOUT": None,
		"ENABLE_PLAYER_PROTECTION": False,
		"ENEMY_AI_BASE_CHANCE": 50,
		"ENABLE_NEW_ENEMIES": False,
	},
	"GOOD": {
		"ALLOW_MULTI_BONUS": True,
		"ENEMY_PICKUP_BONUSES": True,
		"BONUS_FREQ": 4,
		"BONUS_TANK_OFFSET": 3,
		"BONUS_SPAWN_TIMEOUT": 20000,
		"BONUS_TYPES": BONUS_TYPES,
		"FRIENDLY_FIRE": False,
		"EXTRA_LIFE_ONCE": False,
		"PLAYER_START_SUPERPOWER": 0,	# NES: no stars, normal bullets
		"DEFAULT_ENEMY_ARMOR_HEALTH": 600,
		"DEFAULT_ENEMY_SPEED_FAST": DEFAULT_ENEMY_SPEED_FAST,
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
		"BONUS_TANK_OFFSET": 3,
		"BONUS_SPAWN_TIMEOUT": 20000,
		"BONUS_TYPES": BONUS_TYPES,
		"FRIENDLY_FIRE": False,
		"EXTRA_LIFE_ONCE": False,
		"PLAYER_START_SUPERPOWER": 0,	# NES: no stars, normal bullets
		"DEFAULT_ENEMY_ARMOR_HEALTH": 600,
		"DEFAULT_ENEMY_SPEED_FAST": DEFAULT_ENEMY_SPEED_FAST,
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

# sound on / off (settings screen, M key in game)
play_sounds = True
