# 予備実験用データ

取得日: 2026-10-01。元の配布ファイルを `raw/` に変更せず保持する。

| データ | 公式配布元 | 配布物 | 規模 | 許諾 |
|---|---|---|---|---|
| Airfoil Self-Noise | [UCI](https://archive.ics.uci.edu/dataset/291/airfoil%2Bself%2Bnoise) | airfoil_self_noise.zip / airfoil_self_noise.dat | 1503例・5入力・1出力 | CC BY 4.0 |
| Concrete Compressive Strength | [UCI](https://archive.ics.uci.edu/dataset/165/concrete%2Bcompressive%2Bstrength) | concrete_compressive_strength.zip / Concrete_Data.xls / Concrete_Readme.txt | 1030例・8入力・1出力 | CC BY 4.0 |

引用: Brooks, T., Pope, D., & Marcolini, M. (1989), Airfoil Self-Noise,
doi:10.24432/C5VW2C。Yeh, I. (1998), Concrete Compressive Strength,
doi:10.24432/C5PK67。ライセンス: https://creativecommons.org/licenses/by/4.0/

ZIP取得URL:

- https://archive.ics.uci.edu/static/public/291/airfoil%2Bself%2Bnoise.zip
- https://archive.ics.uci.edu/static/public/165/concrete%2Bcompressive%2Bstrength.zip

UBall5Dは外部データ取得を要さず、White et al. (2013), Better GP Benchmarks,
Table 5の式・範囲・訓練1024点/テスト5000点を実装から生成する。
独立validation 1024点は本研究で追加する。

GPの乱数seed（0,1,2）と、データ生成・分割seed（20260527）を分離する。
実データは同一入力の重複を同一partitionにまとめ、unique-input groupを
60%/15%/25%へ分割する。行数比率は完全には一致しない。
X/yの標準化統計はtrainだけで推定する。rawの削除・修正は行わない。
splitの行番号、SHA-256、前処理統計、実際のpartition数は各実験の
`dataset_manifest.json` に保存する。

Excel読取には `.venv/bin/python -m pip install -e '.[dev,datasets]'` が必要。
実験結果はGit対象外の `outputs/thesis_three_problem_pilot/` に保存する。
