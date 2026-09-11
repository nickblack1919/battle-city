# coding=utf-8
""" Battle City: stage, scores, game over, versus result, hiscores screens and saved game """

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

class ScreensMixin():
	""" Part of Game class """

	CURTAIN_COLOR = (99, 99, 99)

	def showStageScreen(self):
		""" Before level starts, like on NES: grey curtain closes from top and bottom over the screen,
		then grey "STAGE N" screen """


		if config.STAGE_SCREEN_TIME <= 0:
			return

		self.stage_screen = True

		# menu, scores or previous stage stays under the curtain
		background = state.screen.copy()
		for frame in range(1, config.CURTAIN_FRAMES + 1):
			self.drawCurtain(background, frame / float(config.CURTAIN_FRAMES))
			self.flip()
			self.delayFrames(1)

		state.screen.fill(self.CURTAIN_COLOR)
		if self.mode == "endless":
			title = "WAVE " + str(self.stage - self.first_stage + 1)
		elif self.mode == "versus":
			title = "VERSUS"
		else:
			title = "STAGE " + str(self.stage)
		text = self.text(title, False, pygame.Color("black"))
		state.screen.blit(text, [(416 - text.get_width()) // 2, (416 - text.get_height()) // 2])

		for i in range(config.STAGE_SCREEN_TIME // 20):
			self.flip()
			self.delay(50)

		self.stage_screen = False

	def openCurtain(self):
		""" NES: grey curtain opens from the middle of the screen showing the stage """
		if config.STAGE_SCREEN_TIME <= 0:
			return

		self.stage_screen = True
		self.draw(False)
		background = state.screen.copy()
		for frame in range(config.CURTAIN_FRAMES - 1, -1, -1):
			self.drawCurtain(background, frame / float(config.CURTAIN_FRAMES))
			self.flip()
			self.delayFrames(1)
		self.stage_screen = False

	def drawCurtain(self, background, closed):
		""" Draw background with grey curtain: closed 0 - open, 1 - whole screen is grey """
		state.screen.blit(background, [0, 0])
		height = int(round(208 * closed))
		state.screen.fill(self.CURTAIN_COLOR, [0, 0, 480, height])
		state.screen.fill(self.CURTAIN_COLOR, [0, 416 - height, 480, height])

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

	def showVersusResult(self):
		""" Versus result screen: winner and kills. Any key / gamepad button returns to menu """

		self.running = False
		del state.gtimer.timers[:]

		state.screen.fill([0, 0, 0])
		white = pygame.Color("white")
		yellow = pygame.Color(255, 200, 0)

		def center(text, y, color):
			surface = self.text(text, False, color)
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
		# bot's score doesn't count
		best_score = max([player.score for player in state.players if not player.bot] or [0])
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

		state.screen.blit(self.text("HI-SCORE", False, purple), [105, 35])
		state.screen.blit(self.text(str(hiscore), False, pink), [295, 35])

		state.screen.blit(self.text("STAGE"+str(self.stage).rjust(3), False, white), [170, 65])

		state.screen.blit(self.text("I-PLAYER", False, purple), [25, 95])

		#player 1 global score
		state.screen.blit(self.text(str(state.players[0].score).rjust(8), False, pink), [25, 125])

		if self.nr_of_players >= 2:
			if state.players[1].bot:
				state.screen.blit(self.text("BOT", False, purple), [350, 95])
			else:
				state.screen.blit(self.text("II-PLAYER", False, purple), [310, 95])

			#player 2 global score
			state.screen.blit(self.text(str(state.players[1].score).rjust(8), False, pink), [325, 125])

		# tanks and arrows
		for i in range(4):
			state.screen.blit(img_tanks[i], [226, 160+(i*45)])
			state.screen.blit(img_arrows[0], [206, 168+(i*45)])
			if self.nr_of_players >= 2:
				state.screen.blit(img_arrows[1], [258, 168+(i*45)])

		state.screen.blit(self.text("TOTAL", False, white), [70, 335])

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
				state.screen.blit(self.text(str(n-1).rjust(2), False, black), [170, 168+(i*45)])
				# print new number of enemies
				state.screen.blit(self.text(str(n).rjust(2), False, white), [170, 168+(i*45)])
				# erase previous text
				state.screen.blit(self.text(str((n-1) * (i+1) * 100).rjust(4)+" PTS", False, black), [25, 168+(i*45)])
				# print new total points per enemy
				state.screen.blit(self.text(str(n * (i+1) * 100).rjust(4)+" PTS", False, white), [25, 168+(i*45)])
				self.flip()
				self.delayFrames(8)

			if self.nr_of_players >= 2:
				tanks = state.players[1].trophies["enemy"+str(i)]

				for n in range(tanks+1):

					if n > 0 and config.play_sounds:
						state.sounds["score"].play()

					state.screen.blit(self.text(str(n-1).rjust(2), False, black), [277, 168+(i*45)])
					state.screen.blit(self.text(str(n).rjust(2), False, white), [277, 168+(i*45)])

					state.screen.blit(self.text(str((n-1) * (i+1) * 100).rjust(4)+" PTS", False, black), [325, 168+(i*45)])
					state.screen.blit(self.text(str(n * (i+1) * 100).rjust(4)+" PTS", False, white), [325, 168+(i*45)])

					self.flip()
					self.delayFrames(8)

			self.delayFrames(20)

		self.delayFrames(30)

		# total tanks
		tanks = sum([i for i in state.players[0].trophies.values()]) - state.players[0].trophies["bonus"]
		state.screen.blit(self.text(str(tanks).rjust(2), False, white), [170, 335])
		if self.nr_of_players >= 2:
			tanks = sum([i for i in state.players[1].trophies.values()]) - state.players[1].trophies["bonus"]
			state.screen.blit(self.text(str(tanks).rjust(2), False, white), [277, 335])

		# third player: short table, there is no room for detailed one
		if self.nr_of_players == 3:
			state.screen.blit(self.text("III-PLAYER", False, purple), [25, 375])
			state.screen.blit(self.text(str(state.players[2].score).rjust(8), False, pink), [325, 375])
			kills = [state.players[2].trophies["enemy" + str(i)] for i in range(4)]
			kills_text = "KILLS " + " ".join([str(k) for k in kills]) + " = " + str(sum(kills))
			state.screen.blit(self.text(kills_text, False, white), [25, 395])

		if kills_bonus_player != None:
			player_names = ["I-PLAYER", "II-PLAYER", "III-PLAYER"]
			name = "BOT" if state.players[kills_bonus_player].bot else player_names[kills_bonus_player]
			bonus_text = self.text(name + " BONUS " + str(config.TWO_PLAYER_KILLS_BONUS), False, white)
			state.screen.blit(bonus_text, [(480 - bonus_text.get_width()) // 2, 355])

		self.flip()

		self.delayFrames(15)
		self.delayFrames(120)

		if self.game_over:
			return self.gameOverScreen
		elif self.test_play:
			return self.showMenu
		else:
			self.saveGame()
			return self.nextLevel

	def loadHiscores(self):
		""" Hiscore tables with names, every difficulty preset has own tables
		@return {"campaign CLASSIC": [[name, score], ...], "endless GOOD": [...], ...}, best score first
		"""
		tables = {}
		try:
			with open(config.dataFile(config.HISCORES_FILE), "r") as f:
				data = json.load(f)
		except (IOError, ValueError):
			data = {}
		if not isinstance(data, dict):
			data = {}
		for key in data:
			# broken table doesn't spoil other ones
			try:
				tables[key] = [[str(entry[0])[:3], int(entry[1])] for entry in data[key]][:config.HISCORES_COUNT]
			except (ValueError, TypeError, AttributeError, IndexError, KeyError):
				pass
		# old tables without preset go to current preset
		for mode in ("campaign", "endless"):
			if mode in tables:
				tables.setdefault(self.hiscoreKey(mode), tables[mode])
				del tables[mode]
		return tables

	def hiscoreKey(self, mode):
		""" Hiscore table name: game mode and difficulty preset """
		return mode + " " + (config.CURRENT_PRESET or "CUSTOM")

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
		if self.mode not in ("campaign", "endless") or self.demo or self.test_play:
			return
		tables = self.loadHiscores()
		table = tables.setdefault(self.hiscoreKey(self.mode), [])

		entered = False
		for player_nr, player in enumerate(state.players):
			# only humans enter hiscore tables
			if player.bot:
				continue
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
			surface = self.text(text, False, color)
			state.screen.blit(surface, [(480 - surface.get_width()) // 2, y])

		center("NEW HIGH SCORE", 80, yellow)
		center(["I", "II", "III"][player_nr] + "-PLAYER  " + str(score), 120, white)
		center("ENTER YOUR NAME", 180, white)

		# big letters with cursor under current one
		x = (480 - 3 * 40) // 2
		for i, letter in enumerate(name):
			surface = pygame.transform.scale(self.text(letter, False, white, False), [32, 32])
			state.screen.blit(surface, [x + i * 40, 220])
			if i == position:
				pygame.draw.rect(state.screen, yellow, [x + i * 40, 256, 32, 4])

		center("ENTER - DONE", 320, white)
		self.flip()

	def showHiscores(self, mode, duration):
		""" Show hiscore table for duration ms or until key / gamepad button is pressed """

		table = self.loadHiscores().get(self.hiscoreKey(mode), [])
		state.screen.fill([0, 0, 0])
		white = pygame.Color("white")
		yellow = pygame.Color(255, 200, 0)

		title = self.text(lang.tr("HIGH SCORES") + " - " + lang.tr(mode.upper()), False, yellow, False)
		state.screen.blit(title, [(480 - title.get_width()) // 2, 30])
		preset = self.text(config.CURRENT_PRESET or "CUSTOM", False, yellow)
		state.screen.blit(preset, [(480 - preset.get_width()) // 2, 54])
		for i, entry in enumerate(table):
			row = "%2d. %-3s %8d" % (i + 1, entry[0], entry[1])
			state.screen.blit(self.text(row, False, white, False), [96, 90 + i * 28])

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

	def saveGame(self):
		""" Save progress after completed stage: stage, number of players, player 2 is bot, preset,
		players' score, lives and superpowers
		"""
		data = {
			"stage": self.stage,
			"nr_of_players": self.nr_of_players,
			"bot": self.bot,
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
			bot = bool(data.get("bot", False))
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
			# player's own preset comes back in menu
			if self.preset_before_continue == None and data["preset"] != config.CURRENT_PRESET:
				self.preset_before_continue = config.CURRENT_PRESET
			config.applyPreset(data["preset"])
		self.mode = "campaign"
		self.stage = stage
		self.nr_of_players = nr_of_players
		self.bot = bot and nr_of_players == 2
		self.loaded_players_stats = stats
		return True

	def deleteSavedGame(self):
		""" Saved game is useless after game over """
		try:
			os.remove(config.dataFile(config.SAVEGAME_FILE))
		except OSError:
			pass
