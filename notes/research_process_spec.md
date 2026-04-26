# 研究の進め方 仕様書

- 作成日: 2026-04-22
- 対象研究: 文脈付き BO による GP の交叉率・突然変異率制御
- 主ノート: `notes/research_note.md`
- 参考文献ルール: `references/reference_workflow_spec.md`
- ブラッシュアップ別紙: `notes/research_brushup_2026-04-21.md`

## 1. 目的

本仕様書は、現在の研究を今後どの順序で進め、どの成果物を作り、どの時点で研究計画を見直すかを定める。

特に、更新済みの参考文献ルールに従い、オープンアクセス文献と Elsevier / ScienceDirect 文献を同列の候補として扱いながら、研究テーマ、提案手法、実験計画を継続的にブラッシュアップすることを目的とする。

本仕様書で扱う範囲は以下である。

- 先行研究調査の進め方
- 研究質問と仮説の管理
- 提案手法の設計判断
- 実装と実験の進め方
- 結果の記録と研究ノートへの反映
- 次に議論すべき未確定事項の整理

## 2. 研究の現在地

本研究の中心は、遺伝的プログラミングにおける交叉率 `p_c` と突然変異率 `p_m` を、固定値ではなく、進化状態に応じて更新される制御入力として扱うことである。

提案手法は、現在の GP 状態を文脈 `c_t` として観測し、文脈付き BO が次の操作率 `(p_c, p_m)` を制御区間ごとに提案する閉ループ構造である。

現時点で実装済みの主な部品:

| 項目 | 状態 | 主なファイル |
|---|---|---|
| 文脈付き BO 制御器 | 実装済み | `src/bogp/controller.py` |
| 閉ループ実行器 | 実装済み | `src/bogp/loop.py` |
| 文脈ベクトル正規化 | 実装済み | `src/bogp/context_metrics.py` |
| 報酬関数 | 実装済み | `src/bogp/objectives.py` |
| toy engine | 実装済み | `src/bogp/toy_engine.py` |
| 構造多様性・意味多様性 | 実装済み | `src/bogp/diversity.py` |
| 参考文献管理 | 整備済み | `references/README.md`, `references/reference_workflow_spec.md` |

現在の弱点:

- adaptive GP operator control の中核文献がまだ不足している
- evolutionary parameter control / online algorithm configuration の位置づけがまだ薄い
- contextual BO の理論的根拠となる文献がまだ不足している
- toy engine 上で baseline 比較がまだ整備されていない
- 実 GP への接続がまだ完了していない

## 3. 基本方針

研究は、次の原則で進める。

1. 文献、設計、実装、実験を分離せず、相互に更新する
2. 新しい設計判断をしたら、可能な限り対応する文献または実験根拠を残す
3. 文献は OA と Elsevier / ScienceDirect を同列候補として扱い、内容の有用性を優先する
4. Elsevier で直接取得できない文献は、手動ダウンロード候補として情報を残し、本文確認前は具体的主張の根拠にしない
5. 実験は一度に大きくしすぎず、toy engine、実 GP smoke、baseline 比較、ablation、統計評価の順に進める
6. 研究ノートは、結果だけでなく「なぜその判断をしたか」を残す

## 4. 研究単位

今後の作業は、次の 6 種類の研究単位に分ける。

| 種別 | 内容 | 完了条件 |
|---|---|---|
| Literature | 文献調査・取得・ノート反映 | `[Rxx]` 採番、用途記録、本文確認状況の明記 |
| Design | 提案手法・報酬・文脈・baseline の設計 | 研究ノートに設計理由と根拠を追記 |
| Implementation | コード実装 | テストまたは smoke run が通る |
| Experiment | 比較実験・ablation・感度分析 | 設定、seed、結果ファイル、要約を保存 |
| Analysis | 結果解釈・失敗分析 | 図表、観察、次の判断を研究ノートへ追記 |
| Writing | 論文・発表資料化 | 関連研究、手法、実験、考察へ反映 |

各研究単位は、必ず以下を残す。

- 何をしたか
- なぜそうしたか
- どのファイルや設定を変えたか
- 確認方法
- 次にやること

## 5. 文献調査の進め方

文献調査は、`references/reference_workflow_spec.md` に従う。

### 5.1 優先調査領域

直近では、以下を優先する。

| 優先度 | 分類 | 探す文献 | 目的 |
|---|---|---|---|
| 高 | A: 中核 | GP の adaptive operator probability / parameter control | 固定率から動的制御へ進む必然性を示す |
| 高 | A: 中核 | evolutionary parameter control / online algorithm configuration | 既存研究の中での位置づけを明確にする |
| 高 | B: 設計根拠 | contextual Bayesian optimization | 文脈付き BO を採用する根拠にする |
| 中 | C: 比較対象 | BO による evolutionary algorithm tuning | 文脈なし BO baseline の妥当性を支える |
| 中 | C: 比較対象 | EC/GP の統計比較方法 | run 数、検定、効果量、信頼区間を設計する |
| 中 | B: 設計根拠 | stagnation detection / restart / diversity recovery | 停滞指標と突然変異率再上昇の根拠にする |

### 5.2 採用時の記録

新規文献を採用候補にする場合は、以下を記録する。

- `Reference ID`: `[R12]` 以降
- 分類: `A/B/C/D/M/H/R`
- 本文確認状況: OA, Elsevier PDF, Elsevier manual candidate, metadata only
- 対応する研究質問: `RQ1` から `RQ5`
- 使い道: 背景、関連研究、手法根拠、baseline、評価指標、統計比較など

### 5.3 Elsevier 手動取得候補

Elsevier / ScienceDirect 上で有用性が高いが直接ダウンロードできない場合は、`M: 手動取得候補` とする。

この場合は、ユーザーに次の形式で返す。

```md
### 手動ダウンロード候補 [N]

- タイトル: `...`
- 著者: `...`
- 年: `...`
- 掲載誌: `...`
- 巻号・ページ: `...`
- DOI: `...`
- Elsevier掲載ページ: `...`
- 推奨検索クエリ1: `完全タイトル`
- 推奨検索クエリ2: `著者名 年 タイトル`
- 推奨検索クエリ3: `DOI`
- 要点: `...`
- 採用理由: `...`
- 想定利用箇所: `...`
```

本文取得前は、研究ノート本文の具体的な主張の根拠として使わない。

## 6. 研究質問と仮説の管理

現時点の研究質問は以下とする。

| ID | 研究質問 | 主な評価 |
|---|---|---|
| RQ1 | 提案法は固定率 GP や手設計スケジュールより解集合品質を改善するか | 最終 HV, HV-AUC |
| RQ2 | 文脈付き BO は文脈なし BO より安定してよい操作率を選べるか | run 間ばらつき, HV-AUC, 報酬時系列 |
| RQ3 | 構造多様性、停滞、bloat は制御判断に寄与するか | ablation, 多様性 collapse, 平均木サイズ |
| RQ4 | 学習された操作率時系列は探索段階ごとに解釈できるか | `p_c`, `p_m` の時系列 |
| RQ5 | BO 制御の計算オーバーヘッドは性能改善に見合うか | 実行時間, 評価回数, 制御器更新時間 |

仮説は、実験前に必ず明文化する。

- H1: 文脈付き BO は固定率 GP より最終 HV または HV-AUC を改善する
- H2: 文脈付き BO は文脈なし BO より run 間のばらつきが小さい
- H3: 構造多様性を文脈に含めると、多様性 collapse と長期停滞が減る
- H4: bloat ペナルティを入れると、性能を大きく落とさず平均木サイズを抑えられる
- H5: 制御区間 3 から 5 世代は、1 世代更新よりノイズと応答性のバランスが良い

実験結果が仮説に反した場合も、失敗として捨てず、どの仮定が崩れたかを記録する。

## 7. 研究フェーズ

### Phase 0: 文献と研究位置づけの補強

目的:

- 新規性の説明を強くする
- baseline の妥当性を支える
- 文脈付き BO の採用理由を文献で補強する

作業:

- adaptive GP operator control の文献を追加する
- evolutionary parameter control / online configuration の文献を追加する
- contextual BO の文献を追加する
- 各文献を `[Rxx]` として採番し、研究ノート第10章へ用途を追記する

完了条件:

- A: 中核文献が少なくとも 3 本追加されている
- B または C の文献が少なくとも 2 本追加されている
- 研究ノートの「先行研究上の不足箇所」が更新されている

### Phase 1: toy engine で baseline 比較を整える

目的:

- 実 GP 接続前に比較枠組みを固める
- 文脈付き BO と文脈なし BO の差を最小環境で確認する

比較対象:

- 固定率 GP
- 手設計スケジュール
- ランダム制御
- 文脈なし BO
- 文脈付き BO

記録:

- `generation`
- `p_c`, `p_m`
- `HV`, `DeltaHV`, `HV-AUC`
- `diversity`
- `stagnation`
- `tree_size`
- `reward`
- `elapsed_time`

完了条件:

- 同じ seed 群で全 baseline を実行できる
- 結果が CSV または JSONL で保存される
- 最低 5 seed の smoke 比較ができる

### Phase 2: 実 GP へ接続する

目的:

- toy engine ではなく、実際の GP 集団で提案法を検証する

初期対象:

- 記号回帰
- 目的 1: 予測誤差
- 目的 2: 木サイズ
- 評価: HV, HV-AUC, 平均木サイズ, 多様性, 停滞頻度

実装要件:

- DEAP 個体から prefix token を生成する
- `population_structural_diversity` を実集団に接続する
- `ClosedLoopRunner` のインターフェースで動かす
- 固定率 baseline と提案法を同じログ形式で比較する

完了条件:

- 1 問題、1 seed で最後まで実行できる
- 制御区間ごとの文脈、操作率、報酬が保存される
- 固定率 baseline と提案法の最小比較ができる

### Phase 3: ablation と感度分析

目的:

- 提案法のどの要素が効いているかを示す

ablation:

- 文脈なし BO
- `tau + HV + DeltaHV` のみ
- 構造多様性あり
- 停滞あり
- bloat あり
- 全文脈あり
- HV のみ報酬
- HV + 多様性報酬
- 全項入り報酬

感度分析:

- 制御区間: 1, 3, 5, 10
- warmup 点数
- candidate pool size
- smoothing factor
- 操作率更新幅制限あり・なし

完了条件:

- 少なくとも主要 ablation が同一 seed 群で比較されている
- 結果が主指標と補助指標の両方で整理されている

### Phase 4: 統計評価と論文化

目的:

- 実験結果を論文または発表資料として説明できる形にする

評価:

- 最終 HV
- HV-AUC
- 所定 HV 到達世代
- run 間ばらつき
- 停滞頻度
- 平均木サイズ
- 実行時間

記録:

- 平均
- 中央値
- 信頼区間
- 効果量
- seed ごとの個別結果
- 代表 run の時系列図

完了条件:

- RQ1 から RQ5 に対して、支持、不支持、保留の判断が書ける
- 成功例だけでなく失敗例も説明できる
- 論文構成案に結果を配置できる

## 8. 実験ログ仕様

実験ログは、あとで比較・図表化できる形式で保存する。

推奨ファイル:

- `results/<experiment_name>/config.json`
- `results/<experiment_name>/runs.csv`
- `results/<experiment_name>/interval_log.csv`
- `results/<experiment_name>/summary.md`

`interval_log.csv` の推奨列:

```text
experiment,method,seed,step,generation_start,generation_end,
p_c,p_m,hv_start,hv_end,hv_delta,hv_auc,
diversity_start,diversity_end,stagnation,mean_tree_size,
reward,hv_term,diversity_term,stagnation_penalty,bloat_penalty,
elapsed_time
```

`summary.md` には以下を書く。

- 実験目的
- 比較対象
- 仮説
- 設定
- 主結果
- 失敗や例外
- 次に変更すべき点

## 9. 設計判断の記録

以下のような判断をした場合は、研究ノートに必ず理由を書く。

- 文脈ベクトルの要素を増減した
- 報酬重みを変えた
- baseline を追加または削除した
- 制御区間を変更した
- HV の参照点を変更した
- 実験対象問題を変更した
- 文献の採用または不採用を決めた

記録形式:

```md
### YYYY-MM-DD | 設計判断: タイトル

- 判断:
- 理由:
- 根拠文献:
- 影響するファイル:
- 確認方法:
- 次に見ること:
```

## 10. 品質ゲート

各段階の終わりで、次のゲートを確認する。

### Literature gate

- `[Rxx]` が採番されている
- 本文確認状況が明記されている
- OA / Elsevier / 手動取得候補の扱いが明確である
- 研究のどの部分に使うかが書かれている

### Implementation gate

- テストまたは smoke run が通る
- 設定が再現可能である
- 主要な出力が保存される

### Experiment gate

- baseline と提案法が同じ条件で比較されている
- seed と評価回数が揃っている
- 主指標と補助指標が保存されている

### Writing gate

- 研究質問に対応する結果がある
- 支持された仮説と支持されなかった仮説が分かれている
- 関連研究との差分が説明できる

## 11. 直近の進め方

現時点では、次の順で進めるのがよい。

1. 文献補強
   - adaptive GP operator control
   - evolutionary parameter control / online configuration
   - contextual BO

2. toy engine baseline 比較
   - 固定率
   - 手設計スケジュール
   - ランダム制御
   - 文脈なし BO
   - 文脈付き BO

3. ログ形式の固定
   - CSV または JSONL
   - `config.json`
   - `summary.md`

4. 実 GP 接続
   - DEAP 記号回帰
   - error と tree size の 2 目的
   - 構造多様性と HV の区間ログ

## 12. 相談して詰めるべき内容

以下は、現時点では仕様として仮置きしている。次に一緒に議論して決めたい。

### 12.1 最初の実 GP 問題

候補:

1. 記号回帰の単純ベンチマークから始める
2. 既存研究で使われる symbolic regression benchmark を選ぶ
3. 多目的 GP に最初から寄せる

仮置き: まずは記号回帰で、目的を予測誤差と木サイズの 2 目的にする。

### 12.2 baseline の強さ

候補:

1. 代表的な固定率だけを置く
2. 事前グリッドで強い固定率を選んだ baseline も置く
3. 手設計スケジュールを複数置く

仮置き: 固定率は代表値と事前グリッド最良の両方を置く。

### 12.3 run 数と統計比較

候補:

1. まず 5 seed の smoke 比較
2. その後 20 seed 以上の本比較
3. 問題数を増やす代わりに seed を減らす

仮置き: smoke は 5 seed、本比較は 20 seed 以上を目標にする。

### 12.4 Elsevier 手動取得候補の扱い

確認したいこと:

- ユーザー側で Elsevier PDF を取得できる環境があるか
- 手動取得した PDF を `references/` に置く運用でよいか
- 手動取得前の文献を `M` として文献台帳に載せるか、別リストにするか

仮置き: `M` として `references/README.md` に載せ、本文取得後に採用扱いへ更新する。

### 12.5 論文・発表のゴール

確認したいこと:

- 卒論、修論、学会発表、進捗報告のどれを第一ゴールにするか
- ページ数や発表時間の制約があるか
- 実験規模をどこまで広げられるか

仮置き: まず進捗報告と卒論・論文草稿の両方に使える構成で進める。

## 13. 次回更新時の作業

この仕様書は、以下のタイミングで更新する。

- 新しい中核文献を追加したとき
- baseline の実装方針が決まったとき
- 実 GP 接続の対象問題が決まったとき
- 実験ログ形式を実装したとき
- 最初の比較実験結果が出たとき

更新時は、変更理由を `notes/research_note.md` の作業ログにも残す。
