""" Endless mode and hiscore tables with names """

import os, json
import harness
import pygame


def hiscores_file():
	return os.path.join(harness.DATA_DIR, ".hiscores.json")


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


def finish_level(ctx):
	del ctx.game.level.enemies_left[:]
	for enemy in ctx.g["enemies"]:
		enemy.state = enemy.STATE_DEAD


def endless(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 1:
		ctx.check("endless mode started", game.mode == "endless" and game.nr_of_players == 2 and len(g["players"]) == 2)
	# level finishes when last enemy is removed, so wait for first spawn
	if ctx.frame == 100:
		finish_level(ctx)
	if ctx.frame > 100:
		if ctx.in_function("showScores"):
			d["scores_shown"] = True
		if game.stage == 2 and game.running:
			ctx.check("next wave starts without scores screen", not d.get("scores_shown"))
			ctx.check("endless is still active", game.mode == "endless")

			game.stage = 5
			game.loadLevelEnemies(False)
			# stage 5 table: 20 tanks; wave 5 (4 waves after first): +2 fast, +1 armor (boss not counted)
			boss_type = getattr(g["Enemy"], "TYPE_BOSS", None)
			tanks = [t for t in game.level.enemies_left if t != boss_type]
			ctx.check("waves get harder (%d tanks)" % len(tanks), len(tanks) == 23)
			ctx.finish()


def write_hiscores():
	table = [["AAA", 1000 * (10 - i)] for i in range(10)]
	with open(hiscores_file(), "w") as f:
		json.dump({"campaign": table, "endless": []}, f)


def name_entry(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	phase = d.get("phase", "start")

	if phase == "start" and ctx.frame == 20:
		g["players"][0].score = 5500
		g["castle"].destroy()
		d["phase"] = "wait_entry"

	elif phase == "wait_entry" and ctx.in_function("enterName"):
		d["phase"] = "typing"
		d["typing_frame"] = ctx.total_frames

	elif phase == "typing":
		step = ctx.total_frames - d["typing_frame"]
		if step == 1:
			return [ctx.key(pygame.K_UP)]	# A -> B
		if step == 2:
			return [ctx.key(pygame.K_RIGHT)]
		if step == 3:
			return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z, mod=0, unicode="z", scancode=0)]	# Z, cursor moves
		if step == 4:
			return [ctx.key(pygame.K_DOWN)]	# A -> space
		if step == 5:
			return [ctx.key(pygame.K_DOWN)]	# space -> 9
		if step == 6:
			d["phase"] = "table"
			return [ctx.key(pygame.K_RETURN)]

	elif phase == "table" and ctx.in_function("showHiscores"):
		with open(hiscores_file()) as f:
			# old table without preset went to current preset (GOOD)
			table = json.load(f)["campaign GOOD"]
		ctx.check("table still has 10 entries", len(table) == 10)
		# 10000 ... 6000, then new 5500
		ctx.check("new entry with typed name at 6th place: %s" % table[5], table[5] == ["BZ9", 5500])
		ctx.check("lowest old entry dropped", table[-1][1] == 2000)
		d["phase"] = "skip_table"
		return [ctx.key(pygame.K_SPACE)]

	elif phase == "skip_table" and ctx.in_function("gameOverScreen") and not ctx.in_function("showHiscores"):
		ctx.check("any key skips hiscore table", True)
		ctx.finish()


def no_entry_for_zero_score(ctx):
	d = ctx.data
	if ctx.frame == 20:
		ctx.g["castle"].destroy()
	if ctx.frame > 20:
		if ctx.in_function("enterName"):
			d["entry"] = True
		if ctx.in_function("gameOverScreen"):
			ctx.check("no name entry with zero score", not d.get("entry"))
			ctx.check("hiscores file not created", not os.path.isfile(hiscores_file()))
			ctx.finish()


SCENARIOS = {
	"endless": {"fn": endless, "menu": select_menu_item("ENDLESS 2P")},
	"name_entry": {"fn": name_entry, "setup": write_hiscores},
	"no_entry_for_zero_score": {"fn": no_entry_for_zero_score},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
