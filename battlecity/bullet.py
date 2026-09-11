# coding=utf-8
""" Battle City: bullets """

import os, random, uuid, sys, json
import pygame
from pygame.locals import *

from battlecity import config, state
from battlecity.effects import Explosion, Label

class Bullet():
	# direction constants
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)

	# bullet's stated
	(STATE_REMOVED, STATE_ACTIVE, STATE_EXPLODING) = range(3)

	(OWNER_PLAYER, OWNER_ENEMY) = range(2)

	def __init__(self, level, position, direction, damage = 100, speed = config.DEFAULT_BULLET_SPEED, power = 1):


		self.level = level
		self.direction = direction
		self.damage = damage
		self.owner = None
		self.owner_class = None

		# mortar shells fly over walls
		self.over_walls = False

		# 1-regular everyday normal bullet
		# 2-can destroy steel
		self.power = power

		self.image = state.sprites.subsurface(75*2, 74*2, 3*2, 4*2)

		# position is tank's top left corner. Like on NES, bullet's center appears
		# on the edge of the tank (8 NES px = 16 px from tank's center). Also rotate image.
		if direction == self.DIR_UP:
			self.rect = pygame.Rect(position[0] + 12, position[1] - 4, 8, 8)
		elif direction == self.DIR_RIGHT:
			self.image = pygame.transform.rotate(self.image, 270)
			self.rect = pygame.Rect(position[0] + 32 - 4, position[1] + 12, 8, 8)
		elif direction == self.DIR_DOWN:
			self.image = pygame.transform.rotate(self.image, 180)
			self.rect = pygame.Rect(position[0] + 12, position[1] + 32 - 4, 8, 8)
		elif direction == self.DIR_LEFT:
			self.image = pygame.transform.rotate(self.image, 90)
			self.rect = pygame.Rect(position[0] - 4, position[1] + 12, 8, 8)

		self.explosion_images = [
			state.sprites.subsurface(0, 80*2, 32*2, 32*2),
			state.sprites.subsurface(32*2, 80*2, 32*2, 32*2),
		]

		self.speed = speed

		# fractional part of movement (speed can be fractional, bullet moves by whole px)
		self.move_credit = 0.0

		# tank can't fire again while its bullet flies or its slot is busy during explosion
		self.slot_busy = True

		self.state = self.STATE_ACTIVE

		self.dbg_label = Label(self.rect.bottomleft, str(self.rect.topleft))


	def draw(self):
		""" draw bullet """
		if self.state == self.STATE_ACTIVE:
			state.screen.blit(self.image, self.rect.topleft)
		elif self.state == self.STATE_EXPLODING:
			self.explosion.draw()

		# debug sprites
		if config.DEBUG_SPRITES:
			red = (255,0,0)
			pygame.draw.rect(state.screen, red, self.rect, 1)
			self.dbg_label.position = self.rect.bottomleft
			self.dbg_label.text = str(self.rect.topleft) + " " + str(self.rect.size)
			self.dbg_label.draw()

	def update(self):

		if self.state == self.STATE_EXPLODING:
			if not self.explosion.active:
				self.destroy()
				del self.explosion

		if self.state != self.STATE_ACTIVE:
			return

		# speed can be fractional: move whole px, keep the rest for next frame.
		# Fast bullet moves in parts not longer than 4 px, so it doesn't fly through thin walls
		self.move_credit += self.speed
		# small epsilon: 4.8 * 10 is 47.999... in floating point
		px = int(self.move_credit + 1e-9)
		self.move_credit -= px
		while px > 0 and self.state == self.STATE_ACTIVE:
			part = min(px, 4)
			px -= part
			self.step(part)

	def step(self, px):
		""" Move bullet by px and handle collisions """
		# area passed during this step: bullets meeting each other must not jump over each other
		previous_rect = self.rect.copy()
		if self.direction == self.DIR_UP:
			self.rect.topleft = [self.rect.left, self.rect.top - px]
			if self.rect.top < 0:
				if config.play_sounds and self.owner == self.OWNER_PLAYER:
					state.sounds["steel"].play()
				self.explode()
				return
		elif self.direction == self.DIR_RIGHT:
			self.rect.topleft = [self.rect.left + px, self.rect.top]
			if self.rect.left > (416 - self.rect.width):
				if config.play_sounds and self.owner == self.OWNER_PLAYER:
					state.sounds["steel"].play()
				self.explode()
				return
		elif self.direction == self.DIR_DOWN:
			self.rect.topleft = [self.rect.left, self.rect.top + px]
			if self.rect.top > (416 - self.rect.height):
				if config.play_sounds and self.owner == self.OWNER_PLAYER:
					state.sounds["steel"].play()
				self.explode()
				return
		elif self.direction == self.DIR_LEFT:
			self.rect.topleft = [self.rect.left - px, self.rect.top]
			if self.rect.left < 0:
				if config.play_sounds and self.owner == self.OWNER_PLAYER:
					state.sounds["steel"].play()
				self.explode()
				return

		has_collided = False
		
		# check for removable tiles
		# if bullet is powerfull enough it can clear those tiles
		# NES stars don't clear grass
		if self.power >= 2 and not (config.NES_STARS and self.owner == self.OWNER_PLAYER):

			rects = self.level.removable_rects
			removable = self.rect.collidelistall(rects)
			if removable != []:
				for i in removable:
					for tile in self.level.mapr:
						if tile.topleft == rects[i].topleft:
							if config.play_sounds:
								state.sounds["brick"].play()
							self.level.mapr.remove(tile)
							break

		# check for collisions with walls. one bullet can destroy several (1 or 2)
		# tiles but explosion remains 1
		rects = self.level.obstacle_rects
		collisions = [] if self.over_walls else self.nearestCollisions(rects, self.rect.collidelistall(rects))
		if collisions != []:
			# castle rect has no tile type
			hit_bricks = [rects[i] for i in collisions if getattr(rects[i], "type", None) == self.level.TILE_BRICK]
			for i in collisions:
				if self.level.hitTile(rects[i].topleft, self.power, self.owner == self.OWNER_PLAYER):
					has_collided = True
			if hit_bricks:
				self.destroyBrickStrip(hit_bricks[0])
		if has_collided:
			self.explode()
			return

		# check for collisions with other bullets
		for bullet in state.bullets:
			if self.state == self.STATE_ACTIVE and bullet.owner != self.owner and bullet != self and bullet.state != bullet.STATE_REMOVED and previous_rect.union(self.rect).colliderect(bullet.rect):
				# player's bullet destroys enemy's bullet and flies on (PLAYER_BULLETS_PRIORITY)
				if config.PLAYER_BULLETS_PRIORITY and self.owner == self.OWNER_PLAYER:
					bullet.destroy()
					continue
				# bullets cancel each other without explosion
				self.destroy()
				if config.PLAYER_BULLETS_PRIORITY and bullet.owner == self.OWNER_PLAYER:
					return
				bullet.destroy()
				return

		# check for collisions with players
		for player in state.players:
			# bullet starts inside its own tank: own tank is never hit
			if player is self.owner_class:
				continue
			if player.state == player.STATE_ALIVE and self.rect.colliderect(player.rect):
				# versus: other player's bullet is hostile
				friendly_fire = self.owner == self.OWNER_PLAYER and (state.game.mode != "versus" or self.owner_class is player)
				absorbed_by_helmet = player.shielded
				if player.bulletImpact(friendly_fire, self.damage, self.owner_class, self.direction):
					# NES: bullet explodes on a tank (its slot stays busy), vanishes on helmet
					if absorbed_by_helmet:
						self.destroy()
					else:
						self.explode(config.BULLET_TANK_HIT_SLOT_TIME)
					return

		# check for collisions with enemies
		for enemy in state.enemies:
			if enemy.state == enemy.STATE_ALIVE and self.rect.colliderect(enemy.rect):
				if enemy.bulletImpact(self.owner == self.OWNER_ENEMY, self.damage, self.owner_class, self.direction):
					# bullet explodes on a tank, tank can fire again a bit before explosion ends
					self.explode(config.BULLET_TANK_HIT_SLOT_TIME)
					return

		# protected castle: protection absorbs the hit, enemy shooter explodes,
		# fortress walls temporarily become steel
		if state.castle.active and state.castle.protected and self.rect.colliderect(state.castle.rect):
			state.castle.protected = False
			self.destroy()
			if self.owner == self.OWNER_ENEMY and self.owner_class.state == self.owner_class.STATE_ALIVE:
				self.owner_class.explode()
			state.game.level.buildFortress(state.game.level.TILE_STEEL)
			state.game.startSteelFortressTimer()
			return

		# check for collision with castles (versus mode has two)
		for target in state.game.castles():
			if target.active and self.rect.colliderect(target.rect):
				target.destroy()
				self.explode()
				return

	def destroyBrickStrip(self, tile):
		""" Destroy bricks in the hit row as wide as a tank (centered on the bullet),
		so a tank driving straight and firing always clears its way.
		NES 3rd star: whole brick tiles (16 px deep) """
		whole = config.NES_STARS and self.owner == self.OWNER_PLAYER and self.power >= 3
		if self.direction in (self.DIR_UP, self.DIR_DOWN):
			if whole:
				strip = pygame.Rect(self.rect.centerx - 16, tile.top // 16 * 16, 32, 16)
			else:
				strip = pygame.Rect(self.rect.centerx - 16, tile.top, 32, tile.height)
		else:
			if whole:
				strip = pygame.Rect(tile.left // 16 * 16, self.rect.centery - 16, 16, 32)
			else:
				strip = pygame.Rect(tile.left, self.rect.centery - 16, tile.width, 32)

		bricks = [brick for brick in self.level.mapr if brick.type == self.level.TILE_BRICK and brick.colliderect(strip)]
		for brick in bricks:
			self.level.mapr.remove(brick)
		if bricks:
			self.level.updateObstacleRects()

	def nearestCollisions(self, rects, collisions):
		""" Keep only tiles in the row (column) nearest to the bullet
		Fast bullet can overlap two rows of brick quarters, but should destroy only one
		"""
		if len(collisions) < 2:
			return collisions

		if self.direction == self.DIR_UP:
			key, best = (lambda rect: rect.bottom), max
		elif self.direction == self.DIR_DOWN:
			key, best = (lambda rect: rect.top), min
		elif self.direction == self.DIR_LEFT:
			key, best = (lambda rect: rect.right), max
		else:
			key, best = (lambda rect: rect.left), min

		nearest = best([key(rects[i]) for i in collisions])
		return [i for i in collisions if key(rects[i]) == nearest]

	def releaseSlot(self):
		self.slot_busy = False

	def explode(self, slot_time = None):
		""" start bullets's explosion
		slot_time: ms after which tank may fire again, None - when explosion ends
		"""
		if self.state != self.STATE_REMOVED:
			if slot_time != None:
				state.gtimer.add(slot_time, lambda :self.releaseSlot(), 1)
			self.state = self.STATE_EXPLODING
			# NES: explosion lasts 9 frames (2 images)
			interval = config.BULLET_EXPLOSION_TIME // len(self.explosion_images)
			self.explosion = Explosion([self.rect.left-16, self.rect.top-16], interval, self.explosion_images)

	def destroy(self):
		self.state = self.STATE_REMOVED
