#!/usr/bin/env python3
"""Verify detached `.sha256` integrity sidecars for published maps (maps#17).

A published map (`maps/<app>/<version_code>.json`) carries no hash OF ITSELF —
a self-hash can't live in the file it hashes, and a new field would break the
strict `additionalProperties: false` clients (see `docs/reference/integrity.md`
and the AGENTS.md "no self-referential map hash field" anti-scope). Instead, a
map's own-bytes integrity is bound from OUTSIDE the artifact by a detached
sidecar that travels next to it:

    maps/com.example.app/30405.json          ← the canonical, unchanged map
    maps/com.example.app/30405.json.sha256   ← this sidecar (detached digest)

This script is the OWNER-side verifier; the rosetta-frida / rosetta-xposed
`rosetta pull` clients implement the IDENTICAL algorithm (see `verify_sidecar`)
so the same sidecar binds the bytes the same way on both sides.

SIDECAR FORMAT (authoritative — kept in lockstep with the consumer clients):

  * Location: directly next to the map; filename = map filename + `.sha256`.
  * Encoding: UTF-8 text, exactly one logical line, terminated by a single
    `\n`.
  * Content: coreutils `sha256sum` format — `<digest>␠␠<basename>`: a
    lowercase 64-hex SHA-256 of the EXACT bytes of the map file, two ASCII
    spaces, then the bare map filename (basename only, no directory). This
    makes `sha256sum -c 30405.json.sha256` work directly from the map's
    directory.

VERIFICATION ALGORITHM (identical on every side — `verify_sidecar`):

  1. Read the sidecar text; the first whitespace-delimited token is the
     expected digest; lowercase it.
  2. Reject if it doesn't match ^[0-9a-f]{64}$.
  3. Compute SHA-256 over the EXACT committed map-file bytes (raw bytes, never
     re-serialized).
  4. Plain lowercase-hex equality. Match -> ok; mismatch -> FAIL CLOSED.

TIER — transport integrity, NOT publisher authenticity. A bare digest detects
corruption/tampering in transit (a poisoned mirror, a truncated download); it
does NOT prove WHO published the map — a PR author who edits the map can edit
the sidecar in the same PR. Because the sidecar is a SEPARATE file, a future
authenticity tier (a detached `.json.sig` signature over this digest) can be
layered on without changing this format. See `docs/reference/integrity.md`.

ROLLOUT — the sidecar is OPTIONAL. A map with NO sidecar is NOT a failure
(`verify_map_path` returns an explicit SKIPPED result); only a PRESENT sidecar
that fails to verify is an error. This lets the corpus adopt sidecars
incrementally without a flag day.

It is APK-free (Hard rule 3): it reads ONLY the committed map bytes and the
committed sidecar text. It uses nothing but the standard library (hashlib),
like the rest of CI.

Usage:
    verify_map_sidecars.py FILE [FILE ...]   # verify each map's sidecar
    verify_map_sidecars.py --self-test       # run built-in accept/reject

Exit status is 0 only when every map whose sidecar is present verifies (and
maps without a sidecar are skipped, not failed).
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum

# The sidecar lives at <map path> + this suffix.
SIDECAR_SUFFIX = ".sha256"

# A SHA-256 digest, lowercase hex, exactly 64 characters.
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class Status(Enum):
    """Outcome of verifying one map against its (maybe-absent) sidecar."""

    OK = "ok"          # sidecar present and the digest binds the map bytes
    SKIPPED = "skipped"  # no sidecar present — optional during rollout
    FAILED = "failed"  # sidecar present but did not verify (fail closed)


@dataclass(frozen=True)
class Result:
    """The outcome plus a human-readable reason."""

    status: Status
    reason: str

    @property
    def ok(self) -> bool:
        """True when this result must NOT fail the run (OK or SKIPPED)."""
        return self.status in (Status.OK, Status.SKIPPED)


def expected_digest(map_bytes: bytes) -> str:
    """Return the canonical lowercase-hex SHA-256 of the EXACT map bytes.

    The single place hashing happens — both verification and sidecar emission
    go through this so the two can never disagree on the algorithm.
    """
    return hashlib.sha256(map_bytes).hexdigest()


def parse_sidecar_digest(sidecar_text: str) -> str | None:
    """Extract and normalise the digest from sidecar text.

    The first whitespace-delimited token is the digest (coreutils
    `sha256sum` format is `<digest>␠␠<basename>`); we lowercase it and require
    it to be exactly 64 hex characters. Returns the normalised digest, or None
    when the sidecar is malformed (empty, or a bad-hex / wrong-length token).
    """
    tokens = sidecar_text.split()
    if not tokens:
        return None
    digest = tokens[0].lower()
    if not _DIGEST_RE.match(digest):
        return None
    return digest


def verify_sidecar(map_bytes: bytes, sidecar_text: str) -> Result:
    """Pure verification core: does `sidecar_text` bind `map_bytes`?

    This is the algorithm the rosetta-frida / rosetta-xposed `rosetta pull`
    clients implement identically. It performs NO I/O — callers read the files
    — so it is trivially unit-testable from the self-test and reusable by any
    client. Fails CLOSED: a malformed sidecar or any digest mismatch is FAILED.
    """
    declared = parse_sidecar_digest(sidecar_text)
    if declared is None:
        return Result(
            Status.FAILED,
            "malformed sidecar: first token is not a lowercase 64-hex SHA-256 "
            "digest (expected coreutils 'sha256sum' format "
            "'<digest>  <basename>')",
        )
    actual = expected_digest(map_bytes)
    if declared != actual:
        return Result(
            Status.FAILED,
            f"digest mismatch: sidecar declares {declared} but the map bytes "
            f"hash to {actual} (the map or its sidecar was altered)",
        )
    return Result(Status.OK, f"digest verified ({actual})")


def sidecar_path_for(map_path: str) -> str:
    """The sidecar path for a map path (map path + the `.sha256` suffix)."""
    return map_path + SIDECAR_SUFFIX


def render_sidecar(map_path: str) -> str:
    """Render the canonical sidecar TEXT for a map file (incl. trailing \\n).

    coreutils `sha256sum` format: `<digest>␠␠<basename>\\n`. Used to author /
    regenerate a sidecar; the verifier and this emitter share `expected_digest`
    so an emitted sidecar always verifies.
    """
    with open(map_path, "rb") as fh:
        map_bytes = fh.read()
    basename = os.path.basename(map_path)
    return f"{expected_digest(map_bytes)}  {basename}\n"


def verify_map_path(map_path: str) -> Result:
    """Verify one map against its on-disk sidecar (absent sidecar -> SKIPPED).

    The OPT-IN rollout rule lives here: a missing sidecar is SKIPPED (not a
    failure); a present sidecar is read and handed, with the map bytes, to the
    pure `verify_sidecar` core.
    """
    side_path = sidecar_path_for(map_path)
    if not os.path.exists(side_path):
        return Result(Status.SKIPPED, "no sidecar present (optional)")
    try:
        with open(map_path, "rb") as fh:
            map_bytes = fh.read()
    except OSError as exc:
        return Result(Status.FAILED, f"could not read map file: {exc}")
    try:
        with open(side_path, encoding="utf-8") as fh:
            sidecar_text = fh.read()
    except OSError as exc:
        return Result(Status.FAILED, f"could not read sidecar: {exc}")
    except ValueError as exc:  # non-UTF-8 sidecar bytes
        return Result(Status.FAILED, f"sidecar is not valid UTF-8 text: {exc}")
    return verify_sidecar(map_bytes, sidecar_text)


# --- Built-in self-test -----------------------------------------------------
#
# The constraint is pinned in BOTH directions (the testing mandate): a matching
# sidecar PASSES, and every way a sidecar can be wrong FAILS. The opt-in rule
# (no sidecar -> PASS) is pinned too, so it can't silently turn into a failure.

# Arbitrary but fixed "map bytes" — the exact bytes are what we hash.
_MAP_BYTES = b'{"schema_version": 2, "app": "com.example.app"}\n'
_GOOD_DIGEST = hashlib.sha256(_MAP_BYTES).hexdigest()


def _self_test() -> int:
    failures = 0

    def check(label: str, got: Result, want: Status) -> None:
        nonlocal failures
        if got.status is want:
            print(f"self-test: {label} -> {got.status.value} ({got.reason})")
        else:
            failures += 1
            print(
                f"SELF-TEST FAIL: {label}: expected {want.value}, got "
                f"{got.status.value} ({got.reason})",
                file=sys.stderr,
            )

    # (a) matching sidecar -> PASS. The full coreutils line (digest + basename)
    #     and a digest-only line must both verify, since we read only the first
    #     token.
    check(
        "matching sidecar (full sha256sum line)",
        verify_sidecar(_MAP_BYTES, f"{_GOOD_DIGEST}  30405.json\n"),
        Status.OK,
    )
    check(
        "matching sidecar (digest token only)",
        verify_sidecar(_MAP_BYTES, _GOOD_DIGEST + "\n"),
        Status.OK,
    )
    # An UPPERCASE digest is normalised to lowercase before comparison, so it
    # still verifies — pin that the normalisation actually happens.
    check(
        "matching sidecar (uppercase digest normalised)",
        verify_sidecar(_MAP_BYTES, _GOOD_DIGEST.upper() + "  30405.json\n"),
        Status.OK,
    )

    # (b) tampered / mismatching digest -> FAIL (fail closed). Flip one nibble.
    tampered = ("0" if _GOOD_DIGEST[0] != "0" else "1") + _GOOD_DIGEST[1:]
    check(
        "tampered digest (one nibble flipped)",
        verify_sidecar(_MAP_BYTES, f"{tampered}  30405.json\n"),
        Status.FAILED,
    )
    # Same digest, but the map bytes were altered after the sidecar was made.
    check(
        "altered map bytes vs a once-correct digest",
        verify_sidecar(_MAP_BYTES + b"x", f"{_GOOD_DIGEST}  30405.json\n"),
        Status.FAILED,
    )

    # (c) malformed sidecar (bad hex / wrong length / empty) -> FAIL.
    check(
        "malformed sidecar (non-hex character)",
        verify_sidecar(_MAP_BYTES, "z" * 64 + "  30405.json\n"),
        Status.FAILED,
    )
    check(
        "malformed sidecar (too short)",
        verify_sidecar(_MAP_BYTES, _GOOD_DIGEST[:-1] + "  30405.json\n"),
        Status.FAILED,
    )
    check(
        "malformed sidecar (too long)",
        verify_sidecar(_MAP_BYTES, _GOOD_DIGEST + "ab  30405.json\n"),
        Status.FAILED,
    )
    check(
        "malformed sidecar (empty)",
        verify_sidecar(_MAP_BYTES, "\n"),
        Status.FAILED,
    )

    # (d) opt-in rollout: a map with NO sidecar -> SKIPPED (must not fail).
    #     Exercised through the on-disk path so the rollout rule itself is
    #     pinned, not just the pure core. Use a temp dir with a map and no
    #     sidecar, plus a sibling that DOES have a (matching) sidecar.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        lonely = os.path.join(tmp, "10000.json")
        with open(lonely, "wb") as fh:
            fh.write(_MAP_BYTES)
        check(
            "map with no sidecar (opt-in rollout)",
            verify_map_path(lonely),
            Status.SKIPPED,
        )

        paired = os.path.join(tmp, "20000.json")
        with open(paired, "wb") as fh:
            fh.write(_MAP_BYTES)
        # render_sidecar must emit a sidecar that verifies (emitter/verifier
        # share one hashing routine) — pins the round-trip.
        with open(sidecar_path_for(paired), "w", encoding="utf-8") as fh:
            fh.write(render_sidecar(paired))
        check(
            "rendered sidecar round-trips through verification",
            verify_map_path(paired),
            Status.OK,
        )

        # A present-but-tampered on-disk sidecar fails through verify_map_path.
        bad = os.path.join(tmp, "30000.json")
        with open(bad, "wb") as fh:
            fh.write(_MAP_BYTES)
        with open(sidecar_path_for(bad), "w", encoding="utf-8") as fh:
            fh.write(f"{tampered}  30000.json\n")
        check(
            "on-disk tampered sidecar fails closed",
            verify_map_path(bad),
            Status.FAILED,
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
    verified = skipped = 0
    for path in args:
        result = verify_map_path(path)
        if result.status is Status.OK:
            verified += 1
            print(f"ok {path}: {result.reason}")
        elif result.status is Status.SKIPPED:
            skipped += 1
            print(f"skip {path}: {result.reason}")
        else:
            overall = 1
            print(f"::error file={sidecar_path_for(path)}::{result.reason}")
            print(f"FAIL {path}: {result.reason}", file=sys.stderr)
    print(
        f"sidecar verification: {verified} verified, {skipped} skipped "
        f"(no sidecar)",
        file=sys.stderr,
    )
    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv))
