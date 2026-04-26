# 文献フォルダ

- 作成日: 2026-04-14
- 更新日: 2026-04-22
- 目的: 文脈付き BO による GP 操作率制御の研究に使う文献を、本文確認、保存、研究ノート反映まで一貫管理する
- 詳細仕様: [reference_workflow_spec.md](reference_workflow_spec.md)

## 現在の研究テーマ

交叉率 `p_c` と突然変異率 `p_m` を、文脈付きベイズ最適化で動的に調整する閉ループ型遺伝的プログラミング手法の設計と評価。

優先して集める文献は、以下に直接関係するものとする。

- GP の操作率、operator probability、adaptive parameter control
- 文脈付き BO、online algorithm configuration、進化計算のハイパーパラメータ制御
- 構造多様性、意味多様性、目的空間多様性
- bloat、program size、simplification
- 多目的 GP、HV、Pareto front、NSGA-II
- 実験比較、ベンチマーク、統計検定

## 現在の取得・保存ルール

- PDF とメタデータノートは、既存リンクを保つため `references/` 直下に保存する。
- PDF は、本文確認可能なオープンアクセス版または Elsevier / ScienceDirect 版を保存する。
- オープンアクセスで本文取得可能な文献と Elsevier / ScienceDirect から本文確認・取得可能な文献は同列の優先候補として扱う。
- 取得元だけで優先順位を決めず、研究テーマとの関連性、信頼性、有用性、入手可能性を総合的に見て採否を判断する。
- Elsevier 上で論文情報は確認できるが直接ダウンロードできない場合は、無理に自動取得せず、手動ダウンロード候補として検索しやすい情報を残す。
- 取得元は、出版社公式 OA、Elsevier / ScienceDirect、DOI リンク先、機関リポジトリ、arXiv 等の公的プレプリント、著者公開版を確認する。
- 著作権状態が不明な転載サイトや海賊版サイトは使わない。
- 本文を確認できないが重要な文献は `H: 保留` または `M: 手動取得候補` とし、メタデータノートのみ作る。この場合、本文中の具体的主張の根拠には使わない。
- ファイル名は論文タイトルベースで統一する。
- 新規文献には作業用文献番号 `[Rxx]` を付け、研究ノート内でも同じ番号を使う。
- 引用数を書く場合は、参照元 DB と確認日を併記する。

## 文献番号台帳

| 番号 | 分類 | 著者・年 | 文献 | 本文確認 | 主用途 |
|---|---|---|---|---|---|
| [R01] | B | Burlacu, Yang, Affenzeller (2024) | [Population diversity and inheritance in genetic programming for symbolic regression.md](Population%20diversity%20and%20inheritance%20in%20genetic%20programming%20for%20symbolic%20regression.md) | PDF 保存済み | 構造類似度、意味類似度、多様性定義 |
| [R02] | D | Vanneschi, Castelli, Silva (2014) | [A survey of semantic methods in genetic programming.md](A%20survey%20of%20semantic%20methods%20in%20genetic%20programming.md) | メタデータ確認 | semantic GP の用語整理 |
| [R03] | D | Moraglio, Krawiec, Johnson (2012) | [Geometric Semantic Genetic Programming.md](Geometric%20Semantic%20Genetic%20Programming.md) | PDF 保存済み | semantic GP の基礎 |
| [R04] | B | Nguyen et al. (2013) | [On the roles of semantic locality of crossover in genetic programming.md](On%20the%20roles%20of%20semantic%20locality%20of%20crossover%20in%20genetic%20programming.md) | メタデータ確認 | semantic locality と fitness cases |
| [R05] | D | Burke, Gustafson, Kendall (2004) | [Diversity in Genetic Programming - An Analysis of Measures and Correlation With Fitness.md](Diversity%20in%20Genetic%20Programming%20-%20An%20Analysis%20of%20Measures%20and%20Correlation%20With%20Fitness.md) | メタデータ確認 | GP 多様性指標の比較 |
| [R06] | B | Burks, Punch (2015) | [An Efficient Structural Diversity Technique for Genetic Programming.md](An%20Efficient%20Structural%20Diversity%20Technique%20for%20Genetic%20Programming.md) | メタデータ確認 | 構造多様性の効率的計算 |
| [R07] | B | Gustafson, Vanneschi (2008) | [Crossover-Based Tree Distance in Genetic Programming.md](Crossover-Based%20Tree%20Distance%20in%20Genetic%20Programming.md) | メタデータ確認 | 交叉と木距離の関係 |
| [R08] | B | Javed, Gobet, Lane (2022) | [Simplification of genetic programs - a literature survey.md](Simplification%20of%20genetic%20programs%20-%20a%20literature%20survey.md) | PDF 保存済み | bloat、size、simplification |
| [R09] | C | Deb et al. (2002) | [A fast and elitist multi-objective genetic algorithm - NSGA-II.md](A%20fast%20and%20elitist%20multi-objective%20genetic%20algorithm%20-%20NSGA-II.md) | メタデータ確認 | crowding distance、目的空間多様性 |
| [R10] | B | Dou, Rockett (2018) | [Comparison of semantic-based local search methods for multiobjective genetic programming.md](Comparison%20of%20semantic-based%20local%20search%20methods%20for%20multiobjective%20genetic%20programming.md) | PDF 保存済み | 多目的 GP、tree size と精度 |
| [R11] | D | Krawiec (2014) | [Genetic programming - where meaning emerges from program code.md](Genetic%20programming%20-%20where%20meaning%20emerges%20from%20program%20code.md) | PDF 保存済み | semantics の背景 |

## 新規追加時のチェックリスト

- [ ] 研究テーマ上の用途を A/B/C/D/M/H/R の分類で決めた
- [ ] DOI、出版社ページ、Elsevier / ScienceDirect 掲載ページ、機関リポジトリなど出典を確認した
- [ ] 本文確認可能な OA 版または Elsevier / ScienceDirect 版を探した
- [ ] PDF、URL、Elsevier 掲載ページ、または手動ダウンロード候補情報と `.md` メタデータノートを保存した
- [ ] Elsevier から直接ダウンロードできない場合は、タイトル、著者、年、掲載誌、巻号ページ、DOI、URL、要点、採用理由、想定利用箇所、推奨検索クエリを返した
- [ ] 文献番号台帳へ `[Rxx]` を追加した
- [ ] `notes/research_note.md` の参考文献章へ、参照箇所と参照内容を追記した
- [ ] 本文へ反映した場合は、該当文に `[Rxx]` を付けた
