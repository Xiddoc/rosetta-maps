# Map safety model

This page states the **real safety invariant** of a rosetta map and why a
tampered or malicious map can never be more than a *correctness* bug — never
code execution. It replaces the earlier "integrity gap / detached `.sha256`
sidecar" design, which was removed (maps#37): that sidecar bound a map's own
bytes but added no protection a PR author couldn't trivially restate (they edit
the map and its digest in the same PR), and it implied a threat — code delivery
— that a map cannot carry.

## Maps are data, never code

A `maps/<app>/<version_code>.json` is **pure data**: a lookup table from real
class/method/field names to the obfuscated names that already exist in the
already-loaded target app. Nothing in a map is ever executed, `eval`-ed,
loaded as a class, or otherwise turned into control flow:

- The resolver only ever **reads** the map and returns a handle
  (`java.lang.reflect.Member` in rosetta-xposed, a `Java.use` proxy in
  rosetta-frida) to a class/method/field **that already exists in the app the
  user is already running**. It cannot conjure new code; it can only point at
  code the app itself shipped.
- A map never names a *file path*, a *URL*, a *shell command*, or a *native
  symbol to dlopen*. Its value space is obfuscated names and JVM type
  descriptors — strings the resolver compares and looks up, never strings it
  runs.

## Therefore: the worst a bad map can do is resolve the wrong member

Because a map only steers name resolution, a malicious or tampered map is, at
absolute worst, a **correctness / denial-of-service** bug:

- **Wrong member** — the map points `requestTicket` at the obfuscated name of
  some *other* method, so the developer's hook fires on the wrong target. That
  is a bug in the hook's behaviour, scoped entirely to what the developer's own
  hook code already does.
- **Unresolvable member** — the map points at a name that does not exist, so
  resolution fails (an error / no-op). That is a denial of service for that one
  hook, nothing more.

In **no** case does a map deliver, fetch, or execute code. There is no
deserialization-of-untrusted-code path, no plugin-load path, no template/`eval`
path. A map is consumed exactly the way a phone-book is consumed: you might dial
a wrong number, but the phone-book cannot dial for you. This is why public CI is
**structural only** (schema + semantics) and deliberately does not try to be a
malware scanner — there is no executable payload to scan for.

## What already protects map distribution

- **Transport integrity comes for free from the channel.** Maps are acquired
  over **git-over-HTTPS** at build/author time on a developer machine (never
  fetched on the device — see [the trust model](trust-model.md)). TLS protects
  the bytes in transit, and git is **content-addressed**: every blob, tree, and
  commit is named by its own SHA, so a corrupted or substituted map byte
  changes a hash git already verifies on checkout. A redundant per-file digest
  sidecar restated this guarantee without strengthening it.
- **`signer_sha256` is a functional version guard, not a security control.** It
  records the signing-certificate hash the map was authored against so a client
  can refuse to apply a map to the *wrong app build* (a stale/mismatched map is
  a correctness hazard). It answers "is this the app this map was written for?"
  — a selection/sanity question — and is not, and was never, a publisher-
  authenticity mechanism.

## If publisher authenticity is ever wanted

A future need to prove **who** published a map (not merely that the bytes are
intact) folds into the existing **attestation tier**
(`<version_code>.json.att.json`, see [the trust model](trust-model.md)), not a
digest sidecar. An attestation is a *detached signature over the map's digest by
a trusted party* — which is the only thing that actually binds bytes to a
publisher. Because it is a separate, opt-in file beside the map, it adds
authenticity without changing the map format or the strict
`additionalProperties: false` clients, and without reintroducing a self-
referential hash field inside the map (still forbidden by the AGENTS.md
anti-scope, for the self-reference reason as much as any security one).
