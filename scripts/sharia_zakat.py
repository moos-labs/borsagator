#!/usr/bin/env python3
"""Zakat calculator for share holdings (issue #173).

Computes zakat al-mal on ONE share holding under a named,
published method, and itemises every step. Two methods ship,
declared as data in ``scripts/sharia_zakat_methods/`` (the same
declarative pattern as the screening rule sets, issue #168):

* ``TRADING`` -- shares bought for trading are trade goods:
  zakat at the method's rate on the MARKET VALUE at the
  valuation date (the end of the hawl), plus cash dividends
  received during the hawl and still held, when the holder
  declares them (IslamWeb 84386, Dar Al-Ifta Egypt 2110;
  Kashif's trader-zakat calculator is this method).
* ``INVESTMENT`` -- shares held for long-term investment /
  dividends: zakat at the method's rate on the holder's share
  of the company's ZAKATABLE ASSETS per AAOIFI Sharia
  Standard No. 35 (Zakah) -- (cash and liquid assets +
  accounts receivable, the components the screening data
  model carries) per share, times the shares held. Market
  value is not the base, and paid-out dividends are not
  added to it (they are the holder's cash, zakat-able with
  his money -- adding them would double-count earnings
  already inside the company's zakatable assets).

Every parameter that can move the number is an explicit input
with its source and date recorded on the output: the price per
share, the nisab metal price, the calendar (lunar 354-day hawl
at 2.5%, or Gregorian 365-day hawl at 2.577% -- AAOIFI Std 35
raises the rate on a Gregorian year, as cited by Amal
Invest). NO wall clock, NO hidden defaults: the method files
declare the published defaults (nisab 85 g gold / 595 g
silver; hawl lengths; rates), a case may override the grams,
and the result echoes what was used. If no nisab input is
given, the amount is still computed but the status is
``nisab-not-provided`` -- the due-ness determination is the
owner's wealth-level test (published guidance judges nisab on
all zakatable wealth together), and the calculator does not
fake it per-holding.

Statuses: ``due`` / ``below-nisab`` (zakat 0, reason stated;
a base exactly AT the nisab is due) / ``hawl-not-complete``
(zakat 0, reason stated) / ``insufficient-data`` (zakat null,
missing inputs named -- never a guessed figure) /
``nisab-not-provided`` (amount computed, nisab test not
performed). The hawl is measured on the holding by default;
a case may instead declare the hawl complete (basis
``declared``, with a note) -- the published basis for shares
bought with money whose hawl is already running, which join
the owner's existing zakat date (IslamWeb fatwa 69087).

FRAMING (binding, from the issue): every output is a
calculation under the named published method -- never a
fatwa and never religious or investment advice. The framing
lines and the method statement ship in English and Arabic at
the top level and on every result; final wording is reviewed
under issue #77. Where published methods differ (the
yield-only position for investment shares; the NZF 25% /
ZakatCalc 30% estimation proxies; Almurakib's published
investment formula), the method files record the alternatives
-- they are never blended into a number.

Stdlib only, deterministic, no network, no wall clock.

Usage:
    sharia_zakat.py calculate --case case.json [--out r.json]
    sharia_zakat.py calculate --ticker POUL.CA --method TRADING
        --shares 10000 --buy 2025-01-06 --valuation 2026-01-10
        --price 8.02 --price-source "..." --price-date 2026-11-16
        --nisab-basis gold --nisab-price-per-gram 4000
        --nisab-source "..." --nisab-date 2026-11-18
        [--snapshot snapshots.json] [--calendar gregorian]
        [--hawl declared --hawl-note "..."]
        [--dividends-received-held 19000] [--currency EGP]

Exit codes: 0 = result produced (status carries the data
state); 2 = bad input / unknown method (fail loudly, nothing
written); 1 = crash.
"""
import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharia_engine as se  # noqa: E402

CALCULATOR_VERSION = "1.0.0"
SCHEMA = "borsagator-sharia-zakat/1"
CALCULATOR_PATH = "scripts/sharia_zakat.py"
METHODS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "sharia_zakat_methods")

FRAMING_EN = ("Zakat calculation under the named published method "
              "only, computed from the inputs shown. This is not a "
              "fatwa, and not religious or investment advice.")
FRAMING_AR = ("حساب زكاة وفق الطريقة المنشورة المذكورة فقط، محسوب من "
              "المدخلات المعروضة. ليس فتوى، وليس نصيحة دينية أو "
              "استثمارية.")

STATUS_DUE = "due"
STATUS_BELOW_NISAB = "below-nisab"
STATUS_HAWL = "hawl-not-complete"
STATUS_INSUFFICIENT = "insufficient-data"
STATUS_NO_NISAB = "nisab-not-provided"

CALENDARS = ("lunar", "gregorian")
NISAB_BASES = ("gold", "silver")

# ------------------------------------------------------- wording

REASON_BELOW_NISAB = {
    "en": ("The zakat base is below the nisab on the declared "
           "basis, so no zakat is due on this holding under "
           "this method."),
    "ar": ("الوعاء الزكوي أقل من النصاب على الأساس المعلن، فلا "
           "زكاة واجبة على هذه الملكية وفق هذه الطريقة."),
}
REASON_AT_NISAB = {
    "en": ("The zakat base is exactly at the nisab; the nisab "
           "is met, so zakat is due."),
    "ar": ("الوعاء الزكوي مساوٍ للنصاب تمامًا؛ فالنصاب متحقّق "
           "وتجب الزكاة."),
}
REASON_ABOVE_NISAB = {
    "en": "The zakat base is above the nisab; zakat is due.",
    "ar": "الوعاء الزكوي فوق النصاب؛ تجب الزكاة.",
}
REASON_HAWL_INCOMPLETE = {
    "en": ("A full hawl has not passed on this holding "
           "({days} of {hawl} days), so no zakat is due yet "
           "under this method."),
    "ar": ("لم يمر حول كامل على هذه الملكية ({days} من {hawl} "
           "يومًا)، فلا تجب الزكاة بعد وفق هذه الطريقة."),
}
REASON_HAWL_DECLARED = {
    "en": ("Hawl taken as complete on the declared basis "
           "recorded with the inputs (the holding joins the "
           "owner's existing zakat date), not measured on the "
           "holding's own dates."),
    "ar": ("اعتُبر الحول مكتملًا على الأساس المعلن المسجل مع "
           "المدخلات (تنضم الملكية إلى تاريخ زكاة المالك "
           "القائم)، لا مقاسًا على تواريخ الملكية نفسها."),
}
REASON_NO_NISAB = {
    "en": ("No nisab input was provided, so the nisab test "
           "was not performed: the amount shown is the "
           "method's rate applied to the base, conditional on "
           "the owner's wealth meeting the nisab. Published "
           "guidance judges the nisab on all of the owner's "
           "zakatable wealth together, not per holding."),
    "ar": ("لم يُقدَّم مدخل للنصاب، فلم يُجرَ اختبار النصاب: "
           "المبلغ المعروض هو نسبة الطريقة مطبقة على الوعاء، "
           "مشروطًا ببلوغ مال المالك النصاب. ووفق الإرشاد "
           "المنشور يُحكم على النصاب من مجموع مال المالك "
           "الزكوي لا لكل ملكية على حدة."),
}
REASON_DIV_EXCLUDED = {
    "en": ("A dividends_received_held figure was provided "
           "under the INVESTMENT method. Per the method's "
           "published rule it is NOT added to the share base "
           "(paid-out dividends are the holder's cash, "
           "zakat-able with his money); it is shown here as "
           "excluded, not silently dropped."),
    "ar": ("قُدّم رقم توزيعات محفوظة وفق طريقة الاستثمار. "
           "ووفق قاعدة الطريقة المنشورة لا يُضاف إلى وعاء "
           "السهم (التوزيعات المدفوعة نقد المالك وتُزكّى مع "
           "ماله)؛ يُعرض هنا مستبعدًا لا محذوفًا بصمت."),
}
REASON_DIV_NOT_PROVIDED = {
    "en": ("No dividends_received_held figure was provided; "
           "the base is the market value alone. Unspent "
           "dividends are never estimated."),
    "ar": ("لم يُقدَّم رقم توزيعات محفوظة؛ الوعاء هو القيمة "
           "السوقية وحدها. لا تُقدَّر التوزيعات غير المنفقة "
           "أبدًا."),
}


def _round6(x):
    return round(float(x), 6)


def _parse_date(value, field):
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), "
                         "got %r" % (field, value))


# ------------------------------------------------------- methods

def available_methods():
    out = []
    for name in sorted(os.listdir(METHODS_DIR)):
        if name.endswith(".json"):
            with open(os.path.join(METHODS_DIR, name),
                      encoding="utf-8") as fh:
                out.append(json.load(fh)["method_id"])
    return out


def load_method(method_id):
    path = os.path.join(METHODS_DIR, method_id.lower() + ".json")
    if not os.path.exists(path):
        raise ValueError("unknown zakat method %r: implemented "
                         "methods are %s"
                         % (method_id,
                            ", ".join(available_methods())))
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------- bases

def _base_trading(method, case, missing):
    shares = case["shares"]
    price = case.get("price_per_share")
    if price is None:
        missing.append("price_per_share")
        return None, [], []
    components = [{
        "id": "market_value",
        "label_en": method["base"]["components"][0]["label_en"],
        "label_ar": method["base"]["components"][0]["label_ar"],
        "amount": _round6(shares * price),
        "detail": {"shares": shares, "price_per_share": price,
                   "price_source": case.get("price_source"),
                   "price_date": case.get("price_date")},
    }]
    total = shares * price
    notes = []
    div = case.get("dividends_received_held")
    if div is None:
        notes.append(REASON_DIV_NOT_PROVIDED)
    else:
        components.append({
            "id": "dividends_received_held",
            "label_en": method["base"]["components"][1]["label_en"],
            "label_ar": method["base"]["components"][1]["label_ar"],
            "amount": _round6(div),
            "detail": {"declared_by": "holder"},
        })
        total += div
    return total, components, notes


def _base_investment(method, case, missing):
    snap = case.get("snapshot")
    if not isinstance(snap, dict):
        missing.append("snapshot")
        return None, [], []
    fin = snap.get("financials") or {}
    fields = method["base"]["fields"]
    divisor = method["base"]["divisor_field"]
    values = {}
    for f in fields + [divisor]:
        if fin.get(f) is None:
            missing.append("financials." + f)
        else:
            values[f] = fin[f]
    if missing:
        return None, [], []
    if values[divisor] == 0:
        missing.append("financials.%s (zero divisor)" % divisor)
        return None, [], []
    per_share = sum(values[f] for f in fields) / values[divisor]
    components = [{
        "id": "zakatable_assets_per_share",
        "label_en": ("Zakatable assets per share: (%s) / %s"
                     % (" + ".join(fields), divisor)),
        "label_ar": ("الموجودات الزكوية للسهم الواحد: (%s) / %s"
                     % (" + ".join(fields), divisor)),
        "amount": _round6(per_share * case["shares"]),
        "detail": {"per_share": _round6(per_share),
                   "fields": {f: values[f] for f in fields},
                   divisor: values[divisor],
                   "shares": case["shares"],
                   "statement_period": snap.get(
                       "statement_period"),
                   "not_yet_in_data_model":
                       method["base"]["not_yet_in_data_model"]},
    }]
    notes = []
    if case.get("dividends_received_held") is not None:
        notes.append(REASON_DIV_EXCLUDED)
    return per_share * case["shares"], components, notes


# ------------------------------------------------------- core

def calculate(case):
    """Zakat for one holding under one named published method.

    ``case`` is a plain dict (see the module docstring / the
    worked-case fixtures). Pure and deterministic: no network,
    no wall clock -- every date and price is an input.
    """
    if not isinstance(case, dict):
        raise ValueError("a case object is required")
    method_id = str(case.get("method") or "").strip().upper()
    if not method_id:
        raise ValueError("case.method is required")
    method = load_method(method_id)

    shares = case.get("shares")
    if shares is None or not isinstance(shares, (int, float)) \
            or isinstance(shares, bool) or shares <= 0:
        raise ValueError("shares must be a positive number")
    buy = _parse_date(case.get("buy_date"), "buy_date")
    valuation = _parse_date(case.get("valuation_date"),
                            "valuation_date")
    if buy is None:
        raise ValueError("buy_date is required")
    if valuation is None:
        raise ValueError("valuation_date is required")
    if valuation < buy:
        raise ValueError("valuation_date %s is before buy_date %s"
                         % (valuation, buy))
    calendar = str(case.get("calendar") or "lunar").strip().lower()
    if calendar not in CALENDARS:
        raise ValueError("calendar must be one of %s, got %r"
                         % (", ".join(CALENDARS),
                            case.get("calendar")))
    div = case.get("dividends_received_held")
    if div is not None and (not isinstance(div, (int, float))
                            or isinstance(div, bool) or div < 0):
        raise ValueError("dividends_received_held must be a "
                         "non-negative number when provided")

    rate = method["rates"][calendar]
    hawl_days = method["hawl_days"][calendar]
    days_held = (valuation - buy).days

    # --- hawl
    hawl_in = case.get("hawl") or {}
    hawl_basis = str(hawl_in.get("basis") or "holding").lower()
    if hawl_basis not in ("holding", "declared"):
        raise ValueError("hawl.basis must be 'holding' or "
                         "'declared', got %r" % hawl_in.get("basis"))
    if hawl_basis == "declared":
        hawl = {"basis": "declared", "complete": True,
                "days_held": days_held, "hawl_days": hawl_days,
                "note": hawl_in.get("note"),
                "reason_en": REASON_HAWL_DECLARED["en"],
                "reason_ar": REASON_HAWL_DECLARED["ar"]}
    else:
        hawl = {"basis": "holding",
                "complete": days_held >= hawl_days,
                "days_held": days_held, "hawl_days": hawl_days}

    # --- base (missing inputs are collected, never guessed)
    missing = []
    if method["base"]["kind"] == "market_value":
        base, components, notes = _base_trading(method, case,
                                                missing)
    else:
        base, components, notes = _base_investment(method, case,
                                                   missing)

    result = {
        "schema": SCHEMA,
        "calculator": CALCULATOR_PATH,
        "calculator_version": CALCULATOR_VERSION,
        "ticker": case.get("ticker"),
        "currency": case.get("currency"),
        "method": {
            "id": method["method_id"],
            "version": method["method_version"],
            "intent": method["intent"],
            "name_en": method["name_en"],
            "name_ar": method["name_ar"],
            "statement_en": method["statement_en"],
            "statement_ar": method["statement_ar"],
            "dividends_rule_en": method["dividends"]["rule_en"],
            "dividends_rule_ar": method["dividends"]["rule_ar"],
            "sources": method["sources"],
        },
        "framing_en": FRAMING_EN,
        "framing_ar": FRAMING_AR,
        "inputs": {
            "shares": shares,
            "buy_date": buy.isoformat(),
            "valuation_date": valuation.isoformat(),
            "calendar": calendar,
            "price_per_share": case.get("price_per_share"),
            "price_source": case.get("price_source"),
            "price_date": case.get("price_date"),
            "dividends_received_held": div,
            "snapshot_ticker": (case.get("snapshot") or {}).get(
                "ticker") if isinstance(case.get("snapshot"),
                                        dict) else None,
            "snapshot_statement_period": (
                case.get("snapshot") or {}).get(
                    "statement_period") if isinstance(
                        case.get("snapshot"), dict) else None,
        },
        "hawl": hawl,
        "rate": rate,
        "notes": notes,
    }

    if missing:
        result["status"] = STATUS_INSUFFICIENT
        result["missing_inputs"] = missing
        result["base"] = None
        result["nisab_check"] = {"performed": False,
                                 "reason_en": "The base could "
                                 "not be computed (insufficient "
                                 "data), so no nisab test was "
                                 "performed.",
                                 "reason_ar": "تعذّر حساب الوعاء "
                                 "(بيانات غير كافية)، فلم يُجرَ "
                                 "اختبار النصاب."}
        result["zakat"] = None
        return result

    result["base"] = {"components": components,
                      "total": _round6(base)}

    # --- nisab
    nisab_in = case.get("nisab")
    if nisab_in is None:
        result["nisab_check"] = {"performed": False,
                                 "reason_en": REASON_NO_NISAB["en"],
                                 "reason_ar": REASON_NO_NISAB["ar"]}
        result["zakat"] = _round6(base * rate)
        result["status"] = (STATUS_NO_NISAB if hawl["complete"]
                            else STATUS_HAWL)
        if not hawl["complete"]:
            result["zakat"] = 0
            result["notes"] = notes + [{
                "en": REASON_HAWL_INCOMPLETE["en"].format(
                    days=days_held, hawl=hawl_days),
                "ar": REASON_HAWL_INCOMPLETE["ar"].format(
                    days=days_held, hawl=hawl_days)}]
        return result

    basis = str(nisab_in.get("basis") or "").strip().lower()
    if basis not in NISAB_BASES:
        raise ValueError("nisab.basis must be one of %s, got %r"
                         % (", ".join(NISAB_BASES),
                            nisab_in.get("basis")))
    grams = nisab_in.get("grams")
    if grams is None:
        grams = method["nisab_grams"][basis]
    ppg = nisab_in.get("price_per_gram")
    if ppg is None or not isinstance(ppg, (int, float)) \
            or isinstance(ppg, bool) or ppg <= 0:
        raise ValueError("nisab.price_per_gram must be a "
                         "positive number")
    nisab_value = grams * ppg
    if base < nisab_value:
        relation, reason = "below", REASON_BELOW_NISAB
    elif base == nisab_value:
        relation, reason = "at", REASON_AT_NISAB
    else:
        relation, reason = "above", REASON_ABOVE_NISAB
    result["nisab_check"] = {
        "performed": True,
        "basis": basis,
        "grams": grams,
        "price_per_gram": ppg,
        "price_source": nisab_in.get("price_source"),
        "price_date": nisab_in.get("price_date"),
        "nisab_value": _round6(nisab_value),
        "relation": relation,
        "reason_en": reason["en"],
        "reason_ar": reason["ar"],
    }

    if not hawl["complete"]:
        result["status"] = STATUS_HAWL
        result["zakat"] = 0
        result["notes"] = notes + [{
            "en": REASON_HAWL_INCOMPLETE["en"].format(
                days=days_held, hawl=hawl_days),
            "ar": REASON_HAWL_INCOMPLETE["ar"].format(
                days=days_held, hawl=hawl_days)}]
    elif relation == "below":
        result["status"] = STATUS_BELOW_NISAB
        result["zakat"] = 0
    else:
        result["status"] = STATUS_DUE
        result["zakat"] = _round6(base * rate)
    return result


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


def _case_from_args(args):
    if args.case:
        with open(args.case, encoding="utf-8") as fh:
            case = json.load(fh)
        if args.snapshot:
            case["snapshot"] = _load_snapshot(
                args.snapshot, case.get("ticker"))
        return case
    case = {"ticker": args.ticker, "method": args.method,
            "shares": args.shares, "buy_date": args.buy,
            "valuation_date": args.valuation,
            "calendar": args.calendar,
            "price_per_share": args.price,
            "price_source": args.price_source,
            "price_date": args.price_date,
            "dividends_received_held":
                args.dividends_received_held,
            "currency": args.currency,
            "hawl": {"basis": args.hawl,
                     "note": args.hawl_note}}
    if args.snapshot:
        case["snapshot"] = _load_snapshot(args.snapshot,
                                          args.ticker)
    if args.nisab_basis:
        case["nisab"] = {"basis": args.nisab_basis,
                         "grams": args.nisab_grams,
                         "price_per_gram":
                             args.nisab_price_per_gram,
                         "price_source": args.nisab_source,
                         "price_date": args.nisab_date}
    return case


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ca = sub.add_parser("calculate",
                        help="zakat for one holding under one "
                             "named published method")
    ca.add_argument("--case", default=None,
                    help="JSON file holding the whole case")
    ca.add_argument("--ticker", default=None)
    ca.add_argument("--method", default=None,
                    help="TRADING or INVESTMENT")
    ca.add_argument("--shares", type=float, default=None)
    ca.add_argument("--buy", default=None,
                    help="buy date, YYYY-MM-DD")
    ca.add_argument("--valuation", default=None,
                    help="zakat valuation date, YYYY-MM-DD")
    ca.add_argument("--calendar", default="lunar",
                    help="lunar (default) or gregorian")
    ca.add_argument("--price", type=float, default=None,
                    help="price per share at the valuation date "
                         "(TRADING)")
    ca.add_argument("--price-source", default=None)
    ca.add_argument("--price-date", default=None)
    ca.add_argument("--dividends-received-held", type=float,
                    default=None,
                    help="cash dividends received during the "
                         "hawl and still held, as declared by "
                         "the holder")
    ca.add_argument("--snapshot", default=None,
                    help="JSON file of engine snapshots "
                         "(INVESTMENT reads the financials)")
    ca.add_argument("--nisab-basis", default=None,
                    help="gold or silver; omit for no nisab "
                         "test")
    ca.add_argument("--nisab-grams", type=float, default=None,
                    help="override the method's declared grams "
                         "(gold 85 / silver 595)")
    ca.add_argument("--nisab-price-per-gram", type=float,
                    default=None)
    ca.add_argument("--nisab-source", default=None)
    ca.add_argument("--nisab-date", default=None)
    ca.add_argument("--hawl", default="holding",
                    help="holding (measured on the holding) or "
                         "declared (caller asserts the hawl)")
    ca.add_argument("--hawl-note", default=None)
    ca.add_argument("--currency", default=None)
    ca.add_argument("--out", default=None,
                    help="write the result JSON here; default: "
                         "stdout")
    args = ap.parse_args(argv)

    try:
        result = calculate(_case_from_args(args))
    except (ValueError, KeyError, TypeError,
            json.JSONDecodeError) as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2

    text = json.dumps(result, ensure_ascii=False, indent=2,
                      sort_keys=True) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("%s: %s/%s zakat=%s -> %s"
              % (result["ticker"], result["method"]["id"],
                 result["status"], result["zakat"], args.out))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
