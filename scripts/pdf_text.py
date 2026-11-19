#!/usr/bin/env python3
"""PDF text extraction for disclosure verification (issue #301).

A maintained engine, not a hand-rolled string scanner: text comes
from pypdf (pinned in requirements.txt), which resolves ToUnicode
CMaps, hex strings, FlateDecode streams and font encodings. The
#299 stdlib reader is NOT reused — it collected Tj text before TJ
text, split literals with newlines, and had no font mapping, so
Arabic labels came back undecodable and any partial decode was
still searched as if it were a fact.

Extraction results are classified, never silently degraded:
- "ok": at least one page yielded non-whitespace text.
- "scanned": a structurally valid PDF whose pages yield no text at
  all — an image-only document that needs OCR. A field absent from
  it is INCONCLUSIVE, never "missing".
- "partial": pages beyond MAX_PAGES were not read (the read pages
  are still usable; fields not found there are "not_checked", not
  "missing").
- "unsupported": pypdf is not installed in this environment. The
  verifier reports inconclusive; it never treats this as a pass or
  a fail of the field.
- "unreadable": not a PDF, over the size cap, or pypdf cannot parse
  it.

RTL normalisation: text is extracted in pypdf layout mode, which
returns Arabic in logical order (plain mode reverses RTL runs, e.g.
"الربح" arrives as "حبرلا"). restore_logical_order() is kept for
plain-mode text: it reverses each maximal Arabic-script run
(including the spaces inside it) back to logical order so role
labels match. Matching tries the restored text first and the raw
text second (recorded as text_variant), so a future engine change
that stops reversing does not silently break verification.

Stdlib only except pypdf. Never raises on bad input.
"""
import io
import re

ENGINE_NAME = "pypdf"
ENGINE_VERSION_REQUIRED = "7.1.1"
MAX_PDF_BYTES = 50 * 1024 * 1024  # mirrors worker/attachment_capture.py
MAX_PAGES = 200

_ARABIC_LETTER = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF"
                            r"\uFB50-\uFDFF\uFE70-\uFEFF]")
# A run starts and ends with an Arabic character; inside it, Arabic
# characters, whitespace and neutral punctuation (colon, parens,
# Arabic comma/semicolon, stops) belong to the run. pypdf reverses
# each such run as a unit — including the colon between a label and
# its "من" — so reversing it restores logical word order too
# ("نم :ةرتفلا نع ..." -> "القوائم المالية المجمعة عن الفترة: من").
# ASCII digits, Latin letters and "/" break a run: numbers and dates
# keep their order and position.
_RTL_RUN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
    r"(?:[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF"
    r"\s:()\u060C\u061B\u061F\u066B.,\-"
    r"\u2013\u2014\"'\[\]]*"
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF])?")


def restore_logical_order(text):
    """Reverse each maximal Arabic-script run back to logical order.

    Idempotent on text with no Arabic runs; Latin text, digits and
    punctuation are untouched. A run is reversed as a whole string,
    which restores both letter order inside words and word order
    inside the run.
    """
    if not text or not _ARABIC_LETTER.search(text):
        return text
    return _RTL_RUN.sub(lambda m: m.group(0)[::-1], text)


def _engine_version():
    try:
        import pypdf
        return getattr(pypdf, "__version__", "unknown")
    except ImportError:
        return None


def _font_has_tounicode(font):
    """True when a font dict carries a ToUnicode CMap (Arabic text
    from it maps to real code points); False/None when it does not
    or the object cannot be resolved."""
    try:
        return font.get("/ToUnicode") is not None
    except Exception:
        return None


def _page_fonts(page):
    """[(font_name, has_tounicode|None)] for one page; [] when the
    page has no font resources or they cannot be read."""
    try:
        res = page.get("/Resources") or {}
        fonts = res.get("/Font") or {}
        out = []
        for name, font in dict(fonts).items():
            out.append((str(name), _font_has_tounicode(font)))
        return out
    except Exception:
        return []


def extract_pages(pdf_bytes, max_pages=MAX_PAGES):
    """Extract text page by page.

    Returns {"status", "pages": [{"page", "text", "fonts", "mode"}],
    "engine", "engine_version", "detail", "truncated"}.
    "pages" text is the RAW pypdf output (visual order for RTL);
    callers normalise with restore_logical_order() before matching.
    "mode" records how the page was read — "layout" (Arabic in
    logical order), "plain" (layout failed; plain mode reverses RTL
    runs, so callers must restore logical order and record which
    variant matched), or "failed" (neither mode read the page).
    Never raises.
    """
    version = _engine_version()
    base = {"status": "unreadable", "pages": [], "engine": ENGINE_NAME,
            "engine_version": version, "detail": "", "truncated": False}
    if version is None:
        base["status"] = "unsupported"
        base["detail"] = ("pypdf is not installed — install it "
                          "(requirements.txt) to read PDF text")
        return base
    if not isinstance(pdf_bytes, (bytes, bytearray)) \
            or not bytes(pdf_bytes).startswith(b"%PDF-"):
        base["detail"] = "input is not a PDF (no %PDF- header)"
        return base
    if len(pdf_bytes) > MAX_PDF_BYTES:
        base["detail"] = ("PDF is %d bytes, over the %d-byte cap"
                          % (len(pdf_bytes), MAX_PDF_BYTES))
        return base
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
        n_pages = len(reader.pages)
    except Exception as exc:  # noqa: BLE001 - corrupt/unparseable PDF
        base["detail"] = "pypdf cannot parse this PDF: %s" % str(exc)[:200]
        return base
    pages = []
    truncated = n_pages > max_pages
    for i, page in enumerate(reader.pages[:max_pages]):
        # Layout mode: text in reading order, Arabic in logical
        # order (plain mode reverses RTL runs). Falls back to plain
        # mode for a page layout mode cannot read; the mode is
        # recorded per page (#312) so the verifier knows which
        # reading it is matching against.
        try:
            text = page.extract_text(extraction_mode="layout") or ""
            mode = "layout"
        except Exception:
            try:
                text = page.extract_text() or ""
                mode = "plain"
            except Exception as exc:  # noqa: BLE001 - one bad page
                text = ""
                pages.append({"page": i + 1, "text": text,
                              "fonts": _page_fonts(page), "mode": "failed",
                              "detail": "page text extraction failed: %s"
                              % str(exc)[:120]})
                continue
        pages.append({"page": i + 1, "text": text,
                      "fonts": _page_fonts(page), "mode": mode})
    base["pages"] = pages
    base["truncated"] = truncated
    if not any(p["text"].strip() for p in pages):
        base["status"] = "scanned"
        base["detail"] = ("valid PDF with no extractable text on any "
                          "page — image-only document, OCR required")
        return base
    # A page whose fonts have no ToUnicode mapping cannot yield
    # trustworthy non-ASCII text: Arabic labels there come back as
    # mojibake, not as missing facts. Pure-ASCII pages are unaffected
    # (WinAnsi covers them), so only pages with non-ASCII output are
    # flagged.
    unmapped = [p["page"] for p in pages
                if p["text"].strip()
                and any(ord(c) > 127 for c in p["text"])
                and p["fonts"]
                and all(v is False for _, v in p["fonts"])]
    if unmapped:
        base["status"] = "partial"
        base["detail"] = ("pages %s have fonts without a ToUnicode "
                          "mapping — Arabic labels there are "
                          "undecodable, not absent"
                          % ", ".join(str(n) for n in unmapped))
        return base
    base["status"] = "partial" if truncated else "ok"
    base["detail"] = ("read %d of %d pages (truncated at the page cap)"
                      % (len(pages), n_pages)) if truncated \
        else ("read %d page(s)" % len(pages))
    return base


def extract_text(pdf_bytes, max_pages=MAX_PAGES):
    """Convenience: joined raw text of all read pages ("" when the
    document yields nothing). Use extract_pages() when page numbers
    or the status classification matter."""
    res = extract_pages(pdf_bytes, max_pages=max_pages)
    return "\n".join(p["text"] for p in res["pages"])
