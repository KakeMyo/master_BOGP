# 問題設定文献 調査メモ

- 作成日: 2026-05-26
- 更新日: 2026-10-01
- 位置づけ: 本実験の問題設定候補を選ぶための文献メモ
- 注意: このフォルダは原則として正式採用前の候補置き場である。2026-09-03に正式採用したPS02=[R29]、PS04=[R30]だけは例外とする
- 詳細: [problem_setting_sources.md](problem_setting_sources.md)

2026-10-01の追加整理:

- [問題設定用文献PDF・メタデータの目的別フォルダ](../../references/problem_settings/README.md)に7本を確保（既存6本の閲覧コピー、新規取得1本）
- [手動取得待ち2論文](../../references/problem_settings/manual_download_list.md)
- [次に実装・pilotへ進める5候補](../../notes/thesis_problem_shortlist_5.md)
- このフォルダの旧候補資料・以前の案は削除していない。最新仕様は上記5候補メモと長期探索型メモを参照する

2026-09-03の長期探索型問題調査では、次を追加した。

- 全候補・pilot・本番構成: [thesis_long_horizon_problem_setting_options.md](../../notes/thesis_long_horizon_problem_setting_options.md)
- 検索・採否ログ: [long_horizon_mogp_search_log.md](long_horizon_mogp_search_log.md)
- PS02 White et al. (2013) と PS04 Liu et al. (2022) は本文・DOI・取得元を再確認し、正式文献 [R29]、[R30] へ昇格した
- 候補フォルダの原ファイルは履歴保持のため残し、正式版を `references/` へ複製した

## 1. 先に結論

現時点で、本研究の提案手法の有効性を見せやすい問題設定は、次の順で有力である。

| 優先 | 問題設定 | 目的関数例 | 良い点 | 注意点 |
|---|---|---|---|---|
| 1 | symbolic regression の精度・複雑さトレードオフ | 誤差最小化、木サイズ最小化 | 実装しやすい、Pareto front が説明しやすい、GP/MOGP 文献が多い | toy 問題だけにすると弱い |
| 2 | MOGP symbolic regression の evolvability / diversity 問題 | 誤差最小化、複雑さ最小化 | NSGA-II で低複雑度個体が過剰複製される問題が報告されており、提案法の多様性制御と相性がよい | データセット選定を丁寧にする必要がある |
| 3 | 機械振動吸収器・ばねダンパ構造探索 | 部品数最小化、応答積分最小化 | 現在の構造探索コードと近く、構造探索研究として説明しやすい | 実装・検証が symbolic regression より重い |
| 4 | shape-constrained symbolic regression | 予測誤差、制約違反、木サイズ | 工学的 prior knowledge を入れられ、3 目的拡張に向く | 3 目的 HV 対応がまだ必要 |
| 5 | 構造 topology optimization | compliance、材料量 | Pareto front が自然で、構造最適化として説得力がある | GP 表現への落とし込みが大きめ |

## 2. 本研究に最も合う最小構成

まずは次の 2 系統で pilot 実験を組むのがよい。

### A. 回帰系: MOGP symbolic regression

目的関数:

```text
f_1(T) = validation error または test error
f_2(T) = tree size または model complexity
```

採用理由:

- 2 目的のまま現在の exact HV が使える。
- 木サイズと予測精度のトレードオフが直感的で、発表で説明しやすい。
- 多様性低下、bloat、低複雑度個体の過剰複製など、提案法の状態依存制御が効きそうな現象が文献で報告されている。
- `template` 問題から自然に拡張できる。

候補データ:

- 最初は小さな合成関数を 2--3 個。
- 次に SRBench / PMLB 系の regression dataset を数個。
- 本実験では「簡単・中程度・難しい」を混ぜる。

### B. 構造系: mechanical vibration absorber / spring-damper structural search

目的関数:

```text
f_1(T) = terminal element count
f_2(T) = impulse response integral または vibration response score
```

採用理由:

- 既存の `StructuralSearchProblem` と近い。
- 木構造・部品値・構造キー `topology_value` の意味がはっきり出る。
- 「望ましい Pareto front を得る」という研究目的と相性がよい。

注意点:

- 現在の小実験では HV が早く飽和しやすい可能性がある。
- 参照点、探索深さ、部品値範囲、評価時間刻みを調整して、固定率 GP との差が出る難易度にする必要がある。

## 3. 採用判断の基準

本研究では、単に有名な benchmark よりも、次の条件を満たす問題を優先する。

- Pareto front が自然に定義できる。
- 探索初期、中盤、終盤で望ましい操作率が変わりそうである。
- 多様性維持と収束速度のトレードオフが発生しやすい。
- 固定率 GP との差を、HV、Diversity、archive size、control history で説明できる。
- 実装コストが大きすぎず、複数 seed を回せる。

## 4. 今回保存したファイル

PDF と HTML は、正式参考文献ではなく問題設定候補として保存した。

- `Genetic Programming Needs Better Benchmarks.pdf`
- `Better GP Benchmarks - Community Survey Results and Proposals.pdf`
- `Contemporary Symbolic Regression Methods and their Relative Performance.html`
- `Evolvability Degeneration in Multi-Objective Genetic Programming for Symbolic Regression.pdf`
- `Automated Synthesis of Mechanical Vibration Absorbers Using Genetic Programming.pdf`

ScienceDirect 等でメタデータ確認に留めた文献は、[problem_setting_sources.md](problem_setting_sources.md) に記録した。
