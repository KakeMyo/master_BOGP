# 修論本実験に向けた長期探索型問題設定・実験構成候補

- 作成日: 2026-09-03
- 状態: 候補比較版。まだ最終問題を確定しない
- 目的: BO warm-up の18世代より後にも十分な探索余地があり、状態依存の操作率制御を検証できる問題を、既存候補を捨てずに選定する
- 文献調査ログ: `reference_candidates/problem_settings/long_horizon_mogp_search_log.md`

## 1. 結論

問題を単に「難しくする」だけでは不十分である。本研究で必要なのは、次の2条件を同時に満たす問題である。

1. 18世代のwarm-up後にも、Pareto archiveのHVを改善できる余地が残る
2. 高突然変異等の一つの固定率が全期間で常に最良ではなく、探索状態によって有効な操作率が変わる

データ数が多いだけの問題は、1世代の計算時間を増やしても、世代方向の収束を遅らせるとは限らない。また、ノイズを加えてHVを揺らすだけでは、BOが有用な状態変化ではなく偶然を学習する危険がある。難しさは、必要な式構造、入力次元、非線形相互作用、無関係変数、外挿、精度と複雑さの不均衡から作る。

現時点の暫定優先順位は次である。

| 役割 | 第一候補 | 理由 |
|---|---|---|
| 主合成問題 | Vladislavleva-4 / UBall5D | 5変数、外挿、再現可能な既知真値、GP benchmarkとしてrobust difficultyが明記されている |
| 機序確認用実データ | Airfoil Self-Noise | accuracy--size MOGPで小さい木の過剰複製とevolvability低下が直接観察されている |
| 独立確認用実データ | Concrete Compressive Strength | 8入力、強い非線形、欠損なし、公開・再現容易 |
| 高負荷stress | Tower | 25入力で、別のMOGP法では平均HVが約400世代まで推移している |
| 既存論文との連続性 | Auto MPG、CCPP | Oh et al.由来の候補を維持し、Auto MPGは開発、CCPPは外的妥当性確認に使える |
| 校正・負の対照 | Friedman-I、Poly-10、Niehaus由来sin | 「早期に解ける問題では適応制御が不要」という適用限界を示せる |

ただし、Airfoilで通常のNSGA-IIが早く停滞するという事実は、「18世代以後も改善する」保証ではない。むしろ、提案法がその停滞を回避できるかを試す機序stressである。最終採用は、BOを一度も使わないcontroller-blind pilotで決める。

## 2. 前回実験で起きていたこと

現行Friedman-I本実験の100 seed平均では、提案法のarchive HVは次であった。

| 世代 | 平均archive HV |
|---:|---:|
| 0 | 0.452491 |
| 18 | 0.740278 |
| 78 | 0.802461 |

したがって、18世代時点で次が起きている。

- 最終HVの約92.3%へ到達
- 世代0から78までの全HV改善量の約82.2%をwarm-up中に獲得
- warm-up中の改善量は、その後60世代の改善量の約4.63倍
- 18世代は全78世代の23.1%を占める

つまり、「BO本制御が始まる時点で大方収束している」という認識は集計値でも正しい。参照データは `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/main_generation_metric_summary.csv` の239、257、317行である。

さらに、現行warm-upは各 `k` を2回観測するため、実質的に次の順で進む。

```text
k = 1, 1, 3, 3, 5, 5
消費世代 = 1 + 1 + 3 + 3 + 5 + 5 = 18
```

この設計には二つの問題がある。

- `k=5` は探索が進んだ後だけで試されるため、`k` の効果と探索時期が交絡する
- 同じ2観測でも、`k=1` は2世代、`k=5` は10世代を消費するため、観測数は均等でも世代予算は均等でない

よって、本実験では「より長い問題」と「warm-up設計の比較」を同時に扱う必要がある。

## 3. 問題選定で守る原則

### 3.1 BOの勝敗で問題を選ばない

提案法が勝った問題だけを選ぶとcherry-pickingになる。問題候補は固定率GPだけでscreenし、次の性質で採否を決める。

- warm-up後の改善余地
- 長期の非ゼロHV傾き
- seed間の再現性
- 操作率に対する反応が探索状態で変わるか
- 計算時間、無効木、bloatが管理可能か

### 3.2 「長い」と「適応余地あり」を分ける

長く改善する問題でも、全世代で高突然変異固定率が最良なら、文脈付きBOを使う必然性は弱い。逆に、最適率が状態で変わっても18世代で解き終われば、BOに学習時間がない。両方を独立に確認する。

### 3.3 現行基盤では2目的に限定する

現行実装は2目的HVだけを正しく計算するため、本番候補は原則として次に統一する。

\[
f_1(T)=\text{prediction error},\qquad
f_2(T)=\text{tree size}
\]

shape constraint等を加えた3目的問題は、多次元HVを実装・検証してからの将来案とする。

## 4. 全候補台帳

評価記号は、`高`、`中`、`低`、`不明`であり、最終採否ではない。

| ID | 出典・問題 | warm-up後headroomの根拠 | 状態依存制御との相性 | 再現性 | 計算費用 | 暫定判断 |
|---|---|---|---|---|---|---|
| P01 | 現行Friedman-I | 低。18世代で全改善の約82% | 中 | 高 | 低 | 負の対照として残す |
| P02 | 現行Poly-10 | 低。初期HVが高く改善がほぼない | 低 | 高 | 低 | 負の対照のみ |
| P03 | Niehaus由来sin | 低～不明。1変数・50点 | 中 | 高 | 低 | 校正用、主問題にはしない |
| P04 | Oh Auto MPG | 不明。小規模なので早期収束リスク | 中 | 高 | 低 | 開発候補として残す |
| P05 | Oh CCPP | 不明。大標本は長期収束を保証しない | 中 | 高 | 高 | 外的妥当性候補として残す |
| P06 | Oh CPU-ERP / PRP | 低～不明 | 低 | 中 | 低 | ERPは負の対照、PRPは独自副問題 |
| P07 | Oh private CTQ | 評価不能 | 評価不能 | 低 | 不明 | 使用不可 |
| P08 | Vladislavleva-4 / UBall5D | 高い候補。robust difficulty、5D、外挿 | 高い可能性 | 高 | 中 | 主合成問題の第一候補 |
| P09 | Korns-12 | 高い候補。原文献群で難しく、無関係3変数 | 高い可能性 | 高 | 高 | feature-selection stress |
| P10 | Keijzer-6 | 中～高。外挿を含む | 中 | 高 | 低 | 安価な補助候補 |
| P11 | Pagie-1 | 中。smoothだが難しいとの評価、次元拡張可能 | 中 | 高 | 低 | 補助・scalable候補 |
| P12 | Dou Salustowicz型F5 | 222世代のMOGP設定 | 中～高 | 高 | 低 | 表現制限下の近似stress |
| P13 | Harrison Synthetic-1 | 必要木が比較的大きい | 高い可能性 | 中 | 中 | 定義曖昧さ解消後の候補 |
| P14 | Airfoil Self-Noise | 通常NSGA-IIは早期停滞、改善法は100世代まで推移 | 高。evolvability機序が直接対応 | 高 | 中 | 機序stressの第一候補 |
| P15 | Concrete Strength | MOGP利用実績、8入力・強い非線形 | 中～高 | 高 | 中 | 独立確認の第一候補 |
| P16 | Energy Efficiency | MOGP利用実績、8入力・2 target | 中 | 高 | 中 | 予備確認候補 |
| P17 | Wine Quality red/white | 11入力、一部変数の関連性が不明 | 中 | 高 | 中～高 | feature-selection実データ候補 |
| P18 | Tower | 別MOGPで約400世代のHV曲線 | 高い可能性 | 中 | 高 | ライセンス・版固定後のstress |
| P19 | Bike Daily | 別MOGP利用実績 | 中 | 中 | 中 | 時系列・leakage処理のため優先度低 |
| P20 | spring--damper構造探索 | 低。現設定は初期HV約0.9986 | 高い可能性 | 中 | 中 | 問題再設計後の将来案 |
| P21 | Ni et al. noisy family | 長期評価設定らしいが正式本文取得待ち | 高い可能性 | 保留 | 中～高 | 手動取得後に追加審査 |
| P22 | SRBench/PMLBからの追加選定 | dataset依存 | dataset依存 | 高 | dataset依存 | 予備pool。事前規則で選ぶ |

## 5. 既存2論文由来の候補は残す

### 5.1 P03: Niehaus and Banzhaf由来のsin回帰

以前の候補を、低コストの校正問題として残す。

```text
x_i = 6.3 i / 49,  i = 0,...,49
y_i = sin(x_i)
目的1 = train error
目的2 = tree size
```

ただし、そのまま `sin` primitiveを与えると `sin(x)` が非常に短い木で表現できる。長期探索を意図する場合は、原設定に合わせてsin/cosをprimitiveから外し、四則演算等による近似問題として使う。最終評価には独立したdense gridを追加する。

判断:

- 実装確認、操作率ログ、HV正規化の検査には使える
- 1変数・50点なので修論の主問題としては弱い
- Niehaus法は個体ごとに複数の突然変異演算子確率を持つのに対し、本研究は集団全体の `(p_c,p_m,k)` を区間単位で制御するため、直接の同一手法比較とは呼ばない

### 5.2 P04: Auto MPG

- 公開元: [UCI Auto MPG](https://archive.ics.uci.edu/dataset/9/auto+mpg)
- 規模: 欠損除去後の標準的な完全行は392件、入力6変数を基本とする
- 役割: 実データadapterと前処理の低コスト開発、Oh由来の連続性確認

注意:

- Oh et al.本文の391件はUCIの通常の欠損除去結果392件と一致しない
- 小規模なので18世代以内に構造が固まる可能性がある
- 主問題ではなく、pilotと実装検証に向く

### 5.3 P05: Combined Cycle Power Plant (CCPP)

- 公開元: [UCI CCPP](https://archive.ics.uci.edu/dataset/294/combined+cycle+power+plant)
- 規模: 9568件、4入力、targetはnet hourly electrical energy output
- 役割: Oh由来の公開確認問題、比較的大きな実データでの外的妥当性

注意:

- 4入力の滑らかな回帰なので、データ件数が多くても式探索が長期化する保証はない
- 1世代のfitness計算が重く、同じ情報量を得るコストが高い
- controller-blind pilotで `q_W` と `t_90` を満たした場合に本番採用する

### 5.4 P06/P07: CPUとprivate CTQ

- CPUのERP targetは元データの線形回帰推定値であり、非線形式探索の主benchmarkとしては不適切
- CPU-ERPは「簡単なtargetではBOが不要」という負の対照にできる
- 実測PRPをtargetに変更する場合は、Oh再現ではなく独自副問題と明記する
- private CTQは件数、分割、データ本体が公開されていないため、再現可能な修論実験には使用できない

### 5.5 Oh-SAGPを比較法として残す場合

Oh-SAGPの式は、平均木長比 `r=L(t-1)/L(t)` を用いて概ね次となる。

\[
p_c=0.9-0.15r,\qquad p_m=0.5-0.35r
\]

`r=1`なら `(p_c,p_m)=(0.75,0.15)` である。しかし、範囲外や `p_c+p_m>1` の処理が本文だけでは十分に再現できない。本研究の排他的な交叉・突然変異・複製へ入れる場合は、次を明示する。

- raw値を保存
- 本研究の許容範囲へclip
- `p_c+p_m<=1` の実行可能領域へ射影
- 実際に適用した値を保存
- 固定 `(0.75,0.15)` も比較し、適応効果と単なる高突然変異化を分離

## 6. 新しい合成問題候補

### 6.1 P08: Vladislavleva-4 / UBall5D

\[
y=\frac{10}{5+\sum_{i=1}^{5}(x_i-3)^2}
\]

canonical data:

```text
train: x_i ~ U[0.05, 6.05], 1024 points
test : x_i ~ U[-0.25, 6.35], 5000 points
dimension: 5
noise: none
```

長期候補として強い理由:

- 5変数すべてを組み合わせた分母構造が必要
- trainより広いtest範囲で外挿を測る
- benchmark提案論文は、単純な入力出力関係であってもGPが発見しにくい問題として紹介している
- 真の式が既知なので、test errorだけでなく構造回復も補助評価できる

本研究での設定案:

- 進化目的: train NRMSEとtree size
- hard node cap: 100
- validation: train domainから独立1024点を追加生成し、問題・ハイパーパラメータ選定にだけ使う
- test: canonical 5000点を本番までlock
- primitive: `{+,-,*,protected_div}` を基本とし、全手法で同一にする
- seedと生成点をmanifestへ保存

### 6.2 P09: Korns-12

\[
y=2-2.1\cos(9.8x)\sin(1.3w)
\]

```text
variables: 5
relevant variables: x, w の2個
irrelevant variables: 3個
train: U[-50, 50], 10000 points
test : U[-50, 50], 10000 independent points
```

長期候補として強い理由:

- 5変数のうち3変数が出力に無関係であり、feature selectionと過学習回避が必要
- 係数 `9.8` と `1.3` の同定、sin/cosの組合せが必要
- benchmark提案論文で、複数の専用技法を用いても未解決だった難問として選ばれている

注意:

- 20000 fitness casesは高コスト
- 現行ERC範囲だけでは9.8の生成が難しく、係数探索が支配的になる可能性がある
- ERC範囲またはcoefficient mutationを全手法共通で事前固定する
- 小標本版でpilotしても、本番をcanonical 10000/10000とするなら別問題扱いにする

### 6.3 P10: Keijzer-6

\[
y(x)=\sum_{i=1}^{x}\frac{1}{i}
\]

```text
train: x=1,...,50
test : x=1,...,120
```

外挿を安価に確認できる。ただし1入力であり、式木GPが連続近似として解くため、適応制御の必要性はP08/P09より弱い。安価なscreen候補とする。

### 6.4 P11: Pagie-1

\[
y=\frac{1}{1+x^{-4}}+\frac{1}{1+y^{-4}}
\]

```text
x,y in [-5,5]
grid spacing: 0.4
```

smoothだが難しいとされ、次元を増やしてscalable problemにできる。別test setが原仕様にないため、独立dense gridまたはランダムtestを事前定義する。次元追加はcanonical reproductionではなく派生問題と明記する。

### 6.5 P12: Dou and RockettのSalustowicz型F5

\[
y=8e^{-x}x^3\cos x\sin x\left(\cos x\sin^2x-1\right),
\qquad x\in[0,10]
\]

文献設定の要点:

- train: 20 random points
- test: 10000 points
- population: 100
- generations: 222
- objectives: errorとnode count
- primitive: `{+,-,*,AQ}`

targetにはexp、sin、cosが含まれる一方、primitiveへ直接は与えず、限られた表現で近似する。このため完全式発見ではなく、近似精度と木サイズのPareto frontを長く改善する候補になる。

注意:

- 難しさの主因が表現集合の不一致である
- 一般的な式発見能力より、「限られた表現下の近似」を測る
- 主問題より、長期挙動を安価に見る補助問題が適切

### 6.6 P13: Harrison Synthetic-1

論文付録のtargetは次である。

\[
y=\sum_{i=1}^{8}\sin(x_i+x_0)
\]

1000標本で、単純な `sin(x)` よりも多変数と反復部分構造を必要とする。ただし、付録は式で `x_0` から `x_8` まで9変数を使う一方、入力スケールとして列挙する素数は8個であり、記載に不整合がある。

判断:

- そのまま「原論文再現」とはできない
- 著者コードまたは補足資料で入力生成を確定できれば有力
- 独自に9番目の素数23を補う場合は `Harrison-S1-derived-9` と命名し、paper-derived problemとして扱う
- 曖昧さが解消するまではP08を主合成第一候補とする

### 6.7 P21: Ni et al.のnoise付き候補

Ripple、RatPol3D、UBall5Dのnoise付き・AQ条件は、長期探索候補として興味深い。しかし、今回の自動検索ではIEEE書誌と抄録は確認できたものの、取得ルールに合う出版社または機関リポジトリ由来の全文を確保できなかった。

したがって現段階では保留とし、具体的な本番仕様へは使わない。DOI `10.1109/TEVC.2012.2195319` の正式本文を手動取得後に再審査する。

## 7. 新しい実データ候補

### 7.1 P14: Airfoil Self-Noise

- 公開元: [UCI Airfoil Self-Noise](https://archive.ics.uci.edu/dataset/291/airfoil%2Bself%2B)
- 規模: 1503件、5入力、欠損なし、CC BY 4.0
- target: scaled sound pressure level

Liu et al.のaccuracy--size MOGPでは、初期に小さい木が過剰複製されると、大きく高精度な木を生み出しにくくなる。AirfoilのHV曲線では、通常NSGA-II等が最初の十数世代後に低い値で停滞する一方、evolvabilityを保つ改良法は100世代を通して改善する。

本研究との対応:

- mean tree sizeは小木による占有を検出できる
- structural diversityは集団の縮退を検出できる
- stagnationとrecent HV deltaは脱出が必要な状態を示せる
- `p_m`を上げる、`p_c`との比を変える、更新間隔を変える意味が出やすい

重要な反対解釈:

- 通常NSGA-IIが早く停滞するため、本研究のwarm-up中にも不可逆な縮退が起きる可能性がある
- 「難しいから長く改善する」のではなく、「早く悪い局所状態へ止まる」だけかもしれない
- したがってP14は無条件の主問題ではなく、提案法が早期縮退を回避できるかを見る機序stressである

### 7.2 P15: Concrete Compressive Strength

- 公開元: [UCI Concrete Compressive Strength](https://archive.ics.uci.edu/dataset/165/concrete%2Bcompressive%2Bstrength)
- 規模: 1030件、8入力、欠損なし、CC BY 4.0
- target: compressive strength
- UCI説明: 強度は材料配合と材齢の強い非線形関数

Airfoilより入力が多く、データも十分あり、公開性が高い。長期収束の直接証拠はTowerほど強くないため、controller-blind pilotで確認する。外的妥当性と再現性のバランスがよい。

### 7.3 P16: Energy Efficiency

- 公開元: [UCI Energy Efficiency](https://archive.ics.uci.edu/dataset/242/energy%2Befficiency)
- 規模: 768件、8入力、欠損なし、CC BY 4.0
- targets: heating load、cooling load

同じ入力に対する2 targetであるため、二つを独立した証拠として数えない。どちらか一方を事前に主targetへ固定し、他方を頑健性確認にする。

### 7.4 P17: Wine Quality

- 公開元: [UCI Wine Quality](https://archive.ics.uci.edu/dataset/186/wine%2Bquality)
- white: 4898件
- red: 1599件
- inputs: 11、欠損なし、CC BY 4.0

UCI自身が全入力の関連性は不明としており、実データのfeature-selection stressになる。ただし官能評価targetは離散的・不均衡であり、純粋な連続物理量回帰とは性質が異なる。

### 7.5 P18: Tower

- 規模: 4999件、25入力
- Harrison et al.のMOGP/GP-GOMEA評価で使用
- 同論文の平均HV曲線は約0～400世代を表示し、18世代後にも長い改善尾部を持つ

長期候補として最も直接的な図がある。ただし、原論文のGP-GOMEAは本研究のNSGA-II型subtree crossover/mutation GPと大きく異なる。そのため、借りられるのはデータ問題であり、同じ収束曲線になるとは主張できない。

正式採用前の条件:

- 配布元と利用許諾の確認
- ファイルversionとSHA-256の固定
- 欠損、標準化、target列、分割規則の固定
- population 100でのruntime pilot

### 7.6 優先度を下げる実データ

- Boston Housing: 古い社会属性変数を含み、Airfoil/Concreteで代替可能
- Bike Daily: `casual`と`registered`はtargetの線形構成要素なので除外必須。加えて時系列性があり、random splitの妥当性が別論点になる
- Dow Chemical: 高次元で魅力はあるが、公開版と前処理の再現性を固定しにくい
- Yacht: 308件と小さく、長期探索を保証しにくい

## 8. 構造探索候補の扱い

### 8.1 P20: spring--damper

構造探索は提案法の構造多様性と親和性が高いため、候補から削除しない。しかし現設定の保存済み固定率実験では、archive HVが世代0で約0.998627、世代3で約0.999522へ達している。現在のままでは、Friedmanよりさらに強い初期飽和問題である。

本番候補へ戻す前に必要な変更:

- 目的上限とreference pointの再定義
- 物理パラメータ範囲と応答積分の検証
- 最大部品数・深さのhard cap
- 初期個体が参照点近くの広い領域を占めるよう正規化を再設計
- 18世代以後のHV headroomを固定率pilotで確認

これを満たすまで、主実験には使用しない。

## 9. controller-blind pilot

### 9.1 固定率だけで候補をscreenする

最初にBOを一度も走らせず、各候補へ同じ固定率集合を適用する。

```text
A1: (p_c,p_m) = (0.80,0.05)  現行standard
A2: (0.70,0.20)              現行high mutation
A3: (0.90,0.05)              現行high crossover
A4: (0.75,0.15)              Oh式のr=1平衡点
A5: (0.60,0.30)              強い探索条件
```

全条件で `p_c+p_m<=1` とし、残りを複製確率とする。

### 9.2 長期headroom指標

固定率 `a` とseed `s` のarchive HVを `HV_{a,s}(g)` とする。各固定率のseed中央値曲線を `\widetilde{HV}_a(g)` とし、最終中央値が最も高い固定率を `a*` とする。

\[
q_W=
\frac{\widetilde{HV}_{a^*}(18)-\widetilde{HV}_{a^*}(0)}
{\widetilde{HV}_{a^*}(G)-\widetilde{HV}_{a^*}(0)}
\]

`q_W`は全改善のうちwarm-up相当区間で得た割合である。

主問題の採用基準案:

1. `\widetilde{HV}_{a*}(G)-\widetilde{HV}_{a*}(0) >= 0.05`
2. `q_W <= 0.70` を必須、`q_W <= 0.50` を優先
3. 改善量の90%へ達する世代のseed中央値 `t_90 >= 54`、望ましくは `>=90`
4. seedの70%以上で `HV(G)-HV(18) > 0.01`
5. 18世代以後の複数窓で正の中央値傾きがある
6. reference pointのclipや初期HV飽和で見かけの値を作っていない

分母が小さい問題は第1条件で除外する。archive HVは単調非減少なので、`t_90`は各seedの全改善量に対して定義し、seedごとの値を集計する。

### 9.3 状態依存の操作率効果を確認する

世代18、60、150の集団、archive、乱数状態を保存する。各checkpointから複数の固定率へ分岐し、15世代の共通予算で `Delta HV` を測る。

適応余地ありとする条件:

- checkpointによって最良または上位の操作率が変わる
- 操作率間の効果差がseed変動に埋もれない
- 初期探索、中期改善、停滞脱出の少なくとも二状態で異なる傾向がある

`k` は固定率GP単体ではGP軌跡を変えないため、このbranch testで直接最適化しない。代わりに、同じ軌跡から1、3、5世代窓の報酬分散、信号対雑音比、状態変化速度を計算し、更新周期を変える情報的価値があるかを確認する。

### 9.4 pilotを二段階にする

計算費用を抑えるため、次を推奨する。

```text
Round 1: population 100, G=120, 5 discovery seeds, fixed A1--A5
Round 2: Round 1を通過した上位4～6問題、population 100,
         G=318, 10 discovery seeds, fixed A1--A5
```

Round 1は明らかな初期飽和と実行不能を除くためであり、最終採否はRound 2で行う。BOの結果は問題採否へ使わない。

## 10. warm-up構成案

### W18-S: 現行sequential

```text
1, 1, 3, 3, 5, 5
total = 18 generations
```

過去実験との連続性を保つbaselineとして必ず残す。

### W18-C: counterbalanced / interleaved

```text
例: 1, 3, 5, 1, 3, 5
total = 18 generations
```

実際にはseed間で `k={1,3,5}` の順序をLatin-square的に均衡化し、全BO変種で同じ順序を共有する。観測数を保ったまま、`k`と探索時期の交絡を弱める。修正版の主候補とする。

### W12-B: generation-budget balanced

観測数でなく消費世代数を約12へそろえる。`k`ごとの観測数が不均等になりsurrogate学習量が偏るため、ablationとして扱う。

### W6-k1: 更新周期を制御しないBO

`k=1`だけを用いるため、6観測なら6世代でwarm-upを終えられる。`p_c,p_m`の状態依存制御の効果と、`k`制御の追加価値を分離する。

### Warm-up replay + fixed

提案法と同じwarm-up制御列を再生した後、tuningで選んだ固定率へ切り替える。これにより、結果差がwarm-up由来か、warm-up後のBO制御由来かを分離する。

暫定推奨:

- 主仕様: W18-C
- 連続性baseline: W18-S
- 機序ablation: W6-k1、warm-up replay + fixed
- W12-Bは計算余力がある場合

## 11. 世代数・評価予算

第一案:

```text
population N = 100
warm-up W = 18 generations
post-warm-up control = 300 generations
total G = 318 generations
```

初期集団を含む目的関数評価回数は、

\[
E=N(G+1)=100\times319=31,900
\]

である。現行報告の `24*78=1872` は子個体だけを数えており、初期24個体を含む真の評価回数は `24*(78+1)=1896` である。本番では必ず初期集団を含める。

この設定の利点:

- warm-up比率が現行23.1%から5.7%へ下がる
- post区間は、常に `k=5` でも最低60回のBO更新を持つ
- 平均 `k=3` なら約100回の更新を持つ
- population 100は文献例と整合し、現行PythonのO(N^2)非優越ソートにも現実的

追加予算:

- P08やP18で `t_90` が318世代を超えるなら、事前に定義した長期感度条件 `G=500` を追加
- population 200は探索感度として有用だが、非優越ソート費用が約4倍になるためruntime確認後のみ
- archive無更新による早期停止は使わない。後期の停滞脱出を測れなくなるためである

## 12. 本番の比較法

### 12.1 core比較

| ID | 手法 | 目的 |
|---|---|---|
| M1 | fixed standard `(0.80,0.05)` | 前回との連続性 |
| M2 | fixed high mutation `(0.70,0.20)` | 現在の最強固定baseline |
| M3 | tuning-only best fixed | 固定率の公平な強baseline |
| M4 | context-free BO | 文脈情報の価値 |
| M5 | contextual BO, `k=1` | 操作率制御と周期制御の分離 |
| M6 | full contextual BO, `k in {1,3,5}` | 提案法 |

### 12.2 secondary比較

- fixed high crossover `(0.90,0.05)`
- fixed Oh equilibrium `(0.75,0.15)`
- projected Oh-SAGP
- W18-S current controller
- warm-up replay + best fixed
- 必要ならNSGA-II+duplicate penalty。ただしselection法自体が変わるため機序比較であり、操作率制御の直接baselineではない

`tuning-only best fixed`は、評価seedごとに最良率を選ぶoracleではない。独立tuning seedsで一つの固定率を問題ごとに決め、confirmatory seedsでは固定する。

## 13. データ分割と探索設定

### 13.1 実データ

- outer split: train 75%、test 25%
- trainの20%をvalidationへ分け、実質train 60%、validation 15%、test 25%
- `X`と`y`の標準化はtrain統計だけで行う
- split index、scaler、data file hashをmanifestへ保存
- 同じsplit、初期集団、algorithm seedを全比較法で共有
- 例: 10 data splits × 3 algorithm seeds = 30 paired runs
- testは仕様freeze後まで問題選択、率選択、controller調整に使わない

### 13.2 合成データ

- canonical train/test範囲と標本数を保持
- validationを足す場合はtrain domainから独立生成し、生成seedを保存
- UBall5Dのtest外挿範囲は変更しない
- Harrison Syntheticのようなraw scaleが問題定義に含まれる場合、実データのような標準化を自動適用しない

### 13.3 関数集合と係数

全問題で同じprimitiveにする必要はないが、同一問題内の全比較法では完全に同じにする。

- 実データprofile: `{+,-,*,protected_div,protected_sqrt,protected_log}` とERCを基本
- Korns-12: `sin,cos`を追加
- UBall5D: `{+,-,*,protected_div}` を基本
- Niehaus近似版: `sin,cos`を除く
- Dou F5: 文献に合わせるならAQを用い、exp/sin/cosを与えない

linear scalingまたはcoefficient mutationを使う場合も、全比較法へ同一に適用する。実データprofileではLiu et al.との整合からtrain-derived linear scalingを第一候補とするが、pilot前に有無を固定する。

## 14. 目的、HV、木サイズ

### 14.1 探索目的

```text
objective 1: train NRMSE、または train MSE / Var(y)
objective 2: node count / 100
hard node cap: 100
```

木サイズ100は現在、目的正規化上限として使われるだけでhard capではない。本番前に、超過子個体を再試行し、上限回数後は親を複製する等の明示的制約を実装する。

### 14.2 HV正規化

現在の`ObjectiveSpec`は範囲外をclipするため、上限設定が甘いと初期HVを不自然に高くできてしまう。候補問題ごとにfixed pilotで分布を確認し、confirmatory testを見る前に次を固定する。

- error normalization
- size normalization
- reference point
- clipの扱い

第一候補はLiu et al.に近い `MSE/Var(y)` とsize/100、reference `(1.1,1.1)` である。ただし現行のreference `(1,1)` とclip実装を変更するため、HV unit testと過去結果との非互換性を明記する。現行仕様を維持する場合は、pilot seedだけから誤差上限を定め、その値を全手法・confirmatory seedsで固定する。

## 15. 評価指標

### 15.1 主評価

1. 最終archiveをtestで再評価したtest HV
2. warm-up後のanytime性能

warm-up後のHV-AUCは、本研究内で次のように定義する。

\[
\mathrm{AUC}_{post}
=\frac{1}{G-W}\sum_{g=W+1}^{G}HV(g)
\]

これは本研究の定義であり、既存論文が同名指標を定義したと主張しない。

### 15.2 必須の補助評価

- `HV(G)-HV(W)`: warm-up後の純改善量
- `t_90`, `t_95`: 全改善量の90%、95%へ達する世代
- train/validation/testのNRMSE--size front
- unique objective、unique topology、unique topology-value数
- structural diversity、duplicate率、木サイズ分布、平均木サイズ
- stagnation長、oversize拒否率、無効数式率
- 実際に適用された交叉・突然変異・複製回数
- BO decision数、`k`分布、行動entropy、率の変化量
- wall-clock time、初期集団込み評価回数
- syntheticでは真の式との構造一致または簡約後の等価性を補助指標にする

### 15.3 統計

- discovery: 5～10 paired seeds
- tuning: discoveryと分離した10程度のpaired seeds
- confirmatory: 未使用30 paired runsを基本。pilot分散から事前に必要なら50へ増やす
- paired bootstrap confidence interval
- paired permutation testまたはWilcoxon signed-rank test
- paired rank-biserial correlation等の効果量
- 事前指定した比較にHolm補正
- win/tie/lossと問題横断rankも併記

平均値とp値だけでなく、差の大きさと不確実性を示す。

## 16. 実装前に必要な修正

1. 任意の配列/CSVと分割manifestを受けるtabular symbolic regression adapter
2. dataset seedとalgorithm seedの分離
3. node cap 100の実制約化
4. 個体式、train/validation/test指標、split ID、scalerの保存
5. 初期集団を含む評価回数の統一
6. HV正規化・reference point・clipの問題別固定
7. 問題別primitive setとERC/coefficient処理の設定化
8. 大集団・大標本用のruntime記録とdiversity pair sampling
9. W18-C等のwarm-up順序設定とログ化
10. final archiveのtest再評価

## 17. 実験の段階構成

### Stage 0: 実装とunit test

- tabular adapter、hard cap、split manifest、式保存、test再評価を実装
- 小規模データで全手法が同じ入力・初期集団を使うことを検証

### Stage 1: controller-blind problem screen

- P03～P19から実行可能候補を固定率A1～A5で評価
- `q_W`、`t_90`、post-warm gain、runtimeで候補を絞る
- 早期収束問題を一つ、負の対照として意図的に残す

### Stage 2: state--action branch test

- checkpoint分岐で状態ごとの率反応を確認
- 高突然変異が全状態で最良なら、「長いが適応不要」と分類する

### Stage 3: tuning

- 問題、primitive、split、HV参照点を固定
- tuning seedsだけでbest fixed、BO hyperparameters、warm-up variantを決める
- この時点でprotocolをfreezeする

### Stage 4: confirmatory experiment

- 未使用paired seedsでcore 6手法を比較
- testはこの段階で初めて主要評価へ使う
- secondary手法は計算予算に応じて追加する

## 18. 暫定的な最終4問題案

pilot前に一案を置くなら、次が最もバランスがよい。

1. P08 UBall5D: 既知真値、外挿、長期合成問題
2. P14 Airfoil: MOGPのevolvability低下という機序stress
3. P15 Concrete: 公開実データ上の独立確認
4. P01 Friedman-I: 早期収束する負の対照

前回案との連続性をより強くする場合は、P15 ConcreteとP05 CCPPをcontroller-blind pilotで競わせ、基準を満たした方を3番目へ採用する。Auto MPGはadapter開発・pilot結果として付録に残す。計算とデータ許諾が整えばTowerを第5のstress testに加える。

この構成の意味は次である。

```text
既知真値・外挿      -> UBall5D
MOGP固有の縮退機序 -> Airfoil
実データ外的妥当性 -> Concrete または CCPP
適応不要の境界条件 -> Friedman-I
```

## 19. 最終選択時の判断表

候補ごとに次を埋め、先に定めた基準で選ぶ。

| 項目 | 測定値 | 合格基準 |
|---|---:|---:|
| 初期から最終の中央値HV改善 |  | `>=0.05` |
| warm-up改善比 `q_W` |  | `<=0.70`、優先`<=0.50` |
| 中央値 `t_90` |  | `>=54`、優先`>=90` |
| post-warm改善seed率 |  | `>=70%` |
| checkpoint別の最良率変化 |  | 2状態以上で差 |
| oversize/invalid率 |  | 事前上限内 |
| 1 run runtime |  | 計算予算内 |
| 公開性・license・hash |  | 全て固定可能 |
| test leakage |  | なし |

## 20. 採用しない設計

- 目的関数やデータを世代途中で変更するdynamic problem
  - 現在の永続archiveに古い目的値が残り、HVと報酬を比較できなくなる
- noiseを増やし、見かけ上収束しない状態を作ること
  - BOが改善可能性でなくランダム揺らぎを追う
- populationを極端に小さくして人工的に遅くすること
  - 問題難度ではなくアルゴリズム弱体化になる
- test結果や提案法の勝敗を見て問題を選ぶこと
  - selection biasになる
- tree size 100を正規化上限だけにして長世代化すること
  - bloatと計算時間が制御不能になる

## 21. 参照文献

- [R10] Dou, T., & Rockett, P. I. (2018). *Comparison of semantic-based local search methods for multiobjective genetic programming*. Genetic Programming and Evolvable Machines, 19, 535–563. https://doi.org/10.1007/s10710-018-9325-4
- [R24] Niehaus, J., & Banzhaf, W. (2001). *Adaption of Operator Probabilities in Genetic Programming*. EuroGP 2001, 325–336. https://doi.org/10.1007/3-540-45355-5_25
- [R25] Oh, S., Suh, W.-H., & Ahn, C.-W. (2021). *Self-Adaptive Genetic Programming for Manufacturing Big Data Analysis*. Processes, 9(11), 1931. https://doi.org/10.3390/pr9111931
- [R28] Harrison, J., Alderliesten, T., & Bosman, P. A. N. (2025). *A Better Multi-Objective GP-GOMEA - But do we Need it?* GECCO '25 Companion. https://doi.org/10.1145/3712255.3734302
- [R29] White, D. R., et al. (2013). *Better GP Benchmarks: Community Survey Results and Proposals*. Genetic Programming and Evolvable Machines, 14(1), 3–29. https://doi.org/10.1007/s10710-012-9177-2
- [R30] Liu, D., Virgolin, M., Alderliesten, T., & Bosman, P. A. N. (2022). *Evolvability Degeneration in Multi-Objective Genetic Programming for Symbolic Regression*. GECCO '22, 973–981. https://doi.org/10.1145/3512290.3528787
