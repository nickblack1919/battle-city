""" Fixes after bug review: stage start not paused, game over after cleared wave, sounds, saved game,
bonuses, castle protection, walls for tanks between cells, water after ship, broken saved files, controls """

import json
import os
import pygame
import harness


def clear_enemies(ctx):
	del ctx.game.level.enemies_left[:]
	del ctx.g["enemies"][:]
	for p in ctx.g["players"]:
		p.shielded = True


def not_paused_after_stage(ctx):
	""" Pause pressed in the frame the stage ends: next stage isn't paused """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 5:
		clear_enemies(ctx)
		d["level"] = game.level
		game.pause()
		game.endLevel(game.nextLevel)
		return
	if "level" in d and game.level is not d["level"]:
		ctx.check("next stage isn't paused, players can move", not game.game_paused and not g["players"][0].paralised)
		ctx.finish()


def endless_game_over(ctx):
	""" Endless: castle destroyed right after the wave was cleared - game is over, no next wave """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 5:
		clear_enemies(ctx)
		game.mode = "endless"
		d["level"] = game.level
		# saved campaign stays
		with open(g["dataFile"](g["SAVEGAME_FILE"]), "w") as f:
			f.write("{}")
		game.finishLevel()
	if ctx.frame == 7:
		g["castle"].destroy()
	if ctx.frame > 7 and (ctx.in_function("showScores") or ctx.in_function("gameOverScreen")):
		ctx.check("game over after cleared wave", game.game_over)
		ctx.check("endless game over keeps saved campaign", os.path.isfile(g["dataFile"](g["SAVEGAME_FILE"])))
		ctx.finish()
	if "level" in d and game.level is not d["level"]:
		ctx.check("game over after cleared wave (next wave started)", False)
		ctx.finish()


def mute_without_sounds(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 5:
		clear_enemies(ctx)
		g["sounds"].clear()
		g["play_sounds"] = False
		return [ctx.key(pygame.K_m)]
	if ctx.frame == 6:
		p = g["players"][0]
		return [ctx.key(p.controls[0])]
	if ctx.frame == 10:
		ctx.check("M without loaded sounds keeps sound off, no crash", not g["play_sounds"])
		ctx.finish()


def engine_sound_new_wave(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	p = g["players"][0]
	if ctx.frame == 5:
		clear_enemies(ctx)
		g["play_sounds"] = True
		game.bg_sound = False
		game.start_music = False
		p.pressed = [True, False, False, False]
	if ctx.frame == 8:
		ctx.check("engine sound plays", game.engine_sound)
		d["level"] = game.level
		game.endLevel(game.nextLevel)
		return
	if "level" in d and game.level is not d["level"]:
		ctx.check("engine sound stopped on next wave", g["sounds"]["engine"].get_num_channels() == 0)
		ctx.finish()


def castle_protection_new_game(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 5:
		g["castle"].protected = True
		game.endLevel(game.showMenu)
		return
	if ctx.frame > 5 and ctx.in_function("showMenu"):
		ctx.check("castle protection doesn't go to next game", not g["castle"].protected)
		ctx.finish()


def pistol_keeps_boss(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	clear_enemies(ctx)
	Enemy, Bonus = g["Enemy"], g["Bonus"]
	game.level.enemies_left[:] = [Enemy.TYPE_BOSS]
	boss = Enemy(game.level, 1, [0, 0])
	boss.state = boss.STATE_ALIVE
	g["enemies"].append(boss)
	health = boss.health
	bonus = Bonus(game.level)
	bonus.setType(bonus.BONUS_PISTOL)
	game.triggerEnemyBonus(bonus, boss)
	ctx.check("enemy pistol keeps boss type and health", boss.type == Enemy.TYPE_BOSS and boss.health == health)
	ctx.finish()


def bonus_applied_once(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	p = g["players"][0]
	if ctx.frame == 5:
		clear_enemies(ctx)
		Enemy, Bonus = g["Enemy"], g["Bonus"]
		game.level.enemies_left[:] = [Enemy.TYPE_BASIC]
		enemy = Enemy(game.level, 1, [0, 0])
		del game.level.enemies_left[:]
		enemy.state = enemy.STATE_ALIVE
		enemy.bonus = None
		g["enemies"].append(enemy)
		bonus = Bonus(game.level)
		bonus.setType(bonus.BONUS_TANK)
		g["bonuses"].append(bonus)
		enemy.bonus_aquired = bonus
		p.bonus = bonus
		d["lives"] = p.lives
	if ctx.frame == 7:
		ctx.check("bonus taken by enemy isn't applied to player too", p.lives == d["lives"])
		ctx.finish()


def wall_between_cells(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	clear_enemies(ctx)
	level, myRect = game.level, g["myRect"]
	# steel column 1 cell wide, tank covers it with its middle
	level.mapr = [myRect(48, y, 16, 16, level.TILE_STEEL) for y in (160, 176, 192)]
	level.updateObstacleRects()
	p = g["players"][0]
	p.rect.topleft = [40, 96]
	p.rotate(p.DIR_DOWN, False)
	for i in range(100):
		p.move(p.DIR_DOWN, 1)
	ctx.check("tank between cells stops at 1 cell wide wall (top %d)" % p.rect.top, p.rect.collidelist(level.obstacle_rects) == -1)
	ctx.finish()


def water_after_ship(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	clear_enemies(ctx)
	level, myRect = game.level, g["myRect"]
	level.mapr = [myRect(x, y, 16, 16, level.TILE_WATER) for x in range(64, 320, 16) for y in (192, 208)]
	level.updateObstacleRects()
	p = g["players"][0]
	# overlaps water by 1 px, no ship
	p.rect.topleft = [33, 192]
	p.rotate(p.DIR_RIGHT, False)
	for i in range(300):
		p.move(p.DIR_RIGHT, 1)
	ctx.check("tank without ship doesn't cross water (left %d)" % p.rect.left, p.rect.left < 64)
	# ship ends on water: tank drives out
	p.rect.topleft = [80, 192]
	p.ship = True
	game.endShip(p)
	p.rotate(p.DIR_LEFT, False)
	for i in range(60):
		p.move(p.DIR_LEFT, 1)
	ctx.check("tank drives out of water after ship ended (left %d)" % p.rect.left, p.rect.left <= 32)
	ctx.finish()


def broken_files(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	with open(g["dataFile"](g["SETTINGS_FILE"]), "w") as f:
		json.dump({"preset": "CLASSIC", "pad_fire": "x", "sound": False, "start_level": 7, "gamepads": [-1, "AUTO", 99]}, f)
	g["play_sounds"] = True
	g["loadSettings"]()
	ctx.check("broken value doesn't reset other settings", not g["play_sounds"] and g["START_LEVEL"] == 7)
	ctx.check("bad gamepad numbers ignored (%s)" % g["GAMEPAD_ASSIGN"], g["GAMEPAD_ASSIGN"] == ["AUTO", "AUTO", "AUTO"])

	with open(g["dataFile"](g["HISCORES_FILE"]), "w") as f:
		json.dump({"campaign GOOD": [["AAA", 5000]], "endless GOOD": [["BBB", "lots"]], "campaign CLASSIC": [["CCC", 900]]}, f)
	tables = game.loadHiscores()
	ctx.check("broken hiscore table doesn't spoil others (%s)" % sorted(tables), tables.get("campaign CLASSIC") == [["CCC", 900]])

	old = list(g["PLAYER_CONTROLS"][0])
	game.setControl(0, 0, pygame.K_p)
	ctx.check("game keys can't be player controls", g["PLAYER_CONTROLS"][0] == old)
	ctx.finish()


def editor_test_play(ctx):
	""" Stage played from editor ends in menu without saving game """
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 5:
		clear_enemies(ctx)
		game.test_play = True
		d["level"] = game.level
		game.endLevel(game.showScores)
		return
	if ctx.frame > 5 and ctx.in_function("showMenu"):
		ctx.check("test play doesn't save game", not os.path.isfile(g["dataFile"](g["SAVEGAME_FILE"])))
		ctx.finish()
	if "level" in d and game.level is not d["level"]:
		ctx.check("test play returns to menu after stage", False)
		ctx.finish()


SCENARIOS = {
	"not_paused_after_stage": {"fn": not_paused_after_stage},
	"endless_game_over": {"fn": endless_game_over},
	"mute_without_sounds": {"fn": mute_without_sounds},
	"engine_sound_new_wave": {"fn": engine_sound_new_wave},
	"castle_protection_new_game": {"fn": castle_protection_new_game},
	"pistol_keeps_boss": {"fn": pistol_keeps_boss},
	"bonus_applied_once": {"fn": bonus_applied_once},
	"wall_between_cells": {"fn": wall_between_cells},
	"water_after_ship": {"fn": water_after_ship},
	"broken_files": {"fn": broken_files},
	"editor_test_play": {"fn": editor_test_play},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
