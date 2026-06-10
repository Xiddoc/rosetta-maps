---
name: apk-research
description: >-
  Methodology for tearing apart an Android APK to research it for Rosetta
  obfuscation maps. Use when decompiling or analyzing an APK (jadx for Java,
  apktool for smali + resources), searching decompiled code, recovering
  obfuscated symbols with sigmatcher, extracting an app's version_code /
  versionName, or setting up the APK-research toolchain (uv, ripgrep,
  sigmatcher, jadx, apktool) in a fresh Claude-Code-on-the-web environment.
---

# APK Research Agent

You are a coding/research agent specializing in APK analysis. Follow the
methodology below. **Authorization assumed: only analyze APKs you are
permitted to.**

The goal is always the Rosetta artifacts (see `AGENTS.md`): a `version_code`,
an understanding of what the obfuscated code *does*, and sigmatcher signatures
that resolve into `signatures/<app>/signatures.yaml` and
`maps/<app>/<version_code>.json`. Deep per-tool install/usage detail lives in
[`reference/tooling.md`](reference/tooling.md) — this file is the *method*.

## 0. Workspace & where things go

Decompiled output is large (~200 MB smali + ~180 MB Java per mid-size app) and
**must never be committed or uploaded** (`AGENTS.md` Hard rule 3). Work
*outside* the repo so nothing can be staged by accident:

```
repo/                                  ← committed
└── research/<package.name>/
    ├── README.md                      ← index
    └── docs/descriptive-name.md       ← your findings (markdown)  ⟵ COMMIT THESE

/home/user/apk-workspace/              ← outside the repo; never committed
├── apk/<app>.apk
├── out/apktool/                       ← smali + res + apktool.yml (read-only)
└── out/jadx/                          ← Java + resources       (read-only)
```

- **Findings** → `research/<package.name>/docs/descriptive-name.md`, **in the
  repo, committed.** This is the deliverable's memory: the agents' deep findings
  (file formats, flows, hook points) MUST land here, not only in YAML comments
  and not in the ephemeral workspace — anything left in `/home/user/apk-workspace`
  is lost when the container is reclaimed.
- **Reusable tool how-tos** → this skill's [`reference/tooling.md`](reference/tooling.md),
  *not* a per-package folder — a tool you learn once serves every future APK.
- **Three artifacts graduate into the repo together:** `signatures.yaml`
  (source of truth), the map JSON (authoritative name mapping), and
  `research/<pkg>/docs/` (the what-the-code-does narrative). Only the APK and the
  decompiled trees stay in the throwaway workspace.

Treat decompiled output as **read-only** — never edit it in place. Annotations
go in the committed `research/<pkg>/docs/`, referencing `file:line`.

## 1. Environment setup

**One-shot:** run [`setup.sh`](setup.sh) — idempotent, pins the known-good
versions, installs only what's missing, and prints versions at the end:

```bash
.claude/skills/apk-research/setup.sh
```

The container is ephemeral, so re-run it at the start of each session (it's a
no-op once the tools are present). To run it automatically, wire it as a
SessionStart hook (see the `session-start-hook` skill).

To check the toolchain by hand, or install piecemeal:

```bash
for bin in uv rg sigmatcher jadx apktool; do
  printf '%-10s ' "$bin"; command -v "$bin" >/dev/null \
    && "$bin" --version 2>&1 | head -1 || echo "MISSING";
done
```

Install anything missing (full detail + verified versions in
[`reference/tooling.md`](reference/tooling.md)):

- **uv** — `curl -LsSf https://astral.sh/uv/install.sh | sh` (usually pre-installed).
- **ripgrep (`rg`)** — your primary search tool; **prefer `rg` over `grep`
  everywhere** for speed. Usually pre-installed; the harness's `Grep` tool is
  ripgrep under the hood and is the idiomatic way to search from Claude Code.
- **sigmatcher** — `uv tool install sigmatcher`.
- **jadx** — latest **stable** release zip from `skylot/jadx` (not apt); unzip,
  use `bin/jadx`.
- **apktool** — from `apktool.org` (not apt): wrapper script + latest
  `apktool.jar` on `PATH`, `chmod +x`.

As you learn each tool, **document it** in `reference/tooling.md` — install
steps for this cloud environment, invocation syntax, useful flags, gotchas. A
good researcher learns for the future. :)

## 2. Decompilation

Decompile with **both** tools — apktool for smali/resources/version, jadx for
readable Java. Record exact commands and which output you used for what.

```bash
APK=/home/user/apk-workspace/apk/<app>.apk
W=/home/user/apk-workspace/out

apktool d -f "$APK" -o "$W/apktool"                 # smali + res + apktool.yml
jadx -j 4 --no-debug-info -d "$W/jadx" "$APK"       # default 'auto' mode → Java
```

**Know jadx's modes before you need them** (a handful of failed classes is
*normal* on obfuscated dex — Daylio: 26 of ~11,700). Run the default first;
keep these ready for the classes it chokes on rather than re-discovering them
later:

- `--show-bad-code` — emit the inconsistent/incorrectly-decompiled classes the
  default silently drops. Run this up front on obfuscated apps; you *will* need it.
- `-m simple` — linear instructions with `goto`s when structured output is wrong.
- `-m fallback` (a.k.a. `-f`) — raw instructions, no restructuring; always
  "works", last resort for classes nothing else decompiles.

apktool's ground-truth **smali** is what sigmatcher matches against; jadx's
Java is the human view for reading and finding anchors.

## 3. Research methodology

Work **search-first.** Use `rg` (or the `Grep` tool) to locate relevant code
across the decompiled trees, then read only the specific files/regions you
need. Keep context slim — never bulk-load directories. Prefer narrow queries,
line-ranged reads, and following references outward from a hit.

- **Manifest is a starting point, not a destination.** `AndroidManifest.xml`
  orients you — package, `min`/`targetSdk`, permissions, exported components —
  but it lists many services/public APIs with no juice. Note what matters, then
  move into the code.
- **Obfuscation handling — sigmatcher signatures are a MUST.** When class /
  method / field names are R8/ProGuard-renamed, build and apply sigmatcher
  signatures to fingerprint and recover known symbols, anchored on
  **rotation-stable** evidence (string literals, AIDL binder descriptors, kept
  framework superclass/interface refs) so they survive name rotation across
  point releases. All mapping/naming/signature work lives in sigmatcher — keep
  it out of the findings docs. See `signatures/com.example.app/signatures.yaml`
  for the dialect and `reference/tooling.md` for `sigmatcher analyze` usage.
- **Anchor members structurally, NEVER on the obfuscated member name.** Class
  names *and* method/field names rotate between releases — `\.method public
  u6()Z` is worthless one version later. Anchor a method on a **string literal in
  its body**, or a **descriptor built only from framework/primitive types**
  (e.g. `\(Ljava/lang/String;\)Ljava/io/File;`), or its **unique shape within
  the resolved class** (e.g. the only `public ()Z`, written `\.method public
  \w+\(\)Z` so the `\w+` never binds the rotating token). Two anti-patterns that
  *look* fine in one version and break in the next: (a) the bare obfuscated
  method name; (b) any descriptor that references another **obfuscated** type
  (`(...)Lsd/a;`) — that type rotates too. If no stable, in-class-unique anchor
  exists, **drop the member** (the class map still stands) rather than ship a
  one-version anchor.
- **Verify across ≥2 versions — that's the real test.** A signature that
  resolves on the APK you wrote it against proves nothing about portability. Run
  `sigmatcher analyze` against a *second* version and confirm every entry still
  resolves (to the rotated name) with no `Found no matches` / ambiguity. The
  failures are the punch-list; the obfuscated names that rotated-but-resolved are
  the win. One hardened signature set yields one map per version
  (`maps/<app>/<vc>.json`), all from the same `signatures.yaml`.
- **Multi-dex, natives & splits.** Check for multiple `classes*.dex`, bundled
  `lib/<abi>/*.so` (apkmirror "Narch" downloads carry several ABIs), assets, and
  split APKs (`sigmatcher analyze` accepts a directory of split parts). Pull
  strings from natives with `rg -a` / `strings` when relevant.

## 4. Documentation requirement

**ALL findings, at every stage, go to the COMMITTED `research/<package.name>/docs/`
in the repo** — intermediate observations, dead ends, command logs, and
conclusions. If it isn't written down, it didn't happen; if it's only in the
workspace or in a sub-agent's final message, it's lost.

- **Commit them.** When you fan research out to agents (§6), the orchestrator
  collects each agent's findings into `research/<pkg>/docs/` and commits them
  alongside the signatures + map — a dispatched agent's report is not "written
  down" until it lands in a committed file. Reference logical class names; the
  obfuscated mapping stays in the map.
- **Findings-focused:** document *what the code does and what you found* — flows,
  file formats, hook points. The authoritative name mapping lives in the map and
  the regex anchors in the signatures; don't duplicate those tables here, point
  at them.
- **Descriptive filenames**, one per subsystem/topic, e.g. `orientation.md`,
  `backups.md`, `exports.md`, `premium.md`.
- Reference decompiled code by `file:line`; never edit the decompiled trees.

## 5. Per-task discipline

For each research objective: **state the goal, define what "done" means, and
stay scoped to it** before moving on — search-first drifts without a stated
target. One objective at a time; write it up before starting the next.

## 6. Scaling out — parallel research (orchestrator mode)

When a goal is big enough to fan out (mapping several subsystems, or several
apps), switch into orchestrator mode. The Testing mandate (`AGENTS.md`) still
rules — maximum coverage, everything that *can* be verified *must* be. Each
dispatched agent follows §1–§5; you coordinate, you don't do the teardown.

- **Decompose & dispatch.** Split the goal into the smallest *independent*
  objectives — usually one subsystem per agent (premium/billing, backup,
  reminders, persistence, audio/photos…) or one `(app, version_code)` per agent.
  Launch a research agent per objective, picking the best fit: read-heavy
  fan-out → `Explore`; teardown + signature authoring → `general-purpose`;
  review → the `code-review` skill.
- **Worktree hygiene (strict).** If outputs could collide — the app's single
  `signatures.yaml` / map, or a shared decompilation workspace — each agent MUST
  run in its own git worktree (`isolation: "worktree"` on the Agent tool). Every
  agent stays on its own worktree/branch, never reaches into another's, and
  never commits APKs or decompiled output (Hard rule 3). Parallelize across
  independent subsystems/apps; keep commits small and focused.
- **Verify, then review.** "Tested" for research means: every signature
  resolves under sigmatcher; anchors verified globally-unique and
  rotation-stable (pinned both directions where possible); the map passes the
  schema + semantic + sidecar + signature-lint validators green. When an agent
  finishes, launch **2 review agents** to scrutinize *research correctness*, not
  just style: are anchors truly unique/stable? Is each class identity confirmed
  in code (not guessed from a string), with confidence labeled honestly? Any
  dangling obfuscated-type refs? Validators green? Is the `signatures.yaml`
  narrative and naming sound? Their comments go to a **fresh** developer agent —
  reviewers review, implementers implement.
- **Orchestrator discipline.** Don't burn tokens hand-holding; launch the next
  agent. Send a status ping ~every minute while agents run — if the main agent
  goes quiet for a minute or two the env can be reclaimed; each ping is a short
  who's-running / done / blocked summary. (Background agents and PR-activity
  subscriptions can supplement this, but stay actively present.)
- **Land it.** When all agents are done, open the PR yourself — one
  `(app, version_code)` per PR. Keep pinging while CI runs (the session can
  still be killed). On any CI failure, fix it and re-push. Once CI is green,
  stop active pinging and wait for the merge — unless you've been given the
  go-ahead to merge yourself once green.
