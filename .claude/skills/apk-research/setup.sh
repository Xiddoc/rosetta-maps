#!/usr/bin/env bash
#
# apk-research toolchain installer — uv, ripgrep, sigmatcher, jadx, apktool.
# Pinned to the known-good versions the skill was verified against.
# Idempotent: re-running installs only what's missing. Targets x86_64 Linux
# (jadx/apktool are JVM-portable; ripgrep's prebuilt binary is x86_64). Per-tool
# detail and rationale: reference/tooling.md.
#
set -euo pipefail

SIGMATCHER_VERSION="1.9.2"
RIPGREP_VERSION="14.1.0"
JADX_VERSION="1.5.5"
APKTOOL_VERSION="3.0.2"
PREFIX="${PREFIX:-/usr/local}"        # CLI launchers go in $PREFIX/bin (must be on PATH)
JADX_HOME="${JADX_HOME:-/opt/jadx}"   # jadx is a dir tree; only its launcher is linked

bin="$PREFIX/bin"; mkdir -p "$bin"
export PATH="$bin:$HOME/.local/bin:$PATH"
have() { command -v "$1" >/dev/null 2>&1; }
say()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }

# Hard prerequisites we do NOT install (jadx/apktool need a JRE 17+).
for p in java curl tar unzip; do
  have "$p" || { echo "FATAL: '$p' is required but not on PATH." >&2; exit 1; }
done

# uv — Astral's Python tool manager; used to install sigmatcher.
have uv || { say "uv"; curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }

# sigmatcher — the Rosetta matcher (regex-over-smali).
have sigmatcher || { say "sigmatcher $SIGMATCHER_VERSION"; uv tool install "sigmatcher==$SIGMATCHER_VERSION"; }

# ripgrep — primary search tool (static musl binary; no package manager needed).
have rg || { say "ripgrep $RIPGREP_VERSION"
  t="ripgrep-$RIPGREP_VERSION-x86_64-unknown-linux-musl"
  curl -fsSL "https://github.com/BurntSushi/ripgrep/releases/download/$RIPGREP_VERSION/$t.tar.gz" | tar -xz -C /tmp
  install -m755 "/tmp/$t/rg" "$bin/rg"; }

# jadx — DEX → readable Java. Release zip → $JADX_HOME; launcher linked into $bin.
have jadx || { say "jadx $JADX_VERSION"
  curl -fsSL -o /tmp/jadx.zip "https://github.com/skylot/jadx/releases/download/v$JADX_VERSION/jadx-$JADX_VERSION.zip"
  rm -rf "$JADX_HOME"; mkdir -p "$JADX_HOME"; unzip -q /tmp/jadx.zip -d "$JADX_HOME"
  chmod +x "$JADX_HOME/bin/jadx"; ln -sf "$JADX_HOME/bin/jadx" "$bin/jadx"; }

# apktool — APK → smali + resources. Wrapper script + jar in $bin (apktool.org method).
have apktool || { say "apktool $APKTOOL_VERSION"
  curl -fsSL -o "$bin/apktool" https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool
  curl -fsSL -o "$bin/apktool.jar" "https://github.com/iBotPeaches/Apktool/releases/download/v$APKTOOL_VERSION/apktool_${APKTOOL_VERSION}.jar"
  chmod +x "$bin/apktool"; }

say "installed:"
for b in uv rg sigmatcher jadx apktool; do printf '  %-10s ' "$b"; "$b" --version 2>&1 | head -1; done
