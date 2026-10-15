"""Small synthetic mechanics; none of these cases invokes a model or measures a user."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import itertools
import json
import math
import unittest
from unittest.mock import patch

from ngen_reforecast.benchmarking import (
    BenchmarkError, WorkflowRecorder, assess_pair, compare_fixture_rows, freeze_contract,
)
from ngen_reforecast.benchmarking.workflow import PHASES


def digest(letter):
    return letter * 64


def keys():
    issue = datetime(2022, 1, 2, tzinfo=timezone.utc)
    return [["03479000", issue.strftime("%Y-%m-%dT%H:%M:%SZ"), lead,
             (issue + timedelta(hours=lead)).strftime("%Y-%m-%dT%H:%M:%SZ")]
            for lead in range(1, 19)]


def contract(**changes):
    spec = dict(trial_manifest_sha256=digest("f"), scientific_identity={name + "_sha256": digest(letter) for name, letter in
                zip(("workload", "model", "inputs", "reference"), "abcd")},
                environment_sha256=digest("e"),
                resources={"cpu_limit": 2, "memory_limit_bytes": 8 * 1024**3, "parallel_jobs": 1},
                cache_stratum="warm-resident", cache_definition="resident-inputs-v1", expected_keys=keys())
    spec.update(changes)
    return freeze_contract(**spec)


def verification(c):
    return {"manifest_sha256": digest("a"), "verification_sha256": digest("b"),
            "reference_sha256": c["scientific_identity"]["reference_sha256"],
            "observed_rows": len(c["expected_keys"]), "outcome": "passed-complete-products"}


def rows(value=2.0):
    return [{"key": k, "unit": "m3 s-1", "discharge": value} for k in keys()]


def reseal(value):
    value = deepcopy(value)
    value.pop("identity_sha256", None)
    value["identity_sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()
    return value


def attempt(c=None, arm="manual", observed=False, step=10, verified=True, human=False, **finish):
    c = c or contract()
    # Patching is test-only: never represent these deterministic samples as observations.
    clock = itertools.count(100, step).__next__
    options = dict(run_id=arm + "-attempt", paired_block_id="block-1", arm=arm,
                   implementation_sha256=digest("a" if arm == "manual" else "b"))
    if observed:
        options.update(measurement_origin="observed-session",
                       observation_record_sha256=digest("c" if arm == "manual" else "d"))
    else:
        options["clock_ns"] = clock
    with patch("ngen_reforecast.benchmarking.workflow.time.monotonic_ns", clock):
        recorder = WorkflowRecorder(c, **options)
        for phase in PHASES:
            recorder.start_phase(phase)
            recorder.end_phase(phase)
        return recorder.finish(verification=verification(c) if verified else None,
                               human_observation_complete=human, **finish)


class ContractTests(unittest.TestCase):
    def test_contract_is_deterministic_order_independent_and_isolated(self):
        original = keys()
        c = contract(expected_keys=list(reversed(original)))
        self.assertEqual(c, contract())
        original[0][0] = "changed"
        self.assertEqual(c["expected_keys"][0][0], "03479000")
        self.assertEqual(c["status"], "draft")

    def test_missing_or_duplicate_population_refused(self):
        for population in (keys()[:-1], keys() + [keys()[0]], []):
            with self.subTest(population=len(population)), self.assertRaises(BenchmarkError):
                contract(expected_keys=population)

    def test_invalid_time_and_bool_lead_refused(self):
        for field, value in ((1, "2022-01-02T00:00:00+00:00"), (2, True),
                             (3, "2022-01-02T02:00:00Z"), (1, "2022-01-02T00:01:00Z")):
            population = keys()
            population[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(BenchmarkError):
                contract(expected_keys=population)

    def test_resources_and_identity_are_strict(self):
        for limits in ({"cpu_limit": True, "memory_limit_bytes": 8, "parallel_jobs": 1},
                       {"cpu_limit": 1, "memory_limit_bytes": 8, "parallel_jobs": 2},
                       {"cpu_limit": 0, "memory_limit_bytes": 8, "parallel_jobs": 1}):
            with self.assertRaises(BenchmarkError):
                contract(resources=limits)
        with self.assertRaises(BenchmarkError):
            contract(environment_sha256="a-local-path")

    def test_cache_strata_require_explicit_definition(self):
        for value in ("cold", None, []):
            with self.assertRaises(BenchmarkError):
                contract(cache_stratum=value)
        with self.assertRaises(BenchmarkError):
            contract(cache_definition="/private/location")

    def test_frozen_rules_cannot_be_resealed_with_new_tolerance(self):
        c = contract()
        c["comparator"]["abs_tol"] = 1e-2
        with self.assertRaises(BenchmarkError):
            WorkflowRecorder(reseal(c), run_id="x", paired_block_id="block-1", arm="manual", implementation_sha256=digest("a"))

    def test_bounded_and_unserializable_inputs_fail_closed(self):
        cases = ([keys()[0]] * 4097, set(), [object()], [2**20000])
        for value in cases:
            with self.subTest(type=type(value)), self.assertRaises(BenchmarkError):
                contract(expected_keys=value)
        # Byte limit is cumulative before cloning the full oversized input.
        with self.assertRaises(BenchmarkError):
            contract(expected_keys=[["x" * 512] * 8] * 600)

    def test_depth_and_dictionary_limits_refuse_before_schema_rebuild(self):
        nested = []
        for _ in range(14):
            nested = [nested]
        for population in (nested, {str(i): 0 for i in range(4097)}):
            with self.assertRaises(BenchmarkError):
                contract(expected_keys=population)


class RecorderTests(unittest.TestCase):
    def recorder(self, clock=None):
        return WorkflowRecorder(contract(), run_id="fixture", paired_block_id="block-1", arm="software",
                                implementation_sha256=digest("a"),
                                clock_ns=clock or itertools.count(100, 10).__next__)

    def test_phase_measurements_and_unclassified_gaps(self):
        result = attempt()
        self.assertEqual(result["elapsed_ns"], 110)
        self.assertEqual(list(result["summary"]["phase_elapsed_ns"].values()), [10] * 5)
        self.assertEqual(result["summary"]["unclassified_elapsed_ns"], 60)
        self.assertIsNone(result["summary"]["meaningful_actions"])
        self.assertTrue(all(v is None for v in result["summary"]["human_activity_ns"].values()))
        self.assertIsNone(result["job_resources"])
        self.assertIsNone(result["cost_usd"])

    def test_explicit_measured_zero_differs_from_unknown(self):
        result = attempt(human=True)
        self.assertEqual(result["summary"]["meaningful_actions"], 0)
        self.assertEqual(result["summary"]["human_activity_ns"]["hands_on"], 0)
        self.assertEqual(result["summary"]["human_unclassified_elapsed_ns"], result["elapsed_ns"])

    def test_observed_activity_can_overlap_system_phase_without_double_counting(self):
        recorder = self.recorder()
        recorder.start_phase("acquisition")
        recorder.start_activity("hands_on")
        recorder.action("choose-site")
        recorder.end_activity("hands_on")
        recorder.start_activity("system_wait")
        recorder.end_activity("system_wait")
        recorder.incident("assistance", "explain-field")
        recorder.incident("failure", "input-missing")
        recorder.end_phase("acquisition")
        result = recorder.finish(status="failed", human_observation_complete=True)
        self.assertEqual(result["summary"]["human_activity_ns"],
                         {"hands_on": 20, "system_wait": 10, "interruption": 0})
        self.assertEqual(result["summary"]["meaningful_actions"], 1)
        self.assertEqual(result["summary"]["incidents"]["assistance"], 1)
        self.assertEqual(result["status"], "failed")

    def test_out_of_order_duplicate_and_overlapping_phases_refused(self):
        for initial, next_phase in ((None, "generation"), ("acquisition", "preparation"),
                                    ("acquisition", "acquisition")):
            recorder = self.recorder()
            if initial:
                recorder.start_phase(initial)
            with self.subTest(next_phase=next_phase), self.assertRaises(BenchmarkError):
                recorder.start_phase(next_phase)

    def test_unmatched_end_activity_overlap_and_duplicate_action_refused(self):
        recorder = self.recorder()
        with self.assertRaises(BenchmarkError):
            recorder.end_phase("acquisition")
        recorder.start_activity("hands_on")
        with self.assertRaises(BenchmarkError):
            recorder.start_activity("system_wait")
        with self.assertRaises(BenchmarkError):
            recorder.end_activity("interruption")
        recorder.action("submit")
        with self.assertRaises(BenchmarkError):
            recorder.action("submit")

    def test_open_incomplete_and_unexplained_failed_attempt_refused(self):
        recorder = self.recorder()
        with self.assertRaises(BenchmarkError):
            recorder.finish()
        with self.assertRaises(BenchmarkError):
            recorder.finish(status="failed")
        recorder.start_phase("acquisition")
        recorder.incident("failure", "failed")
        with self.assertRaises(BenchmarkError):
            recorder.finish(status="failed")

    def test_invalid_and_backwards_clocks_refused(self):
        for ticks in ([100, 99], [100, True], [100, -1], [100, math.inf]):
            recorder = self.recorder(iter(ticks).__next__)
            with self.subTest(ticks=ticks), self.assertRaises(BenchmarkError):
                recorder.start_phase("acquisition")

    def test_finished_recorder_cannot_be_reused_or_mutated_by_receipt(self):
        recorder = self.recorder()
        for phase in PHASES:
            recorder.start_phase(phase)
            recorder.end_phase(phase)
        result = recorder.finish()
        result["events"].clear()
        self.assertEqual(len(recorder._events), 10)
        with self.assertRaises(BenchmarkError):
            recorder.action("again")
        with self.assertRaises(BenchmarkError):
            recorder.finish()

    def test_observed_sessions_require_capture_and_system_clock(self):
        base = dict(contract=contract(), run_id="x", paired_block_id="block-1", arm="manual", implementation_sha256=digest("a"),
                    measurement_origin="observed-session")
        with self.assertRaises(BenchmarkError):
            WorkflowRecorder(**base)
        with self.assertRaises(BenchmarkError):
            WorkflowRecorder(**base, observation_record_sha256=digest("b"), clock_ns=lambda: 0)

    def test_actual_clock_records_in_process_fixture_only(self):
        recorder = WorkflowRecorder(contract(), run_id="system-clock-fixture", paired_block_id="block-1", arm="software",
                                    implementation_sha256=digest("a"))
        for phase in PHASES:
            recorder.start_phase(phase)
            recorder.end_phase(phase)
        result = recorder.finish()
        self.assertGreater(result["elapsed_ns"], 0)
        self.assertEqual(result["measurement_origin"], "synthetic-fixture")
        self.assertEqual(result["clock"], "system-monotonic-ns")

    def test_event_limit_refuses_additional_action_without_erasing_history(self):
        recorder = self.recorder()
        for index in range(512):
            recorder.action("action-" + str(index))
        with self.assertRaises(BenchmarkError):
            recorder.action("over-limit")
        self.assertEqual(len(recorder._events), 512)

    def test_external_resources_and_verification_are_strict(self):
        resources = {"measurement_sha256": digest("a"), "scope": "whole-job", "method": "cgroup-v2-counters",
                     "cpu_seconds": 0, "peak_rss_bytes": 2048, "read_bytes": None,
                     "write_bytes": None, "output_bytes": 100}
        result = attempt(job_resources=resources)
        self.assertEqual(result["job_resources"]["cpu_seconds"], 0)
        resources["scope"] = "one-process"
        with self.assertRaises(BenchmarkError):
            attempt(job_resources=resources)
        c = contract()
        wrong = verification(c)
        wrong["reference_sha256"] = digest("f")
        recorder = self.recorder()
        for phase in PHASES:
            recorder.start_phase(phase)
            recorder.end_phase(phase)
        with self.assertRaises(BenchmarkError):
            recorder.finish(verification=wrong)

    def test_invalid_resource_metrics_and_verification_count_refused(self):
        base = {"measurement_sha256": digest("a"), "scope": "whole-job", "method": "cgroup-v2-counters",
                "cpu_seconds": 0, "peak_rss_bytes": 2048, "read_bytes": None,
                "write_bytes": None, "output_bytes": 100}
        for field, value in (("cpu_seconds", True), ("cpu_seconds", math.nan), ("peak_rss_bytes", -1),
                             ("method", "sampled-process-rss")):
            with self.subTest(field=field, value=value), self.assertRaises(BenchmarkError):
                attempt(job_resources={**base, field: value})
        for field, value in (("observed_rows", 17), ("observed_rows", True), ("outcome", "exit-zero")):
            recorder = self.recorder()
            for phase in PHASES:
                recorder.start_phase(phase)
                recorder.end_phase(phase)
            with self.assertRaises(BenchmarkError):
                recorder.finish(verification={**verification(contract()), field: value})


class PairTests(unittest.TestCase):
    def test_synthetic_never_produces_elapsed_claim(self):
        c = contract()
        report = assess_pair(c, attempt(c), attempt(c, "software"))
        self.assertIsNone(report["observed_elapsed_ratios"])
        self.assertFalse(report["general_speedup_established"])
        self.assertEqual(report["measurement_origin"], "synthetic-fixture")
        self.assertIn("synthetic-manual", [b["code"] for b in report["blockers"]])

    def test_observed_declarations_allow_only_descriptive_elapsed_ratios(self):
        c = contract()
        left, right = attempt(c, observed=True, step=20), attempt(c, "software", observed=True)
        report = assess_pair(c, left, right)
        self.assertEqual(report["blockers"], [])
        self.assertEqual(report["observed_elapsed_ratios"]["total_elapsed_manual_over_software"], 2)
        self.assertIsNone(left["summary"]["meaningful_actions"])
        self.assertIsNone(right["job_resources"])
        self.assertFalse(report["scientific_qualification"])
        self.assertEqual(report["attempt_identity_sha256"],
                         {"manual": left["identity_sha256"], "software": right["identity_sha256"]})

    def test_changed_cache_resources_environment_and_workload_refuse_pair(self):
        c = contract()
        alternatives = (contract(cache_stratum="first-use"), contract(environment_sha256=digest("f")),
            contract(trial_manifest_sha256=digest("a")),
            contract(resources={"cpu_limit": 4, "memory_limit_bytes": 8 * 1024**3, "parallel_jobs": 1}),
            contract(scientific_identity={**c["scientific_identity"], "workload_sha256": digest("f")}))
        for other in alternatives:
            with self.subTest(other=other["identity_sha256"]):
                report = assess_pair(c, attempt(c, observed=True), attempt(other, "software", observed=True))
                self.assertEqual(report["blockers"][0]["code"], "invalid-software")

    def test_wrong_arm_self_comparison_missing_verification_and_mixed_evidence(self):
        c = contract()
        left = attempt(c, observed=True)
        cases = (left, attempt(c, "software", observed=True, verified=False), attempt(c, "software"))
        for right in cases:
            self.assertIsNone(assess_pair(c, left, right)["observed_elapsed_ratios"])

    def test_same_run_or_capture_and_zero_generation_refused(self):
        c = contract()
        left, right = attempt(c, observed=True), attempt(c, "software", observed=True)
        for field, value in (("run_id", left["run_id"]), ("paired_block_id", "another-block"),
                             ("observation_record_sha256", left["observation_record_sha256"])):
            edited = deepcopy(right)
            edited[field] = value
            self.assertIsNone(assess_pair(c, left, reseal(edited))["observed_elapsed_ratios"])
        self.assertIsNone(assess_pair(c, left, attempt(c, "software", observed=True, step=0))["observed_elapsed_ratios"])

    def test_reuse_can_compare_elapsed_but_never_generation(self):
        c = contract(cache_stratum="completed-result-reuse")
        left, right = attempt(c, observed=True), attempt(c, "software", observed=True)
        report = assess_pair(c, left, right)
        self.assertEqual(report["blockers"], [])
        self.assertIsNone(report["observed_elapsed_ratios"]["generation_elapsed_manual_over_software"])

    def test_failed_attempt_retained_and_never_an_eligible_pair(self):
        c = contract()
        with patch("ngen_reforecast.benchmarking.workflow.time.monotonic_ns", itertools.count(100, 10).__next__):
            recorder = WorkflowRecorder(c, run_id="failed-software", paired_block_id="block-1", arm="software",
                implementation_sha256=digest("b"), measurement_origin="observed-session",
                observation_record_sha256=digest("d"))
            recorder.start_phase("acquisition")
            recorder.incident("failure", "unavailable-input")
            recorder.end_phase("acquisition")
            failed = recorder.finish(status="failed")
        report = assess_pair(c, attempt(c, observed=True), failed)
        self.assertIn("failed-software", [b["code"] for b in report["blockers"]])
        self.assertIsNone(report["observed_elapsed_ratios"])
        self.assertEqual(failed["summary"]["incidents"]["failure"], 1)

    def test_tampering_and_malformed_events_return_actionable_blocker(self):
        c = contract()
        good = attempt(c, "software", observed=True)
        for bad in ([], True, {"identity_sha256": digest("a")}):
            self.assertEqual(assess_pair(c, attempt(c), bad)["blockers"][0]["code"], "invalid-software")
        for name, value in (("event", []), ("at_ns", True), ("at_ns", -1), ("at_ns", 10000)):
            bad = deepcopy(good)
            bad["events"][0][name] = value
            report = assess_pair(c, attempt(c), reseal(bad))
            self.assertTrue(report["blockers"][0]["action"])
        bad = deepcopy(good)
        bad["elapsed_ns"] += 1
        self.assertIsNone(assess_pair(c, attempt(c), bad)["observed_elapsed_ratios"])

    def test_boolean_summary_is_not_equal_to_measured_zero(self):
        c = contract()
        bad = attempt(c, "software", observed=True, human=True)
        bad["summary"]["meaningful_actions"] = False
        report = assess_pair(c, attempt(c, observed=True), reseal(bad))
        self.assertEqual(report["blockers"][0]["code"], "invalid-software")


class FixtureTests(unittest.TestCase):
    def test_row_order_determinism_and_inputs_unchanged(self):
        reference, candidate = rows(), list(reversed(rows()))
        before = deepcopy([reference, candidate])
        result = compare_fixture_rows(contract(), reference, candidate)
        self.assertTrue(result["passed"])
        self.assertEqual(result, compare_fixture_rows(contract(), candidate, reference))
        self.assertEqual(before, [reference, candidate])
        self.assertEqual(result["measurement_origin"], "synthetic-fixture")
        self.assertFalse(result["scientific_qualification"])
        changed = compare_fixture_rows(contract(), rows(3), rows(3))
        self.assertNotEqual(result["identity_sha256"], changed["identity_sha256"])

    def test_each_input_digest_tracks_only_that_canonical_input(self):
        original = compare_fixture_rows(contract(), rows(), rows())
        changed = compare_fixture_rows(contract(), rows(), rows(3))
        self.assertEqual(original["reference_content_sha256"], changed["reference_content_sha256"])
        self.assertNotEqual(original["candidate_content_sha256"], changed["candidate_content_sha256"])

    def test_missing_duplicate_extra_shifted_and_wrong_unit_refused(self):
        candidates = [rows()[:-1], rows() + [rows()[0]]]
        duplicate, shifted, unit = rows(), rows(), rows()
        duplicate[0] = deepcopy(duplicate[1])
        shifted[0]["key"][3] = "2022-01-02T02:00:00Z"
        unit[0]["unit"] = "cfs"
        candidates.extend([duplicate, shifted, unit])
        for candidate in candidates:
            with self.assertRaises(BenchmarkError):
                compare_fixture_rows(contract(), rows(), candidate)

    def test_bool_nan_infinity_and_negative_flow_refused(self):
        for value in (True, math.nan, math.inf, -1):
            with self.subTest(value=value), self.assertRaises(BenchmarkError):
                compare_fixture_rows(contract(), rows(), rows(value))

    def test_frozen_symmetric_max_tolerance_and_near_zero(self):
        c = contract()
        self.assertTrue(compare_fixture_rows(c, rows(0), rows(1e-6))["passed"])
        self.assertFalse(compare_fixture_rows(c, rows(0), rows(math.nextafter(1e-6, math.inf)))["passed"])
        # Relative limit is based on the larger magnitude, symmetrically.
        high, low = 1000.0, 999.99
        self.assertTrue(compare_fixture_rows(c, rows(high), rows(low))["passed"])
        self.assertTrue(compare_fixture_rows(c, rows(low), rows(high))["passed"])
        # Difference 0.0000105 exceeds max(1e-6, ~1e-5), but would pass an additive rule.
        self.assertFalse(compare_fixture_rows(c, rows(1), rows(1.0000105))["passed"])


if __name__ == "__main__":
    unittest.main()
