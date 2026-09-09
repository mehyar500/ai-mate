"""A reviewed motion track must not jump from the character to a palm."""
import unittest

from local_app.visual import select_tracked_face


class FaceTrackingTests(unittest.TestCase):
    def test_palm_does_not_steal_established_track(self):
        previous = [150, 70, 60, 80]
        current = [151, 71, 61, 79]
        palm = [70, 145, 30, 35]
        self.assertIs(select_tracked_face([palm, current], previous), current)
        self.assertIs(select_tracked_face([current, palm], previous), current)

    def test_missing_switched_or_ambiguous_face_fails(self):
        previous = [150, 70, 60, 80]
        for faces in [None, [], [[70,145,30,35]],
                      [[151,71,61,79], [152,72,60,80]],
                      [[float('nan'),70,60,80]], [[150,70,0,80]]]:
            with self.subTest(faces=faces), self.assertRaises(RuntimeError):
                select_tracked_face(faces, previous)

    def test_track_must_start_with_exactly_one_face(self):
        face = [150, 70, 60, 80]
        self.assertIs(select_tracked_face([face]), face)
        for faces in [None, [], [face, [70,145,30,35]],
                      [[float('nan'),70,60,80]], [[150,70,0,80]]]:
            with self.assertRaises(RuntimeError):
                select_tracked_face(faces)


if __name__ == '__main__':
    unittest.main()
