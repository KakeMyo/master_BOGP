# Bayesian Optimization Controlled GP

遺伝的プログラミングにおける交叉率・突然変異率を、ベイズ最適化で動的に制御する研究用ワークスペースです。

## 構成

- `notes/research_note.md`: 研究背景、目的、閉ループ設計、実験計画、作業ログ
- `src/bogp/`: 制御器、目的関数、実験ループ、研究補助コード
- `scripts/smoke_test.py`: 動的制御の簡易スモークテスト
- `scripts/log_note.py`: 研究ノートに作業ログを追記する補助スクリプト
- `tests/`: 依存の薄い単体テスト

## セットアップ

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python scripts/smoke_test.py
```

## 次にやること

1. `notes/research_note.md` に沿って、実際の GP 実装に接続する。
2. `src/bogp/toy_engine.py` の代わりに、DEAP などの実 GP エンジンを接続する。
3. 固定率、時変スケジュール、文脈なし BO、提案法を比較する。

