#!/usr/bin/env python3
"""
test_v3_runner_mock.py — End-to-End Mock Testing of v3_runner.py without QPU.

Verifies Point 7:
1. Submission gate closed (missing / invalid token) -> PermissionError, NO submission.
2. Successful submission -> saves metadata, job ID recorded.
3. Resumption & Idempotence -> does not resubmit duplicate job.
4. Result retrieval -> requires NO approval token, validates labels and shot counts.
5. Sequential enforcement -> Session k blocked if Session k-1 not retrieved.
6. Time-window enforcement -> blocked if current time < scheduled time.
7. ISA Hash mismatch -> aborts before submission call.
8. Shot count mismatch in result -> rejected fail-closed.
9. Full 16-session workflow & analysis -> runs analyze_full_campaign() cleanly.
"""

import hashlib
import json
import os
import shutil
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

from qiskit.providers.fake_provider import GenericBackendV2

REPO_ROOT = Path(__file__).resolve().parent.parent
PREREG_DIR = REPO_ROOT / "prereg"
sys.path.insert(0, str(REPO_ROOT / "src"))

import v3_runner
from v3_circuit_builder import CircuitBuilderV3
from v3_manifest import generate_frozen_manifest

TEST_DATA_DIR = REPO_ROOT / "data" / "v3_test_sessions"

class MockPubResult:
    def __init__(self, ones: int, shots: int):
        self.data = MagicMock()
        self.data.c.get_counts.return_value = {"1": ones, "0": shots - ones}

class TestV3RunnerMock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_token = "SECRET_TEST_TOKEN_123"
        cls.test_token_hash = hashlib.sha256(cls.test_token.encode("utf-8")).hexdigest()
        os.environ[v3_runner.ENV_APPROVAL_HASH_KEY] = cls.test_token_hash

        cls.orig_v3_data_dir = v3_runner.V3_DATA_DIR
        cls.orig_results_dir = v3_runner.RESULTS_DIR
        v3_runner.V3_DATA_DIR = TEST_DATA_DIR
        v3_runner.RESULTS_DIR = TEST_DATA_DIR

    @classmethod
    def tearDownClass(cls):
        v3_runner.V3_DATA_DIR = cls.orig_v3_data_dir
        v3_runner.RESULTS_DIR = cls.orig_results_dir
        if TEST_DATA_DIR.exists():
            shutil.rmtree(TEST_DATA_DIR)
        os.environ.pop(v3_runner.ENV_APPROVAL_HASH_KEY, None)

    def setUp(self):
        if TEST_DATA_DIR.exists():
            shutil.rmtree(TEST_DATA_DIR)
        TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def get_mock_backend(self):
        # Use real GenericBackendV2 target for realistic transpilation compatibility
        fake_b = GenericBackendV2(num_qubits=25)
        backend = MagicMock()
        backend.name = "ibm_marrakesh"
        backend.dt = 4e-9
        backend.target = fake_b.target
        return backend

    def get_mock_service(self, remaining_sec=432):
        service = MagicMock()
        service.active_instance.return_value = "crn:mock:open"
        service.instances.return_value = [{
            "crn": "crn:mock:open", "name": "open-instance",
            "plan": "open", "pricing_type": "free"
        }]
        service.usage.return_value = {
            "usage_consumed_seconds": 168,
            "usage_remaining_seconds": remaining_sec,
            "usage_limit_reached": False,
            "instance_id": "crn:mock:open"
        }
        return service

    def create_mock_pub_results(self, session_order, manifest):
        results = []
        for lbl in session_order:
            shots = manifest["circuits_catalog"][lbl]["shots"]
            ones = int(shots * (0.36 if "E" in lbl else 0.002))
            results.append(MockPubResult(ones, shots))
        return results

    # -------------------------------------------------------------------------
    # 1. Submission Gate Closed Without Valid Token
    # -------------------------------------------------------------------------
    def test_01_submission_gate_closed_without_token(self):
        mock_service = self.get_mock_service()
        mock_backend = self.get_mock_backend()

        with patch("v3_runner.SamplerV2") as mock_sampler_cls:
            mock_sampler = MagicMock()
            mock_sampler_cls.return_value = mock_sampler

            # A. None token
            with self.assertRaises(PermissionError):
                v3_runner.submit_session(0, approval_token=None, service=mock_service, backend=mock_backend)

            # B. Wrong token
            with self.assertRaises(PermissionError):
                v3_runner.submit_session(0, approval_token="invalid_token", service=mock_service, backend=mock_backend)

            # Ensure Sampler.run was NEVER called
            mock_sampler.run.assert_not_called()

    # -------------------------------------------------------------------------
    # 2. Successful Submission Writes Meta & Job ID
    # -------------------------------------------------------------------------
    def test_02_successful_submission_writes_metadata(self):
        mock_service = self.get_mock_service()
        mock_backend = self.get_mock_backend()

        with patch("v3_runner.SamplerV2") as mock_sampler_cls, \
             patch("v3_runner.build_and_verify_isa_circuits") as mock_isa_builder:
            
            mock_sampler = MagicMock()
            mock_job = MagicMock()
            mock_job.job_id.return_value = "mock_job_id_session_00"
            mock_sampler.run.return_value = mock_job
            mock_sampler_cls.return_value = mock_sampler

            mock_isa_builder.return_value = {lbl: MagicMock() for lbl in [
                "D_tau_8ns_G_t0", "D_tau_8ns_E_t0", "D_tau_8ns_G_tT", "D_tau_8ns_E_tT",
                "D_tau_8ns_G_t2T_mc", "D_tau_8ns_E_t2T_mc", "I_tau_8ns_G_t0", "I_tau_8ns_E_t0",
                "I_tau_8ns_G_tT", "I_tau_8ns_E_tT", "I_tau_8ns_G_t2T_mc", "I_tau_8ns_E_t2T_mc"
            ]}

            meta = v3_runner.submit_session(
                session_id=0,
                approval_token=self.test_token,
                enforce_schedule=False,
                service=mock_service,
                backend=mock_backend
            )

            mock_sampler.run.assert_called_once()
            meta_path = TEST_DATA_DIR / "session_00_meta.json"
            self.assertTrue(meta_path.exists())
            with open(meta_path, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["job_id"], "mock_job_id_session_00")
            self.assertEqual(saved["status"], "SUBMITTED")

    # -------------------------------------------------------------------------
    # 3. Idempotence & Resumption (Never duplicate submit)
    # -------------------------------------------------------------------------
    def test_03_idempotence_does_not_resubmit(self):
        mock_service = self.get_mock_service()
        mock_backend = self.get_mock_backend()

        meta_path = TEST_DATA_DIR / "session_00_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": 0, "job_id": "existing_mock_job",
                "session_info": {"circuit_execution_order": []},
                "circuits_catalog": {}, "status": "SUBMITTED"
            }, f)

        mock_job = MagicMock()
        mock_job.status.return_value = "RUNNING"
        mock_service.job.return_value = mock_job

        with patch("v3_runner.SamplerV2") as mock_sampler_cls:
            mock_sampler = MagicMock()
            mock_sampler_cls.return_value = mock_sampler

            v3_runner.submit_session(
                session_id=0,
                approval_token=self.test_token,
                enforce_schedule=False,
                service=mock_service,
                backend=mock_backend
            )
            mock_sampler.run.assert_not_called()

    # -------------------------------------------------------------------------
    # 4. Result Retrieval Requires NO Approval Token & Validates Shots
    # -------------------------------------------------------------------------
    def test_04_fetch_result_requires_no_token_and_validates(self):
        mock_service = self.get_mock_service()
        with open(PREREG_DIR / "v3_manifest_core.json", encoding="utf-8") as f:
            manifest = json.load(f)

        s0_info = manifest["sessions"][0]
        meta_path = TEST_DATA_DIR / "session_00_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": 0, "job_id": "mock_fetch_job",
                "session_info": s0_info,
                "circuits_catalog": manifest["circuits_catalog"],
                "status": "SUBMITTED"
            }, f)

        mock_pub_results = self.create_mock_pub_results(s0_info["circuit_execution_order"], manifest)
        mock_job = MagicMock()
        mock_job.status.return_value = "DONE"
        mock_job.result.return_value = mock_pub_results
        mock_job.usage.return_value = {"usage_seconds": 6, "quantum_seconds": 6}
        mock_service.job.return_value = mock_job

        result = v3_runner.fetch_session_result(0, service=mock_service)
        self.assertIsNotNone(result)
        result_path = TEST_DATA_DIR / "session_00_result.json"
        self.assertTrue(result_path.exists())

    # -------------------------------------------------------------------------
    # 5. Sequential Prerequisite Enforcement
    # -------------------------------------------------------------------------
    def test_05_sequential_prerequisite_blocks_jump_ahead(self):
        mock_service = self.get_mock_service()
        mock_backend = self.get_mock_backend()

        with patch("v3_runner.SamplerV2") as mock_sampler_cls:
            mock_sampler = MagicMock()
            mock_sampler_cls.return_value = mock_sampler

            with self.assertRaises(RuntimeError) as ctx:
                v3_runner.submit_session(
                    session_id=1,
                    approval_token=self.test_token,
                    enforce_schedule=False,
                    service=mock_service,
                    backend=mock_backend
                )
            self.assertIn("Prerequisite error: Previous session 0 result is not yet retrieved", str(ctx.exception))
            mock_sampler.run.assert_not_called()

    # -------------------------------------------------------------------------
    # 6. Schedule Window Enforcement
    # -------------------------------------------------------------------------
    def test_06_schedule_window_enforcement(self):
        mock_service = self.get_mock_service()
        mock_backend = self.get_mock_backend()

        with patch("v3_runner.SamplerV2") as mock_sampler_cls:
            mock_sampler = MagicMock()
            mock_sampler_cls.return_value = mock_sampler

            with self.assertRaises(RuntimeError) as ctx:
                v3_runner.submit_session(
                    session_id=0,
                    approval_token=self.test_token,
                    enforce_schedule=True,
                    service=mock_service,
                    backend=mock_backend
                )
            self.assertIn("Schedule window error", str(ctx.exception))
            mock_sampler.run.assert_not_called()

    # -------------------------------------------------------------------------
    # 7. ISA Hash Mismatch Aborts Before Submission
    # -------------------------------------------------------------------------
    def test_07_isa_hash_mismatch_aborts(self):
        mock_service = self.get_mock_service()
        mock_backend = self.get_mock_backend()

        with patch("v3_runner.load_audited_isa_hashes") as mock_audit_loader, \
             patch("v3_runner.transpile") as mock_transpile, \
             patch("v3_runner.SamplerV2") as mock_sampler_cls:
            
            mock_sampler = MagicMock()
            mock_sampler_cls.return_value = mock_sampler

            # Mock transpiled circuit data
            mock_qc = MagicMock()
            mock_qc.data = "mock_compiled_data"
            mock_transpile.return_value = mock_qc

            # Deliberately return mismatched reference hashes
            mock_audit_loader.return_value = {"D_tau_8ns_G_t0": "corrupted_hash_value_12345"}

            with self.assertRaises(ValueError) as ctx:
                v3_runner.submit_session(
                    session_id=0,
                    approval_token=self.test_token,
                    enforce_schedule=False,
                    service=mock_service,
                    backend=mock_backend
                )
            self.assertIn("ISA Hash Mismatch", str(ctx.exception))
            mock_sampler.run.assert_not_called()

    # -------------------------------------------------------------------------
    # 8. Result Shot Mismatch Rejected Fail-Closed
    # -------------------------------------------------------------------------
    def test_08_result_shot_mismatch_rejected(self):
        with open(PREREG_DIR / "v3_manifest_core.json", encoding="utf-8") as f:
            manifest = json.load(f)
        s0_info = manifest["sessions"][0]
        meta = {
            "session_id": 0, "job_id": "test_mismatch_job",
            "session_info": s0_info,
            "circuits_catalog": manifest["circuits_catalog"]
        }
        mock_results = self.create_mock_pub_results(s0_info["circuit_execution_order"], manifest)
        # Corrupt shot count
        mock_results[0].data.c.get_counts.return_value = {"1": 10, "0": 489}

        out_path = TEST_DATA_DIR / "session_00_corrupt_result.json"
        mock_job = MagicMock()
        mock_job.usage.return_value = {"usage_seconds": 6}
        with self.assertRaises(ValueError) as ctx:
            v3_runner.save_and_verify_session_result(0, mock_results, mock_job, meta, out_path)
        self.assertIn("shot mismatch", str(ctx.exception))
        self.assertFalse(out_path.exists())

    # -------------------------------------------------------------------------
    # 9. Full 16-Session Workflow & Analysis
    # -------------------------------------------------------------------------
    def test_09_full_16_sessions_campaign_analysis(self):
        from v3_simulator import PhysicalSimulatorV3
        sim = PhysicalSimulatorV3()
        rng = np.random.default_rng(2026)
        mock_campaign = sim.generate_campaign(l_target=0.08, rng=rng)

        for s_idx in range(16):
            s_raw = mock_campaign[s_idx]
            counts_dict = {}
            for (arm, prep, t_name), c_entry in s_raw.counts.items():
                lbl = f"{arm}_tau_8ns_{prep}_{t_name}"
                if t_name == "t2T":
                    lbl += "_mc"
                counts_dict[lbl] = {"ones": c_entry["ones"], "zeros": c_entry["shots"] - c_entry["ones"], "shots": c_entry["shots"]}
            
            res_path = TEST_DATA_DIR / f"session_{s_idx:02d}_result.json"
            with open(res_path, "w", encoding="utf-8") as f:
                json.dump({
                    "session_id": s_idx, "job_id": f"mock_job_{s_idx}",
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    "counts": counts_dict
                }, f)

        camp_res = v3_runner.analyze_full_campaign()
        self.assertIsNotNone(camp_res)
        self.assertEqual(camp_res.n_sessions_total, 16)
        self.assertTrue(camp_res.all_evaluable)
        self.assertIsNotNone(camp_res.mean_L)
        self.assertTrue((TEST_DATA_DIR / "v3_l_measurement_report.json").exists())

    # -------------------------------------------------------------------------
    # 10. Crash Recovery: Intent Without Meta Halts for Manual Reconciliation
    # -------------------------------------------------------------------------
    def test_10_intent_without_meta_halts_for_manual_reconciliation(self):
        mock_service = self.get_mock_service()
        mock_backend = self.get_mock_backend()
        
        # Even if a job exists on remote backend around that timestamp,
        # runner must NOT automatically assign it!
        mock_job = MagicMock()
        mock_job.job_id.return_value = "suspicious_candidate_job"
        now_utc = datetime.now(timezone.utc)
        mock_job.creation_date = now_utc + timedelta(seconds=1)
        mock_service.jobs.return_value = [mock_job]

        # Simulate crash: intent exists, meta does not
        intent_path = TEST_DATA_DIR / "session_00_intent.json"
        with open(intent_path, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": 0, "intent_created_at_utc": now_utc.isoformat(),
                "status": "INTENT_DECLARED"
            }, f)

        with patch("v3_runner.SamplerV2") as mock_sampler_cls:
            mock_sampler = MagicMock()
            mock_sampler_cls.return_value = mock_sampler

            with self.assertRaises(RuntimeError) as ctx:
                v3_runner.submit_session(
                    session_id=0,
                    approval_token=self.test_token,
                    enforce_schedule=False,
                    service=mock_service,
                    backend=mock_backend
                )
            self.assertIn("KÉZI EGYEZTETÉS SZÜKSÉGES", str(ctx.exception))
            # Critical: must NOT auto-create meta file
            self.assertFalse((TEST_DATA_DIR / "session_00_meta.json").exists())
            # Critical: must NOT have called sampler.run again
            mock_sampler.run.assert_not_called()

    # -------------------------------------------------------------------------
    # 11. Crash Recovery: Manual Resolution Allows Safe Fetch Without Re-run
    # -------------------------------------------------------------------------
    def test_11_manual_resolution_prevents_duplicate_submission(self):
        mock_service = self.get_mock_service()
        mock_backend = self.get_mock_backend()

        now_utc = datetime.now(timezone.utc)
        # Operator manually verified IBM console and created meta file
        meta_path = TEST_DATA_DIR / "session_00_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": 0, "job_id": "manually_verified_job_123",
                "submitted_at_utc": now_utc.isoformat(),
                "status": "SUBMITTED"
            }, f)

        mock_remote_job = MagicMock()
        mock_remote_job.status.return_value = "RUNNING"
        mock_service.job.return_value = mock_remote_job

        with patch("v3_runner.SamplerV2") as mock_sampler_cls:
            mock_sampler = MagicMock()
            mock_sampler_cls.return_value = mock_sampler

            res = v3_runner.submit_session(
                session_id=0,
                approval_token=self.test_token,
                enforce_schedule=False,
                service=mock_service,
                backend=mock_backend
            )
            # Must NOT call sampler.run again
            mock_sampler.run.assert_not_called()
            # Must have fetched from existing job
            mock_service.job.assert_called_with("manually_verified_job_123")

    # -------------------------------------------------------------------------
    # 12. Instance Mismatch Halts Fail-Closed
    # -------------------------------------------------------------------------
    def test_12_instance_mismatch_blocks_submission(self):
        mock_service = self.get_mock_service()
        mock_backend = self.get_mock_backend()
        # Infiltrate a paid instance
        mock_service.active_instance.return_value = "crn:premium:paid"
        mock_service.instances.return_value = [{
            "crn": "crn:premium:paid", "name": "premium-instance",
            "plan": "pay_as_you_go", "pricing_type": "paid"
        }]

        with patch("v3_runner.SamplerV2") as mock_sampler_cls:
            mock_sampler = MagicMock()
            mock_sampler_cls.return_value = mock_sampler

            with self.assertRaises(RuntimeError) as ctx:
                v3_runner.submit_session(
                    session_id=0,
                    approval_token=self.test_token,
                    enforce_schedule=False,
                    service=mock_service,
                    backend=mock_backend
                )
            self.assertIn("Instance is NOT free open-instance", str(ctx.exception))
            mock_sampler.run.assert_not_called()

    # -------------------------------------------------------------------------
    # 13. Rapid Catch-Up & Duplicate Job Detection
    # -------------------------------------------------------------------------
    def test_13_rapid_catchup_and_duplicate_job_detection(self):
        mock_service = self.get_mock_service()
        mock_backend = self.get_mock_backend()

        # Session 0 submitted 5 minutes ago (min 10 min required)
        s0_sub_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        with open(TEST_DATA_DIR / "session_00_meta.json", "w", encoding="utf-8") as f:
            json.dump({
                "session_id": 0, "job_id": "job_0",
                "submitted_at_utc": s0_sub_time.isoformat(),
                "status": "SUBMITTED"
            }, f)
        with open(TEST_DATA_DIR / "session_00_result.json", "w", encoding="utf-8") as f:
            json.dump({"session_id": 0, "job_id": "job_0", "counts": {}}, f)

        # Attempt to submit Session 1 immediately (only 10 min elapsed < 45 min)
        with patch("v3_runner.SamplerV2") as mock_sampler_cls:
            mock_sampler = MagicMock()
            mock_sampler_cls.return_value = mock_sampler

            with self.assertRaises(RuntimeError) as ctx:
                v3_runner.submit_session(
                    session_id=1,
                    approval_token=self.test_token,
                    enforce_schedule=True,
                    service=mock_service,
                    backend=mock_backend
                )
            self.assertIn("Rapid catch-up prohibited", str(ctx.exception))
            mock_sampler.run.assert_not_called()

        # Test duplicate job ID detection in analyze_full_campaign
        with open(TEST_DATA_DIR / "session_01_result.json", "w", encoding="utf-8") as f:
            # Reusing job_0 from session 0
            json.dump({"session_id": 1, "job_id": "job_0", "counts": {}}, f)
        with self.assertRaises(ValueError) as ctx2:
            v3_runner.analyze_full_campaign()
        self.assertIn("DUPLICATE JOB ID DETECTED", str(ctx2.exception))

if __name__ == "__main__":
    unittest.main()
