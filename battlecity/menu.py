# coding=utf-8
""" Battle City: main menu, intro screen and demo """

import os, random, uuid, sys, json
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

class MenuMixin():
	""" Part of Game class """

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

		self.demo = False

		self.animateIntroScreen()

		# ms without input: demo starts after DEMO_IDLE_TIME
		idle = 0

		while True:
			time_passed = self.clock.tick(50)
			idle += time_passed

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
					idle = 0
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

			if move != 0 or activate:
				idle = 0
			elif config.DEMO_IDLE_TIME > 0 and idle >= config.DEMO_IDLE_TIME:
				return self.startDemo()

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

	def startDemo(self):
		""" Demo: computer plays 2 player game on random stage until key is pressed or DEMO_TIME passes """
		self.demo = True
		self.mode = "campaign"
		self.nr_of_players = 2
		self.stage = random.randint(0, 34)
		self.loaded_players_stats = None
		del state.players[:]
		return self.nextLevel

	def stopDemo(self):
		""" Leave demo to main menu """
		pygame.mixer.stop()
		self.endLevel(self.showMenu)

	def demoControl(self):
		""" Demo: gamepad button returns to menu, computer drives players and fires """
		for gamepad in self.gamepads:
			if gamepad.pressed("fire") or gamepad.pressed("start"):
				self.stopDemo()
		if self.level_time >= config.DEMO_TIME:
			self.stopDemo()

		for player in state.players:
			player.pad_pressed = [False] * 4
			player.pad_fire = False
			if player.state != player.STATE_ALIVE:
				continue
			frames = getattr(player, "demo_frames", 0)
			stuck = getattr(player, "demo_position", None) == player.rect.topleft
			# new direction after a while or when stuck
			if frames <= 0 or (stuck and random.randint(0, 3) == 0):
				enemies = [enemy for enemy in state.enemies if enemy.state == enemy.STATE_ALIVE]
				if enemies and random.randint(0, 1):
					# towards nearest enemy along longer axis
					enemy = min(enemies, key=lambda e: abs(e.rect.centerx - player.rect.centerx) + abs(e.rect.centery - player.rect.centery))
					dx, dy = enemy.rect.centerx - player.rect.centerx, enemy.rect.centery - player.rect.centery
					if abs(dx) > abs(dy):
						player.demo_direction = self.DIR_RIGHT if dx > 0 else self.DIR_LEFT
					else:
						player.demo_direction = self.DIR_DOWN if dy > 0 else self.DIR_UP
				else:
					player.demo_direction = random.randint(0, 3)
				frames = random.randint(25, 100)
			player.demo_frames = frames - 1
			player.demo_position = player.rect.topleft
			player.pressed = [direction == player.demo_direction for direction in range(4)]
			player.fire_pressed = False
			if player.demo_frames % 6 == 0:
				self.playerFire(player)

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

			state.screen.blit(self.text("HI- "+str(hiscore), True, pygame.Color('white')), [170, 35])

			for i, item in enumerate(items):
				state.screen.blit(self.text(item[0], True, pygame.Color('white')), [165, 228 + i * 20])

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
