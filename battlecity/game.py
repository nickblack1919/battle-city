# coding=utf-8
""" Battle City: game screens and main loop """

import os, random, uuid, sys, json, array
import pygame
from pygame.locals import *
from sys import exit as quit	# builtin quit() is missing in Mac app (PyInstaller)

from battlecity import config, lang, state
from battlecity.bonus import Bonus
from battlecity.castle import Castle
from battlecity.effects import Label
from battlecity.gamepad import Gamepad, sdl_controller
from battlecity.level import Level
from battlecity.tank import Enemy, Player
from battlecity.menu import MenuMixin
from battlecity.settings import SettingsMixin
from battlecity.editor import EditorMixin
from battlecity.screens import ScreensMixin

class Game(MenuMixin, SettingsMixin, EditorMixin, ScreensMixin):

	# direction constants
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)

	TILE_SIZE = 16

	def __init__(self):


		# center window
		os.environ['SDL_VIDEO_WINDOW_POS'] = 'center'

		pygame.mixer.pre_init(44100, -16, 1, 512)

		pygame.init()

		pygame.display.set_caption("Battle City")

		if config.args['fullscreen'] or config.START_FULLSCREEN:
			self.is_fullscreen = True
		else:
			self.is_fullscreen = False

		self.display = self.setFullScreen(self.is_fullscreen)

		# game is always drawn on this surface, then shown on display (scaled in full screen)
		state.screen = pygame.Surface((480, 416)).convert()

		self.clock = pygame.time.Clock()

		# load sprites (funky version)
		# sprites = pygame.transform.scale2x(pygame.image.load("images/sprites.gif"))
		# load sprites (pixely version)
		state.sprites = pygame.transform.scale(pygame.image.load("images/sprites.gif"), [192, 224])
		#screen.set_colorkey((0,138,104))
		state.sprites2 = pygame.transform.scale(pygame.image.load("images/sprites2.png"), [1024, 512])


		pygame.display.set_icon(state.sprites.subsurface(0, 0, 13*2, 13*2))

		# load sounds (always: sound can be switched on in settings)
		try:
			pygame.mixer.init(44100, -16, 1, 512)

			state.sounds["start"] = pygame.mixer.Sound("sounds/gamestart.ogg")
			state.sounds["gameover"] = pygame.mixer.Sound("sounds/gameover.ogg")
			state.sounds["score"] = pygame.mixer.Sound("sounds/score.ogg")
			state.sounds["bg"] = pygame.mixer.Sound("sounds/background.ogg")
			state.sounds["engine"] = self.makeEngineSound(state.sounds["bg"])
			state.sounds["fire"] = pygame.mixer.Sound("sounds/fire.ogg")
			state.sounds["bonus"] = pygame.mixer.Sound("sounds/bonus.ogg")
			state.sounds["bonusnew"] = pygame.mixer.Sound("sounds/bonusnew.ogg")
			state.sounds["explosion"] = pygame.mixer.Sound("sounds/explosion.ogg")
			state.sounds["boom"] = pygame.mixer.Sound("sounds/boom.ogg")
			state.sounds["brick"] = pygame.mixer.Sound("sounds/brick.ogg")
			state.sounds["steel"] = pygame.mixer.Sound("sounds/steel.ogg")
			state.sounds["armor"] = pygame.mixer.Sound("sounds/armor.ogg")
			state.sounds["ice"] = pygame.mixer.Sound("sounds/ice.ogg")
			state.sounds["life"] = pygame.mixer.Sound("sounds/life.ogg")
			state.sounds["pause"] = pygame.mixer.Sound("sounds/pause.ogg")
		except pygame.error:
			print("Can't load sounds")
			config.play_sounds = False
			state.sounds.clear()

		self.enemy_life_image = state.sprites.subsurface(81*2, 57*2, 7*2, 7*2)
		self.player_life_image = state.sprites.subsurface(89*2, 56*2, 7*2, 8*2)
		self.flag_image = state.sprites.subsurface(64*2, 49*2, 16*2, 15*2)

		# this is used in intro screen
		self.player_image = pygame.transform.rotate(state.sprites.subsurface(0, 0, 13*2, 13*2), 270)
		
		self.player_image_green = pygame.transform.rotate(state.sprites.subsurface(16*2, 0, 13*2, 13*2), 270)


		# if true, no new enemies will be spawn during this time
		self.timefreeze = False
		
		self.game_paused = False

		# load custom font
		self.font = pygame.font.Font("fonts/prstart.ttf", 16)

		# pre-render game over text
		self.prerenderTexts()
		self.game_over_y = 416+40
		

		# number of players. here is defined preselected menu value
		self.nr_of_players = 1

		# selected main menu item
		self.menu_index = 0

		# game mode: campaign (stages with score screens) or endless (waves until game over)
		self.mode = "campaign"
		self.first_stage = 1

		# demo: computer plays when menu is idle
		self.demo = False

		# versus: index of winning player
		self.versus_winner = None

		# players' score, lives and superpowers from saved game (applied when players are created)
		self.loaded_players_stats = None

		state.enemy_spawn_pos_index = 2

		# sounds playing: moving player's engine, engine hum of the stage
		self.engine_sound = False
		self.bg_sound = False

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

		# keys currently held (layout independent key codes)
		self.held_keys = set()

		# connected gamepads (opened in updateGamepads)
		self.gamepads = []
		self.gamepad_count = 0

		del state.players[:]
		del state.bullets[:]
		del state.enemies[:]
		del state.bonuses[:]

	def makeEngineSound(self, sound, pitch = 1.5):
		""" Engine sound of moving player tank: engine hum played faster (higher) """
		frequency, size, channels = pygame.mixer.get_init()
		if size != -16:
			return sound
		samples = array.array("h", sound.get_raw())
		shifted = array.array("h")
		for i in range(int(len(samples) // channels / pitch)):
			start = int(i * pitch) * channels
			shifted.extend(samples[start:start + channels])
		return pygame.mixer.Sound(buffer=shifted.tobytes())

	def playBackgroundSound(self):
		""" Engine hum during the stage (until last enemy is destroyed); moving player's engine sound replaces it """
		self.bg_sound = True
		if config.play_sounds and not self.engine_sound:
			state.sounds["bg"].play(-1)

	def updateEngineSound(self, moving):
		""" NES: engine sound plays while any player tank moves """
		moving = moving and config.play_sounds and "engine" in state.sounds and not self.game_paused and not self.game_over
		if moving == self.engine_sound:
			return
		self.engine_sound = moving
		if moving:
			state.sounds["bg"].stop()
			state.sounds["engine"].play(-1)
		elif "engine" in state.sounds:
			state.sounds["engine"].stop()
			if self.bg_sound and config.play_sounds:
				state.sounds["bg"].play(-1)

	def prerenderTexts(self):
		""" Pre-render "game over" and "pause" texts in current language """
		color = (127, 64, 64)
		game, over = self.text("GAME", False, color), self.text("OVER", False, color)
		self.im_game_over = pygame.Surface((max(game.get_width(), over.get_width()), 40))
		self.im_game_over.set_colorkey((0,0,0))
		self.im_game_over.blit(game, [(self.im_game_over.get_width() - game.get_width()) // 2, 0])
		self.im_game_over.blit(over, [(self.im_game_over.get_width() - over.get_width()) // 2, 20])

		pause = self.text("PAUSE", False, color)
		self.im_pause = pygame.Surface(pause.get_size())
		self.im_pause.set_colorkey((0,0,0))
		self.im_pause.blit(pause, [0, 0])

	def text(self, text, antialias, color, translate = True):
		""" Render text with game font in current language (translate False - as is) """
		return lang.render(self.font, 16, text, antialias, color, translate)

	def toggleDebugMode(self): 
		self.debug_mode = not self.debug_mode
		config.DEBUG_SPRITES = config.DEBUG_DRAW_MESH = self.debug_mode

	def drawMesh(self):
		""" Draw 32 x 32 mesh on screen for debugging """
		blue = pygame.Color(0,0,255)

		size = width, height = 416, 416
		H_STEP, V_STEP = 32, 32
		V_LINES = int(width / V_STEP) + 1
		H_LINES = int(width / H_STEP + 1)

		for i in range(H_LINES):
			pygame.draw.line(state.screen, blue, [0, i*H_STEP], [width, i*H_STEP], 1)

		for i in range(V_LINES):
			pygame.draw.line(state.screen, blue, [i*V_STEP, 0], [i*V_STEP, height], 1)


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
		""" Give gamepads to players: GAMEPAD_ASSIGN (settings) - gamepad number, OFF or AUTO.
		AUTO players get free gamepads: players without keyboard controls (P3) first, then P1, P2 """
		for player in state.players:
			player.gamepad = None
		used = []
		auto = []
		for player_nr, player in enumerate(state.players):
			assign = config.GAMEPAD_ASSIGN[player_nr] if player_nr < len(config.GAMEPAD_ASSIGN) else "AUTO"
			if assign == "AUTO":
				auto.append(player)
			elif assign != "OFF" and assign < len(self.gamepads):
				player.gamepad = self.gamepads[assign]
				used.append(assign)
		free = [gamepad for i, gamepad in enumerate(self.gamepads) if i not in used]
		ordered = [player for player in auto if not player.controls] + [player for player in auto if player.controls]
		for gamepad, player in zip(free, ordered):
			player.gamepad = gamepad

	def applyGamepads(self):
		""" Gamepad controls in game: movement, fire (auto fire while held), Start - pause """
		for gamepad in self.gamepads:
			if gamepad.pressed("start") and not self.game_over and self.active:
				self.pause()
				break

		for player in state.players:
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
			state.gtimer.destroy(timer)
	
	# physical keys (scancodes) of letters, digits and punctuation -> key codes of U.S. layout
	LAYOUT_KEYS = dict(
		[(getattr(pygame, "KSCAN_" + letter), getattr(pygame, "K_" + letter.lower())) for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"] +
		[(getattr(pygame, "KSCAN_" + digit), getattr(pygame, "K_" + digit)) for digit in "0123456789"] +
		[(getattr(pygame, "KSCAN_" + name), getattr(pygame, "K_" + name)) for name in
			("MINUS", "EQUALS", "LEFTBRACKET", "RIGHTBRACKET", "BACKSLASH", "SEMICOLON", "COMMA", "PERIOD", "SLASH")] +
		[(pygame.KSCAN_APOSTROPHE, pygame.K_QUOTE), (pygame.KSCAN_GRAVE, pygame.K_BACKQUOTE)]
	)

	def events(self):
		""" pygame.event.get() with key codes independent of keyboard layout:
		with Russian layout physical W key gives key code of "ц", here it becomes K_w again,
		so controls, hotkeys and editor keys work with any layout
		"""
		events = []
		for event in pygame.event.get():
			if event.type in (pygame.KEYDOWN, pygame.KEYUP):
				key = self.LAYOUT_KEYS.get(getattr(event, "scancode", 0))
				if key != None and key != event.key:
					attributes = dict(event.dict)
					attributes["key"] = key
					event = pygame.event.Event(event.type, attributes)
				if event.type == pygame.KEYDOWN:
					self.held_keys.add(event.key)
				else:
					self.held_keys.discard(event.key)
			events.append(event)
		return events

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

		self.display = pygame.display.get_surface()

		if self.shake_frames > 0:
			self.shake_frames -= 1
			offset = [random.randint(-3, 3), random.randint(-3, 3)]
			self.display.fill([0, 0, 0])
			self.display.blit(state.screen, offset)
		else:
			self.display.blit(state.screen, [0, 0])

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
		if config.SCREEN_SHAKE:
			self.shake_frames = max(self.shake_frames, frames)

	def drawEffectTimers(self):
		""" Bars with time left: shield above players, enemy freeze (top edge, blue),
		players freeze (bottom edge, red), steel fortress walls (above castle) """


		if not config.SHOW_EFFECT_TIMERS:
			return

		def bar(timer_uuid, rect, color):
			remaining = state.gtimer.remaining(timer_uuid) if timer_uuid else None
			if remaining == None:
				return
			width = int(rect[2] * float(remaining[0]) / remaining[1])
			pygame.draw.rect(state.screen, color, [rect[0], rect[1], max(width, 1), rect[3]])

		for player in state.players:
			if player.state == player.STATE_ALIVE and player.shielded:
				bar(player.shield_end_timer, [player.rect.left, player.rect.top - 4, 32, 2], (120, 200, 255))
			if player.state == player.STATE_ALIVE and player.ship:
				bar(player.ship_timer, [player.rect.left, player.rect.top - 7, 32, 2], (60, 140, 255))

		if self.timefreeze:
			bar(self.enemy_freeze_end_timer, [0, 0, 416, 3], (80, 160, 255))
		if self.players_frozen:
			bar(self.players_freeze_end_timer, [0, 413, 416, 3], (255, 80, 80))
		bar(self.fortress_end_timer, [176, 362, 64, 2], (200, 200, 200))

	def setFullScreen(self, fullScreen):
		size = width, height = 480, 416

		if fullScreen:
			display = pygame.display.set_mode(size, SCALED | FULLSCREEN)
		else:
			display = pygame.display.set_mode(size, SCALED)
			
		return display

	def triggerEnemyBonus(self, bonus, enemy):
		""" Execute enemy bonus powers """


		if config.play_sounds:
			state.sounds["ice"].play()

		# destory all players
		if bonus.bonus == bonus.BONUS_GRENADE:
			# for player in players:
			# 	player.explode()
			self.loadLevelEnemies(True)
			if config.play_sounds:
				state.sounds["start"].play()

		# hide all players for 10 seconds
		# all enemies can drive over water for some time
		elif bonus.bonus == bonus.BONUS_SHIP:
			self.setEnemiesShip(True)
			self.destroyTimer(self.enemies_ship_timer)
			self.enemies_ship_timer = state.gtimer.add(config.BONUS_SHIP_TIMEOUT, lambda :self.setEnemiesShip(False), 1)
		elif bonus.bonus == bonus.BONUS_HELMET:
			for player in state.players:
				player.hideTank(config.BONUS_PLAYER_HIDDEN_TIMEOUT)
		# remove walls from fortress for 10 seconds
		elif bonus.bonus == bonus.BONUS_SHOVEL:
			if not config.FORTRESS_FOREVER:
				self.level.buildFortress(self.level.TILE_EMPTY)
				self.stopFortressBlinking()
				self.destroyTimer(self.fortress_end_timer)
				self.fortress_end_timer = state.gtimer.add(config.BONUS_FORTRESS_WALLS_TIMEOUT, lambda :self.level.buildFortress(self.level.TILE_BRICK), 1)
		# increase 1 enemy superpower by 2
		elif bonus.bonus == bonus.BONUS_STAR:
			for enemy in state.enemies:
				enemy.superpowers += 2
				enemy.updateSuperpowers()
		# increase 1 enemy superpower by 2
		elif bonus.bonus == bonus.BONUS_PISTOL:
			for enemy in state.enemies:
				enemy.superpowers += 2
				enemy.type += 2
				if enemy.type >= 3:
					enemy.health = 400
					enemy.type = 3
					enemy.speed = config.DEFAULT_ENEMY_SPEED + config.DEFAULT_ENEMY_SPEED_FAST
				enemy.updateSuperpowers()
		# increase all enemy health by 200
		elif bonus.bonus == bonus.BONUS_TANK:
			for enemy in state.enemies:
				enemy.health += 200
				enemy.updateSprites()
		# freeze players for 10 seconds
		elif bonus.bonus == bonus.BONUS_TIMER:
			self.setPlayersFrozen(True)
			self.destroyTimer(self.players_freeze_end_timer)
			self.players_freeze_end_timer = state.gtimer.add(config.BONUS_TIMER_FREEZE_TIMEOUT, lambda :self.setPlayersFrozen(False), 1)
		
		if bonus in state.bonuses:
			state.bonuses.remove(bonus)

	def triggerBonus(self, bonus, player):
		""" Execute bonus powers """


		player.trophies["bonus"] += 1
		player.score += 500

		explode_count = 0
		# destroy all on screen enemies
		if bonus.bonus == bonus.BONUS_GRENADE:
			if config.play_sounds:
				state.sounds["explosion"].play()
			self.shake(12)
			for enemy in state.enemies:
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
			if config.play_sounds:
				state.sounds["bonus"].play()
			player.ship = True
			self.destroyTimer(player.ship_timer)
			player.ship_timer = state.gtimer.add(config.BONUS_SHIP_TIMEOUT, lambda :self.endShip(player), 1)
		elif bonus.bonus == bonus.BONUS_HELMET:
			if config.play_sounds:
				state.sounds["bonus"].play()
			self.shieldPlayer(player, True, config.BONUS_PLAYER_SHIELD_TIMEOUT)
		# upgrade fortress walls tp steel
		elif bonus.bonus == bonus.BONUS_SHOVEL:
			if config.play_sounds:
				state.sounds["bonus"].play()
			self.level.buildFortress(self.level.TILE_STEEL)
			self.startSteelFortressTimer()
		# upgrade superpower
		elif bonus.bonus == bonus.BONUS_STAR:
			if config.play_sounds:
				state.sounds["bonus"].play()
			player.superpowers += 1
			player.updateSuperpowers()
		# upgrade superpower by 3
		elif bonus.bonus == bonus.BONUS_PISTOL:
			if config.play_sounds:
				state.sounds["bonus"].play()
			player.superpowers += 3
			player.updateSuperpowers()
		# add 1 life
		elif bonus.bonus == bonus.BONUS_TANK:
			if config.play_sounds:
				state.sounds["life"].play()
			player.lives += 1
		# stop all enemies for 10 seconds
		elif bonus.bonus == bonus.BONUS_TIMER:
			if config.play_sounds:
				state.sounds["bonus"].play()
			self.toggleEnemyFreeze(True)
			self.destroyTimer(self.enemy_freeze_end_timer)
			self.enemy_freeze_end_timer = state.gtimer.add(config.BONUS_TIMER_FREEZE_TIMEOUT, lambda :self.toggleEnemyFreeze(False), 1)
		
		if bonus in state.bonuses:
			state.bonuses.remove(bonus)

		state.labels.append(Label(bonus.rect.topleft, "500", config.BONUS_PICKUP_LABEL_TIME))

	def startSteelFortressTimer(self):
		""" Fortress walls stay steel for BONUS_FORTRESS_WALLS_TIMEOUT, blink steel / brick
		during last FORTRESS_BLINK_TIME, then become brick again (like on NES) """
		if config.FORTRESS_FOREVER:
			return
		self.stopFortressBlinking()
		self.destroyTimer(self.fortress_end_timer)
		blink_start = max(config.BONUS_FORTRESS_WALLS_TIMEOUT - config.FORTRESS_BLINK_TIME, 1)
		self.fortress_blink_start_timer = state.gtimer.add(blink_start, lambda :self.startFortressBlinking(), 1)
		self.fortress_end_timer = state.gtimer.add(config.BONUS_FORTRESS_WALLS_TIMEOUT, lambda :self.endSteelFortress(), 1)

	def startFortressBlinking(self):
		self.fortress_blink_start_timer = None
		self.fortress_blink_steel = True
		self.fortress_blink_timer = state.gtimer.add(config.FORTRESS_BLINK_INTERVAL, lambda :self.toggleFortressBlink())

	def toggleFortressBlink(self):
		self.fortress_blink_steel = not self.fortress_blink_steel
		self.level.buildFortress(self.level.TILE_STEEL if self.fortress_blink_steel else self.level.TILE_BRICK)

	def stopFortressBlinking(self):
		self.destroyTimer(self.fortress_blink_start_timer)
		self.destroyTimer(self.fortress_blink_timer)
		self.fortress_blink_start_timer = None
		self.fortress_blink_timer = None

	def endSteelFortress(self):
		self.stopFortressBlinking()
		self.fortress_end_timer = None
		self.level.buildFortress(self.level.TILE_BRICK)

	def enemySpawnInterval(self):
		""" ms between enemy spawns: ENEMY_SPAWN_TIMEOUT or, if it is None, NES formula:
		190 - 4 * stage (up to 35) - 20 in 2 player game, + 1 frames """
		if config.ENEMY_SPAWN_TIMEOUT != None:
			return config.ENEMY_SPAWN_TIMEOUT
		stage = min(max(self.stage, 1), 35)
		frames = 190 - 4 * stage - (20 if self.nr_of_players >= 2 else 0) + 1
		return config.nesFrames(frames)

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
			player.timer_uuid_shield = state.gtimer.add(100, lambda :player.toggleShieldImage())

		if shield and duration != None:
			if player.shield_end_timer:
				state.gtimer.destroy(player.shield_end_timer)
			player.shield_end_timer = state.gtimer.add(duration, lambda :self.shieldPlayer(player, False), 1)


	def delay(self, fps):
		""" Wait like clock.tick(fps), but keep handling quit and full screen keys
		Used on screens without their own event loop (scores)
		"""
		self.clock.tick(fps)
		for event in self.events():
			if event.type == pygame.QUIT:
				quit()
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					quit()
				elif self.isFullScreenKey(event):
					self.toggleFullScreen()

	def delayFrames(self, frames):
		""" Wait n NES frames, handling quit and full screen keys """
		for i in range(max(1, int(round(config.nesFrames(frames) * config.GAME_FRAME_TIMING / 1000.0)))):
			self.delay(config.GAME_FRAME_TIMING)

	def getFreeSpawningPosition(self):
		""" Next enemy spawning position not occupied by any tank
		@return list [x, y] or None if all positions are occupied
		"""

		# NES order: center, right, left
		available_positions = [
			[12 * self.TILE_SIZE, 0],
			[24 * self.TILE_SIZE, 0],
			[0, 0]
		]

		for i in range(len(available_positions)):
			state.enemy_spawn_pos_index += 1
			state.enemy_spawn_pos_index %= len(available_positions)
			position = available_positions[state.enemy_spawn_pos_index]
			spawn_rect = pygame.Rect(position, [32, 32])

			occupied = False
			for tank in state.enemies + state.players:
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


		if self.game_paused:
			return False
		if len(state.enemies) >= self.level.max_active_enemies:
			return False
		if len(self.level.enemies_left) < 1:
			return False
		# don't spawn on top of other tanks, try again later
		position = self.getFreeSpawningPosition()
		if position == None:
			return False
		enemy = Enemy(self.level, 1, position)

		if self.timefreeze:
			enemy.paused = True

		state.enemies.append(enemy)
		return True


	def respawnPlayer(self, player, clear_scores = False, superpowers = None):
		""" Respawn player """
		player.reset()
		player.paralised = self.players_frozen

		# default is read at call time: preset can change it
		player.superpowers = config.PLAYER_START_SUPERPOWER if superpowers == None else superpowers
		player.updateSuperpowers()

		if clear_scores:
			player.trophies = config.emptyTrophies()

		self.shieldPlayer(player, True, config.PLAYER_START_SHIELD_TIMEOUT)

	def gameOver(self):
		""" End game and return to menu """


		if self.demo:
			self.stopDemo()
			return

		print("Game Over")
		self.deleteSavedGame()
		if config.play_sounds:
			for sound in state.sounds:
				state.sounds[sound].stop()
			state.sounds["gameover"].play()

		self.game_over_y = 416+40

		self.game_over = True
		state.gtimer.add(config.GAME_OVER_TIMEOUT, lambda :self.endLevel(self.showScores), 1)

	def castles(self):
		""" Player's castle, in versus mode also castle of player 2 """
		return [target for target in (state.castle, state.castle2) if target != None]

	def castleRects(self):
		return [target.rect for target in self.castles()]

	def spawnVersusBonus(self):
		""" Versus: random bonus useful in players' duel """
		if self.game_paused or self.game_over:
			return
		bonus = Bonus(self.level)
		bonus.setType(random.choice([bonus.BONUS_STAR, bonus.BONUS_HELMET, bonus.BONUS_TANK, bonus.BONUS_SHIP]))
		state.bonuses.append(bonus)
		if config.play_sounds:
			state.sounds["bonusnew"].play()
		if config.BONUS_SPAWN_TIMEOUT > 0:
			state.gtimer.add(max(config.BONUS_SPAWN_TIMEOUT - config.BONUS_BLINK_TIME, 1), lambda :bonus.startBlinking(), 1)
			state.gtimer.add(config.BONUS_SPAWN_TIMEOUT, lambda :state.bonuses.remove(bonus), 1)
		else:
			bonus.startBlinking()

	def versusOver(self, winner):
		""" Versus match is over: show "game over", then result """
		if self.game_over:
			return
		if config.play_sounds:
			for sound in state.sounds:
				state.sounds[sound].stop()
			state.sounds["gameover"].play()
		self.versus_winner = winner
		self.game_over_y = 416+40
		self.game_over = True
		state.gtimer.add(config.GAME_OVER_TIMEOUT, lambda :self.endLevel(self.showVersusResult), 1)

	def reloadPlayers(self):
		""" Init players
		If players already exist, just reset them
		"""


		

		if len(state.players) == 0:
			# first player
			x = 8 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
			y = 24 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2

			player = Player(
				self.level, 0, [x, y], self.DIR_UP, (5*config.S_SIZE*config.T_SIZE, 0, config.T_SIZE, config.T_SIZE), 1
			)
			player.controls = list(config.PLAYER_CONTROLS[0])
			state.players.append(player)

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
					self.level, 0, [x, y], direction, (6*config.S_SIZE*config.T_SIZE, 0, 16*2, 16*2), 2
				)
				player.controls = list(config.PLAYER_CONTROLS[1])
				state.players.append(player)

			# third player
			if self.nr_of_players == 3:
				x = 12 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
				y = 21 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 32) / 2
				player = Player(
					self.level, 0, [x, y], self.DIR_UP, (16*2, 0, 16*2, 16*2), 3
				)
				# third player uses gamepad only
				player.controls = []
				state.players.append(player)

		# continue saved game
		if self.loaded_players_stats:
			for player, stats in zip(state.players, self.loaded_players_stats):
				player.score = stats["score"]
				player.lives = stats["lives"]
				player.superpowers = stats["superpowers"]
				player.next_extra_life = stats["next_extra_life"]
			self.loaded_players_stats = None

		for player in state.players:
			player.level = self.level
			self.respawnPlayer(player, True, player.superpowers)

		self.assignGamepads()

	def draw(self, flip = True):

		state.screen.fill([0, 0, 0])

		self.level.draw([self.level.TILE_EMPTY, self.level.TILE_BRICK, self.level.TILE_STEEL, self.level.TILE_FROZE, self.level.TILE_WATER])

		for target in self.castles():
			target.draw()

		for enemy in state.enemies:
			enemy.draw()

		for label in state.labels:
			label.draw()

		for player in state.players:
			player.draw()

		for bullet in state.bullets:
			bullet.draw()

		for bonus in state.bonuses:
			bonus.draw()

		self.level.draw([self.level.TILE_GRASS])

		self.drawEffectTimers()

		if self.game_paused:
			state.screen.blit(self.im_pause, [(416 - self.im_pause.get_width()) // 2, 188])

		if self.game_over:
			if self.game_over_y > 188:
				self.game_over_y -= config.GAME_OVER_TEXT_SPEED
			state.screen.blit(self.im_game_over, [(416 - self.im_game_over.get_width()) // 2, self.game_over_y])

		self.drawSidebar()

		if config.DEBUG_DRAW_MESH:
			self.drawMesh()

		if flip:
			self.flip()

	def drawSidebar(self):


		x = 416
		y = 0
		state.screen.fill([100, 100, 100], pygame.Rect([416, 0], [64, 416]))

		xpos = x + 16
		ypos = y + 16

		# draw enemy lives (limited so icons don't overlap players' lives)
		max_icons = 20
		for n in range(min(len(self.level.enemies_left), max_icons)):
			state.screen.blit(self.enemy_life_image, [xpos, ypos])
			if n % 2 == 1:
				xpos = x + 16
				ypos+= 17
			else:
				xpos += 17

		hidden_enemies = len(self.level.enemies_left) - max_icons
		if hidden_enemies > 0 and pygame.font.get_init():
			state.screen.blit(self.text("+"+str(hidden_enemies), False, pygame.Color('black')), [x+4, ypos])

		# players' lives
		if pygame.font.get_init():
			text_color = pygame.Color('black')
			for n in range(len(state.players)):
				lives_left = state.players[n].lives - 1
				if lives_left < 0:
					lives_left = 0 
				state.screen.blit(self.text(str(n+1)+"P", False, text_color), [x+20, y+210+n*42])
				state.screen.blit(self.text(str(lives_left), False, text_color), [x+35, y+227+n*42])
				state.screen.blit(self.player_life_image, [x+18, y+227+n*42])

			state.screen.blit(self.flag_image, [x+17, y+280+75])
			state.screen.blit(self.text(str(self.stage), False, text_color), [x+35, y+312+75])


	def toggleEnemyFreeze(self, freeze = True):
		""" Freeze/defreeze all enemies """


		for enemy in state.enemies:
			enemy.paused = freeze
		self.timefreeze = freeze

	# def togglePlayersFreeze(self, freeze = True):
	# 	""" Freeze/defreeze all players """

	# 	global players

	# 	for player in players:
	# 		player.paralised = freeze

	def finishLevel(self):
		""" Finish current level
		Show earned scores and advance to the next stage
		"""


		# engine hum stops, moving tank's engine is still heard
		self.bg_sound = False
		if config.play_sounds:
			state.sounds["bg"].stop()

		state.gtimer.add(config.LEVEL_FINISH_TIMEOUT, lambda :self.endLevel(self.showMenu if self.demo else (self.nextLevel if self.mode == "endless" else self.showScores)), 1)

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
			if config.play_sounds:
				state.sounds["fire"].play()

	def setPlayersFrozen(self, freeze = True):
		""" Freeze/defreeze players by enemy timer bonus """
		self.players_frozen = freeze
		if not self.game_paused:
			self.togglePlayersFreeze(freeze)

	def togglePlayersFreeze(self, freeze = True):
		""" Freeze/defreeze all players """
		
		for player in state.players:
			player.paralised = freeze
			# player.paused = freeze

	def pause(self):
		""" Pause the game """
		
		if not self.game_paused:
			#print "Game paused"
			self.game_paused = True
			# self.toggleEnemyFreeze(True)
			pygame.mixer.stop()
			self.engine_sound = False
			if not config.DEBUG_UNFREEZE_PLAYERS_ON_PAUSE:
				self.togglePlayersFreeze(True)
			if config.play_sounds:
				state.sounds["pause"].play()
							
		else:
			#print "Game unpaused"
			self.game_paused = False
			# self.toggleEnemyFreeze(False)
			# keep players frozen if enemy timer bonus is still active
			self.togglePlayersFreeze(self.players_frozen)
			# keys could be pressed/released during pause
			for player in state.players:
				if player.controls:
					player.fire_pressed = player.controls[0] in self.held_keys
					player.pressed = [key in self.held_keys for key in player.controls[1:]]
			if self.bg_sound:
				self.playBackgroundSound()

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
		new_enemies = config.ENABLE_NEW_ENEMIES and self.mode != "versus"
		if new_enemies and level_number >= config.NEW_ENEMIES_FROM_STAGE:
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
		if new_enemies and not add and level_number % config.BOSS_EVERY_STAGES == 0:
			self.level.enemies_left.insert(0, Enemy.TYPE_BOSS)


	def nextLevel(self):
		""" Start next level """


		del state.bullets[:]
		del state.enemies[:]
		del state.bonuses[:]
		del state.labels[:]
		state.castle.rebuild()

		# versus: second castle at the top for player 2
		state.castle2 = None
		if self.mode == "versus":
			state.castle2 = Castle()
			state.castle2.rect.topleft = (12 * self.TILE_SIZE, 0)
			state.castle2.owner = 1
		del state.gtimer.timers[:]

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
		self.fortress_blink_start_timer = None
		self.fortress_blink_timer = None
		self.next_action = None

		# set number of enemies by types (basic, fast, power, armor) according to level
		self.loadLevelEnemies(False)

		self.engine_sound = False
		self.bg_sound = False
		if config.play_sounds:
			state.sounds["start"].play()
		state.gtimer.add(4330, lambda :self.playBackgroundSound(), 1)

		self.reloadPlayers()

		# NES: first enemy appears immediately, then after spawn interval
		self.spawn_timer = 0 if config.ENEMY_SPAWN_TIMEOUT == None else self.enemySpawnInterval()
		# ms since stage start: NES enemy AI changes goals with time
		self.level_time = 0
		if self.mode == "versus":
			state.gtimer.add(config.VERSUS_BONUS_TIMEOUT, lambda :self.spawnVersusBonus())

		# if True, start "game over" animation
		self.game_over = False

		# if False, game will end w/o "game over" bussiness
		self.running = True

		# if False, players won't be able to do anything
		self.active = True

		if config.FORTRESS_FOREVER > 0:
			self.level.buildFortress(self.level.TILE_STEEL)

		self.openCurtain()
		self.draw()

		while self.running:

			time_passed = self.clock.tick(config.GAME_FRAME_TIMING)
			self.updateGamepads()

			if self.game_paused and not config.DEBUG_UNFREEZE_PLAYERS_ON_PAUSE:
				for event in self.events():
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

			for event in self.events():
				# demo: any key returns to menu
				if self.demo:
					if event.type == pygame.QUIT:
						quit()
					elif event.type == pygame.KEYDOWN:
						self.stopDemo()
					continue
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
						config.play_sounds = not config.play_sounds
						if not config.play_sounds:
							pygame.mixer.stop()
							self.engine_sound = False
						elif self.bg_sound:
							self.playBackgroundSound()

					if self.game_paused and not config.DEBUG_UNFREEZE_PLAYERS_ON_PAUSE:
						continue

					# borrow life from active players
					if event.key == pygame.K_b:
						dead_player = None
						for player in state.players:
							if player.state == player.STATE_DEAD:
								dead_player = player
						
						if dead_player:
							for plr in state.players:
								if plr.state == plr.STATE_ALIVE and plr.lives >= 2:
									plr.lives -= 1
									dead_player.lives += 1
									dead_player.superpowers = config.PLAYER_START_SUPERPOWER
									self.respawnPlayer(dead_player)
									break

					for player in state.players:
						# keys pressed during spawn animation work when tank appears
						if player.state in (player.STATE_ALIVE, player.STATE_SPAWNING):
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
					for player in state.players:
						# keys pressed during spawn animation work when tank appears
						if player.state in (player.STATE_ALIVE, player.STATE_SPAWNING):
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

			if self.demo:
				self.demoControl()
			else:
				self.applyGamepads()

			engine_moving = False
			for player in state.players:
				if player.state == player.STATE_ALIVE and not self.game_over and self.active:
					# keyboard or gamepad
					pressed = [player.pressed[i] or player.pad_pressed[i] for i in range(4)]
					fire_pressed = player.fire_pressed or player.pad_fire
					if (True in pressed or player.slide > 0) and not player.paralised:
						engine_moving = True

					# auto fire while fire button is held: shoot as soon as a bullet slot is free
					if config.AUTO_FIRE and fire_pressed and pygame.time.get_ticks() - player.last_fire_time >= config.PLAYER_AUTO_FIRE_DELAY:
						self.playerFire(player)

					# ice like on NES: tank starting to move on ice slides ICE_SLIDE_DISTANCE, first part of it
					# buttons are ignored, the rest is slid after release. Sliding stops when tank leaves ice
					on_ice = player.onIce()
					if not on_ice:
						player.slide = 0
					if player.slide > config.ICE_CONTROL_DISTANCE:
						player.slide = player.slide - player.speed if player.move(player.direction) else 0
					elif True in pressed:
						# first pressed in order: up, right, down, left
						direction = [self.DIR_UP, self.DIR_RIGHT, self.DIR_DOWN, self.DIR_LEFT][pressed.index(True)]
						moved = player.move(direction)
						if on_ice and player.slide <= 0:
							player.slide = config.ICE_SLIDE_DISTANCE
							if config.play_sounds:
								state.sounds["ice"].play()
						elif player.slide > 0:
							player.slide = player.slide - player.speed if moved else 0
					elif player.slide > 0:
						player.slide = player.slide - player.speed if player.move(player.direction) else 0
				player.update(time_passed)

			self.updateEngineSound(engine_moving)

			self.level_time += time_passed

			# enemy spawn timer: when no place for new enemy, it appears as soon as place is free (NES)
			if not self.game_over and self.active:
				self.spawn_timer -= time_passed
				if self.spawn_timer <= 0:
					self.spawn_timer = self.enemySpawnInterval() if self.spawnEnemy() else 0

			for enemy in state.enemies[:]:
				if enemy.state == enemy.STATE_ALIVE:
						if enemy.bonus_aquired != None:
							self.triggerEnemyBonus(enemy.bonus_aquired, enemy)
							enemy.bonus_aquired = None
				if enemy.state == enemy.STATE_DEAD and not self.game_over and self.active:
					state.enemies.remove(enemy)
					if len(self.level.enemies_left) == 0 and len(state.enemies) == 0:
						self.finishLevel()
				else:
					enemy.update(time_passed)

			if not self.game_over and self.active:
				for player in state.players:
					# extra life every EXTRA_LIFE_SCORE points
					if config.EXTRA_LIFE_SCORE > 0:
						while player.score >= player.next_extra_life:
							player.lives += 1
							if config.EXTRA_LIFE_ONCE:
								# NES: only one extra life
								player.next_extra_life = 10 ** 9
							else:
								player.next_extra_life += config.EXTRA_LIFE_SCORE
							if config.play_sounds:
								state.sounds["life"].play()

					if player.state == player.STATE_ALIVE:
						if player.bonus != None and player.side == player.SIDE_PLAYER:
							self.triggerBonus(player.bonus, player)
							player.bonus = None
					elif player.state == player.STATE_DEAD:
						if not config.PLAYER_INFINITE_LIVES and player.lives > 0:
							player.lives -= 1
						if player.lives > 0:
							player.superpowers = config.PLAYER_START_SUPERPOWER
							self.respawnPlayer(player)
						elif self.mode == "versus":
							# versus: player without lives loses
							self.versusOver(1 - state.players.index(player))
						else:
							total_lives = 0
							for plr in state.players:
								total_lives += plr.lives
							if total_lives <= 0:
									self.gameOver()

			for bullet in state.bullets[:]:
				if bullet.state == bullet.STATE_REMOVED:
					state.bullets.remove(bullet)
				else:
					bullet.update()

			for bonus in state.bonuses[:]:
				if bonus.active == False:
					state.bonuses.remove(bonus)

			for label in state.labels[:]:
				if not label.active:
					state.labels.remove(label)

			if not self.game_over:
				if self.mode == "versus":
					# destroyed castle loses
					for target in self.castles():
						if not target.active:
							self.versusOver(1 - target.owner)
							break
				elif not state.castle.active:
					self.gameOver()

			state.gtimer.update(time_passed)

			self.draw()

		return self.next_action
