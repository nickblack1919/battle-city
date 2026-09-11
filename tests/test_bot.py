""" Computer partner (1 PLAYER + BOT): menu, controls, shooting, safety rules, dodging, not stuck, hiscores, saved game """

import os, json
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


BOT_MENU = select_menu_item("1 PLAYER + BOT")


def empty_field(ctx, fortress = False):
	""" Map without tiles (fortress walls optionally), no enemies; returns human and bot players """
	g, game = ctx.g, ctx.game
	level = game.level
	level.mapr = []
	if fortress:
		level.buildFortress(level.TILE_BRICK)
	level.updateObstacleRects()
	level.updateRemovableRects()
	del level.enemies_left[:]
	del g["enemies"][:]
	human, bot = g["players"]
	return human, bot


def make_enemy(ctx, position, add = True):
	""" Basic enemy standing still (paused: doesn't move or fire) """
	g, game = ctx.g, ctx.game
	Enemy = g["Enemy"]
	game.level.enemies_left[:] = [Enemy.TYPE_BASIC]
	enemy = Enemy(game.level, 1, position)
	del game.level.enemies_left[:]
	enemy.state = enemy.STATE_ALIVE
	enemy.aquired_position = True
	enemy.bonus = None
	enemy.rect.topleft = position
	enemy.paused = True
	if add:
		g["enemies"].append(enemy)
	return enemy


def bot_bullets(ctx, bot):
	return [bullet for bullet in ctx.g["bullets"] if bullet.owner_class is bot]


def fortress_tiles(ctx):
	level = ctx.game.level
	rect = pygame.Rect(11 * 16, 23 * 16, 4 * 16, 3 * 16)
	return len([tile for tile in level.mapr if rect.colliderect(tile)])


def menu_bot(ctx):
	""" Menu item starts 2 player game with bot as player 2, P2 keys and gamepads don't control it, texts fit """
	g, game, d = ctx.g, ctx.game, ctx.data
	players = g["players"]
	if ctx.frame == 1:
		human, bot = players[0], players[1] if len(players) > 1 else None
		ctx.check("campaign with 2 players, player 2 is bot", game.mode == "campaign" and game.bot and len(players) == 2)
		ctx.check("bot drives player 2, player 1 is human", bot.bot != None and human.bot == None)
		ctx.check("bot has no keys", bot.controls == [] and human.controls != [])

		Gamepad = g["Gamepad"]
		pads = [Gamepad(), Gamepad()]
		game.gamepads = pads
		for assign in (["AUTO", "AUTO", "AUTO"], ["OFF", 1, "AUTO"]):
			g["GAMEPAD_ASSIGN"] = assign
			game.assignGamepads()
			ctx.check("no gamepad for bot (%s)" % assign, bot.gamepad == None)
		game.gamepads = []
		g["GAMEPAD_ASSIGN"] = ["AUTO", "AUTO", "AUTO"]
		game.assignGamepads()

		empty_field(ctx)
		# bot doesn't press anything now: only keys could move it
		bot.bot.update = lambda: None
		d["position"] = bot.rect.topleft
		controls = g["PLAYER_CONTROLS"][1]
		d["keys"] = [controls[0], controls[1]]
		return [ctx.key(key) for key in d["keys"]]
	bot = players[1]
	if ctx.frame == 30:
		ctx.check("P2 keys don't move bot (%s -> %s)" % (d["position"], bot.rect.topleft), bot.rect.topleft == d["position"])
		ctx.check("P2 fire key doesn't fire", bot_bullets(ctx, bot) == [])
		return [ctx.key(key, up=True) for key in d["keys"]]
	if ctx.frame == 32:
		lang = g["lang"]
		items = game.menuItems()
		for count in (len(items), len(items) + 1):
			step, top = game.menuLayout(count)
			ctx.check("%d menu items fit on screen (top %d, step %d)" % (count, top, step), top >= 216 and top + (count - 1) * step + 16 <= 416)
		for language in ("EN", "RU"):
			g["LANGUAGE"] = language
			for label in ("1 PLAYER + BOT", "ENDLESS 1P + BOT"):
				width = game.text(label, True, (255, 255, 255)).get_width()
				ctx.check("%s %s fits menu (%d px)" % (language, lang.tr(label), width), 165 + width <= 470)
			sidebar = game.text("BOT", False, (0, 0, 0)).get_width()
			ctx.check("%s BOT fits sidebar (%d px)" % (language, sidebar), 424 + sidebar <= 480)
			game.draw()
			game.drawIntroScreen()
		ctx.check("RU translation", lang.tr("1 PLAYER + BOT") == u"1 ИГРОК + БОТ" and lang.tr("BOT") == u"БОТ")
		g["LANGUAGE"] = "EN"
		ctx.finish()


def endless_bot(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 1:
		players = g["players"]
		ctx.check("endless with bot", game.mode == "endless" and game.bot and len(players) == 2 and players[1].bot != None)
		ctx.finish()


def shoots_enemy(ctx):
	""" Empty map, enemy far away: bot drives to it and destroys it """
	g, game, d = ctx.g, ctx.game, ctx.data
	human, bot = g["players"]
	if ctx.frame == 1:
		empty_field(ctx)
		human.rect.topleft = [0, 384]
		d["enemy"] = make_enemy(ctx, [320, 96])
		d["start"] = bot.rect.topleft
	human.shielded = bot.shielded = True
	enemy = d["enemy"]
	if enemy.state != enemy.STATE_ALIVE or ctx.frame == 600:
		ctx.check("bot destroyed enemy (frame %d, bot at %s)" % (ctx.frame, bot.rect.topleft), enemy.state != enemy.STATE_ALIVE and bot.trophies["enemy0"] == 1)
		ctx.check("bot drove there", bot.rect.topleft != d["start"])
		ctx.finish()


def human_in_line(ctx):
	""" Human between bot and enemy: bot doesn't fire; human goes away: bot fires """
	g, game, d = ctx.g, ctx.game, ctx.data
	human, bot = g["players"]
	if ctx.frame == 1:
		empty_field(ctx)
		g["FRIENDLY_FIRE"] = True
		d["enemy"] = make_enemy(ctx, [96, 32])
		bot.rect.topleft = [96, 320]
		bot.rotate(bot.DIR_UP, False)
		# bot can't drive away to shoot from elsewhere
		bot.speed = 0
		human.rect.topleft = [96, 176]
		d["shots"] = 0
	human.shielded = bot.shielded = True
	if ctx.frame < 250:
		d["shots"] += len(bot_bullets(ctx, bot))
		if human.stunned:
			d["stunned"] = True
	if ctx.frame == 250:
		ctx.check("no shots while human is in line (%d bullet frames)" % d["shots"], d["shots"] == 0)
		ctx.check("human not stunned", not d.get("stunned"))
		human.rect.topleft = [300, 176]
	if ctx.frame > 250 and (bot_bullets(ctx, bot) or ctx.frame == 450):
		ctx.check("bot fires when human is out of line (frame %d)" % ctx.frame, bot_bullets(ctx, bot))
		ctx.finish()


def fortress(ctx):
	""" Enemy left of the castle in bot's row: bot doesn't shoot through castle, destroys enemy from elsewhere """
	g, game, d = ctx.g, ctx.game, ctx.data
	human, bot = g["players"]
	if ctx.frame == 1:
		empty_field(ctx, True)
		human.rect.topleft = [384, 0]
		d["enemy"] = make_enemy(ctx, [32, 384])
		bot.rect.topleft = [256, 384]
		bot.rotate(bot.DIR_LEFT, False)
		d["tiles"] = fortress_tiles(ctx)
		ctx.check("fortress built (%d tiles)" % d["tiles"], d["tiles"] > 0)
		ctx.check("castle in line: not safe to fire", not bot.bot.safeToFire(bot.DIR_LEFT, 160))
		d["broken"] = None
	human.shielded = bot.shielded = True
	if d["broken"] == None and (fortress_tiles(ctx) != d["tiles"] or not g["castle"].active):
		d["broken"] = ctx.frame
	enemy = d["enemy"]
	if enemy.state != enemy.STATE_ALIVE or ctx.frame == 900:
		ctx.check("fortress walls and castle intact (broken at frame %s)" % d["broken"], d["broken"] == None)
		ctx.check("bot destroyed enemy next to fortress from a safe place (frame %d, bot at %s)" % (ctx.frame, bot.rect.topleft), enemy.state != enemy.STATE_ALIVE)
		ctx.finish()


def dodge(ctx, chance):
	""" Enemy bullet flies at standing bot from above: bot dodges it (BOT_DODGE_CHANCE 100) or is hit (0) """
	g, game, d = ctx.g, ctx.game, ctx.data
	human, bot = g["players"]
	if ctx.frame == 1:
		empty_field(ctx)
		g["BOT_DODGE_CHANCE"] = chance
		g["BOT_JUKE_CHANCE"] = 0
		bot.rect.topleft = [192, 192]
		bot.rotate(bot.DIR_RIGHT, False)
		# no goals: bot only reacts to the bullet
		bot.bot.plan = lambda: None
		bot.bot.path = []
		shooter = make_enemy(ctx, [192, 0], add=False)
		Bullet = g["Bullet"]
		bullet = Bullet(game.level, [192, 16], Bullet.DIR_DOWN)
		bullet.owner, bullet.owner_class = Bullet.OWNER_ENEMY, shooter
		g["bullets"].append(bullet)
	human.shielded = True
	bot.shielded = False
	if bot.state != bot.STATE_ALIVE or ctx.frame == 120:
		if chance:
			ctx.check("bot dodges enemy bullet (%s)" % (bot.rect.topleft,), bot.state == bot.STATE_ALIVE and bot.rect.topleft != (192, 192))
		else:
			ctx.check("bot that doesn't dodge is hit", bot.state != bot.STATE_ALIVE)
		ctx.finish()


def lets_human_pass(ctx):
	""" Human drives into bot standing in his way: bot drives aside """
	g, game, d = ctx.g, ctx.game, ctx.data
	human, bot = g["players"]
	if ctx.frame == 1:
		empty_field(ctx)
		human.rect.topleft = [96, 320]
		human.rotate(human.DIR_UP, False)
		bot.rect.topleft = [96, 288]
		bot.aquired_position = human.aquired_position = True
		bot.bot.plan = lambda: None
		bot.bot.path = []
		return [ctx.key(g["PLAYER_CONTROLS"][0][1])]
	human.shielded = bot.shielded = True
	if human.rect.top <= 240 or ctx.frame == 150:
		ctx.check("human passed bot (human y %d, bot at %s, frame %d)" % (human.rect.top, bot.rect.topleft, ctx.frame), human.rect.top <= 240)
		ctx.finish()


def playing(ctx):
	""" Real level: bot drives, fires, isn't inside walls and doesn't stand still without reason for 10 s """
	g, game, d = ctx.g, ctx.game, ctx.data
	human, bot = g["players"]
	if ctx.frame == 1:
		# enemies can't win: castle can't be destroyed
		g["castle"].destroy = lambda: None
		d.update(start=bot.rect.topleft, moved=False, last=(None, 0), longest=0, bullets=set(), in_wall=0)
	human.shielded = bot.shielded = True
	if bot.state == bot.STATE_ALIVE and game.running and not game.game_over:
		for bullet in bot_bullets(ctx, bot):
			d["bullets"].add(id(bullet))
		if abs(bot.rect.left - d["start"][0]) + abs(bot.rect.top - d["start"][1]) > 96:
			d["moved"] = True
		position, since = d["last"]
		# standing and shooting (or being frozen) is fine
		if position != bot.rect.topleft or bot_bullets(ctx, bot) or bot.paralised:
			d["last"] = (bot.rect.topleft, ctx.frame)
		else:
			d["longest"] = max(d["longest"], ctx.frame - since)
		if bot.aquired_position and bot.rect.collidelist(game.level.obstacleRectsFor(bot.canSwim())) != -1:
			d["in_wall"] += 1
	else:
		d["last"] = (None, ctx.frame)
	if ctx.frame == 1500:
		ctx.check("bot drove far", d["moved"])
		ctx.check("bot fired (%d bullets)" % len(d["bullets"]), len(d["bullets"]) >= 3)
		ctx.check("bot not inside walls (%d frames)" % d["in_wall"], d["in_wall"] == 0)
		ctx.check("bot didn't stand still without shooting for 10 s (longest %d frames)" % d["longest"], d["longest"] < 500)
		ctx.finish()


def hiscore_human_only(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	human, bot = g["players"]
	if ctx.frame == 20:
		human.score = 1500
		bot.score = 60000
		d["entries"] = []
		def enterName(player_nr, score):
			d["entries"].append((player_nr, score))
			return "HUM"
		game.enterName = enterName
		game.showHiscores = lambda mode, duration: None
		g["castle"].destroy()
	if ctx.frame > 20 and ctx.in_function("gameOverScreen"):
		ctx.check("only human enters name (%s)" % d["entries"], d["entries"] == [(0, 1500)])
		with open(g["dataFile"](g["HISCORES_FILE"])) as f:
			tables = json.load(f)
		ctx.check("hiscore table has only human (%s)" % tables, list(tables.values()) == [[["HUM", 1500]]])
		ctx.check("bot's score isn't hi-score (%d)" % game.loadHiscore(), game.loadHiscore() != 60000)
		ctx.finish()


def savegame_file():
	return os.path.join(harness.DATA_DIR, ".savegame")


def save_bot(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 100:
		del game.level.enemies_left[:]
		for enemy in g["enemies"]:
			enemy.state = enemy.STATE_DEAD
	if ctx.frame > 100 and game.stage == 2 and game.running:
		with open(savegame_file()) as f:
			data = json.load(f)
		ctx.check("saved game remembers bot (%s)" % data.get("bot"), data.get("bot") == True and data["nr_of_players"] == 2)
		ctx.check("bot still plays next stage", g["players"][1].bot != None)
		ctx.finish()


def write_bot_savegame():
	data = {
		"stage": 3,
		"nr_of_players": 2,
		"bot": True,
		"preset": "GOOD",
		"players": [
			{"score": 12300, "lives": 2, "superpowers": 1, "next_extra_life": 20000},
			{"score": 4500, "lives": 4, "superpowers": 0, "next_extra_life": 20000},
		],
	}
	with open(savegame_file(), "w") as f:
		json.dump(data, f)


def continue_bot(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame == 1:
		human, bot = g["players"]
		ctx.check("continued game has bot", game.bot and bot.bot != None and human.bot == None and bot.controls == [])
		ctx.check("stage and stats restored", game.stage == 4 and bot.score == 4500 and bot.lives == 4)
		ctx.finish()


def borrow_life(ctx):
	""" B gives dead human a life of the bot, never human's life to the bot """
	g, game, d = ctx.g, ctx.game, ctx.data
	human, bot = g["players"]
	human.shielded = bot.shielded = True
	if ctx.frame == 5:
		bot.lives = 3
		human.lives = 1
		human.state = human.STATE_DEAD
	if ctx.frame == 10:
		ctx.check("human without lives", human.state == human.STATE_DEAD and human.lives == 0 and not game.game_over)
		return [ctx.key(pygame.K_b)]
	if ctx.frame == 12:
		ctx.check("B: human borrowed bot's life", human.state != human.STATE_DEAD and human.lives == 1 and bot.lives == 2)
	if ctx.frame == 15:
		human.lives = 3
		bot.lives = 1
		bot.state = bot.STATE_DEAD
	if ctx.frame == 20:
		ctx.check("bot without lives", bot.state == bot.STATE_DEAD and bot.lives == 0)
		return [ctx.key(pygame.K_b)]
	if ctx.frame == 25:
		ctx.check("B doesn't give human's life to bot", bot.state == bot.STATE_DEAD and human.lives == 3)
		ctx.finish()


SCENARIOS = {
	"menu_bot": {"fn": menu_bot, "menu": BOT_MENU},
	"endless_bot": {"fn": endless_bot, "menu": select_menu_item("ENDLESS 1P + BOT")},
	"shoots_enemy": {"fn": shoots_enemy, "menu": BOT_MENU},
	"human_in_line": {"fn": human_in_line, "menu": BOT_MENU},
	"fortress": {"fn": fortress, "menu": BOT_MENU},
	"dodge": {"fn": lambda ctx: dodge(ctx, 100), "menu": BOT_MENU},
	"no_dodge": {"fn": lambda ctx: dodge(ctx, 0), "menu": BOT_MENU},
	"lets_human_pass": {"fn": lets_human_pass, "menu": BOT_MENU},
	"playing": {"fn": playing, "menu": BOT_MENU},
	"hiscore_human_only": {"fn": hiscore_human_only, "menu": BOT_MENU},
	"save_bot": {"fn": save_bot, "menu": BOT_MENU},
	"continue_bot": {"fn": continue_bot, "menu": select_menu_item("CONTINUE"), "setup": write_bot_savegame},
	"borrow_life": {"fn": borrow_life, "menu": BOT_MENU},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
