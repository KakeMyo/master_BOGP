# ver_beta 4 条件 seed 100 比較まとめ

- 作成日: 2026-06-01
- 対象: `bo_current`, `ver_beta_k`, `ver_beta_EI`, `ver_beta_kEI`
- seed: 0 から 99 の 100 本
- 問題: `sr_alpha_friedman`, `sr_alpha_poly10`
- population size: 24
- total generations: 30
- evaluations / run: 720
- archive key: `topology_value`
- 図出力: 今回は 100 seed の全線重ね図が読みにくいため `--skip-plots` で CSV 集計を優先

## 1. 比較条件

| method | warm-up | EI best |
|---|---|---|
| `bo_current` | sequential | per-k |
| `ver_beta_k` | interleaved | per-k |
| `ver_beta_EI` | sequential | global |
| `ver_beta_kEI` | interleaved | global |

## 2. 出力先

```text
outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_seed100_20260601_004320
outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_seed100_20260601_005758
```

## 3. Friedman-I の結果

| method | final archive HV mean | final archive HV std | final diversity mean | final diversity std | archive size mean | archive size std |
|---|---:|---:|---:|---:|---:|---:|
| `bo_current` | 0.773081 | 0.055720 | 0.603050 | 0.123937 | 15.72 | 10.85 |
| `ver_beta_k` | 0.774463 | 0.046293 | 0.603639 | 0.119035 | 15.59 | 11.81 |
| `ver_beta_EI` | 0.774922 | 0.050454 | 0.606697 | 0.122603 | 16.16 | 11.10 |
| `ver_beta_kEI` | 0.771281 | 0.066523 | 0.600508 | 0.139885 | 14.90 | 11.15 |

Friedman-I では、平均 final archive HV は `ver_beta_EI` が最も高かった。ただし `bo_current` との差は約 `0.00184` であり、絶対値としては小さい。

一方で、`ver_beta_kEI` は平均 HV が最も低く、標準偏差も最も大きい。したがって、100 seed に増やしても、`k` の warm-up 改善と global EI を単純に同時導入する案は、Friedman-I では安定改善とは言いにくい。

## 4. Poly-10 の結果

| method | final archive HV mean | final archive HV std | final diversity mean | final diversity std | archive size mean | archive size std |
|---|---:|---:|---:|---:|---:|---:|
| `bo_current` | 0.809864 | 0.015390 | 0.540157 | 0.171922 | 8.37 | 15.17 |
| `ver_beta_k` | 0.810086 | 0.015479 | 0.564073 | 0.185181 | 8.97 | 19.07 |
| `ver_beta_EI` | 0.810057 | 0.015132 | 0.549069 | 0.168610 | 8.87 | 17.59 |
| `ver_beta_kEI` | 0.811320 | 0.016155 | 0.558273 | 0.174853 | 10.58 | 24.36 |

Poly-10 では、平均 final archive HV は `ver_beta_kEI` が最も高かった。ただし `bo_current` との差は約 `0.00146` であり、標準偏差約 `0.016` に比べるとかなり小さい。

平均 diversity は `ver_beta_k` が最も高く、`ver_beta_kEI` も `bo_current` より高い。しかし、Poly-10 は archive size の標準偏差が大きく、seed による外れ値の影響を受けやすい。

## 5. bo_current との差分

同じ seed 内で `bo_current` と各手法を比較した差分も確認した。ここでは final archive HV の差を `method - bo_current` とした。

### 5.1 Friedman-I

| method | HV diff mean | HV diff std | median diff | win count / 100 |
|---|---:|---:|---:|---:|
| `ver_beta_k` | 0.001382 | 0.055148 | 0.000046 | 50 |
| `ver_beta_EI` | 0.001841 | 0.012167 | 0.000000 | 36 |
| `ver_beta_kEI` | -0.001800 | 0.047438 | 0.000831 | 52 |

`ver_beta_EI` は平均差が最も大きく、差分の標準偏差も最も小さい。ただし win count は 36/100 であり、多くの seed で少しずつ勝つというより、一部 seed の改善で平均が押し上がっている可能性がある。

`ver_beta_kEI` は win count だけ見ると 52/100 で半数を超えるが、平均差は負である。これは、小さく勝つ seed はある一方で、大きく負ける seed が存在することを意味する。実際、Friedman-I では `ver_beta_kEI` の標準偏差が最も大きい。

### 5.2 Poly-10

| method | HV diff mean | HV diff std | median diff | win count / 100 |
|---|---:|---:|---:|---:|
| `ver_beta_k` | 0.000222 | 0.015163 | 0.000000 | 48 |
| `ver_beta_EI` | 0.000193 | 0.004025 | 0.000000 | 19 |
| `ver_beta_kEI` | 0.001456 | 0.016811 | 0.000001 | 54 |

Poly-10 では `ver_beta_kEI` が平均差と win count の両方で最も良い。ただし median diff はほぼ 0 であり、全体的には「多くの seed で大きく改善する」というより、一部 seed の改善が平均を押し上げている可能性がある。

## 6. 100 seed で分かったこと

1. 50 seed で見えた大枠は、100 seed でもほぼ維持された。
2. Friedman-I では `ver_beta_EI` が平均 HV で最良であり、`ver_beta_kEI` は最も不安定である。
3. Poly-10 では `ver_beta_kEI` が平均 HV で最良だが、差は標準偏差に比べて小さく、強い優位とは言いにくい。
4. `ver_beta_kEI` は問題によって良し悪しが分かれ、Friedman-I では不安定化、Poly-10 ではわずかな改善という挙動になった。
5. `ver_beta_EI` は Friedman-I で比較的安定しており、次に詳しく調べる候補として有望である。

## 7. 考察

`ver_beta_kEI` が Friedman-I で悪くなりやすい理由として、`k` の interleaved warm-up と global EI が同時に入ることで、BO が探索周期間の比較を強くしすぎる可能性がある。`k=1,3,5` は同じ報酬関数で評価しているが、実際には観測ノイズ、更新頻度、区間内で起こる多様性変化が異なる。

global EI は全 `k` 共通の最高報酬を基準にするため、ある `k` で偶然高い報酬が出ると、別の `k` の候補は改善余地が小さく見えやすい。また interleaved warm-up は `k` の初期順序を公平にする一方、各 `k` の観測数が少ない段階では surrogate の不確実性が残る。この二つが同時に働くと、探索が広がる反面、HV を安定して押し上げる選択に集中しにくくなる可能性がある。

一方で Poly-10 では `ver_beta_kEI` が平均 HV で最も高かった。これは、Poly-10 が初期から HV が高くなりやすく、細かな改善や外れ値 seed の影響を受けやすいためと考えられる。したがって、Poly-10 の結果だけで `ver_beta_kEI` を本採用するのは危険である。

現時点では、次の方針が妥当である。

1. Friedman-I を主判断材料にするなら、`ver_beta_EI` を次候補として詳しく調べる。
2. `ver_beta_kEI` は「同時改善が必ずしも良くない」ことを示す ablation として残す。
3. 次は paired difference の可視化と統計検定を行い、平均差が偶然でないか確認する。
4. `k` の扱いについては、global EI ではなく、`k` 別標準化 EI や報酬分布の正規化を検討する。
