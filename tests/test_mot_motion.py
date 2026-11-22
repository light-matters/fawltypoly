"""Behavior checks for the educational storyboard, independent of Blender."""

import math
import unittest
from projects.mot.motion import population, position, tracks


class StoryboardTests(unittest.TestCase):
    def test_reproducible_and_seeded(self):
        self.assertEqual(tracks(8, 17, 24), tracks(8, 17, 24))
        self.assertNotEqual(tracks(8, 17, 24), tracks(8, 18, 24))

    def test_cooling_and_capture_are_distinct(self):
        atoms = [a for a in population() if a.captured]

        def speed(time):
            return sum(math.dist(position(a, time), position(a, time + 0.001))
                       for a in atoms) / len(atoms) / 0.001

        def spread(time):
            return sum(math.dist(position(a, time), (0, 0, 0)) ** 2
                       for a in atoms) / len(atoms)

        self.assertLess(speed(10), speed(2) * 0.12)
        self.assertLess(spread(18), spread(10) * 0.3)
        self.assertGreater(speed(18), 0.005)  # Residual motion, not frozen atoms.
        self.assertGreater(spread(10), 0.4)  # Cooling alone has not contracted it.

    def test_overlap_and_escape(self):
        for atom in population(20):
            for time in (0, 3.99, 5, 10, 12, 16, 20):
                p = position(atom, time)
                self.assertTrue(all(math.isfinite(x) for x in p))
                if atom.captured:
                    self.assertLess(max(math.hypot(p[i], p[j]) for i, j in ((0, 1), (1, 2), (0, 2))), 1.3)
                elif time >= 16:
                    self.assertGreater(math.hypot(p[0], p[1]), 4)

    def test_no_jumps_at_stage_boundaries(self):
        for atom in population(20):
            for time in (4, 5, 11, 12, 16):
                self.assertLess(math.dist(position(atom, time - 1e-6),
                                          position(atom, time + 1e-6)), 0.0001)

    def test_invalid_options(self):
        for count in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                population(count)
        with self.assertRaises(ValueError):
            tracks(frames=1)


if __name__ == "__main__":
    unittest.main()
