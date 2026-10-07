# 構造探索問題の Python 雛型適用と MATLAB 実装との差分メモ

- 作成日: 2026-05-12
- 対象 MATLAB 実装: `/Users/kakemyo/Downloads/gradthesis/GPfin.m`
- Python 側アダプタ: [test_v1_structural_problem.py](/Users/kakemyo/Downloads/master_BOGP/src/bogp/test_v1_structural_problem.py)
- 汎用雛型: [test_v1_problem.py](/Users/kakemyo/Downloads/master_BOGP/src/bogp/test_v1_problem.py), [test_v1_mo_engine.py](/Users/kakemyo/Downloads/master_BOGP/src/bogp/test_v1_mo_engine.py)

## 1. 位置づけ

本メモは、添付 MATLAB コードで扱われている構造探索問題を、今回作成した汎用多目的 GP 雛型へどのように適用したかを整理するものである。

重要なのは、Python 版は MATLAB 実装の完全コピーではなく、提案手法である「状態依存・閉ループ BO 制御」を適用しやすいように、問題依存部分を `GPProblem` として切り出した研究用アダプタである点である。

## 2. 適用済みの対応関係

| 項目 | MATLAB 実装 | Python 雛型での扱い | 状態 |
|---|---|---|---|
| 個体表現 | `digraph` とノード属性 `Type`, `Value` | `StructuralNode` による再帰木 | 適用済み |
| ルート質量 | `mass`, 値 130 | 暗黙の質量 `mass=130.0` | 適用済み |
| 終端ノード | `spring`, `damper` | `spring`, `damper` | 適用済み |
| 内部ノード | `series`, `parallel` | `series`, `parallel` | 適用済み |
| 目的1 | 終端ノード数を少なくする | `terminal_elements` を最小化 | 適用済み |
| 目的2 | インパルス応答積分を小さくする | `impulse_integral` を最小化 | 適用済み |
| Pareto front | 世代ごとに非劣解を抽出・可視化 | archive と exact 2D HV を管理 | 適用済み |
| 交叉 | 部分木交換 | 部分木交換 | 適用済み |
| 突然変異 | 値変更または部分木追加 | 部分木置換 | 初期版 |
| 外側制御 | 固定 `crossoverRate`, `mutationRate` | BO が `p_c`, `p_m`, `k` を決定 | 提案法として拡張 |

## 3. 研究用に意図的に変更した点

### 3.1 選択・世代交代

MATLAB 実装では Pareto front を可視化しているが、親選択では一部の目的だけを使う処理が含まれている。

Python 版では、本研究の対象を多目的 GP と明確にするため、汎用エンジン側で NSGA-II 型の非優越ソートと crowding distance を用いる。

この変更により、比較対象や提案手法の評価を「最終的に望ましい Pareto front を得る」という研究目的と整合させやすくなる。

### 3.2 制御入力

MATLAB 実装では `crossoverRate=0.8`, `mutationRate=0.05` が固定値として与えられている。

Python 版では、閉ループ制御の行動として

```text
u = (p_c, p_m, k)
```

を扱う。ここで `k` は次回 BO 更新までの世代数であり、単なる効率化ではなく更新周期制御として位置づける。

### 3.3 伝達関数計算

MATLAB 実装では symbolic DAE を構成し、Laplace 変換と Control System Toolbox の `tf`, `impulse` により伝達関数とインパルス応答を計算している。

Python 版の初期アダプタでは、構造木を等価動剛性として扱う。

```text
spring:   K(s) = k
damper:   K(s) = c s
parallel: K(s) = K_1(s) + K_2(s)
series:   K(s) = 1 / sum_i 1 / K_i(s)
X(s)/F(s) = 1 / (m s^2 + K_eq(s))
```

この方針は、構造探索問題をまず汎用雛型上で安定に動かすための簡略化である。今後、MATLAB と数値的に一致させる必要がある場合は、代表構造を固定して両者の伝達関数またはインパルス応答積分を比較する。

### 3.4 初期木生成

MATLAB 実装では、`binary_tree(n)` で生成した木に対して、終端と非終端の種類を割り当てている。

Python 版では、最大深さを指定した再帰生成を用いる。これにより、汎用 GP の問題アダプタとして扱いやすくしている。

完全再現が必要になった場合は、Python 側にも MATLAB と同じ `binary_tree(n)` 型の初期化器を追加する。

### 3.5 突然変異

MATLAB 実装では、終端ノードの場合は値変更、内部ノードの場合は `series` / `parallel` の反転または部分木追加を行う。

Python 版の初期アダプタでは、まず安定性を優先し、選択した部分木をランダム部分木で置換する方式にしている。

これは雛型としての動作確認には十分だが、MATLAB 実装との忠実性を高める場合は、値変更、内部ノード反転、部分木追加の 3 種類を追加する。

## 4. まだ確認が必要な点

- 代表構造に対して、MATLAB 版と Python 版のインパルス応答積分がどの程度一致するか
- `terminal_elements` と `impulse_integral` の正規化範囲が、HV 計算に対して妥当か
- Python 版の初期木生成が、MATLAB 版と同程度の構造複雑さを生むか
- 突然変異の忠実度を上げる必要があるか
- 構造探索問題での `K = {1,3,5}` や population size / generation 数の初期設定をどう置くか

## 5. 現時点の結論

現時点では、添付 MATLAB の構造探索問題は、汎用多目的 GP 雛型へ適用可能な `StructuralSearchProblem` として実装済みである。

ただし、Python 版は MATLAB の完全再現ではなく、提案手法の評価に向けて多目的 GP として整えた初期アダプタである。今後の実験では、この差分を明記したうえで、まず Python 版の小規模実験を行い、必要に応じて MATLAB 実装に近づける。
