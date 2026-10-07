# 指導教員共有用レジュメの図表

作成日: 2026-10-07。元実験の実行日: 2026-10-01。

## コンパイル

ソース一式のZIPは、`notes/`の相対配置を保持している。展開したディレクトリを作業ディレクトリにし、LuaLaTeXで次を2回実行する。

```bash
lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/supervisor_experiment_comparison_resume_20261007.tex
```

日本語クラス`ltjsarticle`、`luatexja`、`amsmath`、`amssymb`、`booktabs`、`geometry`、`graphicx`、`hyperref`、`url`を使用する。リポジトリ内では`.TinyTeX/bin/universal-darwin/lualatex`を使える。

本文の図は日本語ラベルを含む高解像度PNGを参照する。グラフ内の日本語OpenTypeフォントについて閲覧ソフトによる埋め込み警告を避けるため、本文にはPNGを埋め込む。

## 元データと再生成

- 3問題: `outputs/thesis_three_problem_pilot/seminar_conditions_seed3_20261001/`
- 状態入力比較: `outputs/seminar_context_ablation/20261001/`
- 再生成: `.venv/bin/python scripts/build_supervisor_experiment_resume.py`
- 照合記録: `source_validation.json`

ソースZIPにはコンパイル用の本文・図・生成済み表・照合記録を含める。元実験の全記録や参考文献PDFは含めない。図表の再生成には元リポジトリの実験記録が必要である。

標準偏差は実行間の`ddof=0`。3問題は各手法3回、状態入力比較は各条件100回である。画像の破線は18世代。帯は標準偏差で、信頼区間ではない。個別問題のHVやNRMSEの比較・選定上の制約は本文に記載した。
