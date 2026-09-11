# coding=utf-8
""" Battle City: game screens and main loop """

import os, random, uuid, sys, json
import pygame
from pygame.locals import *
from sys import exit as quit	# builtin quit() is missing in Mac app (PyInstaller)

from battlecity import config, state
from battlecity.bonus import Bonus
from battlecity.castle import Castle
from battlecity.effects import Label
from battlecity.gamepad import Gamepad, sdl_controller
from battlecity.level import Level
from battlecity.tank import Enemy, Player

class Game():

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

		state.enemy_spawn_pos_index = 2

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
		""" Give gamepads to players: players without keyboard controls (P3) first, then P1, P2 """
		for player in state.players:
			player.gamepad = None
		ordered = [player for player in state.players if not player.controls] + [player for player in state.players if player.controls]
		for gamepad, player in zip(self.gamepads, ordered):
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

	def showStageScreen(self):
		""" Grey "STAGE N" screen before level starts, like on NES """


		if config.STAGE_SCREEN_TIME <= 0:
			return

		self.stage_screen = True
		state.screen.fill([99, 99, 99])
		if self.mode == "endless":
			title = "WAVE " + str(self.stage - self.first_stage + 1)
		elif self.mode == "versus":
			title = "VERSUS"
		else:
			title = "STAGE " + str(self.stage)
		text = self.font.render(title, False, pygame.Color("black"))
		state.screen.blit(text, [(416 - text.get_width()) // 2, (416 - text.get_height()) // 2])

		for i in range(config.STAGE_SCREEN_TIME // 20):
			self.flip()
			self.delay(50)

		self.stage_screen = False

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


		print("Game Over")
		self.deleteSavedGame()
		if config.play_sounds:
			for sound in state.sounds:
				state.sounds[sound].stop()
			state.sounds["gameover"].play()

		self.game_over_y = 416+40

		self.game_over = True
		state.gtimer.add(config.GAME_OVER_TIMEOUT, lambda :self.endLevel(self.showScores), 1)

	def gameOverScreen(self):
		""" Show game over screen """


		# stop game main loop (if any)
		self.running = False

		state.screen.fill([0, 0, 0])

		self.recordHiscores()

		state.screen.fill([0, 0, 0])
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
			for event in self.events():
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


		# stop game main loop (if any)
		self.running = False

		# clear all timers
		del state.gtimer.timers[:]

		# set current stage to 0
		self.stage = config.START_LEVEL - 1

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

			for event in self.events():
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
					self.stage = config.START_LEVEL - 1
					del state.players[:]
					return self.nextLevel
				elif action == "editor":
					state.castle.rebuild()
					if self.showEditor() == "play":
						# play edited level
						self.mode = "campaign"
						self.nr_of_players = 1
						del state.players[:]
						return self.nextLevel
					self.drawIntroScreen()
				elif action == "versus":
					self.mode = "versus"
					self.nr_of_players = 2
					self.stage = 0
					self.versus_winner = None
					del state.players[:]
					return self.nextLevel
				elif action == "endless":
					self.mode = "endless"
					self.nr_of_players = argument
					self.stage = config.START_LEVEL - 1
					self.first_stage = config.START_LEVEL
					del state.players[:]
					return self.nextLevel
				elif action == "continue":
					if self.loadGame():
						del state.players[:]
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
			with open(config.levelFile(level_nr), "r") as f:
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
		directory = config.dataFile(config.CUSTOM_LEVELS_DIR)
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
			os.remove(os.path.join(config.dataFile(config.CUSTOM_LEVELS_DIR), str(level_nr)))
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

			for event in self.events():
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

		state.screen.fill([0, 0, 0])
		level.draw()
		state.castle.draw()

		grid_color = (40, 40, 40)
		for i in range(27):
			pygame.draw.line(state.screen, grid_color, [i * 16, 0], [i * 16, 416])
			pygame.draw.line(state.screen, grid_color, [0, i * 16], [416, i * 16])

		for col, row in self.EDITOR_PROTECTED:
			pygame.draw.rect(state.screen, (120, 30, 30), [col * 16, row * 16, 32, 32], 1)

		pygame.draw.rect(state.screen, (255, 200, 0), [cursor[0] * 16, cursor[1] * 16, 16, 16], 1)

		# sidebar: level, brush, hints
		state.screen.fill([100, 100, 100], pygame.Rect([416, 0], [64, 416]))
		font = Label.getFont()
		black = pygame.Color("black")

		state.screen.blit(font.render("EDITOR", False, black), [420, 8])
		state.screen.blit(font.render("LVL %d%s" % (level_nr, "*" if modified else ""), False, black), [420, 24])

		tile_images = {"#": level.tile_brick, "@": level.tile_steel, "~": level.tile_water, "%": level.tile_grass, "-": level.tile_froze}
		char, name = self.EDITOR_TILES[brush]
		if char in tile_images:
			state.screen.blit(tile_images[char], [440, 44])
		else:
			pygame.draw.rect(state.screen, black, [440, 44, 16, 16], 1)
		state.screen.blit(font.render(name, False, black), [420, 66])

		hints = ["1-5 TILE", "0 ERASE", "SPC DRAW", "S SAVE", "D RESET", "[ ] LVL", "T TEST", "ESC MENU"]
		for i, hint in enumerate(hints):
			state.screen.blit(font.render(hint, False, black), [418, 100 + i * 14])

		self.flip()

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

	def showVersusResult(self):
		""" Versus result screen: winner and kills. Any key / gamepad button returns to menu """

		self.running = False
		del state.gtimer.timers[:]

		state.screen.fill([0, 0, 0])
		white = pygame.Color("white")
		yellow = pygame.Color(255, 200, 0)

		def center(text, y, color):
			surface = self.font.render(text, False, color)
			state.screen.blit(surface, [(480 - surface.get_width()) // 2, y])

		center(["I", "II"][self.versus_winner] + "-PLAYER WINS", 150, yellow)
		center("KILLS  I: %d  II: %d" % (state.players[0].versus_kills, state.players[1].versus_kills), 200, white)
		center("ENTER - MENU", 300, white)

		for frame in range(10000 // 20):
			self.flip()
			self.clock.tick(50)
			self.updateGamepads()
			for gamepad in self.gamepads:
				if gamepad.pressed("fire") or gamepad.pressed("start"):
					return self.showMenu
			for event in self.events():
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
			with open(config.dataFile(config.HISCORES_FILE), "r") as f:
				data = json.load(f)
			for mode in tables:
				tables[mode] = [[str(entry[0])[:3], int(entry[1])] for entry in data.get(mode, [])][:config.HISCORES_COUNT]
		except (IOError, ValueError, TypeError, AttributeError, IndexError):
			pass
		return tables

	def saveHiscores(self, tables):
		try:
			with open(config.dataFile(config.HISCORES_FILE), "w") as f:
				json.dump(tables, f, indent=1)
		except IOError:
			print("Can't save hiscores")

	def qualifiesForHiscores(self, table, score):
		return score > 0 and (len(table) < config.HISCORES_COUNT or score > table[-1][1])

	def recordHiscores(self):
		""" After game over players with good score enter their names, then hiscore table is shown """
		tables = self.loadHiscores()
		if self.mode not in tables:
			return
		table = tables[self.mode]

		entered = False
		for player_nr, player in enumerate(state.players):
			if self.qualifiesForHiscores(table, player.score):
				table.append([self.enterName(player_nr, player.score), player.score])
				# stable sort: earlier entry with the same score stays higher
				table.sort(key=lambda entry: -entry[1])
				del table[config.HISCORES_COUNT:]
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

			for event in self.events():
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
				else:
					# with non latin layout take letter from layout independent key code
					char = event.unicode.upper() if event.unicode else ""
					if char not in letters and (pygame.K_a <= event.key <= pygame.K_z or pygame.K_0 <= event.key <= pygame.K_9):
						char = chr(event.key).upper()
					if char and char in letters:
						name[position] = letters.index(char)
						move = 1

			name[position] = (name[position] + change) % len(letters)
			position = max(0, min(len(name) - 1, position + move))

			if done:
				return "".join([letters[i] for i in name])

	def drawNameEntry(self, player_nr, score, name, position):

		state.screen.fill([0, 0, 0])
		white = pygame.Color("white")
		yellow = pygame.Color(255, 200, 0)

		def center(text, y, color):
			surface = self.font.render(text, False, color)
			state.screen.blit(surface, [(480 - surface.get_width()) // 2, y])

		center("NEW HIGH SCORE", 80, yellow)
		center(["I", "II", "III"][player_nr] + "-PLAYER  " + str(score), 120, white)
		center("ENTER YOUR NAME", 180, white)

		# big letters with cursor under current one
		x = (480 - 3 * 40) // 2
		for i, letter in enumerate(name):
			surface = pygame.transform.scale(self.font.render(letter, False, white), [32, 32])
			state.screen.blit(surface, [x + i * 40, 220])
			if i == position:
				pygame.draw.rect(state.screen, yellow, [x + i * 40, 256, 32, 4])

		center("ENTER - DONE", 320, white)
		self.flip()

	def showHiscores(self, mode, duration):
		""" Show hiscore table for duration ms or until key / gamepad button is pressed """

		table = self.loadHiscores().get(mode, [])
		state.screen.fill([0, 0, 0])
		white = pygame.Color("white")
		yellow = pygame.Color(255, 200, 0)

		title = self.font.render("HIGH SCORES - " + mode.upper(), False, yellow)
		state.screen.blit(title, [(480 - title.get_width()) // 2, 40])
		for i, entry in enumerate(table):
			row = "%2d. %-3s %8d" % (i + 1, entry[0], entry[1])
			state.screen.blit(self.font.render(row, False, white), [96, 90 + i * 28])

		for frame in range(duration // 20):
			self.flip()
			self.clock.tick(50)
			self.updateGamepads()
			for gamepad in self.gamepads:
				if gamepad.pressed("fire") or gamepad.pressed("start"):
					return
			for event in self.events():
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
			"preset": config.CURRENT_PRESET,
			"players": [{
				"score": player.score,
				"lives": player.lives,
				"superpowers": player.superpowers,
				"next_extra_life": player.next_extra_life
			} for player in state.players],
		}
		try:
			with open(config.dataFile(config.SAVEGAME_FILE), "w") as f:
				json.dump(data, f, indent=1)
		except IOError:
			print("Can't save game")

	def loadGame(self):
		""" Load saved progress, game continues from the stage after saved one
		@return boolean Whether game was loaded
		"""
		try:
			with open(config.dataFile(config.SAVEGAME_FILE), "r") as f:
				data = json.load(f)
			stage = int(data["stage"])
			nr_of_players = int(data["nr_of_players"])
			stats = [{
				"score": int(player["score"]),
				"lives": int(player["lives"]),
				"superpowers": int(player["superpowers"]),
				"next_extra_life": int(player.get("next_extra_life", config.EXTRA_LIFE_SCORE))
			} for player in data["players"]]
		except (IOError, ValueError, KeyError, TypeError, AttributeError):
			print("Can't load saved game")
			return False

		if nr_of_players not in (1, 2, 3) or len(stats) != nr_of_players or stage < 0:
			print("Saved game is broken")
			return False

		if data.get("preset") in config.PRESETS:
			config.applyPreset(data["preset"])
		self.mode = "campaign"
		self.stage = stage
		self.nr_of_players = nr_of_players
		self.loaded_players_stats = stats
		return True

	def deleteSavedGame(self):
		""" Saved game is useless after game over """
		try:
			os.remove(config.dataFile(config.SAVEGAME_FILE))
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
		if os.path.isfile(config.dataFile(config.SAVEGAME_FILE)):
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
			{"label": "DIFFICULTY", "value": config.CURRENT_PRESET or "CUSTOM", "type": "preset"},
			{"label": "SOUND", "value": "ON" if config.play_sounds else "OFF", "type": "sound"},
			{"label": "FULL SCREEN", "value": "ON" if self.is_fullscreen else "OFF", "type": "fullscreen"},
			{"label": "START LEVEL", "value": str(config.START_LEVEL), "type": "level"},
		]
		control_names = ["FIRE", "UP", "RIGHT", "DOWN", "LEFT"]
		for player_nr in range(len(config.PLAYER_CONTROLS)):
			for control in range(5):
				items.append({
					"label": "P%d %s" % (player_nr + 1, control_names[control]),
					"value": pygame.key.name(config.PLAYER_CONTROLS[player_nr][control]).upper(),
					"type": "control", "player": player_nr, "control": control
				})
		# frame rate of NES version: speeds and timings
		items.append({"label": "NES SPEED", "value": config.NES_VERSION, "type": "nes"})
		items.append({"label": "AUTO FIRE", "value": "ON" if config.AUTO_FIRE else "OFF", "type": "autofire"})
		items.append({"label": "ENEMY AI", "value": config.ENEMY_AI, "type": "ai"})
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

			for event in self.events():
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
					config.saveSettings(self.is_fullscreen)
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


		if kind == "preset":
			names = ["CLASSIC", "GOOD", "EXTREME"]
			index = names.index(config.CURRENT_PRESET) if config.CURRENT_PRESET in names else -change
			config.applyPreset(names[(index + change) % len(names)])
		elif kind == "sound":
			# sounds couldn't be loaded: nothing to switch on
			if state.sounds:
				config.play_sounds = not config.play_sounds
				if not config.play_sounds:
					pygame.mixer.stop()
		elif kind == "fullscreen":
			self.toggleFullScreen()
		elif kind == "autofire":
			config.AUTO_FIRE = not config.AUTO_FIRE
		elif kind == "ai":
			names = config.ENEMY_AI_TYPES
			index = names.index(config.ENEMY_AI) if config.ENEMY_AI in names else 0
			config.ENEMY_AI = names[(index + change) % len(names)]
		elif kind == "nes":
			names = sorted(config.NES_VERSIONS)
			index = names.index(config.NES_VERSION) if config.NES_VERSION in names else 0
			config.applyNesVersion(names[(index + change) % len(names)])
		elif kind == "level":
			config.START_LEVEL = (config.START_LEVEL - 1 + change) % 35 + 1
			self.stage = config.START_LEVEL - 1
		elif kind == "reset":
			config.PLAYER_CONTROLS = [list(controls) for controls in config.DEFAULT_PLAYER_CONTROLS]

		config.saveSettings(self.is_fullscreen)

	def setControl(self, player_nr, control, key):
		""" Assign key to player's control. Control already using this key gets the old key (swap) """
		old_key = config.PLAYER_CONTROLS[player_nr][control]
		for controls in config.PLAYER_CONTROLS:
			for i in range(len(controls)):
				if controls[i] == key:
					controls[i] = old_key
		config.PLAYER_CONTROLS[player_nr][control] = key
		config.saveSettings(self.is_fullscreen)

	def drawSettings(self, items, selected, waiting_key):
		""" Draw settings screen """


		state.screen.fill([0, 0, 0])
		white = pygame.Color("white")
		yellow = pygame.Color(255, 200, 0)

		title = self.font.render("SETTINGS", False, white)
		state.screen.blit(title, [(480 - title.get_width()) // 2, 16])

		for i, item in enumerate(items):
			y = 52 + i * 20
			color = yellow if i == selected else white
			if i == selected:
				state.screen.blit(self.font.render(">", False, yellow), [16, y])
			state.screen.blit(self.font.render(item["label"], False, color), [40, y])
			value = "PRESS KEY" if i == selected and waiting_key else item["value"]
			if value:
				state.screen.blit(self.font.render(value[:10], False, color), [288, y])

		self.flip()

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

	def showScores(self):
		""" Show level scores """


		# stop game main loop (if any)
		self.running = False

		# clear all timers
		del state.gtimer.timers[:]

		if config.play_sounds:
			for sound in state.sounds:
				state.sounds[sound].stop()

		# 2+ players: player who destroyed most tanks on this stage gets bonus points (like on NES)
		kills_bonus_player = None
		if self.nr_of_players >= 2 and config.TWO_PLAYER_KILLS_BONUS > 0 and not self.game_over:
			kills = [sum(player.trophies.values()) - player.trophies["bonus"] for player in state.players]
			best_kills = max(kills)
			# NES: only player with lives left gets the bonus
			if best_kills > 0 and kills.count(best_kills) == 1 and state.players[kills.index(best_kills)].lives > 0:
				kills_bonus_player = kills.index(best_kills)
				state.players[kills_bonus_player].score += config.TWO_PLAYER_KILLS_BONUS

		hiscore = self.loadHiscore()

		# update hiscore if needed
		best_score = max([player.score for player in state.players])
		if best_score > hiscore:
			hiscore = best_score
			self.saveHiscore(hiscore)

		img_tanks = [
			state.sprites.subsurface(32*2, 0, 13*2, 15*2),
			state.sprites.subsurface(48*2, 0, 13*2, 15*2),
			state.sprites.subsurface(64*2, 0, 13*2, 15*2),
			state.sprites.subsurface(80*2, 0, 13*2, 15*2)
		]

		img_arrows = [
			state.sprites.subsurface(81*2, 48*2, 7*2, 7*2),
			state.sprites.subsurface(88*2, 48*2, 7*2, 7*2)
		]

		state.screen.fill([0, 0, 0])

		# colors
		black = pygame.Color("black")
		white = pygame.Color("white")
		purple = pygame.Color(127, 64, 64)
		pink = pygame.Color(191, 160, 128)

		state.screen.blit(self.font.render("HI-SCORE", False, purple), [105, 35])
		state.screen.blit(self.font.render(str(hiscore), False, pink), [295, 35])

		state.screen.blit(self.font.render("STAGE"+str(self.stage).rjust(3), False, white), [170, 65])

		state.screen.blit(self.font.render("I-PLAYER", False, purple), [25, 95])

		#player 1 global score
		state.screen.blit(self.font.render(str(state.players[0].score).rjust(8), False, pink), [25, 125])

		if self.nr_of_players >= 2:
			state.screen.blit(self.font.render("II-PLAYER", False, purple), [310, 95])

			#player 2 global score
			state.screen.blit(self.font.render(str(state.players[1].score).rjust(8), False, pink), [325, 125])

		# tanks and arrows
		for i in range(4):
			state.screen.blit(img_tanks[i], [226, 160+(i*45)])
			state.screen.blit(img_arrows[0], [206, 168+(i*45)])
			if self.nr_of_players >= 2:
				state.screen.blit(img_arrows[1], [258, 168+(i*45)])

		state.screen.blit(self.font.render("TOTAL", False, white), [70, 335])

		# total underline
		pygame.draw.line(state.screen, white, [170, 330], [307, 330], 4)

		self.flip()

		# pauses in NES frames
		self.delayFrames(30)

		# points and kills
		for i in range(4):

			# total specific tanks
			tanks = state.players[0].trophies["enemy"+str(i)]

			for n in range(tanks+1):
				if n > 0 and config.play_sounds:
					state.sounds["score"].play()

				# erase previous text
				state.screen.blit(self.font.render(str(n-1).rjust(2), False, black), [170, 168+(i*45)])
				# print new number of enemies
				state.screen.blit(self.font.render(str(n).rjust(2), False, white), [170, 168+(i*45)])
				# erase previous text
				state.screen.blit(self.font.render(str((n-1) * (i+1) * 100).rjust(4)+" PTS", False, black), [25, 168+(i*45)])
				# print new total points per enemy
				state.screen.blit(self.font.render(str(n * (i+1) * 100).rjust(4)+" PTS", False, white), [25, 168+(i*45)])
				self.flip()
				self.delayFrames(8)

			if self.nr_of_players >= 2:
				tanks = state.players[1].trophies["enemy"+str(i)]

				for n in range(tanks+1):

					if n > 0 and config.play_sounds:
						state.sounds["score"].play()

					state.screen.blit(self.font.render(str(n-1).rjust(2), False, black), [277, 168+(i*45)])
					state.screen.blit(self.font.render(str(n).rjust(2), False, white), [277, 168+(i*45)])

					state.screen.blit(self.font.render(str((n-1) * (i+1) * 100).rjust(4)+" PTS", False, black), [325, 168+(i*45)])
					state.screen.blit(self.font.render(str(n * (i+1) * 100).rjust(4)+" PTS", False, white), [325, 168+(i*45)])

					self.flip()
					self.delayFrames(8)

			self.delayFrames(20)

		self.delayFrames(30)

		# total tanks
		tanks = sum([i for i in state.players[0].trophies.values()]) - state.players[0].trophies["bonus"]
		state.screen.blit(self.font.render(str(tanks).rjust(2), False, white), [170, 335])
		if self.nr_of_players >= 2:
			tanks = sum([i for i in state.players[1].trophies.values()]) - state.players[1].trophies["bonus"]
			state.screen.blit(self.font.render(str(tanks).rjust(2), False, white), [277, 335])

		# third player: short table, there is no room for detailed one
		if self.nr_of_players == 3:
			state.screen.blit(self.font.render("III-PLAYER", False, purple), [25, 375])
			state.screen.blit(self.font.render(str(state.players[2].score).rjust(8), False, pink), [325, 375])
			kills = [state.players[2].trophies["enemy" + str(i)] for i in range(4)]
			kills_text = "KILLS " + " ".join([str(k) for k in kills]) + " = " + str(sum(kills))
			state.screen.blit(self.font.render(kills_text, False, white), [25, 395])

		if kills_bonus_player != None:
			player_names = ["I", "II", "III"]
			bonus_text = self.font.render(player_names[kills_bonus_player] + "-PLAYER BONUS " + str(config.TWO_PLAYER_KILLS_BONUS), False, white)
			state.screen.blit(bonus_text, [(480 - bonus_text.get_width()) // 2, 355])

		self.flip()

		self.delayFrames(15)
		self.delayFrames(120)

		if self.game_over:
			return self.gameOverScreen
		else:
			self.saveGame()
			return self.nextLevel


	def draw(self):

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
			state.screen.blit(self.im_pause, [176, 188])

		if self.game_over:
			if self.game_over_y > 188:
				self.game_over_y -= config.GAME_OVER_TEXT_SPEED
			state.screen.blit(self.im_game_over, [176, self.game_over_y]) # 176=(416-64)/2

		self.drawSidebar()

		if config.DEBUG_DRAW_MESH:
			self.drawMesh()

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
			state.screen.blit(self.font.render("+"+str(hidden_enemies), False, pygame.Color('black')), [x+4, ypos])

		# players' lives
		if pygame.font.get_init():
			text_color = pygame.Color('black')
			for n in range(len(state.players)):
				lives_left = state.players[n].lives - 1
				if lives_left < 0:
					lives_left = 0 
				state.screen.blit(self.font.render(str(n+1)+"P", False, text_color), [x+20, y+210+n*42])
				state.screen.blit(self.font.render(str(lives_left), False, text_color), [x+35, y+227+n*42])
				state.screen.blit(self.player_life_image, [x+18, y+227+n*42])

			state.screen.blit(self.flag_image, [x+17, y+280+75])
			state.screen.blit(self.font.render(str(self.stage), False, text_color), [x+35, y+312+75])


	def drawIntroScreen(self, put_on_surface = True):
		""" Draw intro (menu) screen
		@param boolean put_on_surface If True, flip display after drawing
		@return None
		"""


		state.screen.fill([0, 0, 0])

		items = self.menuItems()
		self.menu_index = min(self.menu_index, len(items) - 1)

		if pygame.font.get_init():

			hiscore = self.loadHiscore()

			state.screen.blit(self.font.render("HI- "+str(hiscore), True, pygame.Color('white')), [170, 35])

			for i, item in enumerate(items):
				state.screen.blit(self.font.render(item[0], True, pygame.Color('white')), [165, 228 + i * 20])

		# selected item marker
		marker = self.player_image if self.menu_index == 0 else self.player_image_green
		state.screen.blit(marker, [125, 223 + self.menu_index * 20])

		self.writeInBricks("battle", [65, 80])
		self.writeInBricks("city", [129, 160])

		if put_on_surface:
			self.flip()

	def animateIntroScreen(self):
		""" Slide intro (menu) screen from bottom to top
		If Enter key is pressed, finish animation immediately
		@return None
		"""


		self.drawIntroScreen(False)
		screen_cp = state.screen.copy()

		state.screen.fill([0, 0, 0])

		y = 416
		while (y > 0):
			time_passed = self.clock.tick(50)
			for event in self.events():
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_RETURN or event.key == pygame.K_DOWN:
						y = 0
						break

			state.screen.blit(screen_cp, [0, y])
			self.flip()
			y -= 5

		state.screen.blit(screen_cp, [0, 0])
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


		bricks = state.sprites.subsurface(56*2, 64*2, 8*2, 8*2)
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
			state.screen.blit(surf_letter, [abs_x, abs_y])
			abs_x += letter_w + 16

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

	def loadHiscore(self):
		""" Load hiscore
		Really primitive version =] If for some reason hiscore cannot be loaded, return 20000
		@return int
		"""
		filename = config.dataFile(".hiscore")
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
			f = open(config.dataFile(".hiscore"), "w")
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


		if config.play_sounds:
			state.sounds["bg"].stop()

		state.gtimer.add(config.LEVEL_FINISH_TIMEOUT, lambda :self.endLevel(self.nextLevel if self.mode == "endless" else self.showScores), 1)

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
			if config.play_sounds:
				state.sounds["bg"].play(-1)

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

		if config.play_sounds:
			state.sounds["start"].play()
			state.gtimer.add(4330, lambda :state.sounds["bg"].play(-1), 1)

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
						else:
							state.sounds["bg"].play(-1)

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

			self.applyGamepads()

			for player in state.players:
				if player.state == player.STATE_ALIVE and not self.game_over and self.active:
					# keyboard or gamepad
					pressed = [player.pressed[i] or player.pad_pressed[i] for i in range(4)]
					fire_pressed = player.fire_pressed or player.pad_fire

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
