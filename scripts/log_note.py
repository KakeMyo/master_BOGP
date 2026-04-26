from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.journal import append_operation_log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append an operation log entry to the research note.")
    parser.add_argument("title", help="Log entry title")
    parser.add_argument("--summary", required=True, help="What was done")
    parser.add_argument("--reason", required=True, help="Why it was done")
    parser.add_argument("--detail", action="append", default=[], help="Detail line")
    parser.add_argument("--validation", action="append", default=[], help="Validation line")
    parser.add_argument("--next", dest="next_actions", action="append", default=[], help="Next action line")
    parser.add_argument(
        "--note-path",
        default=str(ROOT / "notes" / "research_note.md"),
        help="Path to the markdown note",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    append_operation_log(
        note_path=Path(args.note_path),
        title=args.title,
        summary=args.summary,
        rationale=args.reason,
        details=args.detail,
        validation=args.validation,
        next_actions=args.next_actions,
    )
    print("Appended log entry to {0}".format(args.note_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

