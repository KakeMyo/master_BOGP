# 文献調査の記録ひな型

項目と保存ルールは毎回`references/reference_workflow_spec.md`の最新内容を確認する。以下はその12・14節に沿う記入ひな型であり、未確認の書誌・本文情報は「未確認」、当てはまらない項目は「該当なし」とする。

## 文献メタデータ

```markdown
# Paper Title

- Reference ID: [既存R番号／新規正式採用のR番号／候補ID]
- Status: Adopted / Hold / Manual download candidate / Rejected
- Category: A / B / C / D / M / H / R
- Citation: 著者，年，完全タイトル，掲載誌・会議，巻号・ページ，DOI
- DOI:
- URL:
- Elsevier URL:
- Source checked: 確認したDB・出版社・取得経路，確認日
- Access: PDF saved / OA HTML / Elsevier PDF saved / metadata only / manual download candidate
- Local PDF: 相対パス。ない場合は未取得
- Version: 出版版／accepted版／preprint／未確認
- Citation signal: 引用数とDB・確認日，または未確認
- Why this paper matters: 今回の問いに対する候補・採用理由
- Information used in this project:

| 確認した情報 | 本文の位置 | 本研究での利用 | 反映先 | 独自設定・限界 |
| --- | --- | --- | --- | --- |
| 実際に本文で読めた内容 | 節・表・図・ページ／HTMLの節とURL | どの判断へ使うか | ノート・仕様の箇所 | 原典と移植条件の差 |

- Related note sections:
- Manual download queries:
  - Complete title:
  - Author year query:
  - DOI:
- Next action:
```

抄録・書誌のみ確認した文献では本文位置を記入せず、その確認範囲と本文取得待ちを明記する。正式採用の新規R番号は台帳を確認してから付ける。

## 調査・採否ログ

```markdown
# テーマ名：文献調査ログ

- 調査日:
- 依頼の問い:
- 保存先・登録の指定:
- 既存資料を確認した範囲:

| 検索先 | クエリ | 日付 | 検索・アクセス状況 |
| --- | --- | --- | --- |
| 実際に調べたDB・サイト | 実行した検索語 | YYYY-MM-DD | 利用可／アクセス不可等 |

| 文献・DOI | 用途分類 | 確認範囲・版 | 採否と理由 | 保存先・取得経路 | 本文参照位置 |
| --- | --- | --- | --- | --- | --- |
| 候補ごとの情報 | A～R | 本文／抄録のみ等 | 採用／保留／不採用 | 保存PDF・メタデータ・URL | 確認できた場合のみ |

- 次に必要な手動取得・確認:
- 重複文献の再利用と既存番号:
- 台帳・研究ノートへの反映／登録保留:
- 残った不確実性:
```

## 本文未取得の手動取得案内

```markdown
### 手動取得候補：完全タイトル

- 著者・年:
- 掲載誌・会議，巻号ページ:
- DOI:
- 出版社／Elsevier掲載URL:
- 確認できた範囲: 書誌・抄録等。本文は未取得
- 抄録で確認できた要点:
- 本研究との関係・候補理由:
- 想定する利用箇所:
- 確認した正規取得経路と結果:
- 検索クエリ: 完全タイトル／著者と年／DOI
- 本文取得後に確認する事項:
```

## 研究ノートへの反映

正式採用文献は参考文献章へ既存の体裁で追記し、どの情報・位置をどの判断へ使うかを書く。採用を保留する指定があれば参考文献章ではなく作業ログへ記録する。作業ログには検索・取得・採否・保存・反映・検証・未達事項と、それらの理由を残す。
