""" Ctrl+F / Cmd+F / Alt+Enter toggle full screen and don't pause / start the game
(dummy video driver can't really switch to full screen, so only key handling is checked) """

import harness
import pygame

COMBOS = [
	("Ctrl+F", pygame.K_f, pygame.KMOD_LCTRL),
	("Cmd+F", pygame.K_f, pygame.KMOD_LMETA),
	("Alt+Enter", pygame.K_RETURN, pygame.KMOD_LALT),
]


def menu(ctx):
	if ctx.menu_frame == 1:
		return [ctx.key(pygame.K_RETURN)]
	if ctx.menu_frame == 3:
		return [ctx.key(pygame.K_RETURN, pygame.KMOD_LALT)]
	if ctx.menu_frame == 4:
		ctx.check("menu: Alt+Enter doesn't start game", not hasattr(ctx.game, "level"))
	if ctx.menu_frame == 5:
		return [ctx.key(pygame.K_RETURN)]
	return []


def keys(ctx):
	game = ctx.game
	plan = []
	for name, key, mod in COMBOS:
		plan.append((name + " in game", key, mod, False))
		plan.append((name + " in pause", key, mod, True))

	step = ctx.data.get("step", 0)
	if step >= len(plan):
		ctx.finish()

	name, key, mod, paused = plan[step]
	step_frame = ctx.frame - 10 - step * 10
	if step_frame == 0:
		if game.game_paused != paused:
			game.pause()
		return [ctx.key(key, mod)]
	if step_frame == 2:
		ctx.check(name + ": handled, pause state kept", game.game_paused == paused)
		ctx.data["step"] = step + 1


SCENARIOS = {
	"fullscreen_keys": {"fn": keys, "menu": menu},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
