"""Inert dispatch envelopes and declared results; no work is dispatched."""

from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from ngen_reforecast.preparation import RequestPreparationError, normalize_request
from ngen_reforecast.preparation import dispatch as api
from ngen_reforecast.preparation.journal import (
    apply_receipt_revision, resume_preparation_journal,
    seal_receipt_revision, start_preparation_journal,
)
from ngen_reforecast.preparation.orchestration import (
    _hash, checkpoint_preparation, plan_preparation, seal_task_receipts,
)


BASE = {"identifier_type": "usgs", "identifier": "03479000", "mode": "reforecast",
        "start_date": "2022-01-01", "end_date": "2022-01-01",
        "start_hour_utc": 1, "end_hour_utc": 6, "max_lead_hours": 6}
ORIGIN = "2022-01-01T00:00:00Z"
DIGEST = hashlib.sha256(b"inert dispatch outcome; no artifact read").hexdigest()


def plan(*, issues_per_task=2, origin=ORIGIN, **changes):
    return plan_preparation(normalize_request({**BASE, **changes}), origin_time_utc=origin,
                            issues_per_task=issues_per_task)


def record(index, state="passed"):
    return {"task_index": index, "check_state": state,
            "evidence": None if state == "unknown" else {
                "artifact_sha256": DIGEST, "evidence_class": "synthetic",
                "detail": "Inert caller declaration; no source qualification."}}


def journal_with(original, states=()):
    receipts = seal_task_receipts(original, [record(index, state) for index, state in states])
    return start_preparation_journal(original, checkpoint_preparation(original, receipts))


def outcome(index, state="passed"):
    return {**record(index, state), "reason": "Synthetic result replaces the explicitly selected declaration."}


def apply(original, journal, revision):
    return apply_receipt_revision(original, journal, revision,
                                  expected_journal_identity_sha256=journal["journal_identity_sha256"])


class PreparationDispatchTests(unittest.TestCase):
    def assert_error(self, call, code):
        with self.assertRaises(RequestPreparationError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)
        self.assertTrue(caught.exception.field)

    def assert_inert(self, result):
        for flag in ("dispatch_supported", "execution_ready", "artifacts_reverified",
                     "source_coverage_qualified", "physical_recovery_established"):
            self.assertIs(result[flag], False)
        self.assertTrue(all(value == 0 for value in result["resource_use"].values()))

    def test_history_only_selection_binds_original_complete_scope(self):
        original = plan()
        journal = start_preparation_journal(original)
        result = api.plan_preparation_dispatch(original, journal)
        self.assertEqual([task["task_index"] for task in result["selected_tasks"]], [0])
        self.assertEqual(result["preparation_binding"], original["preparation_binding"])
        self.assertEqual(result["selected_tasks"][0]["history_interval"],
                         original["tasks"][0]["history_interval"])
        self.assertEqual(result["journal_identity_sha256"], journal["journal_identity_sha256"])
        self.assertEqual(result["revision_head_sha256"], journal["revision_head_sha256"])
        self.assertIsNone(result["selected_tasks"][0]["expected_receipt_sha256"])
        self.assertFalse(result["history_precondition"]["satisfied_by_declaration"])
        self.assertEqual(result["bounds"]["selected_forecast_issue_count"], 0)
        self.assertEqual(result["bounds"]["max_parallel_tasks"], 1)
        self.assert_inert(result)

    def test_unknown_missing_failed_history_do_not_unlock_forecast_checks(self):
        original = plan()
        for state in ("unknown", "missing", "failed"):
            journal = journal_with(original, [(0, state), (1, "passed")])
            result = api.plan_preparation_dispatch(original, journal)
            self.assertEqual([task["task_index"] for task in result["selected_tasks"]], [0])
            self.assertEqual(result["history_precondition"]["declared_check_state"], state)
            self.assertFalse(result["history_precondition"]["scientific_qualification_established"])

    def test_history_pass_orders_pending_forecasts_without_qualifying_history(self):
        original = plan()
        journal = journal_with(original, [(0, "passed"), (1, "passed")])
        result = api.plan_preparation_dispatch(original, journal)
        self.assertEqual([task["task_index"] for task in result["selected_tasks"]], [2])
        self.assertTrue(result["history_precondition"]["satisfied_by_declaration"])
        self.assertFalse(result["history_precondition"]["artifact_reverified"])
        self.assertEqual(result["bounds"]["selected_task_count"], 1)
        self.assertEqual(result["bounds"]["selected_forecast_issue_count"], 2)
        self.assertEqual(result["preparation_binding"]["scope"]["required_source_leads"], {"min": 1, "max": 18})
        self.assert_inert(result)

    def test_superseded_history_state_controls_selection_in_both_directions(self):
        original = plan()
        journal = journal_with(original, [(0, "passed"), (1, "passed")])
        self.assertEqual(api.plan_preparation_dispatch(original, journal)["selected_tasks"][0]["task_index"], 2)
        prior = resume_preparation_journal(original, journal)["current_task_receipts"][0]
        revision = seal_receipt_revision(original, journal, [{**outcome(0, "failed"), "expected_receipt_sha256": prior["receipt_identity_sha256"]}])
        changed = apply(original, journal, revision)
        envelope = api.plan_preparation_dispatch(original, changed)
        self.assertEqual([task["task_index"] for task in envelope["selected_tasks"]], [0])
        self.assertEqual(envelope["history_precondition"]["declared_check_state"], "failed")
        failed = resume_preparation_journal(original, changed)["current_task_receipts"][0]
        revision = seal_receipt_revision(original, changed, [{**outcome(0), "expected_receipt_sha256": failed["receipt_identity_sha256"]}])
        restored = apply(original, changed, revision)
        self.assertEqual(api.plan_preparation_dispatch(original, restored)["selected_tasks"][0]["task_index"], 2)

    def test_revision_capacity_refuses_pending_work_but_never_manufactures_work(self):
        original = plan()
        journal = start_preparation_journal(original)
        revision = seal_receipt_revision(original, journal, [{**outcome(0, "failed"), "expected_receipt_sha256": None}])
        journal = apply(original, journal, revision)
        before = deepcopy(journal)
        with patch.object(api, "MAX_REVISIONS", 1):
            self.assert_error(lambda: api.plan_preparation_dispatch(original, journal), "PREPARATION_DISPATCH_CAPACITY_EXCEEDED")
        self.assertEqual(journal, before)
        complete = journal_with(original, [(index, "passed") for index in range(len(original["tasks"]))])
        prior = resume_preparation_journal(original, complete)["current_task_receipts"][0]
        changed_evidence = outcome(0)
        changed_evidence["evidence"]["detail"] = "Different inert declared evidence; no source verification"
        revision = seal_receipt_revision(original, complete, [{**changed_evidence, "expected_receipt_sha256": prior["receipt_identity_sha256"]}])
        complete = apply(original, complete, revision)
        with patch.object(api, "MAX_REVISIONS", 1):
            envelope = api.plan_preparation_dispatch(original, complete)
            self.assertEqual(envelope["status"], "no_pending_checks")
            self.assertEqual(envelope["selected_tasks"], [])
            self.assert_inert(envelope)

    def test_independent_task_and_issue_bounds_never_split_or_skip_tasks(self):
        original = plan(issues_per_task=1)
        journal = journal_with(original, [(0, "passed"), (2, "passed")])
        result = api.plan_preparation_dispatch(original, journal)
        self.assertEqual([task["task_index"] for task in result["selected_tasks"]], [1, 3])
        self.assertEqual(result["bounds"]["selected_forecast_issue_count"], 2)
        bounded = api.plan_preparation_dispatch(original, journal, max_tasks=1)
        self.assertEqual([task["task_index"] for task in bounded["selected_tasks"]], [1])
        partial = plan(end_hour_utc=5)
        result = api.plan_preparation_dispatch(partial, journal_with(partial, [(0, "passed"), (1, "passed"), (2, "passed")]))
        self.assertEqual(result["selected_tasks"][0]["issues_utc"], ["2022-01-01T05:00:00Z"])
        self.assertEqual(result["bounds"]["selected_forecast_issue_count"], 1)

    def test_invalid_task_bounds_refuse_without_changing_journal(self):
        original = plan()
        journal = start_preparation_journal(original)
        before = deepcopy(journal)
        for maximum in (0, 3, True, 1.0, "2", None):
            self.assert_error(lambda: api.plan_preparation_dispatch(original, journal, max_tasks=maximum),
                              "INVALID_PREPARATION_DISPATCH_BOUNDS")
        self.assertEqual(journal, before)

    def test_all_declared_passes_produce_an_inert_empty_envelope(self):
        original = plan()
        journal = journal_with(original, [(index, "passed") for index in range(len(original["tasks"]))])
        result = api.plan_preparation_dispatch(original, journal)
        self.assertEqual(result["status"], "no_pending_checks")
        self.assertEqual(result["selected_tasks"], [])
        self.assert_inert(result)
        self.assert_error(lambda: api.seal_dispatch_result(original, journal, result, []),
                          "NO_PREPARATION_DISPATCH_TASKS")
        self.assertEqual(journal["revision_count"], 0)

    def test_candidate_result_is_stable_for_reordered_exact_selected_outcomes(self):
        original = plan(issues_per_task=1)
        journal = journal_with(original, [(0, "passed")])
        envelope = api.plan_preparation_dispatch(original, journal)
        first = api.seal_dispatch_result(original, journal, envelope, [outcome(1), outcome(2, "failed")])
        second = api.seal_dispatch_result(original, journal, envelope, [outcome(2, "failed"), outcome(1)])
        self.assertEqual(first, second)
        self.assertEqual(first["based_on_journal_identity_sha256"], journal["journal_identity_sha256"])
        self.assertEqual(first["dispatch_identity_sha256"], envelope["dispatch_identity_sha256"])
        self.assertEqual([item["task_index"] for item in first["receipt_revision"]["updates"]], [1, 2])
        self.assertEqual(journal["revision_count"], 0)
        self.assert_inert(first)

    def test_candidate_uses_exact_prior_receipt_and_preserves_earlier_evidence(self):
        original = plan()
        journal = journal_with(original, [(0, "failed")])
        before = deepcopy(journal)
        envelope = api.plan_preparation_dispatch(original, journal)
        candidate = api.seal_dispatch_result(original, journal, envelope, [outcome(0)])
        prior = journal["base_checkpoint"]["receipts"][0]
        self.assertEqual(candidate["receipt_revision"]["updates"][0]["expected_receipt_sha256"], prior["receipt_identity_sha256"])
        updated = apply(original, journal, candidate["receipt_revision"])
        self.assertEqual(journal, before)
        self.assertEqual(updated["base_checkpoint"], before["base_checkpoint"])
        resumed = resume_preparation_journal(original, updated)
        self.assertEqual(resumed["current_task_receipts"][0]["check_state"], "passed")
        self.assertFalse(resumed["artifacts_reverified"] or resumed["source_coverage_qualified"])

    def test_concurrent_candidates_refuse_stale_apply_and_exact_replay_is_idempotent(self):
        original = plan()
        journal = start_preparation_journal(original)
        envelope = api.plan_preparation_dispatch(original, journal)
        first = api.seal_dispatch_result(original, journal, envelope, [outcome(0)])
        competing = api.seal_dispatch_result(original, journal, envelope, [outcome(0, "failed")])
        updated = apply(original, journal, first["receipt_revision"])
        self.assertEqual(apply(original, updated, first["receipt_revision"]), updated)
        self.assert_error(lambda: apply(original, updated, competing["receipt_revision"]), "STALE_RECEIPT_REVISION")
        self.assert_error(lambda: api.seal_dispatch_result(original, updated, envelope, [outcome(0)]),
                          "STALE_PREPARATION_DISPATCH")

    def test_any_journal_change_invalidates_old_envelope_even_for_another_task(self):
        original = plan()
        journal = start_preparation_journal(original)
        envelope = api.plan_preparation_dispatch(original, journal)
        revision = seal_receipt_revision(original, journal, [
            {**outcome(2, "failed"), "expected_receipt_sha256": None}])
        updated = apply(original, journal, revision)
        self.assert_error(lambda: api.seal_dispatch_result(original, updated, envelope, [outcome(0)]),
                          "STALE_PREPARATION_DISPATCH")
        self.assertEqual(journal["revision_count"], 0)

    def test_foreign_site_origin_retention_and_batch_policy_envelopes_refuse(self):
        original = plan()
        envelope = api.plan_preparation_dispatch(original, start_preparation_journal(original))
        for foreign in (plan(identifier="99999999"), plan(origin="2021-12-31T23:00:00Z"),
                        plan(max_lead_hours=18), plan(issues_per_task=1)):
            self.assert_error(lambda: api.seal_dispatch_result(foreign, start_preparation_journal(foreign), envelope, [outcome(0)]),
                              "PREPARATION_DISPATCH_SCOPE_MISMATCH")

    def test_resealed_tampered_envelopes_do_not_change_selection_or_capability(self):
        original = plan()
        journal = start_preparation_journal(original)
        envelope = api.plan_preparation_dispatch(original, journal)
        mutations = (
            lambda value: value["selected_tasks"].clear(),
            lambda value: value["selected_tasks"][0].update(expected_receipt_sha256="0" * 64),
            lambda value: value["preparation_binding"]["scope"]["required_history_interval"].update(start_time_utc="2021-12-31T00:00:00Z"),
            lambda value: value["history_precondition"].update(satisfied_by_declaration=True),
            lambda value: value["bounds"].update(max_selected_forecast_issues=3),
            lambda value: value["resource_use"].update(model_calls=1),
            lambda value: value.update(dispatch_supported=True),
            lambda value: value.update(extra="not supported"),
        )
        for mutate in mutations:
            changed = deepcopy(envelope)
            mutate(changed)
            changed["dispatch_identity_sha256"] = _hash({key: value for key, value in changed.items() if key != "dispatch_identity_sha256"})
            self.assert_error(lambda: api.seal_dispatch_result(original, journal, changed, [outcome(0)]),
                              "PREPARATION_DISPATCH_MISMATCH")

    def test_outcomes_require_exact_selected_population_without_duplicates(self):
        original = plan(issues_per_task=1)
        journal = journal_with(original, [(0, "passed")])
        envelope = api.plan_preparation_dispatch(original, journal)
        for outcomes in ([], [outcome(1)], [outcome(1), outcome(2), outcome(3)],
                         [outcome(1), outcome(1)], [outcome(1), outcome(3)],
                         [outcome(True), outcome(2)], [{**outcome(1), "expected_receipt_sha256": None}, outcome(2)]):
            self.assert_error(lambda: api.seal_dispatch_result(original, journal, envelope, outcomes),
                              "INVALID_PREPARATION_DISPATCH_OUTCOMES")
        self.assertEqual(journal["revision_count"], 0)

    def test_outcome_evidence_and_reason_are_checked_by_the_journal_contract(self):
        original = plan()
        journal = start_preparation_journal(original)
        envelope = api.plan_preparation_dispatch(original, journal)
        invalid_state = outcome(0, "complete")
        self.assert_error(lambda: api.seal_dispatch_result(original, journal, envelope, [invalid_state]), "INVALID_TASK_RECEIPT")
        self.assert_error(lambda: api.seal_dispatch_result(original, journal, envelope, [{**outcome(0), "reason": " "}]),
                          "INVALID_RECEIPT_REVISION")
        unknown_with_evidence = {**outcome(0, "unknown"), "evidence": record(0)["evidence"]}
        self.assert_error(lambda: api.seal_dispatch_result(original, journal, envelope, [unknown_with_evidence]), "INVALID_TASK_RECEIPT")

    def test_failed_result_stays_pending_and_next_envelope_binds_replacement_identity(self):
        original = plan()
        journal = start_preparation_journal(original)
        envelope = api.plan_preparation_dispatch(original, journal)
        candidate = api.seal_dispatch_result(original, journal, envelope, [outcome(0, "failed")])
        updated = apply(original, journal, candidate["receipt_revision"])
        next_envelope = api.plan_preparation_dispatch(original, updated)
        self.assertEqual([task["task_index"] for task in next_envelope["selected_tasks"]], [0])
        self.assertEqual(next_envelope["selected_tasks"][0]["expected_receipt_sha256"],
                         candidate["receipt_revision"]["updates"][0]["receipt"]["receipt_identity_sha256"])
        self.assertNotEqual(envelope["dispatch_identity_sha256"], next_envelope["dispatch_identity_sha256"])

    def test_detached_json_round_trip_never_changes_source_objects(self):
        original = plan()
        journal = start_preparation_journal(original)
        before = deepcopy((original, journal))
        envelope = api.plan_preparation_dispatch(original, journal)
        outcomes = [outcome(0)]
        candidate = api.seal_dispatch_result(original, journal, json.loads(json.dumps(envelope)), outcomes)
        outcomes[0]["evidence"]["detail"] = "changed after sealing"
        self.assertNotEqual(candidate["receipt_revision"]["updates"][0]["receipt"]["evidence"]["detail"], outcomes[0]["evidence"]["detail"])
        envelope["preparation_binding"]["scope"]["required_history_interval"]["start_time_utc"] = "modified"
        self.assertEqual((original, journal), before)
        self.assertEqual(candidate, json.loads(json.dumps(candidate)))

    def test_unsafe_nonjson_envelopes_refuse_before_result_sealing(self):
        original = plan()
        journal = start_preparation_journal(original)
        for value in (object(), {"constructor": 1}, {1: "bad"}):
            self.assert_error(lambda: api.seal_dispatch_result(original, journal, value, [outcome(0)]),
                              "INVALID_ORCHESTRATION_ARTIFACT")

    def test_public_functions_read_only_policy_and_never_invoke_work(self):
        original = plan()
        journal = start_preparation_journal(original)
        forbidden = ("subprocess.run", "subprocess.Popen", "socket.create_connection", "urllib.request.urlopen",
                     "ngen_reforecast.execution.execute_campaign", "ngen_reforecast.execution.preflight_execution",
                     "ngen_reforecast.archive.verify_result", "ngen_reforecast.archive.export_result",
                     "ngen_reforecast.preparation.forcing_adapter.check_forcing_preparation", "builtins.open")
        policy = Path(__file__).absolute().parents[1] / "src/ngen_reforecast/preparation/request-policy.json"
        original_open = Path.open
        opened = []

        def policy_only(path, *args, **kwargs):
            self.assertEqual(path.absolute(), policy)
            self.assertNotIn("w", args[0] if args else kwargs.get("mode", "r"))
            opened.append(path)
            return original_open(path, *args, **kwargs)

        with ExitStack() as stack:
            for target in forbidden:
                stack.enter_context(patch(target, side_effect=AssertionError(f"Forbidden operation: {target}")))
            stack.enter_context(patch.object(Path, "open", policy_only))
            envelope = api.plan_preparation_dispatch(original, journal)
            result = api.seal_dispatch_result(original, journal, envelope, [outcome(0)])
            self.assert_inert(envelope)
            self.assert_inert(result)
        self.assertTrue(opened)


class PreparationDispatchAnnualTests(unittest.TestCase):
    def test_annual_plan_remains_complete_while_envelope_and_result_are_bounded(self):
        original = plan(start_date="2022-01-01", end_date="2022-12-31", start_hour_utc=0,
                        end_hour_utc=23, origin="2021-12-01T00:00:00Z")
        journal = journal_with(original, [(0, "passed")])
        envelope = api.plan_preparation_dispatch(original, journal)
        candidate = api.seal_dispatch_result(original, journal, envelope, [outcome(1)])
        self.assertEqual(len(original["requested_population"]["issues_utc"]), 8760)
        self.assertEqual(len(original["tasks"]), 4381)
        self.assertEqual(envelope["preparation_binding"], original["preparation_binding"])
        self.assertEqual(envelope["preparation_binding"]["scope"]["required_history_interval"]["stop_time_utc_exclusive"], "2023-01-01T17:00:00Z")
        self.assertEqual(envelope["preparation_binding"]["scope"]["initialization_origin_utc"], "2021-12-01T00:00:00Z")
        self.assertEqual([task["task_index"] for task in envelope["selected_tasks"]], [1])
        self.assertEqual(envelope["bounds"]["selected_forecast_issue_count"], 2)
        self.assertEqual(candidate["plan_identity_sha256"], original["plan_identity_sha256"])
        self.assertEqual(journal["revision_count"], 0)
        self.assertFalse(candidate["dispatch_supported"] or candidate["source_coverage_qualified"])
        self.assertEqual(candidate["resource_use"]["task_dispatches_performed"], 0)


if __name__ == "__main__":
    unittest.main()
