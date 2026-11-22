"""Lab-frame Jones vectors, propagation and E-rotation conventions."""
import math
import unittest
from projects.mot.polarizations import beams


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


class LabPolarizationTests(unittest.TestCase):
    def test_normalized_and_transverse(self):
        for beam in beams():
            self.assertAlmostEqual(sum(abs(v)**2 for v in beam.jones), 1)
            self.assertAlmostEqual(abs(sum(k*v for k,v in zip(beam.direction,beam.jones))), 0)
            self.assertEqual(beam.direction[beam.axis], -beam.source_side)
            for phase in (0, 0.3, math.pi/2):
                field = beam.field(phase)
                self.assertAlmostEqual(sum(v*v for v in field), 1)
                self.assertAlmostEqual(sum(k*v for k,v in zip(beam.direction,field)), 0)

    def test_spin_matches_stated_helicity(self):
        for beam in beams():
            spin = cross(tuple(v.conjugate() for v in beam.jones), beam.jones)
            helicity = sum(k*s.imag for k,s in zip(beam.direction,spin))
            self.assertAlmostEqual(helicity, beam.helicity)
            turning = cross(beam.field(0), beam.field(math.pi/2))
            self.assertAlmostEqual(sum(k*v for k,v in zip(beam.direction,turning)), beam.helicity)

    def test_opposing_beams_conjugate_in_lab(self):
        for axis in range(3):
            a,b = [p for p in beams() if p.axis == axis]
            self.assertEqual(a.jones, tuple(v.conjugate() for v in b.jones))
            self.assertEqual(a.helicity, b.helicity)
        self.assertEqual([p.helicity for p in beams()], [1,1,1,1,-1,-1])


if __name__ == '__main__':
    unittest.main()
