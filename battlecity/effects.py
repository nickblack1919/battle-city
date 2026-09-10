# coding=utf-8
""" Battle City: explosions and score labels """

import os, random, uuid, sys, json
import pygame
from pygame.locals import *

from battlecity import config, state

class Label():

	# shared font: loading font for every label is slow
	font = None

	@staticmethod
	def getFont():
		if Label.font == None:
			Label.font = pygame.font.Font("fonts/prstart.ttf", 8)
		return Label.font

	def __init__(self, position, text = "", duration = None):

		self.position = position

		self.active = True

		self.text = text


		if duration != None:
			state.gtimer.add(duration, lambda :self.destroy(), 1)

	def draw(self):
		""" draw label """
		if not config.DISABLE_LABELS: 
			state.screen.blit(Label.getFont().render(self.text, False, (255,255,255)), [self.position[0]+4, self.position[1]+12])

	def destroy(self):
		self.active = False


class Explosion():
	def __init__(self, position, interval = None, images = None):


		self.position = [position[0]-16, position[1]-16]
		self.active = True

		if interval == None:
			interval = 100

		if images == None:
			images = [
				state.sprites.subsurface(0, 80*2, 32*2, 32*2),
				state.sprites.subsurface(32*2, 80*2, 32*2, 32*2),
				state.sprites.subsurface(64*2, 80*2, 32*2, 32*2)
			]

		images.reverse()

		self.images = [] + images

		self.image = self.images.pop()

		state.gtimer.add(interval, lambda :self.update(), len(self.images) + 1)

	def draw(self):
		""" draw current explosion frame """
		state.screen.blit(self.image, self.position)

	def update(self):
		""" Advace to the next image """
		if len(self.images) > 0:
			self.image = self.images.pop()
		else:
			self.active = False
