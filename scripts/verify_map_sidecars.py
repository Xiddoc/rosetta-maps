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
  * Encoding: UTF-8 text, exactly ONE logical line, optionally terminated by a
    single trailing `\n`.
  * Content: coreutils `sha256sum` format — `<digest>␠␠<basename>`: a
    lowercase 64-hex SHA-256 of the EXACT bytes of the map file, two ASCII
    spaces, then the bare map filename (basename only, no directory). This
    makes `sha256sum -c 30405.json.sha256` work directly from the map's
    directory. The basename token is OPTIONAL (a digest-only line verifies),
    but if present it MUST equal the map's basename.

VERIFICATION ALGORITHM (identical on every side — `verify_sidecar`; the
authoritative prose lives in `docs/reference/integrity.md`):

  1. Take ONLY the first line of the sidecar (content up to the first `\n`; a
     single optional trailing `\n` is allowed). Reject input that has MORE than
     one non-empty line — a single-map sidecar is exactly one line; multi-entry
     coreutils files are explicitly out of scope (see ONE-MAP-PER-SIDECAR).
  2. Split that line on ASCII whitespace (tolerating leading/trailing
     whitespace and any of single-space / multiple-spaces / tab separators).
     The FIRST token is the expected digest; lowercase it.
  3. Reject if it doesn't match ^[0-9a-f]{64}$.
  4. If a SECOND token (the basename) is present it MUST equal the map file's
     basename (e.g. `30405.json`); a mismatch FAILS CLOSED (catches a
     misfiled / copy-pasted sidecar). An absent basename token is allowed.
  5. Compute SHA-256 over the EXACT committed map-file bytes (raw bytes, never
     re-serialized).
  6. Plain lowercase-hex equality. Match -> ok; mismatch -> FAIL CLOSED.

ONE-MAP-PER-SIDECAR — a sidecar describes exactly ONE map (one line). The
multi-entry coreutils `sha256sum` file form (many `<digest>  <name>` lines in
one file) is deliberately OUT OF SCOPE; an authenticity tier is a future,
separate sibling file (`<version_code>.json.sig`), never extra lines here.

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
    verify_map_sidecars.py --emit FILE       # (re)write FILE's `.sha256` sidecar
    verify_map_sidecars.py --self-test       # run built-in accept/reject

`--emit` is the canonical authoring path: it writes `FILE.sha256` from the
real map bytes via the same `render_sidecar` the verifier trusts, so an emitted
sidecar always verifies (and `sha256sum -c` still works). Prefer it over
hand-running `sha256sum` so the emitter and verifier can never disagree.

Verification (no `--emit`) also reports ORPHAN sidecars — a `*.json.sha256`
whose `*.json` map was renamed/deleted, which the per-map glob would otherwise
never visit — and fails when any is found.

Exit status is 0 only when every map whose sidecar is present verifies (maps
without a sidecar are skipped, not failed) AND no orphan sidecar exists.
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


@dataclass(frozen=True)
class _ParsedSidecar:
    """The digest (and optional basename) parsed from a single-line sidecar."""

    digest: str
    basename: str | None


def parse_sidecar(sidecar_text: str) -> _ParsedSidecar | None:
    """Parse the canonical single-line sidecar (see the module VERIFICATION
    ALGORITHM — code and `docs/reference/integrity.md` describe IDENTICAL rules).

    Returns the normalised digest plus the optional basename token, or None when
    the sidecar is malformed: empty, MORE than one non-empty line, or a first
    token that is not a lowercase 64-hex SHA-256. The basename, if present, is
    returned verbatim for the caller to match against the map (an empty-string
    basename never occurs because we split on whitespace).
    """
    # Only the first line is significant; a single optional trailing newline is
    # allowed. Any further NON-EMPTY line makes the sidecar malformed.
    lines = sidecar_text.split("\n")
    first = lines[0]
    if any(rest.strip() for rest in lines[1:]):
        return None  # more than one non-empty line — out of scope, fail closed
    tokens = first.split()
    if not tokens:
        return None
    digest = tokens[0].lower()
    if not _DIGEST_RE.match(digest):
        return None
    basename = tokens[1] if len(tokens) > 1 else None
    return _ParsedSidecar(digest=digest, basename=basename)


def verify_sidecar(
    map_bytes: bytes, sidecar_text: str, map_basename: str | None = None
) -> Result:
    """Pure verification core: does `sidecar_text` bind `map_bytes`?

    This is the algorithm the rosetta-frida / rosetta-xposed `rosetta pull`
    clients implement identically. It performs NO I/O — callers read the files
    — so it is trivially unit-testable from the self-test and reusable by any
    client. Fails CLOSED: a malformed sidecar, a basename mismatch, or any
    digest mismatch is FAILED.

    `map_basename` is the map file's bare filename (e.g. `30405.json`); when a
    sidecar carries a basename token it MUST equal it. Pass None to skip the
    basename check (digest-only verification).
    """
    parsed = parse_sidecar(sidecar_text)
    if parsed is None:
        return Result(
            Status.FAILED,
            "malformed sidecar: expected exactly one line whose first "
            "whitespace-delimited token is a lowercase 64-hex SHA-256 digest "
            "(coreutils 'sha256sum' format '<digest>  <basename>')",
        )
    if (
        map_basename is not None
        and parsed.basename is not None
        and parsed.basename != map_basename
    ):
        return Result(
            Status.FAILED,
            f"basename mismatch: sidecar names '{parsed.basename}' but it sits "
            f"beside '{map_basename}' (a misfiled or copy-pasted sidecar)",
        )
    actual = expected_digest(map_bytes)
    if parsed.digest != actual:
        return Result(
            Status.FAILED,
            f"digest mismatch: sidecar declares {parsed.digest} but the map "
            f"bytes hash to {actual} (the map or its sidecar was altered)",
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


def find_orphan_sidecars(roots: list[str]) -> list[str]:
    """Return sidecars under `roots` whose map file is missing (orphans).

    The per-map verify path is driven by the `maps/**/*.json` glob, so a
    sidecar whose map was RENAMED or DELETED is never visited — it silently
    lingers. This globs `<root>/**/*.json.sha256` and returns every sidecar
    that has no corresponding `*.json` map beside it. Roots may be files or
    directories; files are scanned by their containing directory.
    """
    import glob

    orphans: list[str] = []
    seen: set[str] = set()
    for root in roots:
        base = root if os.path.isdir(root) else os.path.dirname(root) or "."
        for side in glob.glob(
            os.path.join(base, "**", "*.json" + SIDECAR_SUFFIX), recursive=True
        ):
            if side in seen:
                continue
            seen.add(side)
            map_path = side[: -len(SIDECAR_SUFFIX)]
            if not os.path.exists(map_path):
                orphans.append(side)
    return sorted(orphans)


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
    except UnicodeDecodeError as exc:  # non-UTF-8 sidecar bytes
        # UnicodeDecodeError subclasses ValueError; catch it explicitly so the
        # "sidecar must be UTF-8 text" rule is a named, fail-closed case.
        return Result(Status.FAILED, f"sidecar is not valid UTF-8 text: {exc}")
    return verify_sidecar(map_bytes, sidecar_text, os.path.basename(map_path))


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

    bn = "30405.json"  # the map basename the sidecars name

    # (a) matching sidecar -> PASS. The full coreutils line (digest + basename)
    #     and a digest-only line must both verify, since the basename token is
    #     optional and we read the digest from the first token.
    check(
        "matching sidecar (full sha256sum line)",
        verify_sidecar(_MAP_BYTES, f"{_GOOD_DIGEST}  {bn}\n", bn),
        Status.OK,
    )
    check(
        "matching sidecar (digest token only)",
        verify_sidecar(_MAP_BYTES, _GOOD_DIGEST + "\n", bn),
        Status.OK,
    )
    # Digest-only WITHOUT a trailing newline still verifies (the newline is
    # optional) — pin that a bare 64-hex line passes.
    check(
        "matching sidecar (digest only, no trailing newline)",
        verify_sidecar(_MAP_BYTES, _GOOD_DIGEST, bn),
        Status.OK,
    )
    # An UPPERCASE digest is normalised to lowercase before comparison, so it
    # still verifies — pin that the normalisation actually happens.
    check(
        "matching sidecar (uppercase digest normalised)",
        verify_sidecar(_MAP_BYTES, _GOOD_DIGEST.upper() + f"  {bn}\n", bn),
        Status.OK,
    )

    # Separator / whitespace tolerance: the line is split on ASCII whitespace,
    # so leading whitespace, multiple-space and tab separators all parse the
    # same digest + basename and verify.
    check(
        "matching sidecar (leading whitespace before digest)",
        verify_sidecar(_MAP_BYTES, f"   {_GOOD_DIGEST}  {bn}\n", bn),
        Status.OK,
    )
    check(
        "matching sidecar (multiple-spaces separator)",
        verify_sidecar(_MAP_BYTES, f"{_GOOD_DIGEST}     {bn}\n", bn),
        Status.OK,
    )
    check(
        "matching sidecar (tab separator)",
        verify_sidecar(_MAP_BYTES, f"{_GOOD_DIGEST}\t{bn}\n", bn),
        Status.OK,
    )
    # A bare CR is whitespace too, so a CRLF-terminated single line still
    # parses to the same digest + basename and verifies.
    check(
        "matching sidecar (CRLF line ending)",
        verify_sidecar(_MAP_BYTES, f"{_GOOD_DIGEST}  {bn}\r\n", bn),
        Status.OK,
    )

    # Basename token present and CORRECT -> PASS; absent -> PASS (optional);
    # present and WRONG -> FAIL CLOSED (a misfiled / copy-pasted sidecar).
    check(
        "missing basename token is allowed",
        verify_sidecar(_MAP_BYTES, _GOOD_DIGEST + "\n", bn),
        Status.OK,
    )
    check(
        "wrong basename token (misfiled sidecar) fails closed",
        verify_sidecar(_MAP_BYTES, f"{_GOOD_DIGEST}  99999.json\n", bn),
        Status.FAILED,
    )

    # (b) tampered / mismatching digest -> FAIL (fail closed). Flip one nibble.
    tampered = ("0" if _GOOD_DIGEST[0] != "0" else "1") + _GOOD_DIGEST[1:]
    check(
        "tampered digest (one nibble flipped)",
        verify_sidecar(_MAP_BYTES, f"{tampered}  {bn}\n", bn),
        Status.FAILED,
    )
    # Same digest, but the map bytes were altered after the sidecar was made.
    check(
        "altered map bytes vs a once-correct digest",
        verify_sidecar(_MAP_BYTES + b"x", f"{_GOOD_DIGEST}  {bn}\n", bn),
        Status.FAILED,
    )

    # (c) malformed sidecar (bad hex / wrong length / empty / multi-line) -> FAIL.
    check(
        "malformed sidecar (non-hex character)",
        verify_sidecar(_MAP_BYTES, "z" * 64 + f"  {bn}\n", bn),
        Status.FAILED,
    )
    check(
        "malformed sidecar (too short)",
        verify_sidecar(_MAP_BYTES, _GOOD_DIGEST[:-1] + f"  {bn}\n", bn),
        Status.FAILED,
    )
    check(
        "malformed sidecar (too long)",
        verify_sidecar(_MAP_BYTES, _GOOD_DIGEST + f"ab  {bn}\n", bn),
        Status.FAILED,
    )
    check(
        "malformed sidecar (empty)",
        verify_sidecar(_MAP_BYTES, "\n", bn),
        Status.FAILED,
    )
    # More than one NON-EMPTY line is malformed (multi-entry coreutils files are
    # out of scope) — even when the first line is a perfectly good digest.
    check(
        "malformed sidecar (extra trailing non-empty line)",
        verify_sidecar(
            _MAP_BYTES, f"{_GOOD_DIGEST}  {bn}\n{_GOOD_DIGEST}  other.json\n", bn
        ),
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

        # A non-UTF-8 sidecar fails closed through verify_map_path (the
        # UnicodeDecodeError branch). Write raw invalid-UTF-8 bytes.
        nonutf8 = os.path.join(tmp, "40000.json")
        with open(nonutf8, "wb") as fh:
            fh.write(_MAP_BYTES)
        with open(sidecar_path_for(nonutf8), "wb") as fh:
            fh.write(b"\xff\xfe not utf-8\n")
        check(
            "on-disk non-UTF-8 sidecar fails closed",
            verify_map_path(nonutf8),
            Status.FAILED,
        )

        # An on-disk sidecar that names the WRONG basename fails closed even
        # though its digest matches the bytes (misfiled / copy-pasted sidecar).
        misfiled = os.path.join(tmp, "50000.json")
        with open(misfiled, "wb") as fh:
            fh.write(_MAP_BYTES)
        with open(sidecar_path_for(misfiled), "w", encoding="utf-8") as fh:
            fh.write(f"{_GOOD_DIGEST}  99999.json\n")
        check(
            "on-disk wrong-basename sidecar fails closed",
            verify_map_path(misfiled),
            Status.FAILED,
        )

        # Orphan-sidecar detection: a sidecar whose map is gone is flagged, a
        # paired sidecar is not. Pin BOTH directions.
        orphan_side = os.path.join(tmp, "60000.json" + SIDECAR_SUFFIX)
        with open(orphan_side, "w", encoding="utf-8") as fh:
            fh.write(f"{_GOOD_DIGEST}  60000.json\n")
        orphans = find_orphan_sidecars([tmp])
        if orphan_side in orphans and sidecar_path_for(paired) not in orphans:
            print(f"self-test: orphan-sidecar detection -> flagged {orphan_side}")
        else:
            failures += 1
            print(
                "SELF-TEST FAIL: orphan-sidecar detection: expected to flag "
                f"{orphan_side} and not the paired sidecar; got {orphans}",
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

    if args and args[0] == "--emit":
        emit_targets = args[1:]
        if not emit_targets:
            print("::error::--emit requires at least one map FILE", file=sys.stderr)
            return 2
        for path in emit_targets:
            side = sidecar_path_for(path)
            with open(side, "w", encoding="utf-8") as fh:
                fh.write(render_sidecar(path))
            print(f"wrote {side}")
        return 0

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

    # Orphan sweep: a `*.json.sha256` whose map was renamed/deleted is never
    # visited by the per-map args above, so it can silently linger. Glob the
    # directories the args live in and fail on any sidecar with no map.
    orphans = find_orphan_sidecars(args)
    for side in orphans:
        overall = 1
        print(f"::error file={side}::orphan sidecar — its map file is missing")
        print(f"ORPHAN {side}: its map file is missing", file=sys.stderr)

    print(
        f"sidecar verification: {verified} verified, {skipped} skipped "
        f"(no sidecar), {len(orphans)} orphan(s)",
        file=sys.stderr,
    )
    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv))
