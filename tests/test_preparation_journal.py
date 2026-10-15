"""Synthetic declaration supersession; no stored data or physical recovery."""

from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from ngen_reforecast.preparation import RequestPreparationError, normalize_request
from ngen_reforecast.preparation import orchestration as old
from ngen_reforecast.preparation import journal as api
from test_preparation_orchestration import BASE, ORIGIN, plan, record


def update(index, state="passed", *, expected=None, reason="Explicit synthetic recheck declaration"):
    return {**record(index, state), "expected_receipt_sha256": expected, "reason": reason}


def apply(study, journal, revision):
    return api.apply_receipt_revision(study, journal, revision, expected_journal_identity_sha256=journal["journal_identity_sha256"])


def reseal(value, identity):
    value[identity] = old._hash({key: item for key, item in value.items() if key != identity})
    return value


class PreparationJournalTests(unittest.TestCase):
    def setUp(self):
        self.plan = plan()
        self.journal = api.start_preparation_journal(self.plan)

    def assert_error(self, call, code):
        with self.assertRaises(RequestPreparationError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)
        self.assertTrue(caught.exception.field)

    def active(self, journal):
        return api.resume_preparation_journal(self.plan, journal)["current_task_receipts"]

    def test_original_checkpoint_preserved_when_failed_becomes_passed(self):
        failed = old.seal_task_receipts(self.plan, [record(1, "failed")])
        checkpoint = old.checkpoint_preparation(self.plan, failed)
        before = deepcopy(checkpoint)
        journal = api.start_preparation_journal(self.plan, checkpoint)
        revision = api.seal_receipt_revision(self.plan, journal, [update(1, expected=failed[0]["receipt_identity_sha256"])])
        changed = apply(self.plan, journal, revision)
        self.assertEqual(changed["base_checkpoint"], before)
        self.assertEqual(checkpoint, before)
        self.assertEqual(journal["revisions"], [])
        self.assertEqual(self.active(changed)[0]["check_state"], "passed")
        self.assertEqual(changed["revisions"][0], revision)
        self.assertEqual(changed["revision_count"], 1)

    def test_pass_can_be_explicitly_invalidated_to_failed_or_unknown(self):
        passed = old.seal_task_receipts(self.plan, [record(0)])
        journal = api.start_preparation_journal(self.plan, old.checkpoint_preparation(self.plan, passed))
        for state in ("failed", "unknown"):
            with self.subTest(state=state):
                revision = api.seal_receipt_revision(self.plan, journal, [update(0, state, expected=passed[0]["receipt_identity_sha256"])])
                changed = apply(self.plan, journal, revision)
                result = api.resume_preparation_journal(self.plan, changed)
                self.assertEqual(result["current_task_receipts"][0]["check_state"], state)
                self.assertIn(self.plan["tasks"][0]["task_identity_sha256"], result["pending_check_task_ids"])

    def test_unknown_receipt_has_identity_and_is_not_unrecorded(self):
        unknown = old.seal_task_receipts(self.plan, [record(0, "unknown")])
        journal = api.start_preparation_journal(self.plan, old.checkpoint_preparation(self.plan, unknown))
        self.assert_error(lambda: api.seal_receipt_revision(self.plan, journal, [update(0)]), "STALE_TASK_RECEIPT")
        revision = api.seal_receipt_revision(self.plan, journal, [update(0, expected=unknown[0]["receipt_identity_sha256"])])
        self.assertEqual(self.active(apply(self.plan, journal, revision))[0]["check_state"], "passed")

    def test_exact_operation_replay_is_idempotent_even_after_later_revisions(self):
        first = api.seal_receipt_revision(self.plan, self.journal, [update(0)])
        journal = apply(self.plan, self.journal, first)
        second = api.seal_receipt_revision(self.plan, journal, [update(1)])
        journal = apply(self.plan, journal, second)
        self.assertEqual(apply(self.plan, journal, first), journal)
        self.assertEqual(apply(self.plan, journal, second), journal)
        changed = deepcopy(first); changed["updates"][0]["reason"] = "changed"
        self.assert_error(lambda: apply(self.plan, journal, changed), "RECEIPT_REVISION_IDENTITY_MISMATCH")

    def test_sibling_branch_and_numeric_revision_alone_do_not_authorize_merge(self):
        left = api.seal_receipt_revision(self.plan, self.journal, [update(0)])
        right = api.seal_receipt_revision(self.plan, self.journal, [update(1)])
        journal = apply(self.plan, self.journal, left)
        self.assert_error(lambda: apply(self.plan, journal, right), "STALE_RECEIPT_REVISION")
        changed = reseal({**right, "revision_index": 2}, "revision_identity_sha256")
        self.assert_error(lambda: apply(self.plan, journal, changed), "STALE_RECEIPT_REVISION")

    def test_stale_external_anchor_refuses_historical_journal_input(self):
        revision = api.seal_receipt_revision(self.plan, self.journal, [update(0)])
        current = apply(self.plan, self.journal, revision)
        self.assert_error(lambda: api.apply_receipt_revision(self.plan, self.journal, revision,
                         expected_journal_identity_sha256=current["journal_identity_sha256"]), "STALE_PREPARATION_JOURNAL")
        for anchor in (None, [], 1, "0" * 64):
            self.assert_error(lambda: api.apply_receipt_revision(self.plan, self.journal, revision,
                             expected_journal_identity_sha256=anchor), "STALE_PREPARATION_JOURNAL")

    def test_two_task_update_is_atomic_and_order_is_deterministic(self):
        records = [update(1), update(0)]
        first = api.seal_receipt_revision(self.plan, self.journal, records)
        self.assertEqual(first, api.seal_receipt_revision(self.plan, self.journal, list(reversed(records))))
        self.assertEqual([item["task_index"] for item in first["updates"]], [0, 1])
        changed = apply(self.plan, self.journal, first)
        self.assertEqual(len(self.active(changed)), 2)
        before = deepcopy(self.journal)
        self.assert_error(lambda: api.seal_receipt_revision(self.plan, self.journal, [update(0), update(1, expected="0" * 64)]), "STALE_TASK_RECEIPT")
        self.assertEqual(self.journal, before)

    def test_duplicate_task_and_no_op_replacement_refuse(self):
        self.assert_error(lambda: api.seal_receipt_revision(self.plan, self.journal, [update(0), update(0)]), "DUPLICATE_REVISION_TASK")
        revision = api.seal_receipt_revision(self.plan, self.journal, [update(0)])
        journal = apply(self.plan, self.journal, revision)
        active = self.active(journal)[0]
        self.assert_error(lambda: api.seal_receipt_revision(self.plan, journal, [update(0, expected=active["receipt_identity_sha256"])]), "RECEIPT_REVISION_NO_CHANGE")

    def test_changed_evidence_same_state_is_explicit_new_revision(self):
        first = api.seal_receipt_revision(self.plan, self.journal, [update(0)])
        journal = apply(self.plan, self.journal, first)
        record = update(0, expected=self.active(journal)[0]["receipt_identity_sha256"])
        record["evidence"]["detail"] = "A different explicitly declared synthetic observation"
        second = api.seal_receipt_revision(self.plan, journal, [record])
        self.assertNotEqual(first["revision_identity_sha256"], second["revision_identity_sha256"])
        self.assertEqual(apply(self.plan, journal, second)["revision_count"], 2)

    def test_foreign_plan_and_wrong_task_bindings_refuse(self):
        foreign = plan(identifier="99999999")
        revision = api.seal_receipt_revision(foreign, api.start_preparation_journal(foreign), [update(0)])
        self.assert_error(lambda: apply(self.plan, self.journal, revision), "RECEIPT_REVISION_SCOPE_MISMATCH")
        revision = api.seal_receipt_revision(self.plan, self.journal, [update(0)])
        revision["updates"][0]["task_index"] = 1
        reseal(revision, "revision_identity_sha256")
        self.assert_error(lambda: apply(self.plan, self.journal, revision), "RECEIPT_REVISION_SCOPE_MISMATCH")

    def test_reordered_dropped_or_gapped_history_refuses(self):
        first = api.seal_receipt_revision(self.plan, self.journal, [update(0)])
        journal = apply(self.plan, self.journal, first)
        second = api.seal_receipt_revision(self.plan, journal, [update(1)])
        journal = apply(self.plan, journal, second)
        for revisions in ([second, first], [second]):
            changed = {**journal, "revisions": revisions, "revision_count": len(revisions)}
            self.assert_error(lambda: api.resume_preparation_journal(self.plan, changed), "STALE_RECEIPT_REVISION")
        changed = deepcopy(first); changed["revision_index"] = 2
        reseal(changed, "revision_identity_sha256")
        self.assert_error(lambda: apply(self.plan, self.journal, changed), "STALE_RECEIPT_REVISION")

    def test_corrupt_base_flags_head_count_or_outer_identity_refuses(self):
        for key, value in (("execution_ready", True), ("revision_head_sha256", "0" * 64),
                           ("journal_identity_sha256", "0" * 64), ("revision_count", False),
                           ("revision_count", 0.0), ("unexpected", True)):
            changed = {**self.journal, key: value}
            self.assert_error(lambda: api.resume_preparation_journal(self.plan, changed), "PREPARATION_JOURNAL_MISMATCH")
        changed = deepcopy(self.journal); changed["base_checkpoint"]["execution_ready"] = True
        self.assert_error(lambda: api.resume_preparation_journal(self.plan, changed), "PREPARATION_CHECKPOINT_MISMATCH")
        self.assert_error(lambda: api.resume_preparation_journal(self.plan, {}), "INVALID_PREPARATION_JOURNAL")

    def test_replacing_base_checkpoint_does_not_reparent_existing_history(self):
        revision = api.seal_receipt_revision(self.plan, self.journal, [update(0)])
        journal = apply(self.plan, self.journal, revision)
        journal["base_checkpoint"] = old.checkpoint_preparation(self.plan, old.seal_task_receipts(self.plan, [record(1)]))
        self.assert_error(lambda: api.resume_preparation_journal(self.plan, journal), "STALE_RECEIPT_REVISION")

    def test_strict_bounded_record_reason_and_revision_schema(self):
        self.assert_error(lambda: api.seal_receipt_revision(self.plan, self.journal, []), "RECEIPT_REVISION_LIMIT_EXCEEDED")
        self.assert_error(lambda: api.seal_receipt_revision(self.plan, self.journal, [update(0)] * 3), "RECEIPT_REVISION_LIMIT_EXCEEDED")
        self.assert_error(lambda: api.seal_receipt_revision(self.plan, self.journal, [{**update(0), "extra": 1}]), "INVALID_RECEIPT_REVISION")
        for reason in (None, " ", "x" * 513):
            self.assert_error(lambda: api.seal_receipt_revision(self.plan, self.journal, [update(0, reason=reason)]), "INVALID_RECEIPT_REVISION")
        self.assert_error(lambda: api.seal_receipt_revision(self.plan, self.journal, [update(0, expected="bad")]), "INVALID_RECEIPT_REVISION")
        revision = api.seal_receipt_revision(self.plan, self.journal, [update(0)])
        self.assert_error(lambda: apply(self.plan, self.journal, {**revision, "extra": 1}), "INVALID_RECEIPT_REVISION")

    def test_explicit_revision_limit_preserves_history_and_allows_replay(self):
        with patch.object(api, "MAX_REVISIONS", 2):
            first = api.seal_receipt_revision(self.plan, self.journal, [update(0)])
            journal = apply(self.plan, self.journal, first)
            second = api.seal_receipt_revision(self.plan, journal, [update(1)])
            journal = apply(self.plan, journal, second)
            before = deepcopy(journal)
            self.assert_error(lambda: api.seal_receipt_revision(self.plan, journal, [update(2)]), "RECEIPT_REVISION_LIMIT_EXCEEDED")
            self.assertEqual(apply(self.plan, journal, first), before)
            self.assertEqual(journal, before)

    def test_full_artifact_bound_refuses_append_without_compaction(self):
        journal = self.journal
        for index in range(6):
            current = self.active(journal)
            expected = current[0]["receipt_identity_sha256"] if current else None
            revision = api.seal_receipt_revision(self.plan, journal, [update(0, "passed" if index % 2 == 0 else "failed", expected=expected)])
            journal = apply(self.plan, journal, revision)
        limit = max(len(old._json_text(journal).encode()), len(old._json_text(self.plan).encode())) + 20
        before = deepcopy(journal)
        with patch.object(old, "MAX_ARTIFACT_BYTES", limit):
            self.assert_error(lambda: api.seal_receipt_revision(self.plan, journal, [update(1)]), "ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED")
        self.assertEqual(journal, before)

    def test_round_trip_and_detached_output_preserve_all_evidence(self):
        records = [update(0)]
        revision = api.seal_receipt_revision(self.plan, self.journal, records)
        records[0]["reason"] = "changed caller object"
        self.assertNotEqual(revision["updates"][0]["reason"], records[0]["reason"])
        changed = apply(self.plan, self.journal, json.loads(json.dumps(revision)))
        self.assertEqual(changed, apply(self.plan, self.journal, revision))
        changed["revisions"][0]["updates"][0]["reason"] = "mutated output"
        self.assertNotEqual(revision["updates"][0]["reason"], "mutated output")

    def test_all_declarations_passed_never_establish_scientific_or_durable_authority(self):
        receipts = old.seal_task_receipts(self.plan, [record(index) for index in range(4)])
        journal = api.start_preparation_journal(self.plan, old.checkpoint_preparation(self.plan, receipts))
        result = api.resume_preparation_journal(self.plan, journal)
        self.assertTrue(result["all_checks_declared_passed"])
        for flag in ("freshness_established", "dispatch_supported", "execution_ready", "source_coverage_qualified", "artifacts_reverified", "physical_recovery_established", "durable_storage_established"):
            self.assertIs(result[flag], False)

    def test_no_asset_model_adapter_worker_network_or_process_calls(self):
        forbidden = ("subprocess.Popen", "subprocess.run", "socket.create_connection", "urllib.request.urlopen",
                     "ngen_reforecast.execution.execute_campaign", "ngen_reforecast.execution.preflight_execution",
                     "ngen_reforecast.preparation.forcing_adapter.check_forcing_preparation", "builtins.open")
        policy = Path(__file__).absolute().parents[1] / "src/ngen_reforecast/preparation/request-policy.json"
        original = Path.open
        def policy_only(path, *args, **kwargs):
            self.assertEqual(path, policy)
            return original(path, *args, **kwargs)
        with ExitStack() as stack:
            mocks = [stack.enter_context(patch(target, side_effect=AssertionError(target))) for target in forbidden]
            stack.enter_context(patch.object(Path, "open", new=policy_only))
            journal = api.start_preparation_journal(self.plan)
            revision = api.seal_receipt_revision(self.plan, journal, [update(0)])
            api.resume_preparation_journal(self.plan, apply(self.plan, journal, revision))
            for mocked in mocks:
                mocked.assert_not_called()


class AnnualPreparationJournalTests(unittest.TestCase):
    def test_annual_population_and_full_history_survive_supersession(self):
        request = normalize_request({**BASE, "start_hour_utc": 0, "end_hour_utc": 23, "end_date": "2022-12-31"})
        study = old.plan_preparation(request, origin_time_utc="2021-12-01T00:00:00Z")
        failed = old.seal_task_receipts(study, [record(index, "failed") for index in range(len(study["tasks"]))])
        checkpoint = old.checkpoint_preparation(study, failed)
        journal = api.start_preparation_journal(study, checkpoint)
        revision = api.seal_receipt_revision(study, journal, [update(0, expected=failed[0]["receipt_identity_sha256"]),
                                                           update(1, expected=failed[1]["receipt_identity_sha256"])])
        changed = apply(study, journal, revision)
        result = api.resume_preparation_journal(study, changed)
        self.assertEqual(len(study["requested_population"]["issues_utc"]), 8760)
        self.assertEqual(study["tasks"][0]["history_interval"]["start_time_utc"], "2021-12-01T00:00:00Z")
        self.assertEqual(study["tasks"][0]["history_interval"]["stop_time_utc_exclusive"], "2023-01-01T17:00:00Z")
        self.assertEqual(changed["base_checkpoint"], checkpoint)
        self.assertEqual(len(result["current_task_receipts"]), 4381)
        self.assertEqual(len(result["pending_check_task_ids"]), 4379)
        self.assertFalse(result["execution_ready"] or result["source_coverage_qualified"])


if __name__ == "__main__":
    unittest.main()
