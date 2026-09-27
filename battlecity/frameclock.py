# coding=utf-8
""" Exact frame pacing

pygame's Clock.tick() sleeps through the OS, and macOS stretches those sleeps (timer coalescing, App Nap):
the game then runs below its frame rate, and since tank and bullet speeds are counted per frame (like on NES),
everything moves slower than on NES. FrameClock keeps an absolute schedule of frames: it sleeps most of the
wait and spins the last ~2 ms, and a late frame is caught up on the next ones, so the average is the exact
frame rate (50 fps: 20 ms per frame) without keeping a CPU core busy all the time.
"""

import time
import pygame


def _real_clock():
	""" pygame's own Clock (tests replace pygame.time.Clock with a fake one, possibly before this import) """
	return getattr(pygame.time.Clock, "__module__", None) == "pygame.time"

# frames more than this late start a new schedule (e.g. after a long pause or a dragged window)
_RESYNC = 0.1
# wake up at least this much earlier than the frame and spin the rest; more when sleeps overshoot
_SPIN = 0.002


class FrameClock(object):

	def __init__(self, real=False):
		self.next = None
		self.last = None
		# how late sleeps wake up on this system (grows at once, shrinks slowly)
		self.overshoot = 0.0
		# tests replace pygame.time.Clock with a fake one: use it
		self.fake = None if real or _real_clock() else pygame.time.Clock()

	def tick(self, fps):
		""" Wait until the next frame; returns ms passed since the previous tick, like Clock.tick() """
		if self.fake is not None:
			return self.fake.tick(fps)
		period = 1.0 / fps
		now = time.perf_counter()
		if self.next is None or now - self.next > _RESYNC:
			self.next = now
		self.next += period
		remaining = self.next - time.perf_counter()
		spin = _SPIN + self.overshoot
		if remaining > spin:
			wanted = remaining - spin
			start = time.perf_counter()
			time.sleep(wanted)
			late = time.perf_counter() - start - wanted
			self.overshoot = late if late > self.overshoot else self.overshoot * 0.99 + late * 0.01
		while time.perf_counter() < self.next:
			pass
		now = time.perf_counter()
		passed = period if self.last is None else now - self.last
		self.last = now
		return int(round(passed * 1000))

	def tick_busy_loop(self, fps):
		return self.tick(fps)
