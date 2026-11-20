import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import adaptive_controller_v5 as controller
import aes_gcm_integration_v5_roundtrip as aes
import anomaly_detection_v5_hybrid_confirmation as anomaly


class AdaptiveControllerRecoveryTests(unittest.TestCase):
    def test_healthy_background_qkd_replenishes_pool_and_recovers(self):
        rows = [
            {
                "time_seconds": str(t),
                "qber": "0.01",
                "generated_key_bits": "1000",
                "channel_status": "NORMAL",
            }
            for t in range(30)
        ]
        with patch.object(controller, "INITIAL_POOL_BITS", 1000):
            results, _, summary = controller.run_controller(rows)

        self.assertGreater(
            summary["background_qkd_bits_accepted_during_fallback"], 0
        )
        self.assertGreaterEqual(summary["recovery_count"], 1)
        self.assertEqual(summary["final_mode"], "QKD")
        self.assertTrue(summary["accounting_valid"])
        self.assertTrue(any(r["operating_mode"] == "PQC_FALLBACK" for r in results))

    def test_failed_qkd_rekey_is_marked_unsuccessful(self):
        rows = [{
            "time_seconds": "0",
            "qber": "0.01",
            "generated_key_bits": "0",
            "channel_status": "NORMAL",
        }]
        with patch.object(controller, "INITIAL_POOL_BITS", 0), patch.object(
            controller, "FALLBACK_POOL_THRESHOLD", -1
        ):
            results, _, summary = controller.run_controller(rows)
        self.assertEqual(results[0]["rekey_event"], 1)
        self.assertEqual(results[0]["rekey_success"], 0)
        self.assertEqual(results[0]["key_source"], "NONE")
        self.assertEqual(summary["failed_qkd_rekeys"], 1)

    def test_degraded_channel_bits_are_not_accepted_in_fallback(self):
        rows = [
            {
                "time_seconds": str(t),
                "qber": "0.12",
                "generated_key_bits": "1000",
                "channel_status": "DEGRADED",
            }
            for t in range(25)
        ]
        with patch.object(controller, "INITIAL_POOL_BITS", 1000):
            _, _, summary = controller.run_controller(rows)
        self.assertEqual(
            summary["background_qkd_bits_accepted_during_fallback"], 0
        )
        self.assertTrue(summary["accounting_valid"])


    def test_hybrid_controller_uses_same_safe_recovery_rule(self):
        qkd_rows = [
            {
                "time_seconds": str(t),
                "qber": "0.01",
                "generated_key_bits": "1000",
                "channel_status": "NORMAL",
            }
            for t in range(30)
        ]
        scored = pd.DataFrame({
            "time_seconds": list(range(30)),
            "anomaly_prediction": [0] * 30,
            "anomaly_score": [0.0] * 30,
        })
        with patch.object(controller, "INITIAL_POOL_BITS", 1000):
            _, _, summary = anomaly.run_controller_with_anomaly(qkd_rows, scored)
        self.assertGreaterEqual(summary["recovery_count"], 1)
        self.assertTrue(summary["accounting_valid"])


class AESRekeyScheduleTests(unittest.TestCase):
    def test_failed_rekey_attempt_is_skipped(self):
        frame = pd.DataFrame([
            {
                "time_seconds": 10,
                "operating_mode": "QKD",
                "rekey_event": 1,
                "rekey_success": 0,
                "key_source": "NONE",
                "session_key_epoch": 0,
            },
            {
                "time_seconds": 20,
                "operating_mode": "QKD",
                "rekey_event": 1,
                "rekey_success": 1,
                "key_source": "SIMULATED_QKD_POOL",
                "session_key_epoch": 1,
            },
        ])
        schedule, times, registry = aes.generate_key_schedule(frame)
        self.assertEqual(times, [20.0])
        self.assertEqual(len(schedule), 1)
        self.assertEqual(len(registry), aes.NUMBER_OF_SESSIONS)

    def test_legacy_failed_rekey_attempt_is_skipped(self):
        frame = pd.DataFrame([
            {
                "time_seconds": 10,
                "operating_mode": "QKD",
                "rekey_event": 1,
                "key_source": "NONE",
                "session_key_epoch": 0,
            },
            {
                "time_seconds": 20,
                "operating_mode": "QKD",
                "rekey_event": 1,
                "key_source": "SIMULATED_QKD_POOL",
                "session_key_epoch": 1,
            },
        ])
        _, times, _ = aes.generate_key_schedule(frame)
        self.assertEqual(times, [20.0])


class IsolationForestEvaluationTests(unittest.TestCase):
    def test_training_window_is_excluded_from_metrics(self):
        scored = pd.DataFrame({
            "time_seconds": list(range(300)),
            "anomaly_prediction": [0] * 220 + [1] * 60 + [0] * 20,
        })
        metrics, _ = anomaly.evaluate_anomaly_model(scored)
        self.assertEqual(metrics["total_samples"], 80)
        self.assertEqual(metrics["excluded_training_samples"], 220)
        self.assertEqual(metrics["true_positives"], 60)
        self.assertEqual(metrics["false_positives"], 0)
        self.assertEqual(metrics["false_negatives"], 0)
        self.assertEqual(metrics["accuracy"], 1.0)

    def test_empty_holdout_raises(self):
        scored = pd.DataFrame({
            "time_seconds": list(range(220)),
            "anomaly_prediction": [0] * 220,
        })
        with self.assertRaisesRegex(ValueError, "No held-out observations"):
            anomaly.evaluate_anomaly_model(scored)


if __name__ == "__main__":
    unittest.main()
