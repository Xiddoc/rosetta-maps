#!/usr/bin/env python3
"""Validate detached reproduction-attestation sidecars (maps#18).

A published map (`maps/<app>/<version_code>.json`) records nothing about WHO
reproduced it from its signatures + the APK — the `.sha256` sidecar
(`verify_map_sidecars.py`) binds the map's own BYTES (transport integrity), and
the schema validates its SHAPE, but neither says "a human rebuilt these exact
bytes from the source-of-truth and signed the result." That correctness claim
is the first higher trust tier (RFC 0001 Decision 4; docs/reference/trust-model.md),
and it is recorded in a SEPARATE sidecar beside the map — never a field inside
the map (AGENTS.md anti-scope: no self-referential trust field; it would also
break the strict `additionalProperties: false` clients):

    maps/com.example.app/30405.json            ← the canonical, unchanged map
    maps/com.example.app/30405.json.sha256     ← bytes-integrity sidecar (maps#17)
    maps/com.example.app/30405.json.att.json   ← THIS attestation sidecar (maps#18)

This validator is the PUBLIC-CI, tier-1 STRUCTURAL gate for that sidecar. It is
APK-free (Hard rule 3): it reads ONLY the committed attestation JSON and the
committed map bytes. It does NOT fetch the APK and does NOT cryptographically
verify the signatures against a keyring — that is an off-CI higher tier (see the
trust ladder in docs/reference/trust-model.md). What it DOES enforce:

  1. attestation-version  — `attestation_version` is the gated literal 1.
  2. shape                — required keys present, value types/patterns correct,
                            no unknown keys (mirrors rosetta-attestation.schema.json;
                            this script also runs standalone with no check-jsonschema).
  3. map-binding          — `map_sha256` equals the SHA-256 of the EXACT committed
                            bytes of the map the sidecar sits beside. Fails closed
                            on mismatch, so an attestation can never drift off the
                            map it claims to cover.
  4. identity-match       — the sidecar's `app` / `version_code` equal the attested
                            map's `app` / `version_code` (and the filename's
                            `<version_code>`), catching a misfiled / copy-pasted
                            attestation.
  5. reproduced=true      — an attestation that does not claim reproduction is not
                            an attestation.

PRECEDENCE / LADDER (descriptive — only tier 1 is enforced here): structural
attestation (this file) < signature-verified-against-keyring (off-CI) <
self-hosted trusted-runner reproduction < device-telemetry confirmation. A
higher tier SUBSUMES the ones below it; none of them ever uploads an APK.

OPT-IN ROLLOUT — the attestation sidecar is OPTIONAL. A map with NO `.att.json`
is SKIPPED (not failed); only a PRESENT sidecar that fails to validate is an
error. Like `verify_map_sidecars.py`, verification also flags ORPHAN sidecars
(an `*.att.json` whose map was renamed/deleted).

Usage:
    validate_attestations.py FILE [FILE ...]   # validate each map's attestation
    validate_attestations.py --self-test       # run built-in accept/reject

Exit status is 0 only when every map whose attestation is present validates
(maps without one are skipped) AND no orphan attestation exists.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum

# The attestation sidecar lives at <map path> + this suffix.
ATT_SUFFIX = ".att.json"

# The only attestation-sidecar format version this validator understands.
ATTESTATION_VERSION = 1

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_APP_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_MAX_SAFE_INT = 9007199254740991

KNOWN_METHODS = {"minisign", "ssh-ed25519", "gpg"}

_TOP_KEYS = {
    "attestation_version",
    "app",
    "version_code",
    "map_sha256",
    "reproduced",
    "signatures_sha256",
    "apk",
    "attestations",
}
_REQUIRED_TOP = {
    "attestation_version",
    "app",
    "version_code",
    "map_sha256",
    "reproduced",
    "attestations",
}
_APK_KEYS = {"sha256", "signer_sha256", "source"}
_ATT_KEYS = {"attestor", "method", "signature", "signed_at", "public_key", "notes"}
_ATT_REQUIRED = {"attestor", "method", "signature", "signed_at"}


class Status(Enum):
    """Outcome of validating one map against its (maybe-absent) attestation."""

    OK = "ok"            # attestation present and it validates + binds the map
    SKIPPED = "skipped"  # no attestation present — optional during rollout
    FAILED = "failed"    # attestation present but did not validate (fail closed)


@dataclass(frozen=True)
class Result:
    status: Status
    reason: str

    @property
    def ok(self) -> bool:
        """True when this result must NOT fail the run (OK or SKIPPED)."""
        return self.status in (Status.OK, Status.SKIPPED)


def att_path_for(map_path: str) -> str:
    """The attestation-sidecar path for a map path (map path + `.att.json`)."""
    return map_path + ATT_SUFFIX


def _shape_errors(doc: object) -> list[str]:
    """Structural (shape) errors, mirroring rosetta-attestation.schema.json.

    Kept in lockstep with the JSON Schema so this script is a self-contained
    gate even where check-jsonschema is unavailable; the schema is still the
    canonical statement of the format and is exercised by schema/samples/.
    """
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["attestation is not a JSON object"]

    extra = set(doc) - _TOP_KEYS
    if extra:
        errors.append(f"unknown top-level key(s): {sorted(extra)}")
    missing = _REQUIRED_TOP - set(doc)
    if missing:
        errors.append(f"missing required key(s): {sorted(missing)}")

    av = doc.get("attestation_version")
    if av != ATTESTATION_VERSION:
        errors.append(
            f"attestation_version must be the literal {ATTESTATION_VERSION}, got {av!r}"
        )

    app = doc.get("app")
    # Mirror the schema's `app` bounds EXACTLY (minLength:1 is subsumed by the
    # pattern, maxLength:256 is NOT — enforce it here so standalone mode, with no
    # check-jsonschema, applies the same length cap the schema does).
    if not isinstance(app, str) or not _APP_RE.match(app) or len(app) > 256:
        errors.append(f"app must be a dotted package id (<= 256 chars), got {app!r}")

    vc = doc.get("version_code")
    if isinstance(vc, bool) or not isinstance(vc, int) or not (0 <= vc <= _MAX_SAFE_INT):
        errors.append(f"version_code must be an integer in [0, 2^53-1], got {vc!r}")

    ms = doc.get("map_sha256")
    if not isinstance(ms, str) or not _SHA256_RE.match(ms):
        errors.append("map_sha256 must be lowercase 64-hex SHA-256")

    rep = doc.get("reproduced")
    if rep is not True:
        errors.append("reproduced must be the literal boolean true")

    sigs = doc.get("signatures_sha256")
    if sigs is not None and (not isinstance(sigs, str) or not _SHA256_RE.match(sigs)):
        errors.append("signatures_sha256, when present, must be lowercase 64-hex SHA-256")

    apk = doc.get("apk")
    if apk is not None:
        if not isinstance(apk, dict):
            errors.append("apk, when present, must be an object")
        else:
            apk_extra = set(apk) - _APK_KEYS
            if apk_extra:
                errors.append(f"apk has unknown key(s): {sorted(apk_extra)}")
            asha = apk.get("sha256")
            if not isinstance(asha, str) or not _SHA256_RE.match(asha):
                errors.append("apk.sha256 must be lowercase 64-hex SHA-256")
            asigner = apk.get("signer_sha256")
            if asigner is not None and (
                not isinstance(asigner, str) or not _SHA256_RE.match(asigner)
            ):
                errors.append("apk.signer_sha256, when present, must be lowercase 64-hex SHA-256")
            asrc = apk.get("source")
            if asrc is not None and (not isinstance(asrc, str) or len(asrc) > 4096):
                errors.append("apk.source, when present, must be a string <= 4096 chars")

    atts = doc.get("attestations")
    if not isinstance(atts, list) or not (1 <= len(atts) <= 100):
        errors.append("attestations must be a non-empty list (1..100 entries)")
    else:
        for i, att in enumerate(atts):
            errors.extend(_attestation_shape_errors(att, f"attestations[{i}]"))

    return errors


def _attestation_shape_errors(att: object, where: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(att, dict):
        return [f"{where}: each attestation must be an object"]
    extra = set(att) - _ATT_KEYS
    if extra:
        errors.append(f"{where}: unknown key(s): {sorted(extra)}")
    missing = _ATT_REQUIRED - set(att)
    if missing:
        errors.append(f"{where}: missing required key(s): {sorted(missing)}")

    attestor = att.get("attestor")
    if not isinstance(attestor, str) or not (1 <= len(attestor) <= 256):
        errors.append(f"{where}: attestor must be a 1..256-char string")

    method = att.get("method")
    if method not in KNOWN_METHODS:
        errors.append(f"{where}: method must be one of {sorted(KNOWN_METHODS)}, got {method!r}")

    sig = att.get("signature")
    if not isinstance(sig, str) or not (1 <= len(sig) <= 8192):
        errors.append(f"{where}: signature must be a 1..8192-char string")

    when = att.get("signed_at")
    if not isinstance(when, str) or not _DATE_RE.match(when):
        errors.append(f"{where}: signed_at must be an ISO-8601 date (YYYY-MM-DD)")

    pk = att.get("public_key")
    if pk is not None and (not isinstance(pk, str) or not (1 <= len(pk) <= 4096)):
        errors.append(f"{where}: public_key, when present, must be a 1..4096-char string")

    notes = att.get("notes")
    if notes is not None and (not isinstance(notes, str) or len(notes) > 4096):
        errors.append(f"{where}: notes, when present, must be a string <= 4096 chars")

    return errors


def check_attestation(doc: object, map_bytes: bytes, map_doc: object, map_path: str) -> list[str]:
    """Return human-readable errors (empty == valid) for one attestation.

    Combines the structural shape check with the SEMANTIC checks the schema
    can't express: the digest binds the committed map bytes, and the identity
    triple (app / version_code / filename) agrees with the attested map.
    """
    errors = _shape_errors(doc)
    if errors:
        # Shape failures make the semantic checks meaningless (wrong types); stop.
        return errors

    assert isinstance(doc, dict)  # _shape_errors guaranteed object-ness

    # --- check 3: map-binding ---
    actual = hashlib.sha256(map_bytes).hexdigest()
    if doc["map_sha256"] != actual:
        errors.append(
            f"map_sha256 {doc['map_sha256']} does not bind the map bytes "
            f"(committed map hashes to {actual}) — the attestation is stale or "
            f"sits beside the wrong map"
        )

    # --- check 4: identity-match against the map and the filename ---
    base = os.path.splitext(os.path.basename(map_path))[0]  # "<version_code>.json" -> "<version_code>"
    try:
        fname_vc = int(base)
    except ValueError:
        fname_vc = None
    if fname_vc is not None and doc["version_code"] != fname_vc:
        errors.append(
            f"version_code {doc['version_code']} != map filename version_code {fname_vc}"
        )
    if isinstance(map_doc, dict):
        m_app = map_doc.get("app")
        m_vc = map_doc.get("version_code")
        if isinstance(m_app, str) and doc["app"] != m_app:
            errors.append(f"app '{doc['app']}' != attested map app '{m_app}'")
        if isinstance(m_vc, int) and not isinstance(m_vc, bool) and doc["version_code"] != m_vc:
            errors.append(f"version_code {doc['version_code']} != attested map version_code {m_vc}")

    return errors


def validate_map_path(map_path: str) -> Result:
    """Validate one map against its on-disk attestation (absent -> SKIPPED)."""
    att = att_path_for(map_path)
    if not os.path.exists(att):
        return Result(Status.SKIPPED, "no attestation sidecar present (optional)")
    try:
        with open(map_path, "rb") as fh:
            map_bytes = fh.read()
    except OSError as exc:
        return Result(Status.FAILED, f"could not read map file: {exc}")
    try:
        map_doc = json.loads(map_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        map_doc = None  # map itself is malformed; the schema/layout steps report that
    try:
        with open(att, encoding="utf-8") as fh:
            doc = json.load(fh)
    except OSError as exc:
        return Result(Status.FAILED, f"could not read attestation: {exc}")
    except UnicodeDecodeError as exc:
        return Result(Status.FAILED, f"attestation is not valid UTF-8 text: {exc}")
    except ValueError as exc:
        return Result(Status.FAILED, f"attestation is not valid JSON: {exc}")
    errors = check_attestation(doc, map_bytes, map_doc, map_path)
    if errors:
        return Result(Status.FAILED, "; ".join(errors))
    return Result(Status.OK, f"{len(doc['attestations'])} attestation(s) validated")


def find_orphan_attestations(roots: list[str]) -> list[str]:
    """Return `*.att.json` sidecars under `roots` whose map file is missing."""
    import glob

    orphans: list[str] = []
    seen: set[str] = set()
    for root in roots:
        base = root if os.path.isdir(root) else os.path.dirname(root) or "."
        for side in glob.glob(os.path.join(base, "**", "*.json" + ATT_SUFFIX), recursive=True):
            if side in seen:
                continue
            seen.add(side)
            map_path = side[: -len(ATT_SUFFIX)]
            if not os.path.exists(map_path):
                orphans.append(side)
    return sorted(orphans)


# --- Built-in self-test -----------------------------------------------------
#
# The constraint is pinned in BOTH directions: a well-formed attestation that
# binds its map PASSES, and every distinct way one can be wrong FAILS. The
# opt-in rule (no sidecar -> SKIPPED) is pinned too.

# A deliberately MINIMAL binding fixture, NOT a schema-valid map: the attestation
# validator only reads the map's `app` / `version_code` (for the identity cross-
# check) and hashes its raw bytes (for the map-binding check), so the fixture
# carries just those keys. It intentionally omits the fields a real
# `schema_version: 2` map needs (e.g. `classes`, `captured_at`); do not treat it
# as a valid map — the map schema/layout steps validate real maps elsewhere.
_MAP_BYTES = b'{"schema_version": 2, "app": "com.example.app", "version_code": 30405}\n'
_MAP_DOC = json.loads(_MAP_BYTES)
_GOOD_MAP_DIGEST = hashlib.sha256(_MAP_BYTES).hexdigest()
_HEX = "ab" * 32  # an arbitrary valid 64-hex token for non-binding fields


def _valid_doc() -> dict:
    return {
        "attestation_version": 1,
        "app": "com.example.app",
        "version_code": 30405,
        "map_sha256": _GOOD_MAP_DIGEST,
        "reproduced": True,
        "signatures_sha256": _HEX,
        "apk": {"sha256": _HEX, "signer_sha256": _HEX, "source": "f-droid"},
        "attestations": [
            {
                "attestor": "alice",
                "method": "minisign",
                "public_key": "RWQ...",
                "signature": "sig-bytes-base64",
                "signed_at": "2026-06-08",
                "notes": "rebuilt from signatures.yaml @ deadbeef",
            }
        ],
    }


def _invalid_docs() -> dict:
    import copy

    out: dict = {}

    d = copy.deepcopy(_valid_doc())
    d["attestation_version"] = 2
    out["wrong attestation_version"] = d

    d = copy.deepcopy(_valid_doc())
    del d["map_sha256"]
    out["missing map_sha256"] = d

    d = copy.deepcopy(_valid_doc())
    d["unexpected"] = "x"
    out["unknown top-level key"] = d

    d = copy.deepcopy(_valid_doc())
    d["map_sha256"] = "00" * 32
    out["map_sha256 does not bind the map bytes"] = d

    d = copy.deepcopy(_valid_doc())
    d["map_sha256"] = "ZZ" + _GOOD_MAP_DIGEST[2:]
    out["map_sha256 not lowercase hex"] = d

    d = copy.deepcopy(_valid_doc())
    d["app"] = "com.other.pkg"
    out["app != attested map app"] = d

    # Over-length `app` — pins the schema's maxLength:256 in the standalone
    # script. Build a dotted id that is pattern-valid but > 256 chars (the
    # binding-identity cross-check would also reject it, but the shape gate
    # fires first, which is what we are pinning here).
    d = copy.deepcopy(_valid_doc())
    d["app"] = "com." + ("a" * 256)
    out["app exceeds 256-char cap"] = d

    d = copy.deepcopy(_valid_doc())
    d["version_code"] = 99999
    out["version_code != map + filename"] = d

    d = copy.deepcopy(_valid_doc())
    d["reproduced"] = False
    out["reproduced is false"] = d

    d = copy.deepcopy(_valid_doc())
    d["attestations"] = []
    out["empty attestations list"] = d

    d = copy.deepcopy(_valid_doc())
    d["attestations"][0]["method"] = "rot13"
    out["unknown signature method"] = d

    d = copy.deepcopy(_valid_doc())
    del d["attestations"][0]["signature"]
    out["attestation missing signature"] = d

    d = copy.deepcopy(_valid_doc())
    d["attestations"][0]["signed_at"] = "08-06-2026"
    out["bad signed_at date"] = d

    d = copy.deepcopy(_valid_doc())
    d["apk"]["sha256"] = "nope"
    out["bad apk.sha256"] = d

    d = copy.deepcopy(_valid_doc())
    d["apk"]["url"] = "http://example.com/app.apk"
    out["unknown apk key"] = d

    return out


def _self_test() -> int:
    failures = 0
    synth_path = os.path.join("maps", "com.example.app", "30405.json")

    errs = check_attestation(_valid_doc(), _MAP_BYTES, _MAP_DOC, synth_path)
    if errs:
        failures += 1
        print(f"SELF-TEST FAIL: valid attestation rejected: {errs}", file=sys.stderr)
    else:
        print("self-test: valid attestation accepted")

    # A valid doc with NO optional apk/signatures_sha256 must still pass.
    minimal = {
        "attestation_version": 1,
        "app": "com.example.app",
        "version_code": 30405,
        "map_sha256": _GOOD_MAP_DIGEST,
        "reproduced": True,
        "attestations": [
            {
                "attestor": "bob",
                "method": "ssh-ed25519",
                "signature": "sig",
                "signed_at": "2026-06-08",
            }
        ],
    }
    if check_attestation(minimal, _MAP_BYTES, _MAP_DOC, synth_path):
        failures += 1
        print("SELF-TEST FAIL: minimal valid attestation rejected", file=sys.stderr)
    else:
        print("self-test: minimal valid attestation accepted")

    # Boundary (accept direction) for the app maxLength:256 cap: an app exactly
    # at the 256-char limit must still pass the shape gate. Use a fresh map doc
    # whose `app` matches, so only the length cap (not the identity cross-check)
    # is under test.
    long_app = "com." + ("a" * 252)  # 4 + 252 == 256 chars exactly
    assert len(long_app) == 256
    boundary_bytes = json.dumps(
        {"schema_version": 2, "app": long_app, "version_code": 30405}
    ).encode("utf-8")
    boundary_doc = json.loads(boundary_bytes)
    boundary_att = _valid_doc()
    boundary_att["app"] = long_app
    boundary_att["map_sha256"] = hashlib.sha256(boundary_bytes).hexdigest()
    if check_attestation(boundary_att, boundary_bytes, boundary_doc, synth_path):
        failures += 1
        print("SELF-TEST FAIL: app at 256-char cap rejected", file=sys.stderr)
    else:
        print("self-test: app at the 256-char cap accepted")

    for label, doc in _invalid_docs().items():
        if not check_attestation(doc, _MAP_BYTES, _MAP_DOC, synth_path):
            failures += 1
            print(f"SELF-TEST FAIL: invalid fixture accepted: {label}", file=sys.stderr)
        else:
            print(f"self-test: invalid fixture rejected ({label})")

    # Opt-in rollout + on-disk paths + orphan detection, exercised end to end.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        appdir = os.path.join(tmp, "com.example.app")
        os.makedirs(appdir)

        lonely = os.path.join(appdir, "10000.json")
        with open(lonely, "wb") as fh:
            fh.write(_MAP_BYTES)
        if validate_map_path(lonely).status is not Status.SKIPPED:
            failures += 1
            print("SELF-TEST FAIL: map with no attestation should SKIP", file=sys.stderr)
        else:
            print("self-test: map with no attestation -> skipped (opt-in)")

        # A paired, binding attestation validates on disk. The map basename is
        # 30405.json so version_code 30405 lines up with the filename.
        paired = os.path.join(appdir, "30405.json")
        with open(paired, "wb") as fh:
            fh.write(_MAP_BYTES)
        with open(att_path_for(paired), "w", encoding="utf-8") as fh:
            json.dump(_valid_doc(), fh)
        if validate_map_path(paired).status is not Status.OK:
            failures += 1
            print("SELF-TEST FAIL: paired binding attestation should pass", file=sys.stderr)
        else:
            print("self-test: paired binding attestation -> ok")

        # A present-but-tampered attestation fails closed on disk.
        bad = os.path.join(appdir, "40000.json")
        with open(bad, "wb") as fh:
            fh.write(_MAP_BYTES)
        bad_doc = _valid_doc()
        bad_doc["version_code"] = 40000  # matches filename, but map says 30405
        bad_doc["map_sha256"] = _GOOD_MAP_DIGEST  # still binds the bytes
        with open(att_path_for(bad), "w", encoding="utf-8") as fh:
            json.dump(bad_doc, fh)
        if validate_map_path(bad).status is not Status.FAILED:
            failures += 1
            print("SELF-TEST FAIL: vc mismatching the map should fail", file=sys.stderr)
        else:
            print("self-test: attestation vc mismatching the map -> failed")

        # Non-JSON attestation fails closed.
        broken = os.path.join(appdir, "50000.json")
        with open(broken, "wb") as fh:
            fh.write(_MAP_BYTES)
        with open(att_path_for(broken), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        if validate_map_path(broken).status is not Status.FAILED:
            failures += 1
            print("SELF-TEST FAIL: malformed JSON attestation should fail", file=sys.stderr)
        else:
            print("self-test: malformed JSON attestation -> failed")

        # Orphan attestation (its map is gone) is flagged; the paired one is not.
        orphan = os.path.join(appdir, "60000.json" + ATT_SUFFIX)
        with open(orphan, "w", encoding="utf-8") as fh:
            json.dump(_valid_doc(), fh)
        orphans = find_orphan_attestations([tmp])
        if orphan in orphans and att_path_for(paired) not in orphans:
            print(f"self-test: orphan-attestation detection -> flagged {os.path.basename(orphan)}")
        else:
            failures += 1
            print(
                f"SELF-TEST FAIL: orphan detection: expected to flag {orphan}, got {orphans}",
                file=sys.stderr,
            )

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
    validated = skipped = 0
    for path in args:
        result = validate_map_path(path)
        if result.status is Status.OK:
            validated += 1
            print(f"ok {path}: {result.reason}")
        elif result.status is Status.SKIPPED:
            skipped += 1
            print(f"skip {path}: {result.reason}")
        else:
            overall = 1
            print(f"::error file={att_path_for(path)}::{result.reason}")
            print(f"FAIL {path}: {result.reason}", file=sys.stderr)

    orphans = find_orphan_attestations(args)
    for side in orphans:
        overall = 1
        print(f"::error file={side}::orphan attestation — its map file is missing")
        print(f"ORPHAN {side}: its map file is missing", file=sys.stderr)

    print(
        f"attestation validation: {validated} validated, {skipped} skipped "
        f"(no attestation), {len(orphans)} orphan(s)",
        file=sys.stderr,
    )
    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv))
