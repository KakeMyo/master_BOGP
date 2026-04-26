# 参考文献調査・取得・研究ノート反映 仕様書

- 更新日: 2026-04-22
- 対象研究: 交叉率 `p_c` と突然変異率 `p_m` を、文脈付きベイズ最適化で動的に調整する閉ループ型遺伝的プログラミング
- 管理起点: `references/README.md`
- 研究ノート: `notes/research_note.md`

## 1. 目的

本仕様書は、参考文献の探索、採否判断、本文または内容確認可能な文献の取得、メタデータ保存、研究ノートへの反映を一貫して行うための実務ルールを定める。

文献取得対象は、オープンアクセスで本文確認可能な論文と、Elsevier / ScienceDirect から本文または内容を確認できる論文を同列に扱う。どちらかを取得元だけで優先せず、研究テーマとの関連性、信頼性、有用性、入手可能性を総合的に見て採否を判断する。

単に論文を集めるのではなく、本研究の設計判断に使える根拠を増やすことを目的とする。特に、次の判断に直接使える文献を優先する。

- GP の交叉率・突然変異率を固定値ではなく動的制御対象として扱う根拠
- 文脈付き BO を採用する理由
- 文脈ベクトルに入れる指標の選定根拠
- 区間報酬、HV、多様性、停滞、bloat ペナルティの設計根拠
- 固定率 GP、時変スケジュール、文脈なし BO との比較設計
- 実験評価、統計検定、ベンチマーク設計

## 2. 役割

研究補助エージェントは、以下を行う。

1. 現在の研究テーマに沿って候補文献を探索する
2. 候補を研究上の用途別に分類する
3. オープンアクセス版または Elsevier / ScienceDirect 版で本文確認できる文献を優先して取得する
4. 採用、保留、不採用を理由付きで記録する
5. 採用文献の PDF またはメタデータノートを `references/` に保存する
6. `references/README.md` の文献番号台帳を更新する
7. `notes/research_note.md` の参考文献章に、どの設計判断へ使ったかを追記する
8. 研究ノート本文を更新した場合は、該当箇所に文献番号を付ける
9. Elsevier 上で有用性を確認できるが直接ダウンロードできない場合は、手動ダウンロード候補として検索しやすい情報を返す

## 3. 優先して探す文献領域

本研究では、以下の 5 系統を優先する。

### 3.1 直接領域

- genetic programming の crossover rate / mutation rate / operator probability
- adaptive parameter control in genetic programming
- self-adaptive GP operators
- dynamic parameter control in evolutionary computation
- hyperparameter control for evolutionary algorithms

### 3.2 BO と制御

- Bayesian optimization for evolutionary algorithms
- contextual Bayesian optimization
- online algorithm configuration
- sequential model-based optimization
- closed-loop control of stochastic optimization

### 3.3 文脈指標

- diversity in genetic programming
- structural diversity / genotypic diversity
- semantic diversity / semantic locality
- bloat / program size / simplification
- stagnation detection in evolutionary computation

### 3.4 多目的評価

- multiobjective genetic programming
- hypervolume indicator
- Pareto front coverage
- NSGA-II / crowding distance
- tree size versus accuracy trade-off

### 3.5 実験方法

- EC/GP benchmark methodology
- symbolic regression benchmark
- repeated-run statistical comparison
- nonparametric tests for evolutionary algorithms

## 4. 検索クエリ

検索では日本語と英語の両方を使う。英語文献が中心になる見込みのため、英語クエリを主、和文クエリを補助とする。

### 4.1 中核クエリ

- `"genetic programming" "crossover rate" "mutation rate"`
- `"genetic programming" "operator probability" adaptive`
- `"genetic programming" "parameter control"`
- `"adaptive parameter control" "genetic programming"`
- `"Bayesian optimization" "genetic programming"`
- `"Bayesian optimization" "evolutionary algorithm" "parameter control"`
- `"contextual Bayesian optimization" "evolutionary algorithm"`
- `"online algorithm configuration" "evolutionary algorithm"`

### 4.2 文脈指標クエリ

- `"diversity" "genetic programming" "fitness"`
- `"structural diversity" "genetic programming"`
- `"semantic diversity" "genetic programming"`
- `"semantic locality" "crossover" "genetic programming"`
- `"bloat" "genetic programming" "program size"`
- `"multiobjective genetic programming" "tree size"`
- `"hypervolume" "multiobjective genetic programming"`

### 4.3 日本語補助クエリ

- `遺伝的プログラミング 交叉率 突然変異率`
- `遺伝的プログラミング パラメータ制御`
- `進化計算 パラメータ制御 動的`
- `ベイズ最適化 進化計算 パラメータ`
- `文脈付きベイズ最適化`
- `遺伝的プログラミング 多様性 bloat`

## 5. 探索元

主探索元:

- CiNii Research
- Web of Science
- ScienceDirect / Elsevier
- Google Scholar

補助探索元:

- Crossref
- DOI リンク先
- 出版社公式ページ
- 大学・研究機関リポジトリ
- arXiv
- PubMed Central
- J-STAGE

検索時は、出版社ページだけで終わらせず、DOI、著者ページ、機関リポジトリ、論文タイトル検索を最低限確認する。

## 6. 候補分類

候補文献は、最初に次の分類を付ける。

| 分類 | 用途 | 採用目安 |
|---|---|---|
| A: 中核 | 提案手法の前提、先行研究、差分説明に使う | 直接関連、本文確認必須 |
| B: 設計根拠 | 文脈指標、報酬、bloat、多様性など特定設計に使う | 本文確認必須 |
| C: 比較対象 | baseline、評価指標、実験条件の根拠に使う | 本文確認推奨 |
| D: 背景 | 研究背景や用語整理に使う | レビュー・survey を優先 |
| M: 手動取得候補 | Elsevier 上で内容確認できるが Codex 側で直接ダウンロードできない | 検索しやすい情報を返し、ユーザー取得後に採用判断 |
| H: 保留 | 重要だが本文取得や信頼性確認が未完了 | 具体的な本文主張には使わない |
| R: 不採用 | 関連が弱い、信頼性が低い、重複が大きい | 理由のみ記録可 |

## 7. 採用条件

採用文献は、原則として以下を満たすものを優先する。

- 研究テーマとの関連が明確である
- 査読付き論文、主要会議、信頼できる書籍章、または定評あるプレプリントである
- オープンアクセスまたは Elsevier / ScienceDirect で本文を確認できる
- DOI、出版社ページ、Elsevier / ScienceDirect 掲載ページ、機関リポジトリなどで出典を追跡できる
- 本研究のどの設計判断に使うかを一文で説明できる

採用候補として扱ってよい文献:

- オープンアクセスで本文確認可能な論文
- Elsevier / ScienceDirect から本文確認可能な論文
- Elsevier 上で書誌情報、抄録、掲載情報を確認でき、研究上有用と判断される論文

ただし、本文を確認できていない Elsevier 文献は、ユーザーが手動取得するまで `M: 手動取得候補` または `H: 保留` とし、研究ノート本文の具体的主張の根拠には使わない。

特に優先する文献:

- GP の操作率を適応的に変える先行研究
- 進化計算の parameter control / online configuration のレビュー
- BO を進化計算の制御や設定調整に使った研究
- contextual BO の基礎または応用研究
- GP における diversity / bloat / semantic methods の survey
- 多目的 GP と HV / tree size trade-off に関する文献

## 8. 除外条件

以下は採用しない。

- テーマとの関連が弱い
- 本文または Elsevier 上の内容情報が確認できず、アブストラクト以上の根拠にできない
- 出版社、会議、査読体制、編集体制が不透明である
- ハゲタカ誌または疑わしい出版元の可能性が高い
- 同じ内容をより信頼できる文献で代替できる
- 実装記事、ブログ、スライドのみで、学術的出典として弱い

判断に迷う場合は採用せず、`H: 保留` または `R: 不採用` として理由を残す。Elsevier 上で有用性は高いが Codex 側で直接取得できない場合は、`M: 手動取得候補` として扱う。

## 9. 本文アクセス・取得ルール

### 9.1 同列優先対象

PDF または HTML 本文の取得では、以下を同列の優先対象とする。

1. オープンアクセスで本文取得可能な論文
2. Elsevier / ScienceDirect から本文確認または取得可能な論文

この 2 つは取得元の違いとしてのみ扱い、優先順位の差にはしない。採用時は、研究テーマとの直接的関連性、被引用数や学術的影響度、本文または内容確認のしやすさ、査読付きかどうか、掲載誌・出版社の信頼性、新しさ、レビュー論文かどうかを総合的に評価する。

解釈ルール:

- オープンアクセスだから自動的に Elsevier 文献より優先しない
- Elsevier から読めるから自動的にオープンアクセス文献より優先しない
- 両者は同等候補として扱い、内容面で有用なものを選ぶ
- 直接取得できない Elsevier 文献でも、有用性が高ければ候補として保持してよい

### 9.2 取得元の確認順

取得元は以下を確認する。

- 出版社公式のオープンアクセス本文
- Elsevier / ScienceDirect の本文または掲載ページ
- DOI リンク先から辿れる公式本文
- 大学・研究機関リポジトリ
- arXiv などの公的プレプリントサーバ
- 著者公開版

### 9.3 Elsevier 文献の扱い

Elsevier / ScienceDirect 上で PDF 等を直接取得できる場合は、既存の保存・反映ルールと同様に処理する。

- 文献フォルダへ保存する
- ファイル名は論文タイトルに変更する
- `references/README.md` の文献番号台帳へ追加する
- `notes/research_note.md` の参考文献章へ追加する
- 本文へ反映した場合は参考箇所と文献番号を追記する

Elsevier 上で論文情報は確認できるが、Codex 側で直接ダウンロードできない場合は、自動取得を無理に行わない。代わりに、ユーザーが手動で探してダウンロードしやすいよう、検索しやすい形式で論文情報を返す。

### 9.4 ダウンロード不可時の返却仕様

Elsevier から直接ダウンロードできない文献については、最低限以下を返す。

- 論文タイトル
- 著者名
- 発行年
- 掲載誌名
- 巻・号・ページ
- DOI
- Elsevier 上の掲載ページ URL
- 抄録の要点
- この論文を参考文献候補とした理由
- 研究のどの部分に使えそうか

ユーザーが手動検索しやすいよう、以下も併記する。

- コピペしやすい完全な論文タイトル
- DOI そのもの
- 推奨検索クエリ
- 著者名と年を含んだ簡易検索クエリ

推奨出力形式:

```md
### 手動ダウンロード候補 [N]

- タイトル: `論文タイトル`
- 著者: `著者名`
- 年: `2023`
- 掲載誌: `Journal Name`
- 巻号・ページ: `Vol. xx, No. xx, pp. xxx-xxx`
- DOI: `10.xxxx/xxxxx`
- Elsevier掲載ページ: `URL`
- 推奨検索クエリ1: `完全タイトル`
- 推奨検索クエリ2: `著者名 論文タイトル`
- 推奨検索クエリ3: `DOI`
- 要点: `この論文の内容の簡潔な要約`
- 採用理由: `なぜ参考文献として有用か`
- 想定利用箇所: `背景、関連研究、手法比較、評価指標など`
```

使用しない取得元:

- 著作権状態が不明な転載サイト
- 海賊版サイト
- 出典や版が確認できない PDF

本文が取得できないが重要な文献は、`H: 保留` または `M: 手動取得候補` としてメタデータノートのみ作る。この場合、研究ノート本文では「本文で確認した主張」として扱わない。

## 10. 保存ルール

現在のリポジトリでは既存リンクを保つため、PDF と `.md` メモは `references/` 直下に保存する。

- PDF: `references/<論文タイトル>.pdf`
- メタデータノート: `references/<論文タイトル>.md`
- 既存ファイルを移動しない
- 将来 `pdfs/`, `metadata/`, `notes/` に分ける場合は、研究ノートと README のリンクを同時に更新する

ファイル名は論文タイトルベースにする。使用できない文字は置換する。

- `/` は `-`
- `:` は `-`
- `?` と `*` は削除
- 連続スペースは単一スペース
- 末尾ピリオドは削除

同名ファイルがある場合:

1. DOI が同じなら重複とみなし保存しない
2. DOI が異なるなら年または筆頭著者を付ける

例:

- `Paper Title.pdf`
- `Paper Title (2021).pdf`
- `Paper Title (Smith et al., 2021).pdf`

## 11. 文献番号

研究ノート内では、増減しても破綻しにくい作業用文献番号を使う。

- 形式: `[R01]`, `[R02]`, ...
- 採用順に付与する
- 一度付けた番号は原則変更しない
- 論文原稿に移す段階で、投稿先形式に合わせて `[1]`, `[2]` などへ変換する

`references/README.md` を文献番号台帳とし、番号、分類、本文確認状況、主用途を管理する。

## 12. メタデータノート形式

各 `.md` メモには、最低限以下を書く。

```md
# Paper Title

- Reference ID: [Rxx]
- Status: Adopted / Hold / Manual download candidate / Rejected
- Category: A / B / C / D / M / H / R
- Citation: Author. (Year). *Title*. Venue, volume(issue), pages. DOI
- DOI:
- URL:
- Elsevier URL:
- Source checked:
- Access: PDF saved / OA HTML / Elsevier PDF saved / Elsevier manual download candidate / metadata only
- Local PDF:
- Citation signal:
- Why this paper matters:
  - ...
- Information used in this project:
  - ...
- Related note sections:
  - ...
- Manual download queries:
  - Complete title:
  - Author year query:
  - DOI:
- Next action:
  - ...
```

既存メモはこの形式へ段階的に寄せる。急いで全ファイルを書き換える必要はないが、新規追加分はこの形式に従う。

## 13. 研究ノートへの反映

文献を追加したら、以下を行う。

1. `references/README.md` の台帳へ追加する
2. `notes/research_note.md` の `## 10. 参考文献` に用途を追記する
3. 本文を更新した場合は、該当する設計判断の末尾に `[Rxx]` を付ける
4. 参照箇所には、文献から何を使ったかを具体的に書く
5. 引用数を書く場合は、参照元 DB と確認日を併記する
6. `M: 手動取得候補` は、ユーザーが本文を取得するまで本文主張の根拠として使わず、手動ダウンロード用情報を残す

例:

```md
- [Rxx] Author et al. (Year) [Paper Title.md](...)
  - 分類: B: 設計根拠
  - 参照箇所: 5.3.2 構造多様性
  - 参照内容: subtree similarity を用いる根拠
```

本文へ反映するときは、文献番号だけを置くのではなく、設計判断が読める文にする。

例:

```md
初期段階では、操作率の影響を直接受けやすく計算負荷も低い構造多様性を文脈指標の第一候補とする [R01][R06]。
```

## 14. 採否ログ

大きな調査を行う場合は、作業ログまたは別メモに次を残す。

- 検索日
- 検索クエリ
- 確認した DB
- 採用した文献
- 手動ダウンロード候補にした Elsevier 文献と検索用情報
- 保留にした文献と理由
- 不採用にした文献と理由
- 次に探すべきキーワード

## 15. 作業完了条件

参考文献追加作業は、以下を満たしたら完了とする。

- PDF、本文確認可能な URL、Elsevier 掲載ページ URL、または手動ダウンロード候補情報が保存されている
- `.md` メタデータノートがある
- `references/README.md` の台帳に追加されている
- `notes/research_note.md` の参考文献章に用途が書かれている
- 本文へ反映した場合は `[Rxx]` が付いている
- 本文未確認または手動取得待ちの文献は、具体的な主張の根拠として使っていない
