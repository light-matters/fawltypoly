"""Authored educational motion, in display units and storyboard seconds.

No force, scattering, temperature or magnetic-field solver is used. Trigonometric
paths are retimed for cooling and eased into a seeded, disordered cloud. A preset
central population stays inside all three beam cylinders (radius 1.3); the outer
population passes outside their common overlap and departs during capture.
"""

from dataclasses import dataclass
import math
import random

LASER_ON = 4.0
COOLING = 5.0
COILS_ON = 11.0
CAPTURE = 12.0
SETTLED = 16.0
DURATION = 20.0


def ease(start, end, time):
    x = min(1.0, max(0.0, (time - start) / (end - start)))
    return x * x * (3 - 2 * x)


@dataclass(frozen=True)
class Atom:
    captured: bool
    phase: tuple
    frequency: tuple
    destination: tuple


def population(count=144, seed=17):
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("Atom count must be a positive integer")
    rng = random.Random(seed)
    return tuple(Atom(i % 5 != 0,
                      tuple(rng.uniform(0, math.tau) for _ in range(3)),
                      tuple(rng.uniform(3.0, 5.0) for _ in range(3)),
                      tuple(max(-0.5, min(0.5, rng.gauss(0, 0.20))) for _ in range(3)))
                 for i in range(count))


def position(atom, time):
    if not atom.captured:
        angle = atom.phase[0] + time * 1.9
        radius = 2.5 + max(0, time - CAPTURE) * 0.65
        return (radius * math.cos(angle), radius * math.sin(angle),
                1.3 * math.sin(atom.phase[2] + time * 3.2))
    # A continuous clock whose derivative falls smoothly from 1 to 0.04.
    elapsed = max(0, time - COOLING)
    clock = min(time, COOLING) + 0.04 * elapsed + 0.96 * 1.15 * (1 - math.exp(-elapsed / 1.15))
    free = tuple(0.88 * math.sin(p + clock * w) for p, w in zip(atom.phase, atom.frequency))
    blend = ease(CAPTURE, SETTLED, time)
    cold = tuple(d + 0.025 * math.sin(p + time * 1.1)
                 for d, p in zip(atom.destination, atom.phase))
    return tuple((1 - blend) * a + blend * b for a, b in zip(free, cold))


def tracks(count=144, seed=17, frames=480):
    if isinstance(frames, bool) or not isinstance(frames, int) or frames < 2:
        raise ValueError("At least two frames are required")
    return tuple(tuple((frame, position(atom, (frame - 1) / (frames - 1) * DURATION))
                       for frame in range(1, frames + 1))
                 for atom in population(count, seed))
