# Bayesian Optimization Controlled GP

遺伝的プログラミングにおける交叉率・突然変異率を、ベイズ最適化で動的に制御する研究用ワークスペースです。

## 構成

- `notes/research_note.md`: 研究背景、目的、閉ループ設計、実験計画、作業ログ
- `src/bogp/`: 制御器、汎用多目的 GP エンジン、問題アダプタ、実験ループ
- `scripts/smoke_test_v1.py`: 動的制御の簡易スモークテスト
- `scripts/run_test_v1_template_experiment.py`: 問題非依存テンプレート GP の小実験
- `scripts/run_test_v1_plain_gp_baseline_template.py`: 固定率の普通の多目的 GP ベースライン実験
- `scripts/compare_test_v1_plain_gp_vs_bogp_template.py`: 提案手法と普通の GP のテンプレート問題比較
- `scripts/run_test_v1_structural_experiment.py`: 構造探索問題アダプタの極小スモーク実験
- `scripts/run_test_v1_plain_gp_baseline_structural.py`: 構造探索問題に対する固定率 GP ベースライン実験
- `scripts/compare_test_v1_plain_gp_vs_bogp_structural.py`: 構造探索問題に対する提案手法と普通の GP の比較
- `scripts/compare_test_ver2_plain_gp_vs_bogp_template.py`: archive 重複除去を入れた test_ver2 テンプレート比較
- `scripts/compare_test_ver2_plain_gp_vs_bogp_structural.py`: archive 重複除去を入れた test_ver2 構造探索比較
- `scripts/run_test_v1_structural_similarity_experiment.py`: 構造類似度の同形部分木数依存性を調べる小実験
- `scripts/compile_proposed_method_v1.sh`: `notes/提案手法ver.1.tex` を PDF 化する補助スクリプト
- `scripts/log_note.py`: 研究ノートに作業ログを追記する補助スクリプト
- `tests/`: 依存の薄い単体テスト

## セットアップ

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python scripts/smoke_test_v1.py
.venv/bin/python scripts/run_test_v1_template_experiment.py
.venv/bin/python scripts/run_test_v1_plain_gp_baseline_template.py
.venv/bin/python scripts/compare_test_v1_plain_gp_vs_bogp_template.py
.venv/bin/python scripts/run_test_v1_plain_gp_baseline_structural.py
.venv/bin/python scripts/compare_test_v1_plain_gp_vs_bogp_structural.py
.venv/bin/python scripts/compare_test_ver2_plain_gp_vs_bogp_template.py
.venv/bin/python scripts/compare_test_ver2_plain_gp_vs_bogp_structural.py
.venv/bin/python scripts/run_test_v1_structural_similarity_experiment.py
scripts/compile_proposed_method_v1.sh
```

## 次にやること

1. `src/bogp/test_v1_template_problem.py` を基準に、別問題を `GPProblem` として追加する。
2. `src/bogp/test_v1_structural_problem.py` を拡張し、添付 MATLAB コードとの差分を検証する。
3. 固定率、時変スケジュール、文脈なし BO、提案法を比較する。
