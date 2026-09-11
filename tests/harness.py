""" Test harness for tanks.py

Game is started with dummy video/audio drivers, fast fake clock and fake input.
Scenario function is called on every pygame.event.get() call (roughly once per frame)
and returns list of events to inject.

Each test file defines SCENARIOS dict and calls harness.main(SCENARIOS). Without arguments
every scenario runs in its own process (game uses module globals, so it can't be restarted
in the same process). Scenario processes run in parallel, results are printed in SCENARIOS
order. Worker count: BATTLE_CITY_TEST_WORKERS environment variable, default os.cpu_count().
"""

import os, sys, time, runpy, inspect, subprocess, tempfile, threading
from concurrent.futures import ThreadPoolExecutor

GAME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_FILE = os.path.join(GAME_DIR, "tanks.py")

# tanks.py imports battlecity package from game directory
sys.path.insert(0, GAME_DIR)

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# hiscore, settings and saved game go to empty temporary directory, not to player's files
if "BATTLE_CITY_DATA_DIR" not in os.environ:
	os.environ["BATTLE_CITY_DATA_DIR"] = tempfile.mkdtemp(prefix="battle-city-test-")
DATA_DIR = os.environ["BATTLE_CITY_DATA_DIR"]

import pygame


class GameNamespace(object):
	""" Looks names up in battlecity.state, battlecity.config and other battlecity modules;
	assignment changes the value in the module that has it """

	def modules(self):
		names = ["battlecity.state", "battlecity.config"]
		names += sorted([name for name in sys.modules if name.startswith("battlecity.") and name not in names])
		return [sys.modules[name] for name in names if name in sys.modules]

	def __getitem__(self, name):
		for module in self.modules():
			if hasattr(module, name):
				return getattr(module, name)
		raise KeyError(name)

	def __setitem__(self, name, value):
		for module in self.modules():
			if hasattr(module, name):
				setattr(module, name, value)
				return
		raise KeyError(name)

	def __contains__(self, name):
		return any([hasattr(module, name) for module in self.modules()])

	def get(self, name, default=None):
		try:
			return self[name]
		except KeyError:
			return default


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
		# current level object and whether players already appeared on it
		self.level = None
		self.level_ready = False

	@property
	def g(self):
		""" Game names: shared objects, settings and classes from battlecity modules """
		return GameNamespace()

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
	""" Skip intro animation, select number of players, start game
	Menu: 1 PLAYER, 1 PLAYER + BOT, 2 PLAYERS, 3 PLAYERS """
	sequence = [pygame.K_RETURN] + [pygame.K_DOWN] * {1: 0, 2: 2, 3: 3}[players] + [pygame.K_RETURN]

	def menu(ctx):
		i = ctx.menu_frame - 1
		if i < len(sequence):
			return [ctx.key(sequence[i])]
		return []
	return menu


def run(scenario, argv=None, players=1, menu=None, real_time=False, max_frames=5000, setup=None):
	""" Run the game with scenario, return list of (check name, passed)
	setup: function called before the game starts (e.g. to write saved files into DATA_DIR)
	"""

	ctx = Context()
	menu = menu or default_menu(players)

	if setup:
		setup()

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

		# "STAGE N" screen: don't count its frames, so scenario frame numbers match game loop
		if getattr(game, "stage_screen", False):
			return []

		# level start: don't count frames until players appear (spawn animation)
		if getattr(game, "level", None) is not ctx.level:
			ctx.level = game.level
			ctx.level_ready = False
		if not ctx.level_ready:
			players = ctx.g["players"]
			if any([player.state == player.STATE_SPAWNING for player in players]):
				return []
			ctx.level_ready = True

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
	for output, ok in run_parallel([(os.path.abspath(sys.argv[0]), name, scenarios[name]) for name in scenarios]):
		if output:
			print(output)
		if not ok:
			exit_code = 1
	sys.exit(exit_code)


def worker_count():
	""" BATTLE_CITY_TEST_WORKERS or number of CPUs """
	try:
		return max(1, int(os.environ["BATTLE_CITY_TEST_WORKERS"]))
	except (KeyError, ValueError):
		return os.cpu_count() or 4


def run_parallel(jobs, workers=None):
	""" Run (test file, scenario name, options) jobs in separate processes in parallel.
	Yields (output text, passed) in jobs order as soon as results are available.
	Real time scenarios run at most half the workers at once so they are not starved. """

	workers = workers or worker_count()
	real_time_slots = threading.Semaphore(max(1, workers // 2))

	# every scenario gets its own empty data directory
	env = dict(os.environ)
	env.pop("BATTLE_CITY_DATA_DIR", None)

	def run_job(job):
		path, name, options = job
		real_time = options.get("real_time")
		if real_time:
			real_time_slots.acquire()
		try:
			result = subprocess.run([sys.executable, path, name], capture_output=True, text=True, env=env)
		finally:
			if real_time:
				real_time_slots.release()
		lines = [line for line in result.stdout.splitlines() if line.startswith(("OK", "FAIL"))]
		if result.returncode != 0 and not any(line.startswith("FAIL") for line in lines):
			lines.append("FAIL [%s] crashed:\n%s" % (name, result.stderr[-2000:]))
		return "\n".join(lines), result.returncode == 0

	with ThreadPoolExecutor(max_workers=workers) as pool:
		for future in [pool.submit(run_job, job) for job in jobs]:
			yield future.result()
