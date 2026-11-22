"""Check the spatial intensity law independently of Blender's renderer."""
import math
import unittest
from fawltypoly.quantum_optics.materials import beam_profile, validate


class GaussianBeamTests(unittest.TestCase):
    def test_waist_and_radial_falloff(self):
        self.assertAlmostEqual(beam_profile((0, 0, 0), 2), 1)
        self.assertAlmostEqual(beam_profile((0.9, 0, 0), 2), math.exp(-2))
        self.assertLess(beam_profile((1.8, 0, 0), 2), 0.001)

    def test_divergence_and_axis_symmetry(self):
        z, waist, rayleigh = 2, 0.9, 6
        q = 1 + (z / rayleigh) ** 2
        radius = waist * math.sqrt(q)
        self.assertAlmostEqual(beam_profile((0, 0, z), 2), 1 / q)
        self.assertAlmostEqual(beam_profile((radius, 0, z), 2), math.exp(-2) / q)
        self.assertEqual(beam_profile((0.4, 0.5, 1), 2), beam_profile((1, 0.4, 0.5), 0))
        self.assertEqual(beam_profile((0.4, 0.5, 1), 2), beam_profile((0.4, 0.5, -1), 2))

    def test_soft_ends_and_invalid_dimensions(self):
        self.assertEqual(beam_profile((0, 0, 4.1), 2), 0)
        self.assertLess(beam_profile((0, 0, 4.0), 2), beam_profile((0, 0, 3.5), 2))
        with self.assertRaises(ValueError):
            beam_profile((0, 0, 0), 2, waist=0)
        with self.assertRaises(ValueError):
            validate(((1, 0, 0),) * 3, 1, 6, 4, 5, 1)


if __name__ == '__main__':
    unittest.main()
