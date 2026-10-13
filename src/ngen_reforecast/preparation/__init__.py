"""Pure researcher-request validation and complete offline campaign translation.

This module reads only its packaged shared policy. It does not resolve a
location, inspect inputs, create execution locks, contact a worker or run a
model. A service-owned preparation descriptor is caller evidence, never an
authorization or a fresh verification of the scientific configuration.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
from importlib.resources import files
import json
import math
import re
from typing import Any

from ..campaign import CampaignError, normalize_campaign


class RequestPreparationError(ValueError):
    """A request is malformed, inconsistent or cannot be translated offline."""

    def __init__(self, code: str, field: str, message: str):
        super().__init__(message)
        self.code = code
        self.field = field


MAX_REQUEST_BYTES = 65_536
MAX_REQUEST_DEPTH = 16
MAX_REQUEST_NODES = 4_096
_HOUR = timedelta(hours=1)
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_DIGITS = re.compile(r"[0-9]+\Z")
# ECMAScript String.trim whitespace differs from Python str.strip for NEL
# and several control characters. Keep the two request builders identical.
_JS_WHITESPACE = "\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"


def _fail(code: str, field: str, message: str):
    raise RequestPreparationError(code, field, message)


def _json_text(value: Any) -> str:
    # JSON.stringify emits Unicode characters directly, but escapes lone
    # surrogate code units. Python can encounter those after a JSON decode.
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False)
    return "".join(f"\\u{ord(char):04x}" if 0xD800 <= ord(char) <= 0xDFFF
                   else char for char in text)


def _snapshot_json(value: Any) -> Any:
    """Copy only bounded plain JSON values before trusting derived fields."""
    nodes = 0
    ancestors: set[int] = set()

    def copy(item, field, depth):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_REQUEST_NODES or depth > MAX_REQUEST_DEPTH:
            _fail("REQUEST_LIMIT_EXCEEDED", field,
                  "The request exceeds the bounded JSON structure.")
        if item is None or type(item) is bool:
            return item
        if type(item) in (int, float):
            # Only exact integers representable by JavaScript are shared JSON
            # numbers. Large caller integers cannot masquerade as preview data.
            if abs(item) > 2**53 - 1 or not math.isfinite(item):
                _fail("MALFORMED_REQUEST", field,
                      "JSON numbers must be finite safe values.")
            return item
        if type(item) is str:
            if len(item) > MAX_REQUEST_BYTES:
                _fail("REQUEST_LIMIT_EXCEEDED", field,
                      "The request exceeds the JSON byte limit.")
            return item
        if type(item) not in (dict, list):
            _fail("MALFORMED_REQUEST", field,
                  "Only plain JSON values are accepted.")
        if id(item) in ancestors:
            _fail("MALFORMED_REQUEST", field,
                  "A request cannot contain cycles.")
        if len(item) > MAX_REQUEST_NODES:
            _fail("REQUEST_LIMIT_EXCEEDED", field,
                  "The request contains too many JSON members.")
        ancestors.add(id(item))
        if type(item) is list:
            output = [copy(child, f"{field}.{index}", depth + 1)
                      for index, child in enumerate(item)]
        else:
            output = {}
            for key, child in item.items():
                if type(key) is not str or key in {"__proto__", "constructor", "prototype"}:
                    _fail("MALFORMED_REQUEST", field,
                          "Only safe JSON field names are accepted.")
                if len(key) > MAX_REQUEST_BYTES:
                    _fail("REQUEST_LIMIT_EXCEEDED", field,
                          "A JSON field exceeds the byte limit.")
                output[key] = copy(child, f"{field}.{key}", depth + 1)
        ancestors.remove(id(item))
        return output

    result = copy(value, "$", 0)
    if len(_json_text(result).encode("utf-8")) > MAX_REQUEST_BYTES:
        _fail("REQUEST_LIMIT_EXCEEDED", "$",
              "The request exceeds 65,536 UTF-8 JSON bytes.")
    return result


def _policy_bytes() -> bytes:
    return files(__package__).joinpath("request-policy.json").read_bytes()


def request_policy() -> dict:
    """Return a detached copy of the same policy distributed to the browser."""
    return json.loads(_policy_bytes())


def policy_sha256() -> str:
    """Identify packaged policy bytes; this identity never grants admission."""
    return hashlib.sha256(_policy_bytes()).hexdigest()


def _date(value, field) -> datetime:
    if type(value) is not str or not _DATE.fullmatch(value):
        _fail("INVALID_STUDY", field, "Choose a complete date.")
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        _fail("INVALID_STUDY", field, "Enter a real calendar date.")


def _utc(value: datetime) -> str:
    return f"{value.year:04d}-{value.month:02d}-{value.day:02d}T{value.hour:02d}:00:00Z"


def _integer(value, low, high, field, message, *, hour=False) -> int:
    if type(value) is str and _DIGITS.fullmatch(value):
        significant = value.lstrip("0") or "0"
        # Hour form fields accept exactly one or two decimal characters. Lead
        # strings follow the browser's digit grammar, including leading zeros.
        value = int(significant) if len(significant) <= 16 and (not hour or len(value) <= 2) else None
    if (type(value) not in (int, float) or not low <= value <= high
            or not math.isfinite(value) or value != math.floor(value)):
        _fail("INVALID_STUDY", field, message)
    return int(value)


def normalize_request(input: dict) -> dict:
    """Build a canonical portable proposal without reducing requested scope.

    Date-only requests retain whole days. Optional first/last UTC issue hours
    select one inclusive, continuous hourly window across the chosen dates;
    they are not a repeated daily-hour filter.
    """
    if type(input) is not dict:
        _fail("INVALID_STUDY", "identifier", "Enter a study location.")
    policy = request_policy()
    identifier_type = input.get("identifier_type")
    if identifier_type not in ("usgs", "nwm", "watershed"):
        _fail("INVALID_STUDY", "identifier_type",
              "Choose USGS gauge, NWM reach or watershed.")
    raw_identifier = input.get("identifier")
    identifier = (raw_identifier.strip(_JS_WHITESPACE)
                  if type(raw_identifier) is str else "")
    if not identifier or len(identifier.encode("utf-16-le", errors="surrogatepass")) // 2 > policy["max_identifier_length"]:
        _fail("INVALID_STUDY", "identifier",
              "Enter an identifier or watershed name, up to 120 characters.")
    if identifier_type != "watershed" and not _DIGITS.fullmatch(identifier):
        _fail("INVALID_STUDY", "identifier",
              "Use the numeric identifier. Leading zeros are preserved.")
    mode = input.get("mode")
    if mode not in ("reforecast", "continuous_simulation"):
        _fail("INVALID_STUDY", "mode", "Choose whether you want forecast leads.")
    first_day = _date(input.get("start_date"), "start_date")
    last_day = _date(input.get("end_date"), "end_date")
    if last_day < first_day:
        _fail("INVALID_STUDY", "end_date",
              "The last issue date must be on or after the first date.")
    forecast = mode == "reforecast"
    first_hour = last_hour = None
    if forecast:
        first_hour = _integer(input.get("start_hour_utc", policy["default_first_hour_utc"]),
                              0, 23, "start_hour_utc", "Choose a whole UTC hour from 00 to 23.", hour=True)
        last_hour = _integer(input.get("end_hour_utc", policy["default_last_hour_utc"]),
                             0, 23, "end_hour_utc", "Choose a whole UTC hour from 00 to 23.", hour=True)
    first = first_day + (first_hour or 0) * _HOUR
    last = last_day + (last_hour if forecast else 23) * _HOUR
    if last < first:
        _fail("INVALID_STUDY", "end_hour_utc",
              "The last issue hour must be on or after the first issue hour.")
    if forecast and first == datetime(1, 1, 1, tzinfo=timezone.utc):
        _fail("INVALID_STUDY", "start_date",
              "This issue time leaves no representable earlier initialization time. Choose a later UTC hour or date.")
    count = int((last - first) // _HOUR) + 1
    if (count > policy["max_issues"]
            or (forecast and count + policy["forecast_horizon_hours"] > policy["max_history_hours"])):
        _fail("INVALID_STUDY", "end_date",
              "This period exceeds the offline campaign bounds after allowing for initialization and 18-hour forecasts. Shorten it; these bounds do not establish data coverage.")
    try:
        stop = last + _HOUR
        last_physical = last + policy["forecast_horizon_hours"] * _HOUR
    except OverflowError:
        _fail("INVALID_STUDY", "end_date",
              "This date extends beyond the supported calendar representation.")
    max_lead = None
    if forecast:
        max_lead = _integer(input.get("max_lead_hours"), policy["retained_leads"]["min"],
                            policy["retained_leads"]["max"], "max_lead_hours",
                            "Choose a whole number of hours from 1 to 18. Other horizons need a separately qualified profile.")
    demo = identifier_type == "usgs" and identifier == "03479000"
    blockers = [
        {"code": "LOCATION_NOT_RESOLVED", "message": "The Watauga example is a documented demonstration. A live outlet and upstream domain have not been resolved or confirmed." if demo else "A live location resolver is not connected. This identifier has not been matched to an outlet or upstream domain."},
        {"code": "COVERAGE_UNKNOWN", "message": "Historical and forecast input coverage has not been checked for these dates. Eligible dates and gaps are unknown."},
        {"code": "SCIENTIFIC_PROFILE_UNQUALIFIED", "message": "Model, parameter and initialization defaults still require scientific qualification. An initialization start has not been selected."},
        {"code": "EXECUTION_SERVICE_UNAVAILABLE", "message": "Data preparation, Linux execution and verified result downloads are not connected to this prototype."},
    ]
    if not forecast:
        blockers.insert(0, {"code": "MODE_NOT_IMPLEMENTED", "message": "Continuous historical simulation is a proposed mode. Its date interpretation and execution contract are not implemented."})
    return {
        "request_schema_version": policy["request_schema_version"],
        "artifact_type": "researcher_request",
        "interface_stage": "prototype",
        "intended_evaluation_level": "UX_E1",
        "user_study_conducted": False,
        "execution_ready": False,
        "location": {"identifier_type": identifier_type, "submitted_identifier": identifier,
                     "resolution_status": "unresolved", "demonstration": {
                         "label": "Watauga example", "usgs_gauge": "03479000", "catchment_count": 31,
                         "nexus": "1017693", "source": "docs/FIRST_PHYSICAL_EXPERIMENT.md",
                         "is_live_resolution": False,
                     } if demo else None},
        "study": {"mode": mode, "first_date": input["start_date"], "last_date": input["end_date"],
                  "date_semantics": "inclusive_utc_issue_window_proposal" if forecast else "unresolved_continuous_simulation_dates",
                  "time_zone": "UTC", "requested_max_lead_hours": max_lead,
                  "first_issue_hour_utc": first_hour, "last_issue_hour_utc": last_hour,
                  "first_issue_time_utc": _utc(first) if forecast else None,
                  "last_issue_time_utc": _utc(last) if forecast else None},
        "campaign_translation_proposal": {
            "schema_version": "1.1", "issue_schedule": {
                "start_time_utc": _utc(first), "stop_time_utc_exclusive": _utc(stop),
                "cadence_hours": policy["issue_cadence_hours"],
            }, "horizon_hours": policy["forecast_horizon_hours"], "retained_leads": {
                "min_lead_hours": policy["retained_leads"]["min"], "max_lead_hours": max_lead,
                "projection": "export",
            },
        } if forecast else None,
        "preview": {"issue_count": count, "first_issue_utc": _utc(first), "last_issue_utc": _utc(last),
                    "first_retained_valid_time_utc": _utc(first + _HOUR),
                    "last_retained_valid_time_utc": _utc(last + max_lead * _HOUR),
                    "last_physical_valid_time_utc": _utc(last_physical),
                    "retained_rows_per_location": count * max_lead,
                    "generated_rows_per_location": count * policy["forecast_horizon_hours"],
                    "output_timestep_hours": policy["issue_cadence_hours"]} if forecast else None,
        "preparation": {"coverage_status": "unknown", "qualified_profile": None,
                        "initialization_origin_utc": None, "runtime_estimate": None,
                        "cost_estimate": None, "blockers": blockers},
    }


def _difference(actual, expected, field="$") -> str | None:
    if type(actual) in (int, float) and type(expected) in (int, float):
        return None if actual == expected else field
    if type(actual) is not type(expected):
        return field
    if type(actual) is dict:
        if set(actual) != set(expected):
            return f"{field}.{sorted(set(actual) ^ set(expected))[0]}"
        for key in sorted(expected):
            difference = _difference(actual[key], expected[key], f"{field}.{key}")
            if difference:
                return difference
        return None
    if type(actual) is list:
        if len(actual) != len(expected):
            return field
        for index, (left, right) in enumerate(zip(actual, expected)):
            difference = _difference(left, right, f"{field}.{index}")
            if difference:
                return difference
        return None
    return None if actual == expected else field


def validate_request(serialized_request: dict) -> dict:
    """Rebuild all derived values; client previews and readiness are not evidence."""
    request = _snapshot_json(serialized_request)
    if type(request) is not dict:
        _fail("MALFORMED_REQUEST", "$", "Submit a serialized researcher request object.")
    if request.get("request_schema_version") == "0.1":
        _fail("REQUEST_SCHEMA_MIGRATION_REQUIRED", "$.request_schema_version",
              "Schema 0.1 requests must be explicitly rebuilt under schema 0.2; stored requests are not silently migrated.")
    if (request.get("request_schema_version") != request_policy()["request_schema_version"]
            or request.get("artifact_type") != "researcher_request"):
        _fail("UNSUPPORTED_REQUEST_SCHEMA", "$.request_schema_version",
              "Only researcher_request schema 0.2 is supported.")
    location, study = request.get("location"), request.get("study")
    if type(location) is not dict or type(study) is not dict:
        _fail("MALFORMED_REQUEST", "$", "Location and study fields are required.")
    raw = {"identifier_type": location.get("identifier_type"),
           "identifier": location.get("submitted_identifier"), "mode": study.get("mode"),
           "start_date": study.get("first_date"), "end_date": study.get("last_date"),
           "max_lead_hours": study.get("requested_max_lead_hours")}
    if study.get("mode") == "reforecast":
        raw.update(start_hour_utc=study.get("first_issue_hour_utc"),
                   end_hour_utc=study.get("last_issue_hour_utc"))
    rebuilt = normalize_request(raw)
    mismatch = _difference(request, rebuilt, "$")
    if mismatch:
        _fail("INCONSISTENT_REQUEST", mismatch,
              "This request differs from the canonical request rebuilt from its location and study. Rebuild the request; derived previews, resolution and readiness cannot be supplied as evidence.")
    return request


def translate_request(serialized_request: dict, preparation: dict, *, campaign_id: str) -> dict:
    """Translate the entire request using a trusted service-owned descriptor.

    The caller must source the descriptor outside the researcher request. This
    pure function does not prove its evidence class, select initialization,
    verify a crosswalk or acquire any assets. Returned schema-1.1 documents are
    planning specifications; the existing executor must independently admit
    their exact scientific/input/runtime/resource envelope before execution.
    """
    request = validate_request(serialized_request)
    if request["study"]["mode"] != "reforecast":
        _fail("MODE_NOT_IMPLEMENTED", "$.study.mode",
              "Continuous simulation has no implemented campaign translation.")
    descriptor = _snapshot_json(preparation)
    keys = {"origin_time_utc", "domains", "resources", "evidence_class", "location_binding"}
    if type(descriptor) is not dict or set(descriptor) != keys:
        _fail("PREPARATION_DESCRIPTOR_INVALID", "preparation",
              "Supply only the complete service-owned preparation descriptor.")
    if descriptor["evidence_class"] != "server_owned_preparation_descriptor":
        _fail("PREPARATION_DESCRIPTOR_INVALID", "preparation.evidence_class",
              "A service-owned preparation descriptor is required; it does not itself grant execution authority.")
    binding = descriptor["location_binding"]
    if (type(binding) is not dict
            or set(binding) != {"identifier_type", "submitted_identifier", "status"}
            or binding["status"] not in ("declared_candidate", "verified")
            or binding["identifier_type"] != request["location"]["identifier_type"]
            or binding["submitted_identifier"] != request["location"]["submitted_identifier"]):
        _fail("PREPARATION_LOCATION_MISMATCH", "preparation.location_binding",
              "The service-owned mapping must explicitly bind this submitted location; no other watershed is substituted.")
    last = datetime.strptime(request["study"]["last_issue_time_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    profile = request_policy()["profile"]
    horizon = request["campaign_translation_proposal"]["horizon_hours"]
    campaign = {
        **deepcopy(request["campaign_translation_proposal"]),
        "campaign_id": campaign_id, "profile": profile,
        "origin_time_utc": descriptor["origin_time_utc"],
        "history": {"start_time_utc": descriptor["origin_time_utc"],
                    "stop_time_utc": _utc(last + horizon * _HOUR)},
        "domains": descriptor["domains"], "resources": descriptor["resources"],
    }
    try:
        normalized = normalize_campaign(campaign)
    except CampaignError as exc:
        _fail("CAMPAIGN_TRANSLATION_UNSUPPORTED", "preparation",
              f"The complete requested campaign cannot use this preparation descriptor: {exc}")
    return normalized


__all__ = ["RequestPreparationError", "normalize_request", "validate_request",
           "translate_request", "request_policy", "policy_sha256"]
