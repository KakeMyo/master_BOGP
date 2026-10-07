# 構造探索の難しさに関する参考文献候補

- 作成日: 2026-05-26
- 状態: 候補整理のみ。まだ正式な参考文献番号は付けない。
- 方針: `references/` や BibTeX へ入れる前の一時置き場。

## 候補一覧

| 候補ID | 文献 | 主な役割 | 優先度 |
|---|---|---|---|
| SD01 | Malan and Engelbrecht (2013) | fitness landscape analysis 全体の地図 | 最優先 |
| SD02 | Jones and Forrest (1995) | FDC、評価値と最適解距離の相関 | 高 |
| SD03 | Tomassini et al. (2005) | FDC の GP への適用と限界 | 高 |
| SD04 | Vanneschi et al. (2004) | fitness cloud、NSC、GP problem hardness | 高 |
| SD05 | Vanneschi (2010) | GP における地形・難しさのチュートリアル | 高 |
| SD06 | He and Neri (2023) | Local Optima Network による GP 地形分析 | 高 |
| SD07 | Schweim et al. (2022) | GP 初期集団の sampling error | 中 |
| SD08 | Christensen and Oppacher (2002) | Koza computational effort の注意点 | 中 |
| SD09 | Lissovoi and Oliveto (2019) | GP の計算複雑性、可変長表現の難しさ | 中 |
| SD10 | Huband/Barone/While/Hingston (2005) | 多目的ベンチマークでの難しさ特徴 | 高 |
| SD11 | Verel et al. (2012) | Pareto local optima、MOO landscape | 高 |
| SD12 | Liu et al. (2022) | MOGP の evolvability degeneration | 高 |
| SD13 | Stadler et al. (2001) | neutrality と ruggedness | 中 |
| SD14 | Smith et al. (2002) | evolvability statistics | 中 |
| SD15 | Burlacu et al. (2024) | GP 構造・意味多様性、既存採用済み文献 | 高 |
| SD16 | Gustafson and Vanneschi (2008) | crossover-based tree distance | 中 |
| SD17 | Li and Yao (2019) | 多目的解集合品質評価 | 中 |

## SD01: Malan and Engelbrecht (2013)

- Citation: Malan, K. M., & Engelbrecht, A. P. (2013). *A survey of techniques for characterising fitness landscapes and some possible ways forward*. Information Sciences, 241, 148-163. https://doi.org/10.1016/j.ins.2013.04.015
- URL: https://repository.up.ac.za/bitstream/2263/37155/1/Malan_Survey_2013.pdf
- 種別: サーベイ
- 採用候補理由:
  - 「単一の problem hardness 指標は難しい」という本研究の整理に最も使いやすい。
  - ruggedness、neutrality、deception、evolvability、local optima、funnels などを体系化している。
  - landscape は「解集合、近傍/距離、fitness function」の組で決まるという説明が、GP の構造探索に非常に合う。
- 本研究での使い道:
  - 構造探索の難しさを単一スコアではなく特徴量群として扱う根拠。
  - 既存の `D_struct`、`DeltaHV`、停滞、bloat をオンラインな landscape proxy として説明する土台。
  - FDC や NSC を「主指標」ではなく「補助指標」と位置づける根拠。
- 注意:
  - 一般的な fitness landscape analysis の文献なので、GP 構造探索へ適用する際は距離・近傍の定義を明記する必要がある。

## SD02: Jones and Forrest (1995)

- Citation: Jones, T., & Forrest, S. (1995). *Fitness Distance Correlation as a Measure of Problem Difficulty for Genetic Algorithms*. Santa Fe Institute Working Paper 95-02-022.
- URL: https://ideas.repec.org/p/wop/safiwp/95-02-022.html
- PDF: https://sfi-edu.s3.amazonaws.com/sfi-edu/production/uploads/sfi-com/dev/uploads/filer/bf/eb/bfeb9cb0-100f-44d9-a35f-e95243dba350/95-02-022.pdf
- 種別: 基礎文献
- 採用候補理由:
  - Fitness Distance Correlation (FDC) の元文献。
  - 評価値が最適解への距離をどれだけ示しているか、という直感が分かりやすい。
- 本研究での使い道:
  - 構造探索の「評価値が良い方向を示しているか」の候補指標。
  - `sample best` を参照点にした FDC_to_best_sample の補助分析。
- 注意:
  - 真の最適解が必要になる。
  - 多目的問題では品質をスカラー化する必要がある。
  - FDC は万能ではなく、相関で表せない構造を見落とす。

## SD03: Tomassini et al. (2005)

- Citation: Tomassini, M., Vanneschi, L., Collard, P., & Clergue, M. (2005). *A study of fitness distance correlation as a difficulty measure in genetic programming*. Evolutionary Computation, 13(2), 213-239. https://doi.org/10.1162/1063656054088549
- URL: https://sonar.ch/global/documents/54720
- 種別: GP 向け FDC 文献
- 採用候補理由:
  - FDC を GP の problem difficulty に適用した文献。
  - FDC が有用な場合と、矛盾した示唆を出す場合の両方を扱っている。
- 本研究での使い道:
  - FDC を構造 GP に持ち込む際の根拠。
  - FDC を主張の中心ではなく補助指標にする理由。
- 注意:
  - 本文入手状況は要確認。現時点ではメタデータ確認候補。

## SD04: Vanneschi et al. (2004)

- Citation: Vanneschi, L., Clergue, M., Collard, P., Tomassini, M., & Verel, S. (2004). *Fitness clouds and problem hardness in genetic programming*. GECCO 2004, 690-701. https://doi.org/10.1007/978-3-540-24855-2_76
- URL: https://boa.unimib.it/handle/10281/13553
- PDF candidate: https://www.cs.york.ac.uk/rts/docs/GECCO_2004/Conference%20proceedings/papers/3103/31030690.pdf
- 種別: GP problem hardness 文献
- 採用候補理由:
  - GP の fitness cloud と Negative Slope Coefficient (NSC) を提示。
  - FDC と違い、必ずしも真の最適解を前提にしない方向の難しさ指標として使いやすい。
- 本研究での使い道:
  - mutation/crossover 近傍の improvement probability を測る設計根拠。
  - 終盤で改善しにくい品質帯を可視化する分析。
- 注意:
  - NSC はサンプル設計と近傍定義に依存する。

## SD05: Vanneschi (2010)

- Citation: Vanneschi, L. (2010). *Fitness landscapes and problem hardness in genetic programming*. GECCO 2010 Specialized Techniques and Applications Tutorials, 2711-2738. https://doi.org/10.1145/1830761.1830916
- URL: https://gpbib.pmacs.upenn.edu/gpbib.cs.ucl.ac.uk/gp-html/Vanneschi_2010_geccocomp.html
- 種別: チュートリアル
- 採用候補理由:
  - GP では fitness landscape の定義自体が難しいことを明確に述べている。
  - FDC、NSC、neutrality、subtree crossover based distance など、今回の論点がまとまっている。
- 本研究での使い道:
  - 「GP の構造探索では近傍・距離・演算子の定義が難しさ指標そのものに影響する」という説明。
  - 関連研究の導入。
- 注意:
  - チュートリアルなので、個別指標の根拠には元論文も併用した方がよい。

## SD06: He and Neri (2023)

- Citation: He, Y., & Neri, F. (2023). *Fitness Landscape Analysis of Genetic Programming Search Spaces with Local Optima Networks*. GECCO '23 Companion, 2056-2063. https://doi.org/10.1145/3583133.3596305
- URL: https://openresearch.surrey.ac.uk/esploro/outputs/conferenceProceeding/Fitness-Landscape-Analysis-of-Genetic-Programming/99928603102346
- 種別: 近年の GP landscape 分析
- 採用候補理由:
  - tree-based GP search space を Local Optima Network、FDC、neutrality、ruggedness で分析している。
  - parity、symbolic regression、artificial ant の違いを、地形特性として整理している。
- 本研究での使い道:
  - 構造 GP に対して local optima や deception を調べる実例。
  - small-depth enumeration や近傍サンプル分析を将来行う根拠。
- 注意:
  - Local Optima Network は重いので、本研究では最初は近似指標にとどめるのが現実的。

## SD07: Schweim et al. (2022)

- Citation: Schweim, D., Wittenberg, D., & Rothlauf, F. (2022). *On sampling error in genetic programming*. Natural Computing, 21, 173-186. https://doi.org/10.1007/s11047-020-09828-w
- URL: https://link.springer.com/article/10.1007/s11047-020-09828-w
- 種別: GP 初期化・サンプリング
- 採用候補理由:
  - GP 初期集団の代表性と sampling error を扱う。
  - 大きな探索空間に対して小さな population が偏ったサンプルになり得る点が、構造探索の初期化問題に対応する。
- 本研究での使い道:
  - 初期集団多様性、subtree coverage、unique structure ratio の根拠。
  - population size と構造探索の難しさの関係。
- 注意:
  - 直接の problem hardness 指標というより、探索開始時の信頼性・被覆度の文献。

## SD08: Christensen and Oppacher (2002)

- Citation: Christensen, S., & Oppacher, F. (2002). *An Analysis of Koza's Computational Effort Statistic for Genetic Programming*. EuroGP 2002, LNCS 2278, 182-191. https://doi.org/10.1007/3-540-45984-7_18
- URL: https://gpbib.cs.ucl.ac.uk/gp-html/christensen_2002_EuroGP.html
- 種別: GP 実験評価
- 採用候補理由:
  - Koza の computational effort 統計量を分析し、過小評価の可能性を指摘している。
- 本研究での使い道:
  - `time/evaluations to target` を難しさ指標にする際の注意文献。
  - 成功率と評価回数を併記する理由。
- 注意:
  - 古い文献だが、GP の実験指標としては今も説明しやすい。

## SD09: Lissovoi and Oliveto (2019)

- Citation: Lissovoi, A., & Oliveto, P. S. (2019). *Computational Complexity Analysis of Genetic Programming*. arXiv:1811.04465. https://doi.org/10.48550/arXiv.1811.04465
- URL: https://arxiv.org/abs/1811.04465
- 種別: 理論概観
- 採用候補理由:
  - GP は可変長表現と評価品質の扱いにより、通常の関数最適化より複雑になると整理している。
- 本研究での使い道:
  - 構造探索 GP の理論的な難しさ背景。
  - 「木構造を進化させること自体が通常の連続最適化と違う」説明。
- 注意:
  - 本研究の具体指標には直接つながりにくいので、背景向け。

## SD10: Huband/Barone/While/Hingston (2005)

- Citation: Barone, L., While, L., Huband, S., & Hingston, P. (2005). *A Scalable Multi-objective Test Problem Toolkit*. Lecture Notes in Computer Science, 3410, 280-295.
- URL: https://research-repository.uwa.edu.au/en/publications/a-scalable-multi-objective-test-problem-toolkit/
- 種別: 多目的ベンチマーク
- 採用候補理由:
  - WFG Toolkit は、多目的問題の難しさを bias、multi-modality、non-separability、Pareto front geometry などの特徴で組み合わせる。
- 本研究での使い道:
  - 多目的構造探索の難しさを「目的間競合」「非分離性」「front 形状」で説明する根拠。
  - 実験問題の特徴記述。
- 注意:
  - ベンチマーク設計文献なので、直接 GP の難しさではない。

## SD11: Verel et al. (2012)

- Citation: Verel, S., Liefooghe, A., Jourdan, L., & Dhaenens, C. (2012). *Pareto Local Optima of Multiobjective NK-Landscapes with Correlated Objectives*. arXiv:1207.4452. https://doi.org/10.48550/arXiv.1207.4452
- URL: https://arxiv.org/abs/1207.4452
- 種別: 多目的 landscape 分析
- 採用候補理由:
  - 多目的 combinatorial optimization における Pareto local optima を扱う。
  - 問題次元、非線形性、目的数、目的間相関が Pareto local optima 数へ与える影響を分析。
- 本研究での使い道:
  - `pareto_local_optimum_ratio` を構造探索の難しさ指標候補にする根拠。
  - objective correlation を多目的難しさの一部として見る根拠。
- 注意:
  - NK landscape 文献なので、構造木 GP へは近傍定義を置き換えて適用する。

## SD12: Liu et al. (2022)

- Citation: Liu, D., Virgolin, M., Alderliesten, T., & Bosman, P. A. N. (2022). *Evolvability Degeneration in Multi-Objective Genetic Programming for Symbolic Regression*. arXiv:2202.06983. https://doi.org/10.48550/arXiv.2202.06983
- URL: https://arxiv.org/abs/2202.06983
- 種別: 多目的 GP
- 採用候補理由:
  - MOGP で低複雑度モデルが過剰複製される問題を、複雑度ごとの evolvability 不足として分析している。
- 本研究での使い道:
  - `terminal_count` や `tree_size` ごとの one-step improvement rate を見る根拠。
  - 「単純な構造ばかり残るが改善しない」という現象の説明。
- 注意:
  - symbolic regression 文脈なので、機械構造探索へは目的値を置き換える。

## SD13: Stadler et al. (2001)

- Citation: Stadler, P. F. et al. (2001). *Neutrality in fitness landscapes*. Applied Mathematics and Computation, 117(2-3), 321-350. https://doi.org/10.1016/S0096-3003(99)00166-6
- URL: https://www.sciencedirect.com/science/article/abs/pii/S0096300399001666
- 種別: neutrality
- 採用候補理由:
  - ruggedness と neutrality の関係を扱う基礎的文献。
- 本研究での使い道:
  - `neutral_ratio_eps`、`objective_duplicate_ratio`、`cap_hit_ratio` を plateau/neutrality の代理指標として説明する根拠。
- 注意:
  - 一般的 landscape 文献。GP 構造探索へは補助的に使う。

## SD14: Smith et al. (2002)

- Citation: Smith, T., Husbands, P., Layzell, P., & O'Shea, M. (2002). *Fitness landscapes and evolvability*. Evolutionary Computation, 10(1), 1-34. https://doi.org/10.1162/106365602317301754
- URL: https://pubmed.ncbi.nlm.nih.gov/11911781/
- 種別: evolvability
- 採用候補理由:
  - fitness landscape 周辺の evolvability statistics を扱う。
- 本研究での使い道:
  - one-step improvement rate、escape probability の概念的根拠。
- 注意:
  - 現時点ではメタデータ確認中心。本文確認できる版を探す。

## SD15: Burlacu et al. (2024)

- Citation: Burlacu, B., Yang, K., & Affenzeller, M. (2024). *Population diversity and inheritance in genetic programming for symbolic regression*. Natural Computing, 23, 531-566. https://doi.org/10.1007/s11047-022-09934-x
- Local note: `references/Population diversity and inheritance in genetic programming for symbolic regression.md`
- 種別: 既存採用済み GP 多様性文献
- 採用候補理由:
  - 構造類似度と意味類似度の定義が、本研究の `D_struct` と直接つながる。
- 本研究での使い道:
  - 構造多様性を難しさのオンライン proxy として扱う根拠。
  - 構造距離と意味距離の両方を見る拡張案。

## SD16: Gustafson and Vanneschi (2008)

- Citation: Gustafson, S., & Vanneschi, L. (2008). *Crossover-Based Tree Distance in Genetic Programming*. IEEE Transactions on Evolutionary Computation, 12(4), 506-524. https://doi.org/10.1109/TEVC.2008.915993
- Local note: `references/Crossover-Based Tree Distance in Genetic Programming.md`
- 種別: GP 構造距離
- 採用候補理由:
  - GP の木距離は、単なる見た目ではなく、交叉で到達しやすいかを反映すべきという視点がある。
- 本研究での使い道:
  - FDC や locality 指標で使う `d_struct` の候補。
  - subtree Jaccard 距離だけでよいか検討する際の比較文献。

## SD17: Li and Yao (2019)

- Citation: Li, M., & Yao, X. (2019). *Quality evaluation of solution sets in multiobjective optimisation: a survey*. ACM Computing Surveys, 52(2), Article 26. https://doi.org/10.1145/3300148
- Local note: `references/Quality evaluation of solution sets in multiobjective optimisation - a survey.md`
- 種別: 多目的解集合評価
- 採用候補理由:
  - 多目的解集合の品質を convergence、diversity、coverage などに分けて考える根拠。
- 本研究での使い道:
  - empirical difficulty を `final HV` だけでなく `HV-AUC`、spread、coverage と併記する根拠。
- 注意:
  - 問題の難しさ指標というより、結果評価の文献。

## 追加で探すとよい文献

以下はまだ深掘り候補。

- Information content / entropic measures of fitness landscapes
- Borenstein and Poli の information landscape hardness
- Exploratory landscape analysis (ELA) の多目的版
- GP における problem descriptors / predictors of expected performance
- 構造最適化・機械構造設計における infeasible ratio や simulation failure rate の扱い

## 正式採用するなら優先順

最初に採用するなら、以下の 8 本で十分に骨格が作れる。

1. SD01 Malan and Engelbrecht (2013)
2. SD02 Jones and Forrest (1995)
3. SD04 Vanneschi et al. (2004)
4. SD05 Vanneschi (2010)
5. SD06 He and Neri (2023)
6. SD10 Huband/Barone/While/Hingston (2005)
7. SD11 Verel et al. (2012)
8. SD12 Liu et al. (2022)

既存の `references/` と接続するなら、SD15、SD16、SD17 を補助として紐づける。
