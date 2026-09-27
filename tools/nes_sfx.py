""" NES sound effects, synthesized from the Battle City disassembly.

No ROM and no sampled audio: the NES APU pulse channel and the game's little
sound engine are reimplemented here, and the effect data is copied from the
disassembly (cyneprepou4uk/NES-Games-Disassembly, "Battle City", bank_FF.asm).

How the game's sound engine works (addresses are PRG file offsets / CPU addresses):

  sub_EA7E_sound_driver (0x002A8E, 00:EA7E) runs once per frame. Effect data
  starts with 4 header bytes: the channel selector and the three register values
  written to $4000 + channel * 4 (duty/volume, sweep, and the $4003-style byte
  with the length counter index). Channel = first byte - 1, so 02 means the
  second pulse channel ($4004-$4007).

  After the header the interpreter at loc_EB88 (0x002B98, 00:EB88) reads bytes:
    $00-$5F  a note: bit 3-7 index the period table tbl_ECE6 (0x002CF6, 00:ECE6),
             bits 0-2 are a shift count, period = table[index] >> shift
             (00:EB9E-EBD6 does exactly this: AND #$F8, LSR, LSR to index the
             table of 16-bit periods, then AND #$07 LSR/ROR to divide by 2^shift).
             The period is written to the channel's $4002/$4003 halves and the
             channel registers are rewritten, which restarts the envelope.
    $60      hold: keep the current note for one more duration
    $61-$E7  set the duration of the following notes to byte - $60 frames
             (stored in con_se_index_06, counted down at 00:EB42)
    $E8      con_se_cb_stop (ofs_005_EC0A, 0x002C1A): end of effect; the driver
             then writes a silencing value to the channel (00:EAF8 loop)
    $EF-$F2  loop counters, $F9 main loop - not used by this effect

The APU pulse channel: period P gives frequency CPU / (16 * (P + 1)); the
envelope counts down from 15 with one step every (period + 1) quarter frames
(240 Hz), and it restarts on every write of the $4003/$4007 register.

Usage: venv/bin/python tools/nes_sfx.py bonus1000 sounds/bonus1000.wav
"""

import sys, os, math, wave, array

# NTSC NES (the original console); the remake itself runs the game logic at PAL 50 fps,
# but the effect was composed for the NTSC ROM, so it is rendered at 60 Hz.
CPU_HZ = 1789773.0
FRAME_HZ = 60.0
QUARTER_FRAME_HZ = 240.0
SAMPLE_RATE = 44100

# tbl_ECE6 (0x002CF6, 00:ECE6): one chromatic octave of pulse periods, high byte first
PERIOD_TABLE = [0x07F2, 0x0780, 0x0714, 0x06AE, 0x0643, 0x05F4,
	0x059E, 0x054E, 0x0502, 0x04BA, 0x0476, 0x0436]

# _off000_sfx_EE3A_1B_bonus_1000 (0x002E4A, 00:EE3A..00:EE47), ram_sfx_bonus_1000 = $031B
SFX = {
	"bonus1000": [0x02, 0x82, 0x7F, 0x40, 0x63, 0x53, 0x1B, 0x1C, 0x3B, 0x3C, 0x53, 0x6A, 0x54, 0xE8],
}

DUTY_CYCLES = [0.125, 0.25, 0.5, 0.75]


class Note(object):
	def __init__(self, period, frames, duty, volume, envelope_period, constant_volume):
		self.period = period
		self.frames = frames
		self.duty = duty
		self.volume = volume
		self.envelope_period = envelope_period
		self.constant_volume = constant_volume

	def frequency(self):
		return CPU_HZ / (16.0 * (self.period + 1))

	def seconds(self):
		return self.frames / FRAME_HZ


def parseSfx(data):
	""" Run the game's sound engine over the effect data and return the list of notes """
	channel = data[0] - 1
	duty_volume = data[1]
	duty = DUTY_CYCLES[duty_volume >> 6]
	constant_volume = bool(duty_volume & 0x10)
	# with constant volume the low nibble is the volume, otherwise it is the envelope period
	volume = (duty_volume & 0x0F) if constant_volume else 15
	envelope_period = duty_volume & 0x0F

	if channel not in (0, 1):
		raise ValueError("only the pulse channels are implemented (channel %d)" % channel)

	notes = []
	duration = 1
	pos = 4
	while pos < len(data):
		byte = data[pos]
		pos += 1
		if byte == 0xE8:  # con_se_cb_stop
			break
		if byte == 0x60:  # hold the previous note
			if notes:
				notes[-1].frames += duration
			continue
		if byte > 0x60:  # set duration in frames
			if byte > 0xE7:
				raise ValueError("control byte $%02X is not implemented" % byte)
			duration = byte - 0x60
			continue
		period = PERIOD_TABLE[byte >> 3] >> (byte & 0x07)
		notes.append(Note(period, duration, duty, volume, envelope_period, constant_volume))
	return notes


def renderPulse(notes, amplitude=0.6):
	""" Render notes of one pulse channel to a list of floats in [-1, 1] """
	samples = []
	for note in notes:
		count = int(round(SAMPLE_RATE * note.seconds()))
		freq = note.frequency()
		phase = 0.0
		step = freq / SAMPLE_RATE
		for i in range(count):
			if note.constant_volume:
				level = note.volume
			else:
				# envelope decay: 15 down to 0, one step per (period + 1) quarter frames
				step_len = (note.envelope_period + 1) / QUARTER_FRAME_HZ
				level = 15 - int(i / SAMPLE_RATE / step_len)
				level = max(0, level)
			value = 1.0 if phase < note.duty else -1.0
			samples.append(value * amplitude * level / 15.0)
			phase += step
			if phase >= 1.0:
				phase -= 1.0
	return samples


def writeWav(path, samples):
	data = array.array("h", [max(-32767, min(32767, int(round(s * 32767)))) for s in samples])
	if sys.byteorder == "big":
		data.byteswap()
	directory = os.path.dirname(path)
	if directory and not os.path.isdir(directory):
		os.makedirs(directory)
	out = wave.open(path, "wb")
	out.setnchannels(1)
	out.setsampwidth(2)
	out.setframerate(SAMPLE_RATE)
	out.writeframes(data.tobytes())
	out.close()


def render(name, path, verbose=True):
	notes = parseSfx(SFX[name])
	samples = renderPulse(notes)
	writeWav(path, samples)
	if verbose:
		print("%s -> %s" % (name, path))
		print("note  period    Hz  frames  seconds")
		for note in notes:
			print("%4d  %6d  %6.1f  %6d  %7.3f" % (
				notes.index(note), note.period, note.frequency(), note.frames, note.seconds()))
		print("total: %d frames, %.3f s, %d samples" % (
			sum([n.frames for n in notes]), len(samples) / float(SAMPLE_RATE), len(samples)))
	return notes


def main(argv):
	if len(argv) != 3 or argv[1] not in SFX:
		print("usage: %s <%s> <output.wav>" % (os.path.basename(argv[0]), "|".join(sorted(SFX))))
		return 1
	render(argv[1], argv[2])
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv))
