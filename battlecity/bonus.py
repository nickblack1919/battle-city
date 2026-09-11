# coding=utf-8
""" Battle City: bonuses (power-ups) """

import os, random, uuid, sys, json
import pygame
from pygame.locals import *

from battlecity import config, state

class Bonus():
	""" Various power-ups
	When bonus is spawned, it begins flashing and after some time dissapears

	Available bonusses:
		grenade	: Picking up the grenade power up instantly wipes out ever enemy presently on the screen, including Armor Tanks regardless of how many times you've hit them. You do not, however, get credit for destroying them during the end-stage bonus points.
		helmet	: The helmet power up grants you a temporary force field that makes you invulnerable to enemy shots, just like the one you begin every stage with.
		shovel	: The shovel power up turns the walls around your fortress from brick to stone. This makes it impossible for the enemy to penetrate the wall and destroy your fortress, ending the game prematurely. The effect, however, is only temporary, and will wear off eventually.
		star		: The star power up grants your tank with new offensive power each time you pick one up, up to three times. The first star allows you to fire your bullets as fast as the power tanks can. The second star allows you to fire up to two bullets on the screen at one time. And the third star allows your bullets to destroy the otherwise unbreakable steel walls. You carry this power with you to each new stage until you lose a life.
		tank		: The tank power up grants you one extra life. The only other way to get an extra life is to score 20000 points.
		timer		: The timer power up temporarily freezes time, allowing you to harmlessly approach every tank and destroy them until the time freeze wears off.
	"""

	# bonus types
	(BONUS_GRENADE, BONUS_HELMET, BONUS_TIMER, BONUS_SHOVEL, BONUS_TANK, BONUS_STAR, BONUS_PISTOL, BONUS_SHIP) = range(8)

	def __init__(self, level):


		# to know where to place
		self.level = level

		# bonus lives only for a limited period of time
		self.active = True

		# blinking state (blinks only before disappearing)
		self.visible = True
		self.blinking = False
		self.blink_timer = None

		# NES: bonus center is one of 4x4 grid points, chosen again if a player is too close (12 NES px)
		grid = [64, 160, 256, 352]
		for attempt in range(16):
			self.rect = pygame.Rect(0, 0, 32, 32)
			self.rect.center = (random.choice(grid), random.choice(grid))
			near = [player for player in state.players if player.state == player.STATE_ALIVE
				and abs(player.rect.centerx - self.rect.centerx) < 24 and abs(player.rect.centery - self.rect.centery) < 24]
			if not near:
				break

		# bonus types of current preset (NES set in CLASSIC)
		self.bonus = random.choice([getattr(self, "BONUS_" + name) for name in config.BONUS_TYPES])

		#self.bonus = self.BONUS_GRENADE

		# self.image = sprites.subsurface(16*2*self.bonus, 32*2, 16*2, 15*2)
		self.image = state.sprites2.subsurface((7*config.S_SIZE+2)*config.T_SIZE, 32*(self.bonus+1), 32, 32)

	def draw(self):
		""" draw bonus """
		if self.visible:
			state.screen.blit(self.image, self.rect.topleft)

	def setType(self, bonus_type):
		""" Change bonus type and image """
		self.bonus = bonus_type
		self.image = state.sprites2.subsurface((7*config.S_SIZE+2)*config.T_SIZE, 32*(self.bonus+1), 32, 32)

	def startBlinking(self):
		""" Start blinking: bonus is about to disappear """
		self.blinking = True
		self.blink_timer = state.gtimer.add(config.BONUS_BLINK_INTERVAL, lambda :self.toggleVisibility())

	def toggleVisibility(self):
		""" Toggle bonus visibility """
		if self not in state.bonuses:
			state.gtimer.destroy(self.blink_timer)
			return
		self.visible = not self.visible
