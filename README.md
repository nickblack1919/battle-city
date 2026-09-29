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
then to players 1 and 2 (can be changed on the settings screen); gamepad Start pauses the game, Select borrows a life.

| Key | Action |
|---|---|
| Enter | pause |
| Ctrl+F / Cmd+F / Alt+Enter | full screen / window |
| M | sound on / off |
| B / gamepad Select | borrow a life from a partner for a player without lives (the computer partner never gets a human's life; Select asks for the player holding that gamepad) |
| ESC | in game: exit to main menu (asks Y / N), in editor and settings: back to menu, in menu: quit |
| both players' movement keys / arrows / gamepad d-pad / gamepad A and B | on the first "STAGE N" screen of a new game: choose the stage (up, right, A - next, down, left, B - previous; campaign and random levels), Enter / Space / gamepad Start begins it |
| P | freeze enemies (debug, only with `DEBUG_KEYS = True` in config) |
| V | debug sprites and grid (debug, only with `DEBUG_KEYS = True` in config) |

## Game modes

- **1 / 2 / 3 PLAYERS** - campaign: 35 stages (30 with the NEW LEVELS setting), scores screen after every stage.
  Progress is saved after each stage. Four settings change what these items start: WAVES (endless waves instead of the
  campaign), BOT (the computer plays one more tank), RANDOM LEVELS (every stage generated on the fly) and NEW LEVELS
  (30 new maps).
- **BOT setting, one player** - campaign with a computer partner playing player 2 (shown as BOT). It drives with the same speed
  and bullets as a human: finds the best place to shoot enemies from (enemies near the castle first, defends the castle),
  fires only when neither the castle, fortress walls nor the human are in its line of fire, dodges enemy bullets, steps out
  of enemy lines of fire while its bullet isn't ready, picks up near bonuses the human isn't closer to and drives out of
  the human's way. P2 keys and gamepads don't control it; its score doesn't go to hiscores; saved game remembers it.
- **BOT setting, two players** - two humans and a computer helper playing the third tank (blue, so it isn't taken for player 2:
  `BOT_COLOR_ORDER` swaps green and blue channels of its sprites, its lives in the sidebar are blue too), which guards the castle:
  it holds one of three posts in front of it (center or the flank farther from the players: `BOT_GUARD_POST_ROW`,
  `BOT_GUARD_POST_SIDE`, `BOT_GUARD_POST_STICKINESS`), keeps its place within `BOT_GUARD_RADIUS` cells of that post and
  never goes further than `BOT_GUARD_MAX_AWAY` from it, shoots enemies faster than the partner bot
  (`BOT_GUARD_REACTION_FRAMES`, `BOT_GUARD_FIRE_INTERVAL`) taking the ones near the castle first
  (`BOT_GUARD_DEFEND_DISTANCE`), keeps away from the players (`BOT_GUARD_HUMAN_COST`, `BOT_GUARD_HUMAN_NEAR_COST`),
  and saves the castle at the cost of
  its life - when an enemy bullet flies at the castle it shoots the bullet down or drives into it and doesn't dodge
  (`BOT_GUARD_SHIELD`), but only when the bullet reaches the castle within `BOT_GUARD_SHIELD_FRAMES` frames - a bullet
  still far away can be shot down later instead. Otherwise it takes care of itself better than the partner bot:
  it starts with `BOT_LIVES` lives (5 instead of the players' 3), leaves every bonus to the players (it neither goes
  for one nor picks one up while driving over it: `BOT_GUARD_BONUSES`), dodges every bullet flying at it and reacts faster (`BOT_GUARD_DODGE_CHANCE`, `BOT_GUARD_DODGE_REACTION_FRAMES`),
  steps out of enemy lines of fire more often (`BOT_GUARD_JUKE_CHANCE`) and keeps its distance from enemy tanks
  (`BOT_GUARD_ENEMY_COST`, `BOT_GUARD_ENEMY_NEAR_COST`). Bullets between a player and the computer partner never hurt in
  either direction - it doesn't fire when a player is in its line of fire, a bullet that still reaches a partner vanishes
  without damage or stun, and our bullets don't stop the partner either (`BOT_NO_FRIENDLY_FIRE`).
- **CONTINUE** - continue saved campaign (shown when there is a saved game).
- **WAVES setting** - the player items start waves of enemies until game over instead of the campaign: every wave is
  harder, there is no scores screen between them, maps repeat from the beginning of the set. Waves have their own
  hiscore tables.
- **NEW LEVELS setting** - 30 new maps (`levels/new`) instead of the 35 original ones, made by the level generator from
  fixed seeds (`tools/make_levels.py`, run it to build them again). They have their own hiscore tables, their own
  custom levels in the editor, and a saved game remembers which set it was played on.
- **RANDOM LEVELS setting** - every stage is a map generated on the fly, and these maps are never symmetric
  (`generateLevel(seed, stage, "none")`), unlike the original levels: later stages get denser maps with more steel and
  water, enemies come from the stage tables. Every game gets a new seed which is saved with the game, so CONTINUE gives
  the same maps. Generated games have their own hiscore tables.
- **LEVEL OF THE DAY** - hidden: the menu item appears only with `"daily": true` in the settings file
  (`SHOW_DAILY_LEVEL`). 1 player, one generated stage, the same for everyone on this date (seed from the local
  date, stage difficulty 5-30 from the seed). After the stage or game over: scores, hiscore table of the day, menu.
  Every date and difficulty preset has its own hiscore table.
- **VERSUS** - two players fight each other, each defends own castle; destroyed castle or no lives left loses.
- **LEVEL EDITOR** - edit any level of the chosen set (35 original or 30 new ones): arrows / mouse move cursor, 1-5 tile, 0 eraser, space / left mouse draw,
  right mouse erase, `[` `]` level, G fill with generated map, S save, D back to original level, T save and play.
- **SETTINGS** - difficulty preset, sound, full screen, start level, waves, bot, random levels, new levels, controls, NES speed (NTSC / DENDY),
  auto fire (ON by default - holding fire button shoots again when bullet slot is free, with the timing of the
  Dendy turbo button: about 12 presses per second; OFF - every shot needs
  a press, like on NES), enemy AI (CLASSIC - random paths, sometimes towards the castle; NES - like on NES: at
  stage start enemies drive in random directions, later chase players, then go to the castle; a blocked tank
  waits or turns; SMART - chooses the best place to shoot from (short way, few bricks between, from a side the player isn't
  looking at, not next to other enemies), keeps it instead of driving back and forth, shoots through bricks from
  there; dodges player's bullets with sharp turns, steps out of the player's line of fire while its own bullet
  isn't ready, sometimes turns aside to be hard to predict; attacks the castle if the player can't be reached.
  SMART enemies act as a team: they know which cells players can shoot now or soon (clear lines from every
  player, stronger where he looks, and paths of flying bullets) and come through cover. First they gather:
  hide out of the player's lines of fire 4-10 cells from him (grass and places behind walls first, spread
  apart) and wait facing a lane the player may drive into - a player who drives into it gets an ambush shot.
  They attack together when 3 tanks are ready, or at a good moment: the player is stunned or frozen, his
  bullets are busy next to a waiting tank, or he turned away from them; after 9 seconds of waiting they attack
  anyway. In an attack every tank gets its side around the player (not his front; only a tough tank takes
  the front to draw fire), one tank of a big attack goes for the castle; fast tanks hunt: they take places
  ahead of a moving player or behind him. An attack that lost half of its tanks or lasted 15 seconds ends
  with regroup in new hiding spots. One tank rushes the castle while the player is far from it; without
  players all enemies attack the castle. Bullets behind walls aren't dodged, dodges go out of lines of fire), gamepads: which gamepad every player uses (AUTO, OFF or gamepad number) and gamepad fire /
  start / select buttons (Enter, then press the gamepad button; left arrow - default buttons), language (EN / RU; Russian
  text uses pygame default font, the game font has no Cyrillic letters), CRT filter (OFF / SOFT / STRONG - old TV
  look: scanlines, darker edges and rounded corners, STRONG adds light horizontal glow; the game picture itself is not changed).
- **DEMO** - after 20 seconds in the menu without input the computer plays a 2 player game; any key returns to menu.

Campaign, endless, random levels and level of the day have hiscore tables for every difficulty preset: players with top 10 score enter their names after game over.

Generated maps look like original ones: structures of 2x2 cell blocks (tanks fit between them), usually left-right
mirror symmetry (sometimes 4-way or none), brick walls, steel, water, grass and ice. Every map is checked with
a search over tank positions: enemy spawns reach the castle and player starts reach every enemy spawn without
crossing steel or water (bricks can be shot), places no tank can reach are filled; a failed map is generated
again, so the map depends only on seed and stage.

## Difficulty presets

| Preset | |
|---|---|
| NES | everything like in the original: 4 enemies on screen (6 in 2 player game), armor tank 4 hits, bonus carried by 4th / 11th / 18th tank, NES bonus set, bonus lies until it is picked up or a new bonus tank appears, enemies don't pick up bonuses, friendly fire stuns partner, one extra life, NES spawn intervals, no new enemy types, NES star ladder (no armor from stars), and it also switches enemy AI to NES, auto fire off and turn assist off |
| NES+ | NES rules with our additions: all bonuses (pistol and ship too), new enemy types (stealth, mortar, boss), frontal armor at 5 superpowers, armor from 3rd and 6th superpower, enemies pick up bonuses, bonus disappears after a while |
| GOOD (default) | more enemies on screen, shorter spawn intervals, armor tank 6 hits, no friendly fire, extra life every 20000 points |
| EXTREME | even more enemies in 2-3 player games |

Switching the difficulty also sets enemy AI, auto fire and turn assist: NES turns them to the original behaviour,
the other presets set them back to the normal ones. The old preset name CLASSIC is loaded as NES+ (saved settings
and hiscore tables keep their scores).

In every preset timings are taken from NES version (disassembly, counted in NES frames): tank and bullet speeds,
shield, helmet, shovel and clock durations, enemy fire rate, spawn animation, 3 lives. NES SPEED on settings
screen selects frame rate of the console: NTSC (Japan / USA, 60 fps, default - like the original NES) or DENDY
(PAL, Famicom clones, 50 fps, everything 1/5 slower). All values are in `battlecity/config.py`.

Speeds are counted per frame like on NES (player 1 NES px on 3 of 4 frames, basic / power / armor enemies every
other frame, fast enemy every frame, bullet 2 px, fast bullet 4 px), and one game frame is one NES frame: the game
runs at the frame rate of the chosen console (60 or 50 fps) and `battlecity/frameclock.py` keeps an exact frame
schedule (pygame's `Clock.tick()` oversleeps on macOS and made everything slower than on the console).

The ship bonus lasts until the player loses a life and stays with him on the next stages and in a saved game
(`BONUS_SHIP_TIMEOUT` sets a time limit in ms instead, `BONUS_SHIP_ENEMIES_TIMEOUT` is the time enemies keep it).

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
and exploding, also after a hit on a tank. Bullets flying into each other cancel each other, so nobody wins a
head-on duel (`PLAYER_BULLETS_PRIORITY = True` in config gives player's bullets priority instead).

Tanks collide like on NES: every tank marks map cells it occupies (not its top left cell), a moving tank checks only
two corner points of its front edge, so tanks slightly crossing each other's path don't stop; a tank in its spawn
animation marks its cells too (`SPAWNING_TANKS_BLOCK`), an exploding one doesn't. Walls are checked by map cells
under the front edge: a cell (16 px) with any part of a wall blocks the tank, so a brick cell needs two shots.

More NES details: the D-pad is read as right, left, down, up (that direction wins when two are held); turning back
doesn't put the tank on the grid, a 90 degrees turn does; ice is taken from the one cell the tank marks; normal
enemies move 2 px on every other frame (fast ones every frame), even and odd tanks on alternating frames; enemy
spawn points are used in turn even if a tank stands there; bullets of two players cancel each other too.

Turning into a narrow passage is easy (helpful with a gamepad): a turning tank is put on the grid line from which
the passage is open, and a tank between cells slides sideways to it instead of getting stuck on the wall next to
the gap (`PLAYER_TURN_ASSIST` in config). The correction works only for a passage as wide as the tank (walls or
the field edge on both sides of it): turning on open ground or along a single wall never moves the tank, it is
put on the nearest grid line like on NES.

Ice like on NES: a tank starting to move on ice slides 56 px, buttons are ignored during the first part of it,
the rest is slid after the button is released; sliding stops when the tank leaves ice.

Superpowers: 1 fast bullets, 2 two bullets, 3 bullets clear grass and armor (player's tank takes one hit
more, and one more from 6 - `PLAYER_ARMOR_SUPERPOWERS` in config; a new star repairs it, armor is shown as a
light frame around the tank, white for the double one), 4 bullets destroy steel, 5 three bullets and frontal
armor, 6 bullets destroy walls and fly on, 9 castle protection (absorbs one hit).
The same ladder works for players and enemies (an enemy picking up a star gives 2 superpowers to all enemies on
screen). `NES_STARS = True` in config gives players the NES ladder instead: 1 fast bullets, 2 two bullets,
3 bullets destroy steel and whole brick cells, grass stays, more stars do nothing.

Like on NES, a destroyed tank explodes and then shows its points in the same place (18 and 6 steps of the tank's
own speed: 36 + 12 frames for a normal enemy, 18 + 6 for a fast one); the three explosion pictures are shown
equally long.

Like on NES, the game over music starts on the "GAME OVER" screen and the screen stays until the music ends
(any key or gamepad button skips it).

Like on NES, a grey curtain closes before the "STAGE N" screen and opens over the new stage; while a player tank
moves its engine is heard, but only when neither stage start music nor enemy engine hum is playing (e.g. after
the last enemy is destroyed),
so it doesn't distract (the engine sound is the hum played faster, there is no separate sound file).

A bonus blinks all the time it lies on the field (like on NES) and disappears after `BONUS_SPAWN_TIMEOUT` or,
like on NES, when a new bonus tank appears. A player hit by
partner's bullet blinks while stunned, like on NES. The bonus for most tanks destroyed is written under that
player's column on the scores screen with a sound, like on NES.

NES sound effects are synthesized from the game's disassembly (APU pulse channel, no ROM samples) and can be
regenerated with `venv/bin/python tools/nes_sfx.py bonus1000 sounds/bonus1000.wav` (add `--pal` for the DENDY
version: the game plays the one matching NES SPEED).

Like on NES, a bonus appears on one of 16 fixed places (not right under a player), tank explosions last 48 NES
frames (fast tank 24, player 32), scores screen pauses are counted in NES frames.

Extra life every 20000 points (NES and NES+: only once, like on NES). In 2+ player games the player who destroyed most
tanks on a stage gets 1000 points, if they have lives left: dark red "BONUS!" (like on NES) and white points under his
column, in the lowest free row. The computer helper takes no part in it and has no line on the scores screen at all:
its score is counted nowhere. A third human player gets one line in the lowest row: name, score and how many tanks he
destroyed.

## Enemies

| Enemy | Points | |
|---|---|---|
| Basic | 100 | |
| Fast | 200 | |
| Power | 300 | fast bullets |
| Armor | 400 | several hits |
| Stealth | 300 | invisible, only a faint shadow is seen: shows itself for 1 s every 6 s (`STEALTH_SHOW_TIME`, `STEALTH_HIDE_TIME`), and when firing or hit (from stage 5) |
| Mortar | 400 | shells fly over walls (from stage 5); never appears at the middle spawn place above the castle (`MORTAR_CENTER_SPAWN`) |
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
| `battlecity/levelgen.py` | level generator, level of the day seed |
| `battlecity/bullet.py`, `bonus.py`, `castle.py`, `effects.py`, `timer.py`, `gamepad.py` | other game objects |
| `levels/` | level maps: `.` empty, `#` brick, `@` steel, `~` water, `%` grass, `-` ice |
| `levels/new/` | 30 new maps of the NEW LEVELS setting (`tools/make_levels.py`) |
| `tests/` | automated tests |
