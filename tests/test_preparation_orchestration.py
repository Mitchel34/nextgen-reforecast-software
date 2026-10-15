"""Inert annual plans and receipt declarations; no forcing or model access."""

from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from ngen_reforecast.preparation import RequestPreparationError, _json_text, normalize_request
from ngen_reforecast.preparation import orchestration as api
from ngen_reforecast.preparation.readiness import _hash, preparation_binding


BASE = {"identifier_type": "usgs", "identifier": "03479000", "mode": "reforecast",
        "start_date": "2022-01-01", "end_date": "2022-01-01",
        "start_hour_utc": 1, "end_hour_utc": 6, "max_lead_hours": 6}
ORIGIN = "2022-01-01T00:00:00Z"
DIGEST = hashlib.sha256(b"inert test declaration; no artifact read").hexdigest()


def plan(**changes):
    return api.plan_preparation(normalize_request({**BASE, **changes}), origin_time_utc=ORIGIN)


def record(index, state="passed", evidence_class="synthetic"):
    return {"task_index": index, "check_state": state,
            "evidence": None if state == "unknown" else {
                "artifact_sha256": DIGEST, "evidence_class": evidence_class,
                "detail": "Inert caller declaration; no scientific check performed."}}


class PreparationOrchestrationTests(unittest.TestCase):
    def assert_error(self, call, code):
        with self.assertRaises(RequestPreparationError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)
        self.assertTrue(caught.exception.field)

    def test_streaming_hash_matches_existing_canonical_identity(self):
        for candidate in ({"z": 6.0, "a": [None, True, False, "\ud800é😀\x00", {"x": -0.0}]},
                          plan(), api.checkpoint_preparation(plan(), [])):
            self.assertEqual(api._hash(candidate), _hash(candidate))

    def test_exact_issue_partition_and_one_complete_original_history(self):
        result = plan()
        tasks = result["tasks"]
        self.assertEqual(len(tasks), 4)
        self.assertEqual(tasks[0]["task_kind"], "history_coverage")
        self.assertEqual(tasks[0]["issues_utc"], [])
        self.assertEqual(tasks[0]["history_interval"], {
            "start_time_utc": ORIGIN, "stop_time_utc_exclusive": "2022-01-02T00:00:00Z",
            "provider_label": "interval_start", "timestep_hours": 1})
        self.assertEqual([issue for task in tasks[1:] for issue in task["issues_utc"]],
                         result["requested_population"]["issues_utc"])
        self.assertTrue(all(task["history_interval"] is None for task in tasks[1:]))
        binding = preparation_binding(result["request"], origin_time_utc=ORIGIN)
        self.assertEqual(result["preparation_binding"], binding)
        for task in tasks:
            self.assertEqual(task["scope_sha256"], binding["scope_sha256"])
            self.assertEqual(task["request_sha256"], binding["request_sha256"])
            self.assertEqual(task["origin_time_utc"], ORIGIN)
        self.assertFalse(result["dispatch_supported"] or result["execution_ready"] or result["source_coverage_qualified"])

    def test_partial_final_batch_retains_last_issue_and_all_source_leads(self):
        result = plan(end_hour_utc=5, max_lead_hours=1)
        self.assertEqual([len(task["issues_utc"]) for task in result["tasks"]], [0, 2, 2, 1])
        self.assertEqual(result["batch_policy"]["forecast_source_leads"], {"min": 1, "max": 18})
        self.assertEqual(result["requested_population"]["preview"]["generated_rows_per_location"], 90)
        self.assertEqual(result["requested_population"]["preview"]["retained_rows_per_location"], 5)

    def test_identity_changes_with_site_origin_retention_scope_or_batch_policy(self):
        original = plan()
        variants = [plan(identifier="99999999"), plan(max_lead_hours=18), plan(end_hour_utc=5),
                    api.plan_preparation(original["request"], origin_time_utc="2021-12-31T23:00:00Z"),
                    api.plan_preparation(original["request"], origin_time_utc=ORIGIN, issues_per_task=1)]
        for candidate in variants:
            self.assertNotEqual(candidate["plan_identity_sha256"], original["plan_identity_sha256"])
            self.assertNotEqual(candidate["tasks"][1]["task_identity_sha256"], original["tasks"][1]["task_identity_sha256"])
        self.assertEqual(original, plan())

    def test_unsupported_mode_origin_and_batch_policy_refuse_without_defaults(self):
        request = plan()["request"]
        for batch in (0, 3, True, 1.0, "2", None):
            self.assert_error(lambda: api.plan_preparation(request, origin_time_utc=ORIGIN, issues_per_task=batch), "INVALID_BATCH_POLICY")
        self.assert_error(lambda: api.plan_preparation(request, origin_time_utc=None), "INITIALIZATION_NOT_SELECTED")
        for origin in ("2022-01-01T01:00:00Z", "2022-01-01T00:30:00Z", "2022-01-01T00:00:00+00:00"):
            self.assert_error(lambda: api.plan_preparation(request, origin_time_utc=origin), "INVALID_INITIALIZATION_ORIGIN")
        continuous = normalize_request({**BASE, "mode": "continuous_simulation"})
        self.assert_error(lambda: api.plan_preparation(continuous, origin_time_utc=ORIGIN), "MODE_NOT_IMPLEMENTED")

    def test_larger_valid_study_is_refused_without_clipping_or_mutation(self):
        request = normalize_request({**BASE, "start_hour_utc": 0, "end_hour_utc": 23,
                                     "end_date": "2023-01-02"})
        before = deepcopy(request)
        self.assert_error(lambda: api.plan_preparation(request, origin_time_utc="2021-12-01T00:00:00Z"), "PLAN_SCOPE_LIMIT_EXCEEDED")
        self.assertEqual(request, before)

    def test_rebuilt_plan_rejects_tampering_even_when_outer_hash_is_resealed(self):
        original = plan()
        variants = []
        for mutate in (lambda x: x["tasks"].pop(), lambda x: x["tasks"].reverse(),
                       lambda x: x.update(execution_ready=True), lambda x: x.update(extra=True),
                       lambda x: x["tasks"][0]["history_interval"].update(start_time_utc="2021-12-31T23:00:00Z")):
            changed = deepcopy(original)
            mutate(changed)
            changed["plan_identity_sha256"] = _hash({key: value for key, value in changed.items() if key != "plan_identity_sha256"})
            variants.append(changed)
        for candidate in variants:
            self.assert_error(lambda: api.checkpoint_preparation(candidate, []), "PREPARATION_PLAN_MISMATCH")

    def test_artifacts_are_detached_and_json_round_trip_is_deterministic(self):
        original = plan()
        inputs = [record(1)]
        receipts = api.seal_task_receipts(original, inputs)
        inputs[0]["evidence"]["detail"] = "changed"
        self.assertNotEqual(receipts[0]["evidence"]["detail"], "changed")
        checkpoint = api.checkpoint_preparation(original, receipts)
        receipts[0]["evidence"]["detail"] = "changed again"
        self.assertNotEqual(checkpoint["receipts"][0]["evidence"]["detail"], "changed again")
        loaded = json.loads(json.dumps(checkpoint))
        self.assertEqual(api.resume_preparation(original, loaded), api.resume_preparation(original, checkpoint))

    def test_unrecorded_unknown_missing_failed_and_passed_stay_distinct(self):
        original = plan(end_hour_utc=8)
        receipts = api.seal_task_receipts(original, [record(0, "unknown"), record(1, "missing"), record(2, "failed"), record(3)])
        result = api.resume_preparation(original, api.checkpoint_preparation(original, receipts))
        self.assertEqual([task["declared_check_state"] for task in result["tasks"]],
                         ["unknown", "missing", "failed", "passed", "not_recorded"])
        self.assertEqual(len(result["pending_check_task_ids"]), 4)
        self.assertEqual(result["declared_reuse_candidate_task_ids"], [original["tasks"][3]["task_identity_sha256"]])
        self.assertFalse(result["all_checks_declared_passed"])

    def test_empty_checkpoint_keeps_every_check_pending(self):
        original = plan()
        result = api.resume_preparation(original, api.checkpoint_preparation(original, []))
        self.assertEqual(result["pending_check_task_ids"], [task["task_identity_sha256"] for task in original["tasks"]])
        self.assertEqual(result["declared_reuse_candidate_task_ids"], [])

    def test_all_declared_passes_never_grant_verification_or_execution(self):
        original = plan()
        for evidence_class in ("synthetic", "declared_metadata", "verification_receipt"):
            receipts = api.seal_task_receipts(original, [record(index, evidence_class=evidence_class) for index in range(4)])
            checkpoint = api.checkpoint_preparation(original, receipts)
            result = api.resume_preparation(original, checkpoint)
            self.assertTrue(result["all_checks_declared_passed"])
            for flag in ("dispatch_supported", "execution_ready", "source_coverage_qualified", "artifacts_reverified", "physical_recovery_established"):
                self.assertIs(result[flag], False)
            self.assertTrue(all(task["artifact_reverified"] is False for task in result["tasks"]))
            self.assertEqual(result["status"], "planning_only")

    def test_reordered_and_exact_duplicate_receipts_are_idempotent(self):
        original = plan()
        receipts = api.seal_task_receipts(original, [record(0), record(2)])
        expected = api.checkpoint_preparation(original, receipts)
        self.assertEqual(api.checkpoint_preparation(original, list(reversed(receipts)) + receipts), expected)
        self.assertEqual(api.checkpoint_preparation(original, receipts, previous=expected), expected)

    def test_conflicting_update_refuses_and_preserves_previous_checkpoint(self):
        original = plan()
        failed = api.seal_task_receipts(original, [record(1, "failed")])
        checkpoint = api.checkpoint_preparation(original, failed)
        before = deepcopy(checkpoint)
        passed = api.seal_task_receipts(original, [record(1)])
        self.assert_error(lambda: api.checkpoint_preparation(original, passed, previous=checkpoint), "CONFLICTING_TASK_RECEIPT")
        self.assert_error(lambda: api.checkpoint_preparation(original, passed + failed), "CONFLICTING_TASK_RECEIPT")
        self.assertEqual(checkpoint, before)

    def test_foreign_plan_scope_and_task_receipts_refuse(self):
        original = plan()
        foreign = api.seal_task_receipts(plan(identifier="99999999"), [record(0)])
        self.assert_error(lambda: api.checkpoint_preparation(original, foreign), "TASK_RECEIPT_SCOPE_MISMATCH")
        for key in ("scope_sha256", "task_identity_sha256", "plan_identity_sha256"):
            receipts = api.seal_task_receipts(original, [record(0)])
            receipts[0][key] = "0" * 64
            self.assert_error(lambda: api.checkpoint_preparation(original, receipts), "TASK_RECEIPT_SCOPE_MISMATCH")

    def test_corrupt_receipt_and_checkpoint_never_manufacture_empty_resume(self):
        original = plan()
        receipts = api.seal_task_receipts(original, [record(0)])
        receipts[0]["evidence"]["detail"] = "modified"
        self.assert_error(lambda: api.checkpoint_preparation(original, receipts), "TASK_RECEIPT_IDENTITY_MISMATCH")
        checkpoint = api.checkpoint_preparation(original, [])
        for key, value in (("execution_ready", True), ("checkpoint_identity_sha256", "0" * 64), ("extra", 1)):
            changed = {**checkpoint, key: value}
            self.assert_error(lambda: api.resume_preparation(original, changed), "PREPARATION_CHECKPOINT_MISMATCH")
        self.assert_error(lambda: api.resume_preparation(original, {}), "INVALID_PREPARATION_CHECKPOINT")
        self.assert_error(lambda: api.resume_preparation(plan(identifier="99999999"), checkpoint), "PREPARATION_CHECKPOINT_MISMATCH")

    def test_strict_record_schema_indices_states_and_evidence(self):
        original = plan()
        candidates = [[], {**record(0), "extra": True}, record(True), record(1.0), record(-1), record(4), record(0, "complete"),
                      {**record(0, "unknown"), "evidence": record(0)["evidence"]}]
        for key, value in (("artifact_sha256", "A" * 64), ("evidence_class", "trusted"), ("detail", " "), ("detail", "x" * 513)):
            candidate = record(0)
            candidate["evidence"][key] = value
            candidates.append(candidate)
        for candidate in candidates:
            self.assert_error(lambda: api.seal_task_receipts(original, [candidate]), "INVALID_TASK_RECEIPT")
        self.assert_error(lambda: api.seal_task_receipts(original, [record(0)] * 5), "TASK_RECEIPT_LIMIT_EXCEEDED")
        self.assert_error(lambda: api.checkpoint_preparation(original, [{}] * 9), "TASK_RECEIPT_LIMIT_EXCEEDED")

    def test_snapshot_rejects_cycles_unsafe_keys_nonjson_and_huge_numbers(self):
        cycle = []; cycle.append(cycle)
        for candidate in (cycle, {"constructor": 1}, {1: "bad"}, object(), 10**1000, float("nan"), float("inf")):
            self.assert_error(lambda: api._snapshot(candidate), "INVALID_ORCHESTRATION_ARTIFACT")
        nested = None
        for _ in range(22):
            nested = [nested]
        self.assert_error(lambda: api._snapshot(nested), "ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED")
        with patch.object(api, "MAX_ARTIFACT_NODES", 4):
            self.assert_error(lambda: api._snapshot([0, 1, 2, 3]), "ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED")

    def test_encoded_budget_counts_keys_escapes_unicode_and_repeated_strings(self):
        for candidate in ({"long-key": "\x00\n\ud800é😀"}, [None, True, False, 1.5, {"x": []}], ["a" * 100] * 3):
            exact = len(_json_text(candidate).encode("utf-8"))
            with patch.object(api, "MAX_ARTIFACT_BYTES", exact):
                self.assertEqual(api._snapshot(candidate), candidate)
            with patch.object(api, "MAX_ARTIFACT_BYTES", exact - 1):
                self.assert_error(lambda: api._snapshot(candidate), "ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED")
        with patch.object(api, "MAX_ARTIFACT_BYTES", 100):
            self.assert_error(lambda: api._snapshot({"x" * 101: None}), "ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED")

    def test_sealed_output_is_bounded_after_added_identities(self):
        original = plan()
        with patch.object(api, "MAX_ARTIFACT_BYTES", 500), patch.object(api, "_plan", return_value=original):
            self.assert_error(lambda: api.seal_task_receipts(original, [record(0)]), "ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED")

    def test_public_functions_do_not_dispatch_read_artifacts_or_start_processes(self):
        original = plan()
        forbidden = ("subprocess.run", "subprocess.Popen", "socket.create_connection", "urllib.request.urlopen",
                     "ngen_reforecast.execution.execute_campaign", "ngen_reforecast.execution.preflight_execution",
                     "ngen_reforecast.archive.verify_result", "ngen_reforecast.archive.export_result",
                     "ngen_reforecast.preparation.forcing_adapter.check_forcing_preparation", "builtins.open")
        policy = Path(__file__).absolute().parents[1] / "src/ngen_reforecast/preparation/request-policy.json"
        original_open = Path.open
        opened = []

        def policy_only(path, *args, **kwargs):
            self.assertEqual(path, policy, "Only the packaged policy can be read")
            opened.append(path)
            return original_open(path, *args, **kwargs)

        with ExitStack() as stack:
            mocks = [stack.enter_context(patch(target, side_effect=AssertionError(target))) for target in forbidden]
            stack.enter_context(patch.object(Path, "open", new=policy_only))
            receipts = api.seal_task_receipts(original, [record(0)])
            api.resume_preparation(original, api.checkpoint_preparation(original, receipts))
            for mocked in mocks:
                mocked.assert_not_called()
        self.assertGreater(len(opened), 0)


class AnnualPreparationOrchestrationTests(unittest.TestCase):
    def test_complete_nonleap_year_partition_and_global_history(self):
        request = normalize_request({**BASE, "start_hour_utc": 0, "end_hour_utc": 23, "end_date": "2022-12-31"})
        result = api.plan_preparation(request, origin_time_utc="2021-12-01T00:00:00Z")
        self.assertEqual(len(result["tasks"]), 4381)
        population = result["requested_population"]
        self.assertEqual(len(population["issues_utc"]), 8760)
        self.assertEqual(population["preview"]["generated_rows_per_location"], 157680)
        self.assertEqual(population["preview"]["retained_rows_per_location"], 52560)
        self.assertEqual([issue for task in result["tasks"][1:] for issue in task["issues_utc"]], population["issues_utc"])
        self.assertEqual(result["tasks"][0]["history_interval"]["start_time_utc"], "2021-12-01T00:00:00Z")
        self.assertEqual(result["tasks"][0]["history_interval"]["stop_time_utc_exclusive"], "2023-01-01T17:00:00Z")

    def test_leap_year_single_issue_receipt_repeat_fits_annual_bounds(self):
        request = normalize_request({**BASE, "start_date": "2020-01-01", "end_date": "2020-12-31", "start_hour_utc": 0, "end_hour_utc": 23})
        result = api.plan_preparation(request, origin_time_utc="2019-12-01T00:00:00Z", issues_per_task=1)
        self.assertEqual(len(result["requested_population"]["issues_utc"]), 8784)
        self.assertEqual(len(result["tasks"]), 8785)
        receipts = api.seal_task_receipts(result, [record(index) for index in range(8785)])
        checkpoint = api.checkpoint_preparation(result, receipts)
        repeated = api.checkpoint_preparation(result, receipts, previous=checkpoint)
        self.assertEqual(repeated, checkpoint)
        continuation = api.resume_preparation(result, json.loads(json.dumps(checkpoint)))
        self.assertTrue(continuation["all_checks_declared_passed"])
        self.assertEqual(len(continuation["declared_reuse_candidate_task_ids"]), 8785)
        self.assertFalse(continuation["artifacts_reverified"] or continuation["execution_ready"])


if __name__ == "__main__":
    unittest.main()
