# GP性能評価におけるHV-AUC文献調査ログ

- 調査日: 2026-06-12
- 目的: GP / MOGP の性能評価において `HV-AUC` またはそれに近い「HV推移曲線の面積・平均HV」を用いている文献を探す
- 参照した仕様: `references/reference_workflow_spec.md`

## 検索クエリ

- `"genetic programming" "HV-AUC"`
- `"genetic programming" "hypervolume AUC"`
- `"multiobjective genetic programming" "hypervolume" "AUC"`
- `"symbolic regression" "HV-AUC"`
- `"genetic programming" "area under" "hypervolume"`
- `"multi-objective genetic programming" "area under" "hypervolume"`
- `"hypervolume" "area under the curve" "multi-objective"`
- `"hypervolume AUC" "evolutionary algorithm"`
- `"area under hypervolume" "evolutionary algorithm"`
- `"hypervolume over time" "genetic programming"`
- `"mean hypervolume" "genetic programming"`
- `"average hypervolume" "genetic programming"`

## 結論

現時点の検索では，**GP / MOGP の性能評価で `HV-AUC` という名称の指標を直接用いている文献は確認できなかった**。

ただし，MOGP / GP-GOMEA において，最終HVだけでなく，平均HVを世代方向・時間方向にプロットして性能差を論じる文献は確認できた。

## 採用文献

### [R28] A Better Multi-Objective GP-GOMEA - But do we Need it

- 分類: C/D
- 採用理由:
- Symbolic Regression における multi-objective GP-GOMEA の性能評価で average hypervolume を用いている
- `Average Hypervolume per generation` と `Average Hypervolume over time` を比較しており，HVの立ち上がりや時間方向の性能差を読む発想が本研究のHV-AUC利用に近い
- 注意:
- `HV-AUC` という名称や，HV曲線の面積を数値指標として定義しているわけではない
- よって，本研究では「HV-AUCの直接根拠」ではなく，「GP性能評価においてHV推移・時間方向のHVを見る近接根拠」として扱う

## 保留・不採用判断

- Galvan et al. 系の Semantics in Multi-objective Genetic Programming:
- MOGPでHVを評価指標として用いている点では関連するが，現時点でHV-AUCまたはHV曲線面積の利用は確認できていない
- Liu et al. (2022) Evolvability Degeneration in Multi-Objective Genetic Programming for Symbolic Regression:
- MOGPの停滞・早期支配・evolvability低下を議論する重要文献だが，HV-AUCを用いた性能評価文献ではない
- Anytime hypervolume / evolutionary algorithm 系:
- MOEA全般では「時間方向にHVを見る」考え方の文献があるが，GP性能評価に限定すると直接性が弱いため今回は正式採用しない

## レジュメでの安全な書き方

現在の文献状況では，HV-AUCは次のように説明するのが安全である。

```latex
HV-AUCは，既存の多目的評価指標であるHVを世代方向に集約した本稿の補助指標である．
```

さらに文献を付ける場合は，HVそのものの根拠には Guerreiro et al. [R17] を用い，GPでHV推移を性能比較に使う近接事例として Harrison et al. [R28] を用いるのが妥当である。
