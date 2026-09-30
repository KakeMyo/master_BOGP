# 2目的シンボリック回帰 問題設定案

- 作成日: 2026-05-27
- 位置づけ: 本実験候補問題の仕様メモ
- 注意: まだ正式な参考文献欄には反映しない

## 1. 結論

本研究の最初のシンボリック回帰問題は、次の 2 目的問題として設定するのがよい。

```text
目的1: 予測誤差を最小化する
目的2: 数式木の複雑さを最小化する
```

これは MOGP symbolic regression でよく使われる accuracy--complexity trade-off であり、提案手法の「HV 改善と多様性維持の両立」を最も説明しやすい。

## 2. 文献から見た根拠

### 2.1 benchmark 設計の注意

McDermott et al. (2012) と White et al. (2013) は、GP 研究では歴史的に使われてきた benchmark が簡単すぎたり、比較可能性を損ねたりすることがあると指摘している。

本研究では、既存の `y=x^2+x` のような小さい toy 問題は smoke test として使い、本実験では少なくとも中程度以上の symbolic regression 問題を使う。

### 2.2 SRBench / PMLB の示唆

La Cava et al. (2021) の SRBench は、多数の regression problem に対して symbolic regression 手法を比較する枠組みである。実世界データでは、低誤差かつ低複雑度のモデルを得る能力を評価している。

本研究では、この考え方を MOGP に落とし込み、誤差と木サイズを別々の目的関数として扱う。

### 2.3 MOGP symbolic regression の難しさ

Liu et al. (2022) は、NSGA-II による MOGP symbolic regression では、低複雑度モデルが初期世代で過剰に複製され、探索効率が低下することを報告している。

この現象は、本研究の文脈ベクトルである `HV`, `DeltaHV`, `Diversity`, `mean tree size`, `stagnation` と強く関係する。したがって、accuracy--complexity SR は提案法の状態依存制御が効くかを調べる問題として適している。

## 3. 目的関数

個体を数式木 `T` とする。

### 目的1: 正規化予測誤差

基本形は training set 上の NRMSE とする。

```text
f_1(T) = NRMSE_train(T)
       = RMSE_train(T) / (std(y_train) + epsilon)
```

```text
RMSE_train(T)
  = sqrt((1 / n_train) * sum_i (T(x_i) - y_i)^2)
```

実装上は、異常値や発散式が HV を壊さないように、評価値を上限で clip する。

```text
f_1_clipped(T) = clip(f_1(T), 0, E_max)
```

初期値候補:

ver_alpha では、初期個体が上限に張り付きすぎて HV が 0 にならないように、まずは次を使う。

```text
E_max = 5.0
```

### 目的2: 数式木サイズ

```text
f_2(T) = |T|
```

ここで `|T|` は、演算子ノード、変数ノード、定数ノードをすべて数えたノード数とする。

HV 用には次のように正規化する。

```text
f_2_normalized(T)
  = clip((|T| - 1) / (L_max - 1), 0, 1)
```

初期値候補:

```text
L_max = 80 または 100
```

## 4. 最終評価

探索中の目的関数は `training error` と `tree size` にする。

ただし、本実験の報告では次も必ず保存する。

```text
train NRMSE
test NRMSE
tree size
archive HV
population HV
population diversity
mean tree size
archive size
unique objective size
unique structure size
```

test set は探索には使わず、最終 Pareto archive の汎化性能確認に使う。

## 5. 関数集合と終端集合

最初の本実験では、探索空間を広げすぎないために次を基本とする。

```text
Function set:
  {+, -, *, protected_div, sin, cos}

Terminal set:
  {x_1, ..., x_d, ephemeral constants}
```

protected division は次で定義する。

```text
protected_div(a, b) =
  a / b    if |b| > epsilon
  a        otherwise
```

定数は初期生成時に `Uniform(-2, 2)` からサンプリングし、突然変異で再サンプリングできるようにする。

## 6. データ分割

SRBench では train/test split を使う実験設計が採用されている。初期実装では、過度に複雑にしないため、次を推奨する。

```text
train : test = 75 : 25
```

各 seed で分割を変える場合は、seed によるばらつきとして扱う。問題自体の難しさを固定したい場合は、dataset seed と algorithm seed を分ける。

初期実装では次を推奨する。

```text
dataset_seed: 問題ごとに固定
algorithm_seed: 実験 seed として複数反復
```

## 7. 候補問題

### SR-0: Template / Smoke Test

```text
y = x^2 + x
x in [-1, 1]
```

用途:

- 実装確認
- 図の描画確認
- BO 制御履歴の確認

本実験の主結果にはしない。

### SR-1: Friedman-I

```text
y = 10 sin(pi x_1 x_2)
    + 20 (x_3 - 0.5)^2
    + 10 x_4
    + 5 x_5
    + noise

x_j ~ Uniform(0, 1)
```

おすすめ度: 高

理由:

- よく知られた回帰 benchmark で説明しやすい。
- 線形項、二次項、三角関数、変数間相互作用を含む。
- 5 変数なので探索空間が広すぎず、初期本実験に向く。

初期設定:

```text
n_train = 200
n_test = 200
noise_sigma = 0.0 または 0.1 * std(y)
```

### SR-2: Poly-10

```text
y = x_1 x_2
    + x_3 x_4
    + x_5 x_6
    + x_1 x_7 x_9
    + x_3 x_6 x_10

x_j ~ Uniform(-1, 1)
```

おすすめ度: 高

理由:

- 10 変数の sparse interaction 問題で、必要な変数・不要な変数の探索が必要になる。
- 小さい木だけでは高精度になりにくく、accuracy と complexity の trade-off が出やすい。
- 多様性維持の重要性を確認しやすい。

初期設定:

```text
n_train = 300
n_test = 300
noise_sigma = 0.0
```

### SR-3: Pagie-like 2D nonlinear problem

```text
y = 1 / (1 + x_1^{-4})
    + 1 / (1 + x_2^{-4})
```

または protected division を避けるため、

```text
y = sin(x_1) + cos(x_2) + x_1 x_2
```

おすすめ度: 中

理由:

- 2 変数なので可視化しやすい。
- 非線形性があり、関数集合の影響が出やすい。

注意:

- protected division を使う場合、定義域の扱いで評価が不安定になりやすい。
- 初期本実験では Friedman-I と Poly-10 を優先する。

### SR-4: PMLB / SRBench 由来の小規模 real-world regression

おすすめ度: 中

理由:

- toy 問題だけではないことを示せる。
- SRBench の思想に沿っている。

注意:

- データ取得・前処理・標準化が必要。
- まずは synthetic で挙動を固め、その後に追加する。

## 8. 初期本実験での採用案

まずは次の 3 段階を推奨する。

| 段階 | 問題 | 位置づけ |
|---|---|---|
| smoke | SR-0 | 実装確認のみ |
| main-1 | SR-1 Friedman-I | 最初の本実験候補 |
| main-2 | SR-2 Poly-10 | 多様性・探索停滞を見やすい候補 |

初回の本実験では、Friedman-I と Poly-10 の 2 問を主対象にするとよい。

## 9. 提案手法との対応

この問題設定では、提案手法の状態変数が次のように効くことを期待する。

```text
HV:
  accuracy-complexity Pareto front の進展を見る

DeltaHV:
  直近で新しい trade-off が見つかっているかを見る

Diversity:
  同じような小さい木への収束を検出する

Mean tree size:
  bloat または小さすぎる個体への偏りを検出する

Stagnation:
  HV が伸びない状態を検出する
```

特に Poly-10 では、低複雑度個体だけでは十分な精度を得にくいため、`mean tree size` と `diversity` を観測して `p_c`, `p_m`, `k` を変える提案法の意義が出やすい。

## 10. 次に決めること

実装前に次を決める。

```text
1. 目的1を train NRMSE にするか validation NRMSE にするか
2. error upper bound E_max
3. tree size upper bound L_max
4. function set に exp/log を入れるか
5. Friedman-I と Poly-10 の sample 数
6. noise を入れるか
```

初期推奨値:

```text
目的1: train NRMSE
E_max: 5.0
L_max: 100
Function set: {+, -, *, protected_div, sin, cos}
Friedman-I: n_train=200, n_test=200, noise=0
Poly-10: n_train=300, n_test=300, noise=0
```
