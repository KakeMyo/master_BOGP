# 問題設定候補文献メモ

- 作成日: 2026-05-26
- 目的: 本実験で使う問題設定を選ぶための文献候補整理
- 管理方針: `references/README.md` には未反映。正式採用後に参考文献番号へ昇格する。

## PS01: Genetic Programming Needs Better Benchmarks

- 著者: James McDermott, David R. White, Sean Luke, Luca Manzoni, Mauro Castelli, Leonardo Vanneschi, Wojciech Jaskowski, Krzysztof Krawiec, Robin Harper, Kenneth De Jong, Una-May O'Reilly
- 年: 2012
- 掲載: GECCO 2012, pp. 791--798
- DOI: `10.1145/2330163.2330273`
- 確認元: University of Glasgow Enlighten, ACM DOI, PDF
- 保存: `Genetic Programming Needs Better Benchmarks.pdf`
- 用途分類: 問題選定の前提、benchmark 設計

### 要点

GP 研究では、歴史的によく使われる問題が簡単すぎたり、実世界性能を誤解させたりする可能性があるため、問題選定と標準化が重要であると整理している。単に toy problem を使うのではなく、難易度、再現性、比較可能性を意識した benchmark 設計が必要である。

### 本研究への使い方

- symbolic regression を使う場合でも、簡単すぎる関数だけで終わらせない根拠にする。
- 本実験では、まず小さな動作確認問題、次に難易度の異なる複数問題、という段階設計にする。
- 提案法の有効性を見るため、HV がすぐ飽和する問題だけを避ける。

## PS02: Better GP Benchmarks: Community Survey Results and Proposals

- 著者: David R. White, James McDermott, Mauro Castelli, Luca Manzoni, Brian W. Goldman, Gabriel Kronberger, Wojciech Jaskowski, Una-May O'Reilly, Sean Luke
- 年: 2013
- 掲載: Genetic Programming and Evolvable Machines, 14(1), 3--29
- DOI: `10.1007/s10710-012-9177-2`
- 確認元: University of Glasgow Enlighten, FH OOE Pure, GP Benchmarks preprint
- 保存: `Better GP Benchmarks - Community Survey Results and Proposals.pdf`
- 用途分類: benchmark 実験設計、問題選定の注意点

### 要点

GP benchmark 実践について community survey を行い、問題選択と実験厳密性の改善が必要であると報告している。よく使われるが欠点のある問題の blacklist と、代替問題候補の考え方を提案している。

### 本研究への使い方

- 本実験で「わかりやすいが簡単すぎない」問題を選ぶ方針の根拠にする。
- 1 問題だけではなく、回帰系・構造系など複数カテゴリで評価する理由にする。
- 複数 seed、比較 baseline、出力ログの標準化の根拠にする。

## PS03: Contemporary Symbolic Regression Methods and their Relative Performance / SRBench

- 著者: William La Cava, Patryk Orzechowski, Bogdan Burlacu, Fabricio Olivetti de Franca, Marco Virgolin, Ying Jin, Michael Kommenda, Jason H. Moore
- 年: 2021
- 掲載: NeurIPS Datasets and Benchmarks Track
- 確認元: SRBench 公式ページ、PMC HTML
- 保存: `Contemporary Symbolic Regression Methods and their Relative Performance.html`
- 用途分類: symbolic regression benchmark 候補、データセット選定

### 要点

SRBench は symbolic regression の再現可能な benchmark として、多数の手法と多数の regression dataset を統一設定で比較する枠組みである。公式ページでは、SR 分野における benchmark の弱さ、toy dataset への偏り、統一 framework の不足を課題として挙げ、PMLB などの多数データセットを利用している。

### 本研究への使い方

- 回帰問題の本実験候補として、SRBench / PMLB 系 dataset を選ぶ根拠にする。
- 目的関数を `error` と `model size` にする場合、accuracy-complexity trade-off を自然に説明できる。
- 最初は小さな synthetic dataset、次に SRBench から代表 dataset を選ぶ段階設計がよい。

## PS04: Evolvability Degeneration in Multi-Objective Genetic Programming for Symbolic Regression

- 著者: Dazhuang Liu, Marco Virgolin, Tanja Alderliesten, Peter A. N. Bosman
- 年: 2022
- 掲載: GECCO 2022, pp. 973--981
- DOI: `10.1145/3512290.3528787`
- 確認元: TU Delft Research Portal, arXiv, CWI PDF
- 保存: `Evolvability Degeneration in Multi-Objective Genetic Programming for Symbolic Regression.pdf`
- 用途分類: MOGP symbolic regression の難しさ、提案法の有効性が出そうな現象

### 要点

symbolic regression において、NSGA-II は accuracy と complexity のトレードオフを扱う標準的な MOGP 枠組みとして使われる。一方で、初期世代に低複雑度モデルが過剰に複製され、集団を占有してしまうことで探索効率が落ちる問題が報告されている。著者らはこれを evolvability の低下として分析している。

### 本研究への使い方

- 提案法が状態観測により `p_c`, `p_m`, `k` を変える意義を示しやすい。
- 多様性、木サイズ、停滞長、直近 HV 改善量を文脈ベクトルに入れる理由と噛み合う。
- 「単なる固定率置換ではなく、探索状態に応じた制御である」という主張に合う。

### 問題設定案

```text
目的1: validation RMSE または MSE
目的2: tree size / expression complexity
観測: HV, diversity, mean tree size, stagnation
比較: fixed GP, fixed-rate NSGA-II GP, BOGP
```

## PS05: Automated Synthesis of Mechanical Vibration Absorbers Using Genetic Programming

- 著者: Jianjun Hu, E. D. Goodman, S. Li, R. Rosenberg
- 年: 2008
- 掲載: Artificial Intelligence for Engineering Design, Analysis and Manufacturing, 22(3), 207--217
- DOI: `10.1017/S0890060408000140`
- 確認元: University of South Carolina Scholar Commons, author PDF
- 保存: `Automated Synthesis of Mechanical Vibration Absorbers Using Genetic Programming.pdf`
- 用途分類: 構造探索問題、機械振動吸収器の GP 設計

### 要点

GP によって機械振動吸収器の構造を自動合成する研究であり、ばね・ダンパ・質量などの構成要素を含む機械系構造探索に近い。現在の `StructuralSearchProblem` の「ばね・ダンパ構造を木として探索し、応答性能と部品数を評価する」方向と親和性が高い。

### 本研究への使い方

- 構造探索問題を本実験候補にする根拠として使える。
- `topology` と `topology_value` の両方を比較する意味が出る。
- 問題設定として、単なる数式回帰ではなく構造設計に近い応用例を用意できる。

### 問題設定案

```text
目的1: terminal elements / component count
目的2: impulse response integral / vibration suppression score
個体: spring, damper, series, parallel からなる木構造
archive key: topology_value を主条件
```

## PS06: Shape-constrained Multi-objective Genetic Programming for Symbolic Regression

- 著者: C. Haider, F. O. de Franca, B. Burlacu, G. Kronberger
- 年: 2023
- 掲載: Applied Soft Computing, 132, 109855
- DOI: `10.1016/j.asoc.2022.109855`
- 確認元: ScienceDirect
- 保存: メタデータ確認のみ
- 用途分類: 3 目的以上への拡張候補、制約付き symbolic regression

### 要点

shape-constrained symbolic regression に対して、prediction error と constraint violation を多目的に最小化する設定を扱う。positivity、monotonicity、convexity などの事前知識を回帰モデルに入れる方向であり、工学的 prior knowledge を使う問題として説明しやすい。

### 本研究への使い方

- 2 目的から 3 目的へ拡張するときの候補。
- 目的関数を `error`, `constraint violation`, `tree size` にできる。
- ただし、現在の HV 実装が 2 目的 exact HV なので、本実験初期では優先度を下げる。

## PS07: Decomposition Based Cross-parallel Multiobjective Genetic Programming for Symbolic Regression

- 著者: Lei Fan, Zhaobing Su, Xiyang Liu, Yuping Wang
- 年: 2024
- 掲載: Applied Soft Computing, 167, 112239
- DOI: `10.1016/j.asoc.2024.112239`
- 確認元: ScienceDirect
- 保存: メタデータ確認のみ
- 用途分類: SR の bloat, blind search, diversity loss の根拠

### 要点

GP-based symbolic regression は、model bloat、blind search、diversity loss、overfitting の影響を受けやすく、時間がかかり不安定になりやすいと整理している。SRBench に基づく比較にも触れており、本研究の「多様性と収束の両立」という問題設定に合う。

### 本研究への使い方

- 提案手法の報酬に多様性項を残す理由の背景にできる。
- 回帰問題が単なる toy ではなく、bloat と diversity loss を含む探索問題であることを説明できる。

## PS08: Preference-driven Pareto Front Exploitation for Bloat Control in Genetic Programming

- 著者: 検索時点では ScienceDirect metadata 確認
- 年: 2020
- 掲載: Applied Soft Computing, 92, 106254
- DOI: `10.1016/j.asoc.2020.106254`
- 確認元: ScienceDirect
- 保存: メタデータ確認のみ
- 用途分類: MOGP, bloat control, Pareto front exploitation

### 要点

multi-objective GP を bloat control に使い、benchmark symbolic regression tasks で標準 GP、parsimony GP、standard MOGP と比較している。Pareto front のどの領域を探索するかという視点があり、本研究の「状態に応じて操作強度を変える」設計と相性がよい。

### 本研究への使い方

- 精度・サイズ Pareto front を評価対象にする妥当性の補強。
- 固定率 GP だけでなく、bloat control 系 baseline を今後追加する候補にする。

## PS09: Structural Topology Optimization Using Multi-objective Genetic Algorithm with Constructive Solid Geometry Representation

- 著者: Faez Ahmed, Kalyanmoy Deb, Bishakh Bhattacharya
- 年: 2016
- 掲載: Applied Soft Computing, 39, 240--250
- DOI: `10.1016/j.asoc.2015.10.063`
- 確認元: ScienceDirect
- 保存: メタデータ確認のみ
- 用途分類: 構造 topology optimization, Pareto front 生成

### 要点

構造 topology optimization において、構造表現をグラフ・幾何プリミティブで表し、多目的 GA によって compliance と material availability のトレードオフを扱う。GP そのものではないが、構造設計問題で Pareto front を得る設定として参考になる。

### 本研究への使い方

- 将来的に構造探索問題を「ばねダンパ」以外へ拡張する場合の候補。
- 目的関数を `compliance` と `material usage` にする設計の参考。
- 実装負荷は高いため、初回本実験の主対象よりは後続候補。

## 推奨する問題設定案

### 案1: Accuracy--Complexity Symbolic Regression

```text
個体:
  数式木

目的:
  f_1 = validation MSE または RMSE
  f_2 = tree size

比較:
  plain_fixed
  bogp_current
  plain_fixed_grid

期待される観察:
  固定率 GP は早期収束または bloat に寄りやすい
  BOGP は diversity と HV を両立しやすい
```

最もおすすめ。実装が軽く、2 目的 HV が使え、結果の図も説明しやすい。

### 案2: Evolvability-stressed Symbolic Regression

```text
個体:
  数式木

目的:
  f_1 = validation error
  f_2 = expression complexity

問題:
  低複雑度個体が過剰複製されやすい dataset を選ぶ

期待される観察:
  mean tree size, diversity, stagnation が提案法の制御判断に効く
```

提案法の「状態依存制御」を見せるにはかなり良い。ただし dataset 選定と予備分析が必要。

### 案3: Spring-Damper Structural Search

```text
個体:
  series / parallel / spring / damper の木構造

目的:
  f_1 = terminal element count
  f_2 = impulse response integral

期待される観察:
  topology_value archive の意味が出る
  構造多様性と Pareto archive の関係を説明しやすい
```

構造探索研究としては魅力が強い。まずは現在の問題設定を少し難しくして、HV が早期飽和しない条件を探す必要がある。

### 案4: Shape-constrained Symbolic Regression

```text
個体:
  数式木

目的:
  f_1 = prediction error
  f_2 = constraint violation
  f_3 = tree size
```

3 目的化に向くが、現在は HV と図示の整備が必要。第2段階候補。

## 現時点の採用優先度

| 優先度 | 問題 | 理由 |
---|---|---|
| 高 | Accuracy--Complexity Symbolic Regression | 実装容易、2 目的、文献根拠が強い |
| 高 | Spring-Damper Structural Search | 研究テーマの構造探索側に近い |
| 中 | Evolvability-stressed Symbolic Regression | 提案法の状態依存性を見せやすいが dataset 選定が必要 |
| 中 | Shape-constrained Symbolic Regression | 3 目的化・制約付き問題として有望 |
| 低 | CSG Structural Topology Optimization | 説得力はあるが実装負荷が大きい |

