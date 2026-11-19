#!/usr/bin/env python3
"""Minimal PDF text extraction (issue #279) — stdlib only.

Reads the text of a stored disclosure PDF so the extractor's
``verify`` step can check that the fields already extracted from
harvested item text reproduce from the source document. This is a
VERIFICATION aid, not a field extractor: it returns raw text (or
``""`` when nothing is recoverable) and extracts no fields itself.

Coverage: content streams with FlateDecode (zlib) or no filter,
literal strings ``(...)`` shown by ``Tj`` / ``[...] TJ``. Encodings
are NOT resolved (no ToUnicode CMap handling): Arabic glyph text
in custom-encoded fonts comes back as raw bytes, which is fine for
the verify step — it checks ASCII numeric/date tokens (coupon
numbers, amounts, dd/mm/yyyy dates), which survive naive
extraction in the PDFs EGX serves. A PDF whose text is entirely
unrecoverable yields ``""`` and verify reports it explicitly.
"""
import re
import zlib

_STREAM_RE = re.compile(rb"stream\r?\n(.*?)endstream", re.S)
# One PDF literal string, allowing one level of nested parens:
#   \( (?: plain-char | escape | \( (?: plain-char | escape )* \) )* \)
_INNER = r"[^()\\]|\\."
_LITERAL = r"\((?:%s|\((?:%s)*\))*\)" % (_INNER, _INNER)
_LITERAL_RE = re.compile(_LITERAL.encode())
_TJ_OP_RE = re.compile((_LITERAL + r"\s*Tj").encode())
_TJ_ARR_RE = re.compile(rb"\[(?:[^\[\]\\]|\\.)*\]\s*TJ")


def _unescape(raw):
    """PDF literal-string escapes -> bytes."""
    out = bytearray()
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == 0x5C and i + 1 < len(raw):  # backslash
            n = raw[i + 1]
            if n in b"nrtbf":
                out.append({ord("n"): 10, ord("r"): 13, ord("t"): 9,
                            ord("b"): 8, ord("f"): 12}[n])
                i += 2
            elif n in b"()\\":
                out.append(n)
                i += 2
            elif 48 <= n <= 55:  # octal, up to 3 digits
                j = i + 1
                digits = bytearray()
                while j < len(raw) and len(digits) < 3 \
                        and 48 <= raw[j] <= 55:
                    digits.append(raw[j])
                    j += 1
                out.append(int(bytes(digits), 8) & 0xFF)
                i = j
            else:
                out.append(n)
                i += 2
        else:
            out.append(c)
            i += 1
    return bytes(out)


def _decode_stream(stream):
    """One content stream -> bytes (FlateDecode or raw)."""
    try:
        return zlib.decompress(stream)
    except Exception:
        return stream


def _text_from_content(content):
    parts = []
    for m in _TJ_OP_RE.finditer(content):
        lit = m.group(0)
        inner = lit[1:lit.rindex(b")")]
        parts.append(_unescape(inner))
    for m in _TJ_ARR_RE.finditer(content):
        for lit in _LITERAL_RE.findall(m.group(0)):
            parts.append(_unescape(lit[1:-1]))
    # Strings shown by Tj/TJ only: a bare literal that is not
    # followed by a show operator is a metadata string, not page
    # text, and is deliberately ignored.
    return b"\n".join(parts)


def extract_text(pdf_bytes):
    """Best-effort text of a PDF document as a string.

    Returns ``""`` when the input is not a PDF or no show-operator
    text is recoverable. Never raises.
    """
    try:
        if not isinstance(pdf_bytes, (bytes, bytearray)) \
                or not bytes(pdf_bytes).startswith(b"%PDF"):
            return ""
        chunks = []
        for m in _STREAM_RE.finditer(bytes(pdf_bytes)):
            raw = m.group(1)
            if raw.endswith(b"\r\n"):
                raw = raw[:-2]
            elif raw.endswith(b"\n") or raw.endswith(b"\r"):
                raw = raw[:-1]
            chunks.append(_text_from_content(_decode_stream(raw)))
        text = b"\n".join(c for c in chunks if c)
        return text.decode("utf-8", errors="replace")
    except Exception:
        return ""
