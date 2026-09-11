# coding=utf-8
""" Battle City: interface language (EN, RU)

Game font (prstart.ttf) has no Cyrillic letters: translated text with Cyrillic letters is drawn
with pygame default font, numbers and Latin text keep game font.
"""

import re
import pygame

from battlecity import config

LANGUAGES = ["EN", "RU"]

# whole texts
PHRASES = {
	"1 PLAYER": "1 ИГРОК",
	"2 PLAYERS": "2 ИГРОКА",
	"3 PLAYERS": "3 ИГРОКА",
	"CONTINUE": "ПРОДОЛЖИТЬ",
	"ENDLESS 1P": "БЕСКОНЕЧНО 1",
	"ENDLESS 2P": "БЕСКОНЕЧНО 2",
	"LEVEL EDITOR": "РЕДАКТОР",
	"RANDOM LEVELS": "СЛУЧАЙНЫЕ УРОВНИ",
	"LEVEL OF THE DAY": "УРОВЕНЬ ДНЯ",
	"G RANDOM": "G СЛУЧ",
	"FULL SCREEN": "ВО ВЕСЬ ЭКРАН",
	"START LEVEL": "ПЕРВЫЙ УРОВЕНЬ",
	"NES SPEED": "СКОРОСТЬ NES",
	"AUTO FIRE": "АВТОСТРЕЛЬБА",
	"ENEMY AI": "ИИ ВРАГОВ",
	"CRT FILTER": "ФИЛЬТР ЭКРАНА",
	"RESET CONTROLS": "СБРОС КНОПОК",
	"PAD FIRE": "ОГОНЬ ГЕЙМПАДА",
	"PAD START": "СТАРТ ГЕЙМПАДА",
	"PRESS KEY": "НАЖМИ КЛАВИШУ",
	"PRESS BTN": "НАЖМИ КНОПКУ",
	"NEW HIGH SCORE": "НОВЫЙ РЕКОРД",
	"ENTER YOUR NAME": "ВВЕДИ ИМЯ",
	"ENTER - DONE": "ENTER - ГОТОВО",
	"ENTER - MENU": "ENTER - МЕНЮ",
	"HIGH SCORES": "РЕКОРДЫ",
	"1-5 TILE": "1-5 ТАЙЛ",
	"SPC DRAW": "ПРОБЕЛ",
	"[ ] LVL": "[ ] УРОВ",
}

# single words of other texts (e.g. "STAGE 5", "P1 FIRE")
WORDS = {
	"SETTINGS": "НАСТРОЙКИ",
	"VERSUS": "ДУЭЛЬ",
	"DIFFICULTY": "СЛОЖНОСТЬ",
	"SOUND": "ЗВУК",
	"LANGUAGE": "ЯЗЫК",
	"BACK": "НАЗАД",
	"ON": "ВКЛ",
	"OFF": "ВЫКЛ",
	"AUTO": "АВТО",
	"ANY": "ЛЮБАЯ",
	"DEFAULT": "ОБЫЧНАЯ",
	"CLASSIC": "КЛАССИКА",
	"GOOD": "НОРМА",
	"EXTREME": "ЭКСТРИМ",
	"CUSTOM": "СВОЯ",
	"DENDY": "ДЕНДИ",
	"SMART": "УМНЫЙ",
	"SOFT": "МЯГКИЙ",
	"STRONG": "СИЛЬНЫЙ",
	"FIRE": "ОГОНЬ",
	"UP": "ВВЕРХ",
	"RIGHT": "ВПРАВО",
	"DOWN": "ВНИЗ",
	"LEFT": "ВЛЕВО",
	"GAMEPAD": "ГЕЙМПАД",
	"PAD": "ГЕЙМПАД",
	"BUTTON": "КНОПКА",
	"STAGE": "УРОВЕНЬ",
	"WAVE": "ВОЛНА",
	"PAUSE": "ПАУЗА",
	"GAME": "ИГРА",
	"OVER": "ОКОНЧЕНА",
	"HI-SCORE": "РЕКОРД",
	"HI-": "РЕКОРД",
	"I-PLAYER": "I-ИГРОК",
	"II-PLAYER": "II-ИГРОК",
	"III-PLAYER": "III-ИГРОК",
	"PLAYER": "ИГРОК",
	"BONUS": "БОНУС",
	"TOTAL": "ВСЕГО",
	"PTS": "ОЧК",
	"KILLS": "СБИТО",
	"WINS": "ПОБЕДИЛ",
	"CAMPAIGN": "КАМПАНИЯ",
	"ENDLESS": "БЕСКОНЕЧНО",
	"RANDOM": "СЛУЧАЙНЫЕ",
	"-": "-",
	"EDITOR": "РЕДАКТОР",
	"LVL": "УР",
	"ERASE": "ЛАСТИК",
	"BRICK": "КИРПИЧ",
	"STEEL": "СТАЛЬ",
	"WATER": "ВОДА",
	"GRASS": "ТРАВА",
	"ICE": "ЛЁД",
	"SAVE": "СОХР",
	"RESET": "СБРОС",
	"TEST": "ИГРАТЬ",
	"MENU": "МЕНЮ",
}

# pygame default font size giving letters as high as game font of this size
DEFAULT_FONT_SCALE = 1.5

fonts = {}

def tr(text):
	""" Text in current language """
	if config.LANGUAGE != "RU":
		return text
	if text in PHRASES:
		return PHRASES[text]
	return "".join([WORDS.get(part, part) for part in re.split(r"(\s+)", text)])

def render(font, size, text, antialias, color, translate = True):
	""" Render text in current language
	font: game font of this size; translate False - draw text as is (names, key names)
	"""
	if translate:
		text = tr(text)
	if any([ord(char) > 127 for char in text]):
		default_size = int(size * DEFAULT_FONT_SCALE)
		if default_size not in fonts:
			fonts[default_size] = pygame.font.Font(None, default_size)
		font = fonts[default_size]
	return font.render(text, antialias, color)
