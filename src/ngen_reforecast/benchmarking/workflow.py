"""Draft matched-workflow contract and in-process monotonic event recorder.

Seals detect changed declarations, not dishonest observations. External run,
resource and verification records still require independent inspection. This
module cannot launch work, inspect model files or confer scientific admission.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
import time


PHASES = ("acquisition", "preparation", "generation", "verification", "export")
ACTIVITIES = ("hands_on", "system_wait", "interruption")
MAX_ITEMS = 4096
MAX_EVENTS = 512
MAX_INTEGER = 2**63 - 1
ACTION_RULE = "one-observed-meaningful-researcher-action-not-keystrokes-v1"
PHASE_RULE = "ordered-nonoverlapping-phases-gaps-retained-in-total-v1"
COMPARATOR = {"field": "discharge", "unit": "m3 s-1", "abs_tol": 1e-6,
              "rel_tol": 1e-5, "rule": "max-absolute-or-symmetric-relative-v1"}


class BenchmarkError(ValueError):
    """Malformed, inconsistent or unsupported benchmark declaration."""


def _check(condition, message):
    if not condition:
        raise BenchmarkError(message)


def _snapshot(value):
    count = 0
    budget = 0

    def visit(item, depth):
        nonlocal count, budget
        count += 1
        _check(count <= 100000 and depth <= 12, "artifact structure limit")
        if type(item) is dict:
            _check(len(item) <= MAX_ITEMS, "artifact object limit")
            _check(all(type(k) is str and len(k) <= 64 for k in item), "invalid object key")
            budget += 2 + sum(len(_bytes(k)) + 2 for k in item)
            _check(budget <= 2 * 1024 * 1024, "artifact byte limit")
            return {k: visit(v, depth + 1) for k, v in item.items()}
        if type(item) is list:
            _check(len(item) <= MAX_ITEMS, "artifact list limit")
            budget += 2 + len(item)
            _check(budget <= 2 * 1024 * 1024, "artifact byte limit")
            return [visit(v, depth + 1) for v in item]
        _check(item is None or type(item) in (str, int, float, bool), "JSON values required")
        if type(item) is str:
            _check(len(item) <= 512, "artifact string limit")
        if type(item) is float:
            _check(math.isfinite(item), "finite values required")
        if type(item) is int:
            _check(-MAX_INTEGER <= item <= MAX_INTEGER, "artifact integer limit")
        budget += len(_bytes(item))
        _check(budget <= 2 * 1024 * 1024, "artifact byte limit")
        return item

    result = visit(value, 0)
    _check(len(_bytes(result)) <= 2 * 1024 * 1024, "artifact byte limit")
    return result


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _seal(value):
    result = _snapshot(value)
    result["identity_sha256"] = hashlib.sha256(_bytes(result)).hexdigest()
    return result


def _unseal(value):
    result = _snapshot(value)
    _check(type(result) is dict and "identity_sha256" in result, "sealed object required")
    identity = result.pop("identity_sha256")
    _digest(identity)
    _check(hashlib.sha256(_bytes(result)).hexdigest() == identity, "artifact identity mismatch")
    return result


def _fields(value, names):
    _check(type(value) is dict and set(value) == set(names), "unexpected or missing fields")


def _digest(value):
    _check(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
           "lowercase SHA256 required")


def _alias(value):
    _check(type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value),
           "public-safe alias required")


def _integer(value, minimum=0):
    _check(type(value) is int and minimum <= value <= MAX_INTEGER, "bounded integer required")


def _number(value):
    _check(type(value) in (int, float), "numeric value required")
    _check(0 <= value <= MAX_INTEGER and math.isfinite(value), "finite nonnegative value required")


def _utc(value):
    _check(type(value) is str, "UTC timestamp required")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise BenchmarkError("canonical hourly UTC timestamp required") from exc
    _check(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value and
           parsed.minute == parsed.second == 0, "canonical hourly UTC timestamp required")
    return parsed


def _key(value):
    _check(type(value) is list and len(value) == 4, "four-part key required")
    site, issue, lead, valid = value
    _alias(site)
    _integer(lead, 1)
    _check(lead <= 18, "only the complete 18-lead diagnostic is supported")
    try:
        _check(_utc(issue) + timedelta(hours=lead) == _utc(valid), "valid time differs from issue plus lead")
    except OverflowError as exc:
        raise BenchmarkError("timestamp overflow") from exc
    return tuple(value)


def freeze_contract(*, trial_manifest_sha256, scientific_identity, environment_sha256, resources,
                    cache_stratum, cache_definition, expected_keys):
    """Freeze a draft declaration, not execution permission or measured evidence.

    The workload digest must cover domain, original initialization, parameters,
    forcing/time treatment and complete history. The model digest includes the
    physical runtime/components; environment includes architecture and threads.
    """
    scientific_identity, resources, expected_keys = _snapshot(
        [scientific_identity, resources, expected_keys])
    _fields(scientific_identity, ("workload_sha256", "model_sha256", "inputs_sha256", "reference_sha256"))
    for value in scientific_identity.values():
        _digest(value)
    _digest(environment_sha256)
    _digest(trial_manifest_sha256)
    _fields(resources, ("cpu_limit", "memory_limit_bytes", "parallel_jobs"))
    for value in resources.values():
        _integer(value, 1)
    _check(resources["parallel_jobs"] <= resources["cpu_limit"], "parallel jobs exceed CPU limit")
    _check(cache_stratum in ("first-use", "warm-resident", "completed-result-reuse"), "unsupported cache stratum")
    _alias(cache_definition)
    _check(type(expected_keys) is list and 0 < len(expected_keys) <= MAX_ITEMS, "bounded expected keys required")
    keys = [_key(k) for k in expected_keys]
    _check(len(set(keys)) == len(keys), "duplicate expected key")
    populations = {}
    for site, issue, lead, valid in keys:
        populations.setdefault((site, issue), set()).add(lead)
    _check(all(leads == set(range(1, 19)) for leads in populations.values()), "all 18 leads required per issue")
    return _seal({"schema": "matched-workflow/v0.1", "status": "draft",
                  "trial_manifest_sha256": trial_manifest_sha256,
                  "scientific_identity": scientific_identity, "environment_sha256": environment_sha256,
                  "strategy": "independent-cold-jobs", "resources": resources,
                  "cache_stratum": cache_stratum, "cache_definition": cache_definition,
                  "expected_keys": [list(k) for k in sorted(keys)], "comparator": COMPARATOR,
                  "phases": list(PHASES), "phase_rule": PHASE_RULE, "action_rule": ACTION_RULE})


def _contract(value):
    body = _unseal(value)
    _fields(body, ("schema", "status", "trial_manifest_sha256", "scientific_identity", "environment_sha256", "strategy",
                   "resources", "cache_stratum", "cache_definition", "expected_keys", "comparator",
                   "phases", "phase_rule", "action_rule"))
    rebuilt = freeze_contract(**{k: body[k] for k in ("trial_manifest_sha256", "scientific_identity", "environment_sha256",
                              "resources", "cache_stratum", "cache_definition", "expected_keys")})
    _check(_bytes(rebuilt) == _bytes(value), "unsupported contract or changed frozen rules")
    return rebuilt


def _summarize(events, elapsed_ns, status, human_complete):
    _check(type(events) is list and len(events) <= MAX_EVENTS + 3, "bounded events required")
    _integer(elapsed_ns)
    _check(status in ("completed", "failed"), "unsupported outcome")
    _check(type(human_complete) is bool, "human completeness must be Boolean")
    phases = {p: None for p in PHASES}
    activities = {a: 0 for a in ACTIVITIES}
    incidents = {k: 0 for k in ("failure", "retry", "assistance")}
    active_phase = active_activity = None
    next_phase = actions = previous = 0
    action_ids = set()
    for event in events:
        _fields(event, ("at_ns", "event", "value"))
        at, kind, value = event["at_ns"], event["event"], event["value"]
        _integer(at)
        _check(type(kind) is str, "event name required")
        _alias(value)
        _check(previous <= at <= elapsed_ns, "nonmonotonic or out-of-window event")
        previous = at
        if kind == "phase_start":
            _check(active_phase is None and next_phase < len(PHASES) and value == PHASES[next_phase],
                   "phases must be unique, ordered and nonoverlapping")
            active_phase = (value, at)
        elif kind == "phase_end":
            _check(active_phase is not None and active_phase[0] == value, "phase end without matching start")
            phases[value] = at - active_phase[1]
            active_phase = None
            next_phase += 1
        elif kind == "activity_start":
            _check(value in ACTIVITIES and active_activity is None, "invalid or overlapping human activity")
            active_activity = (value, at)
        elif kind == "activity_end":
            _check(active_activity is not None and active_activity[0] == value, "activity end without start")
            activities[value] += at - active_activity[1]
            active_activity = None
        elif kind == "action":
            _alias(value)
            _check(value not in action_ids, "duplicate action identity")
            action_ids.add(value)
            actions += 1
        elif kind in incidents:
            _alias(value)
            incidents[kind] += 1
        else:
            raise BenchmarkError("unsupported event")
    _check(active_phase is None and active_activity is None, "open interval at finish")
    _check(status != "completed" or next_phase == len(PHASES), "completed run requires every phase")
    _check(status != "failed" or incidents["failure"] > 0, "failed run requires failure event")
    return {"phase_elapsed_ns": phases, "unclassified_elapsed_ns": elapsed_ns - sum(v or 0 for v in phases.values()),
            "human_activity_ns": activities if human_complete else {a: None for a in ACTIVITIES},
            "human_unclassified_elapsed_ns": elapsed_ns - sum(activities.values()) if human_complete else None,
            "meaningful_actions": actions if human_complete else None, "incidents": incidents}


def _verification(value, contract):
    if value is None:
        return None
    _fields(value, ("manifest_sha256", "verification_sha256", "reference_sha256", "observed_rows", "outcome"))
    _digest(value["manifest_sha256"])
    _digest(value["verification_sha256"])
    _digest(value["reference_sha256"])
    _check(value["reference_sha256"] == contract["scientific_identity"]["reference_sha256"],
           "verification uses a different physical reference")
    _check(value["outcome"] == "passed-complete-products", "complete external verification required")
    _integer(value["observed_rows"])
    _check(value["observed_rows"] == len(contract["expected_keys"]), "verification row count differs from complete population")
    return _snapshot(value)


def _resources(value):
    if value is None:
        return None
    _fields(value, ("measurement_sha256", "scope", "method", "cpu_seconds", "peak_rss_bytes",
                    "read_bytes", "write_bytes", "output_bytes"))
    _digest(value["measurement_sha256"])
    _check(value["scope"] == "whole-job", "resource scope must include all descendants")
    _check(value["method"] in ("cgroup-v2-counters", "equivalent-whole-job-counters"),
           "whole-job counters required; sampled process RSS is insufficient")
    for name in ("cpu_seconds", "peak_rss_bytes", "read_bytes", "write_bytes", "output_bytes"):
        if value[name] is not None:
            (_number if name == "cpu_seconds" else _integer)(value[name])
    return _snapshot(value)


class WorkflowRecorder:
    """Record one sequential attempt; explicit human events require an observer.

    A synthetic clock is injectable only for synthetic fixtures. An observed
    session needs an external observation-record digest; its validity and the
    authorization for the underlying work are outside this library.
    """

    def __init__(self, contract, *, run_id, paired_block_id, arm, implementation_sha256,
                 measurement_origin="synthetic-fixture", observation_record_sha256=None,
                 clock_ns=None):
        self.contract = _contract(contract)
        _alias(run_id)
        _alias(paired_block_id)
        _check(arm in ("manual", "software"), "manual or software arm required")
        _digest(implementation_sha256)
        _check(measurement_origin in ("synthetic-fixture", "observed-session"), "unsupported evidence origin")
        if measurement_origin == "observed-session":
            _digest(observation_record_sha256)
            _check(clock_ns is None, "observed sessions require the system monotonic clock")
        else:
            _check(observation_record_sha256 is None, "synthetic fixture cannot carry an observed-session binding")
        self._clock = time.monotonic_ns if clock_ns is None else clock_ns
        self._start = self._clock()
        _integer(self._start)
        self._last = self._start
        self._events = []
        self._finished = False
        self._metadata = {"run_id": run_id, "paired_block_id": paired_block_id,
                          "arm": arm, "implementation_sha256": implementation_sha256,
                          "measurement_origin": measurement_origin,
                          "observation_record_sha256": observation_record_sha256,
                          "clock": "system-monotonic-ns" if clock_ns is None else "synthetic-ns"}

    def _stamp(self):
        _check(not self._finished, "attempt already finished")
        now = self._clock()
        _integer(now)
        _check(now >= self._last, "clock moved backwards")
        self._last = now
        return now - self._start

    def _event(self, kind, value):
        _check(len(self._events) < MAX_EVENTS, "event limit")
        _alias(value)
        event = {"at_ns": self._stamp(), "event": kind, "value": value}
        candidate = self._events + [event]
        # Validate prefix transitions without requiring the final phase/intervals.
        _validate_prefix(candidate)
        self._events.append(event)

    def start_phase(self, phase):
        self._event("phase_start", phase)

    def end_phase(self, phase):
        self._event("phase_end", phase)

    def start_activity(self, activity):
        self._event("activity_start", activity)

    def end_activity(self, activity):
        self._event("activity_end", activity)

    def action(self, action_id):
        self._event("action", action_id)

    def incident(self, kind, incident_id):
        _check(kind in ("failure", "retry", "assistance"), "unsupported incident")
        self._event(kind, incident_id)

    def finish(self, *, status="completed", verification=None,
               human_observation_complete=False, job_resources=None):
        elapsed = self._stamp()
        summary = _summarize(self._events, elapsed, status, human_observation_complete)
        receipt = _seal({"schema": "workflow-attempt/v0.1",
                         "contract_sha256": self.contract["identity_sha256"], **self._metadata,
                         "status": status, "elapsed_ns": elapsed, "events": self._events,
                         "human_observation_complete": human_observation_complete, "summary": summary,
                         "verification": _verification(verification, self.contract),
                         "job_resources": _resources(job_resources), "cost_usd": None})
        self._finished = True
        return receipt


def _validate_prefix(events):
    # Close temporary intervals and finish as failed solely to reuse one reducer.
    suffix = []
    phase = activity = None
    for event in events:
        if event["event"] == "phase_start":
            phase = event["value"]
        elif event["event"] == "phase_end":
            phase = None
        elif event["event"] == "activity_start":
            activity = event["value"]
        elif event["event"] == "activity_end":
            activity = None
    at = events[-1]["at_ns"]
    if phase is not None:
        suffix.append({"at_ns": at, "event": "phase_end", "value": phase})
    if activity is not None:
        suffix.append({"at_ns": at, "event": "activity_end", "value": activity})
    suffix.append({"at_ns": at, "event": "failure", "value": "prefix-validation"})
    _summarize(events + suffix, at, "failed", False)


def _run(contract, receipt):
    body = _unseal(receipt)
    _fields(body, ("schema", "contract_sha256", "run_id", "paired_block_id", "arm", "implementation_sha256",
                   "measurement_origin", "observation_record_sha256", "clock", "status", "elapsed_ns",
                   "events", "human_observation_complete", "summary", "verification", "job_resources", "cost_usd"))
    _check(body["schema"] == "workflow-attempt/v0.1" and body["cost_usd"] is None, "unsupported attempt schema")
    _check(body["contract_sha256"] == contract["identity_sha256"], "run bound to different contract")
    _alias(body["run_id"])
    _alias(body["paired_block_id"])
    _digest(body["implementation_sha256"])
    _check(body["arm"] in ("manual", "software"), "unsupported arm")
    if body["measurement_origin"] == "observed-session":
        _digest(body["observation_record_sha256"])
        _check(body["clock"] == "system-monotonic-ns", "observed session requires monotonic clock")
    else:
        _check(body["measurement_origin"] == "synthetic-fixture" and
               body["observation_record_sha256"] is None and
               body["clock"] in ("system-monotonic-ns", "synthetic-ns"), "invalid evidence origin")
    _check(type(body["events"]) is list and len(body["events"]) <= MAX_EVENTS, "event limit")
    summary = _summarize(body["events"], body["elapsed_ns"], body["status"], body["human_observation_complete"])
    _check(_bytes(summary) == _bytes(body["summary"]), "changed measurement summary")
    _verification(body["verification"], contract)
    _resources(body["job_resources"])
    return body


def assess_pair(contract, manual, software):
    """Assess submitted declarations; return actionable blockers, never a general speedup claim."""
    contract = _contract(contract)
    runs = []
    blockers = []
    bindings = {"manual": None, "software": None}
    for label, receipt in (("manual", manual), ("software", software)):
        try:
            run = _run(contract, receipt)
            _check(run["arm"] == label, "wrong comparison arm")
            runs.append(run)
            bindings[label] = receipt["identity_sha256"]
        except BenchmarkError as exc:
            blockers.append({"code": "invalid-" + label, "action": "Replace or repair the bound attempt: " + str(exc)})
    if len(runs) == 2:
        if runs[0]["run_id"] == runs[1]["run_id"]:
            blockers.append({"code": "same-attempt", "action": "Supply two distinct observed attempt identities."})
        if runs[0]["paired_block_id"] != runs[1]["paired_block_id"]:
            blockers.append({"code": "different-blocks", "action": "Use both attempts from the same predeclared paired block."})
        for run in runs:
            if run["measurement_origin"] != "observed-session":
                blockers.append({"code": "synthetic-" + run["arm"], "action": "Collect a separately authorized observed session; retain this fixture."})
            if run["status"] != "completed" or run["summary"]["incidents"]["failure"]:
                blockers.append({"code": "failed-" + run["arm"], "action": "Retain the failed attempt and declare a separate retry."})
            if run["verification"] is None:
                blockers.append({"code": "unverified-" + run["arm"], "action": "Bind the complete product manifest and external verification receipt."})
            if run["elapsed_ns"] == 0 or (contract["cache_stratum"] != "completed-result-reuse" and
                    run["summary"]["phase_elapsed_ns"]["generation"] in (None, 0)):
                blockers.append({"code": "unmeasured-" + run["arm"], "action": "Measure positive total and generation intervals in the declared stratum."})
        if runs[0]["observation_record_sha256"] == runs[1]["observation_record_sha256"]:
            blockers.append({"code": "same-observation", "action": "Bind a distinct observation record for each attempt."})
    ratios = None
    if not blockers:
        baseline, candidate = runs
        ratios = {"total_elapsed_manual_over_software": baseline["elapsed_ns"] / candidate["elapsed_ns"],
                  "generation_elapsed_manual_over_software": None if contract["cache_stratum"] == "completed-result-reuse" else
                  baseline["summary"]["phase_elapsed_ns"]["generation"] /
                  candidate["summary"]["phase_elapsed_ns"]["generation"]}
    origin = "unassessed-declarations"
    if any(run["measurement_origin"] == "synthetic-fixture" for run in runs):
        origin = "synthetic-fixture"
    elif len(runs) == 2:
        origin = "observed-session-declarations"
    return _seal({"schema": "workflow-pair-assessment/v0.1", "contract_sha256": contract["identity_sha256"],
                  "attempt_identity_sha256": bindings,
                  "measurement_origin": origin, "blockers": blockers,
                  "observed_elapsed_ratios": ratios, "general_speedup_established": False,
                  "scientific_qualification": False, "physical_recovery_established": False})


def compare_fixture_rows(contract, reference, candidate):
    """Check small discharge fixtures only; never qualify a physical model run."""
    contract = _contract(contract)
    expected = {tuple(k) for k in contract["expected_keys"]}

    def index(rows):
        rows = _snapshot(rows)
        _check(type(rows) is list and len(rows) == len(expected), "complete row count required")
        result = {}
        for row in rows:
            _fields(row, ("key", "unit", "discharge"))
            key = _key(row["key"])
            _check(key in expected and key not in result, "unexpected or duplicate row key")
            _check(row["unit"] == COMPARATOR["unit"], "discharge unit mismatch")
            _number(row["discharge"])
            result[key] = row["discharge"]
        _check(set(result) == expected, "missing row key")
        return result

    left, right = index(reference), index(candidate)
    def content_identity(values):
        normalized = [{"key": list(k), "unit": COMPARATOR["unit"], "discharge": values[k]}
                      for k in sorted(values)]
        return hashlib.sha256(_bytes(normalized)).hexdigest()

    different = [list(k) for k in sorted(expected) if
                 abs(left[k] - right[k]) > max(COMPARATOR["abs_tol"],
                                              COMPARATOR["rel_tol"] * max(abs(left[k]), abs(right[k])))]
    return _seal({"schema": "discharge-fixture-comparison/v0.1", "contract_sha256": contract["identity_sha256"],
                  "reference_content_sha256": content_identity(left), "candidate_content_sha256": content_identity(right),
                  "measurement_origin": "synthetic-fixture", "rows": len(expected),
                  "different_keys": different, "passed": not different,
                  "scientific_qualification": False, "physical_recovery_established": False})
