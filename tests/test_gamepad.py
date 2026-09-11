""" Gamepad support (fake gamepads: dummy video driver has no devices) """

import harness
import pygame


def make_fake_gamepad(ctx):
	Gamepad = ctx.g["Gamepad"]

	class FakeGamepad(Gamepad):
		def __init__(self):
			Gamepad.__init__(self)
			self.buttons = {}

		def read(self):
			state = {"up": False, "right": False, "down": False, "left": False, "fire": False, "start": False}
			state.update(self.buttons)
			return state

	return FakeGamepad()


def menu(ctx):
	""" 3 players selected with gamepad d-pad, game started with A """
	game, d = ctx.game, ctx.data
	if ctx.menu_frame == 1:
		return [ctx.key(pygame.K_RETURN)]
	if ctx.menu_frame == 2:
		d["pads"] = [make_fake_gamepad(ctx), make_fake_gamepad(ctx)]
		game.gamepads[:] = d["pads"]
		d["pads"][0].buttons = {"down": True}
	if ctx.menu_frame == 3:
		d["pads"][0].buttons = {}
	if ctx.menu_frame == 4:
		d["pads"][0].buttons = {"down": True}
	if ctx.menu_frame == 5:
		d["pads"][0].buttons = {}
	# menu applies gamepad presses after event.get() of the frame, so check one frame later
	if ctx.menu_frame == 6:
		ctx.check("menu: d-pad down twice selects 3 players", game.nr_of_players == 3)
		d["pads"][0].buttons = {"fire": True}
	return []


def gamepad(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	players = g["players"]
	pad0, pad1 = d["pads"]

	if ctx.frame == 1:
		pad0.buttons = {}
		ctx.check("menu: A starts the game", True)
		ctx.check("3 players in game", len(players) == 3)
		ctx.check("P3 has no keyboard controls", players[2].controls == [])
		ctx.check("first gamepad goes to P3", players[2].gamepad is pad0)
		ctx.check("second gamepad goes to P1", players[0].gamepad is pad1)
		ctx.check("P2 without gamepad", players[1].gamepad is None)

	p3 = players[2]
	if ctx.frame == 10:
		p3.shielded = True
		# P3 spawns facing up: steer left so turning is visible even if a wall blocks movement
		pad0.buttons = {"left": True}
	if ctx.frame == 20:
		pad0.buttons = {}
		ctx.check("d-pad left turns P3 left", p3.direction == p3.DIR_LEFT)

	# gamepad state is read at the start of a frame and applied after event.get(),
	# so a button set in frame N is handled in frame N+1 and visible to checks in frame N+2
	if ctx.frame == 25:
		# A held since menu fires right after P3 appears: remove that bullet, P3 has 1 bullet quota
		g["bullets"][:] = [b for b in g["bullets"] if b.owner_class is not p3]
		d["bullets"] = 0
		pad0.buttons = {"fire": True}
	if ctx.frame == 27:
		pad0.buttons = {}
		n = len([b for b in g["bullets"] if b.owner_class is p3])
		ctx.check("A fires P3 bullet", n > d["bullets"])

	if ctx.frame == 40:
		pad1.buttons = {"start": True}
	if ctx.frame == 42:
		ctx.check("Start pauses the game", game.game_paused)
		pad1.buttons = {}
	if ctx.frame == 45:
		pad1.buttons = {"start": True}
	if ctx.frame == 47:
		ctx.check("Start unpauses the game", not game.game_paused)
		pad1.buttons = {}
	if ctx.frame == 50:
		ctx.finish()


def joystick_directions(ctx):
	""" Stick: only dominant axis counts """
	Gamepad = ctx.g["Gamepad"]

	class FakeJoystick(object):
		def __init__(self, axes, hat=(0, 0)):
			self.axes, self.hat = axes, hat
		def get_numhats(self): return 1
		def get_hat(self, i): return self.hat
		def get_numaxes(self): return 2
		def get_axis(self, i): return self.axes[i]
		def get_numbuttons(self): return 10
		def get_button(self, i): return i == 9

	pad = Gamepad()
	pad.joystick = FakeJoystick([0.9, 0.3])
	state = pad.read()
	ctx.check("stick right with small vertical deflection -> only right", state["right"] and not state["up"] and not state["down"])
	pad.joystick = FakeJoystick([0.1, 0.2], (0, 1))
	state = pad.read()
	ctx.check("hat up -> up", state["up"] and not state["down"])
	ctx.check("joystick button 9 -> start", state["start"])
	ctx.finish()


SCENARIOS = {
	"gamepad": {"fn": gamepad, "menu": menu},
	"joystick_directions": {"fn": joystick_directions},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
