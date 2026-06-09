#!/usr/bin/env python3
"""Map-freshness (completeness-drift) dashboard for published maps (maps#34).

`signatures/<app>/signatures.yaml` is the SOURCE OF TRUTH (AGENTS.md): the set
of class rules it carries is the set of classes a map for that app is EXPECTED
to resolve. Over time the signatures grow new class rules; a published
`maps/<app>/<version_code>.json` generated before a rule was added will be
MISSING that class — it is STALE relative to the current signatures
(completeness drift). This check surfaces that drift as a dashboard.

NON-BLOCKING BY DESIGN (the central contract). A stale map is NORMAL and
MERGEABLE: a signatures-only PR that adds a class rule legitimately strands
every older map (you regenerate them on your own cadence, one
`(app, version_code)` per PR). So a staleness FINDING NEVER fails the build —
the script exits 0 whenever the only issue is "a map is stale". A non-zero exit
is reserved EXCLUSIVELY for the script's OWN malformed inputs: a signatures
file or map that cannot be read / parsed (garbled YAML or JSON, a non-list
signatures doc, a map whose `classes` is not an object). Those are real
breakage the other validators also reject; everything else is advisory.

SHARED ALGORITHM (the rosetta-frida CLI implements the IDENTICAL contract so a
map's freshness is computed the same way on both sides):

  1. For each app, parse `signatures/<app>/signatures.yaml` to the SET of real
     FQNs its class rules claim to find. A rule's FQN is `<package>.<name>`,
     where the sigmatcher `$`-nesting in `name` is carried through verbatim:
     a rule `name: 'IRemoteService$Stub'` with `package: 'com.example.app'`
     yields the FQN `com.example.app.IRemoteService$Stub` — which is exactly
     the spelling of the map's `classes` KEY for that class. (No `$`→`.`
     rewrite: map keys keep the `$` nested-class separator.)
  2. For each `maps/<app>/<version_code>.json`, take the SET of its `classes`
     object keys.
  3. `missing = ruleFQNs - mapClassKeys`. Non-empty ⇒ the map is STALE; the
     missing FQNs are the rules the map does not yet resolve.

A map with no missing rules is FRESH (not flagged). A map for an app that has
no signatures directory at all is simply not analysed (no expectation set).

DASHBOARD. Findings are printed to stdout AND, when `$GITHUB_STEP_SUMMARY` is
set (GitHub Actions), appended there as a markdown table so the PR's checks tab
shows the drift without failing. The summary is the point — it is a visible,
non-blocking nudge to regenerate, not a gate.

It is APK-free (Hard rule 3): it reads ONLY the committed signatures YAML and
map JSON. PyYAML is its only non-stdlib dependency, like `lint_signatures.py`.

Usage:
    check_map_freshness.py MAPS_ROOT SIGS_ROOT   # analyse a corpus
    check_map_freshness.py --self-test           # run built-in fixtures

Exit status: 0 for a clean run OR a run whose only findings are stale maps;
non-zero ONLY when an input is malformed (unreadable/garbled YAML or JSON).
"""

from __future__ import annotations

import glob
import json
import os
import sys
from dataclasses import dataclass, field

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    print("error: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


# --- signatures -> expected FQNs --------------------------------------------


class MalformedInput(Exception):
    """Raised when an input cannot be read/parsed — the ONLY non-zero exit."""


def rule_fqns(doc: object, where: str) -> set[str]:
    """Return the SET of `<package>.<name>` FQNs a signatures document claims.

    The sigmatcher `$`-nesting in a rule `name` is carried through verbatim, so
    a rule `IRemoteService$Stub` + `package: com.example.app` yields the FQN
    `com.example.app.IRemoteService$Stub` — identical to the map's `classes`
    key. Raises MalformedInput when the document is not the expected
    non-empty list of rule mappings (mirrors `lint_signatures.py`'s shape),
    since an unparseable source-of-truth is real breakage, not drift.
    """
    if not isinstance(doc, list) or not doc:
        raise MalformedInput(f"{where}: top level must be a non-empty list of rule entries")
    fqns: set[str] = set()
    for i, rule in enumerate(doc):
        if not isinstance(rule, dict):
            raise MalformedInput(f"{where}: rule[{i}] must be a mapping")
        name = rule.get("name")
        package = rule.get("package")
        if not isinstance(name, str) or not name.strip():
            raise MalformedInput(f"{where}: rule[{i}] missing required non-empty string 'name'")
        if not isinstance(package, str) or not package.strip():
            raise MalformedInput(f"{where}: rule[{i}] missing required non-empty string 'package'")
        fqns.add(f"{package}.{name}")
    return fqns


def load_rule_fqns(path: str) -> set[str]:
    """Read a signatures YAML file and return its expected-FQN set."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
    except OSError as exc:
        raise MalformedInput(f"{path}: could not read file: {exc}") from exc
    except yaml.YAMLError as exc:
        raise MalformedInput(f"{path}: could not parse YAML: {exc}") from exc
    return rule_fqns(doc, path)


# --- maps -> class-key set --------------------------------------------------


def map_class_keys(doc: object, where: str) -> set[str]:
    """Return the SET of a map's `classes` object keys.

    Raises MalformedInput when the map is not an object or its `classes` is not
    an object — the schema validator rejects these too; here they are the
    malformed-input case that DOES fail, separate from staleness.
    """
    if not isinstance(doc, dict):
        raise MalformedInput(f"{where}: map is not a JSON object")
    classes = doc.get("classes")
    if not isinstance(classes, dict):
        raise MalformedInput(f"{where}: map 'classes' is not an object")
    return set(classes.keys())


def load_map_class_keys(path: str) -> set[str]:
    """Read a map JSON file and return its `classes` key set."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except OSError as exc:
        raise MalformedInput(f"{path}: could not read file: {exc}") from exc
    except ValueError as exc:
        raise MalformedInput(f"{path}: could not parse JSON: {exc}") from exc
    return map_class_keys(doc, path)


# --- analysis ---------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One stale map: the rule FQNs it does not yet resolve."""

    map_path: str
    app: str
    version_code: str
    missing: tuple[str, ...]


@dataclass
class Report:
    """The outcome of analysing a corpus."""

    findings: list[Finding] = field(default_factory=list)
    maps_checked: int = 0
    apps_with_signatures: int = 0


def analyse(map_app_keys: dict[str, set[str]], sig_app_fqns: dict[str, set[str]]) -> Report:
    """Pure analysis core: compute stale maps from already-parsed inputs.

    `map_app_keys` maps a map PATH to its `classes` key set; `sig_app_fqns`
    maps an APP to its expected-FQN set. A map is stale when its app has
    signatures and `ruleFQNs - mapClassKeys` is non-empty. No I/O — so the
    self-test drives it directly and any client can reuse it.
    """
    report = Report(apps_with_signatures=len(sig_app_fqns))
    for map_path, keys in sorted(map_app_keys.items()):
        report.maps_checked += 1
        app = _app_of(map_path)
        expected = sig_app_fqns.get(app)
        if not expected:
            continue  # no signatures for this app — no expectation set
        missing = expected - keys
        if missing:
            report.findings.append(
                Finding(
                    map_path=map_path,
                    app=app,
                    version_code=os.path.splitext(os.path.basename(map_path))[0],
                    missing=tuple(sorted(missing)),
                )
            )
    return report


def _app_of(map_path: str) -> str:
    """The app directory name for a `maps/<app>/<version_code>.json` path."""
    return os.path.basename(os.path.dirname(map_path))


# --- corpus loading + reporting ---------------------------------------------


def _iter_maps(maps_root: str) -> list[str]:
    """Every `maps/<app>/<version_code>.json`, pruning attestation sidecars.

    Mirrors validate.yml: the `<version_code>.json.att.json` sidecar matches
    `*.json` and must be excluded. (`.json.sha256` sidecars don't match.)
    """
    out: list[str] = []
    for f in glob.glob(os.path.join(maps_root, "**", "*.json"), recursive=True):
        if f.endswith(".json.att.json"):
            continue
        out.append(f)
    return sorted(out)


def _iter_signatures(sigs_root: str) -> list[str]:
    """Every `signatures/<app>/signatures.yaml` under the signatures root."""
    return sorted(glob.glob(os.path.join(sigs_root, "**", "signatures.yaml"), recursive=True))


def load_corpus(maps_root: str, sigs_root: str) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Load the map class-key sets and the per-app expected-FQN sets.

    Raises MalformedInput on the first unreadable/garbled input.
    """
    sig_app_fqns: dict[str, set[str]] = {}
    for sig_path in _iter_signatures(sigs_root):
        app = _app_of(sig_path)
        sig_app_fqns[app] = load_rule_fqns(sig_path)

    map_app_keys: dict[str, set[str]] = {}
    for map_path in _iter_maps(maps_root):
        map_app_keys[map_path] = load_map_class_keys(map_path)

    return map_app_keys, sig_app_fqns


def render_summary(report: Report) -> str:
    """Render the findings as a GitHub-flavoured markdown dashboard table."""
    lines = ["## Map freshness (completeness drift)", ""]
    if not report.findings:
        lines.append(
            f"All {report.maps_checked} map(s) are fresh against the current "
            f"signatures ({report.apps_with_signatures} app(s) with signatures)."
        )
        lines.append("")
        return "\n".join(lines)
    lines.append(
        "These maps are **stale** — the signatures define class rules they do "
        "not yet resolve. This is advisory (a signatures-only change strands "
        "older maps normally); regenerate them when convenient."
    )
    lines.append("")
    lines.append("| Map | App | version_code | Missing classes |")
    lines.append("|---|---|---|---|")
    for fnd in report.findings:
        missing = "<br>".join(f"`{m}`" for m in fnd.missing)
        lines.append(f"| `{fnd.map_path}` | `{fnd.app}` | `{fnd.version_code}` | {missing} |")
    lines.append("")
    return "\n".join(lines)


def write_dashboard(report: Report) -> None:
    """Print the report to stdout and append the table to $GITHUB_STEP_SUMMARY."""
    summary = render_summary(report)
    print(summary)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        try:
            with open(step_summary, "a", encoding="utf-8") as fh:
                fh.write(summary)
                if not summary.endswith("\n"):
                    fh.write("\n")
        except OSError as exc:
            # The dashboard is best-effort; a write failure must not turn a
            # non-blocking check into a failure. Note it on stderr and move on.
            print(f"::warning::could not write $GITHUB_STEP_SUMMARY: {exc}", file=sys.stderr)


# --- Built-in self-test -----------------------------------------------------
#
# Pins the contract in BOTH directions: a map missing a ruled class is flagged
# stale; a map with every ruled class is not; the `$`-nested rule->key mapping
# resolves; AND a malformed input is the ONLY thing that exits non-zero (a
# staleness finding never does).

_SIGS_FRESH = """
- name: 'IRemoteService$Stub'
  package: 'com.example.app'
  signatures:
      - signature: '"com.example.app.IRemoteService"'
        type: regex
- name: 'Config'
  package: 'com.example.app'
  signatures:
      - signature: '"https://x.example/api"'
        type: regex
"""


def _self_test() -> int:  # noqa: C901 - linear, fixture-by-fixture for clarity
    failures = 0

    def ok(label: str, cond: bool, detail: str = "") -> None:
        nonlocal failures
        if cond:
            print(f"self-test: {label}")
        else:
            failures += 1
            print(f"SELF-TEST FAIL: {label} {detail}", file=sys.stderr)

    sig_fqns = rule_fqns(yaml.safe_load(_SIGS_FRESH), "<fixture>")
    expected_fqns = {"com.example.app.IRemoteService$Stub", "com.example.app.Config"}

    # (c) the `$`-nested rule->key mapping: name carries `$` verbatim into the
    #     FQN, which equals the map key spelling.
    ok(
        "`$`-nested rule maps to the map-key FQN (IRemoteService$Stub)",
        sig_fqns == expected_fqns,
        f"got {sorted(sig_fqns)}",
    )

    sig_app = {"com.example.app": sig_fqns}

    # (b) a map containing EVERY ruled class -> NOT flagged (fresh). Include an
    #     extra class the signatures don't mention — supersets are fine.
    fresh_keys = {
        "maps/com.example.app/30405.json": {
            "com.example.app.IRemoteService$Stub",
            "com.example.app.Config",
            "com.example.app.SomethingExtra",
        }
    }
    rpt_fresh = analyse(fresh_keys, sig_app)
    ok(
        "map with every ruled class is NOT flagged",
        not rpt_fresh.findings,
        f"got findings {rpt_fresh.findings}",
    )

    # (a) a map MISSING a ruled class -> flagged stale, with the exact missing
    #     FQN reported. Drop `Config` from the keys.
    stale_keys = {
        "maps/com.example.app/30404.json": {"com.example.app.IRemoteService$Stub"}
    }
    rpt_stale = analyse(stale_keys, sig_app)
    ok(
        "map missing a ruled class IS flagged stale",
        len(rpt_stale.findings) == 1,
        f"got {rpt_stale.findings}",
    )
    if rpt_stale.findings:
        ok(
            "stale finding names the exact missing FQN",
            rpt_stale.findings[0].missing == ("com.example.app.Config",),
            f"got {rpt_stale.findings[0].missing}",
        )

    # An app with NO signatures sets no expectation -> never flagged, even with
    # an empty map.
    no_sig = analyse({"maps/com.other.app/1.json": set()}, sig_app)
    ok(
        "map for an app with no signatures is not analysed",
        not no_sig.findings,
        f"got {no_sig.findings}",
    )

    # The CENTRAL contract: the end-to-end run over a corpus whose ONLY issue is
    # a stale map EXITS 0 (non-blocking). Build a temp corpus and run `main`.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        sdir = os.path.join(tmp, "signatures", "com.example.app")
        mdir = os.path.join(tmp, "maps", "com.example.app")
        os.makedirs(sdir)
        os.makedirs(mdir)
        with open(os.path.join(sdir, "signatures.yaml"), "w", encoding="utf-8") as fh:
            fh.write(_SIGS_FRESH)
        # A map missing `Config` -> stale, but the run must still exit 0.
        with open(os.path.join(mdir, "30404.json"), "w", encoding="utf-8") as fh:
            json.dump(
                {"classes": {"com.example.app.IRemoteService$Stub": {"obfuscated": "a"}}},
                fh,
            )
        rc = main(["check_map_freshness.py", os.path.join(tmp, "maps"), os.path.join(tmp, "signatures")])
        ok("a STALE-ONLY corpus run exits 0 (non-blocking)", rc == 0, f"got exit {rc}")

        # (malformed) garbled JSON map -> MalformedInput -> exit NON-ZERO. This
        # is the only thing that fails the run.
        with open(os.path.join(mdir, "30405.json"), "w", encoding="utf-8") as fh:
            fh.write("{ this is not json")
        rc_bad = main(["check_map_freshness.py", os.path.join(tmp, "maps"), os.path.join(tmp, "signatures")])
        ok("a MALFORMED input exits non-zero", rc_bad != 0, f"got exit {rc_bad}")

    # Direct malformed-input pins on the pure parsers (both directions of the
    # "what counts as malformed" line).
    bad_sig = False
    try:
        rule_fqns("not a list", "<fixture>")
    except MalformedInput:
        bad_sig = True
    ok("non-list signatures doc is malformed", bad_sig)

    bad_map = False
    try:
        map_class_keys({"classes": "nope"}, "<fixture>")
    except MalformedInput:
        bad_map = True
    ok("map with non-object 'classes' is malformed", bad_map)

    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: all cases passed")
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args == ["--self-test"]:
        return _self_test()
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    maps_root, sigs_root = args
    try:
        map_app_keys, sig_app_fqns = load_corpus(maps_root, sigs_root)
    except MalformedInput as exc:
        # The ONLY non-zero exit: an input the script itself could not read.
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    report = analyse(map_app_keys, sig_app_fqns)
    write_dashboard(report)

    # NON-BLOCKING: a staleness finding NEVER fails the build. Emit a GitHub
    # `::notice` per stale map so it's visible in the log, then exit 0.
    for fnd in report.findings:
        print(
            f"::notice file={fnd.map_path}::stale map — missing "
            f"{len(fnd.missing)} ruled class(es): {', '.join(fnd.missing)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
