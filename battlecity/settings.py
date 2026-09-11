# coding=utf-8
""" Battle City: settings screen """

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

class SettingsMixin():
	""" Part of Game class """

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
		items.append({"label": "LANGUAGE", "value": config.LANGUAGE, "type": "lang"})
		items.append({"label": "CRT FILTER", "value": config.CRT_FILTER, "type": "crt"})
		for player_nr in range(len(config.GAMEPAD_ASSIGN)):
			assign = config.GAMEPAD_ASSIGN[player_nr]
			value = assign if assign in ("AUTO", "OFF") else "PAD %d" % (assign + 1)
			items.append({"label": "P%d GAMEPAD" % (player_nr + 1), "value": value, "type": "pad", "player": player_nr})
		for label, name, default in (("PAD FIRE", "GAMEPAD_FIRE_BUTTON", "ANY"), ("PAD START", "GAMEPAD_START_BUTTON", "DEFAULT")):
			button = getattr(config, name)
			items.append({"label": label, "value": default if button == None else "BUTTON %d" % button, "type": "padbutton", "button": name})
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
		# waiting for gamepad button: {gamepad index: buttons held when waiting started}, None - not waiting
		waiting_pad = None

		while True:
			self.clock.tick(50)
			items = self.settingsItems()
			self.drawSettings(items, selected, "PRESS BTN" if waiting_pad != None else waiting_key)

			move = 0
			change = 0
			pad_change = False

			self.updateGamepads()
			if waiting_pad != None:
				for i, gamepad in enumerate(self.gamepads):
					held = gamepad.buttonsHeld()
					new = held - waiting_pad.get(i, set())
					if new:
						self.setPadButton(items[selected]["button"], min(new))
						waiting_pad = None
						break
					# button held when waiting started can be released and pressed again
					waiting_pad[i] = waiting_pad.get(i, set()) & held
			elif waiting_key:
				# gamepad can't set a key: its button cancels waiting
				for gamepad in self.gamepads:
					if gamepad.pressed("fire") or gamepad.pressed("start"):
						waiting_key = False
			else:
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
			pad_change = change != 0

			for event in self.events():
				if event.type == pygame.QUIT:
					quit()
				if event.type != pygame.KEYDOWN:
					continue
				if waiting_pad != None:
					# any key cancels waiting for gamepad button
					waiting_pad = None
				elif waiting_key:
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
					# keys are set from keyboard only
					waiting_key = not pad_change
				elif kind == "padbutton" and change > 0:
					waiting_pad = dict([(i, gamepad.buttonsHeld()) for i, gamepad in enumerate(self.gamepads)])
				else:
					self.changeSetting(kind, change, items[selected])

	def changeSetting(self, kind, change, item = None):
		""" Change setting value and save settings
		item: settings item (player of gamepad setting, button name)
		"""


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
		elif kind == "lang":
			index = lang.LANGUAGES.index(config.LANGUAGE) if config.LANGUAGE in lang.LANGUAGES else 0
			config.LANGUAGE = lang.LANGUAGES[(index + change) % len(lang.LANGUAGES)]
			self.prerenderTexts()
		elif kind == "crt":
			names = config.CRT_MODES
			index = names.index(config.CRT_FILTER) if config.CRT_FILTER in names else 0
			config.CRT_FILTER = names[(index + change) % len(names)]
		elif kind == "ai":
			names = config.ENEMY_AI_TYPES
			index = names.index(config.ENEMY_AI) if config.ENEMY_AI in names else 0
			config.ENEMY_AI = names[(index + change) % len(names)]
		elif kind == "pad":
			values = ["AUTO", "OFF", 0, 1, 2, 3]
			player_nr = item["player"] if item else 0
			current = config.GAMEPAD_ASSIGN[player_nr]
			index = values.index(current) if current in values else 0
			config.GAMEPAD_ASSIGN[player_nr] = values[(index + change) % len(values)]
			self.assignGamepads()
		elif kind == "padbutton":
			# back to default buttons
			setattr(config, item["button"] if item else "GAMEPAD_FIRE_BUTTON", None)
		elif kind == "nes":
			names = sorted(config.NES_VERSIONS)
			index = names.index(config.NES_VERSION) if config.NES_VERSION in names else 0
			config.applyNesVersion(names[(index + change) % len(names)])
		elif kind == "level":
			config.START_LEVEL = (config.START_LEVEL - 1 + change) % 35 + 1
			self.stage = config.START_LEVEL - 1
		elif kind == "reset":
			config.PLAYER_CONTROLS = [list(controls) for controls in config.DEFAULT_PLAYER_CONTROLS]
			config.GAMEPAD_ASSIGN = ["AUTO"] * len(config.GAMEPAD_ASSIGN)
			config.GAMEPAD_FIRE_BUTTON = None
			config.GAMEPAD_START_BUTTON = None
			self.assignGamepads()

		config.saveSettings(self.is_fullscreen)

	def setPadButton(self, name, button):
		""" Use gamepad button for fire or start (name: GAMEPAD_FIRE_BUTTON / GAMEPAD_START_BUTTON) """
		setattr(config, name, button)
		config.saveSettings(self.is_fullscreen)

	def setControl(self, player_nr, control, key):
		""" Assign key to player's control. Control already using this key gets the old key (swap) """
		# keys used by the game itself: pause, quit, mute, borrow life, debug
		if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_m, pygame.K_b) or (config.DEBUG_KEYS and key in (pygame.K_p, pygame.K_v)):
			return
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

		title = self.text("SETTINGS", False, white)
		state.screen.blit(title, [(480 - title.get_width()) // 2, 16])

		# list scrolls: selected item is always visible
		rows = (416 - 52) // 20
		offset = min(max(0, selected - rows + 1), max(0, len(items) - rows))
		for i, item in enumerate(items):
			if not offset <= i < offset + rows:
				continue
			y = 52 + (i - offset) * 20
			color = yellow if i == selected else white
			if i == selected:
				state.screen.blit(self.text(">", False, yellow), [16, y])
			state.screen.blit(self.text(item["label"], False, color), [40, y])
			waiting_text = waiting_key if isinstance(waiting_key, str) else "PRESS KEY"
			value = waiting_text if i == selected and waiting_key else item["value"]
			if value and item["type"] == "control" and not (i == selected and waiting_key):
				# key names aren't translated
				state.screen.blit(self.text(value[:10], False, color, False), [288, y])
			elif value:
				state.screen.blit(self.text(lang.tr(value)[:14], False, color, False), [288, y])

		self.flip()
