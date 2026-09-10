""" NES like rules: extra life, 2 player kills bonus, enemy AI towards base, presets """

import harness


def extra_life(ctx):
	g, d = ctx.g, ctx.data
	p = g["players"][0]
	if ctx.frame == 10:
		d["lives"] = p.lives
		p.score = g["EXTRA_LIFE_SCORE"] - 100
	if ctx.frame == 12:
		ctx.check("no extra life below score", p.lives == d["lives"])
		p.score += 200
	if ctx.frame == 14:
		ctx.check("extra life at %d points" % g["EXTRA_LIFE_SCORE"], p.lives == d["lives"] + 1)
		ctx.check("next extra life at double score", p.next_extra_life == 2 * g["EXTRA_LIFE_SCORE"])
		ctx.finish()


def finish_level(ctx):
	del ctx.game.level.enemies_left[:]
	for enemy in ctx.g["enemies"]:
		enemy.state = enemy.STATE_DEAD


def kills_bonus(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	players = g["players"]
	# level finishes when last enemy is removed, so wait for first spawn
	if ctx.frame == 100:
		players[0].trophies["enemy0"] = 3
		players[1].trophies["enemy1"] = 1
		d["scores"] = [p.score for p in players]
		finish_level(ctx)
	if ctx.frame > 100 and ctx.in_function("showScores") and "checked" not in d:
		d["checked"] = True
		bonus = g["TWO_PLAYER_KILLS_BONUS"]
		ctx.check("player with most kills gets bonus", players[0].score == d["scores"][0] + bonus)
		ctx.check("other player doesn't", players[1].score == d["scores"][1])
	if "checked" in d and game.stage == 2 and game.running:
		ctx.finish()


def kills_tie(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	players = g["players"]
	if ctx.frame == 100:
		players[0].trophies["enemy0"] = 2
		players[1].trophies["enemy2"] = 2
		d["scores"] = [p.score for p in players]
		finish_level(ctx)
	if ctx.frame > 100 and ctx.in_function("showScores") and "checked" not in d:
		d["checked"] = True
		ctx.check("tie: nobody gets kills bonus", [p.score for p in players] == d["scores"])
	if "checked" in d and game.stage == 2 and game.running:
		ctx.finish()


def three_players_scores(ctx):
	g, game, d = ctx.g, ctx.game, ctx.data
	if ctx.frame == 100:
		g["players"][2].trophies["enemy3"] = 2
		finish_level(ctx)
	if game.stage == 2 and game.running:
		ctx.check("3 players scores screen shown without errors", True)
		ctx.finish()


def ai_base(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 10:
		return
	Enemy = g["Enemy"]
	g["ENEMY_AI_BASE_CHANCE"] = 100
	game.level.enemies_left[:] = [0] * 30
	# top left corner of level 1: both down and right are free
	chosen = set()
	for i in range(20):
		enemy = Enemy(game.level, 1, [0, 0])
		enemy.generatePath(None)
		chosen.add(enemy.direction)
	ctx.check("with 100%% chance enemy goes towards base (down/right): %s" % sorted(chosen),
		chosen <= set([enemy.DIR_DOWN, enemy.DIR_RIGHT]))
	ctx.finish()


def presets(ctx):
	g, game = ctx.g, ctx.game
	if ctx.frame != 10:
		return
	p = g["players"][0]

	g["applyPreset"]("CLASSIC")
	ctx.check("CLASSIC preset: 4 enemies on screen", g["MAX_ACTIVE_ENEMIES"] == 4)
	ctx.check("CLASSIC preset: enemies don't pick up bonuses", g["ENEMY_PICKUP_BONUSES"] == False)
	ctx.check("CLASSIC preset: armor tank 4 hits", g["DEFAULT_ENEMY_ARMOR_HEALTH"] == 400)
	game.respawnPlayer(p)
	ctx.check("respawn uses current preset superpower (0)", p.superpowers == 0)

	g["applyPreset"]("GOOD")
	ctx.check("GOOD preset: 5 enemies on screen", g["MAX_ACTIVE_ENEMIES"] == 5)
	ctx.check("current preset remembered", g["CURRENT_PRESET"] == "GOOD")
	game.respawnPlayer(p)
	ctx.check("respawn uses current preset superpower (1)", p.superpowers == 1)
	ctx.finish()


SCENARIOS = {
	"extra_life": {"fn": extra_life},
	"kills_bonus": {"fn": kills_bonus, "players": 2},
	"kills_tie": {"fn": kills_tie, "players": 2},
	"three_players_scores": {"fn": three_players_scores, "players": 3},
	"ai_base": {"fn": ai_base},
	"presets": {"fn": presets},
}

if __name__ == "__main__":
	harness.main(SCENARIOS)
