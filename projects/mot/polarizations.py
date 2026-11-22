"""Explicit lab-frame convention for the educational type-I MOT.

Time dependence: Re[epsilon exp(-i omega t)]. The field gradient is proportional
to (x,y,-2z); the preset assumes an F -> F+1 transition with positive upper g.
Lab bases (u,v) are (y,z), (z,x), (x,y). Jones vectors are (u+i*s*v)/sqrt(2).
No position-dependent sigma labels or LCP/RCP viewing conventions are used.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BeamPolarization:
    axis: int
    source_side: int

    @property
    def propagation_sign(self):
        return -self.source_side

    @property
    def helicity(self):
        return -1 if self.axis == 2 else 1

    @property
    def lab_sense(self):
        return self.propagation_sign * self.helicity

    @property
    def direction(self):
        return tuple(self.propagation_sign if i == self.axis else 0 for i in range(3))

    @property
    def reference(self):
        return tuple(1 if i == (self.axis + 1) % 3 else 0 for i in range(3))

    @property
    def jones(self):
        return tuple((1 if i == (self.axis + 1) % 3 else 0)
                     / math.sqrt(2) + (1j * self.lab_sense if i == (self.axis + 2) % 3 else 0)
                     / math.sqrt(2) for i in range(3))

    def field(self, phase):
        return tuple(math.sqrt(2) * (v.real * math.cos(phase) + v.imag * math.sin(phase))
                     for v in self.jones)

    @property
    def label(self):
        u, v = 'xyz'[(self.axis + 1) % 3], 'xyz'[(self.axis + 2) % 3]
        k = '+' if self.propagation_sign > 0 else '-'
        sense = '+' if self.lab_sense > 0 else '-'
        return f'k {k}{"XYZ"[self.axis]}   ε = ({u} {sense} i{v})/√2'


def beams():
    return tuple(BeamPolarization(axis, side) for axis in range(3) for side in (-1, 1))
