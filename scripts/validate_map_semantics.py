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
  2. referenced-types       — every object type `L...;` referenced by a method
                              descriptor OR a `field.type` that looks
                              APP-INTERNAL (i.e. NOT a framework type and shaped
                              like this map's own obfuscation namespace) must
                              resolve to some class entry in the SAME map (by
                              `obfuscated` name or by real key).
  3. overload-distinctness  — within one class, no two method entries collide
                              on the same (obfuscated-name, descriptor) pair.
  4. app-dir match          — the map's `app` equals its parent directory name
                              under `maps/` (maps/<app>/<version_code>.json).
  5. source-config paths    — every `sources[].config` written as a repo-internal
                              path under `signatures/` must point at a committed
                              file (catches a drifted provenance pointer such as
                              a `signatures/example.json` that never existed).
  6. status/superseded_by   — (v3) `superseded_by` is allowed ONLY when
                              `status == "superseded"`, and `status ==
                              "superseded"` REQUIRES `superseded_by`. The schema
                              validates each field's shape but cannot express
                              this relationship.

CONSERVATIVE BOUND on check 2 (read before assuming it is exhaustive): a
referenced object type is flagged as a dangling app-internal reference ONLY
when it "looks like" one of THIS map's own rotated tokens — a single-segment
name (no `/`) whose characters all fall inside the map's obfuscated-name
alphabet and whose length is within the map's longest obfuscated name. A
referenced type whose characters fall OUTSIDE that alphabet, or whose name is
multi-segment (a real package path), is NOT flagged even if absent — and if a
map defines no single-segment obfuscated names at all, the alphabet cannot be
derived and check 2 is SKIPPED entirely for that map (a `::warning` is emitted
so the skip is visible, not silent). This is deliberate: it avoids false
positives on framework/library types and on short third-party-obfuscated names
the map legitimately references without defining, at the cost of not catching
every conceivable dangling reference.

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
        # descriptor makes: empty segments, stray ';' / '[' / '(' / ')' inside,
        # and the two characters that signal a *source* name leaked into a
        # *binary* descriptor — a '.' (binary names join segments with '/', not
        # '.', so `Lfoo.bar.Baz;` is malformed) or whitespace (no JVM binary
        # name segment contains a space).
        for bad in (";", "[", "(", ")", ".", " ", "\t", "\n", "\r"):
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

    NOTE — multi-segment obfuscated names are SKIPPED on purpose: only
    single-segment `obfuscated` values (no '/' and no '.') contribute to the
    alphabet. An obfuscator that emits package-qualified obfuscated names (e.g.
    `a/b/c`) therefore yields no alphabet, which DISABLES check 2 for that map
    (the namespace can't be derived). That is a deliberate conservative choice —
    we'd rather skip the check than guess at a multi-segment alphabet and
    false-positive — but it is a SILENT no-op unless the caller surfaces it.
    `check_map` emits a `::warning` when the returned alphabet is empty so a
    contributor sees that check 2 was SKIPPED, not passed.
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


# --- source-config path resolution (check 5) --------------------------------
#
# A `sources[].config` value is free-form, but when it is written as a
# REPO-RELATIVE path under `signatures/` it names a file that MUST exist in this
# repo (the worked example's `signatures/com.example.app/signatures.yaml` is the
# canonical case). A drifted config — e.g. the old `signatures/example.json`
# that never existed — is exactly the dangling provenance pointer this check
# catches. We only fire for the unambiguous repo-internal shape (`signatures/…`)
# so a config that legitimately names an out-of-repo tool config (an absolute
# path, a bare filename, a URL) is never flagged.
_SIGNATURES_PREFIX = "signatures/"


def _config_is_repo_internal(config: str) -> bool:
    """True when `config` is a repo-relative path under signatures/ we can resolve."""
    return (
        isinstance(config, str)
        and config.startswith(_SIGNATURES_PREFIX)
        and "\\" not in config
        and ".." not in config.split("/")
    )


def _check_source_configs(doc: dict, map_path: str, errors: list[str]) -> None:
    """check 5: every repo-internal `sources[].config` must point at a real file.

    The repo root is derived from the map path: maps/<app>/<vc>.json lives two
    directories below the repo root, so the signatures/ tree is a sibling of the
    map's grandparent. Resolving relative to the map (not the process CWD) keeps
    the check correct no matter where CI invokes it from.
    """
    sources = doc.get("sources")
    if not isinstance(sources, list):
        return
    # maps/<app>/<vc>.json -> repo root is dirname(dirname(dirname(realpath))).
    map_real = os.path.realpath(map_path)
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(map_real)))
    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            continue
        config = src.get("config")
        if not isinstance(config, str) or not _config_is_repo_internal(config):
            continue
        target = os.path.join(repo_root, config)
        if not os.path.isfile(target):
            errors.append(
                f"sources[{i}].config '{config}' points at a repo-internal "
                f"signatures path that does not exist — fix the path so it names "
                f"a committed file (e.g. signatures/<app>/signatures.yaml), or "
                f"drop the config if the source is not a repo-internal file"
            )


# --- status / superseded_by relationship (check 6) --------------------------
#
# The schema (rosetta-map.schema.json) can validate `status` against its enum
# and `superseded_by` against `integer`, but it cannot express the RELATIONSHIP
# between them — that is a tier-1 semantic check (the same class as the
# descriptor/overload/app-dir checks above). The rule (v3, issue #40):
#
#   * `superseded_by` is allowed ONLY when `status == "superseded"`. A pointer to
#     a successor map is meaningless on an `active`/`retracted`/absent-status map.
#   * when `status == "superseded"`, `superseded_by` MUST be present — a
#     superseded map has to say what supersedes it.
#
# `status` absent is treated as `active` (so `superseded_by` is then forbidden).


def _check_status(doc: dict, errors: list[str]) -> None:
    """check 6: enforce the status <-> superseded_by relationship."""
    status = doc.get("status")
    has_superseded_by = "superseded_by" in doc
    is_superseded = status == "superseded"

    if has_superseded_by and not is_superseded:
        shown = "active (absent)" if status is None else repr(status)
        errors.append(
            f"'superseded_by' is present but status is {shown}; "
            f"'superseded_by' is allowed ONLY when status == 'superseded' — "
            f"set status to 'superseded' or drop 'superseded_by'"
        )
    if is_superseded and not has_superseded_by:
        errors.append(
            "status is 'superseded' but 'superseded_by' is missing; a "
            "superseded map MUST point at its successor's version_code via "
            "'superseded_by'"
        )


def _unresolved_type_error(context: str, binary: str) -> str:
    """Build the actionable error for a dangling app-internal type reference."""
    return (
        f"{context} references app-internal type 'L{binary};' that no class "
        f"entry in this map resolves — add a class entry for 'L{binary};' "
        f"(a stub entry with that `obfuscated` name, or its real key, is "
        f"enough) so the reference resolves. NOTE: a short, single-segment "
        f"third-party-obfuscated name can also trip this if it happens to fall "
        f"inside this map's obfuscation alphabet; if 'L{binary};' is genuinely "
        f"external, the map must still carry a (stub) entry for it to satisfy "
        f"this check."
    )


def check_map(doc: object, path: str) -> list[str]:
    """Return a list of human-readable errors (empty == valid) for one map."""
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["map is not a JSON object"]

    # --- check 6: status <-> superseded_by relationship ---
    # Runs regardless of `classes` (it is a top-level lifecycle invariant, not a
    # per-class one), so check it before the classes early-return below.
    _check_status(doc, errors)

    classes = doc.get("classes")
    if not isinstance(classes, dict):
        # Schema already enforces this; nothing semantic to do.
        return errors

    # --- check 4: app-dir match ---
    # The schema requires `app` to be a present string, but this tier-1 check
    # must not silently skip when it is missing or the wrong type: a map with no
    # usable `app` field can never satisfy the maps/<app>/<version_code>.json
    # contract, so flag it explicitly rather than passing it through.
    app = doc.get("app")
    parent = os.path.basename(os.path.dirname(os.path.realpath(path)))
    if "app" not in doc or not isinstance(app, str):
        errors.append(
            f"map has no usable string 'app' field (got {app!r}); expected "
            f"maps/<app>/<version_code>.json with app == '{parent}'"
        )
    elif parent and app != parent:
        errors.append(
            f"app field '{app}' != parent directory '{parent}' "
            f"(expected maps/<app>/<version_code>.json with app == <app>)"
        )

    # --- check 5: source-config paths resolve ---
    _check_source_configs(doc, path, errors)

    # Resolvable obfuscated-type set: every class's `obfuscated` short name and
    # its real key (so a descriptor or field type may reference either spelling).
    resolvable: set[str] = set()
    for ckey, entry in classes.items():
        resolvable.add(ckey)
        if isinstance(entry, dict):
            obf = entry.get("obfuscated")
            if isinstance(obf, str):
                resolvable.add(obf)

    alphabet, max_len = _obfuscation_namespace(classes)
    if not alphabet:
        # check 2 can't run: no single-segment obfuscated names to derive the
        # map's alphabet from. Surface the SKIP so it isn't a silent no-op
        # (see _obfuscation_namespace). A `::warning` is non-fatal in CI.
        print(
            f"::warning file={path}::referenced-types check (tier-1 check 2) "
            f"SKIPPED — could not derive this map's obfuscation namespace "
            f"(no single-segment 'obfuscated' class names); dangling "
            f"app-internal type references are NOT validated for this map",
            file=sys.stderr,
        )

    def _check_ref(context: str, jvm_type: str) -> None:
        """check 2: a referenced app-internal object type must resolve."""
        binary = _object_binary_name(jvm_type)
        if binary is None:
            return
        if _is_framework_type(binary):
            return
        if not _looks_app_internal(binary, alphabet, max_len):
            return
        if binary not in resolvable:
            errors.append(_unresolved_type_error(context, binary))

    for ckey, entry in classes.items():
        if not isinstance(entry, dict):
            continue

        # --- check 2 (field types): every field.type that looks app-internal
        # must resolve, just like a referenced type in a method descriptor. ---
        fields = entry.get("fields")
        if isinstance(fields, dict):
            for fkey, fentry in fields.items():
                if not isinstance(fentry, dict):
                    continue
                ftype = fentry.get("type")
                if isinstance(ftype, str):
                    _check_ref(f"class '{ckey}' field '{fkey}': type '{ftype}'", ftype)

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

            # --- check 1: descriptor parses ---
            # Parse BEFORE recording the collision key so a malformed descriptor
            # is reported once (here) and the duplicate-detection `continue`
            # below never double-reports the same parse error for a colliding
            # entry.
            try:
                params, ret = parse_method_descriptor(sig)
            except ValueError as exc:
                errors.append(
                    f"class '{ckey}' method '{mkey}': malformed descriptor "
                    f"'{sig}': {exc}"
                )
                continue

            key = (obf, sig)
            if key in seen:
                errors.append(
                    f"class '{ckey}': duplicate method overload — obfuscated "
                    f"'{obf}' with descriptor '{sig}' appears more than once"
                )
                # Already counted this (obf, sig); its types were validated on
                # the first occurrence, so skip re-checking refs for the dup.
                continue
            seen.add(key)

            # --- check 2: referenced app-internal types resolve ---
            for jvm_type in params + [ret]:
                _check_ref(f"class '{ckey}' method '{mkey}': descriptor '{sig}'", jvm_type)

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
                # Array forms — pin that these parse and that app-internal
                # element types inside arrays still resolve. `abab` IS defined
                # below, so `()[Labab;` and `([B)Labab;` must both pass.
                "asBytes": {"obfuscated": "d", "signature": "()[B"},
                "asArray": {"obfuscated": "e", "signature": "()[Labab;"},
                "fromBytes": {"obfuscated": "f", "signature": "([B)Labab;"},
            },
            # A field whose type is an app-internal obfuscated class that the
            # map DOES define (bbbb) — pins that resolvable field types pass.
            "fields": {
                "bar": {"obfuscated": "z", "type": "Lbbbb;"},
            },
        },
        "com.example.app.Bar": {
            "obfuscated": "bbbb",
            "methods": {
                "x": {"obfuscated": "a", "signature": "(Lcom/example/app/RealThing;)V"},
            },
        },
        # Defined so the array-element reference `Labab;` above resolves.
        "com.example.app.Abab": {"obfuscated": "abab", "methods": {}},
    },
}

# A map that references an app-internal type by its REAL key (not obfuscated),
# which must ALSO resolve. To honestly exercise the real-key path, the referenced
# token (`cccc`) is the REAL KEY of a class whose `obfuscated` short name is
# something DIFFERENT and distinct (`q`). The reference is single-segment and
# drawn from the map's alphabet, so the app-internal heuristic fires; it does NOT
# appear anywhere in the obfuscated-name set, so it can resolve ONLY via the
# real-key half of `resolvable`. Deleting `resolvable.add(ckey)` in check_map
# (the real-key resolution line) would make this fixture wrongly fail.
_VALID_REALKEY_REF = {
    "schema_version": 2,
    "app": "com.example.app",
    "version": "1.0",
    "version_code": 1,
    "classes": {
        # Real key `cccc` (single-segment) obfuscated to a DIFFERENT name
        # `cccd` — the reference `Lcccc;` is in-alphabet ({c,d}) and within
        # max_len (4), so the heuristic fires, but `cccc` is NOT an obfuscated
        # name, so it can only resolve through the real-key set.
        "cccc": {"obfuscated": "cccd", "methods": {}},
        "dddc": {
            "obfuscated": "dddc",
            "methods": {"m": {"obfuscated": "a", "signature": "()Lcccc;"}},
        },
    },
}


# A map whose `sources[].config` names the REAL committed signatures file
# (check 5 must ACCEPT a config that resolves). The self-test runs from the
# repo root and synthesises a maps/com.example.app/<vc>.json path, so this
# repo-relative path resolves to the worked example's signatures.
_VALID_SOURCE_CONFIG = {
    "schema_version": 2,
    "app": "com.example.app",
    "version": "1.0",
    "version_code": 1,
    "sources": [
        {"tool": "sigmatcher", "config": "signatures/com.example.app/signatures.yaml"},
        # A non-repo-internal config (bare filename) must be IGNORED, not flagged.
        {"tool": "hand-authored", "config": "notes.txt"},
    ],
    "classes": {"com.example.app.Foo": {"obfuscated": "aaaa", "methods": {}}},
}


# A map that exercises the status/superseded_by relationship in the ACCEPT
# direction: status == "superseded" WITH a superseded_by pointer (check 6 must
# accept this pairing). Carried as a v3 map for honesty; check_map ignores
# schema_version, so the value here is documentary.
_VALID_SUPERSEDED = {
    "schema_version": 3,
    "app": "com.example.app",
    "version": "1.0",
    "version_code": 1,
    "status": "superseded",
    "superseded_by": 2,
    "classes": {"com.example.app.Foo": {"obfuscated": "aaaa", "methods": {}}},
}


def _invalid_fixtures() -> dict:
    import copy

    fixtures: dict = {}

    # check 6: superseded_by present but status is NOT 'superseded' (here:
    # 'active'). The schema accepts both fields independently, so ONLY this
    # semantic check catches the meaningless pairing.
    f6a = copy.deepcopy(_VALID_MAP)
    f6a["status"] = "active"
    f6a["superseded_by"] = 2
    fixtures["superseded_by without status=superseded"] = f6a

    # check 6: superseded_by present with NO status at all (status absent ⇒
    # active ⇒ superseded_by still forbidden).
    f6b = copy.deepcopy(_VALID_MAP)
    f6b["superseded_by"] = 2
    fixtures["superseded_by with absent status"] = f6b

    # check 6: status == 'superseded' but superseded_by MISSING — a superseded
    # map must name its successor.
    f6c = copy.deepcopy(_VALID_MAP)
    f6c["status"] = "superseded"
    fixtures["status=superseded without superseded_by"] = f6c

    # check 5: dangling repo-internal source config — points under signatures/
    # but the file does not exist (the historical `signatures/example.json`
    # drift). Must be flagged.
    f5 = copy.deepcopy(_VALID_MAP)
    f5["sources"] = [{"tool": "sigmatcher", "config": "signatures/example.json"}]
    fixtures["dangling source config path"] = f5

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

    # check 1: dotted binary name — a SOURCE name leaked into a binary
    # descriptor. `Lfoo.bar.Baz;` must be rejected (binary names join with '/').
    f1d = copy.deepcopy(_VALID_MAP)
    f1d["classes"]["com.example.app.Foo"]["methods"]["doIt"]["signature"] = "(Lfoo.bar.Baz;)V"
    fixtures["malformed descriptor (dotted binary name)"] = f1d

    # check 1: space inside a binary name — no JVM name segment has whitespace.
    f1e = copy.deepcopy(_VALID_MAP)
    f1e["classes"]["com.example.app.Foo"]["methods"]["doIt"]["signature"] = "(L ;)V"
    fixtures["malformed descriptor (space in binary name)"] = f1e

    # check 2: unresolved app-internal type. It must be drawn from THIS map's
    # obfuscation alphabet ({a,b}, from class-level obfuscated names) and within
    # its length so the heuristic recognises it as app-internal — 'abba' looks
    # obfuscated but no class defines it. (Note 'abab' IS defined in _VALID_MAP,
    # so it can't be reused here.)
    f2 = copy.deepcopy(_VALID_MAP)
    f2["classes"]["com.example.app.Foo"]["methods"]["make"]["signature"] = "()Labba;"
    fixtures["unresolved app-internal type"] = f2

    # check 2 (field types): dangling field-type reference. `baba` is in the
    # map's alphabet ({a,b}) and within max_len (looks app-internal) but no
    # class defines it — so a field typed `Lbaba;` must be flagged.
    f2b = copy.deepcopy(_VALID_MAP)
    f2b["classes"]["com.example.app.Foo"]["fields"]["bar"]["type"] = "Lbaba;"
    fixtures["unresolved app-internal field type"] = f2b

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

    # check 4: missing `app` field — must be flagged, not silently skipped.
    f4b = copy.deepcopy(_VALID_MAP)
    del f4b["app"]
    fixtures["missing app field"] = f4b

    # check 4: non-string `app` field — same defensive flag.
    f4c = copy.deepcopy(_VALID_MAP)
    f4c["app"] = 123
    fixtures["non-string app field"] = f4c

    return fixtures


def _exact_count_fixtures() -> dict:
    """Invalid fixtures pinning an EXACT error count (not just non-empty).

    Used for cases where the COUNT is the regression we're guarding (e.g. a
    malformed descriptor shared by two colliding entries must not double-report
    the parse error).
    """
    import copy

    fixtures: dict = {}

    # check 1+3 interaction: two method entries that collide AND share a
    # malformed descriptor. The malformed descriptor must be reported once per
    # entry (2 total) and the collision path must NOT add a third error by
    # re-reporting the parse failure or a spurious overload error for an entry
    # that never parsed. Expect exactly 2 errors (one parse error per entry).
    fmd = copy.deepcopy(_VALID_MAP)
    fmd["classes"]["com.example.app.Foo"]["methods"]["over"] = [
        {"obfuscated": "c", "signature": "(I"},
        {"obfuscated": "c", "signature": "(I"},
    ]
    fixtures["malformed duplicate descriptor (exactly 2 errors)"] = (fmd, 2)

    return fixtures


def _self_test() -> int:
    failures = 0
    # Valid baselines: path's parent dir must equal the app field.
    for label, doc in (
        ("valid baseline", _VALID_MAP),
        ("valid real-key ref", _VALID_REALKEY_REF),
        ("valid source config", _VALID_SOURCE_CONFIG),
        ("valid superseded", _VALID_SUPERSEDED),
    ):
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

    # Exact-error-count fixtures: the COUNT is the regression guard.
    for label, (doc, want) in _exact_count_fixtures().items():
        synth_path = os.path.join("maps", "com.example.app", f"{doc['version_code']}.json")
        got = len(check_map(doc, synth_path))
        if got != want:
            failures += 1
            print(
                f"SELF-TEST FAIL: {label}: expected {want} error(s), got {got}",
                file=sys.stderr,
            )
        else:
            print(f"self-test: exact-count fixture pinned ({label}: {got} error(s))")

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
