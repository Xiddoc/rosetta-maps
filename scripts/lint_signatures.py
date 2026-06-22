#!/usr/bin/env python3
"""Lint sigmatcher-dialect signature files (the offline source-of-truth dialect).

This is the signatures/ counterpart to the schema validation that guards
maps/. AGENTS.md declares `signatures/<app>/signatures.yaml` the SOURCE OF
TRUTH from which a map is reproduced, yet CI historically only validated
`maps/**/*.json`. This linter closes that gap (maps#12).

It is deliberately a *minimal structural* lint, not a full sigmatcher
re-implementation: it parses each file as YAML and checks the required
top-level keys and the known rule/member/signature shapes of the
sigmatcher dialect (see `templates/signatures.template.yaml`). It does NOT
fetch, read, or reason about any APK — it only reads the committed YAML, so
it preserves the no-APK invariant (Hard rule 3).

It ALSO enforces a presentation rule: signatures must be written in YAML
*block* style (one key / one list item per line), never the collapsed
*flow* style (`- {name: ..., signatures: [{...}]}`). Flow style is valid
YAML and parses to the same data, but it crushes a rule onto one line, which
defeats line-by-line review and produces unreadable diffs when a single
signature changes. The structural checks operate on the parsed data (which
is style-agnostic), so this rule is checked separately against the YAML node
tree via `yaml.compose`.

Usage:
    lint_signatures.py FILE [FILE ...]   # lint each file; non-zero on any error
    lint_signatures.py --self-test       # run built-in accept/reject fixtures

Exit status is 0 only when every linted file is well-formed.
"""

from __future__ import annotations

import sys

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    print("error: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


# A signature's `type` must be one of the known sigmatcher matcher kinds.
KNOWN_SIGNATURE_TYPES = {"regex", "string", "smali"}


def _is_str(value: object) -> bool:
    return isinstance(value, str)


def _lint_signature(sig: object, where: str, errors: list[str]) -> None:
    if not isinstance(sig, dict):
        errors.append(f"{where}: each signature must be a mapping, got {type(sig).__name__}")
        return
    if "signature" not in sig:
        errors.append(f"{where}: signature entry is missing required key 'signature'")
    elif not _is_str(sig["signature"]) or sig["signature"].strip() == "":
        errors.append(f"{where}: 'signature' must be a non-empty string")
    sig_type = sig.get("type")
    if sig_type is None:
        errors.append(f"{where}: signature entry is missing required key 'type'")
    elif sig_type not in KNOWN_SIGNATURE_TYPES:
        errors.append(
            f"{where}: unknown signature type {sig_type!r} "
            f"(expected one of {sorted(KNOWN_SIGNATURE_TYPES)})"
        )
    # `count` is optional; when present it must be a positive int (>= 1; a
    # zero/negative count is meaningless) or a digit "N" / "N-M" range string.
    # `bool` is an int subclass, so reject it explicitly.
    if "count" in sig:
        count = sig["count"]
        ok = isinstance(count, int) and not isinstance(count, bool) and count >= 1
        if not ok and _is_str(count):
            parts = count.split("-")
            ok = all(p.strip().isdigit() for p in parts) and 1 <= len(parts) <= 2
        if not ok:
            errors.append(f"{where}: 'count' must be a positive int (>= 1) or an 'N'/'N-M' range string, got {count!r}")


def _lint_signature_list(sigs: object, where: str, errors: list[str]) -> None:
    if not isinstance(sigs, list) or not sigs:
        errors.append(f"{where}: 'signatures' must be a non-empty list")
        return
    for i, sig in enumerate(sigs):
        _lint_signature(sig, f"{where}.signatures[{i}]", errors)


def _lint_members(members: object, kind: str, where: str, errors: list[str]) -> None:
    if not isinstance(members, list):
        errors.append(f"{where}: '{kind}' must be a list")
        return
    for i, member in enumerate(members):
        mwhere = f"{where}.{kind}[{i}]"
        if not isinstance(member, dict):
            errors.append(f"{mwhere}: each {kind} entry must be a mapping")
            continue
        if not _is_str(member.get("name")) or member.get("name", "").strip() == "":
            errors.append(f"{mwhere}: missing required non-empty string 'name'")
        if "signatures" not in member:
            errors.append(f"{mwhere}: missing required 'signatures'")
        else:
            _lint_signature_list(member["signatures"], mwhere, errors)


def lint_document(doc: object) -> list[str]:
    """Return a list of human-readable errors (empty == valid)."""
    errors: list[str] = []
    if not isinstance(doc, list) or not doc:
        return ["top level must be a non-empty list of rule entries"]
    for i, rule in enumerate(doc):
        where = f"rule[{i}]"
        if not isinstance(rule, dict):
            errors.append(f"{where}: each rule must be a mapping")
            continue
        if not _is_str(rule.get("name")) or rule.get("name", "").strip() == "":
            errors.append(f"{where}: missing required non-empty string 'name'")
        if not _is_str(rule.get("package")) or rule.get("package", "").strip() == "":
            errors.append(f"{where}: missing required non-empty string 'package'")
        if "signatures" not in rule:
            errors.append(f"{where}: missing required 'signatures'")
        else:
            _lint_signature_list(rule["signatures"], where, errors)
        if "methods" in rule:
            _lint_members(rule["methods"], "methods", where, errors)
        if "fields" in rule:
            _lint_members(rule["fields"], "fields", where, errors)
    return errors


def block_style_errors(text: str) -> list[str]:
    """Return errors for any flow-style (`{...}`/`[...]`) collection node.

    Walks the YAML node tree (`yaml.compose`) rather than the loaded data,
    because `safe_load` discards the flow-vs-block distinction. Every mapping
    and sequence must be block-styled; a flow-styled one (even nested inside an
    otherwise block document) is reported with its 1-based line number. Quoted
    scalars that merely CONTAIN brackets (e.g. a regex `'[a-z]'`) are scalar
    nodes, not flow collections, so they are never flagged.
    """
    errors: list[str] = []
    try:
        root = yaml.compose(text)
    except yaml.YAMLError as exc:
        return [f"could not parse YAML: {exc}"]
    if root is None:
        return errors
    stack = [root]
    while stack:
        node = stack.pop()
        if isinstance(node, yaml.MappingNode):
            if node.flow_style:
                errors.append(
                    f"line {node.start_mark.line + 1}: flow-style mapping "
                    "(`{...}`) is not allowed — use block style (one key per "
                    "line) so rules stay reviewable"
                )
            for key_node, value_node in node.value:
                stack.append(key_node)
                stack.append(value_node)
        elif isinstance(node, yaml.SequenceNode):
            if node.flow_style:
                errors.append(
                    f"line {node.start_mark.line + 1}: flow-style sequence "
                    "(`[...]`) is not allowed — use block style (one item per "
                    "line) so rules stay reviewable"
                )
            stack.extend(node.value)
    return errors


def lint_file(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return [f"could not read file: {exc}"]
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"could not parse YAML: {exc}"]
    return lint_document(doc) + block_style_errors(text)


# --- Built-in self-test (a malformed fixture must be REJECTED) --------------

_VALID_FIXTURE = """
- name: 'Foo'
  package: 'com.example.app'
  signatures:
      - signature: '"com.example.app.Foo"'
        type: regex
        count: 1
  methods:
      - name: 'bar'
        signatures:
            - signature: 'bar\\(\\)V'
              type: regex
              count: 1-2
"""

_INVALID_FIXTURES = {
    "empty document": "",
    "not a list": "name: Foo\npackage: com.example.app\n",
    "rule missing name": "- package: 'com.example.app'\n  signatures:\n      - signature: 'x'\n        type: regex\n",
    "rule missing package": "- name: 'Foo'\n  signatures:\n      - signature: 'x'\n        type: regex\n",
    "rule missing signatures": "- name: 'Foo'\n  package: 'com.example.app'\n",
    "unknown signature type": (
        "- name: 'Foo'\n  package: 'com.example.app'\n  signatures:\n"
        "      - signature: 'x'\n        type: bogus\n"
    ),
    "signature missing 'signature'": (
        "- name: 'Foo'\n  package: 'com.example.app'\n  signatures:\n"
        "      - type: regex\n"
    ),
    "method missing name": (
        "- name: 'Foo'\n  package: 'com.example.app'\n  signatures:\n"
        "      - signature: 'x'\n        type: regex\n  methods:\n"
        "      - signatures:\n            - signature: 'y'\n              type: regex\n"
    ),
    "field missing name": (
        "- name: 'Foo'\n  package: 'com.example.app'\n  signatures:\n"
        "      - signature: 'x'\n        type: regex\n  fields:\n"
        "      - signatures:\n            - signature: 'y'\n              type: regex\n"
    ),
    "bad count": (
        "- name: 'Foo'\n  package: 'com.example.app'\n  signatures:\n"
        "      - signature: 'x'\n        type: regex\n        count: 'lots'\n"
    ),
    "bad count (zero)": (
        "- name: 'Foo'\n  package: 'com.example.app'\n  signatures:\n"
        "      - signature: 'x'\n        type: regex\n        count: 0\n"
    ),
}

# Flow-style fixtures: each parses to STRUCTURALLY VALID data (so
# `lint_document` alone accepts them), and must be rejected ONLY by the
# block-style check — pinning that rule in both directions against the
# block-styled `_VALID_FIXTURE` above.
_FLOW_FIXTURES = {
    "whole rule collapsed to flow": (
        "- {name: 'Foo', package: 'com.example.app', "
        "signatures: [{signature: '\"x\"', type: regex}]}\n"
    ),
    "nested flow signatures list": (
        "- name: 'Foo'\n  package: 'com.example.app'\n"
        "  signatures: [{signature: '\"x\"', type: regex}]\n"
    ),
}


def _self_test() -> int:
    failures = 0
    valid_doc = yaml.safe_load(_VALID_FIXTURE)
    errs = lint_document(valid_doc) + block_style_errors(_VALID_FIXTURE)
    if errs:
        failures += 1
        print(f"SELF-TEST FAIL: valid fixture was rejected: {errs}", file=sys.stderr)
    else:
        print("self-test: valid fixture accepted")
    for label, text in _INVALID_FIXTURES.items():
        doc = yaml.safe_load(text)
        if not lint_document(doc):
            failures += 1
            print(f"SELF-TEST FAIL: invalid fixture accepted: {label}", file=sys.stderr)
        else:
            print(f"self-test: invalid fixture rejected ({label})")
    # Flow-style fixtures: structurally valid, rejected ONLY by the style check.
    for label, text in _FLOW_FIXTURES.items():
        structural = lint_document(yaml.safe_load(text))
        style = block_style_errors(text)
        if structural:
            failures += 1
            print(
                f"SELF-TEST FAIL: flow fixture {label!r} should be structurally "
                f"valid but got {structural}",
                file=sys.stderr,
            )
        elif not style:
            failures += 1
            print(
                f"SELF-TEST FAIL: flow-style fixture accepted (style check missed it): {label}",
                file=sys.stderr,
            )
        else:
            print(f"self-test: flow-style fixture rejected ({label})")
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: all cases passed")
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    if args == ["--self-test"]:
        return _self_test()

    overall = 0
    for path in args:
        errors = lint_file(path)
        if errors:
            overall = 1
            for err in errors:
                print(f"::error file={path}::{err}")
            print(f"FAIL {path}: {len(errors)} error(s)", file=sys.stderr)
        else:
            print(f"ok {path}")
    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv))
