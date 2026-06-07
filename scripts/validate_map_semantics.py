#!/usr/bin/env python3
"""Tier-1 structural SEMANTICS checks for published maps (maps#13 M11).

The JSON Schema (`schema/rosetta-map.schema.json`) validates the *shape* of a
map — required keys, value types, string patterns, size caps. It cannot,
however, reason about relationships BETWEEN values: that a method descriptor is
a well-formed JVM descriptor, that an obfuscated type it references resolves to
a class the same map defines, that two overloads don't collide, or that the
`app` field agrees with the directory the file lives in. Those are the
RFC 0001 Decision-4 *tier-1* structural checks this validator adds.

It is APK-free (Hard rule 3): it reads ONLY the committed map JSON. It uses
nothing but the standard library (json) so it runs on the same plain Python the
rest of CI uses, alongside `lint_signatures.py`.

Checks, per `maps/**/*.json`:

  1. descriptor-parse       — every method `signature` is a well-formed JVM
                              method descriptor `(<params>)<ret>`; each type is
                              a valid JVM type (V, primitives ZBSCIJFD,
                              L<binary/name>;, arrays `[`).
  2. referenced-types       — every object type `L...;` in a descriptor that
                              looks APP-INTERNAL (i.e. NOT a framework type and
                              shaped like this map's own obfuscation namespace)
                              must resolve to some class entry in the SAME map
                              (by `obfuscated` name or by real key).
  3. overload-distinctness  — within one class, no two method entries collide
                              on the same (obfuscated-name, descriptor) pair.
  4. app-dir match          — the map's `app` equals its parent directory name
                              under `maps/` (maps/<app>/<version_code>.json).

Usage:
    validate_map_semantics.py FILE [FILE ...]   # check each map
    validate_map_semantics.py --self-test       # run built-in accept/reject

Exit status is 0 only when every checked map passes every check.
"""

from __future__ import annotations

import json
import os
import sys

# --- JVM descriptor grammar -------------------------------------------------
#
# Primitive field types (JVMS 4.3.2). 'V' (void) is valid ONLY as a return
# type, handled separately below.
_PRIMITIVES = set("ZBSCIJFD")


def _parse_field_type(desc: str, i: int) -> int:
    """Parse one JVM field type starting at desc[i]; return the index past it.

    Raises ValueError on a malformed type. A field type is a primitive
    (ZBSCIJFD), an object type `L<name>;`, or an array `[<field type>`
    (255-dim cap per the JVMS, enforced loosely as "at least one element type").
    """
    n = len(desc)
    # Consume array dimensions.
    dims = 0
    while i < n and desc[i] == "[":
        dims += 1
        i += 1
    if dims > 255:
        raise ValueError("array nesting exceeds 255 dimensions")
    if i >= n:
        raise ValueError("type ends after array prefix '['")
    c = desc[i]
    if c in _PRIMITIVES:
        return i + 1
    if c == "L":
        end = desc.find(";", i + 1)
        if end == -1:
            raise ValueError("object type 'L' has no terminating ';'")
        name = desc[i + 1 : end]
        if name == "":
            raise ValueError("object type 'L;' has an empty class name")
        # A binary class name is one-or-more identifier segments joined by '/'.
        # Be permissive about the identifier charset (obfuscators emit unusual
        # but legal names) but forbid the structural mistakes a typo'd
        # descriptor makes: empty segments, stray ';' or '[' or '(' inside.
        for bad in (";", "[", "(", ")"):
            if bad in name:
                raise ValueError(f"object type name contains illegal {bad!r}: {name!r}")
        if name.startswith("/") or name.endswith("/") or "//" in name:
            raise ValueError(f"object type name has an empty path segment: {name!r}")
        return end + 1
    raise ValueError(f"unexpected type char {c!r}")


def parse_method_descriptor(desc: str) -> tuple[list[str], str]:
    """Parse a JVM method descriptor `(<params>)<ret>`.

    Returns (param_types, return_type) as raw JVM type strings (e.g.
    ['Landroid/os/Bundle;', 'I'], 'V'). Raises ValueError if malformed.
    """
    if not desc.startswith("("):
        raise ValueError("descriptor must start with '('")
    n = len(desc)
    i = 1
    params: list[str] = []
    while i < n and desc[i] != ")":
        start = i
        i = _parse_field_type(desc, i)
        params.append(desc[start:i])
    if i >= n or desc[i] != ")":
        raise ValueError("missing ')' closing the parameter list")
    i += 1  # past ')'
    # Return type: 'V' or a field type, and it must consume the rest exactly.
    if i >= n:
        raise ValueError("descriptor has no return type")
    if desc[i] == "V":
        ret = "V"
        i += 1
    else:
        start = i
        i = _parse_field_type(desc, i)
        ret = desc[start:i]
    if i != n:
        raise ValueError(f"trailing characters after return type: {desc[i:]!r}")
    return params, ret


# --- app-internal-type heuristic --------------------------------------------
#
# referenced-types (check 2) only fires for object types that are CLEARLY
# app-internal, to avoid false positives on framework/library types a map will
# legitimately reference without defining. The heuristic is deliberately
# conservative and TUNABLE here:
#
#   * A type whose binary name starts with any FRAMEWORK_PREFIXES segment is
#     never flagged (java/javax/android/androidx/kotlin/kotlinx and the common
#     bundled libraries Google/AndroidX ship).
#   * Of the remaining types, we ONLY require resolution for those that look
#     like THIS map's own obfuscation namespace — a single-segment name (no
#     '/') drawn from the same alphabet the map's own `obfuscated` class names
#     use. Concretely: the type name has no '/', and it matches the shape of at
#     least one obfuscated class key in the map (same length-class of short
#     lowercase token). We approximate "looks obfuscated" as: a single segment,
#     length <= the longest obfuscated class name in the map, made of the
#     characters that appear in the map's obfuscated class names.
#
# This means a reference to a real, un-renamed app class (e.g.
# `Lcom/example/app/Foo;`, multi-segment) is NOT required to resolve — only the
# short rotated tokens are — which is exactly the set a map is responsible for.
# Widen FRAMEWORK_PREFIXES or relax the namespace test if a real map trips a
# false positive; do NOT weaken a map to satisfy this check.
FRAMEWORK_PREFIXES = (
    "java/",
    "javax/",
    "android/",
    "androidx/",
    "kotlin/",
    "kotlinx/",
    "com/google/",
    "dagger/",
    "org/jetbrains/",
    "io/reactivex/",
    "okhttp3/",
    "okio/",
    "retrofit2/",
    "sun/",
    "jdk/",
)


def _is_framework_type(binary_name: str) -> bool:
    return any(binary_name.startswith(p) for p in FRAMEWORK_PREFIXES)


def _object_binary_name(jvm_type: str) -> str | None:
    """For an L...; type (possibly array-wrapped) return its binary name, else None."""
    t = jvm_type.lstrip("[")
    if t.startswith("L") and t.endswith(";"):
        return t[1:-1]
    return None


def _obfuscation_namespace(class_entries: dict) -> tuple[set[str], int]:
    """Return (alphabet, max_len) describing the map's obfuscated-name namespace.

    The alphabet is the set of characters used in single-segment obfuscated
    class names; max_len is the longest such name. Used to decide whether a
    referenced single-segment type "looks like" one of this map's own renamed
    classes (and therefore must resolve).
    """
    alphabet: set[str] = set()
    max_len = 0
    for entry in class_entries.values():
        if not isinstance(entry, dict):
            continue
        obf = entry.get("obfuscated")
        if isinstance(obf, str) and "/" not in obf and "." not in obf:
            alphabet |= set(obf)
            max_len = max(max_len, len(obf))
    return alphabet, max_len


def _looks_app_internal(binary_name: str, alphabet: set[str], max_len: int) -> bool:
    if not binary_name or "/" in binary_name:
        return False  # multi-segment / real package name: not a rotated token
    if not alphabet or max_len == 0:
        return False  # map defines no obfuscated namespace to compare against
    if len(binary_name) > max_len:
        return False
    return all(ch in alphabet for ch in binary_name)


# --- per-map checks ---------------------------------------------------------


def _iter_method_entries(methods: dict):
    """Yield (method_key, entry_dict) over a class's methods (entry or list)."""
    for mkey, value in methods.items():
        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    yield mkey, entry
        elif isinstance(value, dict):
            yield mkey, value


def check_map(doc: object, path: str) -> list[str]:
    """Return a list of human-readable errors (empty == valid) for one map."""
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["map is not a JSON object"]

    classes = doc.get("classes")
    if not isinstance(classes, dict):
        # Schema already enforces this; nothing semantic to do.
        return errors

    # --- check 4: app-dir match ---
    app = doc.get("app")
    parent = os.path.basename(os.path.dirname(os.path.realpath(path)))
    if isinstance(app, str) and parent and app != parent:
        errors.append(
            f"app field '{app}' != parent directory '{parent}' "
            f"(expected maps/<app>/<version_code>.json with app == <app>)"
        )

    # Resolvable obfuscated-type set: every class's `obfuscated` short name and
    # its real key (so a descriptor may reference either spelling).
    resolvable: set[str] = set()
    for ckey, entry in classes.items():
        resolvable.add(ckey)
        if isinstance(entry, dict):
            obf = entry.get("obfuscated")
            if isinstance(obf, str):
                resolvable.add(obf)

    alphabet, max_len = _obfuscation_namespace(classes)

    for ckey, entry in classes.items():
        if not isinstance(entry, dict):
            continue
        methods = entry.get("methods")
        if not isinstance(methods, dict):
            continue

        # --- check 3: overload distinctness (per class) ---
        seen: set[tuple[str, str]] = set()
        for mkey, mentry in _iter_method_entries(methods):
            obf = mentry.get("obfuscated")
            sig = mentry.get("signature")
            if not isinstance(obf, str) or not isinstance(sig, str):
                continue
            key = (obf, sig)
            if key in seen:
                errors.append(
                    f"class '{ckey}': duplicate method overload — obfuscated "
                    f"'{obf}' with descriptor '{sig}' appears more than once"
                )
            seen.add(key)

            # --- check 1: descriptor parses ---
            try:
                params, ret = parse_method_descriptor(sig)
            except ValueError as exc:
                errors.append(
                    f"class '{ckey}' method '{mkey}': malformed descriptor "
                    f"'{sig}': {exc}"
                )
                continue

            # --- check 2: referenced app-internal types resolve ---
            for jvm_type in params + [ret]:
                binary = _object_binary_name(jvm_type)
                if binary is None:
                    continue
                if _is_framework_type(binary):
                    continue
                if not _looks_app_internal(binary, alphabet, max_len):
                    continue
                if binary not in resolvable:
                    errors.append(
                        f"class '{ckey}' method '{mkey}': descriptor '{sig}' "
                        f"references app-internal type 'L{binary};' that no "
                        f"class entry in this map resolves"
                    )

    return errors


def check_file(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except OSError as exc:
        return [f"could not read file: {exc}"]
    except ValueError as exc:
        return [f"could not parse JSON: {exc}"]
    return check_map(doc, path)


# --- Built-in self-test -----------------------------------------------------
#
# Each invalid fixture pins exactly one of the four checks; each is paired with
# the valid baseline so a check can't silently stop firing OR start
# false-positiving.

_VALID_MAP = {
    "schema_version": 2,
    "app": "com.example.app",
    "version": "1.0",
    "version_code": 1,
    "classes": {
        "com.example.app.Foo": {
            "obfuscated": "aaaa",
            "methods": {
                "doIt": {"obfuscated": "a", "signature": "(Landroid/os/Bundle;Lbbbb;)V"},
                "make": {"obfuscated": "b", "signature": "()Lbbbb;"},
                "over": [
                    {"obfuscated": "c", "signature": "(I)V"},
                    {"obfuscated": "c", "signature": "(J)V"},
                ],
            },
        },
        "com.example.app.Bar": {
            "obfuscated": "bbbb",
            "methods": {
                "x": {"obfuscated": "a", "signature": "(Lcom/example/app/RealThing;)V"},
            },
        },
    },
}

# A map that references an app-internal type by its REAL key (not obfuscated),
# which must also resolve.
_VALID_REALKEY_REF = {
    "schema_version": 2,
    "app": "com.example.app",
    "version": "1.0",
    "version_code": 1,
    "classes": {
        "ab": {"obfuscated": "ab", "methods": {}},
        "cd": {
            "obfuscated": "cd",
            "methods": {"m": {"obfuscated": "a", "signature": "()Lab;"}},
        },
    },
}


def _invalid_fixtures() -> dict:
    import copy

    fixtures: dict = {}

    # check 1: malformed descriptor — missing ')'.
    f1 = copy.deepcopy(_VALID_MAP)
    f1["classes"]["com.example.app.Foo"]["methods"]["doIt"]["signature"] = "(Landroid/os/Bundle;V"
    fixtures["malformed descriptor (no close paren)"] = f1

    # check 1: malformed descriptor — unterminated object type.
    f1b = copy.deepcopy(_VALID_MAP)
    f1b["classes"]["com.example.app.Foo"]["methods"]["make"]["signature"] = "()Lbbbb"
    fixtures["malformed descriptor (unterminated L)"] = f1b

    # check 1: bad type char.
    f1c = copy.deepcopy(_VALID_MAP)
    f1c["classes"]["com.example.app.Foo"]["methods"]["make"]["signature"] = "()Q"
    fixtures["malformed descriptor (bad type char)"] = f1c

    # check 2: unresolved app-internal type. It must be drawn from THIS map's
    # obfuscation alphabet ({a,b} here) and within its length so the heuristic
    # recognises it as app-internal — 'abab' looks obfuscated but no class
    # defines it.
    f2 = copy.deepcopy(_VALID_MAP)
    f2["classes"]["com.example.app.Foo"]["methods"]["make"]["signature"] = "()Labab;"
    fixtures["unresolved app-internal type"] = f2

    # check 3: overload collision — same obfuscated+descriptor twice.
    f3 = copy.deepcopy(_VALID_MAP)
    f3["classes"]["com.example.app.Foo"]["methods"]["over"] = [
        {"obfuscated": "c", "signature": "(I)V"},
        {"obfuscated": "c", "signature": "(I)V"},
    ]
    fixtures["overload collision"] = f3

    # check 4: app != parent dir. The self-test passes a synthetic path whose
    # parent dir is com.example.app, so a mismatching app trips it.
    f4 = copy.deepcopy(_VALID_MAP)
    f4["app"] = "com.other.pkg"
    fixtures["app != parent dir"] = f4

    return fixtures


def _self_test() -> int:
    failures = 0
    # Valid baselines: path's parent dir must equal the app field.
    for label, doc in (("valid baseline", _VALID_MAP), ("valid real-key ref", _VALID_REALKEY_REF)):
        synth_path = os.path.join("maps", doc["app"], f"{doc['version_code']}.json")
        errs = check_map(doc, synth_path)
        if errs:
            failures += 1
            print(f"SELF-TEST FAIL: {label} was rejected: {errs}", file=sys.stderr)
        else:
            print(f"self-test: {label} accepted")

    for label, doc in _invalid_fixtures().items():
        synth_path = os.path.join("maps", "com.example.app", f"{doc['version_code']}.json")
        if not check_map(doc, synth_path):
            failures += 1
            print(f"SELF-TEST FAIL: invalid fixture accepted: {label}", file=sys.stderr)
        else:
            print(f"self-test: invalid fixture rejected ({label})")

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
        errors = check_file(path)
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
