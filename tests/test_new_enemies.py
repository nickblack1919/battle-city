""" New enemies: stealth tank, mortar tank, boss """

import harness
import pygame


def make_enemy(ctx, enemy_type, position=(0, 0)):
	g, game = ctx.g, ctx.game
	game.level.enemies_left[:] = [enemy_type]
	enemy = g["Enemy"](game.level, 1, list(position))
	enemy.state = enemy.STATE_ALIVE
	enemy.bonus = None
	return enemy


def fire_until_bullet(ctx, enemy):
	""" Enemies fire with CHANCE_OF_FIRE: try until bullet is fired """
	for i in range(200):
		if enemy.fire():
			return ctx.g["bullets"][-1]
	return None


def brightness(surface, rect):
	total = 0
	for x in range(rect.left, rect.right, 2):
		for y in range(rect.top, rect.bottom, 2):
			color = surface.get_at((x, y))
			total += color[0] + color[1] + color[2]
	return total


def types(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 10:
		return
	del g["enemies"][:]
	Enemy = g["Enemy"]

	stealth = make_enemy(ctx, Enemy.TYPE_STEALTH)
	mortar = make_enemy(ctx, Enemy.TYPE_MORTAR)
	boss = make_enemy(ctx, Enemy.TYPE_BOSS)
	ctx.check("stealth tank health 1 hit", stealth.health == 100)
	ctx.check("mortar tank health 2 hits", mortar.health == 200)
	ctx.check("boss health %d" % g["BOSS_HEALTH"], boss.health == g["BOSS_HEALTH"])
	ctx.check("boss fires 3 bullets", boss.max_active_bullets == 3)
	ctx.check("points for new enemies", g["ENEMY_POINTS"][4:] == [300, 400, 2000])

	# stealth tank is almost invisible until it fires
	screen = g["screen"]
	screen.fill([0, 0, 0])
	stealth.draw()
	hidden = brightness(screen, stealth.rect)
	screen.fill([0, 0, 0])
	stealth.reveal_frames = 10
	stealth.draw()
	revealed = brightness(screen, stealth.rect)
	ctx.check("hidden stealth tank is much darker (%d vs %d)" % (hidden, revealed), hidden * 3 < revealed)

	stealth.reveal_frames = 0
	g["bullets"][:] = []
	ctx.check("stealth tank fired", fire_until_bullet(ctx, stealth) != None)
	ctx.check("stealth tank revealed after firing", stealth.reveal_frames == g["STEALTH_REVEAL_FRAMES"])
	stealth.update(20)
	ctx.check("reveal counts down", stealth.reveal_frames == g["STEALTH_REVEAL_FRAMES"] - 1)

	# boss health bar
	screen.fill([0, 0, 0])
	boss.rect.topleft = [192, 200]
	boss.draw()
	ctx.check("boss health bar drawn", screen.get_at((193, 197))[:3] == (255, 60, 60))
	ctx.finish()


def stealth_cycle(ctx):
	""" Stealth tank shows itself for 1 s and hides for 5 s, and its shadow is barely visible """
	g, game = ctx.g, ctx.game
	if ctx.frame != 10:
		return
	del g["enemies"][:]
	stealth = make_enemy(ctx, g["Enemy"].TYPE_STEALTH, (64, 64))
	screen = g["screen"]

	ctx.check("stealth tank starts hidden", not stealth.stealthShowing())
	ctx.check("shadow is barely visible (alpha %d)" % g["STEALTH_ALPHA"], g["STEALTH_ALPHA"] <= 16)

	# count ms of showing and hiding over two full cycles
	ms = int(round(1000.0 / g["GAME_FRAME_TIMING"]))
	shown = hidden = 0
	period = g["STEALTH_SHOW_TIME"] + g["STEALTH_HIDE_TIME"]
	for i in range(2 * period // ms):
		stealth.update(ms)
		if stealth.stealthShowing():
			shown += ms
		else:
			hidden += ms
	ctx.check("visible about 2 s of two cycles (%d ms)" % shown, abs(shown - 2 * g["STEALTH_SHOW_TIME"]) <= 2 * ms)
	ctx.check("hidden about 10 s of two cycles (%d ms)" % hidden, abs(hidden - 2 * g["STEALTH_HIDE_TIME"]) <= 2 * ms)

	# showing tank is drawn as a normal tank, hidden one only as a shadow
	stealth.stealth_time = 0
	screen.fill([0, 0, 0])
	stealth.draw()
	showing = brightness(screen, stealth.rect)
	stealth.stealth_time = g["STEALTH_SHOW_TIME"]
	screen.fill([0, 0, 0])
	stealth.draw()
	shadow = brightness(screen, stealth.rect)
	ctx.check("showing stealth tank is much brighter (%d vs %d)" % (showing, shadow), shadow * 10 < showing)

	# firing shows it even during the hidden part of the cycle
	stealth.reveal_frames = g["STEALTH_REVEAL_FRAMES"]
	screen.fill([0, 0, 0])
	stealth.draw()
	ctx.check("firing reveals it while hiding", brightness(screen, stealth.rect) == showing)
	ctx.finish()


def mortar(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 10:
		return
	del g["enemies"][:]
	level, Enemy = game.level, g["Enemy"]

	# level 1: bricks at columns 2-3, rows 18-23; mortar below them shoots up
	shooter = make_enemy(ctx, Enemy.TYPE_MORTAR, (32, 384))
	shooter.rotate(shooter.DIR_UP, False)
	g["bullets"][:] = []
	bullet = fire_until_bullet(ctx, shooter)
	ctx.check("mortar fired", bullet != None)
	ctx.check("mortar shell flies over walls", bullet.over_walls)

	area = pygame.Rect(32, 288, 32, 96)
	bricks_before = len([t for t in level.mapr if t.type == level.TILE_BRICK and t.colliderect(area)])
	for i in range(30):
		bullet.update()
	bricks_after = len([t for t in level.mapr if t.type == level.TILE_BRICK and t.colliderect(area)])
	ctx.check("shell passed bricks without destroying them (%d -> %d)" % (bricks_before, bricks_after), bricks_before == bricks_after and bricks_before > 0)
	ctx.check("shell still flying above bricks", bullet.state == bullet.STATE_ACTIVE and bullet.rect.top < 288)
	ctx.finish()


def boss(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 10:
		return
	del g["enemies"][:]
	g["bonuses"][:] = []
	Enemy = g["Enemy"]
	p = g["players"][0]

	enemy = make_enemy(ctx, Enemy.TYPE_BOSS, (192, 200))
	g["enemies"].append(enemy)
	for i in range(4):
		enemy.bulletImpact(False, 100, p)
	ctx.check("no bonus before %d damage" % g["BOSS_BONUS_EVERY"], len(g["bonuses"]) == 0)
	enemy.bulletImpact(False, 100, p)
	ctx.check("boss drops bonus after %d damage" % g["BOSS_BONUS_EVERY"], len(g["bonuses"]) == 1)

	score = p.score
	enemy.health = 100
	enemy.bulletImpact(False, 100, p)
	ctx.check("boss destroyed", enemy.state == enemy.STATE_EXPLODING)
	ctx.check("2000 points for boss", p.score == score + 2000)
	ctx.check("boss counted in trophies", p.trophies["enemy6"] == 1)
	ctx.finish()


def composition(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 10:
		return
	Enemy = g["Enemy"]

	game.stage = 5
	game.loadLevelEnemies(False)
	enemies_left = game.level.enemies_left
	ctx.check("stage 5: boss is the last enemy", enemies_left[0] == Enemy.TYPE_BOSS and enemies_left.count(Enemy.TYPE_BOSS) == 1)
	ctx.check("stage 5: 3 stealth tanks", enemies_left.count(Enemy.TYPE_STEALTH) == 3)
	ctx.check("stage 5: 2 mortar tanks", enemies_left.count(Enemy.TYPE_MORTAR) == 2)
	ctx.check("stage 5: 20 tanks + boss", len(enemies_left) == 21)

	game.stage = 4
	game.loadLevelEnemies(False)
	ctx.check("stage 4: no new enemies", max(game.level.enemies_left) <= Enemy.TYPE_ARMOR)

	g["applyPreset"]("NES")
	game.stage = 5
	game.loadLevelEnemies(False)
	ctx.check("NES preset: no new enemies on stage 5", max(game.level.enemies_left) <= Enemy.TYPE_ARMOR)
	g["applyPreset"]("GOOD")
	ctx.finish()


SCENARIOS = {
	"types": {"fn": types},
	"stealth_cycle": {"fn": stealth_cycle},
	"mortar": {"fn": mortar},
	"boss": {"fn": boss},
	"composition": {"fn": composition},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
