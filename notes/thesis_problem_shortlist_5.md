# 次に予備実験へ進める問題設定候補：5件

- 作成日: 2026-10-01
- 位置づけ: 実装・固定率pilotへ進める候補の絞り込み。提案法の優位や長期収束を実測済みという意味ではない
- 全22候補・以前の構成案: [元メモ](thesis_long_horizon_problem_setting_options.md)を保持
- 参照本文: [問題設定用文献フォルダ](../references/problem_settings/README.md)
- 手動取得待ち: [2論文のタイトル・DOI](../references/problem_settings/manual_download_list.md)

## 1. 絞り込みの結論

次に採用を検討する新規問題は、以下の5件に限定する。優先1～3から着手し、4・5は役割を分けてscreenする。

| 優先 | 元候補ID | 問題 | 想定する役割 | 採用理由 | 最大の注意点 |
|---|---|---|---|---|---|
| 1 | P08 | UBall5D / Vladislavleva-4 | 主合成問題 | 真値既知、5入力すべてに依存、分母の結合構造、外挿、再現可能な標本仕様 | 18世代後の改善は未確認。小木偏重や表現制限で単に停滞する可能性 |
| 2 | P14 | Airfoil Self-Noise | 縮退機序の確認 | 現行に近いaccuracy--size MOGPで小木の過剰複製・進化可能性低下を観察した研究がある | 早期に悪いfrontへ止まる問題であり、難しさが長期改善とは限らない |
| 3 | P15 | Concrete Compressive Strength | 公開実データでの確認 | 8入力、非線形関係、1030例、MOGP利用実績、比較的扱いやすい計算量 | 原研究の設定と現行population 100の条件差。長期改善の直接根拠は弱い |
| 4 | P05 | Combined Cycle Power Plant (CCPP) | Oh論文との連続性・大標本確認 | 9568例・4入力、公開データ、既存比較論文と同じtargetを使える | 大標本は1世代を重くするだけかもしれない。線形・滑らかな近似で早く収束する危険 |
| 5 | P09 | Korns-12 | 無関係変数・係数探索のstress | 5入力中3入力が無関係、振動関数、既知真値、難度の根拠がある | 係数同定が支配し、BOにも固定率にも改善不能な問題になる危険。計算量が大きい |

この5件は「提案法が勝ちそうだから」ではなく、(a)公開・再現可能、(b)既存基盤から回帰として移植可能、(c)異なる失敗機序を検証できる、という観点で選んだ。長期headroomと状態依存の率効果は、固定率だけのpilotで採否判断する。[R29][R30]

## 2. 各候補の設定・理由・注意点

### 2.1 UBall5D / Vladislavleva-4 — 最優先

\[
f(\mathbf{x})=\frac{10}{5+\sum_{i=1}^{5}(x_i-3)^2}
\]

- train: 1024点、各入力をU[0.05,6.05]から独立生成
- test: 5000点、各入力をU[-0.25,6.35]から独立生成
- validation: trainと同じ範囲から独立1024点を追加（本研究の拡張）
- noise: なし
- 進化目的: train誤差と木サイズの2目的
- 関数集合案: `{+,-,*,protected_div}`。二乗は乗算でも表現できる
- 出典: [R29, Table 5・§6.1]。元のVladislavleva論文はLH01として本文取得待ち

理由: 真の式が分かるため、単なるtrain HVだけでなく、未見点・外挿で改善したか確認できる。5変数を分母へ組み合わせる構造が必要なので、1変数sinより状態・多様性・木サイズの変化を観察しやすい、という仮説を立てられる。

注意点:

- この構造は長期探索の候補理由であり、18世代後に改善する実測根拠ではない
- protected divisionのゼロ近傍処理を固定する。AQへ変える感度条件は別条件とし、手法ごとにprimitiveを変えない
- raw input範囲を保持し、定数生成範囲・定数変更演算をpilot前に固定する。現行ERC[-2,2]を無条件で移植せず、必要な3、5、10の構成可能性を検査する
- 真の式は四則演算木で上限100内に表現可能だが、実装上の木サイズ定義・初期化・変異がその領域へ到達できるか確認する
- test外挿結果を見て率や候補を選ばず、validationを選定に使う

### 2.2 Airfoil Self-Noise — 適応制御の機序確認

- 規模: 1503例、5入力、欠損なし
- target: scaled sound pressure level
- 入力: frequency、attack angle、chord length、free-stream velocity、suction-side displacement thickness
- 配布・許諾: [UCI公式ページ](https://archive.ics.uci.edu/dataset/291/airfoil%2Bself%2B)、CC BY 4.0
- 関数集合案: `{+,-,*,protected_div,protected_sqrt,protected_log}`、train由来linear scalingを全比較法で共通適用
- 出典: [R30, §5・§6.1.2・Figure 3]

理由: 小さい木が集団を占有すると高精度な大きい木が生まれにくくなる機序が、mean tree size・多様性・HV改善・停滞という本研究の文脈と直接対応する。高突然変異固定と、状態に応じて率を変える制御のどちらが有効か、理由まで調べやすい。

注意点:

- 原研究では普通のNSGA-IIが初期十数世代後に低品質へ収束する傾向がある。warm-up中に縮退し、後から率を変えても回復しない可能性
- 原研究のevoNSGA-IIは生存選択を変える。本研究の操作率制御だけで同じ改善が得られるとは主張できない
- 集団・分割・関数集合が違えば収束速度も違う。元図をpopulation 100での予測曲線として使わない
- 固定率pilotで長期headroomを満たさない場合、長期主問題には採用しない。残すなら「早期縮退回避」の副実験と明記し、W18の問題とは分ける

### 2.3 Concrete Compressive Strength — 実データ主候補

- 規模: 1030例、8入力、欠損なし
- target: compressive strength (MPa)
- 入力: cement、slag、fly ash、water、superplasticizer、coarse aggregate、fine aggregate、age
- 配布・許諾: [UCI公式ページ](https://archive.ics.uci.edu/dataset/165/concrete%2Bcompressive%2Bstrength)、CC BY 4.0
- 関数集合・linear scaling案: Airfoilと同じprofile
- 出典: [R30, Tables 2・3]とUCIの非線形関係の説明

理由: 8変数の材料配合・材齢と強度を扱い、Airfoilとは異なる物理現象で確認できる。公開性、欠損の少なさ、標本数、1評価あたり費用のバランスがよく、長期反復実験を組みやすい。

注意点:

- 入力が8個だから収束が遅い、とまではいえない。固定率のHV曲線・木サイズ分布で確認する
- 各データsplitのscalerはtrainだけから推定し、全手法に同じsplitを与える
- 同一入力の重複などを取得時に検査し、分割の扱いをmanifestへ記録する。問題選択後に恣意的な除外をしない
- 固定高突然変異が全探索状態で有効なら、長期でも文脈制御の追加価値を示せない可能性

### 2.4 CCPP — 既存比較論文との連続性

- 規模: 9568例、4入力、欠損なし
- target: net hourly electrical energy output (PE)
- 入力: ambient temperature、exhaust vacuum、ambient pressure、relative humidity
- 配布・許諾: [UCI公式ページ](https://archive.ics.uci.edu/dataset/294/combined%2Bcycle%2Bpower%2Bplant)、CC BY 4.0
- 関数集合・linear scaling案: 他の実データと同じprofile
- 出典: [R25, §4.2]。単目的MSE評価を、本研究では誤差--木サイズへ移植する

理由: Oh論文由来の案を主候補へ残せる。既存のルールベース適応法とBOを、同じ公開targetに対して比較できる。大標本で汎化と計算費用の両面を確認する役割もある。

注意点:

- 比較的滑らかな4入力回帰であり、大標本でも世代方向に早期収束する可能性がある。単に計算時間が長いことを採用理由にしない
- UCI配布物は同じデータを5回shuffleした複数sheetを含む。全sheetを連結して独立標本を増やしてはいけない。1つの9568行版を固定し、ファイルhash・sheet名を記録する
- 縮小標本でruntime確認する場合は実装試験と位置づける。縮小版でのheadroomをフルデータの証拠にはしない
- Ohのpc/pm式を現行の排他的演算子へ入れる場合は実行可能領域への射影を明記し、原法の完全再現とは呼ばない
- Concreteと役割が重なるため、予備実験でheadroomと費用を比べ、計算予算が厳しければ片方だけを本番採用する

### 2.5 Korns-12 — 条件付きの難問候補

\[
f(x,y,z,v,w)=2-2.1\cos(9.8x)\sin(1.3w)
\]

- 入力5変数のうちx、wだけがtargetに関係し、残り3変数は無関係
- train: 10000点、各入力U[-50,50]
- test: 独立10000点、同範囲
- 関数集合案: `{+,-,*,protected_div,sin,cos}`
- 出典: [R29, Table 5・§6.1]

理由: 無関係変数の排除、係数同定、振動関数の組合せという、UBall5Dとは別の難しさがある。構造多様性を維持した探索と、その後の精密化を切り替える価値を検証する候補になる。

注意点:

- 係数9.8の探索を現行ERC[-2,2]に任せると、行動制御より表現・係数生成の制約が支配する可能性。例えばERC[-10,10]とするか、係数変更/最適化を入れるかを全手法共通でpilot前に固定する
- 係数最適化を足す場合は追加評価数・wall-clockもそろえる。提案法だけへ追加しない
- 高い振動数と広い領域では僅かな係数差でも誤差が大きい。全手法が改善不能なら「長期に難しい」と評価せず、今回の制御仮説を検証できないとして不採用にする
- 10000 train casesは高コスト。小標本版で検証した場合はcanonical版と区別する

## 3. 共通の採用判定

1. 固定率5条件のみでscreenする。BOの勝敗を問題選定に使わない。
2. Round 1: population 100、120世代、5 discovery seeds。Round 2: 通過候補を318世代、10 discovery seedsで確認。
3. 18世代までの改善比q_W≤0.70、有限予算内の改善90%到達時間の中央値t_90≥54、70%以上のseedで18世代後の改善があることを仮基準にする。数値は本研究の仮基準であり、文献の標準ではない。
4. 現行archiveは有限なので、選定用は0～1に正規化した履歴最大HVを使い、生HVの低下・保持frontの品質も別報告する。
5. checkpoint分岐で、少なくとも二状態において有効な操作率が変わるか確認する。全状態で同じ高突然変異が最良なら、文脈制御に向く証拠は弱い。
6. 問題・primitive・split・正規化・許容行動・予算をfreezeしてから、未使用seedで本番比較する。testで候補を選ばない。

実データの基本分割はtrain60%/validation15%/test25%、trainのみで標準化・linear scalingする。これは本研究の公平比較用仕様であり、Ohの80/20やLiuの75/25をそのまま再現する条件ではない。全比較法で同一split・初期集団を共有する。[R25][R30]

## 4. 他の案を落とした理由と保持方針

- Niehaus由来sinとAuto MPG: 実装・校正には有用だが、今回の最優先条件である長期headroomの根拠が弱い。既存案は削除せず、補助実験として保持。[R24][R25]
- Tower: 長期HV図は魅力的だが、配布版・利用許諾・runtime固定の追加作業がある。公開性と実装負荷が明確な5件を先に進める。[R28]
- Dou F5: 安価なMOGP例だが、1変数で、targetの超越関数をprimitiveに含めない近似の難しさが主である。別機序の補助候補として保持。[R10]
- Harrison Synthetic-1: 式の9変数と列挙された8素数の不整合を解消するまで保留。[R28]
- private CTQ: 非公開データのため再現不能。主比較に使えない。[R25]
- 現行Friedman-I: 新規採用候補には数えない。以前の結果との比較と「早期収束時には制御価値が小さい」という負の対照として、既存条件を保持する。

5候補すべてを本番へ採用する必要はない。最初はUBall5D・Airfoil・Concreteを評価し、CCPPを連続性確認、Korns-12を難問stressとして追加する。最終的な本番はpilotで通過した問題に限定し、不採用結果も理由とともに報告する。

## 5. 2026-10-01：セミナー条件での3回pilotを実行済み

ユーザー指定により、上記の長期screen条件ではなく、集団24・総78世代・3seedで
UBall5D/Airfoil/Concreteを各4手法実行した。元の候補と条件案は削除・置換していない。
[実験レポート](thesis_three_problem_pilot_report.md)に条件差と実測を記録した。

- Airfoil: 固定率を含め18世代後の改善が観察でき、次の長期pilotの最優先。
- UBall5D: 提案法3回とも訓練最良式が定数。今回の構成のまま長期主問題へ進めない。
- Concrete: 提案法2回が18世代までで停止する一方、高突然変異2回には後半改善。副検証として保持。
- これは最終採用でも統計的優位の確定でもない。問題採否は未使用seedの固定率screenで確認する。
- 今回はセミナーの関数集合を維持し、sqrt/log/AQやfitted linear scalingは追加していない。
