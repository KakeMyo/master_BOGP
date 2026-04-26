from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.journal import append_operation_log


class JournalTests(unittest.TestCase):
    def test_append_operation_log_creates_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            note_path = Path(directory) / "research_note.md"
            note_path.write_text("# Test Note\n\n## 作業ログ\n", encoding="utf-8")
            append_operation_log(
                note_path=note_path,
                title="テスト",
                summary="ログを書き込んだ",
                rationale="追記処理を確認するため",
                details=["detail"],
                validation=["validation"],
                next_actions=["next"],
            )
            content = note_path.read_text(encoding="utf-8")

        self.assertIn("###", content)
        self.assertIn("ログを書き込んだ", content)
        self.assertIn("追記処理を確認するため", content)


if __name__ == "__main__":
    unittest.main()
