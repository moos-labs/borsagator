#!/usr/bin/env python3
"""Render worker/cloud-init.yaml.tmpl into a launch-time cloud-init file.

Implements the contract documented in the template header:
  __GATOR_BUS_URL__   -> the borsagator-only bus URL (from --bus-url or
                         the GATOR_BUS_URL environment variable; required)
  __GATOR_ENV_EXTRA__ -> tool API keys, one KEY=value per line, may be empty

Key values are read ONLY from this process's environment at render time
and written ONLY into the rendered output file. They are never printed,
never committed, and never written into the template. The rendered file
contains live secrets: keep it off git (this script refuses an output
path inside the repo) and delete it from this VM after a successful launch.

Key allowlist (names only; D4 decides the FMP variable name):
  COHERE_API_KEY, SIMFIN_API_KEY — read from the environment if present.
  The FMP variable used by financetoolkit-runner is NOT hardcoded: its
  exact name is still unconfirmed (issue #65, D4). Pass it with
  --fmp-var NAME; without it, no FMP line is emitted.
A key that is absent from the environment is simply omitted from the
extra block — no empty KEY= line is emitted. Tools whose keys are absent
fail their run honestly (worker.py docstring); nothing is faked.
"""
import argparse
import os
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "worker" / "cloud-init.yaml.tmpl"
CONFIRMED_KEYS = ("COHERE_API_KEY", "SIMFIN_API_KEY")


def build_extra(fmp_var):
    names = list(CONFIRMED_KEYS)
    if fmp_var:
        names.append(fmp_var)
    lines = []
    for name in names:
        value = os.environ.get(name)
        if value is None or value == "":
            continue  # absent key: omitted, never emitted empty
        if "\n" in value or "\r" in value:
            sys.exit(f"refusing to render: {name} contains a newline")
        lines.append(f"{name}={value}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", default=str(TEMPLATE))
    ap.add_argument("--out", required=True, help="rendered output path (outside the repo)")
    ap.add_argument("--bus-url", default=os.environ.get("GATOR_BUS_URL"))
    ap.add_argument("--fmp-var", default=None,
                    help="exact FMP env var name for financetoolkit-runner (D4); "
                         "omit and no FMP line is emitted")
    args = ap.parse_args()

    if not args.bus_url:
        sys.exit("refusing to render: no bus URL (--bus-url or GATOR_BUS_URL)")
    if "\n" in args.bus_url or "\r" in args.bus_url:
        sys.exit("refusing to render: bus URL contains a newline")

    out = Path(args.out).resolve()
    repo_root = Path(__file__).resolve().parent.parent
    if out.is_relative_to(repo_root):
        sys.exit(f"refusing to render: output {out} is inside the repo "
                 "(rendered cloud-init carries secrets and must never be committed)")

    text = Path(args.template).read_text()
    if "__GATOR_BUS_URL__" not in text or "__GATOR_ENV_EXTRA__" not in text:
        sys.exit("refusing to render: template is missing a placeholder")
    extra = build_extra(args.fmp_var)
    rendered = text.replace("__GATOR_BUS_URL__", args.bus_url)
    # The extra block sits inside a YAML block scalar (content: |), so
    # every line must keep the placeholder line's indent — a bare
    # str.replace would leave the 2nd+ key lines at column 0, which ends
    # the block scalar and breaks the rendered YAML. Replace ONLY the
    # standalone placeholder line: __GATOR_ENV_EXTRA__ also appears in
    # the header comment, and a global replace would inject key lines
    # into that comment (a non-comment line before `packages:` breaks
    # the document).
    m = re.search(r"(?m)^([ \t]*)__GATOR_ENV_EXTRA__$", rendered)
    if not m:
        sys.exit("refusing to render: template is missing the env-extra placeholder line")
    indent = m.group(1)
    # The match spans the placeholder line including its leading indent,
    # so re-apply the indent to the first key line as well.
    rendered_extra = indent + ("\n" + indent).join(extra.splitlines()) if extra else ""
    rendered = rendered[:m.start()] + rendered_extra + rendered[m.end():]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered)
    out.chmod(0o600)
    print(f"rendered {out} (bus URL + {len(extra.splitlines())} key line(s); "
          "delete after launch)")


if __name__ == "__main__":
    main()
