#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEX_BIN="${TEX_BIN:-/Users/kakemyo/Library/TinyTeX/bin/universal-darwin}"
TEXMFVAR="${TEXMFVAR:-/private/tmp/bogp_texmf-var}"

mkdir -p "$TEXMFVAR" /private/tmp

PATH="$TEX_BIN:$PATH" TEXMFVAR="$TEXMFVAR" \
  lualatex -interaction=nonstopmode -halt-on-error \
  -output-directory /private/tmp \
  "$ROOT/notes/提案手法ver.1.tex"

PATH="$TEX_BIN:$PATH" TEXMFVAR="$TEXMFVAR" \
  lualatex -interaction=nonstopmode -halt-on-error \
  -output-directory /private/tmp \
  "$ROOT/notes/提案手法ver.1.tex"

cp /private/tmp/提案手法ver.1.pdf "$ROOT/notes/提案手法ver.1.pdf"
echo "Wrote $ROOT/notes/提案手法ver.1.pdf"
