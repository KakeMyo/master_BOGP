# 構造探索の「難しさ」指標 調査メモ

- 作成日: 2026-05-26
- 位置づけ: 参考文献候補メモ。まだ `references/README.md`、`overleaf/references.bib`、本文の参考文献欄には反映しない。
- 対象: 本リポジトリの `StructuralSearchProblem` のような、木構造 GP による多目的な構造探索。
- 関連ファイル: [candidate_references.md](candidate_references.md)

## 1. 先に結論

構造探索の「難しさ」は、単一の普遍スコアで表すより、複数の側面に分けて測る方が文献の流れに合う。

特に重要なのは、難しさは「問題そのもの」だけでなく、

- 解の表現方法
- 近傍や距離の定義
- 交叉・突然変異などの探索演算子
- 評価関数
- 多目的選択方式
- 計算資源

に依存するという点である。Fitness landscape analysis のサーベイでも、一般的な problem hardness の単一指標を探すより、ruggedness、neutrality、deception、evolvability、local optima などの特徴量を測る方向が現実的だと整理されている。

本研究で使いやすい結論としては、次の 5 系統に分けるのがよい。

| 系統 | 何を測るか | 代表指標 | 本研究での使い道 |
|---|---|---|---|
| 経験的難しさ | 実際にどれだけ評価回数が必要か | 成功率、目標 HV 到達評価回数、HV-AUC、Koza 型 computational effort | baseline 比較の最終評価 |
| 地形の難しさ | 近い構造の性能がどれだけ不規則か | autocorrelation length、ruggedness、local optima 数、dispersion | 問題インスタンスの事前分析 |
| 誘導情報の難しさ | 評価値が良い方向をどれだけ示すか | FDC、NSC、fitness cloud | 「探索が迷いやすい」説明 |
| 演算子から見た難しさ | 1 回の変異・交叉で改善しやすいか | improvement probability、evolvability、operator locality | 操作率制御の根拠 |
| 多目的特有の難しさ | Pareto front や目的間競合が難しいか | objective conflict、Pareto local optima、front disconnectedness、nondominated ratio | 多目的 GP としての評価 |

## 2. 何を「難しい」と呼ぶか

構造探索の難しさは、少なくとも 3 種類に分けられる。

### 2.1 問題インスタンスとしての難しさ

GP を走らせる前に、ランダムサンプルやランダムウォークで見積もる難しさである。

例:

- ランダムに作った構造の大半が評価失敗する
- 近い構造に移動しても目的値が激しく変わる
- 局所的に改善できる近傍が少ない
- 同じ目的値の構造が大量にあり、評価値が探索を誘導しない

このタイプは、BO の文脈ベクトルというより、問題設定や実験条件の説明に使いやすい。

### 2.2 探索過程の状態としての難しさ

GP の実行中に「今の集団がどれだけ詰まっているか」を測る難しさである。

例:

- `DeltaHV` が小さい
- 構造多様性が落ちている
- 平均木サイズだけが増える
- 評価失敗個体や上限値に張り付いた個体が多い
- 非劣解数は多いが HV が伸びない

このタイプは、提案法の文脈付き BO に直接入れやすい。

### 2.3 アルゴリズムに対する経験的難しさ

固定されたアルゴリズムと予算のもとで、どれだけ成功しにくいかを測る難しさである。

例:

- 目標 HV に到達した seed の割合
- 目標 HV 到達までの評価回数
- 同じ予算での HV-AUC
- run 間ばらつき

これは論文の実験結果で最も説明しやすい。ただし、事前に測れる problem difficulty というより、「この手法にとってこの問題がどれだけ難しかったか」の指標である。

## 3. 指標候補

### 3.1 成功率・目標到達評価回数・computational effort

最も素直な難しさ指標は、「目的の品質に到達するまでに何回評価が必要か」である。

本研究では、例えば目標を

```text
HV >= h_target
```

または

```text
HV-AUC >= a_target
```

と置ける。

候補指標:

```text
P_success(B) = 予算 B 以内に目標へ到達した seed の割合
T_target = 目標到達までの評価回数または世代数
ERT = 成功 run の到達評価回数と失敗 run の打ち切り評価回数を含む期待到達時間
```

GP 文献では Koza の computational effort が古くから使われている。ただし Christensen and Oppacher (2002) は、Koza の統計量が条件によって真の必要計算量を過小評価し得ることを指摘しているため、使うなら「古典的指標だが注意が必要」と書くのがよい。

本研究での使い方:

- 最終比較では `final HV` だけでなく `HV-AUC` と `T_target` を見る。
- 目標到達しない run が多い場合は `success rate` を併記する。
- 「構造探索が難しい」は、最終的には「同じ評価予算で安定して良い Pareto archive に到達しにくい」と言い換えられる。

### 3.2 探索空間サイズとサンプリング誤差

木構造 GP では、最大深さ、関数集合、終端集合、各関数の arity によって探索空間が急激に大きくなる。

本研究の構造探索では、

- 内部ノード: `series`, `parallel`
- 終端ノード: `spring`, `damper`
- 終端値: ばね定数・減衰係数の離散値
- 最大深さ

が探索空間の大きさを決める。

厳密な総数を数え上げるのは難しくても、次は測れる。

```text
unique_structure_ratio = unique_structures / evaluated_individuals
duplicate_ratio = 1 - unique_structure_ratio
value_coverage = 観測された spring/damper 値の種類数 / 候補値種類数
subtree_coverage = 観測された部分木パターン数 / ランダムサンプル内部分木パターン数
```

Schweim et al. (2022) は、GP 初期集団が探索空間を代表するサンプルにならないと sampling error が生じ、信頼できる探索のためには十分な population size が必要だと議論している。これは本研究でも、構造探索の初期個体群が狭い構造だけに偏っているかを見る根拠になる。

本研究での使い方:

- 実験条件表に `max_initial_depth` と `max_mutation_depth` を必ず書く。
- 事前サンプルで `unique_structure_ratio` と `subtree_coverage` を測る。
- 初期集団の多様性が低い場合、難しさは「問題」ではなく初期化の偏りかもしれない。

### 3.3 Ruggedness: 近い構造の性能がどれだけ不規則か

Fitness landscape の ruggedness は、近傍構造間で目的値がどれだけ激しく変化するかを表す。構造探索でいうと、「少しだけ部分木を変えたらインパルス応答が大きく跳ぶ」ような状態である。

測り方の基本はランダムウォークである。

1. ランダム構造 `x_0` を作る。
2. mutation で `x_1, x_2, ...` を作る。
3. 各構造をスカラー品質 `q(x)` に変換する。
4. 時系列 `q(x_t)` の自己相関を見る。

代表指標:

```text
rho(1) = corr(q(x_t), q(x_{t+1}))
ell = -1 / log(|rho(1)|)
```

`ell` は autocorrelation length の簡易形で、短いほど近傍の情報がすぐ失われるため rugged と解釈できる。

多目的の場合は、スカラー品質 `q(x)` を次のいずれかにする。

```text
q_hv(x) = 単独または archive への HV contribution
q_eps(x) = 参照点から見た epsilon 指標の符号反転
q_rank(x) = 非優越 rank の符号反転
q_weighted(x) = 正規化目的の重み付き和の符号反転
```

本研究での使い方:

- まずは `q_weighted = -(normalized_terminal_count + normalized_impulse_integral)` で十分。
- 次に archive が使える段階で `HV contribution` に置き換える。
- BO 文脈に直接入れるより、問題設定の難しさ説明と ablation 解釈に使う。

### 3.4 Fitness Distance Correlation: 評価値がゴールへの距離を示すか

Fitness Distance Correlation (FDC) は、「良い解ほどゴールに近い」という関係があるかを見る指標である。

最大化品質 `q(x)` と、最良解または既知最適解までの距離 `d(x, x*)` について、

```text
FDC = corr(q(x), d(x, x*))
```

と置く。

最大化問題では、理想的には品質が高いほど距離が小さいので FDC は負になる。Jones and Forrest (1995) の整理では、おおまかに次の解釈ができる。

| FDC | 解釈 |
|---|---|
| 大きく負 | 良い方向へ進む手がかりがある |
| 0 付近 | 評価値と距離の関係が弱く、探索が迷いやすい |
| 正 | 評価値がむしろ悪い方向へ誘導する可能性がある |

ただし FDC は、既知の最適解または強い参照解が必要である。本研究の構造探索では真の最適解が不明なので、次のように近似するのが現実的である。

```text
x* = 事前ランダムサンプルまたは全 run archive 内の最良スカラー化解
d(x, x*) = 構造距離、部分木 Jaccard 距離、または operator distance
q(x) = 正規化目的の重み付き和の符号反転、または HV contribution
```

本研究での使い方:

- 本文では「真の最適解が不明なため、FDC は厳密な難易度ではなく searchability の近似」と明記する。
- いきなり主指標にせず、補助的な landscape 指標として扱う。

### 3.5 Fitness cloud と Negative Slope Coefficient

Fitness cloud は、ある構造 `x` の品質と、近傍構造 `N(x)` の品質の関係を散布図で見る方法である。

例:

```text
点 = (q(x), average q(y) for y in N(x))
```

または

```text
点 = (q(x), best q(y) for y in N(x))
```

Negative Slope Coefficient (NSC) は、この fitness cloud から「良い個体ほど次に悪化しやすい」「悪い個体ほど改善しやすい」といった傾向を数値化する GP 向けの難しさ指標として提案された。

直感的には、

- 良い個体の近傍にもさらに良い個体が多い: 探索しやすい
- 良い個体の近傍が悪化しやすい: 局所的に進みにくい
- 悪い個体からだけ改善しやすいが中盤以降詰まる: 長期探索が難しい

という見方になる。

本研究での簡易版:

```text
for x in sample:
    q_parent = q(x)
    q_children = [q(mutate(x)) for _ in range(m)]
    p_improve(x) = mean(q_child > q_parent)
    delta_best(x) = max(q_children) - q_parent
```

これを `q_parent` のビンごとに集計する。

```text
evolvability_curve(bin) = mean(p_improve(x) in bin)
```

良い品質帯で `p_improve` が急に落ちるなら、終盤ほど難しい構造探索だと説明できる。

### 3.6 Neutrality: 評価値が同じ構造が多すぎないか

Neutrality は、隣接構造の評価値が同じ、またはほぼ同じになる現象である。

本研究の構造探索では、次の理由で neutrality が起きやすい。

- 目的 1 が終端ノード数なので、同じ terminal count の構造が多い。
- 目的 2 が失敗時に `10.0` に丸められるため、評価失敗構造が大きな plateau を作る。
- 物理的に異なる構造でも、インパルス応答積分が近い場合がある。
- ばね・ダンパ値の離散化で同じ応答に近づく場合がある。

候補指標:

```text
neutral_ratio_eps =
    # { (x, y): y in N(x), |q(x) - q(y)| <= eps } / # neighbor_pairs

objective_duplicate_ratio =
    1 - unique_objective_vectors / evaluated_individuals

cap_hit_ratio =
    # { x: impulse_integral(x) == penalty_cap } / evaluated_individuals
```

neutrality が高いと、悪いことばかりではない。中立変異で別の良い領域へ移れることもある。一方で、選択圧が弱くなり停滞しやすい。したがって「高いほど常に難しい」ではなく、「改善情報が少ない」「中立漂流が必要」という解釈がよい。

### 3.7 Evolvability / Searchability: 1 ステップで改善できるか

Evolvability は、今の構造から変異・交叉でより良い構造を作れる見込みを表す。

簡単には、

```text
one_step_improvement_rate =
    # { offspring: q(offspring) > q(parent) } / # offspring
```

で測れる。

多目的版では、

```text
dominance_improvement_rate =
    # { offspring dominates parent } / # offspring

archive_improvement_rate =
    # { offspring increases archive HV } / # offspring

rank_improvement_rate =
    # { nondomination_rank(offspring) < nondomination_rank(parent) } / # offspring
```

のようにする。

Liu et al. (2022) は、多目的 GP で低複雑度モデルが過剰に複製される問題を、複雑度レベルごとの evolvability の不足として分析している。本研究でも、終端ノード数が少ない構造が多く残るが、その近傍から性能改善しにくいなら、同様の説明が使える。

本研究での使い方:

- `tree_size` または `terminal_count` ごとに `one_step_improvement_rate` を集計する。
- 低複雑度構造が多いのに改善率が低い場合、「単純構造に集団が寄りすぎて探索が詰まる」と説明できる。
- これは操作率制御の根拠としてかなり相性がよい。

### 3.8 Local optima / Pareto local optima

局所最適が多いほど、単純な変異や局所探索では抜けにくい。

単目的なら、

```text
x is local optimum if q(x) >= q(y) for all y in N(x)
```

多目的なら、

```text
x is Pareto local optimum if no y in N(x) dominates x
```

と定義できる。

候補指標:

```text
local_optimum_ratio = local_optima / sampled_points
pareto_local_optimum_ratio = pareto_local_optima / sampled_points
mean_escape_probability = mean(# improving_neighbors / # neighbors)
```

Verel et al. (2012) は、多目的 NK landscape で、問題次元、非線形性、目的数、目的間相関が Pareto local optima 数に与える影響を分析している。構造探索でも、全探索は無理でも、サンプル近傍で Pareto local optima 率を近似できる。

### 3.9 表現・演算子 locality

GP では、「構造的に近い」ことと「性能や意味が近い」ことが一致しない場合がある。これが強いと、交叉・突然変異で探索を誘導しにくくなる。

候補指標:

```text
structural_objective_locality =
    corr(d_struct(x, y), d_obj(x, y))

structural_semantic_locality =
    corr(d_struct(x, y), d_semantic(x, y))

mutation_step_volatility =
    std(q(mutate(x)) - q(x))
```

`d_struct` は、既存実装に近い部分木 Jaccard 距離や、crossover-based tree distance を候補にできる。`d_obj` は正規化した目的ベクトル距離、`d_semantic` は応答波形距離やサンプル入力上の出力距離にできる。

本研究での使い方:

- 既存の `structural_tokens()` と `population_structural_diversity` に近い。
- 構造距離と目的距離が無相関なら、構造多様性だけでは性能探索の難しさを十分に表せない。
- その場合は、応答波形ベースの semantic diversity を追加候補にする。

### 3.10 多目的特有の難しさ

多目的構造探索では、単に良い解を 1 つ見つけるだけでなく、良い trade-off 集合を作る必要がある。

候補指標:

```text
objective_corr = corr(f1, f2)
nondominated_ratio = nondominated_count / population_size
dominance_pressure = dominated_count / population_size
archive_growth_rate = new_archive_points / generation
hv_slope = DeltaHV / DeltaGeneration
front_spread = spread of nondominated points in objective space
```

目的がどちらも最小化の場合、目的値が正に相関していれば「両方よい/両方悪い」が多く、探索は比較的単純になりやすい。一方、負相関が強い場合は一方を良くすると他方が悪くなりやすく、trade-off 探索が難しくなる。

WFG Toolkit の文献では、多目的ベンチマークの難しさとして、

- bias
- multimodality
- non-separability
- convex / concave / mixed / linear
- degenerate
- disconnected Pareto front

などを組み合わせる考え方が示されている。構造探索でも、Pareto front が途切れている、特定領域に解が偏る、目的間に強い非分離性がある、という形で説明できる。

### 3.11 評価計算としての難しさ

構造探索では、探索地形だけでなく評価計算の難しさも重要である。

本研究の `StructuralSearchProblem` では、構造木から等価動剛性を作り、伝達関数とインパルス応答積分を計算している。ここでは次の指標が有効である。

```text
eval_failure_rate = 評価例外または非有限応答の割合
penalty_cap_rate = impulse_integral が上限値に張り付く割合
mean_eval_time = 1 個体評価時間の平均
p95_eval_time = 1 個体評価時間の 95 パーセンタイル
transfer_order = 伝達関数分母多項式次数
```

`penalty_cap_rate` が高い場合、目的空間に巨大な plateau ができる。これは GP から見ると neutrality とも関係するし、BO から見ると報酬が粗くなる問題にもなる。

## 4. 本研究でまず採るべき指標セット

最初から全部入れると重いので、次の 3 段階がよい。

### 4.1 すぐ実装できる軽量セット

制御文脈またはログに入れやすい。

| 指標 | 意味 | 推奨用途 |
|---|---|---|
| `HV` | 現在の Pareto archive 品質 | 既存文脈 |
| `DeltaHV` | 直近改善速度 | 既存文脈 |
| `D_struct` | 構造多様性 | 既存文脈 |
| `mean_tree_size` | bloat / 複雑化 | 既存文脈 |
| `stagnation` | 改善停止の長さ | 既存文脈 |
| `cap_hit_ratio` | 応答積分上限に張り付く割合 | 構造探索固有の追加候補 |
| `objective_corr` | 目的間競合の強さ | 問題分析・ログ |
| `nondominated_ratio` | 選択圧の弱さ/強さ | 多目的状態ログ |

特に `cap_hit_ratio` は構造探索問題らしい。`impulse_integral=10.0` が大量に出ると、選択や BO 報酬に入る情報が粗くなる。

### 4.2 事前サンプリングで測るセット

GP 本実験前に、ランダム構造とその近傍を評価する。

| 指標 | 測り方 | 解釈 |
|---|---|---|
| `random_sample_failure_rate` | ランダム構造を評価 | 高いほど評価地形が粗い |
| `neutral_ratio_eps` | mutation 前後で目的値差が小さい割合 | 高いほど plateau が多い |
| `one_step_improvement_rate` | mutation/ crossover 近傍の改善割合 | 低いほど evolvability が低い |
| `random_walk_autocorr_length` | mutation ランダムウォーク | 短いほど rugged |
| `FDC_to_best_sample` | サンプル最良構造までの距離相関 | 0 付近または正なら誘導情報が弱い |
| `pareto_local_optimum_ratio` | サンプル近傍で支配改善がない割合 | 高いほど局所 Pareto 停滞が多い |

これは論文の「実験問題の特徴」節に使いやすい。

### 4.3 余力があれば測る重めのセット

| 指標 | 価値 | 注意 |
|---|---|---|
| Local Optima Network | 地形構造を可視化できる | 近傍展開が重い |
| density of states | 良い解がどれくらい希少か見える | サンプル設計に依存 |
| semantic locality | 構造距離と応答距離の対応を見る | 応答波形保存が必要 |
| exact enumeration at small depth | 真の Pareto set に近い分析が可能 | 小さい深さ限定 |

## 5. 本文に使いやすい説明文案

以下は、将来本文へ移せる形の素案である。まだ参考文献番号は付けない。

> 構造探索の難しさは、単に候補構造の数が多いことだけでは決まらない。進化計算における fitness landscape analysis の観点では、探索空間上の近傍構造がどのような目的値を持つか、評価値が良い方向への手がかりを与えるか、局所最適や中立 plateau がどの程度存在するか、さらに使用する交叉・突然変異演算子がどのような近傍を定義するかが探索の難しさを左右する。したがって本研究では、構造探索問題の難しさを単一の指標で定義するのではなく、(i) 評価予算に対する到達性能、(ii) 構造近傍における ruggedness と neutrality、(iii) 演算子による一段階改善可能性、(iv) 多目的 Pareto 探索に固有の目的間競合と Pareto local optima、(v) 評価失敗や上限値張り付きによる情報欠落、という複数の側面から捉える。

提案手法との接続としては、次のように書ける。

> 提案法の文脈ベクトルに含める `DeltaHV`、構造多様性、停滞長、平均木サイズは、単なるログ量ではなく、探索地形の難しさに対するオンラインな代理指標として解釈できる。例えば `DeltaHV` と停滞長は現在の局所的 searchability を、構造多様性は探索領域の縮退を、平均木サイズは GP 固有の bloat を表す。構造探索問題ではさらに、評価失敗率や応答積分上限への張り付き率が高いと、目的空間に plateau が生じ、BO が得る報酬情報も粗くなるため、問題固有の難しさ指標として記録する価値がある。

## 6. 暫定的な採用方針

本研究で一番筋がよいのは、次の整理である。

1. 論文の評価指標としては、`final HV`、`HV-AUC`、`success rate`、`time/evaluations to target` を使う。
2. 問題の難しさ説明としては、`random_walk_autocorr_length`、`neutral_ratio_eps`、`one_step_improvement_rate`、`cap_hit_ratio` を使う。
3. 提案法の制御文脈としては、既存の `HV`、`DeltaHV`、`D_struct`、`stagnation`、`mean_tree_size` を維持し、構造探索問題では `cap_hit_ratio` を追加候補にする。
4. FDC と NSC は文献的には重要だが、真の最適解や十分な近傍サンプルが必要なので、主指標ではなく補助分析候補にする。
5. 多目的の難しさは、`objective_corr`、`nondominated_ratio`、`pareto_local_optimum_ratio` で説明する。

## 7. 実装メモ

`StructuralSearchProblem` に対して難しさの事前分析を実装するなら、次の流れがよい。

```text
1. rng seed を固定する
2. ランダム構造を N 個生成する
3. 各構造を evaluate し、目的値、評価失敗、tree_size、tokens を保存する
4. 各構造について m 個の mutation 近傍を生成する
5. 親子ペアから neutrality、improvement rate、objective jump を計算する
6. 別途ランダムウォークを複数本走らせ、autocorrelation length を計算する
7. sample best を参照点として FDC_to_best_sample を計算する
8. 結果を JSON/CSV と Markdown summary に保存する
```

多目的品質 `q(x)` の初期案:

```text
z1 = normalized terminal_elements in [0, 1]
z2 = normalized impulse_integral in [0, 1]
q(x) = -(z1 + z2) / 2
```

HV archive が安定してからの案:

```text
q(x) = hypervolume contribution of x to sampled archive
```

## 8. 注意点

- ruggedness、FDC、NSC は探索演算子や距離定義に依存する。同じ評価関数でも、mutation 近傍で見るか crossover 近傍で見るかで別の landscape になる。
- FDC は真の最適解が不明だと厳密な problem difficulty ではなく、sample best に対する searchability 近似になる。
- neutrality は高いほど悪いとは限らない。中立探索が有効な場合もある。
- 多目的問題では単一スカラー化で見える難しさと Pareto dominance で見える難しさがずれる。
- 本研究の構造探索では、評価失敗時の上限値 `10.0` が地形を人工的に変えている可能性があるため、`cap_hit_ratio` を必ず別に記録した方がよい。
