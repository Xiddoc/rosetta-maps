# APK-research tooling — install & usage reference

Deep reference for the tools the `apk-research` skill drives. Every command and
version here was run and verified in a Claude-Code-on-the-web cloud environment
(Ubuntu 24.04, OpenJDK 21, Python 3.11). When a value is environment-specific
it's called out.

Contents: [Java](#java-prerequisite) · [uv](#uv) · [sigmatcher](#sigmatcher) ·
[jadx](#jadx) · [apktool](#apktool) ·
[ripgrep & strings](#ripgrep--strings-search) · [Gotchas](#gotchas)

---

## Java (prerequisite)

jadx and apktool are both JVM tools. The cloud box ships **OpenJDK 21**:

```bash
$ java -version
openjdk version "21.0.10" 2026-01-20
```

No action needed. If a future box lacks a JRE, install one (`apt-get install
-y openjdk-21-jre-headless`) before jadx/apktool.

---

## uv

Astral's Python package & tool manager. Used here only to install sigmatcher
into an isolated, PATH-exposed tool environment (no venv juggling).

**Already installed** on the cloud box:

```bash
$ uv --version
uv 0.8.17
```

If ever missing, the official standalone installer (no apt, no system Python):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# puts uv in ~/.local/bin — ensure that's on PATH
```

Useful commands:

```bash
uv tool install <pkg>     # install a CLI tool in its own env, exposed on PATH
uv tool list              # what's installed (and which executables each exposes)
uv tool upgrade <pkg>     # upgrade one tool
```

`uv tool install` drops executables in `~/.local/bin`. Make sure that's on
`PATH` (`export PATH="$HOME/.local/bin:$PATH"`).

---

## sigmatcher

The Rosetta-side matcher: regex-over-smali signatures that identify
classes / methods / fields and resolve obfuscated → original names into a
map. PyPI package `sigmatcher`; source `github.com/oriori1703/sigmatcher`.

### Install

```bash
uv tool install sigmatcher
```

```bash
$ sigmatcher --version
Sigmatcher version: 1.9.2
```

### Commands

```
sigmatcher analyze   Analyze an APK using provided signatures (the main verb)
sigmatcher schema    Print the JSON schema for writing signature definitions
sigmatcher convert   Convert a mapping output between formats
sigmatcher cache     Manage the results cache (dir / clean)
```

### `analyze`

```bash
sigmatcher analyze <APP_INPUT> --signatures <file.yaml> [options]
```

- `APP_INPUT` — an `.apk` / `.apkm` / `.xapk`, **or** a directory of split-APK
  parts. sigmatcher runs apktool internally; it does **not** need you to
  decompile first.
- `--signatures FILE` — required; repeatable. Multiple files are merged.
- `--output-format [raw|enigma|jadx|legacy]` — `raw` (default) is the JSON the
  Rosetta map is built from; `jadx` / `enigma` emit deobfuscation mappings you
  can load into those tools; `legacy` is the old format.
- `--output-file PATH` — write the mapping (otherwise printed to stdout).
- `--apktool TEXT` — apktool command to use (default `apktool`; must be on PATH).
- `--debug` / `--tree-errors` — verbose match-failure diagnostics; use these
  when a signature won't resolve.
- `--cache-dir PATH` / `SIGMATCHER_CACHE_DIR` — defaults to `~/.cache/sigmatcher`.

Verified run (minimal one-class signature against the real Daylio APK):

```bash
$ sigmatcher analyze apk/daylio-1.63.12-252.apk \
    --signatures daylio-demo.yaml --no-progress
{
    "MyApplication": {
        "original": { "name": "MyApplication", "package": "net.daylio" },
        "new":      { "name": "MyApplication", "package": "net.daylio" },
        "matched_methods": [], "matched_fields": [], "exports": []
    }
}
```

(`original == new` here because Daylio's own `net.daylio.*` class names aren't
name-obfuscated — only their internals / dependencies are. That's itself a
useful research finding when planning where signatures add value.)

### Writing signatures

`sigmatcher schema` prints the definition schema. The repo's worked example
(`signatures/com.example.app/signatures.yaml`) is the canonical reference — a
signature pins a class on stable evidence and may carry nested `methods:` /
`fields:`:

```yaml
- name: 'MyApplication'           # logical (original) name you assign
  package: 'net.daylio'
  signatures:
      - signature: '"Noto Color Emoji Compat"'   # regex over the class smali
        type: regex
        count: 1                                  # exact / range e.g. 1-2
```

Anchor on **rotation-stable** evidence (string literals, AIDL binder
descriptor strings, stable framework superclass refs) so signatures keep
resolving as obfuscated names rotate between point releases.

### cache

```bash
sigmatcher cache dir      # print cache path
sigmatcher cache clean    # wipe it (do this if results look stale)
```

---

## jadx

DEX → readable **Java**. Best tool for *reading* and grepping an app to find
anchor strings and understand class relationships. (apktool's smali is the
ground truth you actually write regex against; jadx is the human view.)

### Install (latest stable release zip — not apt)

```bash
curl -sL -o /tmp/jadx.zip \
  https://github.com/skylot/jadx/releases/download/v1.5.5/jadx-1.5.5.zip
mkdir -p /opt/jadx && unzip -q /tmp/jadx.zip -d /opt/jadx
chmod +x /opt/jadx/bin/jadx
ln -sf /opt/jadx/bin/jadx /usr/local/bin/jadx
```

The zip contains `bin/jadx` (CLI) and `bin/jadx-gui` (no use headless) plus
`lib/`. Keep the tree together and symlink only the launcher.

```bash
$ jadx --version
1.5.5
```

#### Fallback when GitHub release downloads are blocked (Maven Central)

Some managed/cloud environments allow `repo1.maven.org` but return **403 on
`github.com/.../releases/download`** (and on `codeload.github.com`) — the release
zip above then can't be fetched. jadx also publishes to Maven Central, but the
`jadx-cli` "all" jar there is **not** a real fat jar and its transitive deps must
be assembled. Resolve `io.github.skylot:jadx-cli:<ver>` (plus the input plugins
`jadx-dex-input`, `jadx-smali-input`, `jadx-java-convert`) and run
`jadx.cli.JadxCLI` off the assembled classpath. Two gotchas seen in the wild:

- **`jadx-cli` hard-references logback** (`ch.qos.logback.classic.Level` in
  `LogHelper`), so you need **both** `logback-classic` *and* `logback-core` on the
  classpath — a resolver that pulls only `logback-classic` crashes at startup with
  `NoClassDefFoundError: ch/qos/logback/classic/Level` (and, one layer up,
  `LogbackServiceProvider Unable to get public no-arg constructor`). Dropping
  logback entirely makes jadx swallow all errors via the SLF4J NOP logger — you
  then see `exit 1` with no message. Keep both logback jars.
- Large jars (jadx-core ~2 MB+) may `IncompleteRead` through a re-terminating
  proxy when fetched with Python `urllib`; fetch jars with `curl` (`--retry`)
  instead. A ~40-line stdlib POM walker (parent + `${...}` + dependencyManagement,
  skipping test/provided/optional) is enough to build the classpath.

Run it via a wrapper: `java -Xmx6g -cp "$CP" jadx.cli.JadxCLI "$@"`.

### Usage

```bash
jadx -j 4 --no-debug-info -d <outdir> <app.apk>
```

- `-d` — output dir; produces `sources/` (Java) and `resources/`.
- `-j N` — parallelism.
- `--no-debug-info` — cleaner output; drop it if you want line/debug data.
- `ERROR - finished with errors, count: N` is **normal** — a handful of
  classes (≈26 of ~11,700 for Daylio) fail to decompile. The rest are fine.

**Decompilation modes** (`-m <mode>`), best → most literal — reach for the next
one only when a class won't come out clean:

| Mode / flag | What it does | When |
| --- | --- | --- |
| `-m auto` (default) | best-effort structured Java | normal reading |
| `--show-bad-code` | also emit the inconsistent classes `auto` silently drops | run up front on obfuscated apps |
| `-m simple` | linear instructions with `goto`s | structured output looks wrong |
| `-m fallback` (`-f`) | raw instructions, no restructuring; always "works" | last resort for un-decompilable classes |

Then read/search the Java with ripgrep (see below):

```bash
rg -l 'someAnchorString' <outdir>/sources/
```

Single-class spot decompile (faster than the whole APK):

```bash
jadx --single-class net.daylio.MyApplication -d /tmp/one <app.apk>
```

---

## apktool

APK → **smali** + decoded resources + the manifest, and crucially
`apktool.yml` with the version metadata. Smali is what sigmatcher signatures
match against.

### Install (apktool.org manual install — not apt)

The documented install is a wrapper script + the jar, both in `/usr/local/bin`:

```bash
# Linux wrapper script (from the Apktool repo, as apktool.org links it)
curl -sL -o /usr/local/bin/apktool \
  https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool
# Latest jar, renamed to apktool.jar (the wrapper looks for it next to itself)
curl -sL -o /usr/local/bin/apktool.jar \
  https://github.com/iBotPeaches/Apktool/releases/download/v3.0.2/apktool_3.0.2.jar
chmod +x /usr/local/bin/apktool
```

```bash
$ apktool --version
3.0.2
```

#### Fallback when GitHub release downloads are blocked (Maven Central)

When `github.com/.../releases/download` 403s but `repo1.maven.org` is reachable,
grab the self-contained CLI jar straight from Maven Central — unlike jadx's, this
one **is** a fat jar (`Main-Class: brut.apktool.Main`, ~22 MB, bundles
`brut.androlib`):

```bash
curl -fsSL -o /opt/tools/apktool-cli-3.0.2.jar \
  https://repo1.maven.org/maven2/org/apktool/apktool-cli/3.0.2/apktool-cli-3.0.2.jar
printf '#!/usr/bin/env bash\nexec java -jar /opt/tools/apktool-cli-3.0.2.jar "$@"\n' \
  > ~/.local/bin/apktool && chmod +x ~/.local/bin/apktool
```

`sigmatcher analyze` shells out to whatever `apktool` is on `PATH`, so this
wrapper is all it needs.

### Usage

```bash
apktool d -f <app.apk> -o <outdir>     # decode (-f overwrites an existing outdir)
```

Output of interest:

```
<outdir>/apktool.yml              ← versionCode / versionName / sdk info
<outdir>/AndroidManifest.xml      ← decoded manifest (package=, components)
<outdir>/smali/  smali_classes2/  ← baksmali'd dex (one dir per classesN.dex)
<outdir>/res/                     ← decoded resources
```

Read the version (the map's identity key):

```bash
$ grep -A4 sdkInfo <outdir>/apktool.yml
sdkInfo:
  minSdkVersion: 26
  targetSdkVersion: 35
versionInfo:
  versionCode: 252
  versionName: 1.63.12
```

apktool prints `W: Could not decode attribute value...` warnings on some
resource references — harmless for research; ignore them.

First run downloads a framework to `~/.local/share/apktool/framework/1.apk`;
that's expected and cached.

---

## ripgrep & strings (search)

Search-first research lives on these two. Both ship on the cloud box.

```bash
$ rg --version
ripgrep 14.1.0
$ strings --version
GNU strings (GNU Binutils for Ubuntu) 2.42
```

**ripgrep (`rg`)** — primary search across the decompiled trees; prefer it over
`grep` for speed. From Claude Code, the `Grep` tool is ripgrep under the hood
and is the idiomatic entry point. Handy flags:

```bash
rg -l 'pattern' <dir>          # files-with-matches only (cheap, context-slim)
rg -n 'pattern' <dir>          # with line numbers, to drive line-ranged reads
rg -a 'pattern' lib/           # treat binaries as text (search native .so)
rg -tjava 'class .* implements Foo' out/jadx/sources   # restrict by file type
```

**strings** — pull readable literals from native libraries / assets, the
companion to `rg -a` for `.so` files:

```bash
strings -n 8 out/apktool/lib/arm64-v8a/libfoo.so | rg -i 'http|token|key'
```

---

## Gotchas

- **GitHub API rate limit.** Unauthenticated `api.github.com` is 60 req/hr and
  returns `{"message":"API rate limit exceeded..."}` instead of JSON — which
  silently breaks any `releases/latest` JSON parse. To resolve the newest tag,
  read the HTML redirect instead:
  `curl -sI https://github.com/<owner>/<repo>/releases/latest | grep -i '^location:'`
- **PATH for uv tools.** `sigmatcher` lands in `~/.local/bin`; export it if a
  fresh shell can't find the command.
- **Never commit APKs or decompiled output** (Hard rule 3). Decompile under
  `/home/user/apk-workspace` (outside the repo). ~200 MB smali + ~180 MB Java
  per mid-size app — keep it out of git entirely.
- **jadx "finished with errors" is not failure** — expect a few unrecoverable
  classes; the output is still usable.
- **Ephemeral box.** Tools, caches, and the workspace vanish when the
  container is reclaimed. Re-run Setup each session; only repo-committed
  `signatures.yaml` / map JSON persist.
- **Multi-volume RAR uploads (`.part1.rar`/`.part2.rar`/…).** A large APK may
  arrive split into RAR5 volumes. `unrar-free` (apt) mishandles RAR5 multi-volume
  (extracts a truncated file); use `7z` (`apt-get install -y p7zip-full p7zip-rar`).
  Volume auto-detection keys off a **consistent base name**, so first strip any
  per-file upload hash prefixes — rename to `Name.part1.rar`, `Name.part2.rar`, …
  — then `7z x Name.part1.rar` reassembles all volumes (it reports `Volumes = N`).
- **sigmatcher matching model** (verify anchors before writing them): a class
  `signature` regex must match the target class **exactly `count` times** (default
  `count: 1`) AND that `(regex, count)` must be **globally unique to one class
  file**, or the class won't resolve. A `count` mismatch (e.g. a string that
  appears twice) yields `Found no matches!`. Verify both with ripgrep:
  `rg -oN --pcre2 -e 'REGEX' <class.smali> | wc -l` (== count) and
  `rg -lN --pcre2 -e 'REGEX' <smali-roots> | wc -l` (== 1). Method `signature`s
  resolve within the already-matched class; **field** signatures proved
  unreliable on Moovit (skip field-level mapping — anchor classes + methods).
