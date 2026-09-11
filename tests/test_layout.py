""" Keys work with non latin keyboard layout (Russian): events have Cyrillic key codes, physical scancodes """

import harness
import pygame

# physical key -> key code produced with Russian layout
RUSSIAN = {
	pygame.KSCAN_W: ord(u"ц"),
	pygame.KSCAN_J: ord(u"о"),
	pygame.KSCAN_M: ord(u"ь"),
}


def russian_key(scancode, up=False):
	event_type = pygame.KEYUP if up else pygame.KEYDOWN
	return pygame.event.Event(event_type, key=RUSSIAN[scancode], mod=0, unicode=chr(RUSSIAN[scancode]), scancode=scancode)


def russian_layout(ctx):
	g, d = ctx.g, ctx.data
	p = g["players"][0]
	if ctx.frame == 1:
		del ctx.game.level.enemies_left[:]
		del g["enemies"][:]
		ctx.check("P1 controls are W / J (U.S. key codes)", p.controls[1] == pygame.K_w and p.controls[0] == pygame.K_j)
		d["y"] = p.rect.top
		d["sound"] = g["play_sounds"]
		return [russian_key(pygame.KSCAN_W), russian_key(pygame.KSCAN_J)]
	if ctx.frame == 3:
		ctx.check("physical J with Russian layout fires", len([b for b in g["bullets"] if b.owner_class is p]) == 1)
	if ctx.frame == 21:
		ctx.check("physical W with Russian layout moves tank up (%d px)" % (d["y"] - p.rect.top), d["y"] - p.rect.top > 20)
		ctx.check("held key is tracked", pygame.K_w in ctx.game.held_keys)
		return [russian_key(pygame.KSCAN_W, up=True), russian_key(pygame.KSCAN_J, up=True), russian_key(pygame.KSCAN_M)]
	if ctx.frame == 23:
		d["y"] = p.rect.top
		ctx.check("key release with Russian layout stops tank", not p.pressed[0] and pygame.K_w not in ctx.game.held_keys)
		ctx.check("hotkey M with Russian layout toggles sound", g["play_sounds"] != d["sound"])
	if ctx.frame == 30:
		ctx.check("tank stays after release (%d px)" % (d["y"] - p.rect.top), d["y"] == p.rect.top)
		ctx.finish()


SCENARIOS = {
	"russian_layout": {"fn": russian_layout},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
