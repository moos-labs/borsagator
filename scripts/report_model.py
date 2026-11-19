#!/usr/bin/env python3
"""Report Model version contract — the single pinned authority (issue #280).

Every producer and consumer of ``report-model.json`` imports this module
(``compile_model.py`` emits, ``delta.py`` and ``render.py`` consume,
``--check-model`` validates). No file carries its own copy of the version
markers: a version exists here or nowhere, so producer and readers can
never drift apart again.

Version policy (strict D-7, ``compile_model.py`` D-7):
  * any field change increments ``model_version`` and the ``schema``
    string together. The two markers are ONE version: a model whose
    markers disagree about the version is refused everywhere, and a
    model that carries a contract field its declared version does not
    define is refused by the schema-diff check below — marker equality
    alone cannot enforce that rule (#280 comment 14:41Z).
  * supported versions are exactly (1, ``borsagator-report-model/1``)
    and (2, ``borsagator-report-model/2``). Anything else — mixed
    markers, unknown future versions — is refused by every consumer.

Historical v1 exception, BOUNDED (issue #170): the ``sharia`` block was
added under v1 without a bump, as a one-off additive block. It is part
of the frozen v1 field vocabulary, so v1 models with or without it are
both legal — but it is NOT a general override: no further field may be
added to v1 silently, and from v2 on every field change bumps the
version. Never copy the exception into another silent v1 addition.

v2 (issue #280) adds exactly one top-level field, ``disclosure_events``
— the structured bilingual EGX disclosure events surfaced from the
#109/#278 feed (``disclosure-events/<CODE>-events.json`` per sweep).
A v1 input means events were not recorded by that contract, NOT an
empty events set: consumers must say "not recorded", never "no events".

The ``disclosure_events`` block (frozen v2 contract):
  status: "valid" | "missing" | "unavailable" | "stale"
    - valid: feed read and validated; events carried verbatim.
      Zero events is a valid-empty state (events [], counts zero) —
      recorded absence, not a gap.
    - missing: no events file for the ticker in the sweep dir.
    - unavailable: a file exists but failed validation (unparseable,
      wrong feed schema, malformed event). Events [] + reason.
    - stale: feed valid, but its quarter window ends before the sweep
      date, so it does not cover the sweep. Events still carried,
      with the reason named.
  source: sweep-dir-relative feed path, or null when there is none.
  feed_schema_version / extractor_version / config_hash / quarter /
  feed_report: the feed's own provenance, or null when unavailable.
  events: event records verbatim from the feed (see
  ``validate_event_record``); amounts are decimal STRINGS, never
  floats; every field carries evidence pointers (source_url,
  document_revision_id ``clipped-body-sha256:…``, per-field spans).
  counts: derived from ``events`` (events / verified / candidates /
  stale / by_type / by_verification).
  reason: null on valid, otherwise the one-line explanation.

Stdlib only. No side effects on import.
"""
import re
from decimal import Decimal, InvalidOperation

MODEL_VERSION = 2
SCHEMA = "borsagator-report-model/2"

# Exact supported (model_version, schema) tuples. Nothing else is a
# Report Model, in any consumer.
SUPPORTED_VERSIONS = (
    (1, "borsagator-report-model/1"),
    (2, "borsagator-report-model/2"),
)
SUPPORTED_SCHEMAS = {schema for _, schema in SUPPORTED_VERSIONS}

# Frozen top-level field vocabulary per version. v1's set is the exact
# set the v1 compiler emitted (including the optional historical
# ``sharia`` block — see the module docstring); v2 adds exactly one
# field. A model carrying a field outside its version's set is a
# contract-field change without the required bump: refused.
V1_FIELDS = frozenset((
    "model_version", "schema", "ticker", "job", "job_shape", "market",
    "date", "started", "finished", "sweep_dir", "archive_commit",
    "provenance", "partial", "ensemble_absent", "ensemble_empty",
    "ensemble_shape", "degraded", "degraded_derived", "ticker_mismatch",
    "coercion_failed", "secret_fields_dropped", "ensemble", "price",
    "price_series_last", "price_series_excluded", "family_scores",
    "horizons", "risk", "risk_events_truncated", "corporate_actions",
    "kronos_ex_rescale", "weights", "ledger_pin", "news", "tools",
    "tools_absent", "tools_failed", "recommendation", "levels",
    "reaction_profile", "llm", "benchmark", "sharia", "flags",
    "metrics_schema",
))
V2_FIELDS = V1_FIELDS | frozenset(("disclosure_events",))
FIELDS_BY_VERSION = {1: V1_FIELDS, 2: V2_FIELDS}

# Required fields per version. v1's list is the pre-existing
# MODEL_REQUIRED_FIELDS; v2 adds the events block (a v2 model without
# it is incomplete, not a v1 model in disguise).
V1_REQUIRED_FIELDS = (
    "model_version", "schema", "ticker", "job", "job_shape", "date",
    "finished", "sweep_dir", "archive_commit", "provenance",
    "partial", "ensemble_absent", "ensemble_shape", "degraded",
    "ticker_mismatch", "coercion_failed", "ensemble", "price",
    "price_series_last", "family_scores", "horizons", "risk",
    "corporate_actions", "kronos_ex_rescale", "weights", "ledger_pin",
    "news", "tools", "tools_absent", "tools_failed", "recommendation",
    "levels", "reaction_profile", "llm", "flags", "metrics_schema")
V2_REQUIRED_FIELDS = V1_REQUIRED_FIELDS + ("disclosure_events",)
REQUIRED_BY_VERSION = {1: V1_REQUIRED_FIELDS, 2: V2_REQUIRED_FIELDS}

DISCLOSURE_EVENTS_STATUSES = ("valid", "missing", "unavailable", "stale")

# --- disclosure-events feed contract (frozen; producer: #109/#278) ---
FEED_SCHEMA_VERSION = 1
FEED_EXTRACTOR_VERSION = "disclosure-events/1.0.0"
EVENT_TYPES = ("dividend", "earnings", "board_decision")
EXTRACTION_STATUSES = ("extracted", "candidate")
VERIFICATION_STATUSES = ("verified", "unverified")
SOURCE_KINDS = ("primary", "republication")

# Per-type payload keys (the extractor's frozen record shape).
EVENT_PAYLOAD_KEYS = {
    "dividend": ("coupon_number", "amount_per_share", "currency",
                 "ex_date", "entitlement_end", "record_date",
                 "payout_date"),
    "earnings": ("period_start", "period_end", "fiscal_year",
                 "fiscal_quarter", "basis", "npat", "npat_comparative",
                 "revenue", "yoy_npat_pct"),
    "board_decision": ("meeting_date", "decision_subtype", "state",
                       "subject_ar", "subject_en", "assembly_date",
                       "assembly_time"),
}
# Payload fields that are {value, basis, evidence, ...} date records.
DATE_PAYLOAD_FIELDS = {
    "dividend": ("ex_date", "entitlement_end", "record_date",
                 "payout_date"),
    "earnings": ("period_start", "period_end"),
    "board_decision": ("meeting_date", "assembly_date"),
}
# Payload fields that are {value, currency, scale, raw, evidence}
# money records (value is a decimal STRING, never a float).
MONEY_PAYLOAD_FIELDS = {
    "dividend": ("amount_per_share",),
    "earnings": ("npat", "npat_comparative", "revenue"),
    "board_decision": (),
}
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_str_or_none(value):
    return value is None or isinstance(value, str)


def _check_no_float(obj, path, problems, where):
    """Amounts are decimal strings; a float anywhere in an event
    record is a contract violation, never a rounding detail."""
    if isinstance(obj, float):
        problems.append(f"{where}: float value at {path} (amounts "
                        "are decimal strings, never floats)")
    elif isinstance(obj, dict):
        for key, val in obj.items():
            _check_no_float(val, f"{path}/{key}", problems, where)
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            _check_no_float(val, f"{path}[{i}]", problems, where)


def _check_date_field(field, value, problems, where):
    if not isinstance(value, dict):
        problems.append(f"{where}: payload.{field} is not an object")
        return
    if not _is_str_or_none(value.get("value")):
        problems.append(f"{where}: payload.{field}.value is not a "
                        "string-or-null")
    elif value.get("value") is not None and not ISO_DATE_RE.match(
            value["value"]):
        problems.append(f"{where}: payload.{field}.value "
                        f"{value['value']!r} is not an ISO date")
    if not isinstance(value.get("basis"), str):
        problems.append(f"{where}: payload.{field}.basis is not a "
                        "string")


def _check_money_field(field, value, problems, where):
    if not isinstance(value, dict):
        problems.append(f"{where}: payload.{field} is not an object")
        return
    raw = value.get("value")
    if raw is not None:
        if not isinstance(raw, str):
            problems.append(f"{where}: payload.{field}.value is not "
                            "a decimal string")
        else:
            try:
                Decimal(raw)
            except (InvalidOperation, ValueError):
                problems.append(f"{where}: payload.{field}.value "
                                f"{raw!r} is not a decimal string")
    if not _is_str_or_none(value.get("currency")):
        problems.append(f"{where}: payload.{field}.currency is not "
                        "a string-or-null")
    if not _is_str_or_none(value.get("scale")):
        problems.append(f"{where}: payload.{field}.scale is not a "
                        "string-or-null")


def validate_event_record(event):
    """Strict shape check for one disclosure event record (the frozen
    v2 contract). Returns a list of problems (empty = valid)."""
    where = "disclosure_events event"
    problems = []
    if not isinstance(event, dict):
        return [f"{where}: event is not an object"]
    ev_id = event.get("event_id")
    where = f"disclosure_events event {ev_id!r}"
    if event.get("schema_version") != FEED_SCHEMA_VERSION:
        problems.append(f"{where}: schema_version "
                        f"{event.get('schema_version')!r}, expected "
                        f"{FEED_SCHEMA_VERSION}")
    _check_no_float(event, "", problems, where)
    for field in ("event_id", "event_revision_id", "subtype",
                  "source_document_id", "document_revision_id",
                  "source_url", "extractor_version", "config_hash"):
        if not isinstance(event.get(field), str) or not event.get(field):
            problems.append(f"{where}: {field} is not a non-empty "
                            "string")
    if not str(event.get("document_revision_id") or "").startswith(
            "clipped-body-sha256:"):
        problems.append(f"{where}: document_revision_id is not a "
                        "clipped-body-sha256 pointer")
    event_type = event.get("event_type")
    if event_type not in EVENT_TYPES:
        problems.append(f"{where}: event_type {event_type!r} is not "
                        f"one of {', '.join(EVENT_TYPES)}")
        return problems
    issuer = event.get("issuer")
    if not isinstance(issuer, dict):
        problems.append(f"{where}: issuer is not an object")
    else:
        for field in ("ticker", "isin", "name_ar", "name_en"):
            if field not in issuer or not _is_str_or_none(
                    issuer.get(field)):
                problems.append(f"{where}: issuer.{field} is not a "
                                "string-or-null")
    if event.get("source_kind") not in SOURCE_KINDS:
        problems.append(f"{where}: source_kind "
                        f"{event.get('source_kind')!r} is not one of "
                        f"{', '.join(SOURCE_KINDS)}")
    announced = event.get("announced")
    if not isinstance(announced, dict):
        problems.append(f"{where}: announced is not an object")
    else:
        _check_date_field("announced", announced, problems, where)
    for field in ("summary_ar", "summary_en"):
        if not _is_str_or_none(event.get(field)):
            problems.append(f"{where}: {field} is not a "
                            "string-or-null")
    if not isinstance(event.get("summary_meta"), dict):
        problems.append(f"{where}: summary_meta is not an object")
    payload = event.get("payload")
    if not isinstance(payload, dict):
        problems.append(f"{where}: payload is not an object")
    else:
        expected = set(EVENT_PAYLOAD_KEYS[event_type])
        got = set(payload)
        for field in sorted(expected - got):
            problems.append(f"{where}: payload missing {field}")
        for field in sorted(got - expected):
            problems.append(f"{where}: payload has unknown field "
                            f"{field} for {event_type}")
        for field in DATE_PAYLOAD_FIELDS[event_type]:
            if field in payload:
                _check_date_field(field, payload[field], problems, where)
        for field in MONEY_PAYLOAD_FIELDS[event_type]:
            if field in payload:
                _check_money_field(field, payload[field], problems,
                                   where)
    if not isinstance(event.get("evidence"), list):
        problems.append(f"{where}: evidence is not a list")
    if event.get("extraction_status") not in EXTRACTION_STATUSES:
        problems.append(f"{where}: extraction_status "
                        f"{event.get('extraction_status')!r} is not "
                        f"one of {', '.join(EXTRACTION_STATUSES)}")
    if event.get("verification_status") not in VERIFICATION_STATUSES:
        problems.append(f"{where}: verification_status "
                        f"{event.get('verification_status')!r} is not "
                        f"one of {', '.join(VERIFICATION_STATUSES)}")
    for field in ("candidate_reasons", "duplicate_links"):
        if not isinstance(event.get(field), list):
            problems.append(f"{where}: {field} is not a list")
    if not isinstance(event.get("stale"), bool):
        problems.append(f"{where}: stale is not a boolean")
    return problems


def validate_disclosure_events_block(block):
    """Strict shape check for a model's ``disclosure_events`` block.
    Returns a list of problems (empty = valid)."""
    where = "disclosure_events"
    problems = []
    if not isinstance(block, dict):
        return [f"{where}: block is not an object"]
    status = block.get("status")
    if status not in DISCLOSURE_EVENTS_STATUSES:
        problems.append(f"{where}: status {status!r} is not one of "
                        f"{', '.join(DISCLOSURE_EVENTS_STATUSES)}")
        return problems
    if not _is_str_or_none(block.get("source")):
        problems.append(f"{where}: source is not a string-or-null")
    if status == "missing" and block.get("source") is not None:
        problems.append(f"{where}: status missing but source is set")
    if status in ("valid", "stale"):
        if block.get("feed_schema_version") != FEED_SCHEMA_VERSION:
            problems.append(f"{where}: feed_schema_version "
                            f"{block.get('feed_schema_version')!r}, "
                            f"expected {FEED_SCHEMA_VERSION}")
        if not isinstance(block.get("extractor_version"), str):
            problems.append(f"{where}: extractor_version is not a "
                            "string")
        if not isinstance(block.get("config_hash"), str):
            problems.append(f"{where}: config_hash is not a string")
        quarter = block.get("quarter")
        if not isinstance(quarter, dict) or not ISO_DATE_RE.match(
                str(quarter.get("start") or "")) or not ISO_DATE_RE.match(
                str(quarter.get("end") or "")):
            problems.append(f"{where}: quarter is not "
                            "{start, end} ISO dates")
        if not isinstance(block.get("feed_report"), dict):
            problems.append(f"{where}: feed_report is not an object")
    if status == "valid" and block.get("reason") is not None:
        problems.append(f"{where}: status valid but reason is set")
    if status != "valid" and not isinstance(block.get("reason"), str):
        problems.append(f"{where}: status {status} needs a reason "
                        "string")
    events = block.get("events")
    if not isinstance(events, list):
        problems.append(f"{where}: events is not a list")
        return problems
    if status in ("missing", "unavailable") and events:
        problems.append(f"{where}: status {status} must carry no "
                        "events")
    seen_ids = set()
    for event in events:
        problems.extend(validate_event_record(event))
        ev_id = event.get("event_id") if isinstance(event, dict) \
            else None
        if ev_id in seen_ids:
            problems.append(f"{where}: duplicate event_id {ev_id!r}")
        seen_ids.add(ev_id)
    counts = block.get("counts")
    if not isinstance(counts, dict):
        problems.append(f"{where}: counts is not an object")
    else:
        derived = {
            "events": len(events),
            "verified": sum(1 for e in events
                            if isinstance(e, dict) and
                            e.get("verification_status") == "verified"),
            "candidates": sum(1 for e in events
                              if isinstance(e, dict) and
                              e.get("extraction_status") == "candidate"),
            "stale": sum(1 for e in events
                         if isinstance(e, dict)
                         and e.get("stale") is True),
        }
        for key, value in derived.items():
            if counts.get(key) != value:
                problems.append(f"{where}: counts.{key} is "
                                f"{counts.get(key)!r}, derived "
                                f"{value} from events")
        by_type = {}
        by_verification = {}
        for event in events:
            if not isinstance(event, dict):
                continue
            by_type[event.get("event_type")] = \
                by_type.get(event.get("event_type"), 0) + 1
            by_verification[event.get("verification_status")] = \
                by_verification.get(
                    event.get("verification_status"), 0) + 1
        if counts.get("by_type") != by_type:
            problems.append(f"{where}: counts.by_type is "
                            f"{counts.get('by_type')!r}, derived "
                            f"{by_type}")
        if counts.get("by_verification") != by_verification:
            problems.append(f"{where}: counts.by_verification is "
                            f"{counts.get('by_verification')!r}, "
                            f"derived {by_verification}")
    return problems


def validate_model(model):
    """Consumer-side schema check (F-8 / D-7), shared by every
    consumer: the validator (``--check-model``), the renderer and
    the delta adapter. Refuses, with a problem per violation:
      * a version tuple that is not exactly (1, /1) or (2, /2) —
        mixed markers and unknown future versions alike;
      * a missing required field for the declared version;
      * a top-level field the declared version does not define —
        the no-bump schema-diff check: a contract-field change
        without the required version bump fails here even when the
        markers agree;
      * a malformed ``disclosure_events`` block (v2).
    Returns a list of problems (empty = valid)."""
    problems = []
    if not isinstance(model, dict):
        return ["model is not an object"]
    version = model.get("model_version")
    schema = model.get("schema")
    if (version, schema) not in SUPPORTED_VERSIONS:
        problems.append(
            f"model_schema_unsupported: expected (1, "
            f"'borsagator-report-model/1') or (2, "
            f"'borsagator-report-model/2'), found "
            f"({version!r}, {schema!r})")
        # The version is unknown: required-field and schema-diff
        # checks need a declared version to check against, so they
        # cannot run. The tuple refusal above is the verdict.
        return problems
    for field in REQUIRED_BY_VERSION[version]:
        if field not in model:
            problems.append(f"missing required field: {field}")
    allowed = FIELDS_BY_VERSION[version]
    for field in sorted(set(model) - allowed):
        problems.append(
            f"schema_diff: field {field!r} is not part of "
            f"borsagator-report-model/{version} (contract-field "
            f"change without a version bump)")
    if version == 2 and "disclosure_events" in model:
        problems.extend(
            validate_disclosure_events_block(
                model["disclosure_events"]))
    return problems
