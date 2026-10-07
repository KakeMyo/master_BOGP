# ver_beta 4 条件 seed 50 比較まとめ

- 作成日: 2026-05-29
- 対象: `bo_current`, `ver_beta_k`, `ver_beta_EI`, `ver_beta_kEI`
- seed: 0 から 49 の 50 本
- 問題: `sr_alpha_friedman`, `sr_alpha_poly10`
- population size: 24
- total generations: 30
- evaluations / run: 720
- archive key: `topology_value`

## 1. 比較条件

| method | warm-up | EI best |
|---|---|---|
| `bo_current` | sequential | per-k |
| `ver_beta_k` | interleaved | per-k |
| `ver_beta_EI` | sequential | global |
| `ver_beta_kEI` | interleaved | global |

## 2. 出力先

Friedman-I は最初の 50 seed 実行で完了した。

```text
outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_seed50_20260529_154012
```

Poly-10 は最初の実行で個体木の deepcopy 中に再帰上限へ到達したため、実験実行時の Python 再帰上限を上げたうえで Poly-10 のみ再実行した。アルゴリズムや GP 操作は変更していない。

```text
outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_seed50_20260529_155025
```

## 3. Friedman-I の結果

| method | final archive HV mean | final archive HV std | final diversity mean | final diversity std | archive size mean | archive size std |
|---|---:|---:|---:|---:|---:|---:|
| `bo_current` | 0.776702 | 0.056612 | 0.616345 | 0.119777 | 14.36 | 9.03 |
| `ver_beta_k` | 0.769842 | 0.056652 | 0.605506 | 0.126564 | 14.80 | 10.43 |
| `ver_beta_EI` | 0.779312 | 0.047184 | 0.618944 | 0.118501 | 14.12 | 8.86 |
| `ver_beta_kEI` | 0.761945 | 0.077493 | 0.593911 | 0.151447 | 14.42 | 11.10 |

Friedman-I では、平均 final archive HV は `ver_beta_EI` が最も高かった。また標準偏差も 4 条件の中で最も小さく、今回の 50 seed 条件では `global EI` 単独が比較的安定している。

一方、`ver_beta_k` は 3 seed 実験では有望に見えたが、50 seed では `bo_current` より平均 HV が低くなった。したがって、3 seed 時点の `ver_beta_k` 優位は seed 依存の可能性が高い。

`ver_beta_kEI` は平均 HV が最も低く、標準偏差も最も大きかった。これは、warm-up の interleaved 化と global EI を同時に入れると、探索方針が不安定になる可能性を示している。

## 4. Poly-10 の結果

| method | final archive HV mean | final archive HV std | final diversity mean | final diversity std | archive size mean | archive size std |
|---|---:|---:|---:|---:|---:|---:|
| `bo_current` | 0.807258 | 0.013684 | 0.542788 | 0.189975 | 10.26 | 17.53 |
| `ver_beta_k` | 0.808129 | 0.013714 | 0.542272 | 0.205808 | 12.20 | 26.37 |
| `ver_beta_EI` | 0.807570 | 0.013730 | 0.545946 | 0.179187 | 9.32 | 17.06 |
| `ver_beta_kEI` | 0.808818 | 0.014069 | 0.549244 | 0.189135 | 15.84 | 33.49 |

Poly-10 では、平均 final archive HV は `ver_beta_kEI` が最も高かった。ただし、手法間の平均差は最大でも約 0.0016 程度であり、標準偏差約 0.014 に比べるとかなり小さい。

したがって、Poly-10 の結果は「`ver_beta_kEI` が明確に良い」とまでは言えない。現時点では、Poly-10 は手法差が小さく、seed 依存や外れ値の影響も大きい問題として扱うのがよい。

## 5. 50 seed で分かったこと

1. 3 seed の結論はかなり揺れやすい。
2. Friedman-I では `ver_beta_EI` が平均 HV と安定性の両方で最も良かった。
3. Friedman-I では `ver_beta_kEI` が最も悪く、`k` と EI の改善を単純に同時導入する方針は慎重に扱う必要がある。
4. Poly-10 では `ver_beta_kEI` の平均 HV が最も高いが、差は標準偏差に比べて小さいため強い結論にはしにくい。
5. archive size は Poly-10 で特に標準偏差が大きく、特定 seed で大きな archive が発生している可能性がある。

## 6. 考察

`ver_beta_kEI` が Friedman-I で悪くなった理由として、interleaved warm-up と global EI が同時に働くことで、BO が `k` 間の比較を強くしすぎた可能性がある。`k=1,3,5` は同じ報酬スケールで扱っているが、実際には観測ノイズ、更新頻度、区間内の多様性変化が異なる。そのため global EI にすると、ある `k` の偶然高い報酬が全体基準になり、他の `k` の候補が過度に不利になることがある。

また、interleaved warm-up は `k` の初期観測順序を公平にする一方で、初期の各 `k` の観測点が少ない段階では surrogate の分散が大きくなりやすい。この状態で global EI を使うと、不確実性の大きい候補や偶然の報酬に引っ張られ、HV 改善に安定して寄与する制御入力を選びにくくなる可能性がある。

今回の seed 50 結果を踏まえると、Friedman-I では次の候補は `ver_beta_EI` を優先し、`ver_beta_k` と `ver_beta_kEI` は ablation として残すのが妥当である。ただし、平均差は標準偏差に比べて大きくないため、次は paired test や seed ごとの差分解析を行う必要がある。
