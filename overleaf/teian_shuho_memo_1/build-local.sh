#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
PATH="$ROOT_DIR/../../.TinyTeX/bin/universal-darwin:$PATH"
export PATH

cd "$ROOT_DIR"
latexmk -lualatex -interaction=nonstopmode -halt-on-error main.tex
