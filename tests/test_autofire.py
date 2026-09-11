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


SCENARIOS = {
	# auto fire delay uses real time
	"autofire": {"fn": autofire, "real_time": True},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
