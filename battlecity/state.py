""" Battle City: objects shared by all modules, set when the game starts """

# Timer calling functions after interval
gtimer = None

# images
sprites = None
sprites2 = None

# game is drawn on this surface, then shown on display
screen = None

players = []
enemies = []
bullets = []
bonuses = []
labels = []

# name -> pygame.mixer.Sound
sounds = {}

game = None

# player's castle; castle of player 2 in versus mode
castle = None
castle2 = None

# index of last used enemy spawn position
enemy_spawn_pos_index = 0
