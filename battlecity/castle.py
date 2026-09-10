# coding=utf-8
""" Battle City: player's castle """

import os, random, uuid, sys, json
import pygame
from pygame.locals import *

from battlecity import config, state
from battlecity.effects import Explosion

class Castle():
	""" Player's castle/fortress """

	(STATE_STANDING, STATE_DESTROYED, STATE_EXPLODING) = range(3)

	def __init__(self):


		# images
		self.img_undamaged = state.sprites.subsurface(0, 15*2, 16*2, 16*2)
		self.img_destroyed = state.sprites.subsurface(16*2, 15*2, 16*2, 16*2)

		# protection (player superpower 9): absorbs one enemy hit
		self.protected = False
		self.img_protected = state.sprites2.subsurface((10+5)*32+4, 9*32, 16*2, 16*2)

		# init position
		self.rect = pygame.Rect(12*16, 24*16, 32, 32)

		# index of player owning the castle (versus mode has castle for each player)
		self.owner = 0

		# start w/ undamaged and shiny castle
		self.rebuild()

	def draw(self):
		""" Draw castle """

		state.screen.blit(self.image, self.rect.topleft)

		if self.protected:
			state.screen.blit(self.img_protected, self.rect.topleft)

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

		if config.play_sounds:
			state.sounds["boom"].play()

		state.game.shake(25)

		self.state = self.STATE_EXPLODING
		self.explosion = Explosion(self.rect.topleft)
		self.image = self.img_destroyed
		self.active = False
