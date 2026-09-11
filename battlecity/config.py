# coding=utf-8
""" Battle City settings

Values can be changed here. Difficulty presets (PRESETS) override some of them,
settings screen changes and saves others (.settings.json).
"""

import os, pygame, time, random, uuid, sys, argparse, json
from pygame.locals import *

# NES TIMING: timings and speeds are taken from NES version (disassembly) and counted in its frames.
# Game logic is the same on every console, only frame rate differs:
# DENDY (PAL, Famicom clones, 50 fps) or NTSC (Japan / USA, 60 fps). Can be changed on settings screen.
NES_VERSIONS = {"DENDY": 50, "NTSC": 60}
NES_VERSION = "DENDY"
GAME_FRAME_TIMING = 50	# frames per second of this game

def nesFrames(frames):
	""" Duration of n NES frames in ms """
	return int(round(frames * 1000.0 / NES_VERSIONS[NES_VERSION]))

def applyNesVersion(name):
	""" Set NES version (frame rate) and recalculate all NES timings and speeds """
	global NES_VERSION, NES_FPS, NES_PX_PER_FRAME
	global FRIENDLY_FIRE_STUN_TIME, LEVEL_FINISH_TIMEOUT, GAME_OVER_TIMEOUT, BONUS_TIMER_FREEZE_TIMEOUT
	global BONUS_FORTRESS_WALLS_TIMEOUT, FORTRESS_BLINK_TIME, FORTRESS_BLINK_INTERVAL, BONUS_PLAYER_SHIELD_TIMEOUT
	global BONUS_BLINK_INTERVAL, BONUS_PICKUP_LABEL_TIME, ENEMY_SPAWN_ANIMATION_TIME, PLAYER_SPAWN_ANIMATION_TIME
	global PLAYER_START_SHIELD_TIMEOUT, CHANCE_OF_FIRE, GAME_OVER_TEXT_SPEED, BULLET_EXPLOSION_TIME, BULLET_TANK_HIT_SLOT_TIME
	global DEFAULT_BULLET_SPEED, FAST_BULLET_SPEED, PLAYER_DEFAULT_SPEED, DEFAULT_ENEMY_SPEED, DEFAULT_ENEMY_SPEED_FAST
	global ENEMY_EXPLOSION_TIME, FAST_ENEMY_EXPLOSION_TIME, PLAYER_EXPLOSION_TIME

	NES_VERSION = name
	NES_FPS = NES_VERSIONS[name]
	# NES pixels are 2x smaller than here: speed of 1 NES px per NES frame in px per frame of this game
	NES_PX_PER_FRAME = 2.0 * NES_FPS / GAME_FRAME_TIMING

	# durations in ms of NES frame counts
	FRIENDLY_FIRE_STUN_TIME = nesFrames(267)	# partner hit: 200 counts on 3 of 4 frames
	LEVEL_FINISH_TIMEOUT = nesFrames(128)	# after the last enemy is destroyed
	GAME_OVER_TIMEOUT = nesFrames(256)	# "game over" before scores screen
	BONUS_TIMER_FREEZE_TIMEOUT = nesFrames(640)	# clock: 10 x 64 frames
	BONUS_FORTRESS_WALLS_TIMEOUT = nesFrames(1280)	# shovel: 20 x 64 frames
	FORTRESS_BLINK_TIME = nesFrames(192)	# steel walls blink steel / brick during last 3 x 64 frames
	FORTRESS_BLINK_INTERVAL = nesFrames(16)
	BONUS_PLAYER_SHIELD_TIMEOUT = nesFrames(640)	# helmet: 10 x 64 frames
	BONUS_BLINK_INTERVAL = nesFrames(8)	# bonus: 8 frames visible, 8 hidden
	BONUS_PICKUP_LABEL_TIME = nesFrames(50)	# "500" after bonus pickup
	ENEMY_SPAWN_ANIMATION_TIME = nesFrames(56)	# flashing star before enemy appears
	PLAYER_SPAWN_ANIMATION_TIME = nesFrames(38)
	PLAYER_START_SHIELD_TIMEOUT = nesFrames(192)	# after (re)spawn: 3 x 64 frames
	# bullet explosion; tank can't fire again until its bullet stops exploding
	BULLET_EXPLOSION_TIME = nesFrames(9)
	# not NES: bullet which exploded on a tank frees its slot earlier, so shooting at a tank at point blank
	# is a bit faster and explosion on enemy's front keeps stopping enemy bullets until the next shot
	BULLET_TANK_HIT_SLOT_TIME = nesFrames(5)
	# tank explosion
	ENEMY_EXPLOSION_TIME = nesFrames(48)
	FAST_ENEMY_EXPLOSION_TIME = nesFrames(24)
	PLAYER_EXPLOSION_TIME = nesFrames(32)

	# enemy tries to fire every frame (ENEMY_FIRE_TIMER) with 1/32 chance per NES frame
	CHANCE_OF_FIRE = 100.0 * NES_FPS / 32 / GAME_FRAME_TIMING

	# speeds in px per frame of this game
	DEFAULT_BULLET_SPEED = 2 * NES_PX_PER_FRAME	# NES: 2 px per frame
	FAST_BULLET_SPEED = 4 * NES_PX_PER_FRAME	# NES: 4 px - player with star, power tank
	PLAYER_DEFAULT_SPEED = 0.75 * NES_PX_PER_FRAME	# NES: 1 px on 3 of 4 frames
	DEFAULT_ENEMY_SPEED = 0.5 * NES_PX_PER_FRAME	# NES: 1 px every other frame - basic, power, armor tanks
	DEFAULT_ENEMY_SPEED_FAST = 0.5 * NES_PX_PER_FRAME	# added to DEFAULT_ENEMY_SPEED for fast tank (NES: 1 px every frame)
	GAME_OVER_TEXT_SPEED = 1 * NES_PX_PER_FRAME	# "game over" text rises 1 NES px per frame


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
MAX_ACTIVE_ENEMIES = 4
MAX_ACTIVE_ENEMIES_2_PLAYERS = 10
MAX_ACTIVE_ENEMIES_3_PLAYERS = 12
ENEMY_SPAWN_TIMEOUT = 1000	# ms between enemy spawns, None - NES formula (depends on stage and players)
BONUS_PLAYER_HIDDEN_TIMEOUT = 10000
BONUS_SPAWN_TIMEOUT = 20000	# bonus disappears after n ms, 0 - stays until picked up (NES)
BONUS_SHIP_TIMEOUT = 20000	# ship bonus: tank can drive over water
VERSUS_BONUS_TIMEOUT = 15000	# versus mode: new random bonus every n ms
ICE_SLIDE_DISTANCE = 28 * 2	# px tank slides when it starts moving on ice, NES: 28 px
ICE_CONTROL_DISTANCE = 16 * 2	# ... buttons are ignored until this many px are left (NES: first 12 px), rest is slid after release
BRICK_QUARTERS = True	# brick tiles consist of 4 parts, bullet destroys nearest half (like on NES)
# enemy fires with CHANCE_OF_FIRE % (see applyNesVersion) every ENEMY_FIRE_TIMER ms
ENEMY_FIRE_TIMER = 1000 // GAME_FRAME_TIMING
ENEMY_GRID_PAUSE_CHANCE = 1 / 32.0	# NES: enemy on 8 px grid spends a move choosing direction with 1/16 chance (2 steps here)
HEAD_SHIELD_WHEN_PROTECTED = True	# protected player tank isn't hurt by bullets hitting its front
ENABLE_PLAYER_PROTECTION = True	# player gets frontal armor at superpower 5
# NES stars: 1 fast bullets, 2 two bullets, 3 bullets destroy steel and whole bricks (grass stays), more stars do nothing
NES_STARS = False

# bonuses which can appear (names of Bonus.BONUS_* types), repeated types are more frequent
BONUS_TYPES = ["STAR", "STAR", "GRENADE", "GRENADE", "HELMET", "SHOVEL", "SHOVEL", "TANK", "TIMER", "PISTOL", "SHIP"]
# NES: star and grenade 2/8, helmet, timer, shovel, tank 1/8
NES_BONUS_TYPES = ["STAR", "STAR", "GRENADE", "GRENADE", "HELMET", "TIMER", "SHOVEL", "TANK"]

# NES TIMINGS AND SPEEDS: bullets, tanks, bonus durations, spawn animation... (see applyNesVersion)
applyNesVersion(NES_VERSION)

# ENEMY
DEFAULT_ENEMY_ARMOR_HEALTH = 600

# PLAYER
PLAYER_START_SUPERPOWER = 0	# NES: no stars, normal bullets
PLAYER_START_LIFE = 3	# NES: 3 (sidebar shows lives left: 2)
PLAYER_START_HEALTH = 100
PLAYER_START_SCORE = 0
PLAYER_START_MAX_ACTIVE_BULLETS = 1
AUTO_FIRE = True	# holding fire button fires again as soon as bullet slot is free. NES (False): every shot needs a press
PLAYER_AUTO_FIRE_DELAY = 100	# min ms between shots while fire button is held
# not NES (there bullets cancel each other): player's bullet destroys enemy's bullet and flies on,
# so player shooting at an enemy head-on wins even if the enemy fires too
PLAYER_BULLETS_PRIORITY = True

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
STAGE_SCREEN_TIME = 1500	# grey "STAGE N" screen before level, 0 - don't show (and no curtain)
CURTAIN_FRAMES = 16	# NES: grey curtain closes before "STAGE N" and opens over the stage in 16 frames
SHOW_EFFECT_TIMERS = False	# bars showing time left for shield, ship, freeze and fortress walls

# CONSTANTS
S_SIZE = 4
T_SIZE = 32

# NES LIKE RULES
EXTRA_LIFE_SCORE = 20000	# extra life every n points, 0 - disabled
EXTRA_LIFE_ONCE = False	# NES: extra life only once, at 20000
TWO_PLAYER_KILLS_BONUS = 1000	# 2+ players: player who destroyed most tanks on stage gets these points
ENEMY_AI_BASE_CHANCE = 30	# % chance enemy prefers directions towards player's castle (CLASSIC AI)
# CLASSIC - random paths, sometimes towards castle; NES - like NES: random directions at stage start,
# then chasing players, then going to castle; blocked tank waits or turns
ENEMY_AI_TYPES = ["CLASSIC", "NES"]
ENEMY_AI = "CLASSIC"

# interface language: EN or RU (settings screen)
LANGUAGE = "EN"

# GAMEPADS (settings screen): gamepad of players 1-3: "AUTO", "OFF" or gamepad number from 0;
# fire / start button numbers, None - default buttons (A, B, X, Y fire, Start)
GAMEPAD_ASSIGN = ["AUTO", "AUTO", "AUTO"]
GAMEPAD_FIRE_BUTTON = None
GAMEPAD_START_BUTTON = None

# DEMO: computer plays after n ms in menu without input (0 - no demo), demo lasts n ms
DEMO_IDLE_TIME = 20000
DEMO_TIME = 40000

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
		"ENEMY_PICKUP_BONUSES": True,	# NES: enemies don't pick up bonuses
		"BONUS_FREQ": 7,
		"BONUS_TANK_OFFSET": 3,
		"BONUS_SPAWN_TIMEOUT": 0,
		"BONUS_TYPES": NES_BONUS_TYPES,
		"FRIENDLY_FIRE": True,
		"EXTRA_LIFE_ONCE": True,
		"PLAYER_START_SUPERPOWER": 0,
		"DEFAULT_ENEMY_ARMOR_HEALTH": 400,
		"MAX_ACTIVE_ENEMIES": 4,
		"MAX_ACTIVE_ENEMIES_2_PLAYERS": 6,
		"MAX_ACTIVE_ENEMIES_3_PLAYERS": 8,
		"ENEMY_SPAWN_TIMEOUT": None,
		"ENABLE_PLAYER_PROTECTION": False,
		"ENEMY_AI_BASE_CHANCE": 50,
		"ENABLE_NEW_ENEMIES": False,
		"NES_STARS": True,
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
		"MAX_ACTIVE_ENEMIES": 5,
		"MAX_ACTIVE_ENEMIES_2_PLAYERS": 8,
		"MAX_ACTIVE_ENEMIES_3_PLAYERS": 12,
		"ENEMY_SPAWN_TIMEOUT": 1000,
		"ENABLE_PLAYER_PROTECTION": True,
		"ENEMY_AI_BASE_CHANCE": 30,
		"ENABLE_NEW_ENEMIES": True,
		"NES_STARS": False,
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
		"MAX_ACTIVE_ENEMIES": 4,
		"MAX_ACTIVE_ENEMIES_2_PLAYERS": 14,
		"MAX_ACTIVE_ENEMIES_3_PLAYERS": 16,
		"ENEMY_SPAWN_TIMEOUT": 1000,
		"ENABLE_PLAYER_PROTECTION": True,
		"ENEMY_AI_BASE_CHANCE": 30,
		"ENABLE_NEW_ENEMIES": True,
		"NES_STARS": False,
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
	BATTLE_CITY_DATA_DIR environment variable changes the directory (used by tests),
	default is game directory, or ~/Library/Application Support/Battle City for Mac app
	"""
	directory = os.environ.get("BATTLE_CITY_DATA_DIR", "")
	if not directory and getattr(sys, "frozen", False):
		# Mac app: never write into app bundle
		directory = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Battle City")
		if not os.path.isdir(directory):
			os.makedirs(directory)
	return os.path.join(directory, name)

def levelFile(level_nr):
	""" Level map file: custom level made in editor or original one """
	custom = dataFile(os.path.join(CUSTOM_LEVELS_DIR, str(level_nr)))
	if os.path.isfile(custom):
		return custom
	return os.path.join("levels", str(level_nr))

def loadSettings():
	""" Apply settings saved on settings screen """
	global play_sounds, START_LEVEL, START_FULLSCREEN, PLAYER_CONTROLS, AUTO_FIRE, ENEMY_AI
	global GAMEPAD_ASSIGN, GAMEPAD_FIRE_BUTTON, GAMEPAD_START_BUTTON, LANGUAGE

	try:
		with open(dataFile(SETTINGS_FILE), "r") as f:
			settings = json.load(f)
	except (IOError, ValueError):
		return

	try:
		if settings.get("preset") in PRESETS:
			applyPreset(settings["preset"])
		if settings.get("nes_version") in NES_VERSIONS:
			applyNesVersion(settings["nes_version"])
		AUTO_FIRE = bool(settings.get("auto_fire", AUTO_FIRE))
		if settings.get("enemy_ai") in ENEMY_AI_TYPES:
			ENEMY_AI = settings["enemy_ai"]
		if settings.get("language") in ("EN", "RU"):
			LANGUAGE = settings["language"]
		gamepads = settings.get("gamepads")
		if isinstance(gamepads, list) and len(gamepads) == len(GAMEPAD_ASSIGN):
			GAMEPAD_ASSIGN = [g if g in ("AUTO", "OFF") else int(g) for g in gamepads]
		for key, name in (("pad_fire", "GAMEPAD_FIRE_BUTTON"), ("pad_start", "GAMEPAD_START_BUTTON")):
			if settings.get(key) != None:
				globals()[name] = int(settings[key])
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
		"nes_version": NES_VERSION,
		"auto_fire": AUTO_FIRE,
		"enemy_ai": ENEMY_AI,
		"language": LANGUAGE,
		"gamepads": GAMEPAD_ASSIGN,
		"pad_fire": GAMEPAD_FIRE_BUTTON,
		"pad_start": GAMEPAD_START_BUTTON,
		"controls": PLAYER_CONTROLS,
	}
	try:
		with open(dataFile(SETTINGS_FILE), "w") as f:
			json.dump(settings, f, indent=1)
	except IOError:
		print("Can't save settings")

# sound on / off (settings screen, M key in game)
play_sounds = True
