""" Test harness for tanks.py

Game is started with dummy video/audio drivers, fast fake clock and fake input.
Scenario function is called on every pygame.event.get() call (roughly once per frame)
and returns list of events to inject.

Each test file defines SCENARIOS dict and calls harness.main(SCENARIOS). Without arguments
every scenario runs in its own process (game uses module globals, so it can't be restarted
in the same process).
"""

import os, sys, time, runpy, inspect, subprocess

GAME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_FILE = os.path.join(GAME_DIR, "tanks.py")

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame


class Context(object):
	""" Passed to scenario functions """

	def __init__(self):
		# frames since game level loop started (0 while in menu)
		self.frame = 0
		self.menu_frame = 0
		self.total_frames = 0
		self.checks = []
		# free storage for scenario state
		self.data = {}
		self.finished = False
		# name of the check expecting game to quit on next frame
		self.expecting_exit = None

	@property
	def g(self):
		""" Game module globals """
		return sys.modules["__main__"].__dict__

	@property
	def game(self):
		return self.g.get("game")

	def key(self, k, mod=0, up=False):
		event_type = pygame.KEYUP if up else pygame.KEYDOWN
		return pygame.event.Event(event_type, key=k, mod=mod, unicode="", scancode=0)

	def check(self, name, condition):
		self.checks.append((name, bool(condition)))

	def in_function(self, name):
		""" True if game code with this function name is on the call stack """
		return any(frame.function == name for frame in inspect.stack())

	def expect_exit(self, name, k=pygame.K_ESCAPE):
		""" Send key which must quit the game """
		self.expecting_exit = name
		return [self.key(k)]

	def finish(self):
		""" Stop the test """
		self.finished = True
		raise SystemExit


def default_menu(players):
	""" Skip intro animation, select number of players, start game """
	sequence = [pygame.K_RETURN] + [pygame.K_DOWN] * (players - 1) + [pygame.K_RETURN]

	def menu(ctx):
		i = ctx.menu_frame - 1
		if i < len(sequence):
			return [ctx.key(sequence[i])]
		return []
	return menu


def run(scenario, argv=None, players=1, menu=None, real_time=False, max_frames=5000):
	""" Run the game with scenario, return list of (check name, passed) """

	ctx = Context()
	menu = menu or default_menu(players)

	class FakeClock(object):
		def tick(self, *args):
			if real_time:
				time.sleep(0.02)
			return 20

	pygame.time.Clock = FakeClock
	original_get = pygame.event.get

	def fake_get(*args, **kwargs):
		original_get()
		ctx.total_frames += 1

		if ctx.expecting_exit:
			# game is still running after quit key
			ctx.check(ctx.expecting_exit, False)
			ctx.expecting_exit = None
			ctx.finish()

		if ctx.total_frames > max_frames:
			ctx.check("finished in %d frames" % max_frames, False)
			ctx.finish()

		game = ctx.game
		if not hasattr(game, "level"):
			ctx.menu_frame += 1
			return menu(ctx) or []

		ctx.frame += 1
		return scenario(ctx) or []

	pygame.event.get = fake_get
	sys.argv = [GAME_FILE] + (argv or [])
	os.chdir(GAME_DIR)

	try:
		runpy.run_path(GAME_FILE, run_name="__main__")
	except SystemExit:
		pass

	if ctx.expecting_exit:
		ctx.check(ctx.expecting_exit, True)

	if not ctx.checks:
		ctx.check("scenario made any checks", False)

	return ctx.checks


def main(scenarios):
	""" Run one scenario (name in argv) or all of them in separate processes """

	if len(sys.argv) > 1:
		name = sys.argv[1]
		options = dict(scenarios[name])
		scenario = options.pop("fn")
		checks = run(scenario, **options)
		failed = 0
		for check_name, passed in checks:
			print(("OK   " if passed else "FAIL ") + "[%s] %s" % (name, check_name))
			if not passed:
				failed += 1
		sys.stdout.flush()
		os._exit(1 if failed else 0)

	exit_code = 0
	for name in scenarios:
		result = subprocess.run([sys.executable, sys.argv[0], name], capture_output=True, text=True)
		lines = [line for line in result.stdout.splitlines() if line.startswith(("OK", "FAIL"))]
		print("\n".join(lines))
		if result.returncode != 0:
			exit_code = 1
			if not any(line.startswith("FAIL") for line in lines):
				print("FAIL [%s] crashed:\n%s" % (name, result.stderr[-2000:]))
	sys.exit(exit_code)
