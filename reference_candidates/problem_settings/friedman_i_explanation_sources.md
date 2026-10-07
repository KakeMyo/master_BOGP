# Friedman-I / Friedman #1 理解用文献メモ

- 作成日: 2026-06-09
- 目的: 本研究で用いる Friedman-I 型シンボリック回帰問題を、原典・実装名・GP/SR 文脈の各観点から正しく説明するための文献整理
- 注意: 本研究で使っている式は scikit-learn などでは `Friedman #1` / `make_friedman1` と呼ばれる。一方で、GP/SR 文献の一部では同じ式を `Friedman-II` と呼ぶ例があるため、論文本文では必ず式を明示する。

## 1. 本研究で使う式

本研究の現在の Friedman-I 実験では、次の 5 変数式を用いる。

```tex
y =
10\sin(\pi x_1x_2)
+20(x_3-0.5)^2
+10x_4
+5x_5 .
```

実装上は、入力 \(x_j\) を一様分布から生成し、訓練 NRMSE と木サイズを 2 目的として最小化する。

## 2. 呼称ゆれ

### scikit-learn / 一般 ML 実装での呼称

scikit-learn の `make_friedman1` では、上記の sine-interaction 型の式を `Friedman #1` と呼ぶ。

この呼び方では、特徴量数は標準で 10 とされ、そのうち目的変数に実際に効くのは \(x_1,\ldots,x_5\) の 5 変数であり、残りは無関係変数として扱われる。

### GP/SR 文献での呼称

Burlacu et al. (2024) では、Friedman-I を additive 型、

```tex
f(\mathbf{x}) =
0.1e^{4x_1}
+ \frac{4}{1+e^{-20x_2+10}}
+3x_3+2x_4+x_5
```

とし、本研究で使っている sine-interaction 型を Friedman-II と呼んでいる。

したがって、論文本文では「Friedman-I」という名称だけに依存せず、必ず式を併記する。必要なら、次の表現を使う。

```text
本研究では，scikit-learn の make_friedman1 に対応する Friedman #1 型の合成回帰問題を用いる。
```

または、

```text
本研究では，以下の式で定義される Friedman 型合成回帰問題を用いる。
```

## 3. 採用候補文献

### [R26] Friedman (1991), Multivariate Adaptive Regression Splines

- 位置づけ: 原典
- 使い方:
  - Friedman 系合成回帰問題の原典として引用する。
  - この問題が単なる自作 toy problem ではなく、統計的学習・非線形回帰の文脈から来た標準的 synthetic benchmark であることを説明する。
- 注意:
  - 式の実装上の呼び方は、後続の実装系資料や二次文献と照合して書く。

### [R27] Breiman (1996), Bagging Predictors

- 位置づけ: 標準 ML benchmark としての利用例
- 使い方:
  - Friedman #1 が機械学習の古典的 benchmark として使われていることを補強する。
  - scikit-learn が Friedman (1991) とともに Breiman (1996) を参照しているため、実装上の `make_friedman1` に近い説明の補助文献として使う。
- 注意:
  - 主題は bagging であり、GP/SR の問題設定そのものではない。

### [R01] Burlacu, Yang, Affenzeller (2024), Population diversity and inheritance in genetic programming for symbolic regression

- 位置づけ: GP/SR 文脈で Friedman 系問題を使う例
- 使い方:
  - Friedman 系問題が GP symbolic regression の benchmark として使われることを示す。
  - 既知の目標式を持つ問題では、探索中に発見される subtree / building block を目標式の部分構造と対応づけられる、という説明に使う。
  - diversity や継承分析と Friedman 系問題の関係を説明する。
- 注意:
  - この文献では、本研究で使う sine-interaction 型を Friedman-II と呼んでいる。呼称ゆれの注意書きに使える。

### scikit-learn documentation, make_friedman1

- 位置づけ: 実装仕様確認
- URL: https://scikit-learn.org/stable/modules/generated/sklearn.datasets.make_friedman1.html
- 使い方:
  - 式、入力分布、無関係変数、ノイズ項の実装仕様を確認する。
  - ただし学術論文の正式参考文献というより、実装仕様確認用として扱う。

## 4. 採用判断

本研究の論文では、Friedman 型問題を次のように説明するのが安全である。

```tex
対象問題は，Friedman (1991) に由来する Friedman 系の合成回帰問題である。
本研究では，scikit-learn の make_friedman1 に対応する
\[
y=
10\sin(\pi x_1x_2)
+20(x_3-0.5)^2
+10x_4
+5x_5
\]
を用いる。
この問題は，非線形項，変数間相互作用，二次項，線形項を含み，
精度と式複雑さのトレードオフを評価する symbolic regression benchmark として扱いやすい。
```

## 5. 今後の推奨修正

- 論文本文では `Friedman-I` だけでなく、`Friedman #1 型` または `make_friedman1 型` と式を併記する。
- 実験設定表では、変数数を明確にする。
  - 現在の実装が 5 変数なら「5 relevant variables only」と明記する。
  - 10 変数版へ変更する場合は「5 relevant + 5 irrelevant variables」と明記する。
- Friedman 系問題の説明では [R26] を原典、[R27] を ML benchmark 補助、[R01] を GP/SR 文脈の補助として使う。
