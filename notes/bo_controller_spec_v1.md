# BO 制御器詳細設計仕様 V1

- 作成日: 2026-04-28
- 位置づけ: 提案法のうち、外側制御器として用いる文脈付き Bayesian Optimization (BO) の詳細仕様を独立に固定する
- 関連仕様: [proposed_method_spec_v1.md](/Users/kakemyo/Downloads/master_BOGP/notes/proposed_method_spec_v1.md)
- 参照文献: [R12], [R13], [R14]

## 1. 一文定義

本研究の BO 制御器は、更新時点の GP 状態 `x_ell` を観測し、各更新周期 `k` に条件づけた GP surrogate 上で Expected Improvement (EI) を比較することで、次区間の行動 `u_ell = (p_c,p_m,k)` を決定する文脈付き BO 制御器である。

ここで重要なのは、BO が単に操作率 `(p_c,p_m)` のよい固定値を探すのではなく、現在状態 `x_ell` のもとで、操作強度 `(p_c,p_m)` と更新周期 `k` を同時に選ぶ点である。この問題設定は、各ラウンドで文脈を観測してから行動を選ぶ文脈付き GP bandit / contextual BO の考え方に対応する [R12]。

## 2. 入出力と学習データ

制御ステップを `ell` とする。BO 制御器への入力は、更新時点 `g_ell` で観測された状態ベクトル

```text
x_ell = [
  tau_ell,
  HV_tilde_ell,
  DeltaHV_tilde_ell,
  D_ell,
  L_tilde_ell,
  s_tilde_ell
]^T
```

である。BO 制御器の出力は

```text
u_ell = (p_{c,ell}, p_{m,ell}, k_ell)
```

であり、GP プラントはこのうち `p_c` と `p_m` を `k_ell` 世代の間保持して進化する。区間終了後、報酬 `r_ell` が観測される。

BO 全体の履歴データは

```text
D = {(x_i, p_{c,i}, p_{m,i}, k_i, r_i)}_{i=1}^n
```

である。V1 では `k` を離散候補として扱うため、実際の surrogate 学習では `k` ごとの部分データ

```text
D_k = {
  (x_i, p_{c,i}, p_{m,i}, r_i)
  | k_i = k
}
```

を用いる。

## 3. `k` の扱い

更新周期 `k` は連続変数ではなく、有限離散集合

```text
K = {k^(1), k^(2), ..., k^(M)}
```

から選ぶ。更新時点 `g_ell` で残り世代数が `T - g_ell` のとき、有効な候補集合は

```text
K(x_ell) = {k in K | k <= T - g_ell}
```

とする。

`k` を通常の実数値特徴量として 1 本の GP に入れる方法も考えられるが、GP は基本的に実数値入力を仮定するため、整数・カテゴリ変数を単純に丸めたり符号化したりすると不適切なモデル化になる可能性がある [R14]。そこで V1 では、`k` を数値特徴として直接 surrogate に押し込まず、各 `k` に条件づけた BO として扱う。

この設計により、`k` は単なる効率化変数ではなく、状態が安定しているときは更新を粗くし、変化が大きいときは更新を密にするための制御入力として位置づけられる。

## 4. Surrogate モデル

各 `k` に対して、報酬関数を

```text
r = f_k(x, p_c, p_m) + epsilon
```

とモデル化する。ここで

```text
f_k(x,p_c,p_m) ~ GP(m_k, K_k)
```

である。

各 surrogate の入力は

```text
z_k = [x, p_c, p_m]
```

であり、`x` が 6 次元、`(p_c,p_m)` が 2 次元であるため、入力次元は合計 8 次元となる。

カーネルは初稿では次を基本形とする。

```text
K_k(z,z') =
  Constant
  * Matern_ARD(nu=2.5)
  + WhiteNoise
```

報酬 `r` は surrogate の学習時に標準化する。これは報酬スケールが問題や実験条件により変動しうるためである。

V1 では `k` ごとに独立した surrogate を持つ。これにより、`k` によって報酬分布やノイズ特性が異なる場合でも、単一モデルに無理に押し込まずに扱える。ただし、各 `k` の観測数が少ない場合には学習が不安定になるため、warm-up と疎データ時の扱いを明示する。

## 5. 獲得関数

獲得関数は Expected Improvement (EI) に固定する。EI は高コストな black-box 関数最適化において、surrogate の予測平均と不確実性を用いて次の評価点を選ぶ代表的な基準であり、EGO の中核的な考え方として整理されている [R13]。

各 `k` に対して、現在状態 `x_ell` を固定し、候補 `(p_c,p_m)` の EI を計算する。

```text
EI_k(x_ell,p_c,p_m | D_k)
```

最終的な制御則は

```text
u_ell^*
= argmax_{k in K(x_ell)}
    max_{(p_c,p_m) in U_k(x_ell)}
    EI_k(x_ell,p_c,p_m | D_k)
```

である。

`k` による制御コストは、報酬 `r_ell` の中に `C_k(k_ell)` として含める。したがって、V1 では cost-aware acquisition には広げず、獲得関数自体は EI のままにする。これにより、BO の設計を単純に保ち、報酬設計と獲得関数の役割を分離できる。

## 6. 候補生成と行動選択

各更新時点では、次の手順で行動を選択する。

1. 現在状態 `x_ell` を観測する。
2. 有効な `K(x_ell)` を作る。
3. 各 `k in K(x_ell)` について、feasible な `(p_c,p_m)` 候補を Sobol または LHS で生成する。
4. 各候補について `EI_k(x_ell,p_c,p_m)` を評価する。
5. 全 `k` と全候補の中で EI が最大となる `(p_c,p_m,k)` を選ぶ。

V1 では勾配法による内側最適化は用いない。理由は、feasible 領域に `p_c + p_m <= 1` の制約があり、さらに `k` が離散であるため、候補点列挙の方が実装と説明の両面で扱いやすいからである。

## 7. 制約

行動空間は次で定義する。

```text
U_k(x_ell) = {
  (p_c,p_m)
  | p_c in [p_c^min, p_c^max],
    p_m in [p_m^min, p_m^max],
    p_c + p_m <= 1,
    |p_c - p_c^prev| <= Delta_c,
    |p_m - p_m^prev| <= Delta_m
}
```

ただし、前回制御が存在しない warm-up 初回では変化量制約は適用しない。

更新周期の制約は

```text
k in K(x_ell) = {k in K | k <= T - g_ell}
```

とする。残り世代数を超える `k` は候補から除外し、後から切り詰めない。これは、BO が評価した行動と実際に適用される行動がずれることを避けるためである。

## 8. Warm-up

`k` ごとに surrogate を持つため、warm-up は各 `k` に最低限の観測を配る balanced warm-up とする。

```text
for k in K:
  generate n0 feasible (p_c,p_m) design points
```

warm-up 期間中は EI による最適化を行わず、事前に生成した設計点を順に使う。設計点は Sobol または LHS で生成し、`p_c + p_m <= 1` を満たす候補のみを採用する。

warm-up 完了条件は

```text
|D_k| >= n0  for all k in K_active
```

である。ここで `K_active` は、実験開始時点で有効な候補集合である。

## 9. 疎データ時と fallback

ある `k` の観測数が

```text
|D_k| < n_min
```

である場合、その `k` はまだ十分に評価されていないとみなす。V1 では、このような `k` を探索優先候補として扱い、EI の比較に入る前に不足分の設計点を優先的に実行する。

fully BO mode に入った後でも、特定の `k` のモデル学習が失敗した場合は、その `k` については次の順で fallback する。

1. その `k` の未使用 warm-up 候補があれば使う。
2. feasible 領域から LHS / Sobol でランダム候補を生成する。
3. それでも候補が得られない場合は、その `k` を今回の選択から除外する。

全 `k` で surrogate 評価が失敗した場合は、feasible な全候補からランダムに 1 点を選ぶ。この場合も、選択した `(x_ell,u_ell,r_ell)` は履歴に追加し、次回以降の学習に用いる。

## 10. 非文脈 BO baseline との対応

非文脈 BO baseline でも、`k` の扱い、warm-up、候補生成、制約は提案法と同じにする。差分は、surrogate の入力に `x_ell` を含めるかどうかだけに限定する。

提案法:

```text
r = f_k(x_ell,p_c,p_m) + epsilon
```

非文脈 BO:

```text
r = h_k(p_c,p_m) + epsilon
```

このように比較設計を揃えることで、性能差を「BO を使ったかどうか」ではなく、「現在状態を条件に含めたかどうか」に帰着できる。

## 11. 実装へ渡すインターフェース前提

今回の V1 は文書仕様であり、コード実装は次段階に回す。ただし、次の実装で迷わないよう、必要な型と設定項目を先に固定する。

`ControlInput` は将来的に次を持つ。

```text
ControlInput:
  crossover_rate: float
  mutation_rate: float
  update_period: int
```

BO 設定は少なくとも次を持つ。

```text
BOControllerConfig:
  candidate_k_values
  warmup_per_k
  min_observations_per_k
  candidate_pool_size_per_k
  kernel_family
  exploration_jitter
  rate_step_limit
  random_seed
```

閉ループ実行側は、固定 `control_interval` ではなく、controller が返す `update_period` を用いて GP を進める。

## 12. 採用しない選択肢と理由

### 単一 surrogate に `k` を数値入力として入れる案

V1 では採用しない。`k` は整数・離散変数であり、単純な実数値入力として扱うと GP の距離構造が実際の制御意味とずれる可能性があるためである [R14]。

### 先に `k` を決めてから `(p_c,p_m)` を最適化する階層型

V1 では採用しない。提案法の主張は、操作強度と更新周期を同時に切り替える点にあるため、`(p_c,p_m,k)` は 1 つの行動として扱う。

### UCB / Thompson Sampling / Safe BO

V1 では採用しない。文脈付き BO の理論的文脈では UCB 系も自然だが [R12]、本研究の初稿では EGO/EI の説明しやすさと既存実装との整合を優先して EI に固定する [R13]。

### Cost-aware acquisition

V1 では採用しない。更新コストは報酬関数の `C_k(k_ell)` に含めるため、獲得関数側でさらにコスト補正を入れると、報酬設計と獲得関数設計の役割が重複するためである。

## 13. 文献との対応

| 設計判断 | 根拠文献 | 使い方 |
|---|---|---|
| 文脈 `x_ell` を観測して行動を選ぶ | [R12] | 文脈付き BO としての問題設定 |
| 文脈と行動の結合空間を surrogate にする | [R12] | `z=[x,u]` の設計根拠 |
| 獲得関数に EI を使う | [R13] | EGO / EI の古典的根拠 |
| `k` を単純な連続入力にしない | [R14] | 離散・整数変数を GP で扱う際の注意 |
| `k` を列挙し条件付き surrogate を持つ | [R14] | V1 での実装容易な回避策 |

## 14. V1 で固定すること

- BO 制御器は文脈付き BO とする。
- 行動は `(p_c,p_m,k)` とする。
- `k` は離散列挙し、各 `k` に条件づけた surrogate を使う。
- surrogate は GP 回帰器とし、カーネルは `Matern(nu=2.5)` + `WhiteNoise` + `Constant` を基本形にする。
- 獲得関数は EI に固定する。
- warm-up は `k` ごとの balanced warm-up とする。
- 非文脈 BO baseline との差分は、`x_ell` を入力に含めるかどうかに限定する。

## 15. V1 では固定しないこと

- `K` の具体値
- `n0` と `n_min` の具体値
- `w_p`, `w_d`, `w_c` の具体値
- カーネル比較
- UCB / TS / entropy search との比較
- 離散変数専用カーネルの実装
- Safe BO や制約付き BO への拡張

これらは、BO 制御器 V1 の成立性を確認した後、実験または文献調査に基づいて次段階で扱う。
