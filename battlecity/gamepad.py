# coding=utf-8
""" Battle City: gamepad input """

import os, random, uuid, sys, json
import pygame
from pygame.locals import *

from battlecity import config, state

# SDL game controller API: standard button layout for known gamepads
try:
	from pygame._sdl2 import controller as sdl_controller
except ImportError:
	sdl_controller = None

class Gamepad():
	""" Gamepad state reader
	Known gamepads are read through SDL game controller API (d-pad, left stick, A/B/X/Y, Start),
	other devices as plain joystick (hat 0, axes 0-1, buttons 0-3 fire, 7 or 9 start)
	"""

	# stick deflection needed to move
	AXIS_THRESHOLD = 0.5

	def __init__(self, index = None):
		""" index None creates gamepad without device (used by tests) """
		self.controller = None
		self.joystick = None
		self.state = {}
		self.prev = {}

		if index == None:
			return
		if sdl_controller != None and sdl_controller.is_controller(index):
			self.controller = sdl_controller.Controller(index)
		else:
			self.joystick = pygame.joystick.Joystick(index)
			self.joystick.init()

	def read(self):
		""" Read raw device state
		@return dict with booleans: up, right, down, left, fire, start
		"""
		up = right = down = left = fire = start = False
		x = y = 0.0

		if self.controller != None:
			c = self.controller
			up = c.get_button(pygame.CONTROLLER_BUTTON_DPAD_UP)
			right = c.get_button(pygame.CONTROLLER_BUTTON_DPAD_RIGHT)
			down = c.get_button(pygame.CONTROLLER_BUTTON_DPAD_DOWN)
			left = c.get_button(pygame.CONTROLLER_BUTTON_DPAD_LEFT)
			x = c.get_axis(pygame.CONTROLLER_AXIS_LEFTX) / 32768.0
			y = c.get_axis(pygame.CONTROLLER_AXIS_LEFTY) / 32768.0
			fire_buttons = (pygame.CONTROLLER_BUTTON_A, pygame.CONTROLLER_BUTTON_B, pygame.CONTROLLER_BUTTON_X, pygame.CONTROLLER_BUTTON_Y)
			start_buttons = (pygame.CONTROLLER_BUTTON_START,)
		elif self.joystick != None:
			j = self.joystick
			if j.get_numhats() > 0:
				hat_x, hat_y = j.get_hat(0)
				up, down = hat_y > 0, hat_y < 0
				right, left = hat_x > 0, hat_x < 0
			if j.get_numaxes() >= 2:
				x, y = j.get_axis(0), j.get_axis(1)
			fire_buttons = range(4)
			start_buttons = (7, 9)

		if self.controller != None or self.joystick != None:
			# buttons chosen on settings screen
			if config.GAMEPAD_FIRE_BUTTON != None:
				fire_buttons = (config.GAMEPAD_FIRE_BUTTON,)
			if config.GAMEPAD_START_BUTTON != None:
				start_buttons = (config.GAMEPAD_START_BUTTON,)
			held = self.buttonsHeld()
			fire = any([button in held for button in fire_buttons])
			start = any([button in held for button in start_buttons])
		# left stick: only dominant axis counts (tanks can't move diagonally)
		if abs(x) > abs(y):
			right = right or x > self.AXIS_THRESHOLD
			left = left or x < -self.AXIS_THRESHOLD
		else:
			down = down or y > self.AXIS_THRESHOLD
			up = up or y < -self.AXIS_THRESHOLD

		return {
			"up": bool(up), "right": bool(right), "down": bool(down), "left": bool(left),
			"fire": bool(fire), "start": bool(start)
		}

	def buttonsHeld(self):
		""" Numbers of held buttons (SDL controller or joystick button numbers) """
		try:
			if self.controller != None:
				return set([b for b in range(pygame.CONTROLLER_BUTTON_MAX) if self.controller.get_button(b)])
			if self.joystick != None:
				return set([b for b in range(self.joystick.get_numbuttons()) if self.joystick.get_button(b)])
		except pygame.error:
			pass
		return set()

	def update(self):
		""" Read new state, remember previous one (call once per frame) """
		self.prev = self.state
		try:
			self.state = self.read()
		except pygame.error:
			# device was disconnected
			self.state = {}

	def held(self, name):
		return self.state.get(name, False)

	def pressed(self, name):
		""" True only on the frame button was pressed """
		return self.held(name) and not self.prev.get(name, False)

	def directions(self):
		""" @return [up, right, down, left] """
		return [self.held("up"), self.held("right"), self.held("down"), self.held("left")]
