# coding=utf-8
""" Battle City: level map """

import os, random, uuid, sys, json
import pygame
from pygame.locals import *

from battlecity import config, state

class myRect(pygame.Rect):
	""" Add type property """
	def __init__(self, left, top, width, height, type):
		pygame.Rect.__init__(self, left, top, width, height)
		self.type = type


class Level():

	# tile constants
	(TILE_EMPTY, TILE_BRICK, TILE_STEEL, TILE_WATER, TILE_GRASS, TILE_FROZE) = range(6)

	# tile width/height in px
	TILE_SIZE = 16

	def __init__(self, level_nr = None, rows = None):
		""" There are total 35 different levels. If level_nr is larger than 35, loop over
		to next according level so, for example, if level_nr ir 37, then load level 2
		rows: map rows (e.g. generated level) instead of level file """


		# max number of enemies simultaneously  being on map
		self.max_active_enemies = config.MAX_ACTIVE_ENEMIES

		if state.game.nr_of_players == 1:
			self.max_active_enemies = config.MAX_ACTIVE_ENEMIES
		elif state.game.nr_of_players == 2:
			self.max_active_enemies = config.MAX_ACTIVE_ENEMIES_2_PLAYERS
		elif state.game.nr_of_players == 3:
			self.max_active_enemies = config.MAX_ACTIVE_ENEMIES_3_PLAYERS

		tile_images = [
			pygame.Surface((8*2, 8*2)),
			state.sprites.subsurface(48*2, 64*2, 8*2, 8*2),
			state.sprites.subsurface(48*2, 72*2, 8*2, 8*2),
			state.sprites.subsurface(56*2, 72*2, 8*2, 8*2),
			state.sprites.subsurface(64*2, 64*2, 8*2, 8*2),
			state.sprites.subsurface(72*2, 64*2, 8*2, 8*2),
			state.sprites.subsurface(64*2, 72*2, 8*2, 8*2)
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

		if rows != None:
			self.loadRows(rows)
		else:
			self.loadLevel(level_nr)

		# tiles' rects on map, tanks cannot move over
		self.obstacle_rects = []
		
		# tiles' rects on map which can be removed by bullets
		self.removable_rects = []

		# update these tiles
		self.updateObstacleRects()
		self.updateRemovableRects()

		state.gtimer.add(600, lambda :self.toggleWaves())

	def hitTile(self, pos, power = 1, sound = False):
		"""
			Hit the tile
			@param pos Tile's x, y in px
			@return True if bullet was stopped, False otherwise
		"""


		for tile in self.mapr:
			if tile.topleft == pos:
				if tile.type == self.TILE_BRICK:
					if config.play_sounds and sound:
						state.sounds["brick"].play()
					self.mapr.remove(tile)
					self.updateObstacleRects()
					if power >= 4:
						return False
					return True
				elif tile.type == self.TILE_STEEL:
					if config.play_sounds and sound:
						state.sounds["steel"].play()
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
		filename = config.levelFile(level_nr)
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
		if config.BRICK_QUARTERS:
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


		if tiles == None:
			tiles = [self.TILE_BRICK, self.TILE_STEEL, self.TILE_WATER, self.TILE_GRASS, self.TILE_FROZE]

		for tile in self.mapr:
			if tile.type in tiles:
				if tile.type == self.TILE_BRICK:
					# brick quarter: draw matching part of brick image
					state.screen.blit(self.tile_brick, tile.topleft, [tile.left % self.TILE_SIZE, tile.top % self.TILE_SIZE, tile.width, tile.height])
				elif tile.type == self.TILE_STEEL:
					state.screen.blit(self.tile_steel, tile.topleft)
				elif tile.type == self.TILE_WATER:
					state.screen.blit(self.tile_water, tile.topleft)
				elif tile.type == self.TILE_FROZE:
					state.screen.blit(self.tile_froze, tile.topleft)
				elif tile.type == self.TILE_GRASS:
					state.screen.blit(self.tile_grass, tile.topleft)
					
	def updateRemovableRects(self):
		""" Set self.removable_rects to all tiles' rects that players can drive through and clear
		with bullets having enough power """


		self.removable_rects = state.game.castleRects()

		for tile in self.mapr:
			if tile.type == self.TILE_GRASS:
				self.removable_rects.append(tile)

	def updateObstacleRects(self):
		""" Set self.obstacle_rects to all tiles' rects that players can destroy
		with bullets """


		self.obstacle_rects = state.game.castleRects()

		# same without water (for tanks with ship)
		self.land_obstacle_rects = state.game.castleRects()

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
		tank_rects = [tank.rect for tank in state.players + state.enemies if tank.state == tank.STATE_ALIVE]

		for cell in cells:
			if tile == self.TILE_EMPTY or cell.collidelist(tank_rects) != -1:
				continue
			if tile == self.TILE_BRICK:
				self.addBrick(cell.left, cell.top)
			else:
				self.mapr.append(myRect(cell.left, cell.top, self.TILE_SIZE, self.TILE_SIZE, tile))

		self.updateObstacleRects()
