from django.test import SimpleTestCase

from accounts.grading import grade_question


class _Q:
    def __init__(self, question_type, correct_answer='', case_sensitive=False):
        self.question_type = question_type
        self.correct_answer = correct_answer
        self.case_sensitive = case_sensitive


class GradingTests(SimpleTestCase):
    def test_identification_case_insensitive_and_whitespace(self):
        q = _Q('identification', 'Photosynthesis')
        ok, credit = grade_question(q, '  photosynthesis. ')
        self.assertTrue(ok)
        self.assertEqual(credit, 1.0)

    def test_identification_alternatives(self):
        q = _Q('identification', 'HTTP | Hypertext Transfer Protocol')
        ok, _ = grade_question(q, 'http')
        self.assertTrue(ok)
        ok, _ = grade_question(q, 'Hypertext Transfer Protocol')
        self.assertTrue(ok)

    def test_identification_wrong_answer(self):
        q = _Q('identification', 'Manila')
        ok, credit = grade_question(q, 'Cebu')
        self.assertFalse(ok)
        self.assertEqual(credit, 0.0)

    def test_identification_manual_when_no_key(self):
        q = _Q('identification', '')
        ok, credit = grade_question(q, 'anything')
        self.assertIsNone(ok)
        self.assertEqual(credit, 0.0)

    def test_enumeration_newline_and_numbered(self):
        q = _Q('enumeration', 'Apple\nBanana\nOrange')
        ok, credit = grade_question(q, '1. apple\n2. banana\n3. orange')
        self.assertTrue(ok)
        self.assertEqual(credit, 1.0)

    def test_enumeration_comma_separated(self):
        q = _Q('enumeration', 'Apple\nBanana')
        ok, credit = grade_question(q, 'banana, apple')
        self.assertTrue(ok)
        self.assertEqual(credit, 1.0)

    def test_enumeration_partial_credit(self):
        q = _Q('enumeration', 'Apple\nBanana\nOrange')
        ok, credit = grade_question(q, 'apple\nbanana')
        self.assertFalse(ok)
        self.assertAlmostEqual(credit, 2 / 3)

    def test_multiple_choice(self):
        q = _Q('multiple_choice', 'Option A')
        ok, credit = grade_question(q, 'option a')
        self.assertTrue(ok)
        self.assertEqual(credit, 1.0)


class GazeLabelStickyTests(SimpleTestCase):
    CLASSES = [
        "Looking above the screen",
        "Looking at the left",
        "Looking at the right",
        "Looking at the screen (Normal)",
        "Looking below",
    ]

    def test_residual_right_does_not_stick_when_looking_at_screen(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        probs = np.array([0.04, 0.05, 0.41, 0.46, 0.04], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking at the screen (Normal)")

    def test_clear_right_look_still_detected(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[11] = 0.18
        geo[5] = 0.12
        geo[7] = 0.12
        probs = np.array([0.05, 0.08, 0.62, 0.18, 0.07], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking at the right")

    def test_held_left_look_not_forced_to_normal(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[11] = -0.04
        geo[5] = -0.05
        geo[7] = -0.05
        probs = np.array([0.06, 0.45, 0.10, 0.30, 0.09], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking at the left")

    def test_held_above_look_detected(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[1] = -0.06
        geo[6] = -0.05
        geo[8] = -0.05
        geo[12] = -0.06
        probs = np.array([0.40, 0.08, 0.07, 0.35, 0.10], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking above the screen")

    def test_clear_left_look_detected(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[11] = -0.18
        geo[5] = -0.12
        geo[7] = -0.12
        probs = np.array([0.05, 0.62, 0.08, 0.18, 0.07], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking at the left")

