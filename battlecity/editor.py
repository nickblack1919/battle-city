# coding=utf-8
""" Battle City: level editor """

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

class EditorMixin():
	""" Part of Game class """

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

		state.screen.blit(lang.render(font, 8, "EDITOR", False, black), [420, 8])
		state.screen.blit(lang.render(font, 8, "LVL %d%s" % (level_nr, "*" if modified else ""), False, black), [420, 24])

		tile_images = {"#": level.tile_brick, "@": level.tile_steel, "~": level.tile_water, "%": level.tile_grass, "-": level.tile_froze}
		char, name = self.EDITOR_TILES[brush]
		if char in tile_images:
			state.screen.blit(tile_images[char], [440, 44])
		else:
			pygame.draw.rect(state.screen, black, [440, 44, 16, 16], 1)
		state.screen.blit(lang.render(font, 8, name, False, black), [420, 66])

		hints = ["1-5 TILE", "0 ERASE", "SPC DRAW", "S SAVE", "D RESET", "[ ] LVL", "T TEST", "ESC MENU"]
		for i, hint in enumerate(hints):
			state.screen.blit(lang.render(font, 8, hint, False, black), [418, 100 + i * 14])

		self.flip()
