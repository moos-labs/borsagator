#!/usr/bin/env python3
"""Timing-aware purification calculator (issue #171).

Given a ticker snapshot (the Sharia engine's data model, issue
#168), a share count, a buy date and a sell date (or "still
holding" with an as-of date), this calculator works out what the
holder must purify under each selected standard -- with no manual
dividend entry: dividend events are read from the snapshot's event
list (the fleet's event stream, issue #109, lands in that field).

The calculator consumes the engine's outputs only -- the
purification ratio and the per-share figure from
``sharia_engine.screen`` -- and never re-derives a screening
ratio. What each standard purifies is declared by its rule set:

* **Dividend component** (rule set ``purification.defined``):
  for every dividend whose entitlement falls inside the holding
  window, ``dividend per share x purification ratio x shares``.
* **Capital component** (rule set
  ``purification.capital_component`` -- the declaration issue
  #171 requires each rule set to carry): where it applies, the
  statement period's non-permissible income per share accrued
  over the holding days: ``per share x days held / days in the
  statement period``. Kashif documents purification applying to
  capital gains as well as dividends, and Musaffa's AAOIFI
  practice purifies the non-permissible portion of income, so
  the AAOIFI rule set declares it; EGX33 publishes no
  purification rule at all and declares none. Where a component
  does not apply it is reported as such, with the reason -- never
  as a silent zero.

ENTITLEMENT CONVENTION (stated, not assumed): a dividend belongs
to the holding iff the holder bought BEFORE its ex-date and was
still holding on it -- ``buy_date < ex_date <= window end``.
Shares bought on the ex-date itself trade without the dividend,
so buying on the ex-date is NOT entitled; selling on the ex-date
keeps the entitlement, because entitlement fixed at the start of
that day. Every event in the stream is listed in the output,
entitled or not, with the reason.

HONESTY ON GAPS (issue #171): the event stream extract in a
snapshot is bounded by the snapshot's screening date. A window
running past it is computed from the events known and marked
``partial`` with the uncovered range named. A snapshot with no
dividend field at all yields no dividend figure and no total --
never a zero built on missing events. Engine inputs the
calculator needs but the snapshot lacks (ratio, per-share,
statement period) surface as ``insufficient-data`` with the
missing inputs named, mirroring the engine's own verdict.

METHOD DECISIONS the issue left open, taken here and documented
in docs/sharia-engine.md:

* ``days held`` = (window end - buy date) in calendar days; the
  accrual fraction is capped at one full statement period when
  the holding runs longer, because a single period's snapshot is
  available -- the cap is flagged on the component, not silent.
* Amounts are rounded to 6 decimal places, matching the engine.
* A standard with no purification rule reports ``total: null``
  with status ``no-purification-rule`` -- not zero, which would
  claim nothing is owed under a rule that does not exist.

FRAMING (binding, from the issue): every output is a
per-standard SCREENING result -- "screened under standard X" --
never a fatwa and never religious or investment advice. The
framing lines ship in English and Arabic at the top level and on
every per-standard entry; final wording is reviewed under
issue #77.

Stdlib only, deterministic, no network, no wall clock: a
still-held holding requires an explicit as-of date.

Usage:
    sharia_purification.py calculate --snapshot snapshots.json
        --ticker POUL.CA --shares 10000 --buy 2026-11-02
        --sell 2026-11-20 [--as-of 2026-11-20]
        [--standard AAOIFI] [--standard EGX33]
        [--variant avg36m|spot] [--out result.json]

Exit codes: 0 = result produced (per-standard statuses carry the
data states); 2 = bad input / unknown standard / invalid holding
(fail loudly, nothing written); 1 = crash.
"""
import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharia_engine as se  # noqa: E402

CALCULATOR_VERSION = "1.0.0"
SCHEMA = "borsagator-sharia-purification/1"
CALCULATOR_PATH = "scripts/sharia_purification.py"

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_INSUFFICIENT = "insufficient-data"
STATUS_NO_RULE = "no-purification-rule"

# ------------------------------------------------------- wording

REASON_HELD_INTO_EX = {
    "en": ("Entitled: bought before the ex-date and still held "
           "on it -- the holder owned the shares when entitlement "
           "fixed."),
    "ar": ("مستحق: تم الشراء قبل تاريخ الاستحقاق وما زالت "
           "الأسهم مملوكة في ذلك التاريخ — ثبت الاستحقاق "
           "للمالك عندها."),
}
REASON_BOUGHT_ON_OR_AFTER_EX = {
    "en": ("Not entitled: bought on or after the ex-date -- "
           "shares bought on the ex-date trade without this "
           "dividend."),
    "ar": ("غير مستحق: تم الشراء في تاريخ الاستحقاق أو بعده — "
           "الأسهم المشتراة في ذلك التاريخ تُتداول بدون هذا "
           "التوزيع."),
}
REASON_SOLD_BEFORE_EX = {
    "en": ("Not entitled: the holding ended before the ex-date, "
           "so entitlement never fixed on this holding."),
    "ar": ("غير مستحق: انتهت الملكية قبل تاريخ الاستحقاق، فلم "
           "يثبت الاستحقاق لهذه الملكية."),
}
REASON_EX_AFTER_AS_OF = {
    "en": ("Not yet entitled at the calculation date: the "
           "ex-date falls after the as-of date."),
    "ar": ("لم يستحق بعد في تاريخ الحساب: تاريخ الاستحقاق يقع "
           "بعد تاريخ الحساب."),
}
REASON_NO_RULE = {
    "en": ("This standard publishes no purification rule; no "
           "purification amount is computed under it."),
    "ar": ("هذا المعيار لا ينشر قاعدة تطهير؛ لا تُحسب قيمة "
           "تطهير وفقًا له."),
}
REASON_NO_CAPITAL = {
    "en": ("The rule set declares no capital component under "
           "this standard; the capital component is 0."),
    "ar": ("لا يعلن هذا المعيار مكوّنًا رأسماليًا؛ مكوّن رأس "
           "المال يساوي صفرًا وفق هذا المعيار."),
}
REASON_CAPITAL_CAPPED = {
    "en": ("The holding runs longer than one statement period; "
           "the accrual is capped at one full period because a "
           "single period's snapshot is available."),
    "ar": ("تتجاوز مدة الملكية فترة مالية واحدة؛ يُحتسب "
           "الاستحقاق بحد أقصى فترة كاملة لأن المتاحة لقطة "
           "فترة واحدة فقط."),
}
GAP_EVENTS_UNAVAILABLE = {
    "en": ("Dividend event data is unavailable in this snapshot "
           "(no dividends field): no dividend figure is computed "
           "and no total is presented."),
    "ar": ("بيانات أحداث التوزيعات غير متاحة في هذه اللقطة "
           "(لا يوجد حقل توزيعات): لا تُحسب قيمة للتوزيعات ولا "
           "يُعرض إجمالي."),
}
GAP_EVENT_MALFORMED = {
    "en": ("A dividend event in the stream lacks an ex-date or "
           "a per-share amount and was skipped: {event}"),
    "ar": ("حدث توزيع في القائمة ينقصه تاريخ الاستحقاق أو قيمة "
           "السهم وتم تخطيه: {event}"),
}
GAP_COVERAGE = {
    "en": ("The event stream in this snapshot covers events up "
           "to {coverage} (the snapshot screening date); the "
           "holding window runs to {window_end}. Dividends with "
           "ex-dates after {coverage} are not included."),
    "ar": ("قائمة الأحداث في هذه اللقطة تغطي الأحداث حتى "
           "{coverage} (تاريخ فحص اللقطة)؛ وتمتد فترة الملكية "
           "حتى {window_end}. التوزيعات التي تقع تواريخ "
           "استحقاقها بعد {coverage} غير مشمولة."),
}
GAP_NO_SCREENING_DATE = {
    "en": ("The snapshot carries no screening date, so the "
           "event stream's coverage cannot be bounded; the "
           "result is marked partial."),
    "ar": ("لا تحمل اللقطة تاريخ فحص، فلا يمكن تحديد مدى "
           "تغطية قائمة الأحداث؛ تُعلَّم النتيجة كجزئية."),
}


def _parse_date(value, field):
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("invalid date for %s: %r" % (field, value))


def _round6(value):
    return round(value, 6) if value is not None else None


# ------------------------------------------------------- window

def _resolve_window(buy_raw, sell_raw, as_of_raw):
    """Validate the holding and resolve its window.

    Returns (buy, end, end_kind, days_held). Fails loudly on an
    impossible holding -- a still-held position REQUIRES an
    as-of date (no silent wall clock in a deterministic tool).
    """
    buy = _parse_date(buy_raw, "buy_date")
    if buy is None:
        raise ValueError("buy_date is required")
    sell = _parse_date(sell_raw, "sell_date")
    as_of = _parse_date(as_of_raw, "as_of")
    if sell is not None:
        end, end_kind = sell, "sell"
    else:
        if as_of is None:
            raise ValueError(
                "still holding (no sell_date) requires an as-of "
                "date")
        end, end_kind = as_of, "as-of"
    if end < buy:
        raise ValueError("window end %s precedes buy_date %s"
                         % (end, buy))
    return buy, end, end_kind, (end - buy).days


def _entitlement(buy, end, end_kind, ex_date):
    """(entitled, reason) under the stated convention:
    buy < ex_date <= window end."""
    if buy >= ex_date:
        return False, REASON_BOUGHT_ON_OR_AFTER_EX
    if end < ex_date:
        if end_kind == "sell":
            return False, REASON_SOLD_BEFORE_EX
        return False, REASON_EX_AFTER_AS_OF
    return True, REASON_HELD_INTO_EX


# ------------------------------------------------------- per standard

def _calculate_standard(snapshot, ruleset, params, shares,
                        buy, end, end_kind, days_held):
    row = se.screen(snapshot, ruleset, params)
    pur = row["purification"]
    entry = {
        "standard": ruleset["standard_id"],
        "name_en": ruleset.get("name_en"),
        "name_ar": ruleset.get("name_ar"),
        "ruleset_version": ruleset["ruleset_version"],
        "engine_version": row["engine_version"],
        "parameters": row["parameters"],
        "screening_verdict": row["verdict"],
        "statement_period": row["statement_period"],
        "purification": {"defined": pur["defined"],
                         "ratio": pur["ratio"],
                         "per_share": pur["per_share"]},
        "dividend_events": [],
        "components": {
            "dividends": {"applies": pur["defined"],
                          "amount": None, "events_counted": 0},
            "capital": {"applies": False, "amount": None},
        },
        "total": None,
        "total_partial": False,
        "status": None,
        "gaps": [],
        "missing_inputs": list(row["missing_inputs"]),
        "framing_en": se.FRAMING_EN,
        "framing_ar": se.FRAMING_AR,
    }

    # Events are standard-independent facts: list every event in
    # the stream with its entitlement determination either way.
    events_known = isinstance(snapshot.get("dividends"), list)
    events = snapshot.get("dividends") if events_known else []
    malformed = False
    entitled_events = []
    for event in events:
        ex = _parse_date(event.get("ex_date"), "ex_date") \
            if isinstance(event, dict) else None
        per_share = event.get("per_share") \
            if isinstance(event, dict) else None
        if ex is None or per_share is None:
            malformed = True
            entry["gaps"].append({
                "en": GAP_EVENT_MALFORMED["en"].format(
                    event=json.dumps(event, ensure_ascii=False,
                                     sort_keys=True, default=str)),
                "ar": GAP_EVENT_MALFORMED["ar"].format(
                    event=json.dumps(event, ensure_ascii=False,
                                     sort_keys=True, default=str)),
            })
            continue
        entitled, reason = _entitlement(buy, end, end_kind, ex)
        item = {"ex_date": event.get("ex_date"),
                "pay_date": event.get("pay_date"),
                "per_share": per_share,
                "entitled": entitled,
                "reason_en": reason["en"],
                "reason_ar": reason["ar"],
                "purification": None}
        entry["dividend_events"].append(item)
        if entitled:
            entitled_events.append(item)

    # --- no purification rule under this standard (e.g. EGX33)
    if not pur["defined"]:
        entry["status"] = STATUS_NO_RULE
        entry["components"]["dividends"]["reason_en"] = \
            REASON_NO_RULE["en"]
        entry["components"]["dividends"]["reason_ar"] = \
            REASON_NO_RULE["ar"]
        entry["components"]["capital"]["reason_en"] = \
            REASON_NO_RULE["en"]
        entry["components"]["capital"]["reason_ar"] = \
            REASON_NO_RULE["ar"]
        return entry

    gaps = entry["gaps"]
    if not events_known:
        gaps.append(dict(GAP_EVENTS_UNAVAILABLE))
    else:
        coverage = _parse_date(snapshot.get("screening_date"),
                               "screening_date")
        if coverage is None:
            gaps.append(dict(GAP_NO_SCREENING_DATE))
        elif end > coverage:
            gaps.append({
                "en": GAP_COVERAGE["en"].format(
                    coverage=coverage.isoformat(),
                    window_end=end.isoformat()),
                "ar": GAP_COVERAGE["ar"].format(
                    coverage=coverage.isoformat(),
                    window_end=end.isoformat()),
            })

    # --- engine figures the calculator needs: the purification
    # ratio always; the per-share figure only where the rule set
    # declares a capital component (issue #169: MSCI / FTSE /
    # Islamicly publish a dividend purification ratio only, and
    # their rows carry no per-share figure).
    declaration = (ruleset.get("purification") or {}).get(
        "capital_component") or {}
    if pur["ratio"] is None or (declaration.get("applies")
                                and pur["per_share"] is None):
        entry["status"] = STATUS_INSUFFICIENT
        return entry

    # --- dividend component: DPS x ratio x shares, per entitled
    # event, from the event stream -- no manual entry.
    div = entry["components"]["dividends"]
    if events_known:
        total_div = 0.0
        for item in entitled_events:
            amount = item["per_share"] * pur["ratio"] * shares
            item["purification"] = _round6(amount)
            total_div += amount
        div["amount"] = _round6(total_div)
        div["events_counted"] = len(entitled_events)

    # --- capital component, where the rule set declares it
    cap = entry["components"]["capital"]
    cap["applies"] = bool(declaration.get("applies"))
    cap["method"] = declaration.get("method")
    if not cap["applies"]:
        cap["amount"] = 0.0
        cap["reason_en"] = REASON_NO_CAPITAL["en"]
        cap["reason_ar"] = REASON_NO_CAPITAL["ar"]
    else:
        period = snapshot.get("statement_period") or {}
        p_start = _parse_date(period.get("start"),
                              "statement_period.start")
        p_end = _parse_date(period.get("end"),
                            "statement_period.end")
        if p_start is None or p_end is None:
            if "statement_period" not in entry["missing_inputs"]:
                entry["missing_inputs"].append("statement_period")
            entry["status"] = STATUS_INSUFFICIENT
            return entry
        days_in_period = (p_end - p_start).days + 1
        fraction = days_held / days_in_period
        capped = fraction > 1.0
        if capped:
            fraction = 1.0
        cap["days_held"] = days_held
        cap["days_in_period"] = days_in_period
        cap["fraction"] = _round6(fraction)
        cap["capped"] = capped
        if capped:
            cap["reason_en"] = REASON_CAPITAL_CAPPED["en"]
            cap["reason_ar"] = REASON_CAPITAL_CAPPED["ar"]
        cap["amount"] = _round6(pur["per_share"] * fraction
                                * shares)

    # --- total: only over components that produced a figure.
    amounts = [c["amount"] for c in entry["components"].values()
               if c["applies"]]
    if amounts and all(a is not None for a in amounts):
        entry["total"] = _round6(sum(amounts))
    if gaps or malformed:
        entry["status"] = STATUS_PARTIAL
        entry["total_partial"] = entry["total"] is not None
    else:
        entry["status"] = STATUS_OK
    return entry


# ------------------------------------------------------- top level

def _rule_differences(entries):
    """Name how the selected standards' purification rules
    differ -- the side-by-side is only honest if the difference
    travels with the numbers."""
    diffs = []
    defining = [e for e in entries if e["purification"]["defined"]]
    not_defining = [e for e in entries
                    if not e["purification"]["defined"]]
    for a in defining:
        for b in not_defining:
            diffs.append({
                "en": ("%s defines a purification rule (a ratio "
                       "and a per-share figure, computed by the "
                       "engine); %s publishes no purification "
                       "rule, so no purification amount is "
                       "computed under %s."
                       % (a["standard"], b["standard"],
                          b["standard"])),
                "ar": ("%s يعرّف قاعدة تطهير (نسبة وقيمة للسهم "
                       "يحسبها المحرك)؛ أما %s فلا ينشر قاعدة "
                       "تطهير، فلا تُحسب قيمة تطهير وفقًا له."
                       % (a["standard"], b["standard"])),
            })
    cap_yes = [e for e in defining
               if e["components"]["capital"]["applies"]]
    cap_no = [e for e in defining
              if not e["components"]["capital"]["applies"]]
    for a in cap_yes:
        for b in cap_no:
            diffs.append({
                "en": ("A capital component applies under %s "
                       "(time-apportioned per-share "
                       "non-permissible income) and not under %s."
                       % (a["standard"], b["standard"])),
                "ar": ("ينطبق مكوّن رأس المال وفق %s (الدخل غير "
                       "المتوافق للسهم موزّعًا على أيام الملكية) "
                       "ولا ينطبق وفق %s."
                       % (a["standard"], b["standard"])),
            })
    for i, a in enumerate(defining):
        for b in defining[i + 1:]:
            ra = a["purification"]["ratio"]
            rb = b["purification"]["ratio"]
            if ra is not None and rb is not None and ra != rb:
                diffs.append({
                    "en": ("Purification ratios differ: %s %s "
                           "vs %s %s."
                           % (a["standard"], ra, b["standard"],
                              rb)),
                    "ar": ("تختلف نسبتا التطهير: %s %s مقابل "
                           "%s %s."
                           % (a["standard"], ra, b["standard"],
                              rb)),
                })
    return diffs


def calculate(snapshot, shares, buy_date, sell_date=None,
              as_of=None, standards=None, params=None):
    """Purification for one holding under each selected
    standard. Pure and deterministic.

    ``snapshot`` is one engine snapshot (data model in
    sharia_engine.py); ``standards`` defaults to all implemented
    standards and fails loudly on an unknown one (the #170
    selection contract); ``params`` passes engine parameters
    (e.g. the AAOIFI denominator variant) through to the screen.
    """
    if snapshot is None or not isinstance(snapshot, dict):
        raise ValueError("a snapshot object is required")
    if shares is None or not isinstance(shares, (int, float)) \
            or isinstance(shares, bool) or shares <= 0:
        raise ValueError("shares must be a positive number")
    buy, end, end_kind, days_held = _resolve_window(
        buy_date, sell_date, as_of)

    implemented = se.available_standards()
    if standards is None:
        resolved = list(implemented)
    else:
        resolved = []
        for raw in standards:
            std = str(raw).strip().upper()
            if not std:
                continue
            if std not in implemented:
                raise ValueError(
                    "unknown sharia standard %r: implemented "
                    "standards are %s"
                    % (raw, ", ".join(implemented)))
            if std not in resolved:
                resolved.append(std)
        if not resolved:
            raise ValueError("standards selection names no "
                             "standard")

    entries = []
    for std in resolved:
        ruleset = se.load_ruleset(std)
        entries.append(_calculate_standard(
            snapshot, ruleset, params, shares, buy, end,
            end_kind, days_held))

    return {
        "schema": SCHEMA,
        "calculator": CALCULATOR_PATH,
        "calculator_version": CALCULATOR_VERSION,
        "engine_version": se.ENGINE_VERSION,
        "ticker": snapshot.get("ticker"),
        "shares": shares,
        "window": {"buy_date": buy.isoformat(),
                   "end_date": end.isoformat(),
                   "end_kind": end_kind,
                   "days_held": days_held},
        "framing_en": se.FRAMING_EN,
        "framing_ar": se.FRAMING_AR,
        "standards": entries,
        "rule_differences": _rule_differences(entries),
    }


# ---------------------------------------------------------------- CLI

def _load_snapshot(path, ticker):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    snapshots = data if isinstance(data, list) else [data]
    if ticker is not None:
        for snap in snapshots:
            if isinstance(snap, dict) \
                    and snap.get("ticker") == ticker:
                return snap
        raise ValueError("no snapshot for ticker %s in %s"
                         % (ticker, path))
    if len(snapshots) != 1:
        raise ValueError("%s holds %d snapshots; --ticker is "
                         "required" % (path, len(snapshots)))
    return snapshots[0]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ca = sub.add_parser("calculate",
                        help="purification for one holding")
    ca.add_argument("--snapshot", required=True,
                    help="JSON file: one snapshot object or a "
                         "list of them (engine data model)")
    ca.add_argument("--ticker", default=None,
                    help="select the snapshot by ticker")
    ca.add_argument("--shares", required=True, type=float,
                    help="shares held (constant over the window)")
    ca.add_argument("--buy", required=True,
                    help="buy date, YYYY-MM-DD")
    ca.add_argument("--sell", default=None,
                    help="sell date, YYYY-MM-DD; omit when still "
                         "holding and pass --as-of instead")
    ca.add_argument("--as-of", default=None,
                    help="calculation date for a still-held "
                         "holding, YYYY-MM-DD")
    ca.add_argument("--standard", action="append", default=None,
                    help="standard id (repeatable); default: all "
                         "implemented standards")
    ca.add_argument("--variant", default=None,
                    help="value for a rule set's "
                         "denominator_variant parameter, where it "
                         "defines one (AAOIFI: avg36m|spot)")
    ca.add_argument("--out", default=None,
                    help="write the result JSON here; default: "
                         "stdout")
    args = ap.parse_args(argv)

    try:
        snapshot = _load_snapshot(args.snapshot, args.ticker)
        params = {}
        if args.variant is not None:
            params["denominator_variant"] = args.variant
        result = calculate(snapshot, args.shares, args.buy,
                           sell_date=args.sell, as_of=args.as_of,
                           standards=args.standard, params=params)
    except (ValueError, KeyError, TypeError,
            json.JSONDecodeError) as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2

    text = json.dumps(result, ensure_ascii=False, indent=2,
                      sort_keys=True) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("%s: %s -> %s"
              % (result["ticker"],
                 ", ".join("%s=%s" % (e["standard"], e["status"])
                           for e in result["standards"]),
                 args.out))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
