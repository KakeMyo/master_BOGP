# proto_alpha 制御履歴解析と BO 制御器調整案

- 作成日: 2026-05-29
- 対象: `ver_alpha_20260528_205110`
- 位置づけ: proto_alpha レポートの「次に行うべきこと」4番と5番の作業メモ

## 1. 実行したこと

proto_alpha レポートの 4 番である「BO 制御履歴 `p_c,p_m,k` と HV/Diversity の関係を問題ごとに詳しく見る」を実行した。

解析では、BO が 1 回出力した制御区間を 1 行として扱った。例えば、世代 `g=2` から `g=5` まで `k=3` として `p_c,p_m` を保持した場合、その区間の

- 開始時 archive HV
- 終了時 archive HV
- 世代あたり HV 改善量
- 開始時 diversity
- 終了時 diversity
- 区間平均 diversity
- 報酬
- `p_c,p_m,k`

を対応づけて集計した。

出力先は次である。

```text
outputs/symbolic_regression_alpha/proto_alpha_control_analysis/ver_alpha_20260528_205110
```

主な出力は次である。

- `control_interval_analysis_all.csv`
- `control_interval_summary_by_problem_k.csv`
- `problem_k_comparison.png`
- `proto_alpha_control_analysis_summary.md`
- `sr_alpha_friedman/control_metric_timeline_seed_*.png`
- `sr_alpha_friedman/hv_diversity_k_alignment_seed_*.png`
- `sr_alpha_friedman/control_interval_outcomes_by_k.png`
- `sr_alpha_poly10/control_metric_timeline_seed_*.png`
- `sr_alpha_poly10/hv_diversity_k_alignment_seed_*.png`
- `sr_alpha_poly10/control_interval_outcomes_by_k.png`

`hv_diversity_k_alignment_seed_*.png` は、上段から archive HV、population diversity、更新周期 `k` を同じ generation 軸で並べた図である。縦の点線は BO の更新位置を表し、下段の太線はその区間で選ばれた `k` を表す。この図を見ることで、「どの `k` が選ばれている間に HV が伸びたか」「どの `k` の区間で diversity が落ちたか、あるいは回復したか」を直接確認できる。

## 2. Friedman-I の制御履歴から分かること

Friedman-I の `k` ごとの平均結果は次であった。

| k | count | mean hv_rate | mean delta_hv | mean delta_diversity | mean reward |
|---:|---:|---:|---:|---:|---:|
| 1 | 11 | 0.019844 | 0.019844 | -0.043511 | 0.227139 |
| 3 | 13 | 0.010715 | 0.032146 | -0.068649 | 0.297105 |
| 5 | 8 | 0.011347 | 0.056735 | 0.078928 | 0.401870 |

`k=1` は世代あたり HV 改善量が最も大きかった。これは、短い周期で制御を更新した方が、改善が出る局面に素早く追従できる可能性を示している。

一方で、`k=5` は区間全体の HV 改善量が大きく、平均 diversity 変化も正であった。これは、ある程度長い区間で操作率を保持することで、集団が安定して探索し、diversity を回復または維持する局面があることを示している。

この結果は、`k` を単なる計算効率化変数ではなく、探索状態に応じて制御周期を切り替える入力として扱う方針と整合する。

ただし、現行 controller の warm-up は `k=1,1,3,3,5,5` のように、各 `k` を順番に埋める挙動を持つ。そのため、`k` の効果と「どの世代でその `k` が試されたか」が混ざっている。Friedman-I の結果は有望だが、`k=5` が良いのか、あるいは中盤以降に試されたから良く見えたのかを切り分ける必要がある。

## 3. Poly-10 の制御履歴から分かること

Poly-10 の `k` ごとの平均結果は次であった。

| k | count | mean hv_rate | mean delta_hv | mean delta_diversity | mean reward |
|---:|---:|---:|---:|---:|---:|
| 1 | 12 | 0.000807 | 0.000807 | -0.026572 | 0.006493 |
| 3 | 6 | 0.000000 | 0.000000 | -0.118766 | 0.169490 |
| 5 | 12 | 0.000042 | 0.000212 | -0.005396 | 0.067383 |

Poly-10 では、どの `k` でも HV 改善量が非常に小さかった。これは proto_alpha レポートで述べた通り、現行設定では HV が初期から高く、改善余地が小さいためである。

一方で、`k=3` の報酬が比較的高い場面があった。これは HV 改善ではなく diversity 項によって報酬が支えられている可能性がある。つまり、Poly-10 では報酬が「性能改善」ではなく「多様性目標への近さ」に偏っている局面がある。

このことから、Poly-10 の現行設定は BO 制御器の良し悪しを評価するには弱い。BO 調整より先に、問題難易度と HV 正規化を見直す必要がある。

## 4. 現行 BO 制御器の懸念

### 4.1 warm-up が時系列的に偏る

現行の `ContextualBayesianRateController` は、各 `k` に最低観測数を配る balanced warm-up を持つ。ただし、実際の順序はほぼ次のようになる。

```text
k=1, k=1, k=3, k=3, k=5, k=5, ...
```

このため、各 `k` は同じ進化段階で比較されていない。特に `k=5` は初期ではなく少し世代が進んだ後に試されやすい。状態依存制御を主張するには、`k` の性能差と世代進行の影響を分ける必要がある。

### 4.2 warm-up の評価予算が `k` によって異なる

各 `k` に同じ観測数を配ると、実際に消費する GP 世代数は異なる。

```text
k=1 を2回試す: 2世代
k=5 を2回試す: 10世代
```

したがって、同じ観測数 balanced warm-up は、同じ評価予算 balanced warm-up ではない。本実験では、観測数で揃えるのか、消費世代数で揃えるのかを決める必要がある。

### 4.3 EI 比較の基準が `k` ごとに分かれている

現行実装では `k` ごとに surrogate を持つ。これは離散 `k` を扱う上では分かりやすい。一方で、EI の改善基準が各 `k` の観測履歴内の best reward になっている。

そのため、`k=1` の EI と `k=5` の EI を比較するとき、完全に同じ基準で比較しているとは限らない。`k` を同時制御対象として主張するなら、EI を `k` 間でどう比較するかを明確にする必要がある。

## 5. BO 制御器の調整・比較案

### 案 A: current controller を基準線として残す

まず現行 controller は必ず baseline として残す。

```text
BO-current:
  warm-up: k ごと sequential balanced
  EI: k ごとの surrogate と k ごとの best reward を基準
```

これを残すことで、次の調整が本当に改善になっているかを比較できる。

### 案 B: interleaved warm-up

各 `k` の warm-up を順番に埋めるのではなく、進化初期から `k=1,3,5` を混ぜて試す。

例:

```text
k=1, k=3, k=5, k=1, k=3, k=5
```

または seed ごとに順序をランダム化する。

利点は、各 `k` を似た進化段階で観測できることである。`k` の効果と世代進行の影響を分けやすくなる。

### 案 C: generation-budget balanced warm-up

観測数ではなく、消費世代数がなるべく近くなるように warm-up を設計する。

例えば、総 warm-up 予算を 12 世代とするなら、

```text
k=1 を4回: 4世代
k=3 を1回または2回: 3--6世代
k=5 を1回: 5世代
```

のようにする。

利点は、`k=5` だけが warm-up で多くの世代を消費してしまう問題を抑えられることである。一方で、各 `k` の観測数が不均等になるため、surrogate の学習データ数には偏りが出る。

### 案 D: global-best EI

surrogate は `k` ごとに分けたまま、EI の改善基準だけを全 `k` 共通にする。

現行:

```text
EI_k は k ごとの best reward を基準にする
```

変更案:

```text
EI_k は全観測の best reward を基準にする
```

利点は、`k=1,3,5` の EI を同じ基準で比較しやすくなることである。提案法の「`p_c,p_m,k` を 1 つの行動として同時に選ぶ」という主張とも相性がよい。

### 案 E: fixed-k ablation

`k` を BO の出力に含める意味を確認するため、次の比較を追加する。

```text
BO-fixed-k1:
  BO は p_c,p_m のみ制御し、k=1 固定

BO-fixed-k3:
  BO は p_c,p_m のみ制御し、k=3 固定

BO-fixed-k5:
  BO は p_c,p_m のみ制御し、k=5 固定

BO-dynamic-k:
  BO が p_c,p_m,k を同時制御
```

これにより、性能差が `p_c,p_m` の動的制御によるものなのか、`k` を動的に変えたことによるものなのかを切り分けられる。

## 6. 次に実装するなら

次に実装するなら、まずは最小構成で次の 4 条件を比較するのがよい。

| 条件名 | warm-up | EI 比較 | 目的 |
|---|---|---|---|
| `bo_current` | sequential balanced | k-local best | 現行基準 |
| `bo_interleaved_warmup` | interleaved balanced | k-local best | warm-up 順序の影響を見る |
| `bo_global_best_ei` | sequential balanced | global best | EI 比較基準の影響を見る |
| `bo_interleaved_global_ei` | interleaved balanced | global best | 推奨候補 |

この 4 条件を Friedman-I で先に確認する。Poly-10 は HV 飽和が強いため、BO 制御器比較の主対象にはまだしない方がよい。

その後、`k` の意義を強く主張する段階で fixed-k ablation を追加する。

## 7. 現時点の推奨方針

現時点では、次の方針が最もよい。

1. Friedman-I を主対象として、`bo_current` と `bo_interleaved_global_ei` を比較する。
2. 改善が見えたら、`bo_interleaved_warmup` と `bo_global_best_ei` を追加し、どちらの変更が効いたか切り分ける。
3. その後、`BO-fixed-k1/3/5` を追加し、`k` を動的制御対象にする意義を検証する。
4. Poly-10 は BO 制御器比較ではなく、先に問題難易度と HV 正規化を調整する。

この順に進めると、実験数を増やしすぎずに、提案手法の中核である「状態依存に操作強度と更新周期を切り替える」という主張を強くしやすい。
