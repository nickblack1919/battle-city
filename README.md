# battle-city

My favorite retro game: Battle City (NES, 1985) remake in Python and pygame, with extra modes and features.

## Run

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python tanks.py
```

Command line arguments:

| Argument | Meaning |
|---|---|
| `-l N`, `--level N` | start level (has priority over start level from settings) |
| `-f`, `--fullscreen` | start in full screen mode |

## Controls

| | Player 1 | Player 2 | Player 3 |
|---|---|---|---|
| Move | W A S D | arrows | gamepad |
| Fire (hold for auto fire) | J | right Shift | gamepad A / B / X / Y |

Player 1 and 2 keys can be changed on the settings screen. Gamepads are assigned to player 3 first,
then to players 1 and 2 (can be changed on the settings screen); gamepad Start pauses the game.

| Key | Action |
|---|---|
| Enter | pause |
| Ctrl+F / Cmd+F / Alt+Enter | full screen / window |
| M | sound on / off |
| B | borrow a life from partner for a player without lives |
| ESC | quit (in editor and settings: back to menu) |
| P | freeze enemies (debug) |
| V | debug sprites and grid |

## Game modes

- **1 / 2 / 3 PLAYERS** - campaign: 35 stages, scores screen after every stage. Progress is saved after each stage.
- **CONTINUE** - continue saved campaign (shown when there is a saved game).
- **ENDLESS 1P / 2P** - waves of enemies until game over, every wave is harder.
- **VERSUS** - two players fight each other, each defends own castle; destroyed castle or no lives left loses.
- **LEVEL EDITOR** - edit any of 35 levels: arrows / mouse move cursor, 1-5 tile, 0 eraser, space / left mouse draw,
  right mouse erase, `[` `]` level, S save, D back to original level, T save and play.
- **SETTINGS** - difficulty preset, sound, full screen, start level, controls, NES speed (DENDY / NTSC),
  auto fire (ON by default - holding fire button shoots again when bullet slot is free; OFF - every shot needs
  a press, like on NES), enemy AI (CLASSIC - random paths, sometimes towards the castle; NES - like on NES: at
  stage start enemies drive in random directions, later chase players, then go to the castle; a blocked tank
  waits or turns; SMART - finds the cheapest way to a player or the castle (through bricks, around steel and water),
  shoots bricks on its way and aims at a target in line of fire after a short reaction time; armor tanks go to the
  castle, fast tanks hunt players, other tanks take turns), gamepads: which gamepad every player uses (AUTO, OFF or gamepad number) and gamepad fire /
  start buttons (Enter, then press the gamepad button; left arrow - default buttons), language (EN / RU; Russian
  text uses pygame default font, the game font has no Cyrillic letters).
- **DEMO** - after 20 seconds in the menu without input the computer plays a 2 player game; any key returns to menu.

Campaign and endless mode have hiscore tables for every difficulty preset: players with top 10 score enter their names after game over.

## Difficulty presets

| Preset | |
|---|---|
| CLASSIC | NES rules: 4 enemies on screen (6 in 2 player game), armor tank 4 hits, bonus carried by 4th / 11th / 18th tank, NES bonus set, bonus stays until picked up, enemies pick up bonuses too (not on NES), friendly fire stuns partner, one extra life, NES enemy spawn intervals, no new enemies |
| GOOD (default) | more enemies, enemies pick up bonuses, player starts with one star, new enemies |
| EXTREME | even more enemies in 2-3 player games |

In every preset timings are taken from NES version (disassembly, counted in NES frames): tank and bullet speeds,
shield, helmet, shovel and clock durations, enemy fire rate, spawn animation, 3 lives. NES SPEED on settings
screen selects frame rate of the console: DENDY (PAL, 50 fps, default) or NTSC (Japan / USA, 60 fps, everything
1/5 faster). All values are in `battlecity/config.py`.

## Bonuses

| Bonus | Player | Enemy picks it up |
|---|---|---|
| Grenade | destroys enemies on screen | new wave of enemies |
| Helmet | shield | players become invisible |
| Shovel | steel fortress walls | fortress walls disappear |
| Star | next superpower | enemies get 2 superpowers |
| Tank | extra life | enemies get more armor |
| Timer | freezes enemies | freezes players |
| Pistol | 3 superpowers | enemies become stronger tank types |
| Ship | drive over water | enemies drive over water |

Like on NES, a bullet appears on the edge of the tank and a tank can't fire again until its bullet finished flying
and exploding. Two differences from NES make head-on fights winnable: after a hit on a tank the slot is free a bit
earlier (5 NES frames), and player's bullets destroy enemy bullets and fly on (on NES bullets cancel each other).

Tanks collide like on NES: every tank marks map cells it occupies (not its top left cell), a moving tank checks only
two corner points of its front edge, so tanks slightly crossing each other's path don't stop. Walls are checked
the same way: a map cell (16 px) with any part of a wall blocks the tank, so a brick cell needs two shots.

Ice like on NES: a tank starting to move on ice slides 56 px, buttons are ignored during the first part of it,
the rest is slid after the button is released; sliding stops when the tank leaves ice.

Superpowers: 1 fast bullets, 2 two bullets, 3 bullets clear grass, 4 bullets destroy steel, 5 three bullets and
frontal armor, 6 bullets destroy walls and fly on, 9 castle protection (absorbs one hit).
CLASSIC (NES stars): 1 fast bullets, 2 two bullets, 3 bullets destroy steel and whole brick cells, grass stays.

Like on NES, a grey curtain closes before the "STAGE N" screen and opens over the new stage; while a player tank
moves its engine is heard, but only when neither stage start music nor enemy engine hum is playing (e.g. after
the last enemy is destroyed),
so it doesn't distract (the engine sound is the hum played faster, there is no separate sound file).

Like on NES, a bonus appears on one of 16 fixed places (not right under a player), tank explosions last 48 NES
frames (fast tank 24, player 32), scores screen pauses are counted in NES frames.

Extra life every 20000 points (CLASSIC: only once, like on NES). In 2+ player games the player who destroyed most
tanks on a stage gets 1000 points, if they have lives left.

## Enemies

| Enemy | Points | |
|---|---|---|
| Basic | 100 | |
| Fast | 200 | |
| Power | 300 | fast bullets |
| Armor | 400 | several hits |
| Stealth | 300 | almost invisible, shows itself when firing or hit (from stage 5) |
| Mortar | 400 | shells fly over walls (from stage 5) |
| Boss | 2000 | last enemy of every 5th stage, drops bonuses |

## Saved files

Saved in the game directory (or in `BATTLE_CITY_DATA_DIR` if set):

| File | |
|---|---|
| `.settings.json` | settings |
| `.savegame` | campaign progress |
| `.hiscore` | best score |
| `.hiscores.json` | hiscore tables with names |
| `custom_levels/` | levels made in editor |

## Mac app

```bash
./build_app.sh
```

Builds `dist/Battle City.app` with PyInstaller (`venv/bin/pip install pyinstaller` first), spec is `battle_city.spec`.
The app saves files to `~/Library/Application Support/Battle City` (or to `BATTLE_CITY_DATA_DIR` if set).

## Tests

```bash
venv/bin/python tests/run_all.py
```

Tests start the game with dummy video and audio drivers and fake input, every scenario in its own process.
Scenario processes run in parallel (all files share one pool); output is printed per file in a fixed order.
Worker count defaults to the number of CPUs and can be set with `BATTLE_CITY_TEST_WORKERS`, e.g. `BATTLE_CITY_TEST_WORKERS=1 venv/bin/python tests/run_all.py` runs sequentially.
One test file: `venv/bin/python tests/test_versus.py`, one scenario: `venv/bin/python tests/test_versus.py bonus`.

## Project structure

| Path | |
|---|---|
| `tanks.py` | entry point |
| `battlecity/config.py` | settings, difficulty presets, saved settings |
| `battlecity/state.py` | objects shared by modules: screen, players, enemies, castle, ... |
| `battlecity/game.py` | game loop, bonuses, spawning, drawing (Game class, other parts are mixins below) |
| `battlecity/menu.py` | main menu, intro screen, demo |
| `battlecity/settings.py` | settings screen |
| `battlecity/editor.py` | level editor |
| `battlecity/screens.py` | stage, scores, game over, versus result, hiscores screens, saved game |
| `battlecity/lang.py` | interface language (EN / RU) |
| `battlecity/tank.py` | player and enemy tanks |
| `battlecity/level.py` | level map |
| `battlecity/bullet.py`, `bonus.py`, `castle.py`, `effects.py`, `timer.py`, `gamepad.py` | other game objects |
| `levels/` | level maps: `.` empty, `#` brick, `@` steel, `~` water, `%` grass, `-` ice |
| `tests/` | automated tests |
