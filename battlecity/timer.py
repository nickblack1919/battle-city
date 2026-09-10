# coding=utf-8
""" Battle City: timers calling functions after interval """

import os, random, uuid, sys, json
import pygame
from pygame.locals import *

from battlecity import config, state

class Timer(object):
	def __init__(self):
		self.timers = []

	def add(self, interval, f, repeat = -1):
		options = {
			"interval"	: interval,
			"callback"	: f,
			"repeat"		: repeat,
			"times"			: 0,
			"time"			: 0,
			"uuid"			: uuid.uuid4()
		}
		self.timers.append(options)

		return options["uuid"]

	def destroy(self, uuid_nr):
		for timer in self.timers:
			if timer["uuid"] == uuid_nr:
				self.timers.remove(timer)
				return

	def remaining(self, uuid_nr):
		""" Time left until timer fires
		@return [remaining ms, interval ms] or None if there is no such timer
		"""
		for timer in self.timers:
			if timer["uuid"] == uuid_nr:
				return [timer["interval"] - timer["time"], timer["interval"]]
		return None

	def update(self, time_passed):
		# iterate over a copy: callbacks may add or remove timers
		for timer in self.timers[:]:
			if timer not in self.timers:
				continue
			timer["time"] += time_passed
			if timer["time"] > timer["interval"]:
				timer["time"] -= timer["interval"]
				timer["times"] += 1
				if timer["repeat"] > -1 and timer["times"] == timer["repeat"]:
					self.timers.remove(timer)
				try:
					timer["callback"]()
				except Exception:
					if timer in self.timers:
						self.timers.remove(timer)
