""" Holding fire button shoots as soon as bullet quota allows """

import harness
import pygame


def count_bullets(ctx, player):
	seen = ctx.data.setdefault("seen", set())
	for bullet in ctx.g["bullets"]:
		if bullet.owner_class is player:
			seen.add(id(bullet))
	return len(seen)


def autofire(ctx):
	p = ctx.g["players"][0]
	fire_key = p.controls[0]
	n = count_bullets(ctx, p)
	d = ctx.data

	if ctx.frame == 10:
		# auto fire is off by default (NES: every shot needs a press)
		ctx.g["AUTO_FIRE"] = True
		# shoot left: screen edge is close (128 px), so several shots fit in check window
		# (like on NES, next shot waits until bullet flew and exploded)
		p.rotate(p.DIR_LEFT, False)
		p.shielded = True
		d["start"] = n
		return [ctx.key(fire_key)]
	if ctx.frame == 110:
		ctx.check("held fire, 1 bullet quota: several shots (%d)" % (n - d["start"]), n - d["start"] >= 2)
		p.superpowers = 2
		p.updateSuperpowers()
		d["start1"] = n - d["start"]
		d["start"] = n
	if ctx.frame == 210:
		ctx.check("held fire, 2 bullet quota: more shots (%d)" % (n - d["start"]), n - d["start"] > d["start1"])
		d["start"] = n
		return [ctx.key(fire_key, up=True)]
	if ctx.frame == 310:
		ctx.check("released fire: no shots (%d)" % (n - d["start"]), n - d["start"] == 0)
		ctx.finish()


def turbo_gap(ctx):
	""" Turbo speed of a Dendy gamepad: two bullets (2nd star) don't fly right next to each other """
	g, d = ctx.g, ctx.data
	p = g["players"][0]
	if ctx.frame == 10:
		g["AUTO_FIRE"] = True
		del g["enemies"][:]
		del ctx.game.level.enemies_left[:]
		del g["bullets"][:]
		p.shielded = True
		p.superpowers = 2
		p.updateSuperpowers()
		p.rotate(p.DIR_LEFT, False)
		d["seen"] = []
		return [ctx.key(p.controls[0])]
	if ctx.frame > 10:
		for bullet in g["bullets"]:
			if bullet.owner_class is p and not any([bullet is b for b in d["seen"]]):
				d["seen"].append(bullet)
	if ctx.frame == 120:
		gaps = []
		for first, second in zip(d["seen"], d["seen"][1:]):
			if first.state == first.STATE_ACTIVE and second.state == second.STATE_ACTIVE:
				gaps.append(abs(first.rect.centerx - second.rect.centerx))
		ctx.check("bullets don't fly next to each other (%s)" % gaps, all([gap >= 16 for gap in gaps]))
		ctx.check("turbo delay is 4 NES frames", g["PLAYER_AUTO_FIRE_DELAY"] == g["nesFrames"](4))
		ctx.finish()


SCENARIOS = {
	# auto fire delay uses real time
	"autofire": {"fn": autofire, "real_time": True},
	"turbo_gap": {"fn": turbo_gap, "real_time": True},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
