"""Compile a BOGP LaTeX handout and render pages for visual inspection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]


def command(args):
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(f"Command failed: {args[0]}\n{completed.stdout[-3000:]}\n{completed.stderr[-1500:]}")
    return completed.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tex", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("notes"))
    parser.add_argument("--preview-dir", type=Path)
    parser.add_argument("--max-pages", type=int, default=8)
    args = parser.parse_args()
    tex = (ROOT / args.tex).resolve()
    tex.relative_to(ROOT)
    if not tex.is_file() or tex.suffix != ".tex":
        raise ValueError("Specify an existing .tex file in this repository.")
    if args.max_pages < 1:
        raise ValueError("--max-pages must be positive.")
    output = (ROOT / args.output_dir).resolve()
    output.relative_to(ROOT)
    preview = (ROOT / (args.preview_dir or Path("tmp/pdfs") / tex.stem)).resolve()
    preview.relative_to(ROOT)
    bundled_tex = ROOT / ".TinyTeX/bin/universal-darwin/lualatex"
    latex = str(bundled_tex) if bundled_tex.is_file() else shutil.which("lualatex")
    pdfinfo, renderer = shutil.which("pdfinfo"), shutil.which("pdftoppm")
    missing = [name for name, value in (("lualatex", latex), ("pdfinfo", pdfinfo), ("pdftoppm", renderer)) if not value]
    if missing:
        raise RuntimeError("Required tools unavailable: " + ", ".join(missing))
    output.mkdir(parents=True, exist_ok=True)
    preview.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        command([latex, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={output}", str(tex)])
    pdf = output / f"{tex.stem}.pdf"
    log = output / f"{tex.stem}.log"
    log_text = log.read_text(encoding="utf-8", errors="replace")
    warning_pattern = r"^(?:LaTeX|Package \S+|Class \S+) Warning:|^(?:Overfull|Underfull) \\[hv]box|^!"
    warnings = [line for line in log_text.splitlines() if re.search(warning_pattern, line)]
    blocking = [line for line in warnings if re.search(r"undefined|Overfull|Rerun|^!", line, re.I)]
    if "Rerun to get" in log_text and not any("Rerun" in line for line in blocking):
        blocking.append("LaTeX requested another run to resolve references or outlines.")
    page_match = re.search(r"^Pages:\s+(\d+)", command([pdfinfo, str(pdf)]), re.M)
    if not page_match:
        raise RuntimeError("Could not read PDF page count.")
    pages = int(page_match.group(1))
    command([renderer, "-r", "110", "-png", str(pdf), str(preview / "page")])
    # Only the current build's page count is listed if older previews remain.
    images = []
    for n in range(1, pages + 1):
        image = preview / f"page-{n:0{len(str(pages))}d}.png"
        if not image.is_file():
            raise RuntimeError(f"Rendered page missing: {image}")
        images.append(str(image))
    report = {"pdf": str(pdf), "pages": pages, "max_pages": args.max_pages,
              "latex_warnings": warnings, "blocking_issues": blocking, "rendered_pages": images,
              "visual_review_required": True}
    (preview / "build_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if blocking or pages > args.max_pages:
        raise RuntimeError("Review unresolved LaTeX issues or the exceeded page limit in build_check.json.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
