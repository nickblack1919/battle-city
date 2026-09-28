""" Computer helper of two players (2 PLAYERS + BOT): guards the castle, dies for it,
never hurts players; players borrow lives from each other (key B, gamepad Select) """

import pygame
import harness


def select_menu_item(label):
	""" Menu: skip intro, select item by label, activate it """
	def menu(ctx):
		game = ctx.game
		if ctx.menu_frame == 1:
			return [ctx.key(pygame.K_RETURN)]
		if ctx.menu_frame == 2:
			labels = [item[0] for item in game.menuItems()]
			ctx.check("menu has %s: %s" % (label, labels), label in labels)
			ctx.data["menu_target"] = labels.index(label)
		if 2 <= ctx.menu_frame < 2 + ctx.data.get("menu_target", 0):
			return [ctx.key(pygame.K_DOWN)]
		if ctx.menu_frame == 2 + ctx.data.get("menu_target", 0):
			return [ctx.key(pygame.K_RETURN)]
		return []
	return menu


GUARD_MENU = select_menu_item("2 PLAYERS + BOT")


def clear(ctx, fortress = True):
	""" Empty map (with fortress walls), no enemies; returns the two humans and the guard """
	g, game = ctx.g, ctx.game
	level = game.level
	level.mapr = []
	if fortress:
		level.buildFortress(level.TILE_BRICK)
	level.updateObstacleRects()
	level.updateRemovableRects()
	del level.enemies_left[:]
	del g["enemies"][:]
	p1, p2, guard = g["players"]
	return p1, p2, guard


def enemy_bullet(ctx, position, direction, speed = None):
	""" Enemy bullet flying from position """
	g, game = ctx.g, ctx.game
	Bullet = g["Bullet"]
	bullet = Bullet(game.level, [position[0] - 12, position[1] - 12], direction)
	bullet.owner = bullet.OWNER_ENEMY
	bullet.rect.topleft = position
	if speed != None:
		bullet.speed = speed
	g["bullets"].append(bullet)
	return bullet


def make_enemy(ctx, position):
	""" Basic enemy standing still """
	g, game = ctx.g, ctx.game
	Enemy = g["Enemy"]
	game.level.enemies_left[:] = [Enemy.TYPE_BASIC]
	enemy = Enemy(game.level, 1, list(position))
	del game.level.enemies_left[:]
	enemy.state = enemy.STATE_ALIVE
	enemy.aquired_position = True
	enemy.bonus = None
	enemy.rect.topleft = list(position)
	enemy.paused = True
	g["enemies"].append(enemy)
	return enemy


def mode(ctx):
	""" 2 PLAYERS + BOT: two humans and a computer helper guarding the castle """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	players = g["players"]
	ctx.check("three tanks", len(players) == 3 and game.nr_of_players == 3)
	ctx.check("computer plays the third tank", game.bot == 3)
	ctx.check("players 1 and 2 are humans", players[0].bot == None and players[1].bot == None)
	ctx.check("player 1 keys work", players[0].controls == list(g["PLAYER_CONTROLS"][0]))
	ctx.check("player 2 keys work", players[1].controls == list(g["PLAYER_CONTROLS"][1]))
	ctx.check("helper is a guard bot", players[2].bot != None and players[2].bot.guard)
	ctx.check("helper isn't driven by keys or gamepads", players[2].controls == [] and players[2].gamepad == None)

	# helper's tank has its own color, so it isn't taken for player 2
	ctx.check("helper has its own color", players[2].color_order == g["BOT_COLOR_ORDER"] and players[0].color_order == None and players[1].color_order == None)

	def colors(player):
		""" Colors of the tank's sprite, grey ones (black, white) left out """
		image = player.image
		found = set([image.get_at((x, y))[:3] for x in range(0, 32, 2) for y in range(0, 32, 2)])
		return set([color for color in found if max(color) != min(color)])

	bot_colors, p2_colors = colors(players[2]), colors(players[1])
	ctx.check("helper is drawn in other colors than player 2 (%s vs %s)" % (sorted(bot_colors), sorted(p2_colors)),
		bot_colors and not (bot_colors & p2_colors))
	# green tank became blue: every color of it has more blue than green
	ctx.check("helper's tank is blue (%s)" % (sorted(bot_colors),), all([color[2] >= color[1] for color in bot_colors]))
	ctx.check("player 2 stays green (%s)" % (sorted(p2_colors),), all([color[1] >= color[2] for color in p2_colors]))
	ctx.finish()


def harmless(ctx):
	""" Helper's bullet never hurts a player: no damage, no stun, bullet just vanishes """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	p1, p2, guard = clear(ctx)
	p1.shielded = False
	p1.rect.topleft = [200, 200]
	guard.rect.topleft = [200, 300]
	guard.rotate(guard.DIR_UP, False)
	health, lives = p1.health, p1.lives
	game.playerFire(guard)
	bullet = g["bullets"][-1]
	ctx.check("helper fired", bullet.owner_class is guard)
	for i in range(60):
		bullet.update()
		if bullet.state == bullet.STATE_REMOVED:
			break
	ctx.check("bullet gone on the partner (%d)" % bullet.state, bullet.state == bullet.STATE_REMOVED)
	ctx.check("partner not damaged", p1.health == health and p1.lives == lives and p1.state == p1.STATE_ALIVE)
	ctx.check("partner not stunned", not p1.stunned and not p1.paralised)
	ctx.finish()


def our_bullets_dont_stop_it(ctx):
	""" A player's bullet doesn't damage or stun the computer partner either """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	p1, p2, guard = clear(ctx)
	guard.shielded = False
	guard.rect.topleft = [200, 200]
	p1.rect.topleft = [200, 300]
	p1.rotate(p1.DIR_UP, False)
	health, lives = guard.health, guard.lives
	game.playerFire(p1)
	bullet = g["bullets"][-1]
	for i in range(60):
		bullet.update()
		if bullet.state == bullet.STATE_REMOVED:
			break
	ctx.check("our bullet vanishes on the helper (%d)" % bullet.state, bullet.state == bullet.STATE_REMOVED)
	ctx.check("helper not damaged", guard.health == health and guard.lives == lives and guard.state == guard.STATE_ALIVE)
	ctx.check("helper not stunned", not guard.stunned and not guard.paralised)
	ctx.finish()


def careful(ctx):
	""" Guard takes care of itself: dodges every bullet, reacts fast, keeps away from enemies """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	p1, p2, guard = clear(ctx, fortress = False)
	bot = guard.bot
	ctx.check("guard dodges every bullet (%d%%)" % bot.setting("DODGE_CHANCE"), bot.setting("DODGE_CHANCE") == g["BOT_GUARD_DODGE_CHANCE"] >= g["BOT_DODGE_CHANCE"])
	ctx.check("guard reacts faster (%d frames)" % bot.setting("DODGE_REACTION_FRAMES"), bot.setting("DODGE_REACTION_FRAMES") <= g["BOT_DODGE_REACTION_FRAMES"])
	ctx.check("guard steps aside more often (%d%%)" % bot.setting("JUKE_CHANCE"), bot.setting("JUKE_CHANCE") >= g["BOT_JUKE_CHANCE"])
	ctx.check("guard keeps away from enemies (%d)" % bot.setting("ENEMY_COST"), bot.setting("ENEMY_COST") > g["BOT_ENEMY_COST"])

	# the partner bot keeps the common settings
	p1.rect.topleft = [0, 0]
	p2.rect.topleft = [32, 0]
	partner = g["Bot"](game, p1)
	ctx.check("partner bot uses common settings", partner.setting("DODGE_CHANCE") == g["BOT_DODGE_CHANCE"] and partner.setting("ENEMY_COST") == g["BOT_ENEMY_COST"])

	# guard's way goes around an enemy, not next to it
	guard.rect.topleft = [192, 320]
	enemy = make_enemy(ctx, [192, 256])
	bot.plan()
	near = set()
	for cell in bot.path:
		rect = pygame.Rect(cell[0] * 16, cell[1] * 16, 32, 32)
		if rect.inflate(16, 16).colliderect(enemy.rect):
			near.add(cell)
	ctx.check("guard's way doesn't touch the enemy (%s)" % sorted(near), not near)
	ctx.finish()


def never_shoots_players(ctx):
	""" Helper doesn't fire when a player is in its line of fire """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	p1, p2, guard = clear(ctx)
	bot = guard.bot
	guard.rect.topleft = [200, 300]
	guard.rotate(guard.DIR_UP, False)
	p1.rect.topleft = [200, 200]
	p2.rect.topleft = [500, 500]
	ctx.check("partner in line: not safe to fire", not bot.safeToFire(guard.DIR_UP))
	p1.rect.topleft = [300, 200]
	ctx.check("line free: safe to fire", bot.safeToFire(guard.DIR_UP))
	# own castle is never shot either
	guard.rect.topleft = [200, 300]
	guard.rotate(guard.DIR_DOWN, False)
	ctx.check("castle in line: not safe to fire", not bot.safeToFire(guard.DIR_DOWN))
	# an enemy behind the partner isn't aimed at
	p1.rect.topleft = [200, 200]
	make_enemy(ctx, [200, 100])
	guard.rotate(guard.DIR_UP, False)
	aim = bot.aim()
	ctx.check("enemy behind the partner isn't aimed at (%s)" % (aim,), aim == None or aim[0] != guard.DIR_UP)
	ctx.finish()


def shields_castle(ctx):
	""" Bullet flies at the castle: helper steps into it and doesn't dodge it """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	p1, p2, guard = clear(ctx, fortress = False)
	bot = guard.bot
	p1.rect.topleft = [0, 0]
	p2.rect.topleft = [32, 0]
	castle = g["castle"]

	# bullet flying down at the castle from above
	bullet = enemy_bullet(ctx, [castle.rect.centerx - 4, 250], 2)
	threats = bot.castleThreats()
	ctx.check("bullet is a threat to the castle (%s)" % (threats,), len(threats) == 1)
	ctx.check("it hits the castle soon (%d frames)" % threats[0][0], threats[0][0] <= g["BOT_GUARD_SHIELD_FRAMES"])

	# helper standing beside the lane steps into it
	guard.rect.topleft = [castle.rect.centerx + 12, 330]
	guard.rotate(guard.DIR_UP, False)
	direction = bot.shieldCastle()
	ctx.check("helper steps into the bullet lane (%s)" % direction, direction == guard.DIR_LEFT)

	# helper on the lane stays there and turns to the bullet
	guard.rect.topleft = [castle.rect.centerx - 16, 330]
	guard.rotate(guard.DIR_RIGHT, False)
	bot.move_px = 0
	direction = bot.shieldCastle()
	ctx.check("helper on the lane turns to the bullet (%s)" % direction, direction == guard.DIR_UP)
	ctx.check("helper covers the castle", bot.shieldsCastle(bullet))

	# and it doesn't dodge that bullet, even though it flies at the tank
	g["BOT_DODGE_CHANCE"] = 100
	bot.bullets = {id(bullet): [-1000, True]}
	guard.rotate(guard.DIR_RIGHT, False)
	dodges = [bot.dodge() for i in range(10)]
	ctx.check("helper doesn't dodge a bullet aimed at the castle (%s)" % dodges, all([d == None for d in dodges]))

	# a bullet still far from the castle isn't blocked yet: no need to risk the tank
	g["bullets"][:] = []
	far = enemy_bullet(ctx, [castle.rect.centerx - 4, 40], 2)
	guard.rect.topleft = [castle.rect.centerx + 12, 330]
	bot.move_px = 0
	ctx.check("far bullet isn't blocked yet (%d frames)" % bot.castleThreats()[0][0], bot.shieldCastle() == None)

	# a bullet not aimed at the castle is dodged as usual
	g["bullets"][:] = []
	guard.rect.topleft = [64, 330]
	side = enemy_bullet(ctx, [guard.rect.centerx - 4, 250], 2)
	ctx.check("side bullet is not a castle threat", bot.castleThreats() == [])
	bot.bullets = {id(side): [-1000, True]}
	ctx.check("helper dodges a bullet aimed at itself", bot.dodge() != None)
	ctx.finish()


def keeps_to_castle(ctx):
	""" Helper doesn't wander off: its place stays near the castle """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	p1, p2, guard = clear(ctx, fortress = False)
	bot = guard.bot
	p1.rect.topleft = [0, 0]
	p2.rect.topleft = [32, 0]
	guard.rect.topleft = [192, 320]
	castle = g["castle"]
	# one far enemy at the top: a normal bot would go there, the guard stays home
	make_enemy(ctx, [0, 32])
	bot.plan()
	goal = bot.goal
	distance = None
	if goal != None:
		rect = pygame.Rect(goal[0] * 16, goal[1] * 16, 32, 32)
		distance = (abs(rect.centerx - castle.rect.centerx) + abs(rect.centery - castle.rect.centery)) / 16.0
	ctx.check("guard stays within %d cells of the castle (%s cells, place %s)" % (g["BOT_GUARD_RADIUS"], distance, goal),
		goal != None and distance <= g["BOT_GUARD_RADIUS"] + 2)
	ctx.finish()


def borrow_life(ctx):
	""" A player without lives borrows one from a partner: key B and gamepad Select """
	g, game = ctx.g, ctx.game
	if ctx.frame != 5:
		return
	p1, p2, guard = clear(ctx)
	Gamepad = g["Gamepad"]

	class FakeGamepad(Gamepad):
		def __init__(self):
			Gamepad.__init__(self)
			self.held_buttons = set()

		def read(self):
			state = dict([(name, False) for name in ("up", "right", "down", "left", "fire", "start", "select")])
			state["select"] = g["GAMEPAD_SELECT_BUTTON"] in self.held_buttons if g["GAMEPAD_SELECT_BUTTON"] != None else bool(self.held_buttons & set([6, 8]))
			return state

		def buttonsHeld(self):
			return set(self.held_buttons)

	# player 1 is out of lives, player 2 has a spare one
	p1.state = p1.STATE_DEAD
	p1.lives = 0
	p2.lives = 2
	guard.lives = 3

	pad = FakeGamepad()
	game.gamepads = [pad]
	game.assignGamepads()
	ctx.check("gamepad goes to a human, not to the helper", p1.gamepad is pad and guard.gamepad == None)

	pad.held_buttons = set([6])
	game.updateGamepads()
	game.applyGamepads()
	ctx.check("Select: partner's life taken (P1 %d lives, P2 %d)" % (p1.lives, p2.lives),
		p1.state != p1.STATE_DEAD and p1.lives == 1 and p2.lives == 1)

	# helper never takes a human's life
	guard.state = guard.STATE_DEAD
	guard.lives = 0
	p2.lives = 2
	ctx.check("helper gets no life from a player", not game.borrowLife(guard) and guard.lives == 0 and p2.lives == 2)

	# nobody to borrow from: partner has only one life left
	p2.state, p2.lives = p2.STATE_DEAD, 0
	p1.lives = 1
	ctx.check("nothing to borrow from a last life", not game.borrowLife(p2) and p1.lives == 1)
	p1.lives = 2
	ctx.check("key B borrows too", game.borrowLife() and p2.lives == 1 and p1.lives == 1)
	ctx.finish()


SCENARIOS = {
	"mode": {"fn": mode, "menu": GUARD_MENU},
	"harmless": {"fn": harmless, "menu": GUARD_MENU},
	"never_shoots_players": {"fn": never_shoots_players, "menu": GUARD_MENU},
	"our_bullets_dont_stop_it": {"fn": our_bullets_dont_stop_it, "menu": GUARD_MENU},
	"careful": {"fn": careful, "menu": GUARD_MENU},
	"shields_castle": {"fn": shields_castle, "menu": GUARD_MENU},
	"keeps_to_castle": {"fn": keeps_to_castle, "menu": GUARD_MENU},
	"borrow_life": {"fn": borrow_life, "menu": GUARD_MENU},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
