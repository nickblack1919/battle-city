# coding=utf-8
""" Battle City: CRT (old TV) filter applied to the display picture

Overlays are rendered once per mode and display size, every frame only blits them:
- STRONG: dimmed copy of the picture shifted 1 px right is added (light horizontal bloom, brighter picture)
- multiply overlay: scanlines (second row of every NES pixel darker), faint RGB aperture stripes,
  vignette with rounded dark corners
Game screen (state.screen) is never changed, only the display surface.
"""

import pygame

MODES = ["OFF", "SOFT", "STRONG"]

# mode: (scanline row brightness, vignette edge darkening 0-1, corner radius px, bloom brightness 0-255)
PARAMS = {
	"SOFT": (205, 0.28, 18, 0),
	"STRONG": (150, 0.45, 26, 70),
}

class CRTFilter():

	def __init__(self):
		self.key = None
		self.overlay = None
		self.bloom = None

	def vignette(self, size, strength, radius):
		""" Multiply surface: 255 in the center, darker to edges, black rounded corners """
		width, height = size
		# small image computed per pixel, smoothly scaled up
		sw, sh = max(8, width // 8), max(8, height // 8)
		small = pygame.Surface((sw, sh))
		r = radius / 8.0
		for y in range(sh):
			ny = (y + 0.5) / sh * 2 - 1
			for x in range(sw):
				nx = (x + 0.5) / sw * 2 - 1
				# darkening grows near edges
				value = 1.0 - strength * (nx ** 4 + ny ** 4) ** 0.75
				# rounded corners: outside of corner circle is black
				cx = min(x + 0.5, sw - x - 0.5)
				cy = min(y + 0.5, sh - y - 0.5)
				if cx < r and cy < r:
					distance = ((r - cx) ** 2 + (r - cy) ** 2) ** 0.5
					if distance > r:
						value *= max(0.0, 1.0 - (distance - r) * 1.5)
				value = int(max(0, min(255, value * 255)))
				small.set_at((x, y), (value, value, value))
		return pygame.transform.smoothscale(small, size)

	def build(self, mode, size):
		scanline, strength, radius, bloom = PARAMS[mode]
		width, height = size

		# scanlines and aperture: pattern repeats every 2 rows and 3 columns
		lines = pygame.Surface(size)
		lines.fill((255, 255, 255))
		for y in range(1, height, 2):
			lines.fill((scanline, scanline, scanline), (0, y, width, 1))
		tints = [(255, 244, 244), (244, 255, 244), (244, 244, 255)]
		stripes = pygame.Surface(size)
		for x in range(width):
			stripes.fill(tints[x % 3], (x, 0, 1, height))
		lines.blit(stripes, (0, 0), special_flags = pygame.BLEND_RGB_MULT)

		overlay = self.vignette(size, strength, radius)
		overlay.blit(lines, (0, 0), special_flags = pygame.BLEND_RGB_MULT)
		self.overlay = overlay.convert() if pygame.display.get_surface() else overlay
		self.bloom = None
		self.bloom_level = bloom
		if bloom:
			self.bloom = pygame.Surface(size).convert() if pygame.display.get_surface() else pygame.Surface(size)

	def apply(self, display, screen, offset, mode):
		""" Draw filter over display on which screen was just blitted at offset """
		if mode not in PARAMS:
			return
		size = display.get_size()
		if self.key != (mode, size):
			self.key = (mode, size)
			self.build(mode, size)
		if self.bloom:
			self.bloom.blit(screen, (0, 0))
			level = self.bloom_level
			self.bloom.fill((level, level, level), special_flags = pygame.BLEND_RGB_MULT)
			display.blit(self.bloom, (offset[0] + 1, offset[1]), special_flags = pygame.BLEND_RGB_ADD)
		display.blit(self.overlay, (0, 0), special_flags = pygame.BLEND_RGB_MULT)
