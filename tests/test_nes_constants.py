""" Timings and constants taken from NES version (counted in NES frames, selected NES version fps) """

import os, json
import harness
import pygame


def near(value, expected, tolerance=1):
	return abs(value - expected) <= tolerance


def timings(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	c = lambda name: g[name]
	fps = c("NES_FPS")
	ms = lambda frames: int(round(frames * 1000.0 / fps))
	px = c("NES_PX_PER_FRAME")
	gtimer = g["gtimer"]
	p = g["players"][0]

	ctx.check("start lives 3", p.lives == 3)
	ctx.check("bullet speed: NES 2 px per frame -> %.1f" % c("DEFAULT_BULLET_SPEED"), near(c("DEFAULT_BULLET_SPEED"), 2 * px, 0.01))
	ctx.check("fast bullet speed: NES 4 px -> %.1f" % c("FAST_BULLET_SPEED"), near(c("FAST_BULLET_SPEED"), 4 * px, 0.01))
	ctx.check("helmet 640 NES frames", c("BONUS_PLAYER_SHIELD_TIMEOUT") == ms(640))
	ctx.check("shield after spawn 192 NES frames", c("PLAYER_START_SHIELD_TIMEOUT") == ms(192))
	ctx.check("clock 640 NES frames", c("BONUS_TIMER_FREEZE_TIMEOUT") == ms(640))
	ctx.check("shovel 1280 NES frames", c("BONUS_FORTRESS_WALLS_TIMEOUT") == ms(1280))
	ctx.check("stage end 128 NES frames", c("LEVEL_FINISH_TIMEOUT") == ms(128))
	ctx.check("enemy fire chance: 1/32 per NES frame", near(c("CHANCE_OF_FIRE") / 100.0 * c("GAME_FRAME_TIMING"), fps / 32.0, 0.01))

	# bullets really move with NES speed
	Bullet = g["Bullet"]
	bullet = Bullet(game.level, [192, 192], Bullet.DIR_UP, speed=c("DEFAULT_BULLET_SPEED"))
	bullet.over_walls = True
	start = bullet.rect.top
	for i in range(10):
		bullet.update()
	expected = int(10 * c("DEFAULT_BULLET_SPEED") + 1e-9)
	ctx.check("bullet flew %d px in 10 frames (%d)" % (expected, start - bullet.rect.top), start - bullet.rect.top == expected)

	# player with a star and power tank fire fast bullets
	p.superpowers = 1
	p.updateSuperpowers()
	ctx.check("player with star: fast bullets", p.bullet_speed == c("FAST_BULLET_SPEED"))
	game.level.enemies_left[:] = [g["Enemy"].TYPE_POWER, g["Enemy"].TYPE_BASIC]
	basic = g["Enemy"](game.level, 1, [0, 0])
	power = g["Enemy"](game.level, 1, [192, 0])
	ctx.check("power tank: fast bullets, basic: normal", power.bullet_speed == c("FAST_BULLET_SPEED") and basic.bullet_speed == c("DEFAULT_BULLET_SPEED"))

	# shield after respawn and spawn animation
	game.respawnPlayer(p)
	remaining = gtimer.remaining(p.shield_end_timer)
	ctx.check("respawn: shield for 192 NES frames", remaining != None and remaining[1] == ms(192))
	ctx.check("respawn: spawn animation", p.state == p.STATE_SPAWNING)
	ctx.check("enemy spawn animation 56 NES frames", gtimer.remaining(basic.timer_uuid_spawn_end)[1] == ms(56))
	ctx.finish()


def fortress_blink(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	level = game.level
	if ctx.frame == 5:
		bonus = g["Bonus"](level)
		bonus.setType(bonus.BONUS_SHOVEL)
		game.triggerBonus(bonus, g["players"][0])
		ctx.check("shovel: steel walls", game.fortress_end_timer and level_steel(level) == 8)
		# skip to 1 s before blinking starts
		for timer in g["gtimer"].timers:
			if timer["uuid"] == game.fortress_blink_start_timer:
				timer["time"] = timer["interval"] - 1000
			if timer["uuid"] == game.fortress_end_timer:
				timer["time"] = timer["interval"] - 1000 - g["FORTRESS_BLINK_TIME"]
	# blinking starts 1000 ms (50 frames) later
	if ctx.frame == 5 + 60:
		ctx.check("walls blink before shovel ends", game.fortress_blink_timer != None)
		d["seen_brick"] = False
	if 5 + 60 < ctx.frame < 5 + 60 + 60 and level_steel(level) == 0:
		d["seen_brick"] = True
	if ctx.frame == 5 + 60 + 60:
		ctx.check("blinking walls are brick sometimes", d["seen_brick"])
	end_frame = 5 + 50 + (1000 + g["FORTRESS_BLINK_TIME"]) // 20 + 10
	if ctx.frame == end_frame:
		ctx.check("walls are brick after shovel ends", level_steel(level) == 0 and game.fortress_blink_timer == None)
		ctx.finish()


def level_steel(level):
	area = pygame.Rect(176, 368, 64, 48)
	return len([tile for tile in level.mapr if tile.type == level.TILE_STEEL and tile.colliderect(area)])


def classic_rules(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	Enemy, Bonus = g["Enemy"], g["Bonus"]
	ms = lambda frames: int(round(frames * 1000.0 / g["NES_FPS"]))
	ctx.check("CLASSIC preset active", g["CURRENT_PRESET"] == "CLASSIC")
	ctx.check("NES: 4 enemies on screen in 1 player game", game.level.max_active_enemies == 4)
	ctx.check("NES: 6 enemies in 2 player game", g["MAX_ACTIVE_ENEMIES_2_PLAYERS"] == 6)
	ctx.check("NES: first enemy appears immediately", len(g["enemies"]) == 1)
	ctx.check("NES: first enemy at center spawn point", g["enemies"][0].rect.topleft == (192, 0))
	ctx.check("NES: spawn interval stage 1, 1 player = 187 frames", game.enemySpawnInterval() == ms(187))
	game.nr_of_players = 2
	game.stage = 35
	ctx.check("NES: spawn interval stage 35, 2 players = 31 frames", game.enemySpawnInterval() == ms(31))
	game.nr_of_players = 1
	game.stage = 1

	# bonus tanks: 4th, 11th, 18th
	carriers = []
	for number in range(1, 21):
		game.level.enemies_left[:] = [0] * (21 - number)
		enemy = Enemy(game.level, 1, [0, 0])
		if enemy.bonus:
			carriers.append(number)
	ctx.check("NES: bonus tanks 4th, 11th, 18th: %s" % carriers, carriers == [4, 11, 18])

	types = set([Bonus(game.level).bonus for i in range(200)])
	ctx.check("NES bonus set (no pistol, ship)", Bonus.BONUS_PISTOL not in types and Bonus.BONUS_SHIP not in types)

	enemy.spawnBonus()
	bonus = g["bonuses"][-1]
	ctx.check("NES: bonus doesn't disappear, blinks", bonus.blinking and len([t for t in g["gtimer"].timers if t["interval"] == g["BONUS_SPAWN_TIMEOUT"]]) == 0)
	ctx.check("NES: friendly fire stuns partner", g["FRIENDLY_FIRE"] and g["FRIENDLY_FIRE_STUN_TIME"] == ms(267))

	p = g["players"][0]
	d["lives"] = p.lives
	p.score = 25000


def classic_game(ctx):
	d = ctx.data
	if ctx.frame == 1:
		classic_rules(ctx)
	if ctx.frame == 3:
		p = ctx.g["players"][0]
		ctx.check("NES: extra life at 20000", p.lives == d["lives"] + 1)
		p.score = 45000
	if ctx.frame == 5:
		p = ctx.g["players"][0]
		ctx.check("NES: extra life only once", p.lives == d["lives"] + 1)
		ctx.finish()


def write_classic_settings():
	with open(os.path.join(harness.DATA_DIR, ".settings.json"), "w") as f:
		json.dump({"preset": "CLASSIC"}, f)


def write_ntsc_settings():
	with open(os.path.join(harness.DATA_DIR, ".settings.json"), "w") as f:
		json.dump({"nes_version": "NTSC"}, f)


def saved_nes_version(ctx):
	g = ctx.g
	if ctx.frame == 1:
		ctx.check("saved NES version applied", g["NES_VERSION"] == "NTSC" and abs(g["PLAYER_DEFAULT_SPEED"] - 1.8) < 0.01)
		ctx.check("player created with NTSC speed", abs(g["players"][0].speed - 1.8) < 0.01)
		ctx.finish()


SCENARIOS = {
	"timings": {"fn": timings},
	"fortress_blink": {"fn": fortress_blink},
	"classic_rules": {"fn": classic_game, "setup": write_classic_settings},
	"saved_nes_version": {"fn": saved_nes_version, "setup": write_ntsc_settings},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
