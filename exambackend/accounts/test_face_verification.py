"""Synthetic score checks for the exam face verification boundary."""
import json
from unittest.mock import patch

import numpy as np
from django.test import SimpleTestCase

from . import face_service


class FaceVerificationThresholdTests(SimpleTestCase):
    def setUp(self):
        self.image = np.zeros((120, 160, 3), dtype=np.uint8)
        self.features = np.zeros((1, 128), dtype=np.float32)
        self.stored = json.dumps([0.0] * 128)

    def verify_with_scores(self, scores):
        with patch.object(face_service, '_get_recognizer') as recognizer, \
                patch.object(face_service, '_load_image_bytes', return_value=self.image), \
                patch.object(face_service, '_get_face_features', return_value=self.features) as extract:
            recognizer.return_value.match.side_effect = scores
            result = face_service.verify_face_bytes(self.stored, b'synthetic-frame')
            return result, extract.call_count

    def test_weak_and_borderline_impostor_scores_are_rejected(self):
        for score in (0.10, 0.30, 0.362):
            with self.subTest(score=score):
                result, attempts = self.verify_with_scores([score, score])
                self.assertFalse(result['verified'])
                self.assertEqual(attempts, 2)

    def test_reference_threshold_accepts_genuine_score_without_mirror_retry(self):
        result, attempts = self.verify_with_scores([0.363])
        self.assertTrue(result['verified'])
        self.assertEqual(attempts, 1)

    def test_mirror_retry_can_accept_a_strong_match(self):
        result, attempts = self.verify_with_scores([0.20, 0.40])
        self.assertTrue(result['verified'])
        self.assertEqual(attempts, 2)
