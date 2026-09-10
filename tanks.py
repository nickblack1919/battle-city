#!/usr/bin/python
# coding=utf-8
""" Battle City

Run: python tanks.py [-l LEVEL] [-f]
Game code is in battlecity package, settings in battlecity/config.py
"""

from battlecity import config, state
from battlecity.timer import Timer
from battlecity.castle import Castle
from battlecity.game import Game

if __name__ == "__main__":

	state.gtimer = Timer()

	config.loadSettings()

	state.game = Game()
	state.castle = Castle()
	state.castle2 = None

	# each screen returns the next one to show
	action = state.game.showMenu
	while action:
		action = action()
