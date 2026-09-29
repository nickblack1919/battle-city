# coding=utf-8
""" Battle City: build the 30 new campaign levels (NEW LEVELS setting)

Maps are made by the level generator (battlecity/levelgen.py) from fixed seeds, so they are
reproducible: running this tool again gives the same 30 levels. Difficulty of level n uses the
generator's stage n * 35 / 30, so the set grows from open maps to dense ones like the original campaign.
Every map is checked by the generator itself (enemy spawns reach the castle, players reach every spawn)
and here once more: protected areas free, fortress walls in place, not too empty and not too dense.

Run: venv/bin/python tools/make_levels.py [--check]
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from battlecity import levelgen

LEVELS = 30
DIRECTORY = os.path.join("levels", "new")
# one seed per level: different maps, same result on every run
SEEDS = [7130 + 137 * (n + 1) for n in range(LEVELS)]


def levelRows(number):
	""" Rows of new level number (1..30) """
	stage = max(1, min(35, int(round(number * 35.0 / LEVELS))))
	return levelgen.generateLevel(SEEDS[number - 1], stage)


def check(number, rows):
	""" Level is playable and looks like a level: returns list of problems """
	problems = []
	grid = [list(row) for row in rows]
	if len(grid) != levelgen.SIZE or any([len(row) != levelgen.SIZE for row in grid]):
		return ["wrong size"]
	for col, row in levelgen.PROTECTED:
		for x in range(col, col + 2):
			for y in range(row, row + 2):
				if grid[y][x] != ".":
					problems.append("protected cell %d,%d is %s" % (x, y, grid[y][x]))
	for col, row in levelgen.FORTRESS:
		if grid[row][col] not in "#@":
			problems.append("fortress cell %d,%d is %s" % (col, row, grid[row][col]))
	if not levelgen.isPlayable(grid):
		problems.append("not playable")
	filled = sum([1 for row in grid for ch in row if ch != "."])
	if filled < 120:
		problems.append("too empty (%d cells)" % filled)
	if filled > 520:
		problems.append("too dense (%d cells)" % filled)
	return problems


def main():
	only_check = "--check" in sys.argv
	if not only_check and not os.path.isdir(DIRECTORY):
		os.makedirs(DIRECTORY)
	failed = 0
	for number in range(1, LEVELS + 1):
		rows = levelRows(number)
		problems = check(number, rows)
		if problems:
			failed += 1
			print("level %d: %s" % (number, ", ".join(problems)))
		if not only_check:
			with open(os.path.join(DIRECTORY, str(number)), "w") as f:
				f.write("\n".join(rows))
	print("%d levels %s, %d with problems" % (LEVELS, "checked" if only_check else "written to " + DIRECTORY, failed))
	return 1 if failed else 0


if __name__ == "__main__":
	sys.exit(main())
