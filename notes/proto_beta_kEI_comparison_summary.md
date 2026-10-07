# ver_beta_kEI / ver_beta_k / ver_beta_EI 比較結果まとめ

- 作成日: 2026-05-29
- 対象: `bo_current`, `ver_beta_k`, `ver_beta_EI`, `ver_beta_kEI`
- 初回実験名: `ver_beta_kEI_20260529_120723`
- 4 条件切り分け実験名: `ver_beta_kEI_20260529_122615`

## 1. 比較した内容

`ver_beta_kEI` は、現行 BO 制御器に対して次の 2 点を変更した版である。

1. warm-up を sequential から interleaved に変更した
2. EI の改善基準を k ごとの best reward から全 k 共通の best reward に変更した

現行版は次である。

```text
bo_current:
  warm-up = sequential
  EI best = per_k
```

改善案は次である。

```text
ver_beta_kEI:
  warm-up = interleaved
  EI best = global
```

ここで sequential warm-up とは、概ね次のように k を順番に埋める方法である。

```text
k=1, k=1, k=3, k=3, k=5, k=5
```

interleaved warm-up とは、次のように k を混ぜて試す方法である。

```text
k=1, k=3, k=5, k=1, k=3, k=5
```

global EI とは、各 k が自分自身の過去最高報酬だけを見るのではなく、全 k を含む過去最高報酬を基準に Expected Improvement を計算する方法である。

## 2. 実験条件

proto_alpha と同じ小規模条件で比較した。

| 項目 | 値 |
|---|---:|
| 問題 | Friedman-I, Poly-10 |
| seed | 0, 1, 2 |
| population size | 24 |
| total generations | 30 |
| evaluations / run | 720 |
| archive key | topology_value |
| 比較手法 | bo_current, ver_beta_kEI |

出力先は次である。

```text
outputs/symbolic_regression_alpha_bo_compare
```

## 3. Friedman-I の結果

| method | final archive HV mean | final diversity mean | archive size mean |
|---|---:|---:|---:|
| bo_current | 0.784951 | 0.665762 | 17.67 |
| ver_beta_kEI | 0.771838 | 0.720279 | 21.00 |

Friedman-I では、`ver_beta_kEI` は現行版より平均 final archive HV が低かった。

一方で、final diversity は `ver_beta_kEI` の方が高かった。また archive size も `ver_beta_kEI` の方が大きかった。

この結果は、`ver_beta_kEI` が現行版より探索範囲を広く保った一方で、その探索が最終 HV の押し上げには十分つながらなかった可能性を示している。

seed 別に見ると、`ver_beta_kEI` は seed 1 では現行版よりわずかに良いが、seed 0 と seed 2 では現行版より低い。

| seed | bo_current HV | ver_beta_kEI HV |
|---:|---:|---:|
| 0 | 0.776370 | 0.744859 |
| 1 | 0.776453 | 0.778391 |
| 2 | 0.802030 | 0.792264 |

## 4. Poly-10 の結果

| method | final archive HV mean | final diversity mean | archive size mean |
|---|---:|---:|---:|
| bo_current | 0.799458 | 0.569561 | 4.00 |
| ver_beta_kEI | 0.799690 | 0.330284 | 2.33 |

Poly-10 では、`ver_beta_kEI` の final archive HV は現行版よりわずかに高かった。

ただし差は非常に小さく、Poly-10 はそもそも HV が初期から飽和気味である。そのため、HV の微小差を強い改善とは解釈しない方がよい。

むしろ重要なのは、`ver_beta_kEI` で diversity が大きく低下した点である。特に seed 2 では後半に diversity がほぼ 0 に落ちており、global EI が短期的な報酬改善または一点集中を強めた可能性がある。

## 5. k の選ばれ方の変化

Friedman-I の k 系列を見ると、現行版は warm-up で次のように始まる。

```text
bo_current:
  k=1, 1, 3, 3, 5, 5, ...
```

一方、`ver_beta_kEI` は意図通り次のように始まる。

```text
ver_beta_kEI:
  k=1, 3, 5, 1, 3, 5, ...
```

したがって、warm-up の時系列偏りを減らすという実装上の目的は達成できている。

ただし、global EI を入れたことで、以降の k 選択がより強く「全体で一番良い報酬を超えられそうか」に引っ張られる。その結果、探索の広がりや diversity の扱いが変化した可能性がある。

## 6. 4番の制御履歴解析から分かること

proto_alpha の制御履歴解析では、Friedman-I で次の傾向が見えた。

| k | mean hv_rate | mean delta_hv | mean delta_diversity |
|---:|---:|---:|---:|
| 1 | 0.019844 | 0.019844 | -0.043511 |
| 3 | 0.010715 | 0.032146 | -0.068649 |
| 5 | 0.011347 | 0.056735 | 0.078928 |

この結果から、短い k は世代あたり改善に強く、長い k は区間全体の改善と diversity 回復に寄与する可能性がある。

しかし今回の `ver_beta_kEI` 比較では、k を公平に試しやすくしても最終 HV は必ずしも上がらなかった。これは、`k` の試し方だけでなく、報酬設計、EI 基準、diversity 項の重みづけが相互に効いていることを示している。

## 7. 考察

`ver_beta_kEI` は「k の比較を公平にする」という設計上の改善としては妥当である。

一方で、小規模実験の結果だけを見ると、Friedman-I では現行版の方が HV は高かった。したがって、現時点では `ver_beta_kEI` をそのまま正規版に置き換えるのではなく、次のように位置づけるのがよい。

```text
ver_beta_kEI:
  k の比較公平性を高める ablation / 候補版
```

特に重要なのは、warm-up 改善と global EI 改善を同時に入れたため、どちらが効いたのか、あるいはどちらが悪影響を出したのかを切り分けられていない点である。

次に進むなら、次の 2 条件を追加して切り分けるべきである。

```text
bo_interleaved_only:
  warm-up = interleaved
  EI best = per_k

bo_globalEI_only:
  warm-up = sequential
  EI best = global
```

これにより、Friedman-I で HV が下がった原因が、interleaved warm-up なのか global EI なのかを確認できる。

## 8. 現時点の結論

現時点では、次の結論が妥当である。

1. 4番の解析により、Friedman-I では `k=1` と `k=5` が異なる役割を持つ可能性が見えた。
2. `ver_beta_kEI` は warm-up の k 順序を意図通り改善できた。
3. しかし Friedman-I では、`ver_beta_kEI` は現行版より final HV が下がった。
4. 一方で、Friedman-I の diversity は `ver_beta_kEI` の方が高くなった。
5. Poly-10 では HV はわずかに上がったが、diversity が大きく下がり、問題自体も飽和気味であるため強い結論は出せない。
6. 次は `interleaved only` と `global EI only` を追加し、warm-up と EI の効果を切り分ける必要がある。

## 9. warm-up と EI の切り分け実験

前節の結論を受けて、次の 4 条件を同一 seed、同一問題、同一評価回数で比較した。

| method | warm-up | EI best |
|---|---|---|
| `bo_current` | sequential | per-k |
| `ver_beta_k` | interleaved | per-k |
| `ver_beta_EI` | sequential | global |
| `ver_beta_kEI` | interleaved | global |

出力先は次である。

```text
outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_20260529_122615
outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_20260529_122615
```

### 9.1 Friedman-I の結果

| method | final archive HV mean | final archive HV std | final diversity mean | archive size mean |
|---|---:|---:|---:|---:|
| `bo_current` | 0.784951 | 0.012076 | 0.665762 | 17.67 |
| `ver_beta_k` | 0.785831 | 0.005708 | 0.689566 | 14.00 |
| `ver_beta_EI` | 0.783829 | 0.010490 | 0.659011 | 15.67 |
| `ver_beta_kEI` | 0.771838 | 0.019900 | 0.720279 | 21.00 |

Friedman-I では、warm-up のみを interleaved にした `ver_beta_k` が平均 final archive HV で最も高く、標準偏差も最も小さかった。差は大きくないが、`k` の warm-up 順序を公平化する変更は少なくとも悪化要因ではなく、安定性の改善に寄与している可能性がある。

一方、EI のみを global best にした `ver_beta_EI` は `bo_current` とほぼ同等であった。`ver_beta_kEI` は diversity と archive size は大きいが、HV は最も低かった。このため、global EI と interleaved warm-up を同時に入れると、Friedman-I では探索範囲は広がる一方、短期的な Pareto front 押し上げが弱くなる可能性がある。

seed 別に見ると、`ver_beta_k` は seed 0 と seed 1 で `bo_current` を上回り、seed 2 では下回った。したがって、現時点では強い優位性ではなく、「有望な候補」として扱うのが妥当である。

### 9.2 Poly-10 の結果

| method | final archive HV mean | final archive HV std | final diversity mean | archive size mean |
|---|---:|---:|---:|---:|
| `bo_current` | 0.799458 | 0.000554 | 0.569561 | 4.00 |
| `ver_beta_k` | 0.799521 | 0.000346 | 0.368478 | 2.33 |
| `ver_beta_EI` | 0.799183 | 0.000395 | 0.557039 | 3.67 |
| `ver_beta_kEI` | 0.799690 | 0.000355 | 0.330284 | 2.33 |

Poly-10 では全手法の HV が 0.799 付近に集中しており、現行設定では HV による BO 制御器比較が難しい。`ver_beta_kEI` が平均 HV では最も高いが、差はごく小さい。

重要なのは、interleaved warm-up を含む `ver_beta_k` と `ver_beta_kEI` で diversity と archive size が低下している点である。特に seed 2 では diversity が 0 まで低下しており、探索が単一構造または非常に近い構造へ集中した可能性がある。Poly-10 は今回の設定では初期から HV が飽和しやすいため、BO 制御器調整の主判断材料にはしにくい。

### 9.3 切り分けから分かること

今回の 4 条件比較から、次のように整理できる。

1. `ver_beta_k` は Friedman-I で HV 平均と安定性をわずかに改善したため、warm-up の interleaved 化は有望である。
2. `ver_beta_EI` は単独では大きな改善を示さず、少なくとも今回の小規模条件では global EI の効果は限定的である。
3. `ver_beta_kEI` は diversity を高める方向には働くが、Friedman-I では HV が低下したため、両方を単純に組み合わせれば良いわけではない。
4. Poly-10 は HV が飽和気味で、BO 制御器の細かな違いを見るには問題設定の難易度調整が必要である。

### 9.4 次の方針

現段階では、`ver_beta_k` を次の本実験候補として優先し、`ver_beta_EI` と `ver_beta_kEI` は ablation 用に残すのがよい。

ただし seed が 3 本と少ないため、次に進む場合は次を確認する。

- Friedman-I で seed 数を増やし、`ver_beta_k` の安定性改善が偶然でないか確認する。
- Poly-10 は難易度を上げるか、BO 制御器比較からは補助的位置づけにする。
- global EI は報酬スケールや k ごとの分布差に敏感な可能性があるため、採用するなら標準化 EI や k ごとの不確実性補正も検討する。

## 10. seed 別の追加可視化

全 seed を 1 枚に重ねた `hv_progress.png` と `diversity_progress.png` は全体傾向を見るには便利である。一方で、4 手法 × 3 seed の 12 本の線が同時に表示されるため、個別 seed 内でどの手法がどのように違うかは読み取りにくい。

そこで、既存図は残したまま、各 seed ごとに次の 3 指標を 1 枚にまとめた図を追加した。

- archive HV
- population diversity
- BO が選択した更新周期 `k`

追加図は次の形式で保存した。

```text
seedwise_hv_diversity_k_seed_0.png
seedwise_hv_diversity_k_seed_1.png
seedwise_hv_diversity_k_seed_2.png
```

保存先は以下である。

```text
outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_20260529_122615
outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_20260529_122615
```

この図では、1 枚あたり同一 seed の 4 手法のみを比較する。これにより、初期集団の違いによるばらつきを固定した上で、warm-up 改善と EI 改善が HV、多様性、`k` 選択に与える影響を確認しやすくなる。
