""" Player controls with real key events (CLASSIC preset: friendly fire is on) """

import os, json
import harness
import pygame


def write_classic_settings():
	with open(os.path.join(harness.DATA_DIR, ".settings.json"), "w") as f:
		json.dump({"preset": "CLASSIC"}, f)


def own_bullet(ctx):
	""" Fire and move with key events: own bullet must not stun own tank """
	g, d = ctx.g, ctx.data
	p = g["players"][0]
	fire, up = p.controls[0], p.controls[1]
	if ctx.frame == 1:
		del ctx.game.level.enemies_left[:]
		del g["enemies"][:]
		d["y"] = p.rect.top
		return [ctx.key(fire)]
	if ctx.frame == 3:
		ctx.check("bullet fired with fire key", len([b for b in g["bullets"] if b.owner_class is p]) == 1)
		ctx.check("own bullet doesn't stun own tank (CLASSIC friendly fire)", not p.paralised)
		return [ctx.key(fire, up=True), ctx.key(up)]
	if ctx.frame == 23:
		ctx.check("tank moves with movement key after firing (%d px)" % (d["y"] - p.rect.top), d["y"] - p.rect.top > 20)
		ctx.finish()


def key_during_spawn_menu(ctx):
	""" Start game; hold keys while player 1 spawns """
	game = ctx.game
	if ctx.menu_frame in (1, 2):
		return [ctx.key(pygame.K_RETURN)]
	return []


def key_during_spawn(ctx):
	# harness counts frames only after players appeared, so press keys from menu hook is too early;
	# instead respawn player and press keys during spawn animation
	g, d = ctx.g, ctx.data
	p = g["players"][0]
	fire, up = p.controls[0], p.controls[1]
	if ctx.frame == 1:
		del ctx.game.level.enemies_left[:]
		del g["enemies"][:]
		# held fire shoots after spawn only with auto fire (off by default, like on NES)
		g["AUTO_FIRE"] = True
		ctx.game.respawnPlayer(p)
		ctx.check("player spawning after respawn", p.state == p.STATE_SPAWNING)
		d["y"] = p.rect.top
		return [ctx.key(up), ctx.key(fire)]
	if ctx.frame == 60:
		ctx.check("player appeared", p.state == p.STATE_ALIVE)
		ctx.check("key held during spawn moves tank after it appears (%d px)" % (d["y"] - p.rect.top), d["y"] - p.rect.top > 10)
		ctx.check("fire held during spawn fires after tank appears", len([b for b in g["bullets"] if b.owner_class is p]) > 0 or p.last_fire_time > 0)
		ctx.finish()


def partner_bullet(ctx):
	""" CLASSIC: other player's bullet stuns, own doesn't """
	g = ctx.g
	if ctx.frame != 1:
		return
	p1, p2 = g["players"]
	p1.shielded = p2.shielded = False
	Bullet = g["Bullet"]
	bullet = Bullet(ctx.game.level, [p1.rect.left, p1.rect.top], Bullet.DIR_UP)
	bullet.owner = Bullet.OWNER_PLAYER
	bullet.owner_class = p2
	bullet.rect.topleft = [p1.rect.left + 12, p1.rect.top + 12]
	g["bullets"].append(bullet)
	bullet.update()
	ctx.check("partner's bullet stuns player (CLASSIC)", p1.paralised and p1.state == p1.STATE_ALIVE)
	ctx.finish()


SCENARIOS = {
	"own_bullet": {"fn": own_bullet, "setup": write_classic_settings},
	"key_during_spawn": {"fn": key_during_spawn, "setup": write_classic_settings},
	"partner_bullet": {"fn": partner_bullet, "players": 2, "setup": write_classic_settings},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
