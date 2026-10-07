# 研究ノート: 交叉率・突然変異率をベイズ最適化で動的に調整する遺伝的プログラミング

## 1. 研究テーマ

**テーマ**  
交叉率 $p_c$ と突然変異率 $p_m$ を、ベイズ最適化で動的に調整する閉ループ型遺伝的プログラミング手法の設計と評価

## 2. 背景

遺伝的プログラミング（GP）は、構造最適化、記号回帰、非線形モデリングなど多様な問題に用いられる。一方で、交叉率や突然変異率は探索挙動を大きく左右するにもかかわらず、実装上は固定値で与えられることが多い。

しかし実際には、

- 探索初期は多様性維持のため突然変異率を高めたい
- 中盤以降は有望解の組み替えを進めるため交叉率を高めたい
- 収束停滞時には再び探索性を戻したい

といったように、望ましい設定は世代や集団状態に応じて変化する。

このため、GP を「制御対象」、パラメータ調整器を「制御器」とみなす閉ループ設計が有効であると考えられる。本研究では、上位層にベイズ最適化（Bayesian Optimization, BO）を置き、GP の進化状態を観測しながら次の操作率と更新周期を提案する構造を採用する。

## 3. 目的

本研究では、最終的に望ましいパレートフロントまたは非劣解集合を得ることを目標とするため、対象とする GP は**多目的遺伝的プログラミング**である。

本研究の目的は、多目的 GP の交叉率、突然変異率、更新周期を固定値ではなく**世代状態に応じて自動的に更新される制御入力**として扱い、

- 収束性能
- 探索多様性
- 収束時間

のバランスを改善することである。

最終的には、固定率 GP や単純な時変スケジュール GP に対して、提案法がより安定して良いパレートフロントまたは解集合を得られるかを検証する。

## 4. 研究課題

### 4.1 中核課題

通常 GP で固定または手設計される $(p_c, p_m)$ と制御更新周期 $k$ を、ベイズ最適化により逐次調整可能な制御入力として扱う。

### 4.2 技術的な難しさ

単純に

$$
f(p_c, p_m, k)
$$

のみを BO で学習すると、「世代が進むほど有効な操作強度や更新周期が変わる」という時変性を取り込みにくい。探索初期、停滞期、収束期では、同じ $(p_c, p_m, k)$ でも得られる効果が異なるためである。

したがって、本研究では**文脈付き BO（contextual BO）として扱う方が自然**である。すなわち、現在の GP 状態 $c_t$ を入力に含め、

$$
r_t = g(c_t, p_c, p_m, k) + \varepsilon_t
$$

を学習し、現在の文脈 $c_t$ のもとで最良の操作率と更新周期を選ぶ。

## 5. 提案手法の具体化

## 5.1 閉ループ構造

- **プラント**: GP 本体
- **制御器**: BO
- **制御入力**: $u_t = [p_c, p_m, k]^\top$
- **観測量**: 多目的進化性能と多様性を表す指標
- **報酬**: 1 制御区間で得られた改善量をまとめたスカラー値

制御ループの流れは以下の通り。

1. 現在世代の GP 状態 $c_t$ を観測する
2. BO が現在文脈 $c_t$ のもとで次の $u_t = (p_c, p_m, k)$ を提案する
3. その設定で多目的 GP を $k$ 世代だけ実行する
4. 得られた改善量から報酬 $r_t$ を計算する
5. $(c_t, u_t, r_t)$ を BO に追加学習させる
6. 次区間の操作率と更新周期を再提案する

## 5.2 制御周期

当初案では「各世代を 1 実験」とみなす方針であるが、1 世代ごとの評価はノイズが大きく、BO の観測として不安定になりやすい。

そのため、正規版の提案法では、制御区間の長さを固定値として手で与えるのではなく、BO の行動に含まれる更新周期 $k$ として扱う。

- **更新周期**: $k \in \mathcal{K}$ の有限離散候補から BO が選択する
- 区間中は $p_c, p_m$ を固定する
- 区間終了時に HV 改善量、多様性、制御コストから報酬を集計して BO を更新する

この設計により、観測ノイズを軽減しつつ、状態が安定しているときは粗く、変化が大きいときは密に制御する適応的な更新周期を扱える。

## 5.3 観測文脈の設計

BO に渡す文脈ベクトル $c_t$ の候補は以下。

$$
c_t =
\left[
\tau_t,\;
HV_t,\;
\Delta HV_t,\;
D_t,\;
s_t,\;
b_t
\right]
$$

ここで、

- $\tau_t$: 正規化世代 $t / T$
- $HV_t$: 現在のハイパーボリューム
- $\Delta HV_t$: 直近区間におけるハイパーボリューム増加量
- $D_t$: 多様性指標
- $s_t$: 停滞世代数
- $b_t$: 平均木サイズまたは bloat 指標

### 推奨理由

- $\tau_t$ により探索初期と収束後半を区別できる
- $D_t$ により探索性不足を検知できる
- $\Delta HV_t$ と $s_t$ により停滞状態を検知できる
- $b_t$ により過度な木成長を抑制できる

### 指標選定の原則

文脈ベクトルに入れる指標は、多ければ良いわけではない。特に本研究では、1 回の制御区間ごとに 1 観測しか増えないため、BO 側の学習データ数は多くならない。そのため、以下の基準で絞り込むのが重要である。

- **制御との因果が近いこと**: 交叉率・突然変異率の変更で状態が変わりやすい指標を優先する
- **状態識別に効くこと**: 探索初期、収束期、停滞期、bloat 発生期を区別できること
- **低次元であること**: 文脈次元が大きすぎると GP 回帰の学習が不安定になる
- **追加計算が重すぎないこと**: 各制御区間で安定して測れること
- **正規化しやすいこと**: 問題ごとにスケールが大きく変わっても扱いやすいこと

以上を踏まえると、初期段階では「探索段階」「改善速度」「探索性」「停滞」「複雑化」をそれぞれ 1 指標ずつ持たせる構成が最もバランスが良い。

### 初期採用案

初期実装での推奨文脈ベクトルは、以下の 6 次元である。

$$
c_t =
\left[
\tau_t,\;
\widetilde{HV}_t,\;
\widetilde{\Delta HV}_t,\;
D^{\mathrm{struct}}_t,\;
\widetilde{s}_t,\;
\widetilde{b}_t
\right]
$$

ここで、

- $\tau_t$: 正規化世代。$\tau_t = t / T$
- $\widetilde{HV}_t$: 正規化した現在 HV
- $\widetilde{\Delta HV}_t$: 直近制御区間での HV 改善量を正規化した値
- $D^{\mathrm{struct}}_t$: 構造多様性
- $\widetilde{s}_t$: 正規化停滞長
- $\widetilde{b}_t$: 正規化平均木サイズまたは複雑度

現在の実装でも、この 6 次元を基本形として採用している。

### 各指標を採用する理由

#### 1. $\tau_t$: 進化段階を表す最小限の文脈

- **採用理由**: 探索初期と終盤では望ましい操作率が異なるため、世代進行を直接表す軸が必要である
- **良い点**:
  - 実装が簡単
  - 問題に依存しない
  - 探索期から収束期への大まかなモード遷移を表せる
- **代替候補との比較**:
  - 世代番号そのものは問題サイズ依存なので、正規化世代 $\tau_t$ の方が比較しやすい
  - 評価回数比率でもよいが、制御区間を世代単位で置く本研究では $\tau_t$ が自然である

#### 2. $\widetilde{HV}_t$: 現在どこまで到達しているかを表す性能レベル

- **採用理由**: 同じ $\Delta HV_t \approx 0$ でも、「まだ低性能で迷っている状態」と「ほぼ収束して頭打ちの状態」は区別したい
- **良い点**:
  - 現在の探索位置を性能面から表せる
  - $\tau_t$ だけでは捉えられない「進化の遅れ・進みすぎ」を表現できる
- **代替候補との比較**:
  - 最良適応度だけでは多目的性能を十分に表せない
  - 集団平均適応度は改善の兆候を平滑化しすぎることがある
  - 多目的 GP では HV の方が収束とフロント被覆を同時に要約しやすい

#### 3. $\widetilde{\Delta HV}_t$: いま改善できているかを表す局所速度

- **採用理由**: BO が次の率を決める上で重要なのは、「現在の状態そのもの」だけでなく、「直近で前進しているか止まりかけているか」である
- **良い点**:
  - 停滞の兆候を早めに反映できる
  - 次区間で探索性を上げるべきか、収束を進めるべきかの判断に効く
- **代替候補との比較**:
  - 現在 HV だけでは改善速度が分からない
  - 最良個体改善量だけだと多目的フロント全体の改善を見落とす
  - 単一世代差分はノイズが大きいため、制御区間単位で集計した $\Delta HV_t$ が本研究に合う

#### 4. $D^{\mathrm{struct}}_t$: 操作率が直接影響しやすい探索性指標

- **採用理由**: 交叉と突然変異が直接変えるのはプログラム構造であり、構造多様性はその影響を最も素直に受ける
- **良い点**:
  - GP の表現そのものに対応している
  - 問題依存性が低い
  - 追加の目的関数評価を必要としない
- **代替候補との比較**:
  - **意味多様性**は有用だが、入力サンプル上での振る舞い評価が必要で計算負荷が増える
  - **目的空間多様性**や crowding 指標はフロントの散らばりは見えるが、木構造の収縮や表現の偏りを捉えにくい
  - **ユニーク個体数**は計算が軽い一方で、距離情報がなく粗すぎる

したがって、初期段階では **構造多様性を第一候補** とし、必要に応じて意味多様性や目的空間多様性を追加比較するのがよい。

#### 5. $\widetilde{s}_t$: 一時的停滞と持続的停滞を分ける記憶変数

- **採用理由**: $\Delta HV_t$ が小さいだけでは、たまたま改善が小さかったのか、本当に停滞しているのか分からない
- **良い点**:
  - 停滞が続いていることを BO に伝えられる
  - 突然変異率を戻すべき場面の検知に効く
- **代替候補との比較**:
  - 移動平均改善量だけでは「連続して止まっている」情報が弱い
  - 停滞世代数は単純だが、制御判断に必要な履歴を短い形で保持できる

#### 6. $\widetilde{b}_t$: GP 特有の bloat を制御に反映するための複雑度指標

- **採用理由**: GP では性能改善が小さいのに木だけ大きくなることがあり、これは操作率選択に影響する重要な状態である
- **良い点**:
  - GP らしい問題設定に強く結び付いている
  - 報酬側の bloat ペナルティと整合する
  - 計算が軽い
- **代替候補との比較**:
  - 木深さだけでは一部の偏った成長に引っ張られやすい
  - intron 比率は理想的だが算出が複雑で初期実装には重い
  - 平均木サイズは近似的ではあるが、安定して測れて比較しやすい

### 多様性指標は何を使うか

多様性 $D_t$ については、候補を次の 3 種に分けて考えるとよい。

1. **構造多様性**
2. **意味多様性**
3. **目的空間多様性**

このうち、本研究の初期段階に最も適しているのは **構造多様性** である。

- 交叉・突然変異という制御対象が、まず木構造へ直接作用するため
- 評価関数を追加で回さなくてよく、制御区間ごとの観測が軽い
- 問題に依らず定義しやすく、比較実験でも使いやすい

一方で、意味多様性は「見た目は違うが振る舞いが同じ個体」を見抜けるため魅力的であり、将来的な拡張候補として価値が高い。目的空間多様性も多目的 GP では有用だが、これは主にフロント形状の話であり、操作率が直接変える構造探索の状態とは少し距離がある。

### 初期段階では見送る指標

以下の指標は有用性はあるが、初期の文脈には入れすぎない方がよい。

- **最良適応度のみ**: 多目的性能や集団全体の状態を落としやすい
- **集団平均適応度**: 改善の局所性がぼやけやすい
- **crowding distance のみ**: 目的空間の広がりには効くが、構造探索の詰まりを直接示しにくい
- **木深さのみ**: 一部の極端な個体に影響されやすい
- **指標の過剰投入**: BO の入力次元が増え、少数観測での学習が難しくなる

そのため、まずは 6 次元構成で始め、必要なら比較実験で

- $\widetilde{HV}_t$ を除いた 5 次元版
- $D^{\mathrm{struct}}_t$ を意味多様性に置き換えた版
- 目的空間多様性を追加した拡張版

を比較するのがよい。

### 5.3.1 文脈指標の具体的な計算式

初期実装では、各指標を以下のように正規化する。

$$
\tau_t = \frac{t}{T}
$$

$$
\widetilde{HV}_t
=
\mathrm{clip}
\left(
\frac{HV_t - HV_{\min}}{HV_{\max} - HV_{\min}},
0, 1
\right)
$$

初期段階では HV を $[0,1]$ に正規化できる問題設定を想定し、$HV_{\min}=0,\ HV_{\max}=1$ と置く。参照点設計が変わる場合は、この範囲も合わせて更新する。

$$
\widetilde{\Delta HV}_t
=
\mathrm{clip}
\left(
\frac{\Delta HV_t}{\delta_{HV}},
-1, 1
\right)
$$

ここで、$\delta_{HV}$ は改善量の基準スケールであり、初期値は $\delta_{HV}=0.03$ とする。これは「1 制御区間で十分に改善した」とみなす HV 増分の目安である。

$$
\widetilde{s}_t
=
\mathrm{clip}
\left(
\frac{s_t}{s_{\max}},
0, 1
\right)
$$

初期値として $s_{\max}=15$ を想定する。

$$
\widetilde{b}_t
=
\mathrm{clip}
\left(
\frac{\bar{L}_t}{L_{\mathrm{ref}}},
0, 1
\right)
$$

ここで、$\bar{L}_t$ は平均木サイズ、$L_{\mathrm{ref}}$ は複雑度の参照スケールであり、初期値は $L_{\mathrm{ref}}=100$ とする。

したがって、実装上の文脈ベクトルは

$$
c_t =
\left[
\frac{t}{T},\;
\widetilde{HV}_t,\;
\widetilde{\Delta HV}_t,\;
D_t,\;
\widetilde{s}_t,\;
\widetilde{b}_t
\right]
$$

とする。

### 5.3.2 構造多様性の具体的な定義

初期実装では、多様性指標として **構造多様性** を採用する。その定義は、Burlacu らの genotypic similarity に基づき、各個体間の構造類似度の平均から導く形にする。

2 個体 $T_i,\ T_j$ の構造類似度を

$$
Sim_g(T_i, T_j)
=
\frac{|M(T_i, T_j)|}{|T_i| + |T_j| - |M(T_i, T_j)|}
$$

と定める。

ここで、

- $|T_i|,\ |T_j|$ は木のノード数
- $|M(T_i, T_j)|$ は、同型な部分木の対応数

である。これは部分木集合に対する Jaccard 類似度に相当する。

集団 $P_t = \{T_1,\dots,T_N\}$ に対して、平均構造多様性を

$$
D_t^{\mathrm{struct}}
=
1
-
\frac{2}{N(N-1)}
\sum_{1 \le i < j \le N}
Sim_g(T_i, T_j)
$$

と定義する。

値域はおおむね $[0,1]$ であり、

- $0$ に近いほど集団の構造が似通っている
- $1$ に近いほど集団の構造がばらけている

と解釈できる。

### 5.3.3 構造多様性の実装方針

構造多様性の計算は、以下の手順で実装する。

1. 各個体木を prefix 表現へ変換する
2. 各ノードについて、子部分木のハッシュから bottom-up に部分木ハッシュを計算する
3. 各個体を「部分木ハッシュの multiset」として表す
4. 2 個体間で multiset の積集合サイズを取り、$|M(T_i,T_j)|$ を得る
5. 上式により $Sim_g(T_i,T_j)$ を計算し、平均して $D_t^{\mathrm{struct}}$ を求める

この方針を採用する理由は以下の通り。

- **木編集距離より軽い**: 厳密な tree edit distance は計算コストが高い
- **GP の木表現と相性が良い**: 部分木単位の一致を自然に扱える
- **交叉との対応がある**: 部分木交換を基本とする GP において、どれだけ構造部品を共有しているかを反映しやすい
- **問題依存性が低い**: 振る舞い評価用の入力サンプルを追加で必要としない

初期段階では全組合せ平均でよいが、集団サイズが大きくなった場合は個体対をサンプリングして近似してもよい。

### 5.3.4 多様性指標の詳細比較

#### 構造多様性

- **何を見るか**: 木構造、演算子、終端、部分木の違い
- **強み**:
  - 交叉率・突然変異率の変化が直接反映されやすい
  - 問題に依存せず計算できる
  - 文脈指標として軽量
- **弱み**:
  - 構造が違っても振る舞いが同じ個体は区別できない
  - 見た目の差を大きく見積もることがある

#### 意味多様性

意味多様性は、個体の**出力挙動**の違いを測る。個体 $T_i,\ T_j$ の出力ベクトルを $\mathbf{y}_i,\ \mathbf{y}_j$ とすると、Burlacu らに従って類似度を

$$
Sim_p(T_i, T_j)
=
\begin{cases}
1 & \sigma_i = \sigma_j = 0 \\
0 & \sigma_i = 0,\ \sigma_j \ne 0\ \text{or}\ \sigma_i \ne 0,\ \sigma_j = 0 \\
r^2(\mathbf{y}_i,\mathbf{y}_j) & \text{otherwise}
\end{cases}
$$

とし、意味多様性を $D^{\mathrm{sem}} = 1 - \overline{Sim_p}$ とできる。

- **何を見るか**: 同じ入力集合に対して、どれだけ異なる出力を返すか
- **強み**:
  - 見た目は違うが意味が同じ個体を見抜ける
  - 実際の探索挙動により近い情報を与えられる
- **弱み**:
  - 入力サンプル上での追加評価が必要
  - 問題依存性が高い
  - 制御区間ごとの観測コストが重くなりやすい

#### 目的空間多様性

目的空間多様性は、非劣解集合や集団の目的ベクトル $\mathbf{f}_i$ の散らばり具合を見る指標である。代表例として、crowding distance や近傍距離平均がある。

たとえば非劣解集合 $F_t$ に対し、最近傍距離ベースで

$$
D_t^{\mathrm{obj}}
=
\frac{1}{|F_t|}
\sum_{\mathbf{f}_i \in F_t}
\frac{\min_{j \ne i}\|\mathbf{f}_i - \mathbf{f}_j\|_2}
{\|\mathbf{f}_{\max} - \mathbf{f}_{\min}\|_2 + \varepsilon}
$$

のような指標を置くことができる。

- **何を見るか**: パレートフロント上での散らばり、被覆の均一性
- **強み**:
  - 多目的最適化の目的に直接対応する
  - front collapse を検知しやすい
- **弱み**:
  - 木構造そのものの探索状態は見えにくい
  - 文脈指標としては、交叉率・突然変異率との因果距離がやや遠い

### 5.3.5 本研究での採用順序

本研究では、初期段階では以下の順に採用する。

1. 文脈指標: **構造多様性**
2. 報酬・評価補助: 必要に応じて目的空間多様性を比較
3. 発展版: 意味多様性を追加し、構造多様性との差を比較する

この順にする理由は、まず BO 制御の成立性を確認したい段階では、計算負荷が軽く、操作率変更との関係が分かりやすい指標が適しているためである。

## 5.4 制御入力の制約

初期設定として、以下のような制約を置く。

- $p_c \in [0.55, 0.95]$
- $p_m \in [0.01, 0.30]$
- 必要なら $p_c + p_m \le 1.0$

さらに、急激な操作率変動で探索が不安定になることを避けるため、区間ごとの変化量にも制限を設ける。

- $|p_c^{(t+1)} - p_c^{(t)}| \le \Delta_{\max}$
- $|p_m^{(t+1)} - p_m^{(t)}| \le \Delta_{\max}$

初期値として $\Delta_{\max} = 0.10 \sim 0.15$ 程度を想定する。

## 5.5 目的関数の推奨設計

多目的 GP を主対象とする場合、報酬はハイパーボリューム増加量と多様性維持を両立させる形が自然である。初期実装では、以下のスカラー報酬を採用する。

$$
r_t =
w_{hv} \cdot \widetilde{\Delta HV}_t
+ w_d \cdot S_D(D_t, \tau_t)
- w_s \cdot S_{\mathrm{stag}}(s_t)
- w_b \cdot S_{\mathrm{bloat}}(b_t)
$$

ここで、

- $\widetilde{\Delta HV}_t$: 正規化したハイパーボリューム増加量
- $S_D$: 世代進行に応じた目標多様性との整合度
- $S_{\mathrm{stag}}$: 停滞ペナルティ
- $S_{\mathrm{bloat}}$: 木肥大化ペナルティ

### 目標多様性スケジュール

多様性そのものを最大化するのではなく、世代進行に応じて目標値を下げる。

$$
D^\ast(\tau) = D_{\mathrm{start}} - (D_{\mathrm{start}} - D_{\mathrm{end}})\tau
$$

例:

- $D_{\mathrm{start}} = 0.60$
- $D_{\mathrm{end}} = 0.20$

つまり、

- 初期は高多様性を維持
- 後半はある程度の収束を許容

という形にする。

### 推奨重みの初期値

- $w_{hv} = 0.55$
- $w_d = 0.25$
- $w_s = 0.10$
- $w_b = 0.10$

### 補足

本研究の本線は多目的 GP であり、最終的な報酬・評価は HV ベースで行う。もし初期段階でハイパーボリューム計算や多目的評価が重い場合のみ、制御器単体のデバッグ用として暫定的に

- 最良適応度改善量
- 集団平均適応度改善量
- 構造多様性

を用いた単目的版の簡易報酬で検証し、その後は必ず HV ベースの多目的評価に戻す。

## 5.6 BO モデル

初期実装では、以下を採用する。

- **回帰器**: Gaussian Process Regressor
- **カーネル**: Matern $\nu = 2.5$ + White noise
- **取得関数**: Expected Improvement (EI)
- **初期探索**: LHS または Sobol

その後、`k` を含む BO 制御器の詳細仕様として、[bo_controller_spec_v1.md](/Users/kakemyo/Downloads/master_BOGP/notes/bo_controller_spec_v1.md) を追加した。V1 では、文脈付き BO の問題設定を Krause and Ong の contextual GP bandit に基づけ [R12]、獲得関数は EGO / EI の古典的文献に基づき EI に固定する [R13]。また、更新周期 `k` は整数・離散変数であるため、単純に連続値特徴として GP に入れるのではなく、離散候補として列挙し、各 `k` に条件づけた surrogate を持つ設計とする [R14]。

現在文脈 $c_t$ を固定した上で、正規版では更新周期 $k$ も含めて

$$
(p_c, p_m, k)_{t+1}
=
\arg\max_{(p_c, p_m, k)}
\mathrm{EI}\left((c_t, p_c, p_m, k)\mid \mathcal{D}_t\right)
$$

として次区間の操作率と更新周期を選ぶ。BO 制御器詳細仕様 V1 では、`k` を直接連続入力として扱わず、各 `k` に条件づけた `EI_k(c_t,p_c,p_m)` を比較する設計に更新している。

## 5.7 なぜ「文脈なし BO」ではなく「文脈付き BO」か

文脈なし BO は

$$
r = f(p_c, p_m, k)
$$

を仮定するが、実際には同じ操作率・更新周期でも GP 状態に応じて効果が変わる。そのため、

- 早期探索で有効な操作強度と更新周期
- 停滞打破で有効な操作強度と更新周期
- 収束終盤で有効な操作強度と更新周期

が混ざって観測され、BO の近似対象が非定常になりやすい。

本研究では、この問題を避けるため、正規化世代、現在 HV、直近 HV 改善量、多様性、平均木サイズ、停滞長を文脈に含める。

## 5.8 実装上の段階分け

### 段階 1: 制御器単体の確認

まずは簡易シミュレータで、探索初期と終盤で最適率が変わる状況を人工的に作り、制御器が追従できるかを確認する。

### 段階 2: 実 GP へ接続

次に、DEAP などの GP 実装へ接続し、

- 個体群更新
- 評価
- 多様性計測
- HV 計測

を実際の進化計算に置き換える。

### 段階 3: 実験比較

以下の比較対象を置く。

1. 固定率 GP
2. 手設計の時変スケジュール GP
3. 文脈なし BO
4. 提案法: 文脈付き BO

## 6. 評価指標

主指標として以下を用いる。

- 最終ハイパーボリューム
- 実行中の平均多様性
- 所定 HV 到達までの世代数
- 停滞発生頻度
- 平均木サイズ

必要に応じて補助指標として以下も記録する。

- ベスト個体の複雑さ
- BO が提案した $(p_c, p_m, k)$ の時系列
- 報酬値の時系列

## 7. 実験条件の初期案

- 実装言語: Python
- GP ライブラリ候補: DEAP
- BO 実装: scikit-learn の GPR をベースに自作制御器
- 更新周期: BO が候補集合 $\mathcal{K}$ から `k` を選択
- 初期設計点数: `k` ごとに balanced warm-up 点を配置
- 候補評価点数: 512 点

## 8. 現時点の設計方針まとめ

現時点では、以下の方針を採る。

1. 外側 BO の行動は `(p_c, p_m, k)` とし、操作率だけでなく次回更新までの世代数 `k` も制御対象に含める
2. 1 世代ごとの更新ではなく、`k` 世代ごとの状態依存・区間制御にする
3. 文脈なし BO ではなく、現在状態を入力に含む文脈付き BO として扱う
4. 目的関数は「世代あたり HV 改善量」を主、多様性維持を副、制御コストを弱い抑制項とする
5. 状態変数には、進行率、現在 HV、直近改善量、多様性、平均木サイズ、停滞長を含める
6. 急激な率変動や非現実的な設定を避けるため、入力空間と更新幅に制約を置く

この時点の固定仕様を 1 ページに圧縮した別紙として、検討用ラフ版 [proposed_method_rough.md](/Users/kakemyo/Downloads/master_BOGP/notes/proposed_method_rough.md) を作成した。

その後、`k` を含む混合空間同時最適化、区間平均多様性、`f(x,p_c,p_m,k)` を学習対象とする点まで固定した**正規版仕様メモ**として、[proposed_method_spec_v1.md](/Users/kakemyo/Downloads/master_BOGP/notes/proposed_method_spec_v1.md) を参照元にする。

### 8.1 ブラッシュアップ後の研究計画

参考文献取得ルールに照らして見直すと、本研究は「GP の操作率を BO で調整する」だけではなく、次の 4 つを一貫して示す研究として整理した方が強い。

1. **問題設定**: GP の交叉率・突然変異率は探索段階や集団状態によって望ましい値が変わるため、固定率では状態依存性を扱いにくい。
2. **提案**: 現在の進化状態を文脈 $x_\ell$ として観測し、BO が区間ごとに $(p_c,p_m,k)$ を提案する閉ループ制御として定式化する。
3. **設計根拠**: 文脈には、進化段階、HV、HV 改善量、構造多様性、停滞、bloat を入れ、報酬では世代あたり性能改善、多様性維持、制御更新コストを同時に扱う [R01][R05][R08][R09][R10]。
4. **検証**: 固定率、手設計スケジュール、文脈なし BO と比較し、「状態を見ること」と「更新周期も制御すること」が最終性能、安定性、探索挙動の解釈性に効くかを検証する。

### 8.2 研究上の主張

論文化を意識した場合、主張は以下の形に絞る。

- **主張 1**: GP の操作率制御は、単なるハイパーパラメータ最適化ではなく、進化過程に依存する逐次制御問題として扱える。
- **主張 2**: 文脈付き BO は、同じ $(p_c,p_m,k)$ でも進化状態によって効果が変わる問題を、文脈なし BO より自然に扱える。
- **主張 3**: 提案法は、操作強度 `(p_c,p_m)` だけでなく更新周期 `k` も状態依存で切り替える適応制御として定義できる。
- **主張 4**: 構造多様性、停滞、bloat を観測と報酬に入れることで、最終性能だけでなく探索過程の健全性も制御対象にできる。
- **主張 5**: 提案法の価値は、最終 HV の向上だけでなく、率と更新周期の時系列、停滞時の反応、多様性低下時の挙動を説明できる点にもある。

### 8.3 研究質問

研究質問は、次のように明示する。

- **RQ1**: 提案法は固定率 GP や手設計スケジュール GP より、最終 HV または解集合品質を改善するか。
- **RQ2**: 文脈付き BO は、文脈なし BO より安定して良い操作率を選べるか。
- **RQ3**: 文脈ベクトルのうち、構造多様性、停滞、bloat は操作率制御にどの程度寄与するか。
- **RQ4**: 提案法が学習する $(p_c,p_m)$ の時系列は、探索初期、停滞期、収束期で解釈可能な変化を示すか。
- **RQ5**: BO 制御の計算オーバーヘッドは、得られる性能改善に対して許容できるか。

### 8.4 仮説

初期仮説は以下とする。

- **H1**: 文脈付き BO は、固定率 GP より最終 HV と HV-AUC を改善する。
- **H2**: 文脈付き BO は、文脈なし BO より run 間のばらつきが小さい。
- **H3**: 構造多様性を文脈に含めると、多様性 collapse と長期停滞が減る。
- **H4**: bloat ペナルティを入れると、最終性能を大きく落とさず平均木サイズを抑えられる。
- **H5**: 更新周期 `k` を制御対象に含めることで、毎世代更新より少ない制御回数で同等以上の HV 改善と多様性維持を達成できる。

### 8.5 先行研究調査の不足箇所

現在の文献は、多様性、semantic GP、bloat、多目的 GP の根拠は比較的そろっている。一方で、研究計画を強くするには、参考文献ルールに従って次の領域を追加で調査する必要がある。

| 優先度 | 分類 | 必要な文献 | 使い道 |
|---|---|---|---|
| 高 | A: 中核 | GP の操作率、operator probability、adaptive parameter control | 固定率を動的制御へ拡張する必然性 |
| 高 | A: 中核 | 進化計算の parameter control / online algorithm configuration | 既存の制御・設定調整研究との差分 |
| 高 | B: 設計根拠 | contextual BO の基礎または応用 | 文脈付き BO を採用する理論的根拠 |
| 中 | C: 比較対象 | BO による evolutionary algorithm tuning | 文脈なし BO baseline の妥当性 |
| 中 | C: 比較対象 | evolutionary computation の統計比較・ベンチマーク方法 | run 数、検定、効果量の設計 |
| 中 | B: 設計根拠 | stagnation detection / restart / diversity recovery | 停滞指標と突然変異率再上昇の根拠 |

次回の文献追加では、上表を優先順位として `references/README.md` の文献番号台帳へ追加する。

### 8.6 実験計画の改訂案

実験は、次の段階で進める。

#### 段階 0: 先行研究の穴を埋める

- GP の adaptive parameter control、進化計算の online configuration、contextual BO の中核文献を追加する。
- 各文献は `[Rxx]` として採番し、どの研究質問に対応するかを研究ノートへ追記する。

#### 段階 1: toy engine で制御器の妥当性を確認する

- 目的: BO 制御器が、状態によって最適率が変わる環境で追従できるかを確認する。
- 比較: 固定率、時変スケジュール、ランダム制御、文脈なし BO、文脈付き BO。
- 追加検証: 更新周期候補集合 $\mathcal{K}$、warmup 点数、候補点数、平滑化係数の感度を見る。

#### 段階 2: 実 GP エンジンへ接続する

- 初期対象は記号回帰とし、目的は予測誤差と木サイズの 2 目的にする。
- DEAP 個体から prefix token を生成し、構造多様性を現在の `src/bogp/diversity.py` へ接続する。
- HV、構造多様性、平均木サイズ、停滞世代数を区間単位で記録する。

#### 段階 3: baseline 比較を行う

- 固定率 GP: 代表的な固定設定と、事前グリッドで選んだ強い固定設定を置く。
- 手設計スケジュール GP: 初期は高突然変異、後半は高交叉へ寄せる単純スケジュールを置く。
- 文脈なし BO: 入力を $(p_c,p_m)$ のみにした BO を置く。
- 提案法: $c_t$ と $(p_c,p_m)$ を入力にする文脈付き BO を置く。

#### 段階 4: ablation を行う

- 文脈 ablation: `tau + HV + DeltaHV` のみ、構造多様性あり、停滞あり、bloat ありを比較する。
- 報酬 ablation: HV のみ、HV + 多様性、HV + 多様性 + bloat、全項入りを比較する。
- 制約 ablation: 操作率の更新幅制限あり・なしを比較する。

#### 段階 5: 統計的に評価する

- 各条件を複数 seed で実行し、同じ評価回数予算で比較する。
- 主指標は最終 HV、HV-AUC、所定 HV 到達世代、平均木サイズ、停滞発生頻度とする。
- 補助指標として、$(p_c,p_m)$ の時系列、多様性時系列、BO 報酬時系列、実行時間を保存する。
- 統計比較では平均だけでなく中央値、信頼区間、効果量も確認する。

### 8.7 成功条件

提案法が研究として成立したと言える最低条件は、次のいずれかを満たすことである。

- 固定率または手設計スケジュールに対して、最終 HV または HV-AUC が一貫して改善する。
- 最終性能が同等でも、平均木サイズ、停滞頻度、run 間ばらつきが改善する。
- 文脈なし BO より、停滞時や多様性低下時の率変更が解釈しやすい。
- ablation により、構造多様性、停滞、bloat のいずれかが制御判断に寄与することを示せる。

### 8.8 リスクと対策

| リスク | 起きる問題 | 対策 |
|---|---|---|
| 文脈次元が多い | BO の観測数に対して学習が不安定になる | 6 次元を基本にし、ablation で低次元版を比較する |
| 報酬設計が複雑 | 最終性能より報酬 shaping に最適化される | 最終 HV と HV-AUC を主指標として分けて評価する |
| bloat ペナルティと木サイズ目的が重複 | 木サイズを過度に抑えて性能が落ちる | bloat 項あり・なしを比較する |
| HV 参照点が不適切 | 問題間比較が歪む | 問題ごとに参照点を固定し、設定をログに残す |
| BO の計算負荷が重い | GP 本体より制御器がボトルネックになる | 候補点数、更新頻度、実行時間を補助指標として記録する |
| 先行研究との差分が弱い | 新規性が曖昧になる | adaptive GP、online configuration、contextual BO の中核文献を優先的に追加する |

### 8.9 直近の作業順序

1. 参考文献ルールに従い、adaptive GP operator control、online algorithm configuration、contextual BO の中核文献を追加する。
2. toy engine に固定率、時変スケジュール、文脈なし BO の baseline runner を追加する。
3. DEAP 接続の最小実装を作り、記号回帰で `error` と `tree size` の 2 目的を測れるようにする。
4. 構造多様性、HV、停滞、bloat、操作率時系列を CSV または JSONL で保存する。
5. まず小規模 seed で smoke 実験を行い、その後 run 数を増やして統計比較へ進む。

### 8.10 実装状況に基づく補足レビュー

研究計画を実装状況と照らすと、現在は「文脈付き BO 制御の最小骨格」はすでにできている。具体的には、BO 制御器、閉ループ実行器、文脈ベクトル、報酬関数、toy engine、構造多様性計算、smoke test は実装済みである。

一方で、研究として次に必要なのは、提案法そのものを増やすことではなく、比較可能な実験単位へ落とすことである。したがって直近では、以下を優先する。

1. 先行研究補強: adaptive GP operator control、evolutionary parameter control、contextual BO の中核文献を `[R12]` 以降として追加する。
2. baseline 整備: toy engine 上で固定率、時変スケジュール、ランダム制御、文脈なし BO、文脈付き BO を同じログ形式で比較できるようにする。
3. ログ形式の固定: 各制御区間の `generation`, `p_c`, `p_m`, `k`, `HV`, `DeltaHV`, `diversity`, `stagnation`, `tree_size`, `reward` を CSV または JSONL で保存する。
4. 実 GP 接続: DEAP の記号回帰を最小対象とし、予測誤差と木サイズの 2 目的で HV を測る。
5. ablation へ進む条件: baseline 比較が同じ seed 群で再現可能になってから、文脈・報酬項の ablation を追加する。

この補足レビューの詳細は [research_brushup_2026-04-21.md](/Users/kakemyo/Downloads/master_BOGP/notes/research_brushup_2026-04-21.md) にまとめる。

### 8.11 研究の進め方仕様

今後の研究は、[research_process_spec.md](/Users/kakemyo/Downloads/master_BOGP/notes/research_process_spec.md) を運用仕様として進める。

この仕様書では、文献調査、研究質問、実装、実験、分析、論文化を一連の研究単位として扱い、各段階の完了条件と品質ゲートを定める。更新済みの参考文献ルールに従い、オープンアクセス文献と Elsevier / ScienceDirect 文献を同列候補として評価し、直接取得できない Elsevier 文献は手動ダウンロード候補として管理する。

## 9. 今後の追記ルール

以後このノートには、実装・変更・実験・失敗・改善点を時系列で追記する。

各ログには最低限、以下を書く。

- 何をしたか
- なぜそうしたか
- どのファイルや設定を変えたか
- 実行結果や確認方法
- 次に何をすべきか

## 10. 参考文献

### 10.1 文献フォルダ

- 文献は [references/README.md](/Users/kakemyo/Downloads/master_BOGP/references/README.md) を起点に管理する
- 参考文献調査・取得・研究ノート反映の詳細仕様は [reference_workflow_spec.md](/Users/kakemyo/Downloads/master_BOGP/references/reference_workflow_spec.md) に置く
- オープンアクセスまたは Elsevier / ScienceDirect から本文確認できるものは、同列の優先候補として扱う
- PDF が取得できたものは `references/` に保存する
- Elsevier 上で論文情報は確認できるが直接ダウンロードできない文献は、手動ダウンロード候補として、タイトル、著者、年、掲載誌、巻号ページ、DOI、URL、要点、採用理由、想定利用箇所、推奨検索クエリを残す
- 本文確認できないが重要な文献は、同名の `.md` メモに DOI、出典、確認できた範囲、保留理由または手動取得待ちであることを残す
- 研究ノート内では作業用文献番号 `[R01]`, `[R02]`, ... を使い、論文原稿に移す段階で投稿先形式に変換する

### 10.2 本研究で特に参照した文献と用途

- [R01] Burlacu, Yang, Affenzeller (2024) [Population diversity and inheritance in genetic programming for symbolic regression.md](/Users/kakemyo/Downloads/master_BOGP/references/Population%20diversity%20and%20inheritance%20in%20genetic%20programming%20for%20symbolic%20regression.md)
  - 参照箇所: 5.3.2, 5.3.3, 5.3.4
  - 参照内容: 構造類似度 `Sim_g` の Jaccard 型定義、意味類似度 `Sim_p` の二乗相関定義

- [R02] Vanneschi, Castelli, Silva (2014) [A survey of semantic methods in genetic programming.md](/Users/kakemyo/Downloads/master_BOGP/references/A%20survey%20of%20semantic%20methods%20in%20genetic%20programming.md)
  - 参照箇所: 5.3 の多様性指標比較
  - 参照内容: semantic methods の分類、semantic diversity を将来拡張候補とする位置づけ

- [R03] Moraglio, Krawiec, Johnson (2012) [Geometric Semantic Genetic Programming.md](/Users/kakemyo/Downloads/master_BOGP/references/Geometric%20Semantic%20Genetic%20Programming.md)
  - 参照箇所: 5.3.4 意味多様性の説明
  - 参照内容: semantics を挙動空間として捉える視点

- [R04] Nguyen et al. (2013) [On the roles of semantic locality of crossover in genetic programming.md](/Users/kakemyo/Downloads/master_BOGP/references/On%20the%20roles%20of%20semantic%20locality%20of%20crossover%20in%20genetic%20programming.md)
  - 参照箇所: 5.3.4 意味多様性の説明
  - 参照内容: semantic distance と semantic locality の重要性、fitness cases 上で semantics を測る考え方

- [R05] Burke, Gustafson, Kendall (2004) [Diversity in Genetic Programming - An Analysis of Measures and Correlation With Fitness.md](/Users/kakemyo/Downloads/master_BOGP/references/Diversity%20in%20Genetic%20Programming%20-%20An%20Analysis%20of%20Measures%20and%20Correlation%20With%20Fitness.md)
  - 参照箇所: 5.3 の指標選定原則と比較
  - 参照内容: GP における diversity measure 比較の必要性

- [R06] Burks, Punch (2015) [An Efficient Structural Diversity Technique for Genetic Programming.md](/Users/kakemyo/Downloads/master_BOGP/references/An%20Efficient%20Structural%20Diversity%20Technique%20for%20Genetic%20Programming.md)
  - 参照箇所: 5.3.3 構造多様性の実装方針
  - 参照内容: 構造多様性を効率よく扱う必要性

- [R07] Gustafson, Vanneschi (2008) [Crossover-Based Tree Distance in Genetic Programming.md](/Users/kakemyo/Downloads/master_BOGP/references/Crossover-Based%20Tree%20Distance%20in%20Genetic%20Programming.md)
  - 参照箇所: 5.3.3 構造多様性の実装方針
  - 参照内容: 木距離は探索演算子との関係も踏まえるべきという視点

- [R08] Javed, Gobet, Lane (2022) [Simplification of genetic programs - a literature survey.md](/Users/kakemyo/Downloads/master_BOGP/references/Simplification%20of%20genetic%20programs%20-%20a%20literature%20survey.md)
  - 参照箇所: 5.3 の bloat 指標、5.5 の bloat ペナルティ
  - 参照内容: size/depth/simplification と bloat の関係

- [R09] Deb et al. (2002) [A fast and elitist multi-objective genetic algorithm - NSGA-II.md](/Users/kakemyo/Downloads/master_BOGP/references/A%20fast%20and%20elitist%20multi-objective%20genetic%20algorithm%20-%20NSGA-II.md)
  - 参照箇所: 5.3.4 目的空間多様性の説明
  - 参照内容: crowding distance を含む objective-space diversity の基本的な考え方

- [R10] Dou, Rockett (2018) [Comparison of semantic-based local search methods for multiobjective genetic programming.md](/Users/kakemyo/Downloads/master_BOGP/references/Comparison%20of%20semantic-based%20local%20search%20methods%20for%20multiobjective%20genetic%20programming.md)
  - 参照箇所: 5.3.4 と 5.5
  - 参照内容: 多目的 GP では tree size と精度の両方が重要であること

- [R11] Krawiec (2014) [Genetic programming - where meaning emerges from program code.md](/Users/kakemyo/Downloads/master_BOGP/references/Genetic%20programming%20-%20where%20meaning%20emerges%20from%20program%20code.md)
  - 参照箇所: 5.3.4 意味多様性の背景
  - 参照内容: semantics を program behavior として捉える背景説明

- [R12] Krause, Ong (2011) [Contextual Gaussian Process Bandit Optimization.md](/Users/kakemyo/Downloads/master_BOGP/references/Contextual%20Gaussian%20Process%20Bandit%20Optimization.md)
  - 参照箇所: 5.6 BO モデル、BO 制御器詳細設計仕様 V1
  - 参照内容: 文脈を観測し、その文脈の下で行動を選択する contextual GP bandit / contextual BO の問題設定

- [R13] Jones, Schonlau, Welch (1998) [Efficient Global Optimization of Expensive Black-Box Functions.md](/Users/kakemyo/Downloads/master_BOGP/references/Efficient%20Global%20Optimization%20of%20Expensive%20Black-Box%20Functions.md)
  - 参照箇所: 5.6 BO モデル、BO 制御器詳細設計仕様 V1
  - 参照内容: 高コスト black-box 最適化における EGO と Expected Improvement、EI の閉形式、space-filling / Latin hypercube design による初期設計点生成
  - 確認状況: 2026-06-08 に添付 PDF の本文を確認し、PDF を `references/` に保存した

- [R14] Garrido-Merchan, Hernandez-Lobato (2020) [Dealing with categorical and integer-valued variables in Bayesian Optimization with Gaussian processes.md](/Users/kakemyo/Downloads/master_BOGP/references/Dealing%20with%20categorical%20and%20integer-valued%20variables%20in%20Bayesian%20Optimization%20with%20Gaussian%20processes.md)
  - 参照箇所: 5.6 BO モデル、BO 制御器詳細設計仕様 V1
  - 参照内容: GP ベース BO におけるカテゴリ・整数変数の扱いと単純な丸め・one-hot encoding の問題、離散値を考慮した covariance / kernel 設計の必要性
  - 確認状況: 2026-06-08 に添付 PDF の本文を確認し、PDF を `references/` に保存した

- [R15] Audet et al. (2021) [Performance indicators in multiobjective optimization.md](/Users/kakemyo/Downloads/master_BOGP/references/Performance%20indicators%20in%20multiobjective%20optimization.md)
  - 参照箇所: 多目的評価プロトコル、Pareto archive の性能分析
  - 参照内容: Pareto front 近似の評価指標を cardinality、convergence、distribution/spread などへ分ける考え方

- [R16] Li, Yao (2019) [Quality evaluation of solution sets in multiobjective optimisation - a survey.md](/Users/kakemyo/Downloads/master_BOGP/references/Quality%20evaluation%20of%20solution%20sets%20in%20multiobjective%20optimisation%20-%20a%20survey.md)
  - 参照箇所: 多目的評価プロトコル、指標選定の注意点
  - 参照内容: 解集合品質評価の総説として、convergence、diversity、coverage、cardinality、preference-aware evaluation を整理する根拠

- [R17] Guerreiro, Fonseca, Paquete (2021) [The Hypervolume Indicator - Computational Problems and Algorithms.md](/Users/kakemyo/Downloads/master_BOGP/references/The%20Hypervolume%20Indicator%20-%20Computational%20Problems%20and%20Algorithms.md)
  - 参照箇所: HV 計算、Pareto archive 評価、`src/bogp/test_v1_hypervolume.py`
  - 参照内容: HV の理論的性質、計算上の注意、参照点と正規化を固定して比較する必要性

- [R18] Galvan et al. (2022) [Semantics in Multi-objective Genetic Programming.md](/Users/kakemyo/Downloads/master_BOGP/references/Semantics%20in%20Multi-objective%20Genetic%20Programming.md)
  - 参照箇所: 多目的 GP の比較実験、Diversity と HV の関係
  - 参照内容: MOGP で平均 HV と統計的有意性を用いて Pareto 近似解集合を評価する近年の実例

- [R19] Li, Chen, Yao (2022) [How to evaluate solutions in Pareto-based search-based software engineering.md](/Users/kakemyo/Downloads/master_BOGP/references/How%20to%20evaluate%20solutions%20in%20Pareto-based%20search-based%20software%20engineering.md)
  - 参照箇所: 多目的評価プロトコル、評価指標の使い分け
  - 参照内容: 問題特性や意思決定者の選好に応じて Pareto 解集合の評価方法を選ぶべきという方法論的注意

- [R20] Verma, Pant, Snasel (2021) [A Comprehensive Review on NSGA-II for Multi-Objective Combinatorial Optimization Problems.md](/Users/kakemyo/Downloads/master_BOGP/references/A%20Comprehensive%20Review%20on%20NSGA-II%20for%20Multi-Objective%20Combinatorial%20Optimization%20Problems.md)
  - 参照箇所: NSGA-II の関連研究説明、実験手法における NSGA-II 型の非優越ソート・多様性維持選択の背景説明
  - 参照内容: NSGA-II が多目的最適化で広く利用されていること、conventional / modified / hybrid NSGA-II の分類、性能指標・統計検定・case study・benchmarking などの評価慣行
  - 注意: 原典の主張や正確なアルゴリズム定義には Deb et al. (2002) [R09] を併用し、本論文は総説・補強文献として使う

- [R21] Eiben, Hinterding, Michalewicz (1999) [Parameter control in evolutionary algorithms.md](/Users/kakemyo/Downloads/master_BOGP/references/Parameter%20control%20in%20evolutionary%20algorithms.md)
  - 参照箇所: 第1章「はじめに」の固定率では不十分な理由，提案法を parameter tuning ではなく parameter control として位置づける説明
  - 参照内容: パラメータを実行前に固定する tuning と，実行中に変更する control の区別，deterministic / adaptive / self-adaptive control の古典的分類
  - 確認状況: 2026-06-08 に CiNii，DOI，大学PDFを確認し，PDF を `references/` に保存した

- [R22] Karafotias, Hoogendoorn, Eiben (2015) [Parameter Control in Evolutionary Algorithms - Trends and Challenges.md](/Users/kakemyo/Downloads/master_BOGP/references/Parameter%20Control%20in%20Evolutionary%20Algorithms%20-%20Trends%20and%20Challenges.md)
  - 参照箇所: 第1章「はじめに」の探索初期・終盤で望ましい値が変わるという説明，関連研究における parameter control の動向整理
  - 参照内容: parameter control 研究の近年動向，探索段階や問題状態に応じて EA パラメータを変える考え方，方法論上の課題
  - 確認状況: 2026-06-08 に添付PDFの本文を確認し，PDF を `references/` に保存した

- [R23] Aleti, Moser (2016) [A systematic literature review of adaptive parameter control methods for evolutionary algorithms.md](/Users/kakemyo/Downloads/master_BOGP/references/A%20systematic%20literature%20review%20of%20adaptive%20parameter%20control%20methods%20for%20evolutionary%20algorithms.md)
  - 参照箇所: 第1章「はじめに」の「問題依存・探索段階依存で固定率が不十分」という説明，BO制御器をフィードバック型調整器として説明する部分
  - 参照内容: adaptive parameter control の体系的レビュー，mutation rate，crossover rate，population size などが調整対象になること，探索中のフィードバックに基づき値を変える考え方
  - 確認状況: 2026-06-08 に添付PDFの本文を確認し，PDF を `references/` に保存した

- [R24] Niehaus, Banzhaf (2001) [Adaption of Operator Probabilities in Genetic Programming.md](/Users/kakemyo/Downloads/master_BOGP/references/Adaption%20of%20Operator%20Probabilities%20in%20Genetic%20Programming.md)
  - 参照箇所: 第1章「はじめに」の GP では操作率が自由パラメータになりやすいこと，操作率適応の直接先行研究としての説明
  - 参照内容: GP における genetic operator probability を適応させる先行研究，symbolic regression と classification での実験，経験的パラメータ設定への依存を減らす問題意識
  - 確認状況: 2026-06-08 に GP bibliography，DOI を確認し，ユーザー添付の Springer/LNCS PDF pp.325-336 を本文確認した。PDF を `references/` に保存した

- [R25] Oh, Suh, Ahn (2021) [Self-Adaptive Genetic Programming for Manufacturing Big Data Analysis.md](/Users/kakemyo/Downloads/master_BOGP/references/Self-Adaptive%20Genetic%20Programming%20for%20Manufacturing%20Big%20Data%20Analysis.md)
  - 参照箇所: 第1章「はじめに」の GP 交叉率・突然変異率を動的に扱う具体例，平均木サイズ・複雑さを制御状態に含める根拠
  - 参照内容: GP の交叉・突然変異確率を木構造の複雑さに応じて自己適応させる実例，精度と解釈性・複雑さのバランスを扱う設計
  - 確認状況: 2026-06-08 に MDPI ページと GIST 機関リポジトリPDFを確認し，PDF を `references/` に保存した

- [R26] Friedman (1991) [Multivariate Adaptive Regression Splines.md](/Users/kakemyo/Downloads/master_BOGP/references/Multivariate%20Adaptive%20Regression%20Splines.md)
  - 参照箇所: Friedman 系合成回帰問題の原典説明，Friedman-I / Friedman #1 型 symbolic regression の実験設定
  - 参照内容: Friedman 系 synthetic regression benchmark の原典，非線形回帰・相互作用を含む合成問題としての位置づけ
  - 確認状況: 2026-06-09 に CiNii，Project Euclid，Stanford technical report metadata を確認し，大学講義ページ上の PDF を `references/` に保存した

- [R27] Breiman (1996) [Bagging Predictors.md](/Users/kakemyo/Downloads/master_BOGP/references/Bagging%20Predictors.md)
  - 参照箇所: Friedman #1 が標準的な機械学習 benchmark として使われていることの補助説明
  - 参照内容: Friedman simulated regression data sets を古典的 ML 実験で用いる例，Friedman #1 の benchmark としての普及
  - 確認状況: 2026-06-09 に Springer，CiNii metadata を確認し，Springer PDF を `references/` に保存した

- [R28] Harrison, Alderliesten, Bosman (2025) [A Better Multi-Objective GP-GOMEA - But do we Need it.md](/Users/kakemyo/Downloads/master_BOGP/references/A%20Better%20Multi-Objective%20GP-GOMEA%20-%20But%20do%20we%20Need%20it.md)
  - 参照箇所: HV-AUC / HV推移を用いた収束性評価の位置づけ，MOGP / GP-GOMEA におけるHV評価の近接事例
  - 参照内容: Symbolic Regression の MOGP / GP-GOMEA で average hypervolume を評価に用い，世代方向および時間方向の average hypervolume を比較していること
  - 注意: `HV-AUC` という名称や曲線下面積指標を直接定義している文献ではないため，本研究では「HV-AUCの直接根拠」ではなく「HV推移による性能評価の近接根拠」として扱う
  - 確認状況: 2026-06-12 に arXiv，ACM DOI，PDF本文を確認し，PDF を `references/` に保存した

- [R29] White et al. (2013) [Better GP Benchmarks - Community Survey Results and Proposals.md](/Users/kakemyo/Downloads/master_BOGP/references/Better%20GP%20Benchmarks%20-%20Community%20Survey%20Results%20and%20Proposals.md)
  - 参照箇所: 修論本実験の問題選定，長期探索型symbolic regression benchmark
  - 参照内容: 易しい低次多項式だけの評価を避けること，問題選定でcherry-pickingをしないこと，Vladislavleva-4・Korns-12・Keijzer-6等の式、次元、train/test sampling
  - 確認状況: 2026-09-03 に Springer DOI，GP Benchmarks community site，著者・community版PDF本文を確認し，PDFを `references/` に保存した

- [R30] Liu, Virgolin, Alderliesten, Bosman (2022) [Evolvability Degeneration in Multi-Objective Genetic Programming for Symbolic Regression.md](/Users/kakemyo/Downloads/master_BOGP/references/Evolvability%20Degeneration%20in%20Multi-Objective%20Genetic%20Programming%20for%20Symbolic%20Regression.md)
  - 参照箇所: accuracy--size MOGPの問題設定，Airfoil/Concrete等の実データ候補，提案法の文脈指標と停滞機序
  - 参照内容: NSGA-II型MOGPで小さい木が初期に過剰複製されevolvabilityが低下すること，75/25 split、train-only標準化、hard size cap 100、外部archive、HV、30反復の実験設定
  - 注意: 通常NSGA-IIが最初の十数世代で停滞する例であり，Airfoilを採用するだけで18世代後の改善が保証されるわけではない。controller-blind pilotでheadroomを確認する
  - 確認状況: 2026-09-03 に ACM DOI，arXiv，TU Delft機関リポジトリ，PDF本文を確認し，PDFを `references/` に保存した

### 10.2.1 問題設定用文献の取得状況

2026-10-01の問題設定用文献整理では、採用済み[R10][R24][R25][R28][R29][R30]を[目的別フォルダ](../references/problem_settings/README.md)に同一PDFの閲覧コピーとしてまとめた。直下原本と番号は変更していない。

未正式採用文献は以下の3件を別管理する。

- LH01 Vladislavleva et al. (2009): [メタデータ](../references/Order%20of%20Nonlinearity%20as%20a%20Complexity%20Measure%20for%20Models%20Generated%20by%20Symbolic%20Regression%20via%20Pareto%20Genetic%20Programming.md)。UBall5Dの原条件確認用。本文未取得であり、具体的な標本仕様の根拠には使わない。
- LH02 Ni et al. (2013): [メタデータ](../references/The%20Use%20of%20an%20Analytic%20Quotient%20Operator%20in%20Genetic%20Programming.md)。AQ・難問条件確認用。本文未取得であり、未確認の条件は本番仕様へ使わない。
- LH03 Zhang et al. (2025): [メタデータ](../references/A%20Multi-Objective%20Genetic%20Programming%20with%20Size%20Diversity%20for%20Symbolic%20Regression%20Problem.md)。Brunel機関リポジトリ版本文を取得。1000世代の評価例として保存するが、事後的なMSE外れ値除外手順を本研究へ採用しない。取得と正式採用を区別する。

次に実装・pilotへ進める候補は[5件の絞り込みメモ](thesis_problem_shortlist_5.md)にまとめた。選定根拠は本文確認済み[R29][R30]と、以前の比較論文との連続性[R25]である。全22案は削除せず保持する。

### 10.3 今後の追加ルール

- 新たに参照した論文は、[reference_workflow_spec.md](/Users/kakemyo/Downloads/master_BOGP/references/reference_workflow_spec.md) の手順で調査、取得、採否判断を行う
- 採用文献は `references/README.md` の文献番号台帳へ `[Rxx]` として追加する
- そのうえで、本節に「どの設計判断のために参照したか」を追記する
- 研究ノート本文を更新した場合は、該当文に `[Rxx]` を付ける
- 本文未確認の文献は、具体的な主張の根拠として使わず、保留理由を明記する
- Elsevier の手動ダウンロード候補は、ユーザーが本文取得するまでは具体的主張の根拠にせず、検索しやすい情報をブロック形式で返す
- 引用数を記す場合は、参照元 DB と確認日を併記する

## 11. 作業ログ

### 2026-04-09 | 初期ワークスペース整備

- 何をしたか: 研究用ワークスペースを新規作成し、研究ノート、実験コード、スモークテスト、ログ追記補助スクリプトの置き場を定義した。
- なぜそうしたか: 空のワークスペースだったため、今後の実装と実験ログを同じ場所で一貫管理できる土台が必要だった。
- 変更対象: `README.md`、`pyproject.toml`、`notes/research_note.md`、`src/bogp/`、`scripts/`、`tests/`
- 確認方法: プロジェクト構成と Python 実装方針が追跡できる形になっていることを目視確認する。
- 次にやること: Python 仮想環境を作成し、依存関係を導入してスモークテストを実行する。

### 2026-04-09 | 閉ループ制御設計の具体化

- 何をしたか: 文脈付き BO を採用する理由、制御周期、文脈ベクトル、報酬関数、操作率制約、比較対象を明文化した。
- なぜそうしたか: 単に「BO で率を変える」だけでは研究として曖昧であり、どの情報を観測し、何を最適化するかを先に明確にする必要があった。
- 変更対象: `notes/research_note.md`
- 確認方法: 制御対象、観測量、入力、報酬、評価軸がそれぞれ明示されていることを確認する。
- 次にやること: この設計に沿った制御器と簡易シミュレータをコードとして実装する。


### 2026-04-09 14:12 | 実装環境構築と動作確認

- 何をしたか: 仮想環境を作成し、依存パッケージを導入してスモークテストと単体テストを実行した
- なぜそうしたか: 研究計画を文書だけでなく実行可能な形にし、次回以降すぐ実験へ入れる状態にするため
- 詳細:
- Python 3.9 の仮想環境 .venv を作成した
- pip・setuptools・wheel を更新し、pyproject.toml の依存関係を editable install した
- Contextual BO 制御器の文脈ベクトル整形バグを修正した
- スモークテスト出力を整理し、収束警告を抑制した
- 確認方法:
- PYTHONPATH=src .venv/bin/python -m unittest discover -s tests が成功した
- .venv/bin/python scripts/smoke_test_v1.py が成功し、HV 0.1000 から 0.4355 への改善を確認した
- 次にやること:
- DEAP を使った実 GP エンジンを実装する
- HV と多様性指標を実問題に接続する

### 2026-04-12 14:21 | 進捗報告スライド案の作成

- 何をしたか: 研究ノート第1章から第8章をもとに、30分前後の進捗報告用スライド構成案を作成した
- なぜそうしたか: 次回の進捗報告で、閉ループ制御の仕組み、目的関数の設計理由、現時点の方針を重点的に説明できるようにするため
- 詳細:
- slides/progress_report_outline.md を新規作成した
- 章対応、スライドタイトル、主張、図案、時間配分を整理した
- 第5章と第8章に説明の重心を置く18枚構成とした
- 確認方法:
- スライド案が研究ノート1章から8章の内容を漏れなくカバーしていることを確認した
- 30分前後で説明できるよう、各スライドに目安時間を付与した
- 次にやること:
- 必要に応じてこの構成をもとに PowerPoint 本体を作成する
- 図表化する模式図を優先順位付きで具体化する

### 2026-04-12 21:20 | 進捗報告用スライド原稿の具体化

- 何をしたか: PowerPoint に貼り付けやすい形で、各スライドの本文、発表原稿、図のラフ案を作成した
- なぜそうしたか: 進捗報告スライド案をそのまま発表資料へ落とし込める状態にし、説明の一貫性を保つため
- 詳細:
- slides/progress_report_draft.md を新規作成した
- 18枚分の各スライドについて、本文、原稿、図のラフ案を記載した
- 閉ループ制御、目的関数、文脈付き BO の説明に重点を置いた
- 確認方法:
- 研究ノート1章から8章の内容とスライド構成案に整合することを確認した
- 30分前後の発表を想定した時間配分を維持した
- 次にやること:
- 必要に応じて PowerPoint 本体を作成する
- 模式図を実際の図として清書する

### 2026-04-12 21:46 | 進捗報告用模式図の清書

- 何をしたか: Slide 7、8、10、12、15 用の模式図を PowerPoint に挿入しやすい SVG として作成した
- なぜそうしたか: 発表資料にそのまま使える図を用意し、閉ループ制御や目的関数の説明を視覚的に分かりやすくするため
- 詳細:
- slides/figures/ 配下に 5 枚の SVG 図と README を追加した
- 閉ループ構造、制御フロー、文脈ベクトル、報酬関数、文脈付き BO 採用理由を図として清書した
- 配色とレイアウトを統一し、PowerPoint へ拡大挿入しやすいベクター形式で作成した
- 確認方法:
- slides/figures 配下の SVG を XML としてパースし、構文エラーがないことを確認した
- 図ファイルが Slide 7、8、10、12、15 に対応して揃っていることを確認した
- 次にやること:
- 必要に応じて各図の配色や文言を発表スライドのデザインに合わせて微調整する
- PowerPoint 本体へ挿入してサイズと余白を最終確認する

### 2026-04-12 22:10 | 模式図のスライド実装向け調整

- 何をしたか: 模式図の文言を日本語スライド向けに短文化し、PowerPoint への配置ガイドを作成した
- なぜそうしたか: 図をそのまま発表資料に挿入したときに、文字量が多すぎず、配置や配色で迷わないようにするため
- 詳細:
- Slide 7、8、10、12、15 用 SVG の見出し・本文を短い日本語中心に調整した
- 図内フォントを日本語スライドで見やすいフォント指定へ変更した
- slides/powerpoint_insertion_guide.md を追加し、配置案、配色、本文量の目安を整理した
- 確認方法:
- 更新後の SVG を XML として再パースし、構文エラーがないことを確認した
- 配置ガイドに Slide 7、8、10、12、15 それぞれの使い方が記載されていることを確認した
- 次にやること:
- 必要に応じて PowerPoint 本体へ挿入して最終的なサイズ感を確認する
- 必要なら図の日本語表現をさらに口頭説明に寄せて微調整する

### 2026-04-12 22:23 | 進捗報告スライドの完成レイアウト設計

- 何をしたか: 18枚分のスライドについて、最終本文と完成レイアウト案をまとめた設計書を作成した
- なぜそうしたか: PowerPoint 本体を作る際に、各スライドで何を載せるかと、図をどう配置するかを一目で判断できるようにするため
- 詳細:
- slides/final_deck_spec.md を新規作成した
- 各スライドにタイトル、最終本文、使用図、完成レイアウト、発表メモを記載した
- 図を使うスライドは図中心、それ以外は短い本文中心になるよう統一した
- 確認方法:
- 18枚分すべてに本文とレイアウト指示があることを確認した
- 既存の図ファイルと対応関係が取れていることを確認した
- 次にやること:
- 必要に応じて PowerPoint 本体を作成する
- 実際の発表時間に合わせて一部スライドの本文量を微調整する

### 2026-04-12 23:03 | PowerPoint 本体の生成

- 何をしたか: テンプレートのスライドマスターを使って、進捗報告用の PowerPoint 260412_A.pptx を生成した
- なぜそうしたか: 研究ノート、スライド本文、図素材をもとに、実際に報告に使える PowerPoint ファイルを作成するため
- 詳細:
- slides/251022_明神.pptx をテンプレートとして読み込み、既存スライドを置き換えて18枚の新規スライドを生成した
- slides/figures の SVG 図を macOS Quick Look で PNG 化し、slides/generated_assets/260412_A に保存した
- scripts/build_260412_a.py を作成し、再生成可能な形で PowerPoint を組み立てられるようにした
- 確認方法:
- slides/260412_A.pptx が生成され、ファイルサイズ 2.2MB で存在することを確認した
- 生成した PowerPoint を python-pptx で再読込し、スライド数が18枚であることと各タイトルが想定どおりであることを確認した
- 次にやること:
- 必要に応じて PowerPoint 上で最終的な見た目を確認し、文字量や図サイズを微調整する
- 必要なら発表用にアニメーションや話者ノートを追加する

### 2026-04-12 23:25 | PowerPoint 図の収まり調整

- 何をしたか: 図の PNG 生成方式と配置ロジックを修正し、見切れのあったスライドを再生成した
- なぜそうしたか: Quick Look 由来の正方形 PNG のままだと Slide 7、12、15 で図が縦方向にはみ出していたため、正しい縦横比で描画しつつスライド内に収まる配置へ直す必要があった
- 詳細:
- scripts/build_260412_a.py の SVG→PNG 変換を qlmanage から Google Chrome のヘッドレス描画へ切り替え、2400x1350 の PNG を生成するようにした
- 図挿入処理に add_picture_contain を追加し、指定領域内へアスペクト比を保って収める配置へ変更した
- Slide 7、8、10、12、15 の図配置を見直し、タイトルや補助テキストと干渉しない範囲でサイズを再調整した
- 確認方法:
- 再生成後の PNG がすべて 2400x1350 であることを確認した
- slides/260412_A.pptx を再読込し、問題のあった Slide 7、8、10、12、15 の図形サイズがスライド高さ 7.5 inch 内に収まっていることを確認した
- 次にやること:
- 必要に応じて PowerPoint 上で最終表示を目視確認し、読みやすさ優先で図サイズを微調整する

### 2026-04-14 12:15 | 文脈ベクトル指標の詳細整理

- 何をしたか: 文脈ベクトルに入れる候補指標を具体化し、採用理由と代替候補との比較を研究ノートへ追記した
- なぜそうしたか: 文脈ベクトルの構成は報酬設計と BO の学習品質に直結するため、どの状態を最小限かつ有効に観測すべきかを先に明確化する必要があった
- 詳細:
- 選定原則として、制御との因果の近さ、状態識別力、低次元性、計測コスト、正規化しやすさを整理した
- 初期採用案を tau, 正規化HV, 正規化DeltaHV, 構造多様性, 正規化停滞長, 正規化bloat の 6 次元として明記した
- 構造多様性を第一候補とし、意味多様性や目的空間多様性は比較・拡張候補として位置付けた
- 最良適応度のみ、平均適応度、crowding distance のみ、木深さのみなどを初期文脈に入れすぎない理由も整理した
- 確認方法:
- notes/research_note.md に文脈指標の選定原則、各指標の採用理由、見送り候補、比較方針が追加されていることを確認した
- 次にやること:
- 次段階では各指標の具体的な計算式と正規化方法をさらに詰め、実 GP 実装に接続する

### 2026-04-14 13:15 | 文脈指標の計算式と参考文献整理

- 何をしたか: 文脈ベクトルの計算式、構造多様性の実装方針、多様性指標の比較、参考文献フォルダを追加した
- なぜそうしたか: 文脈ベクトルの構成要素は報酬設計と BO の学習品質に直結するため、式と文献根拠を先に固めておく必要があった
- 詳細:
- src/bogp/context_metrics.py を追加し、progress, HV, DeltaHV, stagnation, tree size の正規化関数を実装した
- src/bogp/diversity.py を追加し、部分木ハッシュと Jaccard 類似度に基づく構造多様性、および相関ベースの意味多様性を実装した
- notes/research_note.md に文脈指標の具体式、構造多様性の定義、意味多様性・目的空間多様性との比較、参考文献章を追記した
- references/ に公開 PDF と文献メモを保存し、各論文が研究ノートのどの判断に使われたかを対応付けた
- 確認方法:
- PYTHONPATH=src .venv/bin/python -m unittest discover -s tests が成功した
- references/*.pdf が PDF 文書として認識されることを確認した
- 研究ノートの章立てに 10. 参考文献 が追加され、文献用途の対応が記載されていることを確認した
- 次にやること:
- 次段階では構造多様性を実 GP エンジンへ接続し、DEAP 個体から prefix token を生成する実装を追加する

### 2026-04-21 | 参考文献取得仕様の実用化とルール更新

- 何をしたか: 参考文献調査・取得・研究ノート反映の仕様書を、本研究のテーマに合わせて実用的な運用手順へ改訂した
- なぜそうしたか: 交叉率・突然変異率を文脈付き BO で制御する研究では、文献を単に集めるだけでなく、どの設計判断に使うかまで追跡する必要があるため
- 詳細:
- references/reference_workflow_spec.md を追加し、優先文献領域、検索クエリ、採否分類、OA 取得順、保存規則、文献番号、研究ノート反映手順を明文化した
- references/README.md を更新し、現在の研究テーマに沿った取得ルールと文献番号台帳を追加した
- notes/research_note.md の参考文献章を更新し、既存文献に [R01] から [R11] の作業用文献番号を付けた
- 確認方法:
- 仕様書、文献フォルダ README、研究ノート第10章のリンクと番号が対応していることを確認した
- 次にやること:
- 次回以降の文献追加では、文献番号台帳と研究ノート本文の [Rxx] 参照を同時に更新する

### 2026-04-21 | 研究計画のブラッシュアップ

- 何をしたか: 更新済みの参考文献ルールに基づき、研究計画を研究質問、仮説、先行研究ギャップ、実験段階、成功条件、リスクに分けて再整理した
- なぜそうしたか: 提案手法の設計だけでなく、論文化時に必要な新規性、比較対象、実験で示すべき点を明確にするため
- 詳細:
- notes/research_note.md の 8 章に「ブラッシュアップ後の研究計画」を追加した
- 現在の文献では多様性、semantic GP、bloat、多目的 GP は根拠がある一方で、adaptive parameter control、online algorithm configuration、contextual BO の中核文献が不足していることを明記した
- 実験計画を toy engine 検証、実 GP 接続、baseline 比較、ablation、統計評価の 5 段階に分けた
- 確認方法:
- 研究質問、仮説、実験比較、成功条件が対応する形で記載されていることを確認した
- 次にやること:
- 参考文献ルールに従い、adaptive GP operator control、online algorithm configuration、contextual BO の中核文献を追加する

### 2026-04-21 | 研究計画レビューの別紙化

- 何をしたか: 現在の実装到達点と今後の研究計画を突き合わせ、研究計画ブラッシュアップ用の別紙を作成した
- なぜそうしたか: 研究ノート本体の方針だけでは、実装済みの部品、未充足の先行研究、次の実験単位が分散して見えにくいため
- 詳細:
- notes/research_brushup_2026-04-21.md を追加した
- 研究の再定義、現在の到達点、提案手法の構成、研究質問、先行研究上の穴、実験計画、成功条件、論文構成案、直近 3 ステップを整理した
- notes/research_note.md の 8.10 に、実装状況に基づく補足レビューと別紙へのリンクを追加した
- 確認方法:
- 研究ノート本体からブラッシュアップ別紙へ辿れることを確認した
- 次にやること:
- 文献取得ルールに沿って `[R12]` 以降の中核文献を追加し、baseline runner の実装へ進む

### 2026-04-22 | Elsevier 文献取得ルールの追加

- 何をしたか: 参考文献取得ルールに、Elsevier / ScienceDirect から本文または内容確認できる論文の扱いを追加した
- なぜそうしたか: オープンアクセス文献だけに限定すると、中核的な関連研究を拾い落とす可能性があるため、Elsevier から読める論文も同列の参考文献候補として扱えるようにする必要があった
- 詳細:
- references/reference_workflow_spec.md の採用条件、本文アクセス・取得ルール、Elsevier 文献の扱い、手動ダウンロード候補の返却仕様、メタデータノート形式、作業完了条件を更新した
- references/README.md の現在の取得・保存ルールと新規追加チェックリストを更新した
- notes/research_note.md の参考文献章に、Elsevier / ScienceDirect 文献と手動ダウンロード候補の扱いを追記した
- 確認方法:
- 仕様書、README、研究ノートに Elsevier / ScienceDirect と手動ダウンロード候補のルールが反映されていることを確認した
- 次にやること:
- 次回の文献調査では、OA 文献と Elsevier 文献を同列に評価し、直接取得できない Elsevier 文献は検索しやすい候補情報として返す

### 2026-04-22 | 研究の進め方仕様書の作成

- 何をしたか: 今後の研究を進めるための運用仕様書を作成した
- なぜそうしたか: 参考文献ルール、提案手法、実装、実験計画を別々に進めるのではなく、研究質問に対応する形で一貫して管理する必要があるため
- 詳細:
- notes/research_process_spec.md を追加した
- 文献調査、研究質問と仮説、研究フェーズ、実験ログ、設計判断の記録、品質ゲート、直近の進め方、相談して詰めるべき内容を整理した
- notes/research_note.md の 8.11 に研究の進め方仕様へのリンクを追加した
- 確認方法:
- 研究ノートから研究の進め方仕様書へ辿れることを確認した
- 次にやること:
- 仕様書の「相談して詰めるべき内容」をもとに、最初の実 GP 問題、baseline の強さ、run 数、Elsevier 手動取得候補の扱いを決める

### 2026-04-26 14:00 | 提案手法ラフ仕様の固定

- 何をしたか: 状態・行動・報酬・更新周期を再定義し、提案法を文脈付き BO による状態依存・閉ループ制御として 1 ページ仕様へ圧縮した
- なぜそうしたか: 実装やテストより先に、提案法の芯を強くし、固定率法や非文脈 BO との差分、新規性、仮説を明瞭にしておく必要があった
- 詳細:
- notes/proposed_method_rough.md を新規作成し、数理定義、処理流れ、主張、仮説を一つの仕様メモにまとめた
- 行動を (p_c, p_m, k) とし、k を単なる効率化変数ではなく適応的な制御更新周期として定義した
- 報酬は raw DeltaHV ではなく、k の影響を受けにくい世代あたり HV 改善量を主項とする形へ整理した
- research_note.md の設計方針まとめを更新し、新しい仕様メモへのリンクを追加した
- 確認方法:
- notes/proposed_method_rough.md に 1. 手法の一文定義, 2. 数理定義, 3. アルゴリズム, 4. 主張, 5. 仮説 が揃っていることを確認した
- research_note.md から仕様メモへ辿れることを確認した
- 次にやること:
- 次段階では、この仕様メモを基準に論文用の制御図と手法節の文章を整備する

### 2026-04-27 | 提案手法仕様メモ V1 の確定

- 何をしたか: 提案手法の正規版仕様メモを新規作成し、数理定義、アルゴリズム、主張、仮説を `k` を含む形で固定した
- なぜそうしたか: ラフ版では提案の芯は整理できていたが、論文化や今後の実装検討で参照する正式仕様としては、BO と GP の接続、混合空間同時最適化、区間平均多様性の扱いをより明確に固定する必要があった
- 詳細:
- `notes/proposed_method_spec_v1.md` を新規作成した
- 提案法を `r = f(x,p_c,p_m,k)` を学習する文脈付き BO 制御として定義した
- BO の行動を `(p_c,p_m,k)` の混合空間同時最適化として固定した
- 報酬を世代あたり HV 改善量、区間平均多様性、制御コストで定義した
- Mermaid による中心フローチャートと 8 ステップの擬似コードを追加した
- `research_note.md` の設計方針まとめと研究上の主張を新仕様に合わせて更新した
- 確認方法:
- `notes/proposed_method_spec_v1.md` に一文定義、数理定義、BO-GP 接続、フローチャート、擬似コード、主張、仮説が揃っていることを確認した
- `research_note.md` からラフ版と正規版仕様メモの両方へ辿れることを確認した
- 次にやること:
- 次段階では、この V1 仕様メモを基準に手法節ドラフトと論文用の制御図説明文を整備する

### 2026-04-28 | 論文用ドラフト文章の整備

- 何をしたか: 提案手法仕様メモ V1 をもとに、論文本文へ流用できる手法節、中心図説明文、比較手法節のドラフトを整備した
- なぜそうしたか: 仕様メモの内容をそのまま研究用メモに留めず、論文化の際に使える文章へ早めに変換しておくことで、今後の記号統一、主張整理、比較設計を進めやすくするため
- 詳細:
- `notes/paper_method_section_draft.md` を追加し、閉ループ定式化、状態、行動、報酬、文脈付き BO、アルゴリズムの文章下書きを作成した
- `notes/paper_central_figure_explanation_draft.md` を追加し、中心図のキャプション案、本文中の説明文案、図中ラベル対応、強調主張を整理した
- `notes/paper_comparison_methods_draft.md` を追加し、固定率 GP、手設計スケジュール GP、非文脈 BO、提案法の差分と仮説対応を文章化した
- 手法節と中心図説明文の記号を `\Delta HV^{\mathrm{rate}}_\ell` の表記へ統一した
- 確認方法:
- 3 つのドラフトがそれぞれ手法本文、図説明、比較手法の役割を持ち、`notes/proposed_method_spec_v1.md` の定義と整合していることを確認した
- 次にやること:
- 次段階では、これら 3 つのドラフトをもとに、論文の「提案手法」節本文と比較節本文の推敲、および中心図の図番号やキャプション長の最適化を行う

### 2026-04-28 | 3・4章統合本文ドラフトの作成

- 何をしたか: 既存の手法節ドラフト、中心図説明文ドラフト、比較手法節ドラフトを統合し、修士論文寄りの密度で読める 3 章・4 章の本文ドラフトを新規作成した
- なぜそうしたか: 個別メモとしては材料が揃っていたが、そのままでは章間の接続や主張の流れが分散していたため、今後の論文本文の起点となる統合版を用意する必要があった
- 詳細:
- `notes/paper_sections_3_4_full_draft.md` を新規作成した
- 3 章では、提案法の基本方針、閉ループ定式化、状態ベクトル、行動と制約、報酬関数、文脈付き BO、アルゴリズム概要を連続した本文として再編した
- 3.2 に中心図のキャプション案と本文説明を埋め込み、観測量、制御入力、区間統計、学習データの対応が自然に読めるようにした
- 4 章では、固定率 GP、手設計スケジュール GP、非文脈 BO、提案法の差分を、検証設計として読める文章に再編した
- `k` の意味づけを「更新周期」で統一し、非文脈 BO と提案法の差分を `f(p_c,p_m,k)` と `f(x_\ell,p_c,p_m,k)` の対比で明記した
- 確認方法:
- `notes/paper_sections_3_4_full_draft.md` に 3 章と 4 章が連続して存在し、状態、行動、報酬、更新周期、文脈付き BO、比較対象 4 種が含まれていることを確認する
- 次にやること:
- 次段階では、この統合ドラフトをもとに、論文の 5 章「実験設定」へつながる導入文の精緻化と、必要に応じた文献参照プレースホルダの追加を行う

### 2026-04-28 | Notion への提案手法ドラフト反映

- 何をしたか: 3・4章統合本文ドラフトをもとに、Notion に「提案手法ドラフト案１」というページを新規作成した
- なぜそうしたか: ローカル原稿だけでなく、Notion 上でも継続的に追記・整理できる研究メモとして管理できるようにするため
- 詳細:
- 親ページ `提案手法ラフ` の子ページとして、Notion ページ `提案手法ドラフト案１` を作成した
- 内容は `notes/paper_sections_3_4_full_draft.md` を基準に、Executive Summary、Key Findings、Detailed Analysis、Conclusions、Hypotheses、Next Steps、Sources の構成で整理した
- `提案手法ラフ` への Notion ページ参照を Sources に含め、ローカル原稿ファイル名も明記した
- 確認方法:
- Notion 上でページ `提案手法ドラフト案１` が作成され、親ページ `提案手法ラフ` 配下に配置されていることを確認した
- 次にやること:
- 今後の提案手法の更新内容や論文化の進捗に応じて、この Notion ページにも追記していく

### 2026-04-28 | BO 制御器詳細設計仕様 V1 の作成

- 何をしたか: 提案法全体から外側 BO 制御器だけを切り出し、`k` の扱い、surrogate、EI、warm-up、制約、fallback を固定する詳細仕様メモを作成した
- なぜそうしたか: 提案法の中核である「状態依存・閉ループ制御」を成立させるには、BO がどの入力を見て、どの空間をどう探索し、どの根拠で `(p_c,p_m,k)` を選ぶかを先に明確にする必要があったため
- 詳細:
- `notes/bo_controller_spec_v1.md` を新規作成した
- `k` は連続値として扱わず、離散候補を列挙して各 `k` ごとに `f_k(x,p_c,p_m)` を学習する方針に固定した
- surrogate は GP 回帰器、カーネルは `Matern(nu=2.5)` + `WhiteNoise` + `Constant`、獲得関数は EI とした
- warm-up は各 `k` に最低観測数を配る balanced warm-up とし、疎データ時とモデル失敗時の fallback も仕様化した
- 文献 [R12], [R13], [R14] を追加し、文脈付き BO、EI、離散・整数変数 BO の設計根拠として仕様メモに反映した
- 確認方法:
- `notes/bo_controller_spec_v1.md` に `D_k`, `f_k(x,p_c,p_m)`, `EI_k`, `K(x_\ell)`, balanced warm-up, fallback, 非文脈 BO baseline との差分が含まれていることを確認する
- 次にやること:
- 次段階では、この BO 仕様 V1 をもとに、論文 3 章の BO 詳細節へ反映し、その後に `ControlInput` と閉ループ実行器を `k` 対応へ拡張する

### 2026-05-11 | 多目的 GP 前提と正規版仕様への記述更新

- 何をしたか: 研究ノート前半に残っていた古い `(p_c,p_m)` のみの記述や固定制御区間の記述を、正規版の多目的 GP 前提と `(p_c,p_m,k)` 制御へ更新した
- なぜそうしたか: 本研究の対象は最終的に望ましいパレートフロントまたは非劣解集合を得る多目的 GP であり、外側 BO も操作率だけでなく更新周期 `k` を含めて制御するため、古い記述が残ると研究計画の前提が曖昧になるため
- 詳細:
- 目的章に「対象とする GP は多目的遺伝的プログラミングである」と明記した
- 技術的課題、閉ループ構造、BO モデル、文脈なし BO との差分を `(p_c,p_m,k)` と `f(c_t,p_c,p_m,k)` の形へ更新した
- 制御周期の説明を、固定の 3-5 世代ではなく、BO が候補集合から `k` を選ぶ更新周期制御として更新した
- 単目的版報酬は本線ではなく、制御器単体のデバッグ用の暫定手段であると明記した
- 評価指標、実験条件、仮説、ログ項目に `k` と balanced warm-up の考え方を反映した
- 確認方法:
- `research_note.md` 内で、古い `f(p_c,p_m)`、固定 `制御区間: 3 世代`、`BO が提案した (p_c,p_m) の時系列` といった表現が残っていないことを確認する
- 次にやること:
- 次段階では、論文用 3・4章統合ドラフトにも必要に応じて「対象は多目的 GP である」ことを冒頭でさらに明確化する

### 2026-05-12 | 汎用多目的 GP テンプレート実装

- 何をしたか: 構造探索問題へ直接入る前に、問題非依存の多目的 GP + 文脈付き BO 制御テンプレートを実装した
- なぜそうしたか: 提案手法を特定問題専用に作り込むと、研究上の主張である「GP の状態依存・閉ループ制御」と、対象問題固有の実装が混ざってしまうため、まず問題側を `GPProblem` として差し替え可能にする必要があった
- 詳細:
- `src/bogp/test_v1_problem.py` を追加し、`ObjectiveSpec`, `EvaluatedIndividual`, `GPProblem` を定義した
- `src/bogp/test_v1_mo_engine.py` を追加し、NSGA-II 型の非優越ソート、crowding distance、archive 更新、状態スナップショット生成を持つ汎用 `MultiObjectiveGPEngine` を実装した
- `src/bogp/test_v1_hypervolume.py` を追加し、V1 では 2 目的 exact HV を計算するようにした
- `ControlInput` を `p_c`, `p_m`, `k` に対応させ、閉ループ実行器が固定間隔ではなく `control.update_period` を用いるように更新した
- 報酬関数を、世代あたり HV 改善量、区間平均多様性、制御更新コストを使う V1 仕様へ寄せた
- `src/bogp/test_v1_template_problem.py` に 2 目的の雛型 symbolic regression 問題を追加した
- `src/bogp/test_v1_structural_problem.py` に、添付 MATLAB コードに対応する構造探索問題アダプタの初期版を追加した
- `scripts/run_test_v1_template_experiment.py` と `scripts/run_test_v1_structural_experiment.py` を追加し、テンプレート問題と構造探索問題の小実験を実行できるようにした
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile ...` で主要ファイルの構文確認を行った
- `.venv/bin/python -m unittest discover -s tests` で 18 件の単体テストが通ることを確認した
- `.venv/bin/python scripts/smoke_test_v1.py` で既存 toy 閉ループが完走することを確認した
- `.venv/bin/python scripts/run_test_v1_template_experiment.py` でテンプレート問題が 30 世代まで完走し、最終 HV と archive が出力されることを確認した
- `.venv/bin/python scripts/run_test_v1_structural_experiment.py` で構造探索問題の極小設定が 5 世代まで完走し、Pareto archive が出力されることを確認した
- 次にやること:
- 構造探索問題について、MATLAB 実装との差分、伝達関数計算の妥当性、目的関数の正規化範囲を確認する
- 固定率 GP、非文脈 BO、提案法の比較実験スクリプトを整備する

### 2026-05-12 | 構造探索問題の差分整理と Pareto front 可視化

- 何をしたか: 添付 MATLAB 実装と Python 雛型上の構造探索アダプタとの差分を整理し、テンプレート問題と構造探索問題の小実験を実行して Pareto front を可視化した
- なぜそうしたか: 構造探索問題を提案手法へ適用する前に、MATLAB 実装をどこまで再現し、どこを多目的 GP / 閉ループ BO 制御向けに変更しているかを明確にする必要があったため
- 詳細:
- `notes/structural_problem_matlab_diff.md` を追加し、個体表現、目的関数、選択・世代交代、伝達関数計算、初期化、突然変異の差分を整理した
- `scripts/run_test_v1_template_experiment.py` に `pareto_front.png` と `control_history.png` の出力を追加した
- `scripts/run_test_v1_structural_experiment.py` にも同様の図出力を追加した
- テンプレート問題では、2 目的 `MSE` と `tree_size` の Pareto archive を可視化した
- 構造探索問題では、2 目的 `terminal_elements` と `impulse_integral` の Pareto archive を極小設定で可視化した
- 実行結果:
- テンプレート GP: `records=12`, `final_generation=30`, `final_hypervolume=0.9893683271865878`, `final_diversity=0.5245663153271849`, `archive_size=200`
- テンプレート GP 出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/template_gp/20260512_022552`
- 構造探索 GP: `records=3`, `final_generation=5`, `final_hypervolume=0.9995396366770549`, `final_diversity=0.71498778998779`, `archive_size=31`
- 構造探索 GP 出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/structural_gp/20260512_022552`
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/run_test_v1_template_experiment.py scripts/run_test_v1_structural_experiment.py src/bogp/test_v1_structural_problem.py` が通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 18 件の単体テストが通ることを確認した
- `.venv/bin/python scripts/run_test_v1_template_experiment.py` と `.venv/bin/python scripts/run_test_v1_structural_experiment.py` が完走し、Pareto front 図が生成されることを確認した
- 次にやること:
- 構造探索問題について、代表構造を固定して MATLAB 版と Python 版のインパルス応答積分を比較する
- 構造探索問題の population size / generation 数を増やし、Pareto front が安定して形成されるか確認する
- 固定率 GP と提案法の比較実験に進む

### 2026-05-12 | 制御履歴図における `k` 区間表示の修正

- 何をしたか: 制御履歴図の最下段に描いていた更新周期 `k` の表示を、各制御入力が実際に保持された世代区間に一致する描画へ修正した
- なぜそうしたか: 旧図では各制御区間の終了世代を横軸にして `step(..., where="post")` を描いていたため、`k` の段差が実際の適用区間より 1 区間ぶん右にずれて見え、上段の HV・多様性観測点との対応が不自然だったため
- 詳細:
- `scripts/run_test_v1_template_experiment.py` と `scripts/run_test_v1_structural_experiment.py` の `k` 描画を修正した
- `k` は `start_generation` から `end_generation` までの水平線として描き、次区間で `k` が変わる場合のみ境界世代に縦線を入れる方式へ変更した
- これにより、たとえば `k=5` は「5 世代ぶん同じ操作率を保持した区間」として直感的に読める
- 再生成した図:
- テンプレート GP 制御履歴: `/Users/kakemyo/Downloads/master_BOGP/outputs/template_gp/20260512_133340/control_history.png`
- 構造探索 GP 制御履歴: `/Users/kakemyo/Downloads/master_BOGP/outputs/structural_gp/20260512_133341/control_history.png`
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/run_test_v1_template_experiment.py scripts/run_test_v1_structural_experiment.py` が通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 18 件の単体テストが通ることを確認した
- 両実験スクリプトを再実行し、`k` の水平区間が実際の `start_generation -> end_generation` と一致していることを図で確認した

### 2026-05-12 | 普通の GP ベースライン実装と提案法との初期比較

- 何をしたか: 提案手法の良さを大まかに見るため、BO 制御を使わない固定率の普通の多目的 GP ベースラインを実装し、テンプレート問題上で提案手法と比較した
- なぜそうしたか: 提案手法だけを動かしても、得られた HV や多様性の値が良いのか判断しにくいため、同じ `GPProblem` と同じ多目的 GP エンジンを使う最小ベースラインが必要だった
- 詳細:
- `src/bogp/test_v1_plain_gp_baseline.py` を追加し、固定の交叉率 `p_c` と突然変異率 `p_m` で毎世代 GP を進める `PlainFixedRateGPRunner` を実装した
- 普通の GP も多目的 GP として扱い、選択・archive・HV・多様性計算は提案手法と同じ `MultiObjectiveGPEngine` に統一した
- `scripts/run_test_v1_plain_gp_baseline_template.py` を追加し、テンプレート問題に対する普通の GP の HV / Diversity 推移と Pareto archive を出力できるようにした
- `scripts/compare_test_v1_plain_gp_vs_bogp_template.py` を追加し、同一テンプレート問題・同一世代数・同一乱数 seed で提案手法と普通の GP を並べて実行し、HV / Diversity 推移を重ねて描画できるようにした
- 実行結果:
- 普通の GP 単独実験: `final_generation=30`, `final_hypervolume=0.9794046007620395`, `final_diversity=0.3478260869565218`, `archive_size=200`
- 普通の GP 出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/plain_gp_baseline_template/20260512_173145`
- 提案手法との比較実験: 提案手法は `final_hypervolume=0.9893683271865878`, `final_diversity=0.5245663153271849`, `control_steps=12`
- 同比較における普通の GP は `final_hypervolume=0.9794046007620395`, `final_diversity=0.3478260869565218`, `records=31`
- 比較出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/template_plain_vs_bogp/20260512_173147`
- 簡単な考察:
- この単一 seed のテンプレート問題では、提案手法の方が最終 HV と最終 Diversity の両方で普通の GP を上回った
- 普通の GP は初期に Diversity が大きく低下し、その後ある程度回復するが、提案手法ほど高い多様性までは戻らなかった
- ただし、現時点の結果は「提案手法が良さそうかを見るための初期確認」であり、研究上の主張には複数 seed、固定率の複数設定、非文脈 BO、時変スケジュールとの比較が必要である
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile src/bogp/test_v1_plain_gp_baseline.py scripts/run_test_v1_plain_gp_baseline_template.py scripts/compare_test_v1_plain_gp_vs_bogp_template.py` が通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 19 件の単体テストが通ることを確認した
- `.venv/bin/python scripts/run_test_v1_plain_gp_baseline_template.py` と `.venv/bin/python scripts/compare_test_v1_plain_gp_vs_bogp_template.py` が完走し、HV / Diversity 推移図が生成されることを確認した

### 2026-05-12 | 構造探索問題における普通の GP と提案法の比較

- 何をしたか: 構造探索問題アダプタに対して、固定率の普通の GP と BO 制御付き GP を同じ設定で実行し、HV / Diversity 推移と Pareto archive を比較した
- なぜそうしたか: テンプレート問題だけでなく、本研究で対象としたい構造探索問題でも、提案手法が少なくとも不自然な挙動をせず、普通の GP と比較できる形で動くか確認するため
- 詳細:
- `scripts/run_test_v1_plain_gp_baseline_structural.py` を追加し、構造探索問題に対する普通の固定率 GP の単独実験を実行できるようにした
- `scripts/compare_test_v1_plain_gp_vs_bogp_structural.py` を追加し、構造探索問題で提案手法と普通の GP を同一 seed・同一世代数・同一集団サイズで比較できるようにした
- 比較図として `hv_diversity_comparison.png`, `bogp_control_periods.png`, `pareto_front_comparison.png` を出力するようにした
- Pareto archive の比較は点が重なりやすいため、普通の GP と提案手法を左右2パネルで表示する形式にした
- 実行設定:
- `population_size=8`, `total_generations=10`, `random_seed=7`
- 構造探索問題は `max_initial_depth=3`, `time_steps=401`
- 普通の GP は `p_c=0.80`, `p_m=0.05`
- 提案手法は `K={1,3}`, warm-up は各 `k` 1点
- 実行結果:
- 普通の GP 単独実験: `final_generation=10`, `final_hypervolume=0.999533113434812`, `final_diversity=0.7500465224522009`, `archive_size=57`
- 普通の GP 出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/plain_gp_baseline_structural/20260512_175910`
- 構造探索比較実験: 提案手法は `final_hypervolume=0.9995459267018961`, `final_diversity=0.7833335948222349`, `control_steps=6`, `archive_size=63`
- 同比較における普通の GP は `final_hypervolume=0.999533113434812`, `final_diversity=0.7500465224522009`, `records=11`, `archive_size=57`
- 比較出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/structural_plain_vs_bogp/20260512_180049`
- 簡単な考察:
- この軽量設定では、提案手法が普通の GP より最終 HV と Diversity の両方でわずかに高くなった
- ただし HV は初期時点から 0.998 以上でほぼ飽和しており、この問題設定・正規化範囲・参照点では HV 差だけで性能差を論じにくい
- Pareto archive は両手法とも「端子数 1 で応答積分が大きい解」と「端子数を増やして応答積分をほぼ 0 にする解」を含み、短い世代数でも基本的なトレードオフ構造は出ている
- 提案手法は `k=1 -> 3 -> 3 -> 1 -> 1 -> 1` のように、序盤から中盤で制御更新を粗くし、終盤で密に更新する挙動を示した
- 次にやること:
- HV が飽和しすぎているため、構造探索問題の目的関数正規化範囲、参照点、制約条件を見直す
- より長い世代数・複数 seed・複数固定率で比較し、今回の差が安定して出るか確認する
- MATLAB 実装により忠実な目的関数・構造表現へ近づけたうえで同じ比較を再実行する
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/run_test_v1_plain_gp_baseline_structural.py scripts/compare_test_v1_plain_gp_vs_bogp_structural.py` が通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 19 件の単体テストが通ることを確認した
- `.venv/bin/python scripts/run_test_v1_plain_gp_baseline_structural.py` と `.venv/bin/python scripts/compare_test_v1_plain_gp_vs_bogp_structural.py` が完走し、構造探索版の比較図が生成されることを確認した

### 2026-05-13 | 検証用コードの `test_v1` 命名整理

- 何をしたか: 現段階の雛型実装・小実験・比較実験・単体テストが検証用コードであることを明確にするため、対象ファイル名へ `test_v1` を含める命名へ整理した
- なぜそうしたか: 後から本実装や改訂版を追加した際に、現在のコードが「初期検証版」であることをファイル名だけで判別できるようにするため
- 詳細:
- 汎用多目的 GP 雛型、HV、問題インターフェース、テンプレート問題、構造探索アダプタ、固定率 GP ベースラインを `src/bogp/test_v1_*.py` へ整理した
- toy engine は `src/bogp/test_v1_toy_engine.py`、スモーク実行は `scripts/smoke_test_v1.py` とした
- テンプレート問題・構造探索問題の実験スクリプトと比較スクリプトは、`scripts/run_test_v1_*.py` または `scripts/compare_test_v1_*.py` に統一した
- 単体テストは `tests/test_v1_*.py` に統一し、`unittest discover` の対象となる命名を維持した
- README、構造探索差分メモ、研究進行メモ、研究ノート内の参照パスを新しいファイル名へ更新した
- 確認方法:
- `rg` で旧モジュール名・旧スクリプト名の参照が残っていないことを確認した
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m compileall src/bogp scripts tests` が通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 19 件の単体テストが通ることを確認した
- `.venv/bin/python scripts/smoke_test_v1.py` が完走し、閉ループスモーク結果を出力することを確認した
- 次にやること:
- 本実装へ昇格させる段階では、`test_v1` 系から正規版モジュールへ切り出す範囲を整理する

### 2026-05-18 | 提案手法清書版 `提案手法ver.1` の作成

- 何をしたか: これまで整理してきた提案手法の内容を、Markdown 版と TeX 版の清書メモとして作成した
- なぜそうしたか: archive 重複除去や HV 正規化など細部を詰める前に、現時点での提案手法の核を読みやすい形で固定し、今後の論文化・資料化の基準にするため
- 詳細:
- `notes/提案手法ver.1.md` を作成し、背景、全体構造、数理定義、状態、行動、報酬、BO 制御器、アルゴリズム、比較手法、研究仮説、未確定事項をまとめた
- `notes/提案手法ver.1.tex` を作成し、同内容を TeX 形式で整理した
- TeX 版には TikZ による「閉ループ制御構造」と「アルゴリズムフロー」の 2 図を含めた
- TeX 版は LuaLaTeX 用に `ltjsarticle` を指定した
- 確認方法:
- `wc -l notes/提案手法ver.1.md notes/提案手法ver.1.tex` で Markdown 版 552 行、TeX 版 525 行であることを確認した
- `rg` で TeX 内に `tikzpicture`、図キャプション、章構成が含まれていることを確認した
- この環境では `lualatex` が見つからなかったため、PDF へのコンパイル確認は未実施
- 次にやること:
- LaTeX 環境がある端末で TeX をコンパイルし、図の配置やページ幅を確認する
- 次段階では、この清書版を基準に archive 重複除去、HV 正規化、報酬と文脈の整合性を詰める

### 2026-05-18 | TinyTeX による LaTeX コンパイル環境確認と PDF 生成

- 何をしたか: 既存の TinyTeX 環境を確認し、`提案手法ver.1.tex` を LuaLaTeX でコンパイルできるように必要パッケージを追加して PDF を生成した
- なぜそうしたか: TeX ファイルに含めた日本語本文と TikZ 図が実際にコンパイル可能であることを確認し、今後の論文・資料作成で同じ手順を再利用できるようにするため
- 詳細:
- `~/Library/TinyTeX` に TinyTeX が既に存在することを確認した
- TinyTeX の `lualatex` と `tlmgr` を直接利用できることを確認した
- 不足していた `luatexja`, `haranoaji`, `pgf`, `enumitem` を `tlmgr install` で追加した
- LuaTeX のフォントキャッシュ用に `TEXMFVAR=/private/tmp/bogp_texmf-var` を指定する方針にした
- `notes/提案手法ver.1.pdf` を生成した
- `scripts/compile_proposed_method_v1.sh` を追加し、TeX から PDF を再生成できるようにした
- 確認方法:
- `scripts/compile_proposed_method_v1.sh` が完走し、`notes/提案手法ver.1.pdf` を出力することを確認した
- `/private/tmp/提案手法ver.1.log` に `Warning`, `Error`, `Undefined`, `Overfull`, `Underfull` が残っていないことを確認した
- 出力 PDF は 7 ページ、約 245 KB であることを確認した
- 次にやること:
- PDF の紙面上で図の見やすさを確認し、必要であれば TikZ 図の幅や配置を調整する

### 2026-05-18 | 図1「閉ループ制御構造」の視認性改善

- 何をしたか: `notes/提案手法ver.1.tex` の図1について、矢印がブロックや文字に重なっていたため、TikZ の配置と矢印経路を見直した
- なぜそうしたか: 図1は提案手法の中心図であり、GP プラント、BO 制御器、観測量、制御入力、報酬更新の閉ループ関係が一目で読める必要があるため
- 詳細:
- ブロックを循環構造として再配置し、`State Observation`、`Contextual BO Controller`、`Action Output`、`MOGP Plant`、`Interval Statistics`、`Reward and BO Update` の流れを明確にした
- 矢印ラベルに白背景を持つ `labelbox` を追加し、線と文字が重なって読みにくくならないようにした
- 報酬更新から BO 制御器へ戻る矢印は右外側を迂回させ、`Action Output` ブロック付近を横切らないようにした
- GP プラントから状態観測へ戻る矢印は左外側を迂回させ、主要ブロックの内部を通らないようにした
- 図全体を `\resizebox{0.96\linewidth}{!}{...}` で紙面幅に収め、横方向にはみ出さないようにした
- 確認方法:
- `scripts/compile_proposed_method_v1.sh` が完走し、`notes/提案手法ver.1.pdf` を再生成できることを確認した
- `/private/tmp/提案手法ver.1.log` に `Warning`, `Error`, `Undefined`, `Overfull`, `Underfull` が残っていないことを確認した
- 出力 PDF は 8 ページ、約 245 KB であることを確認した

### 2026-05-19 | 構造類似度の同形部分木数依存性を調べる小実験

- 何をしたか: 現行の `structural_similarity` が、同形部分木を増やしたときにどのような関数形を示すか確認するための小実験を実装し、CSV と図を生成した
- なぜそうしたか: 本研究では多様性指標として構造類似度に基づく構造多様性を用いているため、この指標が「共有される同形部分木の増加」に対してどのように反応するかを把握しておく必要があったため
- 詳細:
- `src/bogp/test_v1_structural_similarity_experiment.py` を追加し、理想 multiset 実験、実木構造実験、片側増加実験、ランダム背景付き実験を実装した
- `scripts/run_test_v1_structural_similarity_experiment.py` を追加し、`similarity_curve.csv`, `similarity_curve.png`, `one_sided_curve.png`, `random_background_curve.png`, `summary.json` を出力できるようにした
- `tests/test_v1_structural_similarity_experiment.py` を追加し、理想式との一致、同一木の類似度 1、両側増加時の単調増加、片側増加時のピーク、多様性との補数関係を確認するテストを追加した
- 実行結果:
- 出力先: `/Users/kakemyo/Downloads/master_BOGP/outputs/structural_similarity_test_v1/20260519_122639`
- 共通モチーフ 1 個あたりの部分木ハッシュ数は `q=3`
- 理想 multiset 実験では理論式との最大誤差が `0.0` であり、`Sim(m)=mq/(U_A+U_B+mq)` と一致した
- 実木構造実験では、理想式よりわずかに低いが、同じ飽和型の単調増加曲線になった
- 片側増加実験では、固定側の `m=8` で類似度が最大になり、その後は木サイズ不一致により低下した
- ランダム背景付き実験では全体として類似度は上昇傾向だが、背景木サイズのばらつきにより局所的な揺れが生じた
- 簡単な考察:
- 現行の構造類似度は、同形部分木が両個体にバランスよく増えると飽和型に上昇する
- 多様性は `1 - similarity` なので、同形部分木が増えるほど飽和型に低下する
- 片側だけ同形部分木が増えても類似度は上がり続けず、共通度と木サイズのバランスが重要である
- ランダム背景付き実験の揺れは、実際の GP 集団では共通部分木数だけでなく、背景構造の大きさも類似度の分母に効くことを示している
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile src/bogp/test_v1_structural_similarity_experiment.py scripts/run_test_v1_structural_similarity_experiment.py tests/test_v1_structural_similarity_experiment.py` が通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 23 件の単体テストが通ることを確認した
- `.venv/bin/python scripts/run_test_v1_structural_similarity_experiment.py` が完走し、CSV と 3 種類の図が生成されることを確認した
- 次にやること:
- 必要であれば、構造探索問題の実個体群に対して同じ分析を行い、人工木で見た曲線と実集団での類似度分布を比較する

### 2026-05-19 | test_ver2 archive 最小修正の実装

- 何をしたか: ver1 を上書きせず、archive の完全重複除去とユニーク数集計だけを入れた `test_ver2` 実装を追加した
- なぜそうしたか: 現行の archive では同じ目的値・同じ構造の個体が複数保存され、archive size が Pareto front の実質的な広がりを過大評価しやすかったため
- 詳細:
- `src/bogp/test_ver2_mo_engine.py` を追加し、ver1 の GP エンジンを残したまま、archive のみを `(objective_key, structure_key)` で重複除去する方針へ変更した
- BO 制御器、状態ベクトル、報酬関数、`p_c,p_m,k` の選択則、archive 更新タイミングは変更していない
- `objective_key` は目的値を丸めたキー、`structure_key` は既存の `structural_tokens` に基づく構造トークン列として定義した
- HV 計算は unique objective archive に基づいて行うようにした
- `archive_size`, `archive_unique_objective_size`, `archive_unique_structure_size`, `archive_unique_pair_size` を取得できる `archive_statistics()` を追加した
- `scripts/compare_test_ver2_plain_gp_vs_bogp_template.py` と `scripts/compare_test_ver2_plain_gp_vs_bogp_structural.py` を追加し、ver2 archive 方針で提案手法と普通の GP を比較できるようにした
- `tests/test_ver2_archive.py` を追加し、同じ目的値・同じ構造は重複除去され、同じ目的値でも構造が違えば残ることを確認した
- 実行結果:
- テンプレート問題 ver2 比較では、提案手法の archive は `archive_size=5`, `archive_unique_objective_size=5`, `archive_unique_structure_size=5`, 普通の GP は `archive_size=2`, `archive_unique_objective_size=2`, `archive_unique_structure_size=2` になった
- テンプレート問題 ver2 出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/template_plain_vs_bogp_test_ver2/20260519_171401`
- 構造探索問題 ver2 比較では、提案手法の archive は `archive_size=9`, `archive_unique_objective_size=9`, `archive_unique_structure_size=9`, 普通の GP は `archive_size=7`, `archive_unique_objective_size=7`, `archive_unique_structure_size=7` になった
- 構造探索問題 ver2 出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/structural_plain_vs_bogp_test_ver2/20260519_171411`
- 提案手法への影響:
- 制御器と報酬関数は変更していないため、`p_c,p_m,k` の提案ロジックそのものへの影響は最小限である
- archive の重複が整理されたため、Pareto front 図と archive size の解釈は ver1 より正直になった
- HV は unique objective archive から計算するが、同一目的値の重複は元々 HV にほぼ寄与しないため、今回の実行では最終 HV の値は ver1 と同じになった
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile src/bogp/test_ver2_mo_engine.py scripts/compare_test_ver2_plain_gp_vs_bogp_template.py scripts/compare_test_ver2_plain_gp_vs_bogp_structural.py tests/test_ver2_archive.py` が通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 25 件の単体テストが通ることを確認した
- `.venv/bin/python scripts/compare_test_ver2_plain_gp_vs_bogp_template.py` と `.venv/bin/python scripts/compare_test_ver2_plain_gp_vs_bogp_structural.py` が完走し、unique objective Pareto front 図を生成することを確認した
- 次にやること:
- ver2 の archive 結果を見たうえで、次段階では archive 更新対象を combined に広げるか、報酬用 HV と状態用 ΔHV を見直すかを判断する

### 2026-05-19 | test_ver2 各世代 HV / Diversity 推移図の追加

- 何をしたか: test_ver2 の比較実験で、提案手法と普通の GP の HV および Diversity を各世代ごとに重ねて表示する図を追加した
- なぜそうしたか: これまでの提案手法側の比較図は制御更新点、つまり `k` 世代ごとの観測点を中心に描いていたため、普通の GP と同じ「各世代の推移」として比較しにくかったため
- 詳細:
- `src/bogp/test_ver2_mo_engine.py` に `state_history` を追加し、初期世代から最終世代までの `GPStateSnapshot` を保存できるようにした
- `scripts/compare_test_ver2_plain_gp_vs_bogp_template.py` に `per_generation_hv_diversity_comparison.png` と `bogp_per_generation_records.jsonl`, `plain_gp_per_generation_records.jsonl` の出力を追加した
- `scripts/compare_test_ver2_plain_gp_vs_bogp_structural.py` にも同様の出力を追加した
- 既存の制御更新点ベースの `hv_diversity_comparison.png` と `bogp_control_periods.png` は残した
- 実行結果:
- テンプレート問題 per-generation 図: `/Users/kakemyo/Downloads/master_BOGP/outputs/template_plain_vs_bogp_test_ver2/20260519_172654/per_generation_hv_diversity_comparison.png`
- 構造探索問題 per-generation 図: `/Users/kakemyo/Downloads/master_BOGP/outputs/structural_plain_vs_bogp_test_ver2/20260519_172715/per_generation_hv_diversity_comparison.png`
- 簡単な確認:
- テンプレート問題では、提案手法の HV が普通の GP より早く高い水準へ進み、Diversity も中盤以降で高く維持されていることが世代単位で確認できた
- 構造探索問題では、HV は両手法とも早期に飽和気味だが、Diversity は提案手法が終盤で普通の GP を上回る推移が確認できた
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile src/bogp/test_ver2_mo_engine.py scripts/compare_test_ver2_plain_gp_vs_bogp_template.py scripts/compare_test_ver2_plain_gp_vs_bogp_structural.py tests/test_ver2_archive.py` が通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 26 件の単体テストが通ることを確認した
- `.venv/bin/python scripts/compare_test_ver2_plain_gp_vs_bogp_template.py` と `.venv/bin/python scripts/compare_test_ver2_plain_gp_vs_bogp_structural.py` を再実行し、各世代ごとの HV / Diversity 図が生成されることを確認した

### 2026-05-20 | Pareto front 性能評価文献の追加調査

- 何をしたか: NSGA-II レビュー論文における Pareto front / 非優越解集合の性能評価方法を整理し、文献仕様書に従って関連文献を追加した
- なぜそうしたか: 現行実験では HV と Diversity を中心に見ているが、論文化では archive size、front の広がり、収束性、統計検定、post-Pareto 分析をどう組み合わせるかを明確にする必要があるため
- 詳細:
- `references/README.md` に [R15] から [R19] を追加した
- [R15] Audet et al. (2021) を Pareto front 近似の性能指標分類の手動取得候補として追加した
- [R16] Li, Yao (2019) を解集合品質評価の包括的 survey として追加した
- [R17] Guerreiro et al. (2021) を HV 計算と参照点設定の根拠として追加した
- [R18] Galvan et al. (2022) を多目的 GP で平均 HV と統計的評価を使う近年の実例として追加した
- [R19] Li, Chen, Yao (2022) を Pareto 解集合評価の方法論的注意として追加した
- 簡単な考察:
- NSGA-II レビュー論文では、評価は大きく「性能指標」「統計検定」「case study」「post-Pareto analysis」に分かれている
- 本研究では、最小構成として HV、unique objective archive size、spread/spacing 系指標、複数 seed の統計検定を揃えると説明しやすい
- IGD/GD は真の Pareto front または十分信頼できる reference front がある場合に使うのが自然である
- 確認方法:
- 追加文献の `.md` メタデータノートを `references/` 直下に作成した
- `references/README.md` の文献番号台帳と `notes/research_note.md` の参考文献章に用途を追記した

### 2026-05-20 | test_ver2_b archive / population 分離と構造キー切替の実装

- 何をしたか: 既存の test_v1 / test_ver2 を残したまま、archive 評価と population 状態観測を分離した `test_ver2_b` 実装を追加した
- なぜそうしたか: HV・報酬・最終 Pareto front は探索中に得た成果集合 archive で評価し、多様性や平均木サイズは現在の探索状態である population から観測する方針に整理するため
- 詳細:
- `src/bogp/test_ver2_b_mo_engine.py` を追加し、archive 更新対象を `A_g ∪ P_g ∪ Q_g` に広げた
- `GPStateSnapshot.hypervolume` は archive HV として維持し、`population_hypervolume()` で現在集団 HV を別に取得できるようにした
- `generation_metrics_history` を追加し、各世代の archive HV、population HV、population diversity、archive サイズ、unique objective / structure / pair 数を保存できるようにした
- `recent_hv_delta` は区間総改善量ではなく、archive HV の世代あたり改善量として扱うようにした
- `archive_structure_key_mode` を追加し、`topology` を test_ver2_b1、`topology_value` を test_ver2_b2 として切り替えられるようにした
- `topology` ではノードラベルと arity のみ、`topology_value` ではノードラベル、arity、ばね定数・減衰係数・定数ノード値などの `value` も構造キーに含める
- `scripts/compare_test_ver2_b_plain_gp_vs_bogp_template.py` と `scripts/compare_test_ver2_b_plain_gp_vs_bogp_structural.py` を追加し、b1/b2 を同じスクリプトで連続実行できるようにした
- `tests/test_ver2_b_archive_metrics.py` を追加し、構造キー切替、offspring 由来の非劣解 archive 保存、archive HV / population HV 分離、世代別メトリクス保存を確認した
- `notes/提案手法ver2_b.tex` と `notes/提案手法ver2_b.pdf` を追加し、提案手法 ver2_b として archive / population 分担と b1/b2 構造キーを整理した
- 実行結果:
- テンプレート問題 b1 出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/template_plain_vs_bogp_test_ver2_b1/20260520_172012`
- テンプレート問題 b2 出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/template_plain_vs_bogp_test_ver2_b2/20260520_172015`
- 構造探索問題 b1 出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/structural_plain_vs_bogp_test_ver2_b1/20260520_172025`
- 構造探索問題 b2 出力: `/Users/kakemyo/Downloads/master_BOGP/outputs/structural_plain_vs_bogp_test_ver2_b2/20260520_172026`
- 構造探索問題では b2 の提案手法 archive が `archive_size=10`, `archive_unique_objective_size=9`, `archive_unique_structure_size=10` となり、同一目的値でもパラメータ値込み構造が異なる解を保持できることが確認できた
- 確認方法:
- `.venv/bin/python -m unittest discover -s tests` で 33 件の単体テストが通ることを確認した
- `.venv/bin/python scripts/compare_test_ver2_b_plain_gp_vs_bogp_template.py` が完走し、b1/b2 両方の図と summary を生成することを確認した
- `.venv/bin/python scripts/compare_test_ver2_b_plain_gp_vs_bogp_structural.py` が完走し、b1/b2 両方の図と summary を生成することを確認した
- `lualatex` により `notes/提案手法ver2_b.pdf` を生成できることを確認した
- 次にやること:
- b1 と b2 の archive サイズ差、unique structure 数差、Pareto front 図の差を確認し、構造探索問題ではどちらの構造キーを主実験に採用するかを検討する

### 2026-05-26 | 進捗まとめ用 LaTeX レポートの作成

- 何をしたか: ver1 から ver2 シリーズ、ver2_b までの改善内容と予備実験結果をまとめた LaTeX 文書を 2 種類作成した
- なぜそうしたか: 小発表前に、自分用の詳細な振り返り資料と、他者に短時間で説明するための簡易的な進捗報告資料を分けて準備するため
- 詳細:
- `notes/progress_report_detailed_ver2_b.tex` を作成し、背景、提案手法の基本構造、ver1 / ver2 / ver2_b の改善理由、結果表、図、考察、今後の方針をレポート風に整理した
- `notes/progress_report_brief_ver2_b.tex` を作成し、他者向けに研究の狙い、改善の流れ、主要結果、分かったこと、今後の課題を簡潔にまとめた
- 既存の実験図を LaTeX 内に取り込み、テンプレート問題と構造探索問題の HV / Diversity 推移を視覚的に説明できるようにした
- それぞれ `progress_report_detailed_ver2_b.pdf` と `progress_report_brief_ver2_b.pdf` としてコンパイルした
- 確認方法:
- `lualatex` を 2 回ずつ実行し、詳細版 9 ページ、簡易版 4 ページの PDF が生成されることを確認した
- 次にやること:
- 小発表用スライドを作る場合は、簡易版を骨子にし、詳細版から必要な表・図・考察を抜き出して構成する

### 2026-05-26 | 汎用本実験ランナー基盤の追加

- 何をしたか: 本実験の主対象問題をまだ固定せず、テンプレート回帰問題・構造探索問題・今後追加する問題を同じ形式で実行できる汎用実験ランナーを追加した
- なぜそうしたか: 本実験に入る前に、問題ごとに個別スクリプトを書く状態から脱し、seed 反復、手法比較、ログ保存、集計、図作成を共通化するため
- 詳細:
- `src/bogp/formal_experiment.py` を追加し、`ProblemSpec`, `FormalExperimentConfig`, `FixedRateMethodConfig`, `run_problem_experiment`, `run_registered_experiment` を定義した
- 既存の `test_ver2_b` エンジンは上書きせず、本実験用ランナーから再利用する構成にした
- 比較手法の最小構成として、固定率 GP の `plain_fixed` と現在の提案法 `bogp_current` を同じ runner から実行できるようにした
- 各 run ごとに `summary.json`, `generation_metrics.jsonl`, `control_records.jsonl`, `pareto_archive.json`, `unique_objective_archive.json` を保存する形式に統一した
- 実験全体の集計として `summary_by_seed.csv`, `aggregate_summary.csv`, `run_summaries.json` を出力するようにした
- 共通図として `hv_progress.png`, `diversity_progress.png`, `archive_size_progress.png`, 2 目的問題では seed 別 Pareto front 図を生成するようにした
- 3 目的以上の問題では、現段階の exact HV が 2 目的専用であるため、ログ上は HV を `not_available` として扱う設計にした
- `scripts/run_formal_experiment.py` を追加し、CLI から登録済み問題を実行できる入口を用意した
- `tests/test_formal_experiment_runner.py` を追加し、テンプレート問題、構造探索問題、3 目的ダミー問題で共通 runner が動作することを確認した
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile src/bogp/formal_experiment.py scripts/run_formal_experiment.py tests/test_formal_experiment_runner.py` が通ることを確認した
- `.venv/bin/python -m unittest tests/test_formal_experiment_runner.py` で 3 件の新規テストが通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 36 件の全テストが通ることを確認した
- `.venv/bin/python scripts/run_formal_experiment.py --problem template --seeds 0 --population-size 6 --total-generations 1 --run-id cli_smoke --output-root /private/tmp/bogp_formal_cli_smoke` が完走し、`/private/tmp/bogp_formal_cli_smoke/template/cli_smoke` に出力が生成されることを確認した
- 次にやること:
- この runner を使って小規模 pilot 実験を回し、問題ごとの HV 飽和、Diversity 推移、archive サイズ、制御履歴の見え方を確認する
- その後、`k` の warm-up や EI 比較方法など BO 制御器内部の調整に進む

### 2026-05-26 | 本実験の問題設定候補文献の調査

- 何をしたか: 本実験で使う問題設定を決める前段階として、GP / MOGP / symbolic regression / 構造探索に関する問題設定文献を調査した
- なぜそうしたか: 提案手法の有効性を示すには、固定率 GP と状態依存 BOGP の差が出やすく、かつ Pareto front と diversity の説明がしやすい問題を選ぶ必要があるため
- 詳細:
- `reference_candidates/problem_settings/` を作成し、正式参考文献欄とは分けた問題設定候補フォルダとして管理することにした
- `reference_candidates/problem_settings/README.md` に問題設定候補の優先順位、採用判断基準、推奨する最小構成を整理した
- `reference_candidates/problem_settings/problem_setting_sources.md` に `PS01` から `PS09` として候補文献を整理した
- 正式な `references/README.md` にはまだ追加していない
- PDF として保存できた文献:
- `Genetic Programming Needs Better Benchmarks.pdf`
- `Better GP Benchmarks - Community Survey Results and Proposals.pdf`
- `Evolvability Degeneration in Multi-Objective Genetic Programming for Symbolic Regression.pdf`
- `Automated Synthesis of Mechanical Vibration Absorbers Using Genetic Programming.pdf`
- HTML として保存した文献:
- `Contemporary Symbolic Regression Methods and their Relative Performance.html`
- 調査時点の結論:
- 第一候補は accuracy--complexity symbolic regression。2 目的で実装しやすく、HV と Pareto front を説明しやすい
- 第二候補は spring-damper structural search。現在の構造探索コードと近く、構造探索研究としての説得力がある
- 第三候補は evolvability-stressed symbolic regression。MOGP における低複雑度個体の過剰複製や diversity 問題が出やすく、提案法の状態依存性を示しやすい
- shape-constrained symbolic regression と CSG structural topology optimization は有望だが、3 目的対応や実装負荷の観点から後続候補とした
- 次にやること:
- 候補問題を 2--3 個に絞り、現在の汎用本実験ランナーに差し込むための `ProblemSpec` と目的関数定義を設計する
- まず小規模 pilot で HV 飽和、diversity 推移、archive size、Pareto front の見え方を確認する

### 2026-05-27 | 2目的シンボリック回帰の問題設定案の整理

- 何をしたか: シンボリック回帰を本研究の最初の 2 目的問題として使うため、文献調査に基づいて目的関数、関数集合、データ分割、候補 benchmark を整理した
- なぜそうしたか: 提案手法の有効性を見るには、accuracy と complexity の trade-off が自然に生じ、かつ多様性低下や bloat が起きうる問題設定が必要であるため
- 詳細:
- `reference_candidates/problem_settings/symbolic_regression_2objective_setting.md` を追加した
- 2 目的は `f_1 = train NRMSE`, `f_2 = tree size` を基本案とした
- HV 用には誤差と木サイズを正規化・clip する方針を整理した
- 関数集合は初期案として `{+, -, *, protected_div, sin, cos}`、終端集合は変数と ephemeral constants とした
- 候補問題として、実装確認用 `y=x^2+x`、本実験候補 `Friedman-I`、多様性・探索停滞を見やすい `Poly-10`、後続候補として Pagie-like nonlinear problem と PMLB / SRBench 由来の real-world regression を整理した
- 調査時点の結論:
- 最初の主候補は Friedman-I と Poly-10 の 2 問にするのがよい
- `y=x^2+x` は smoke test に留め、本実験の主結果には使わない
- PMLB / SRBench 系 dataset は、synthetic benchmark で挙動を固めた後に追加する
- 次にやること:
- Friedman-I と Poly-10 を `GPProblem` として実装する計画を作成する
- 実装前に `E_max`, `L_max`, sample 数、noise 有無、train/validation/test の扱いを確定する

### 2026-05-28 | 本実験用テスト問題 ver_alpha の実装と pilot 実行

- 何をしたか: 2 目的シンボリック回帰を本実験用テスト問題 `ver_alpha` として実装し、Friedman-I と Poly-10 を通常 GP と BO 制御 GP で比較した
- なぜそうしたか: 提案手法の本実験候補として、accuracy と complexity の Pareto front を持つ symbolic regression 問題を実際に動かせる形にするため
- 詳細:
- `src/bogp/symbolic_regression_alpha.py` を追加し、`SymbolicRegressionAlphaProblem` と `AlphaExpressionNode` を実装した
- 目的関数は `train_nrmse` と `tree_size` の 2 目的とした
- 関数集合は `{+, -, *, protected_div, sin, cos}`、終端集合は変数と ephemeral constants とした
- `target_name` により `friedman_i` と `poly10` を切り替えられるようにした
- `src/bogp/formal_experiment.py` に `sr_alpha_friedman` と `sr_alpha_poly10` を登録した
- `scripts/run_symbolic_regression_alpha_experiment.py` を追加し、2 問題を seed 0,1,2 でまとめて実行できるようにした
- `tests/test_symbolic_regression_alpha.py` を追加し、目的関数評価、protected division、登録済み問題の smoke 実行を確認した
- 初回実行では `error_upper=1.0` により HV が 0 に潰れたため、`error_upper=5.0` に変更して再実行した
- 実行条件:
- 問題: `sr_alpha_friedman`, `sr_alpha_poly10`
- 手法: `plain_fixed`, `bogp_current`
- seed: `0,1,2`
- population size: `24`
- total generations: `30`
- evaluations per run: `720`
- 出力:
- Friedman-I: `/Users/kakemyo/Downloads/master_BOGP/outputs/symbolic_regression_alpha/sr_alpha_friedman/ver_alpha_20260528_205110`
- Poly-10: `/Users/kakemyo/Downloads/master_BOGP/outputs/symbolic_regression_alpha/sr_alpha_poly10/ver_alpha_20260528_205110`
- 結果概要:
- Friedman-I では、BO 制御 GP の平均 final archive HV が `0.78495`、通常 GP が `0.68354` となり、今回の小規模 pilot では BO 制御 GP が高かった
- Friedman-I の diversity は通常 GP が `0.68812`、BO 制御 GP が `0.66576` で大差はなかった
- Poly-10 では、BO 制御 GP の平均 final archive HV が `0.79946`、通常 GP が `0.79980` でほぼ同等だった
- Poly-10 は両手法とも HV が高い値で揃っており、今回の設定では差が出にくい可能性がある
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile src/bogp/symbolic_regression_alpha.py src/bogp/formal_experiment.py scripts/run_symbolic_regression_alpha_experiment.py tests/test_symbolic_regression_alpha.py` が通ることを確認した
- `.venv/bin/python -m unittest tests/test_symbolic_regression_alpha.py` で 3 件の新規テストが通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 39 件の全テストが通ることを確認した
- `.venv/bin/python scripts/run_symbolic_regression_alpha_experiment.py` が完走することを確認した
- 注意点:
- BO の GaussianProcessRegressor で `ConvergenceWarning` が複数出たが、実行は正常終了した。BO 制御器の詳細調整段階で kernel bound や warning 抑制を検討する
- Poly-10 は現行設定では差が見えにくいため、次は世代数、木サイズ上限、関数集合、noise、データ点数を調整して難易度を確認する

### 2026-05-29 | proto_alpha 実験結果の LaTeX レポート化

- 何をしたか: 2 目的シンボリック回帰の pilot 実験を `proto_alpha` として位置づけ、対象問題、実験条件、結果、考察、今後の方針を LaTeX レポートにまとめた
- なぜそうしたか: 小発表や本実験準備で、今回の実験が何を確認するためのものだったのか、どの結果が有望で、どの設定に再検討が必要かを説明しやすくするため
- 作成物:
- `notes/proto_alpha_symbolic_regression_report.tex`
- `notes/proto_alpha_symbolic_regression_report.pdf`
- レポートに含めた内容:
- proto_alpha の位置づけ
- 対象問題 `sr_alpha_friedman` と `sr_alpha_poly10` の定義
- 2 目的 `train_nrmse` と `tree_size` の意味
- 通常 GP と BO 制御 GP の比較条件
- Friedman-I と Poly-10 の final archive HV, diversity, archive size の表
- HV 推移、多様性推移、archive size 推移、最終 Pareto front の図
- 結果からわかること:
- Friedman-I では BO 制御 GP が通常 GP より高い final archive HV を示し、提案手法の有効性を確認する問題として有望である
- Poly-10 では両手法の HV が初期から高く、今回の設定では差が見えにくいため、難易度調整または別問題の併用が必要である
- 注意点:
- 今回は seed 3 本・30 世代の小規模 pilot であり、統計的結論ではなく本実験設計のための予備確認として扱う
- BO 制御器の詳細設計、特に `k` の warm-up、EI 比較、kernel bound はまだ調整対象として残っている
- 確認方法:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/proto_alpha_symbolic_regression_report.tex` を 2 回実行し、PDF が生成されることを確認した

### 2026-05-29 | proto_alpha レポート図の凡例修正

- 何をしたか: proto_alpha レポートで使用している HV, Diversity, archive size の履歴図について、各線に手法名と seed 番号が分かる凡例を付けるように修正した
- なぜそうしたか: これまでの履歴図では seed ごとに複数本の線を描いているにもかかわらず、凡例が `plain_fixed` と `bogp_current` の 2 種類だけであり、各線がどの試行を表すか分かりにくかったため
- 変更内容:
- `src/bogp/formal_experiment.py` の `_plot_metric_history()` を修正し、凡例ラベルを `method_name (seed=n)` の形式にした
- 同じ手法は同系統の色、seed の違いは線種と marker の違いでも見分けられるようにした
- 保存済みの proto_alpha 実験データを再利用し、実験は再実行せずに図だけを再生成した
- `notes/proto_alpha_symbolic_regression_report.tex` に、履歴図の各線が 1 回の試行に対応することを説明する文を追加した
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile src/bogp/formal_experiment.py` が通ることを確認した
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/proto_alpha_symbolic_regression_report.tex` を実行し、PDF が再生成されることを確認した
- `notes/proto_alpha_symbolic_regression_report.log` に未解決参照がないことを確認した

### 2026-05-29 | proto_alpha の BO 制御履歴解析と次段階 BO 調整案の整理

- 何をしたか: proto_alpha レポートの「次に行うべきこと」4番に対応して、BO 制御履歴 `p_c,p_m,k` と HV / Diversity の関係を問題ごとに解析した
- なぜそうしたか: 提案手法では `k` を単なる効率化変数ではなく制御周期として扱うため、実際にどの `k` がどの局面で選ばれ、性能・多様性とどう対応したかを確認する必要があるため
- 追加したスクリプト:
- `scripts/analyze_proto_alpha_control_relationships.py`
- 出力先:
- `outputs/symbolic_regression_alpha/proto_alpha_control_analysis/ver_alpha_20260528_205110`
- 生成物:
- `control_interval_analysis_all.csv`
- `control_interval_summary_by_problem_k.csv`
- `problem_k_comparison.png`
- `proto_alpha_control_analysis_summary.md`
- 問題別の `control_metric_timeline_seed_*.png`
- 問題別の `hv_diversity_k_alignment_seed_*.png`
- 問題別の `control_interval_outcomes_by_k.png`
- 解析内容:
- BO の 1 制御区間を 1 行として扱い、開始 HV、終了 HV、世代あたり HV 改善量、開始 diversity、終了 diversity、区間平均 diversity、報酬、`p_c,p_m,k` を対応づけた
- Friedman-I では `k=1` が世代あたり HV 改善量で最も高く、`k=5` は区間総改善量と diversity 変化で良い傾向を示した
- Poly-10 ではどの `k` でも HV 改善量が非常に小さく、現行設定では BO 制御器比較の主対象としては弱いことを再確認した
- 分かった懸念:
- 現行 warm-up は概ね `k=1,1,3,3,5,5` の順で観測を埋めるため、`k` の効果と世代進行の影響が混ざりやすい
- 各 `k` に同じ観測数を配ると、実際に消費する GP 世代数は `k` によって異なる
- 現行 EI は `k` ごとの best reward を基準にしており、`k` 間で同じ基準の EI 比較になっているか検討が必要である
- 追加した研究メモ:
- `notes/proto_alpha_control_and_bo_adjustment_plan.md`
- 次段階の推奨:
- まず Friedman-I で `bo_current`, `bo_interleaved_warmup`, `bo_global_best_ei`, `bo_interleaved_global_ei` を比較する
- その後、`BO-fixed-k1/3/5` を追加して、`k` を動的制御対象に含める意義を検証する
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/analyze_proto_alpha_control_relationships.py` が通ることを確認した
- `.venv/bin/python scripts/analyze_proto_alpha_control_relationships.py` が完走し、62 個の制御区間を解析できることを確認した

### 2026-05-29 | ver_beta_kEI の実装と bo_current との比較

- 何をしたか: BO 制御器の warm-up と EI 比較基準を改善した `ver_beta_kEI` を実装し、現行 `bo_current` と比較した
- なぜそうしたか: proto_alpha の制御履歴解析から、現行 warm-up では `k=1,1,3,3,5,5` のように試行順序が偏り、`k` の効果と世代進行の影響が混ざる懸念が見えたため
- 実装内容:
- `src/bogp/controller.py` に `warmup_strategy` を追加した
- `warmup_strategy="sequential"` は従来通り
- `warmup_strategy="interleaved"` は `k=1,3,5,1,3,5` のように warm-up を混ぜる
- `src/bogp/controller.py` に `ei_best_scope` を追加した
- `ei_best_scope="per_k"` は従来通り k ごとの best reward を EI 基準にする
- `ei_best_scope="global"` は全 k 共通の best reward を EI 基準にする
- `tests/test_v1_controller_k.py` に interleaved warm-up, global EI best, 不正設定のテストを追加した
- `scripts/run_proto_beta_kEI_comparison.py` を追加し、`bo_current` と `ver_beta_kEI` を同条件で比較できるようにした
- 実験条件:
- 問題: `sr_alpha_friedman`, `sr_alpha_poly10`
- seed: `0,1,2`
- population size: `24`
- total generations: `30`
- evaluations per run: `720`
- 出力:
- Friedman-I: `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_20260529_120723`
- Poly-10: `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_20260529_120723`
- 結果概要:
- Friedman-I では `bo_current` の平均 final archive HV が `0.78495`、`ver_beta_kEI` が `0.77184` であり、現行版の方が高かった
- Friedman-I の平均 final diversity は `bo_current` が `0.66576`、`ver_beta_kEI` が `0.72028` であり、`ver_beta_kEI` の方が高かった
- Poly-10 では `bo_current` の平均 final archive HV が `0.79946`、`ver_beta_kEI` が `0.79969` でわずかに `ver_beta_kEI` が高かった
- Poly-10 の平均 final diversity は `bo_current` が `0.56956`、`ver_beta_kEI` が `0.33028` であり、`ver_beta_kEI` で大きく低下した
- 考察:
- `ver_beta_kEI` は warm-up の k 順序を意図通り改善できたが、最終 HV の改善には直結しなかった
- Friedman-I では diversity を高く保つ方向に寄った一方、HV 改善は現行版より弱くなった可能性がある
- Poly-10 は現行設定では HV が飽和気味であり、HV の微小差より diversity 低下の方を重く見るべきである
- 次にやること:
- `interleaved only` と `global EI only` を追加し、warm-up 改善と EI 改善のどちらが結果に効いたかを切り分ける
- `ver_beta_kEI` を正規版に置き換えるのではなく、現時点では BO 制御器設計の ablation 候補として扱う
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile src/bogp/controller.py tests/test_v1_controller_k.py scripts/run_proto_beta_kEI_comparison.py` が通ることを確認した
- `.venv/bin/python -m unittest tests/test_v1_controller_k.py` で 5 件の controller テストが通ることを確認した
- `.venv/bin/python -m unittest discover -s tests` で 42 件の全テストが通ることを確認した
- `.venv/bin/python scripts/run_proto_beta_kEI_comparison.py` が完走することを確認した
- 注意:
- 実行中に sklearn の `ConvergenceWarning` が複数出たが、実験自体は正常終了した。BO kernel bound は後続の調整対象である

### 2026-05-29 | ver_beta_k / ver_beta_EI を追加した BO 制御器 ablation 比較

- 何をしたか: 前回の `ver_beta_kEI` で同時に変更していた warm-up 改善と EI 改善を切り分けるため、`ver_beta_k` と `ver_beta_EI` を追加して 4 条件比較を行った
- なぜそうしたか: `ver_beta_kEI` では Friedman-I の diversity は上がった一方で final HV が下がったため、悪化要因が interleaved warm-up なのか global EI なのか、あるいは両者の組み合わせなのかを確認する必要があったため
- 比較条件:
- `bo_current`: sequential warm-up + per-k EI best
- `ver_beta_k`: interleaved warm-up + per-k EI best
- `ver_beta_EI`: sequential warm-up + global-best EI
- `ver_beta_kEI`: interleaved warm-up + global-best EI
- 実装内容:
- `scripts/run_proto_beta_kEI_comparison.py` を更新し、上記 4 条件を同じ seed・同じ問題・同じ評価回数で実行できるようにした
- 既存の `BOControllerConfig.warmup_strategy` と `BOControllerConfig.ei_best_scope` を設定で切り替えるだけにし、GP エンジンや報酬設計は変更していない
- 出力:
- Friedman-I: `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_20260529_122615`
- Poly-10: `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_20260529_122615`
- Friedman-I の結果:
- `bo_current`: final archive HV mean `0.784951`, diversity mean `0.665762`
- `ver_beta_k`: final archive HV mean `0.785831`, diversity mean `0.689566`
- `ver_beta_EI`: final archive HV mean `0.783829`, diversity mean `0.659011`
- `ver_beta_kEI`: final archive HV mean `0.771838`, diversity mean `0.720279`
- Poly-10 の結果:
- `bo_current`: final archive HV mean `0.799458`, diversity mean `0.569561`
- `ver_beta_k`: final archive HV mean `0.799521`, diversity mean `0.368478`
- `ver_beta_EI`: final archive HV mean `0.799183`, diversity mean `0.557039`
- `ver_beta_kEI`: final archive HV mean `0.799690`, diversity mean `0.330284`
- 考察:
- Friedman-I では `ver_beta_k` が平均 HV と標準偏差の両面で最も良く、warm-up を interleaved にして `k` の試行順序を公平化する変更は有望である
- `ver_beta_EI` は単独ではほぼ現行版と同等であり、global EI の改善効果は今回の小規模条件では限定的である
- `ver_beta_kEI` は diversity と archive size を増やす一方で Friedman-I の HV が下がったため、warm-up 改善と global EI を単純に組み合わせると探索が広がりすぎる、または HV 押し上げが弱くなる可能性がある
- Poly-10 は全手法の HV が 0.799 付近に集中しており、今回の設定では BO 制御器調整の主判断材料にはしにくい
- 次にやること:
- 本実験候補としては `ver_beta_k` を優先し、`ver_beta_EI` と `ver_beta_kEI` は ablation 用に残す
- Friedman-I で seed 数を増やし、`ver_beta_k` の安定性改善が再現するか確認する
- Poly-10 は難易度調整または補助問題としての位置づけを検討する
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/run_proto_beta_kEI_comparison.py` が通ることを確認した
- `.venv/bin/python scripts/run_proto_beta_kEI_comparison.py` が完走することを確認した
- `.venv/bin/python -m unittest discover -s tests` で 42 件の全テストが通ることを確認した
- 追加メモ:
- `notes/proto_beta_kEI_comparison_summary.md` に 4 条件比較の表と考察を追記した
- 実行中に sklearn の `ConvergenceWarning` が複数出たが、実験自体は正常終了した。BO kernel bound は引き続き後続の調整対象である

### 2026-05-29 | ver_beta ablation の seed 別追加図の作成

- 何をしたか: `bo_current`, `ver_beta_k`, `ver_beta_EI`, `ver_beta_kEI` の比較について、各 seed ごとに archive HV、population diversity、更新周期 `k` を 1 枚にまとめた追加図を作成した
- なぜそうしたか: 既存の `hv_progress.png` と `diversity_progress.png` は 4 手法 × 3 seed の全線を 1 枚に重ねており、全体傾向は見えるが、個別 seed 内での手法差が読みにくかったため
- 追加したスクリプト:
- `scripts/plot_proto_beta_seedwise_comparison.py`
- 作成した図:
- `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_20260529_122615/seedwise_hv_diversity_k_seed_0.png`
- `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_20260529_122615/seedwise_hv_diversity_k_seed_1.png`
- `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_20260529_122615/seedwise_hv_diversity_k_seed_2.png`
- `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_20260529_122615/seedwise_hv_diversity_k_seed_0.png`
- `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_20260529_122615/seedwise_hv_diversity_k_seed_1.png`
- `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_20260529_122615/seedwise_hv_diversity_k_seed_2.png`
- 図の読み方:
- 上段は archive HV で、最終的な Pareto front 近似の進展を見る
- 中段は population diversity で、現在集団の構造的な広がりを見る
- 下段は BO が各制御区間で選択した `k` で、どの手法がいつ密に更新し、いつ粗く更新したかを見る
- 既存図は削除・上書きせず、追加図だけを同じ出力フォルダに保存した
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/plot_proto_beta_seedwise_comparison.py` が通ることを確認した
- `.venv/bin/python scripts/plot_proto_beta_seedwise_comparison.py` が完走し、Friedman-I と Poly-10 で合計 6 枚の seed 別図が生成されることを確認した
- `notes/proto_beta_kEI_comparison_summary.md` に seed 別追加可視化の説明を追記した

### 2026-05-29 | ver_beta 4 条件の seed 50 再比較

- 何をしたか: `bo_current`, `ver_beta_k`, `ver_beta_EI`, `ver_beta_kEI` の 4 条件比較を seed 0 から 49 の 50 本で再実行した
- なぜそうしたか: seed 3 本では `ver_beta_k` が良く見えたが、ばらつきが大きく、平均だけでなく標準偏差も含めて安定性を確認する必要があったため
- 実装上の調整:
- `scripts/run_proto_beta_kEI_comparison.py` に `--seed-count`, `--seed-start`, `--run-label`, `--problem`, `--skip-plots` を追加し、seed 数や対象問題をコマンドラインから変えられるようにした
- seed 50 では全 seed 重ね図が重く読みにくいため、今回の実行では `--skip-plots` を使って CSV 集計を優先した
- Poly-10 の途中で個体木の deepcopy が Python の再帰上限に到達したため、実験実行時の再帰上限を上げた。アルゴリズムや GP 操作は変更していない
- 出力:
- Friedman-I: `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_seed50_20260529_154012`
- Poly-10: `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_seed50_20260529_155025`
- Friedman-I の結果:
- `bo_current`: final archive HV mean `0.776702`, std `0.056612`, diversity mean `0.616345`, std `0.119777`
- `ver_beta_k`: final archive HV mean `0.769842`, std `0.056652`, diversity mean `0.605506`, std `0.126564`
- `ver_beta_EI`: final archive HV mean `0.779312`, std `0.047184`, diversity mean `0.618944`, std `0.118501`
- `ver_beta_kEI`: final archive HV mean `0.761945`, std `0.077493`, diversity mean `0.593911`, std `0.151447`
- Poly-10 の結果:
- `bo_current`: final archive HV mean `0.807258`, std `0.013684`, diversity mean `0.542788`, std `0.189975`
- `ver_beta_k`: final archive HV mean `0.808129`, std `0.013714`, diversity mean `0.542272`, std `0.205808`
- `ver_beta_EI`: final archive HV mean `0.807570`, std `0.013730`, diversity mean `0.545946`, std `0.179187`
- `ver_beta_kEI`: final archive HV mean `0.808818`, std `0.014069`, diversity mean `0.549244`, std `0.189135`
- 考察:
- Friedman-I では seed 50 に増やすと `ver_beta_EI` が平均 HV と標準偏差の両面で最も良く、3 seed 時点で有望だった `ver_beta_k` は現行版より低くなった
- `ver_beta_kEI` は Friedman-I で平均 HV が最も低く、標準偏差も大きいため、warm-up 改善と global EI を単純に同時導入する方針は不安定な可能性がある
- Poly-10 では `ver_beta_kEI` が平均 HV で最も高いが、手法間の差は標準偏差に比べてかなり小さく、強い優位とは解釈しにくい
- 次にやること:
- seed ごとの paired difference を計算し、平均差が seed 内比較でも安定しているか確認する
- 必要に応じて Wilcoxon signed-rank test などの統計検定を追加する
- Poly-10 では archive size の標準偏差が大きいため、外れ値 seed の挙動を確認する
- 追加メモ:
- 詳細は `notes/proto_beta_seed50_comparison_summary.md` にまとめた

### 2026-06-01 | ver_beta 4 条件の seed 100 再比較

- 何をしたか: `bo_current`, `ver_beta_k`, `ver_beta_EI`, `ver_beta_kEI` の 4 条件比較を seed 0 から 99 の 100 本で再実行した
- なぜそうしたか: seed 50 で見えた傾向が seed 数をさらに増やしても維持されるかを確認し、平均だけでなく標準偏差と seed 内差分から安定性を評価するため
- 実行条件:
- 問題: `sr_alpha_friedman`, `sr_alpha_poly10`
- seed: `0..99`
- population size: `24`
- total generations: `30`
- evaluations per run: `720`
- archive key: `topology_value`
- 出力:
- Friedman-I: `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_friedman/ver_beta_kEI_seed100_20260601_004320`
- Poly-10: `outputs/symbolic_regression_alpha_bo_compare/sr_alpha_poly10/ver_beta_kEI_seed100_20260601_005758`
- Friedman-I の結果:
- `bo_current`: final archive HV mean `0.773081`, std `0.055720`, diversity mean `0.603050`, std `0.123937`
- `ver_beta_k`: final archive HV mean `0.774463`, std `0.046293`, diversity mean `0.603639`, std `0.119035`
- `ver_beta_EI`: final archive HV mean `0.774922`, std `0.050454`, diversity mean `0.606697`, std `0.122603`
- `ver_beta_kEI`: final archive HV mean `0.771281`, std `0.066523`, diversity mean `0.600508`, std `0.139885`
- Poly-10 の結果:
- `bo_current`: final archive HV mean `0.809864`, std `0.015390`, diversity mean `0.540157`, std `0.171922`
- `ver_beta_k`: final archive HV mean `0.810086`, std `0.015479`, diversity mean `0.564073`, std `0.185181`
- `ver_beta_EI`: final archive HV mean `0.810057`, std `0.015132`, diversity mean `0.549069`, std `0.168610`
- `ver_beta_kEI`: final archive HV mean `0.811320`, std `0.016155`, diversity mean `0.558273`, std `0.174853`
- seed 内差分:
- Friedman-I では `ver_beta_EI - bo_current` の HV 差分平均が `0.001841`、差分標準偏差が `0.012167` で最も安定していた
- Friedman-I では `ver_beta_kEI - bo_current` の HV 差分平均が `-0.001800` であり、平均では悪化した
- Poly-10 では `ver_beta_kEI - bo_current` の HV 差分平均が `0.001456` で最も高かったが、差分標準偏差は `0.016811` と大きく、median diff はほぼ 0 だった
- 考察:
- seed 100 でも、Friedman-I では `ver_beta_EI` が平均 HV で最良であり、`ver_beta_kEI` は不安定という傾向が維持された
- Poly-10 では `ver_beta_kEI` が平均 HV で最良だが、差は標準偏差に比べて小さいため、強い優位とは言いにくい
- `k` の interleaved warm-up と global EI を同時に入れると、`k` 間比較が強くなりすぎ、問題によっては不安定化する可能性がある
- 次にやること:
- `ver_beta_EI` を次候補として、Friedman-I で paired difference の可視化と統計検定を行う
- `ver_beta_kEI` は「同時改善が必ずしも有効ではない」ことを示す ablation として残す
- `k` 別の報酬分布を標準化した EI や、`k` 別 surrogate の比較方法を再検討する
- 追加メモ:
- 詳細は `notes/proto_beta_seed100_comparison_summary.md` にまとめた

### 2026-06-02 | beta_EI における EI 説明の LaTeX 化

- 何をしたか: `beta_EI` で用いる EI の意味、`bo_current` との違い、100 seed 比較結果からの読み取りを LaTeX 形式で整理した
- なぜそうしたか: 今後 `beta_EI` を基準候補として進める前に、EI の基準値を `k` ごとに見る場合と全 `k` 共通で見る場合の違いを、研究メモ・発表資料・論文下書きへ転用しやすい形で固定するため
- 作成物:
- `notes/beta_EI_explanation.tex`
- `notes/beta_EI_explanation.pdf`
- 内容:
- EI の基本式と、予測平均・予測分散・改善基準値の役割を整理した
- `bo_current` は `k` ごとの履歴内最良報酬を基準に EI を計算する `per_k` 方式であると整理した
- `beta_EI` は全ての `k` の履歴内最良報酬を共通基準にする `global` 方式であり、更新周期どうしを同じ基準で比較しやすいことを説明した
- seed 100 比較では、Friedman-I で `beta_EI` が平均 HV と差分安定性の面で有望であり、Poly-10 でも現行法と同等以上の傾向を示したことをまとめた
- 確認方法:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/beta_EI_explanation.tex` で PDF 生成を確認した
- フォントサイズ置換の警告は残ったが、コンパイルは成功し、PDF は 6 ページで生成された

### 2026-06-02 | beta_EI 説明資料への図表追加

- 何をしたか: `notes/beta_EI_explanation.tex` に図とグラフを追加し、説明を視覚的に理解しやすくした
- なぜそうしたか: EI の基準値を `k` ごとに見る方式と全 `k` 共通で見る方式の違いは数式だけでは直感的に伝わりにくいため、制御フロー図、基準値比較図、seed 100 実験結果の棒グラフを使って説明できるようにするため
- 追加した図:
- `notes/figures/beta_EI/beta_EI_control_flow.png`: BO 制御器内で EI 基準値の変更がどこに入るかを示す概念図
- `notes/figures/beta_EI/ei_reference_comparison.png`: `bo_current` と `beta_EI` の EI 基準値の違いを数値例で示す図
- `notes/figures/beta_EI/seed100_hv_diversity_bars.png`: Friedman-I と Poly-10 の final HV / diversity を平均 ± 標準偏差で比較する図
- `notes/figures/beta_EI/seed100_hv_diff_vs_bo_current.png`: `bo_current` を基準にした seed 内 final HV 差分の図
- 実装上の変更:
- `scripts/plot_beta_EI_explanation_figures.py` を追加し、図を再生成できるようにした
- Matplotlib の描画バックエンドを `Agg` に固定し、GUI を開かずに PNG を保存するようにした
- `notes/beta_EI_explanation.tex` に `graphicx` を追加し、生成した図を本文中に埋め込んだ
- 確認方法:
- `MPLCONFIGDIR=/private/tmp/bogp_matplotlib .venv/bin/python scripts/plot_beta_EI_explanation_figures.py` で図を生成した
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/beta_EI_explanation.tex` を複数回実行し、図参照が解決された PDF を生成した
- PDF は 7 ページで生成された。フォントサイズ置換の警告は残るが、図の取り込みとコンパイルは正常に完了した

### 2026-06-02 | Seminar 後に検討する資料の退避

- 何をしたか: `beta_EI` の説明 PDF を Seminar 後に再検討する資料として `notes/Seminar後検討/` にコピーした
- なぜそうしたか: 本実験 for Seminar では一旦 `bo_current` 方針で進め、`beta_EI` や EI 基準値の変更案は Seminar 終了後に改めて検討するため
- 保存先:
- `notes/Seminar後検討/beta_EI_explanation.pdf`
- 方針メモ:
- 今回の Seminar 向け本実験では `bo_current` を採用する
- `beta_EI` は有望な検討候補として残すが、現時点では本線にはしない

### 2026-06-02 | Seminar 用 bo_current 本実験: Friedman-I seed 100

- 何をしたか: Seminar 用本実験として、Friedman-I symbolic regression のみを対象に `bo_current` と固定率 GP 3 条件を seed 100 本で比較した
- なぜそうしたか: Seminar ではまず対象問題を Friedman-I に絞り、現時点の本線である `bo_current` 方針の有効性と課題を整理するため
- 実験条件:
- problem: `sr_alpha_friedman`
- seed: `0..99`
- population size: `24`
- total generations: `30`
- evaluations/run: `720`
- archive key: `topology_value`
- 比較手法:
- `plain_fixed_standard`: `p_c=0.80`, `p_m=0.05`
- `plain_fixed_high_mutation`: `p_c=0.70`, `p_m=0.20`
- `plain_fixed_high_crossover`: `p_c=0.90`, `p_m=0.05`
- `bogp_current`: `p_c,p_m,k` を文脈付き BO で制御
- 出力先:
- `outputs/seminar_bo_current/sr_alpha_friedman/seminar_bo_current_seed100_20260602`
- 主な結果:
- `plain_fixed_standard`: final archive HV mean `0.757001`, std `0.076593`, diversity mean `0.601648`
- `plain_fixed_high_mutation`: final archive HV mean `0.776600`, std `0.051848`, diversity mean `0.609492`
- `plain_fixed_high_crossover`: final archive HV mean `0.764665`, std `0.072106`, diversity mean `0.615219`
- `bogp_current`: final archive HV mean `0.773081`, std `0.055720`, diversity mean `0.603050`
- seed 内差分:
- `bogp_current - plain_fixed_standard`: HV diff mean `0.016080`, win/tie/loss `64/4/32`
- `bogp_current - plain_fixed_high_mutation`: HV diff mean `-0.003519`, win/tie/loss `40/4/56`
- `bogp_current - plain_fixed_high_crossover`: HV diff mean `0.008416`, win/tie/loss `54/2/44`
- `bogp_current - best fixed per seed`: HV diff mean `-0.020092`, win/tie/loss `21/1/78`
- `bo_current` の制御傾向:
- k selection counts: `{1: 491, 3: 333, 5: 302}`
- mean `p_c`: `0.7025`
- mean `p_m`: `0.1381`
- mean control steps: `11.26`
- 考察:
- `bo_current` は標準固定率 GP と高交叉固定率 GP より final HV 平均が高く、閉ループ制御の枠組みは動作している
- 一方で、高突然変異固定率 GP が最良 HV 平均となり、`bo_current` は tuned baseline を安定して上回る段階にはまだ達していない
- Seminar では「提案法が全 baseline に勝った」ではなく、「標準固定率を上回るが、報酬設計・BO制御器・k の扱いに改善余地がある」と説明するのが妥当である
- 作成物:
- `scripts/run_seminar_bo_current_experiment.py`
- `scripts/summarize_seminar_bo_current_results.py`
- `outputs/seminar_bo_current/sr_alpha_friedman/seminar_bo_current_seed100_20260602/seminar_bo_current_friedman_summary.md`
- `outputs/seminar_bo_current/sr_alpha_friedman/seminar_bo_current_seed100_20260602/seminar_analysis_summary.json`
- `notes/seminar_bo_current_friedman_report.tex`
- `notes/seminar_bo_current_friedman_report.pdf`
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/run_seminar_bo_current_experiment.py`
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/summarize_seminar_bo_current_results.py`
- `.venv/bin/python -m unittest tests.test_formal_experiment_runner`
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/seminar_bo_current_friedman_report.tex`
- 備考:
- 当初は Friedman-I と Poly-10 の両方を実行しようとしたが、ユーザー方針により Friedman-I のみに対象を絞った
- 2 問題実行時の Poly-10 側では木の deepcopy が深くなり `RecursionError` が出たため、再実行用スクリプトでは `sys.setrecursionlimit(10000)` を設定した

### 2026-06-02 | Seminar 用 bo_current 発表スライド作成

- 何をしたか: Friedman-I の `bo_current` 本実験結果をもとに、Seminar 発表用の PowerPoint を作成した
- なぜそうしたか: 成果発表に向けて、研究背景、提案手法、実験条件、結果、考察、今後の方針を一連の発表資料として説明できるようにするため
- 作成物:
- `slides/seminar_bo_current_friedman.pptx`
- `scripts/build_seminar_bo_current_friedman_deck.py`
- スライド構成:
- 1. タイトル
- 2. 今日のメッセージ
- 3. 研究背景: 固定率 GP の限界
- 4. 提案法 `bo_current` の閉ループ構造
- 5. `bo_current` の数理的整理
- 6. 対象問題: Friedman-I symbolic regression
- 7. 実験条件
- 8. 結果1: final HV と diversity
- 9. 結果2: seed 内差分
- 10. 結果3: HV 分布と外れ値
- 11. 結果4: `k` 選択傾向
- 12. 考察
- 13. 今後の方針
- 発表での主張:
- `bo_current` は標準固定率 GP と高交叉固定率 GP より final HV 平均が高い
- 一方で、高突然変異固定率 GP にはわずかに届かず、最良固定率を安定して上回る段階にはまだ達していない
- Seminar では「閉ループ制御は動作し、標準固定率は上回るが、報酬設計・BO制御器・k の扱いに改善余地がある」と説明する
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/build_seminar_bo_current_friedman_deck.py`
- `.venv/bin/python scripts/build_seminar_bo_current_friedman_deck.py`
- `.venv/bin/python` で PPTX を読み込み、13 枚のスライドと画像4枚の埋め込みを確認した
- `unzip -t slides/seminar_bo_current_friedman.pptx` で PPTX zip 構造にエラーがないことを確認した
- `qlmanage` により macOS Quick Look サムネイル生成を確認した

### 2026-06-03 | warm-up 除外世代定義による Friedman-I bo_current 本実験

- 何をしたか: Friedman-I symbolic regression を対象に、`bo_current` と固定率 GP 3 条件を 100 seed で比較する本実験を実行した
- なぜそうしたか: 今回から「世代数」は BO warm-up を含まない本制御・本評価区間として扱う方針にしたため、現行 `bo_current` の warm-up 18 世代に加えて本評価 60 世代を実行し、BO が初期観測後に制御する区間を十分に確保するため
- 実験条件:
- problem: `sr_alpha_friedman`
- seed: `0..99`
- population size: `24`
- warm-up generations: `18`
- evaluation generations: `60`
- total generations: `78`
- evaluations/run: `1872`
- archive key: `topology_value`
- 比較手法:
- `plain_fixed_standard`: `p_c=0.80`, `p_m=0.05`
- `plain_fixed_high_mutation`: `p_c=0.70`, `p_m=0.20`
- `plain_fixed_high_crossover`: `p_c=0.90`, `p_m=0.05`
- `bogp_current`: `p_c,p_m,k` を文脈付き BO で制御
- 文献に基づく設定理由:
- McDermott et al. (2012) と White et al. (2013) の GP benchmark 設計に関する指摘を踏まえ、単純すぎる toy problem ではなく、線形項・二次項・三角関数・変数間相互作用を含む Friedman-I を採用した
- La Cava et al. (2021) の SRBench の考え方を参考に、symbolic regression を train/test split を持つ benchmark として扱い、精度とモデル複雑さを重視する設定にした
- Liu et al. (2022) の MOGP symbolic regression における低複雑度個体の過剰複製・多様性低下の議論を踏まえ、accuracy--complexity の 2 目的問題として Friedman-I を評価した
- Li and Yao (2019) の多目的解集合評価の整理を踏まえ、archive HV を主指標、多様性を副指標として併用した
- 出力先:
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603`
- 主な結果:
- `plain_fixed_standard`: final archive HV mean `0.782991`, std `0.055371`, diversity mean `0.624480`
- `plain_fixed_high_mutation`: final archive HV mean `0.808315`, std `0.029862`, diversity mean `0.646372`
- `plain_fixed_high_crossover`: final archive HV mean `0.794766`, std `0.029513`, diversity mean `0.630678`
- `bogp_current`: final archive HV mean `0.802461`, std `0.022454`, diversity mean `0.640513`
- warm-up 後指標:
- `bogp_current` の HV gain after warm-up mean: `0.062183`
- `bogp_current` の HV-AUC after warm-up mean: `0.787353`
- seed 内 final HV 差分:
- `bogp_current - plain_fixed_standard`: diff mean `0.019469`, win/tie/loss `70/2/28`, Wilcoxon p `0.0000`
- `bogp_current - plain_fixed_high_mutation`: diff mean `-0.005854`, win/tie/loss `40/1/59`, Wilcoxon p `0.0103`
- `bogp_current - plain_fixed_high_crossover`: diff mean `0.007695`, win/tie/loss `57/1/42`, Wilcoxon p `0.0523`
- `bogp_current - best fixed per seed`: diff mean `-0.014851`, win/tie/loss `31/0/69`, Wilcoxon p `0.0000`
- `bo_current` の制御傾向:
- k selection counts all: `{1: 1702, 3: 816, 5: 730}`
- k selection counts after warm-up: `{1: 1502, 3: 616, 5: 530}`
- mean `p_c` after warm-up: `0.7137`
- mean `p_m` after warm-up: `0.1402`
- 考察:
- `bogp_current` は標準固定率 GP を明確に上回り、高交叉固定率 GP に対しても平均では上回った
- 一方で、高突然変異固定率 GP が final archive HV 平均で最良となり、`bogp_current` は強い固定率 baseline を安定して上回る段階にはまだ達していない
- `bogp_current` は final HV 標準偏差が `0.022454` と比較的小さく、固定率より安定した挙動を示す可能性がある
- k 選択は warm-up 後も `k=1` が多く、Friedman-I では短い更新周期を多く選ぶ傾向が見られた
- したがって、現時点の主張は「閉ループ制御は標準固定率より有効で、安定性も見込めるが、最良固定率を超えるには報酬設計・BO制御器・k 選択の改善が必要」である
- 作成物:
- `scripts/run_main_bo_current_friedman_experiment.py`
- `scripts/summarize_main_bo_current_friedman_results.py`
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/main_bo_current_friedman_summary.md`
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/main_analysis_summary.json`
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/main_final_hv_diversity.png`
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/main_hv_mean_progress.png`
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/main_diversity_mean_progress.png`
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/main_k_selection_counts.png`
- `notes/main_bo_current_friedman_report.tex`
- `notes/main_bo_current_friedman_report.pdf`
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/run_main_bo_current_friedman_experiment.py scripts/summarize_main_bo_current_friedman_results.py`
- `.venv/bin/python scripts/run_main_bo_current_friedman_experiment.py --seed-count 1 --evaluation-generations 2 --run-id smoke_main_bo_current_friedman --output-root /private/tmp/bogp_main_smoke`
- `.venv/bin/python scripts/summarize_main_bo_current_friedman_results.py --output-dir /private/tmp/bogp_main_smoke/sr_alpha_friedman/smoke_main_bo_current_friedman --report-path /private/tmp/bogp_main_smoke/smoke_report.tex`
- `.venv/bin/python scripts/run_main_bo_current_friedman_experiment.py --seed-count 100 --evaluation-generations 60 --run-id main_bo_current_friedman_seed100_eval60_20260603`
- `.venv/bin/python scripts/summarize_main_bo_current_friedman_results.py --output-dir outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603 --report-path notes/main_bo_current_friedman_report.tex`
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/main_bo_current_friedman_report.tex` を 2 回実行し、PDF 生成と図参照の解決を確認した
- `summary_by_seed.csv` が 400 行、各手法 100 seed、最終世代 `78`、評価回数 `1872` で揃っていることを確認した
- 備考:
- `lualatex` は PATH にはなかったが、プロジェクト内の `.TinyTeX/bin/universal-darwin/lualatex` を直接使うことで PDF コンパイルできた

### 2026-06-09 | 図8の Pareto 個体の木構造・ノード値抽出

- 何をしたか: `notes/main_bo_current_friedman_report.pdf` の図8に対応する代表 seed `26` の `bogp_current` について、横軸 `train_nrmse` が `2.5..3.0` に入る Pareto 個体の木構造とノード値を抽出した
- なぜそうしたか: 保存済みの `pareto_archive.json` / `unique_objective_archive.json` には目的関数値のみが保存され、個体木本体が保存されていなかったため、同一 seed・同一設定で決定論的に再実行して archive 個体を復元する必要があった
- 対象:
- experiment: `main_bo_current_friedman_seed100_eval60_20260603`
- method: `bogp_current`
- seed: `26`
- filter: `2.5 <= train_nrmse <= 3.0`
- 結果:
- 該当個体数: `1`
- objective values: `train_nrmse=2.780311079392626`, `tree_size=1.0`
- test NRMSE: `2.745437164096515`
- expression: `1.92726571912`
- tree: `const` ノード1個、`value=1.927265719120086`
- topology value key: `["const", 1.92726572, 0, []]`
- 出力先:
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/extracted_bogp_current_seed26_x2p5_3p0_trees.json`
- 備考:
- 再実行時に scikit-learn の Gaussian Process kernel に関する `ConvergenceWarning` が表示されたが、これはハイパーパラメータ最適化の境界警告であり、処理自体は正常終了した
- 今後は archive 保存時に `expression`, `tree`, `topology_value_key`, `test_nrmse` も同時保存するようにすると、再実行なしで Pareto 解の中身を確認できる

### 2026-06-09 | 図8の縦軸最大解の木構造図を作成

- 何をしたか: 図8に対応する代表 seed `26` の `bogp_current` Pareto front について、縦軸最大、すなわち `tree_size=32` の解の木構造を PNG 図として描画した
- なぜそうしたか: Pareto front 上の点がどのようなプログラム木・定数値・変数参照を持つかを視覚的に確認し、精度と複雑さのトレードオフを解の中身から説明できるようにするため
- 入力:
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/extracted_bogp_current_seed26_max_tree_size_solution.json`
- 出力:
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/bogp_current_seed26_max_tree_size_solution_tree.png`
- 作成物:
- `scripts/plot_extracted_solution_tree.py`
- 図の読み方:
- 青系ノードは演算子ノード、緑系ノードは変数ノード、橙系ノードは定数ノードを表す
- 変数ノードは `x1` から `x5` と表示した
- 定数ノードには小数値を表示した
- 確認方法:
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/plot_extracted_solution_tree.py`
- `.venv/bin/python scripts/plot_extracted_solution_tree.py --input outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/extracted_bogp_current_seed26_max_tree_size_solution.json --output outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/bogp_current_seed26_max_tree_size_solution_tree.png`
- `view_image` で図が生成され、式木として読めることを確認した

### 2026-06-07 | NSGA-II レビュー論文 [R20] の正式採用

- 何をしたか: 添付された Verma, Pant, Snasel (2021) の NSGA-II レビュー論文を、文献仕様書に従って正式参考文献 [R20] として採用した
- なぜそうしたか: 論文構成案で予定している [5] の NSGA-II 根拠文献について、既存の Deb et al. (2002) [R09] はメタデータ確認のみであったため、NSGA-II の概要、応用範囲、評価方法を説明できる本文確認済みの補強文献が必要だった
- 確認したこと:
- 添付 PDF のメタデータから IEEE Access, volume 9, pages 57757-57791, DOI `10.1109/ACCESS.2021.3070634` を確認した
- CiNii Research と VSB 機関リポジトリで、著者、掲載誌、DOI、ページ範囲、PDF 入手可能性を確認した
- この論文は NSGA-II の総説であり、conventional / modified / hybrid NSGA-II、性能指標、統計検定、case study、benchmarking などを説明する補強文献として有用である
- 採用判断:
- [R20] は正式採用する
- 今回の論文案では、予定していた [5] の枠に [R20] を用いる
- ただし、NSGA-II の原典・正確なアルゴリズム定義を述べる箇所では Deb et al. (2002) [R09] も併用する
- [R20] は「NSGA-II が広く使われていること」「応用・変種・評価方法を整理すること」の根拠として使う
- 作成物:
- `references/A Comprehensive Review on NSGA-II for Multi-Objective Combinatorial Optimization Problems.pdf`
- `references/A Comprehensive Review on NSGA-II for Multi-Objective Combinatorial Optimization Problems.md`
- `references/README.md` の [R20] 追記
- `notes/research_note.md` の参考文献章と作業ログ追記

### 2026-06-08 | EI / EGO 文献 [R13] の本文確認

- 何をしたか: 添付された `A_1008306431147.pdf` を読み込み、Jones, Schonlau, Welch (1998) の *Efficient Global Optimization of Expensive Black-Box Functions* と一致することを確認した
- なぜそうしたか: 論文構成案で予定している [7] は、提案手法の BO 制御器で用いる Expected Improvement (EI) の中核根拠であるため、本文確認済み文献として使えるかを確認する必要があった
- 確認したこと:
- PDF のタイトルが *Efficient Global Optimization of Expensive Black-Box Functions* であることを確認した
- 本文中に expected improvement、EI の閉形式、EGO algorithm、space-filling / Latin hypercube design による初期設計点生成の記述があることを確認した
- 本研究の BO 制御器において、GP surrogate のもとで EI を最大化して次の制御入力を選ぶ説明の根拠として使える
- 採用判断:
- [R13] は当初予定通り、EI / EGO の正式な根拠文献として使える
- 特に、BO 制御器の獲得関数を EI に固定する理由、warm-up 後に surrogate と EI で逐次的に行動を選ぶ説明、初期設計点を space-filling design として与える説明に使う
- 作成物:
- `references/Efficient Global Optimization of Expensive Black-Box Functions.pdf`
- `references/Efficient Global Optimization of Expensive Black-Box Functions.md` の本文確認済み更新
- `references/README.md` の [R13] 本文確認状況更新
- `notes/research_note.md` の参考文献章と作業ログ追記

### 2026-06-08 | 離散・整数変数 BO 文献 [R14] の本文確認

- 何をしたか: 添付された `1-s2.0-S0925231219315619-main.pdf` を読み込み、Garrido-Merchan and Hernandez-Lobato (2020) の *Dealing with categorical and integer-valued variables in Bayesian Optimization with Gaussian processes* と一致することを確認した
- なぜそうしたか: 論文構成案で予定している [8] は、提案手法で更新周期 `k` を連続変数ではなく離散候補として扱う理由の根拠文献であるため、本文確認済みで使えるかを確認する必要があった
- 確認したこと:
- PDF のタイトル、掲載誌 Neurocomputing, volume 380, pages 20-35, DOI `10.1016/j.neucom.2019.11.004` を確認した
- 本文中に、GP ベース BO は基本的に実数値入力を仮定すること、整数値変数の単純丸めやカテゴリ変数の one-hot encoding が問題を生みうること、離散値の性質を covariance / kernel 側に反映する必要があることが述べられている
- 本研究の `k` は整数・離散的な更新周期であるため、`k` を単純な連続特徴として 1 本の GP surrogate に押し込まない設計判断の根拠として使える
- 採用判断:
- [R14] は当初予定通り、離散・整数変数を含む BO の正式な根拠文献として使える
- ただし、本研究の `k` ごとの surrogate 設計はこの論文の提案する変換そのものではないため、本文では「離散変数を連続変数と同様に扱うことへの注意」および「将来的には離散変数向け kernel 設計を検討できる」という根拠として使う
- 作成物:
- `references/Dealing with categorical and integer-valued variables in Bayesian Optimization with Gaussian processes.pdf`
- `references/Dealing with categorical and integer-valued variables in Bayesian Optimization with Gaussian processes.md` の本文確認済み更新
- `references/README.md` の [R14] 本文確認状況更新
- `notes/research_note.md` の参考文献章と作業ログ追記

### 2026-06-08 | 8ページ2段組論文構成案の LaTeX 化

- 何をしたか: Friedman-I 本実験結果と補強済み文献精査の結果を踏まえ、8ページ上限・2段組を想定した論文構成案を LaTeX 形式で作成した
- なぜそうしたか: 成果発表および論文執筆へ移る前に、章立て、ページ配分、引用番号、図表配置、主張の強弱を固定し、本文執筆時に迷わない土台を作るため
- 作成した内容:
- Abstract, Introduction, Related Work, Proposed Method, Experimental Setup, Results, Discussion, Conclusion の章構成
- 2段組でのページ配分案
- 提案法の中心主張、数理定義、報酬式、非文脈 BO との差分
- Friedman-I 本実験の主要結果表と、本文に入れる優先図表の配置案
- 参考文献番号 [1]--[11] と本文中での参照用途の対応表
- 結果の主張は、「標準固定率 GP に対する改善」と「安定性の可能性」を中心とし、高突然変異固定率 GP が平均 final HV で最良だった点を隠さず Discussion に回す方針で整理した
- 参照した主な文献:
- [PS01] McDermott et al. (2012): GP benchmark 選定の問題意識
- [PS02] White et al. (2013): GP benchmark の実験厳密性
- [PS03] La Cava et al. (2021): symbolic regression benchmark
- [PS04] Liu et al. (2022): MOGP symbolic regression における多様性・低複雑度個体の問題
- [R20] Verma et al. (2021): NSGA-II の概要
- [R12] Krause and Ong (2011): 文脈付き BO
- [R13] Jones et al. (1998): EI / EGO
- [R14] Garrido-Merchan and Hernandez-Lobato (2020): 離散・整数変数 BO
- [R16] Li and Yao (2019): 多目的解集合評価
- [R17] Guerreiro et al. (2021): Hypervolume indicator
- [R01] Burlacu et al. (2024): GP symbolic regression における多様性
- 作成物:
- `notes/paper_8page_2col_structure_plan.tex`

### 2026-06-08 | 8ページ上限・2段組の論文本体ドラフト作成

- 何をしたか: `notes/paper_8page_2col_structure_plan.tex` をもとに、構成案ではなく本文として読める 2段組論文ドラフトを新規作成した
- なぜそうしたか: 今回の Friedman-I 本実験結果を、成果発表後の論文化に向けて、Abstract、Introduction、Related Work、Proposed Method、Experimental Setup、Results、Discussion、Conclusion、References を備えた論文形式に落とし込むため
- 論文の主張:
- 多目的 GP の操作率設定を固定ハイパーパラメータ調整ではなく、世代状態を観測して制御入力を逐次決める閉ループ制御問題として定式化する
- 交叉率 `p_c`、突然変異率 `p_m` に加えて、次回制御更新までの世代数 `k` を制御対象に含める
- Friedman-I symbolic regression の accuracy--complexity 2目的実験において、`bo_current` は標準固定率 GP を上回るが、高突然変異固定率 GP を平均 final HV で上回るには至っていないため、現行 BO 制御器には改善余地がある
- 反映した主要結果:
- `bo_current` final HV mean: `0.802461`, std: `0.022454`
- `plain_fixed_standard` final HV mean: `0.782991`, std: `0.055371`
- `plain_fixed_high_mutation` final HV mean: `0.808315`, std: `0.029862`
- `plain_fixed_high_crossover` final HV mean: `0.794766`, std: `0.029513`
- `bo_current` は standard に対して seed 内差分平均 `+0.019469`、high mutation に対して `-0.005854`
- `k` 選択は warm-up 後で `k=1:1502`, `k=3:616`, `k=5:530`
- 参照文献:
- [PS01] McDermott et al. (2012), [PS02] White et al. (2013), [PS03] La Cava et al. (2021), [PS04] Liu et al. (2022)
- [R20] Verma et al. (2021), [R16] Li and Yao (2019), [R17] Guerreiro et al. (2021), [R01] Burlacu et al. (2024)
- [R13] Jones et al. (1998), [R12] Krause and Ong (2011), [R14] Garrido-Merchan and Hernandez-Lobato (2020)
- 作成物:
- `notes/paper_8page_2col_draft.tex`
- `notes/paper_8page_2col_draft.pdf`
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft.tex` を実行し PDF 生成を確認した
- 2回目のコンパイル後、未定義参照、LaTeX warning、overfull warning が出ていないことを `rg` で確認した
- 生成 PDF は LaTeX ログ上で 5 pages であり、8ページ上限を満たしている

### 2026-06-08 | 8ページ上限・2段組論文の補強版作成

- 何をしたか: 既存の `notes/paper_8page_2col_draft.tex` は残したまま、参考文献を除いて本文6ページ以上となる補強版 `notes/paper_8page_2col_draft_expanded.tex` を新規作成した
- なぜそうしたか: 既存ドラフトは全体5ページであり、本文量が不足していたため、成果発表・論文化に向けて提案手法、実験設定、結果解釈を自然に補強する必要があった
- ユーザー指定に基づく反映:
- archive 更新式は記載しない方針とした
- 結果章に代表 seed=26 の Pareto front 図を追加した
- Pareto front 図の読み方、HV との違い、低複雑度領域・高精度領域・front の広がりに基づく比較と考察を追加した
- 追加した主な内容:
- 提案手法章に archive と population の役割分担を文章で追加
- 制御方策の差分表を追加し、固定率 GP、手設計、非文脈 BO、提案法の違いを整理
- Algorithm 1 として、文脈付き BO 制御型 MOGP の処理流れを追加
- 実験設定章に Friedman-I の問題選定理由、accuracy--complexity 2目的設定の意味、固定率 baseline の位置づけを補強
- 結果章に `main_representative_pareto_front.png` を掲載し、Pareto front 形状からの比較を追加
- 考察章に、HV だけでなく Pareto front の領域別評価が今後必要であることを追加
- 作成物:
- `notes/paper_8page_2col_draft_expanded.tex`
- `notes/paper_8page_2col_draft_expanded.pdf`
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を 2 回実行し、PDF 生成と参照解決を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (7 pages, 802917 bytes).` を確認した
- `\clearpage` 後に参考文献を開始しており、本文は 1--6 ページ、参考文献は 7 ページ目から開始するため、参考文献を除いて6ページ以上、全体8ページ以内を満たす
- `rg` によるログ確認で、最終ログに未定義参照、LaTeX warning、overfull warning が出ていないことを確認した

### 2026-06-08 | 論文補強版の英語専門語表記を日本語へ統一

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の本文中に残っていた英語専門語を日本語表記へ修正した
- なぜそうしたか: 本文の読みやすさを高め、`symbolic regression` や `crowding distance` などの語を日本語論文として自然な表記に統一するため
- 主な修正:
- `symbolic regression` を `シンボリック回帰` に変更
- `crowding distance` を `混雑距離` に変更
- `Pareto front` を `パレートフロント` に変更
- `Pareto archive` / `archive` を文脈に応じて `パレートアーカイブ` / `アーカイブ` に変更
- `population` を `集団` に変更
- `baseline` を `ベースライン` に変更
- `warm-up` を `ウォームアップ` に変更
- `seed` を `乱数シード` に変更
- `final archive HV` を `最終アーカイブHV` に変更
- `tree size` を `木サイズ` に変更
- `black-box` / `surrogate model` を `ブラックボックス` / `代理モデル` に変更
- `Expected Improvement` は本文では `期待改善量（EI）` に変更
- 備考:
- `GP`, `BO`, `HV`, `EI`, `NSGA-II`, `Friedman-I`, `NRMSE`, `bo_current` は略称・問題名・コード上の条件名として残した
- 参考文献の英語タイトルは正式タイトルであるため変更しなかった
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を実行し、PDF 更新を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (7 pages, 803889 bytes).` を確認した
- `rg` によるログ確認で、最終ログに未定義参照、LaTeX warning、overfull warning が出ていないことを確認した

### 2026-06-08 | 論文補強版「はじめに」の目的文接続と構成修正

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の第1章「はじめに」を修正し，固定率の限界，動的調整の必要性，本研究の目的，提案手法，検証問題，本稿の構成が順に読めるように再構成した
- なぜそうしたか: これまでの導入では，ベンチマーク文献の説明が固定率の問題を述べる段落に入っており，提案手法の仕組みに直接つながる主線がやや散っていたため
- 主な修正:
- 固定率を用いる方法の利点と限界を分けて説明した
- 探索初期・中盤・終盤で望ましい操作が異なるため，固定された交叉率・突然変異率では探索状態へ十分に適応できない可能性がある，という説明を追加した
- 「そこで本研究の目的は，交叉率・突然変異率を探索状態に応じて動的に調整することで，多目的GPにおける収束性と多様性の改善を図ることである．」という目的文を，提案手法説明の直前に追加した
- ベンチマーク文献の説明を固定率の問題段落から外し，Friedman-Iシンボリック回帰を初期検証問題として用いる理由の段落へ移した
- 「本稿の構成」段落を追加し，第2章から第6章までの役割を明記した
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を 2 回実行し，PDF 生成と参照解決を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 807134 bytes).` を確認した
- `rg` によるログ確認で，最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-06-09 | 論文補強版へのアーカイブ説明追加

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` に，アーカイブおよびアーカイブキーの簡潔な説明を追加した
- なぜそうしたか: 本文中で `アーカイブHV` や `パレートアーカイブ` が使われていたが，初出時点でアーカイブの意味が明示されておらず，読者が現在集団との違いを理解しにくい可能性があったため
- 追加した内容:
- 第3章 `状態，行動，報酬` に，アーカイブを「探索過程で得られた非劣解を保存する外部集合」として定義した
- 現在集団は世代交代で入れ替わる一方，アーカイブは過去に得られた良好な解を保持し，最終的なパレートフロント近似およびHV評価に用いることを説明した
- 第4章の実験設定表の直後に，アーカイブキーがアーカイブ内で同一解とみなすための識別基準であり，本実験では木のトポロジーとノード値の組を用いることを追記した
- 注意:
- 以前の方針どおり，本文にはアーカイブの具体的な更新式は記載していない
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を 2 回実行し，PDF 生成と参照解決を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 818926 bytes).` を確認した
- `rg` によるログ確認で，最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-06-08 | 「はじめに」の固定率・動的操作率主張を補強する文献調査

- 何をしたか: 第1章「はじめに」における，GPと操作率の重要性，固定率では不十分な理由，操作率を動的に変える必要性を補強する文献を調査し，文献取得仕様書に従って `references/` へ保存・採番した
- なぜそうしたか: 現行の導入では主張の流れは整理されたが，「固定率ではなく動的制御が必要である」という根拠文献が不足していたため
- 検索観点:
- `genetic programming crossover rate mutation rate adaptive`
- `genetic programming operator probability adaptive`
- `parameter control in evolutionary algorithms`
- `adaptive parameter control evolutionary algorithms`
- 採用・候補文献:
- [R21] Eiben et al. (1999): EA の parameter tuning と parameter control の古典的区別，deterministic / adaptive / self-adaptive control の分類
- [R22] Karafotias et al. (2015): parameter control の近年動向と課題，探索段階に応じた値変更の一般的根拠
- [R23] Aleti and Moser (2016): adaptive parameter control の体系的レビュー，mutation rate / crossover rate などが問題・探索段階依存であること
- [R24] Niehaus and Banzhaf (2001): GP における operator probability adaptation の直接先行研究
- [R25] Oh et al. (2021): GP の交叉・突然変異確率を木構造複雑さに応じて自己適応させる近年の実例
- 保存状況:
- PDF 保存済み: [R21], [R22], [R23], [R24], [R25]
- メタデータノート / 手動取得候補: なし
- 反映:
- `references/README.md` の文献番号台帳に [R21]--[R25] を追加した
- `notes/research_note.md` の参考文献章に [R21]--[R25] の用途を追加した
- 今回は論文本体 `notes/paper_8page_2col_draft_expanded.tex` にはまだ引用番号を反映していない
- 次の候補:
- 論文本体の「はじめに」に [R21]--[R25] の引用を追加し，固定率の限界と動的操作率の必要性を文献つきで補強する
- [R24] は，GP 固有の操作率適応の直接先行研究として本文中で具体的に使える

### 2026-06-08 | [R22] Karafotias et al. (2015) の本文確認

- 何をしたか: ユーザーが添付した `parameter-control-in-evolutionary-algorithms-trends-and-24a9inzajy.pdf` を読み込み，[R22] Karafotias, Hoogendoorn, Eiben (2015) の本文を確認した
- なぜそうしたか: 第1章「はじめに」における，固定率では不十分であり探索状態に応じて操作率を動的に調整する必要がある，という主張を補強する文献として本当に使えるか確認するため
- 保存:
- `references/Parameter Control in Evolutionary Algorithms - Trends and Challenges.pdf` として保存した
- `references/Parameter Control in Evolutionary Algorithms - Trends and Challenges.md` の status を `Adopted`，access を `PDF saved / full text checked` に更新した
- 本文確認で重要だった内容:
- EA の性能はパラメータ値に大きく依存し，よい値を選ぶ問題は parameter tuning problem として整理される
- 一方，最適に近いパラメータ値は実行中に変わり得るため，実行中に値を変える parameter control problem がある
- parameter control の利点として，探索段階ごとに適切な値を使えること，動的問題へ適応できること，探索中の情報を蓄積して後半の性能改善に使えることが説明されている
- variation operator 関連のパラメータ，特に mutation rate と crossover rate の制御は，EA parameter control 文献で最も多く扱われる対象の一つと整理されている
- feedback として fitness，diversity，exploration / exploitation などの探索状態記述子を用いることが重要であると述べられている
- 提案手法への使い方:
- 「固定された交叉率・突然変異率では探索段階の変化に適応しにくい」という導入主張の根拠として使える
- 「本研究は parameter tuning ではなく，探索状態を見て実行中に操作率を変える parameter control として位置づけられる」という説明に使える
- 「多様性や直近改善量などの状態変数を文脈ベクトルに入れる」設計の背景として使える
- 注意点:
- 本文献は EA 全般の survey であり，GP 専用文献ではないため，GP における具体例は [R24] や [R25] と併用する
- 文献自体も，parameter control 研究には実験方法・比較設計・ベンチマークの弱さがあると指摘しているため，本研究でも固定率，調整済み固定率，制御履歴の可視化などを丁寧に示す必要がある

### 2026-06-08 | [R23] Aleti and Moser (2016) の本文確認

- 何をしたか: ユーザーが添付した `2996355.pdf` を読み込み，[R23] Aleti and Moser (2016) の本文を確認した
- なぜそうしたか: 第1章「はじめに」における，交叉率・突然変異率などのパラメータが問題依存・探索段階依存であり，フィードバックに基づく動的調整が必要になる，という主張を補強する文献として本当に使えるか確認するため
- 保存:
- `references/A systematic literature review of adaptive parameter control methods for evolutionary algorithms.pdf` として保存した
- `references/A systematic literature review of adaptive parameter control methods for evolutionary algorithms.md` の status を `Adopted`，access を `PDF saved / full text checked` に更新した
- 本文確認で重要だった内容:
- EA の頑健性は mutation rate，crossover rate，population size などの調整可能パラメータに影響され，これらは問題だけでなく問題インスタンスにも依存し得る
- 異なるパラメータ値が探索過程の異なる段階で最適になり得るため，固定率は探索・活用のバランスの観点で不十分になり得る
- adaptive parameter control は，探索中のアルゴリズム性能や状態からフィードバックを集め，次の反復で使うパラメータ値を調整する枠組みである
- 152本の論文を対象とした体系的レビューであり，mutation rate，crossover rate，population size が探索中に制御される代表的なパラメータとして整理されている
- 概念モデルとして，feedback collection，effect assessment，quality attribution，parameter update の4段階を提示している
- 検証方法として，静的パラメータ設定との比較，複数試行の平均，評価回数の公平化，統計検定，制御器の挙動分析が重要であると整理されている
- 提案手法への使い方:
- 「固定率では探索段階の変化に適応しにくい」という導入主張の根拠として使える
- 「文脈ベクトルで HV，改善量，多様性，木サイズ，停滞などを観測し，BO が次の操作率を決める」設計を，feedback-based adaptive parameter control の一種として位置づける根拠になる
- 「交叉率・突然変異率を制御対象にする妥当性」を，既存研究で mutation rate / crossover rate が代表的な調整対象であることから補強できる
- 「比較実験では固定率ベースライン，評価回数の公平化，複数乱数シード，制御履歴分析が必要」という実験設計の根拠として使える
- 注意点:
- 本文献は EA 全般の systematic literature review であり GP 専用ではないため，GP 固有の操作率適応の根拠には [R24] や [R25] を併用する
- 文献の対象は adaptive parameter control であり，BO を用いた制御そのものの根拠ではないため，BO 部分には [R12]--[R14] を併用する

### 2026-06-08 | [R24] Niehaus and Banzhaf (2001) の本文確認

- 何をしたか: ユーザーが添付した `3-540-45355-5.pdf` の pp.325-336 を読み込み，[R24] Niehaus and Banzhaf (2001) の本文を確認した
- なぜそうしたか: 第1章「はじめに」における，GP では操作率が自由パラメータになりやすく，固定値に依存しない適応的な操作率決定が有効になり得る，という主張を GP 固有の文献で補強するため
- 保存:
- `references/Adaption of Operator Probabilities in Genetic Programming.pdf` として保存した
- `references/Adaption of Operator Probabilities in Genetic Programming.md` の status を `Adopted`，access を `PDF saved / target pages checked` に更新した
- 本文確認で重要だった内容:
- GP には多くの自由パラメータがあり，問題ごとに異なるパラメータ集合を要求するため，ユーザー側の経験や事前のパラメータ調査に依存しやすいと説明されている
- 研究目的として，解の品質を落とさずに GP の自由パラメータ数を減らすこと，経験的に選んだ静的設定に近い性能を得ること，ランダムな静的設定より良い結果を得ることが掲げられている
- mutation operator の適用確率を，Population-level Dynamic Probabilities，Fitness Based Dynamic Probabilities，Individual-level Dynamic Probabilities の3方式で実行中に適応させている
- symbolic regression と classification の2問題で実験し，適応的手法はランダム静的設定より平均的に良く，symbolic regression では経験的静的設定と競合または上回る場合があると報告されている
- 提案手法への使い方:
- 「GP の操作率は固定値として与えられることが多いが，実行中に適応させる研究が既に存在する」という GP 固有の直接根拠として使える
- 「固定率の置き換え」ではなく「探索中の観測に基づく閉ループ制御」として本研究を位置づける際，先行研究との差分を説明する土台になる
- 本研究との差分として，[R24] は演算子の成功履歴に基づく適応であり，本研究は HV，改善量，多様性，木サイズ，停滞長を含む状態ベクトルを用いて BO が `p_c,p_m,k` を選ぶ点を強調できる
- 注意点:
- 本文献は単目的 GP の operator probability adaptation であり，多目的 GP，HV，Pareto front，BO，更新周期 `k` は扱っていない
- 実験は古い GP システム GGP と2つの問題に基づくため，本研究の方法論そのものの根拠ではなく，「GP 操作率適応の直接先行研究」として引用するのが適切である

### 2026-06-09 | 「はじめに」への文献番号つき補強反映

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の第1章「はじめに」を，参考文献 [1]--[5] に基づいて補強した
- なぜそうしたか: GP と操作率の重要性，固定率では不十分な理由，操作率を動的に変える必要性を，本文確認済みの先行研究に基づく主張として明確にするため
- 反映した参考文献番号:
- [1] Niehaus and Banzhaf (2001): GP における演算子確率適応の直接先行研究
- [2] Oh et al. (2021): GP の交叉率・突然変異率を木構造複雑さに応じて自己適応させる研究
- [3] Eiben et al. (1999): parameter tuning と parameter control の古典的区別
- [4] Karafotias et al. (2015): EA parameter control の動向と探索段階に応じた値変更の根拠
- [5] Aleti and Moser (2016): adaptive parameter control の体系的レビュー，mutation rate / crossover rate が代表的制御対象である根拠
- 主な修正:
- GP には多くの自由パラメータがあり，問題ごとに適切な設定が異なるため，事前調整に経験や試行錯誤が必要になるという説明を追加した
- 固定率を parameter tuning，実行中の値変更を parameter control として整理し，固定率の限界を先行研究ベースで補強した
- GP 固有の先行研究として，演算子確率適応と交叉率・突然変異率の自己適応を説明し，本研究の閉ループ制御への接続を強化した
- 参考文献欄の先頭に [1]--[5] の文献を追加し，本文中の直接番号と対応するようにした

### 2026-06-09 | 論文中の `bo_current` 表示名の修正

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の本文，表，図キャプションに残っていた `bo_current` 表記を，読者向けの「提案手法」に修正した
- なぜそうしたか: `bo_current` は実装・実験管理上の内部条件名であり，論文本文では手法名として不自然なため
- 図対応:
- 既存の実験出力図は残したまま，論文用のラベル修正版を `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/paper_labelled_figures/` に生成した
- 図中の `BO-controlled GP (bo_current)` は `Proposed method` に置き換えた
- LaTeX 側の `\includegraphics` は，ラベル修正版の図を参照するよう変更した
- 注意:
- ファイルパスや実験出力ディレクトリ名に含まれる `bo_current` は，実験管理用の識別子として残した

### 2026-06-09 | 「はじめに」の英語用語の日本語化

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の第1章「はじめに」に残っていた `parameter tuning`，`parameter control`，`adaptive parameter control` を日本語表現に修正した
- なぜそうしたか: 本文全体の用語を日本語中心に統一し，読者が概念の違いを自然に読めるようにするため
- 修正方針:
- `parameter tuning` は，実行前に値を決める意味を明確にするため「事前パラメータ調整」とした
- `parameter control` は，探索中に値を変える意味として「パラメータ制御」とした
- `adaptive parameter control` は「適応的パラメータ制御」とした

### 2026-06-09 | Friedman-I / Friedman #1 理解用文献の追加調査

- 何をしたか: Friedman-I 型シンボリック回帰問題の理解を深めるため，文献取得ルールに従って原典・標準 ML benchmark・GP/SR 文脈の文献を調査した
- なぜそうしたか: 現在の論文では Friedman-I を本実験対象としているが，Friedman 系問題には文献ごとの呼称ゆれがあり，式を明示せずに名称だけで説明すると誤解が生じる可能性があるため
- 採用した文献:
- [R26] Friedman (1991) *Multivariate Adaptive Regression Splines*: Friedman 系合成回帰問題の原典として採用した
- [R27] Breiman (1996) *Bagging Predictors*: Friedman #1 が古典的 ML benchmark として使われていることの補助文献として採用した
- 既存 [R01] Burlacu et al. (2024): GP/SR 文脈で Friedman 系問題を使う例，および呼称ゆれの確認に使う
- 重要な確認:
- scikit-learn の `make_friedman1` では，本研究で使っている
- \(y=10\sin(\pi x_1x_2)+20(x_3-0.5)^2+10x_4+5x_5\)
- を `Friedman #1` と呼んでいる
- 一方で，Burlacu et al. (2024) では同じ sine-interaction 型の式を `Friedman-II` と呼び，additive 型の別式を `Friedman-I` と呼んでいる
- したがって，論文本文では `Friedman-I` という名称だけに依存せず，必ず式を明示する必要がある
- 作成物:
- `references/Multivariate Adaptive Regression Splines.pdf`
- `references/Multivariate Adaptive Regression Splines.md`
- `references/Bagging Predictors.pdf`
- `references/Bagging Predictors.md`
- `reference_candidates/problem_settings/friedman_i_explanation_sources.md`
- `references/README.md` の [R26], [R27] 追記
- `notes/research_note.md` の参考文献章と作業ログ追記
- 今後の推奨:
- 論文本文では「Friedman-I」だけでなく「Friedman #1 型」または「make_friedman1 型」と式を併記する
- 実験設定表では，現在の実装が 5 変数版なのか，10 変数版で無関係変数を含むのかを明記する
- 必要であれば，本実験の再現性を高めるために 10 変数版，つまり 5 relevant + 5 irrelevant variables に切り替えるかを検討する

### 2026-06-09 | Seminar レジュメ論文への Friedman 系問題の位置づけ反映

- 何をしたか: `notes/paper_8page_2col_draft.tex` と `notes/paper_8page_2col_draft_expanded.tex` に，Friedman 系問題の真の式と Pareto 解評価の関係を追記した
- なぜそうしたか: 本実験 forSeminar2 では，提案手法が多目的 GP としてどの程度良い Pareto front を得られるかを検証するため，真の式構造の完全復元と Pareto 最適性を混同しない説明が必要になったため
- 反映した内容:
- 本研究で用いる式は機械学習分野では Friedman #1 型として扱われる一方，Burlacu et al. では Friedman-II と呼ばれる場合があるため，本文では名称だけでなく式で対象問題を定義することを明記した
- 真の式はデータ生成と結果解釈の基準であり，GP に真の式構造を探索制約として与えるものではないことを明記した
- 真の式と異なる構造の式でも，NRMSE と tree size の2目的空間で非劣なら Pareto archive に記録されることを説明した
- 提案手法の主評価は，真の式の完全復元ではなく，固定率 GP と比較した final archive HV，Pareto front 改善，多様性維持に基づくと整理した
- 真の構造に固定して係数だけを最適化する設定は，構造探索ではなく既知モデル形のパラメータ推定問題になるため，主検証ではなく oracle baseline / sanity check として扱うのが妥当であると記述した
- 注意:
- LaTeX コンパイル確認は，この環境に `lualatex` が無かったため未実施である

### 2026-06-09 | 論文補強版の Friedman-II 表記と評価位置づけの整理

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` において，対象問題の主呼称を `Friedman-II` に統一し，第4章 `対象問題` の説明を整理した
- なぜそうしたか: 本実験では，真の関数が既知なシンボリック回帰ベンチマークとして Friedman-II を用いていること，ただし評価目的は真の式の完全復元ではなく，固定率GPと比較した Pareto front 改善と多様性維持であることを明確にするため
- 反映した内容:
- 第4章の冒頭を「本実験では，Friedman-IIを真の関数が既知なシンボリック回帰ベンチマークとして用いる」と書き換えた
- Friedman \#1 型 / `make_friedman1` 型 / Friedman-II という呼称ゆれを残しつつ，対象問題を名称だけでなく式で定義する方針を明記した
- 真の関数が既知であることは，GPに真の式構造を事前知識として与えることではないと説明した
- 提案手法の有効性は，真の式の完全復元ではなく，固定率GPと比較した誤差と式複雑さのパレートフロント改善，および探索中の多様性維持によって評価すると明記した
- 第6章の今後の課題に，最終アーカイブ中の式が \(x_1x_2\)，\(\sin\)，\(x_3\) の二次項，\(x_4,x_5\) などの真の式の構成要素を含むかを調べ，目的関数値だけでは分からない式構造の獲得傾向を分析する方針を追加した
- 表記整理:
- 本文中の `Friedman-I` 表記を `Friedman-II` に統一した
- `building block` を `構成要素` に変更した
- `Pareto archive` を `パレートアーカイブ` に変更した
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を 2 回実行し，PDF 生成と参照解決を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 819388 bytes).` を確認した
- `rg` によるログ確認で，最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-06-09 | 12分発表用スライド構成案の作成

- 何をしたか: `notes/presentation_12min_20slides_structure.md` を新規作成し，論文内容をもとに12分発表・20枚上限のスライド構成案を整理した
- なぜそうしたか: 論文内容をすべて伝えるのではなく，固定率GPの限界，提案法の閉ループ制御，Friedman-IIでの初期検証結果，今後の改善方針に絞って発表する必要があるため
- 反映した方針:
- スライド枚数は20枚上限とし，1枚あたりの主張を小さく分けた
- 元案の時間配分は合計12分を超えていたため，内容は維持したまま合計12分00秒になるように再配分した
- `今後の構成要素分析` は必須枠から外し，最終スライドでは `BO制御器の改善`，`比較実験の追加`，`評価指標の拡張`，`対象問題の拡張` を今後やることとして整理した
- 添付PDFの表紙デザインを参考に，白余白，大きな中央タイトル，図中心，大きめ文字の方針を記載した
- 作成物:
- `notes/presentation_12min_20slides_structure.md`

### 2026-06-09 | 12分発表用スライドデザイン案のPPTX化

- 何をしたか: `notes/presentation_12min_20slides_structure.md` をもとに，20枚構成の発表スライド案を `slides/BOGP_12min_presentation.pptx` として作成した
- なぜそうしたか: 小発表に向けて，論文内容をそのまま詰め込むのではなく，固定率GPの問題，提案法の閉ループ制御，Friedman-IIでの初期検証結果，今後やることを12分で説明できる形にするため
- デザイン方針:
- 添付PDF `SICE2025_myojin_final.pdf` の表紙を参考に，白い余白，暗色の中央フレーム，大きな白文字タイトル，図中心，大きめ文字の方向に寄せた
- 通常スライドは白背景に太い見出し，淡い色のカード，中央の模式図または実験図を大きく配置する形式にした
- 色は暗灰，金，青，緑，橙を基調にし，提案法・評価・結果の区分が視覚的に分かるようにした
- 反映した内容:
- 1〜6枚目で研究背景，固定率GPの限界，多目的GPにおける収束性と多様性の両立，研究目的を説明する構成にした
- 7〜11枚目でGPをプラント，BOを制御器とする閉ループ，制御入力 \(p_c,p_m,k\)，状態ベクトル，報酬，アルゴリズムを図中心で説明する構成にした
- 12〜14枚目でFriedman-IIの対象問題，評価方針，比較条件をまとめた
- 15〜19枚目で本実験の最終HV・多様性，ばらつき，世代推移，Pareto front，更新周期 \(k\) の結果図を配置した
- 20枚目でBO制御器の改善，比較実験の追加，評価指標の拡張，対象問題の拡張を今後やることとして整理した
- 技術的補足:
- 通常の presentation artifact tool は macOS の `skia.node` コード署名エラーで使用できなかったため，Python標準ライブラリでPowerPointのOOXMLを直接生成する代替手段を用いた
- 生成用スクリプトは `scripts/build_bogp_12min_presentation.py` として保存した
- 検証:
- `unzip -t slides/BOGP_12min_presentation.pptx` によりPowerPointパッケージの展開検査を実施し，エラーがないことを確認した
- `unzip -l` により20枚のスライドXMLと4つの実験図画像が含まれることを確認した
- `qlmanage` で先頭スライドのサムネイルを生成し，表紙レイアウトに大きな崩れがないことを確認した

### 2026-06-10 | 12分発表用スライド dense 版の作成

- 何をしたか: 前回作成した20枚構成のスライド案をもとに，1枚あたりの情報量を増やした16枚構成の dense 版 `slides/BOGP_12min_presentation_dense.pptx` を作成した
- なぜそうしたか: 前回版は1枚1主張で余白が多く，発表時にもう少し各スライドへ背景・根拠・読み方を同居させてもよいと判断したため
- デザイン方針:
- 20枚を細かく送る構成から，16枚で「主張」「根拠図・式」「読み方」を同じスライド内に置く構成へ変更した
- 背景と固定率GPの課題，多目的GPの評価軸，研究目的と新規性をそれぞれ統合し，導入部の密度を上げた
- 提案手法の説明では，閉ループ全体図，状態・行動・報酬，BO制御器，アルゴリズム・アーカイブを4枚に整理した
- 実験結果では，最終HV・多様性の図に主要数値を併記し，HV推移スライドには標準偏差の比較も同居させた
- 反映した内容:
- `BO current` の最終HV `0.802 ± 0.022`，多様性 `0.641 ± 0.087` を結果スライドに明記した
- 標準固定率，高突然変異，高交叉の比較値も載せ，提案法が標準固定率より良い一方，高突然変異固定率を平均HVで上回っていない点を明示した
- 更新周期 \(k\) のスライドでは，`k=1` が多く選ばれたことと，密な再調整が有効だった可能性・報酬やEI設計の偏りの可能性を併記した
- 作成物:
- `scripts/build_bogp_12min_presentation_dense.py`
- `slides/BOGP_12min_presentation_dense.pptx`
- 検証:
- `unzip -t slides/BOGP_12min_presentation_dense.pptx` によりPowerPointパッケージの展開検査を実施し，エラーがないことを確認した
- `unzip -l` により16枚のスライドXMLと4つの実験図画像が含まれることを確認した
- 注意:
- `qlmanage` によるサムネイル生成は，ディスク残量不足により未実施である

### 2026-06-10 | dense版スライドへのレジュメ由来考察の反映

- 何をしたか: `notes/seminar_bo_current_friedman_report.tex` の考察章と，現在の本実験版 `notes/paper_8page_2col_draft_expanded.tex` の考察をもとに，dense版スライドの結果スライドへ短い考察枠を追加した
- なぜそうしたか: 結果図を示すだけでは，提案法の有効性をどこまで主張できるか，どこに改善余地があるかが伝わりにくいため，発表中にそのまま説明できる「読み取り」と「考察」をスライド内に入れる必要があった
- 作成物:
- `scripts/build_bogp_12min_presentation_dense_discussion.py`
- `slides/BOGP_12min_presentation_dense_discussion.pptx`
- 反映した内容:
- Slide 11 `結果1: 最終HV・多様性` に，提案法が標準固定率GPを上回る一方，高突然変異固定率には平均HVで届いていないため，全baselineに勝ったとは主張しない，という考察を追加した
- Slide 12 `結果2: 世代推移と安定性` に，提案法の最終HV標準偏差が小さいことを，閉ループ制御がseed依存の不安定さを抑えた可能性として説明する考察を追加した
- Slide 13 `結果3: Pareto front形状` に，HVだけでは低複雑度・高精度・中間領域のどこが改善されたか分からないため，front形状の確認が必要であるという考察を追加した
- Slide 14 `結果4: 更新周期 k の挙動` に，`k=1` が多いことについて，密な再調整が有効だった可能性と，EI比較・warm-up設計が短周期を選びやすくした可能性の両面を追加した
- Slide 15 `総合考察` を，`枠組みは動いた`，`標準固定率には有効`，`強いbaselineに課題`，`次の切り分け` の4点に整理した
- 表記:
- 古いレジュメに残っていた `Friedman-I` 表記は持ち込まず，現在の本文方針に合わせて `Friedman-II` に統一した
- 検証:
- `.venv/bin/python scripts/build_bogp_12min_presentation_dense_discussion.py` でPPTX生成を確認した
- `unzip -t slides/BOGP_12min_presentation_dense_discussion.pptx` によりPowerPointパッケージの展開検査を実施し，エラーがないことを確認した
- `unzip -l` により16枚のスライドXMLと4つの実験図画像が含まれることを確認した
- `qlmanage` により先頭スライドのサムネイル生成を確認した

### 2026-06-10 | 多目的GP説明とBO説明強化版スライドの作成

- 何をしたか: `dense_discussion` 版を土台に，多目的GPの基礎説明とBOの説明を強化した18枚構成のスライド `slides/BOGP_12min_presentation_dense_intro_gp_bo_expanded_discussion.pptx` を作成した
- なぜそうしたか: BOは本研究の中核概念であり，研究目的スライドで初めて登場するため，短すぎない説明を加えたうえで提案手法に接続する必要があったため
- 作成物:
- `scripts/build_bogp_12min_presentation_dense_intro_gp_bo_expanded_discussion.py`
- `slides/BOGP_12min_presentation_dense_intro_gp_bo_expanded_discussion.pptx`
- 反映した内容:
- Slide 2 `多目的GPとは` を追加し，GPを木構造の数式・プログラムを進化的に探索する方法として説明した
- Slide 2 で，多目的GPの目的を `minimize f(T)=(f_1(T),f_2(T))` として示し，本研究では `f_1=予測誤差`，`f_2=式木サイズ` であることを説明した
- Slide 5 `研究目的と提案法の要点` でBOを初出させ，探索状態に応じて次に試す制御入力を選ぶ外側の最適化器として紹介した
- Slide 6 `BOとは` を追加し，surrogate，不確実性，獲得関数，次候補選択の流れを説明した
- Slide 6 では，`D_\ell={(x_i,u_i,r_i)}` と `u_next=argmax EI(u|x_\ell)` 程度の式に留め，カーネルやEI導出には踏み込まない構成にした
- Slide 9 `BO制御器の処理` を，本研究固有の文脈付きBOとして，状態 \(x_\ell\) を固定して `EI_k(x_\ell,p_c,p_m)` を比較する説明に更新した
- 結果スライドに追加済みのレジュメ由来考察は維持した
- 検証:
- `.venv/bin/python scripts/build_bogp_12min_presentation_dense_intro_gp_bo_expanded_discussion.py` でPPTX生成を確認した
- `unzip -t slides/BOGP_12min_presentation_dense_intro_gp_bo_expanded_discussion.pptx` によりPowerPointパッケージの展開検査を実施し，エラーがないことを確認した
- `unzip -l` により18枚のスライドXMLと4つの実験図画像が含まれることを確認した
- スライド番号の繰り下げが反映されていることを，slide13 と slide18 のXML内フッターで確認した
- `qlmanage` により先頭スライドのサムネイル生成を確認した

### 2026-06-11 | レジュメ図1のブロック塗りつぶし色の削除

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の図1「提案法の閉ループ制御構造」において，各ブロックの塗りつぶし色を削除した
- なぜそうしたか: レジュメの図1を白黒・印刷向けにも見やすくし，色による強調を避けたシンプルな模式図にするため
- 反映した内容:
- TikZ の `block`, `ctrl`, `plant`, `data` スタイルから `fill=blue!5`, `fill=orange!12`, `fill=green!10`, `fill=purple!7` を削除した
- 矢印ラベルの背景 `labelbox/.style={fill=white, ...}` は，線と文字の重なりを避けるため維持した
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を実行し，PDF生成を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 819327 bytes).` を確認した
- `rg` によるログ確認で，最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-06-11 | レジュメ参考文献の BibTeX ライブラリへの追加

- 何をしたか: `/Users/kakemyo/Downloads/library.bib` に，`notes/paper_8page_2col_draft_expanded.tex` の681行目以降に記載されている参考文献16件を BibTeX 形式で追加した
- なぜそうしたか: レジュメ本文中の `thebibliography` に直接書かれていた文献を，今後 BibTeX 管理できるようにするため
- 反映した内容:
- `niehaus2001`, `oh2021`, `eiben1999`, `karafotias2015`, `aleti2016`, `mcdermott2012`, `white2013`, `lacava2021`, `liu2022`, `verma2021`, `li2019`, `guerreiro2021`, `burlacu2024`, `jones1998`, `krause2011`, `garrido2020` を追加した
- 既存の `{niehaus2001}` は BibTeX エントリではなかったため，正規の `@inproceedings{niehaus2001, ...}` に置き換えた
- 既存の `Kanai2000BED`, `Kanai1992IDC`, `indX` は残した
- 検証:
- `rg` と `sed` で `library.bib` の追加内容を確認した
- `perl` によるキー一覧確認で，追加した各 cite key が1回ずつ存在し，重複がないことを確認した

### 2026-06-11 | GPプラント・BO制御器の閉ループブロック線図の作成

- 何をしたか: 発表スライドで使うため，GPをプラント，BOを制御器と見なした提案手法の閉ループ構造をブロック線図として作成した
- なぜそうしたか: 提案法の中心である「状態観測 → BOによる制御入力決定 → GPの区間実行 → 報酬計算 → BO更新」という流れを，口頭説明だけでなく視覚的に示せるようにするため
- 作成物:
- `scripts/draw_gp_bo_control_block_diagram.py`
- `slides/figures/gp_bo_closed_loop_block_diagram.png`
- `slides/figures/gp_bo_closed_loop_block_diagram.svg`
- 図の内容:
- `BO 制御器` は文脈付きBO，GP surrogate，EIにより制御入力を選ぶブロックとして表現した
- `多目的 GP プラント` は，交叉・突然変異・NSGA-II・archive更新を含む進化実行部として表現した
- 制御入力は `u_\ell=(p_c,p_m,k)` として，操作強度と更新周期を同時に決定することを明示した
- 観測状態 `x_\ell`，区間統計，報酬 `r_\ell`，BO学習データ `D_k` のフィードバックを矢印で示し，閉ループであることが一目で分かる構成にした
- 検証:
- `.venv/bin/python scripts/draw_gp_bo_control_block_diagram.py` によりPNG/SVGの生成を確認した
- `PYTHONPYCACHEPREFIX=/private/tmp/bogp_pycache .venv/bin/python -m py_compile scripts/draw_gp_bo_control_block_diagram.py` により構文確認を行った
- 生成PNGを目視確認し，文字切れや大きな配置崩れがないことを確認した

### 2026-06-10 | 導入部を指定内容に沿って再構成した v2 スライドの作成

- 何をしたか: `slides/BOGP_12min_presentation_intro_research_context.pptx` を土台に，Slide 2〜5 を指定された導入の流れに合わせて再構成した v2 版 `slides/BOGP_12min_presentation_intro_research_context_v2.pptx` を作成した
- なぜそうしたか: 発表の導入で，GPとは何か，GPの探索が操作率に依存すること，問題や探索段階によって適切なパラメータが変わること，関連研究が示す操作率制御の重要性，多目的GPでの収束性と多様性の両立という流れを明確にしたうえで，研究目的と提案手法に接続するため
- 作成物:
- `scripts/build_bogp_12min_presentation_intro_research_context_v2.py`
- `slides/BOGP_12min_presentation_intro_research_context_v2.pptx`
- 反映した内容:
- Slide 2 `背景: GPと操作率` に，GPが回帰や構造探索に用いられる手法であり，数式・プログラムを進化的に探索する方法であることを追加した
- Slide 2 に，探索はパラメータに依存し，特に交叉率 \(p_c\) と突然変異率 \(p_m\) が重要であることを明示した
- Slide 2 に，適切な値は問題ごとに異なるだけでなく探索段階にも依存し，調整には経験や試行錯誤が必要であることを追加した
- Slide 3 `関連研究: 操作率を固定しない方向性` に，演算子の出現率を調整した例，木構造の複雑さに応じて操作率を調整した例を整理した
- Slide 3 に，GPの操作率は単なる実装上の定数ではなく，探索過程を制御する重要な入力であるという示唆を追加した
- Slide 4 `多目的GPにおいて` に，多目的GPでは単一の最良個体ではなく，精度と複雑さなどのトレードオフを表すPareto front近似を得ることが目的であることを明記した
- Slide 4 に，単に収束を速めるだけではなく，多様な解候補を維持しながらPareto front全体を改善する必要があることを追加した
- Slide 4 に，探索状態に応じて交叉率・突然変異率を動的に調整することは，収束性と多様性を両立する方策になり得ることを追加した
- Slide 5 `研究ギャップと目的` は，Slide 2〜4 の結論を受けて，BOを制御器として \(p_c,p_m,k\) を決定する提案法へつなげる構成に微修正した
- Slide 6 以降のBO説明，提案手法，実験，結果，考察，今後やることは維持した
- 検証:
- `.venv/bin/python scripts/build_bogp_12min_presentation_intro_research_context_v2.py` でPPTX生成を確認した
- `unzip -t slides/BOGP_12min_presentation_intro_research_context_v2.pptx` によりPowerPointパッケージの展開検査を実施し，エラーがないことを確認した
- `unzip -l` により18枚のスライドXMLと4つの実験図画像が含まれることを確認した
- スライド番号の繰り下げが反映されていることを，slide13 と slide18 のXML内フッターで確認した
- `qlmanage` により先頭スライドのサムネイル生成を確認した

### 2026-06-10 | レジュメ「はじめに」に沿った導入再編版スライドの作成

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の「はじめに」に沿って，導入部を研究文脈中心に再構成した18枚構成のスライド `slides/BOGP_12min_presentation_intro_research_context.pptx` を作成した
- なぜそうしたか: 冒頭を単なる用語説明にするのではなく，GPの操作率依存性，固定率の限界，操作率適応の関連研究，多目的GPでの収束性と多様性の必要性をつなげてから，研究目的と提案手法へ自然に接続するため
- 作成物:
- `scripts/build_bogp_12min_presentation_intro_research_context.py`
- `slides/BOGP_12min_presentation_intro_research_context.pptx`
- 反映した内容:
- Slide 2 `背景: GPの操作率は探索を左右する` を作成し，交叉率 \(p_c\) と突然変異率 \(p_m\) が多様性，収束速度，解集合品質に影響することを図示した
- Slide 3 `関連研究: 操作率を固定しない方向性` を作成し，固定率ではなく操作率を適応させる研究があること，探索状態に応じて操作を変える方向性が有効であること，ただし多目的GPで \(p_c,p_m,k\) を状態依存に同時制御する余地があることを整理した
- Slide 4 `多目的GPでは何が難しいか` を，単なる用語説明ではなく，精度と複雑さのPareto front，HV，多様性の必要性を説明するスライドとして再構成した
- Slide 5 `研究ギャップと目的` を作成し，操作率設定を静的ハイパーパラメータではなく，状態観測に基づく閉ループ制御問題として扱うことを明示した
- Slide 5 でBOを，探索状態に応じて次に試す制御入力を選ぶ外側の最適化器として初出させた
- Slide 6 `BOとは` は維持し，surrogate，不確実性，獲得関数，次候補選択を短すぎない粒度で説明する構成とした
- 関連研究はスライド下部に `[R1]` などの文献番号のみを小さく表示し，著者名は大きく出さない方針にした
- 結果スライドのレジュメ由来考察は維持した
- 検証:
- `.venv/bin/python scripts/build_bogp_12min_presentation_intro_research_context.py` でPPTX生成を確認した
- `unzip -t slides/BOGP_12min_presentation_intro_research_context.pptx` によりPowerPointパッケージの展開検査を実施し，エラーがないことを確認した
- `unzip -l` により18枚のスライドXMLと4つの実験図画像が含まれることを確認した
- スライド番号の繰り下げが反映されていることを，slide13 と slide18 のXML内フッターで確認した
- `qlmanage` により先頭スライドのサムネイル生成を確認した

### 2026-06-11 | レジュメ2.2「文脈付きBO」説明の修正

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の2.2節を，`文脈条件付きBO制御器の位置づけ` として差し替えた
- なぜそうしたか: 旧記述では，Krause and Ong の文脈付きガウス過程バンディット最適化そのものを本研究で使っているように読める余地があったため
- 修正内容:
- [14] Jones et al. は期待改善量（EI）とEGOの根拠として位置づけた
- [15] Krause and Ong は「文脈を観測してから行動を選ぶ」という考え方の根拠として位置づけ，本研究のBO制御器そのものではないことを明記した
- 本研究では，GPの世代状態 \(x_\ell\) を文脈，\(u_\ell=(p_{c,\ell},p_{m,\ell},k_\ell)\) を行動，区間報酬 \(r_\ell\) を観測値とし，\(r=f(x_\ell,p_c,p_m,k)\) を学習することを明記した
- [16] Garrido-Merchan and Hernandez-Lobato は，離散的な更新周期 \(k\) を有限候補集合として列挙し，各 \(k\) のもとで \((p_c,p_m)\) 候補に対するEIを評価する混合空間最適化の根拠として残した

### 2026-06-12 | 関連研究への操作率適応セクション追加

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の「はじめに」を短く整理し，「関連研究」の冒頭に `GPにおける操作率適応とパラメータ制御` 節を追加した
- なぜそうしたか: 文献[1][2]との差分を単なる機能比較ではなく，「なぜ多目的GPでは不十分になり得るか」「本研究では何を扱えるようにするか」という研究意義として説明するため
- 反映した内容:
- 「はじめに」では，[1][2]を GP 操作率が探索過程を制御する重要な入力である根拠として短く説明する構成にした
- 関連研究の新2.1節では，事前パラメータ調整とパラメータ制御の違い，[1][2]でできていること，本研究で扱う世代状態・閉ループ制御・更新周期 \(k\) の差分を整理した
- 貢献文では，更新周期 \(k\) を「再調整タイミング」として扱うことを明確化した
- 8ページ上限を維持するため，新2.1節は要点を残して圧縮し，参考文献欄は `\footnotesize`，参考文献前の強制改ページは削除した
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を実行し，PDF生成を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 829963 bytes).` を確認した

### 2026-06-12 | 文献[8] La Cava et al. の repeated trials 表現確認

- 何をしたか: ユーザー提供の `2107.14351v1.pdf` がレジュメ参考文献[8] `Contemporary Symbolic Regression Methods and their Relative Performance` であることを確認し，`references/Contemporary Symbolic Regression Methods and their Relative Performance.pdf` として保存した
- なぜそうしたか: レジュメで「seed数」と表記している実験反復数について，[8] の論文ではどのように表現しているかを本文ベースで確認するため
- 確認方法:
- arXiv v1 の source files を一時取得し，PDF本文に対応する `contents.tex`, `tables/experiment_table.tex`, `appendix.tex` を検索した
- `contents.tex` では，各アルゴリズムを各データセットで `10 repeated trials` 実行し，異なる `random state` が train/test split と algorithm seed を制御すると説明されていることを確認した
- `tables/experiment_table.tex` では `No. of trials per dataset` が 10 と表記されていることを確認した
- `appendix.tex` では，ジョブは固定乱数シードの単一データセット・単一手法の学習として説明されていることを確認した
- 判断:
- `seed` は実験回数そのものではなく乱数状態を指定する値である
- 今回のレジュメでは `乱数シード数` ではなく `独立実行数` または `独立試行数` を主表記にし，括弧で `異なる乱数シードを使用` と補足するのが [8] の表現に近い
- 作成物:
- `references/Contemporary Symbolic Regression Methods and their Relative Performance.pdf`
- `references/Contemporary Symbolic Regression Methods and their Relative Performance.md`

### 2026-06-12 | レジュメ結果説明を収束性中心へ差し替え

- 何をしたか: `main_hv_mean_progress.png` の説明を，多様性ではなく収束性の議論として読めるように `notes/paper_8page_2col_draft_expanded.tex` と `notes/paper_8page_2col_draft.tex` を更新した
- なぜそうしたか: 既存の結果図では多様性の議論が複数箇所にあり，`archive HV` の世代推移図は「Pareto archive の品質がどれだけ早く高い水準へ到達したか」を示す収束性図として使う方が自然であるため
- 反映した内容:
- `世代推移と乱数シード内比較` を `収束性と乱数シード内比較` に変更した
- `main_hv_mean_progress.png` の説明に，`g=30`, `g=48`, `warm-up後HV-AUC` の数値を追加し，提案手法が標準固定率より早く高HV水準へ近づく傾向を明示した
- 考察では，最終HV中心の説明から，HVの立ち上がり，HV-AUC，収束過程のばらつきに基づく説明へ変更した
- 高突然変異固定率に対しては，提案手法がHV-AUCで近い水準を示す一方，最終HVでは届かないため，BO制御器には改善余地があるという慎重な結論にした
- おわりにでは，標準固定率に対する最終HV改善だけでなく，収束性改善と収束過程の安定化の可能性を明記した
- 本実験対象に合わせ，詳細版に残っていた `Friedman-II` 表記を `Friedman-I` に統一した
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を2回実行し，PDF生成と参照更新を確認した
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft.tex` を2回実行し，PDF生成と参照更新を確認した
- `rg -n "Friedman-II"` により，対象レジュメ内に `Friedman-II` 表記が残っていないことを確認した

### 2026-06-12 | レジュメへのHV-AUC説明追加

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` と `notes/paper_8page_2col_draft.tex` の結果章冒頭に，HV-AUCの簡潔な説明を追加した
- なぜそうしたか: 結果表や収束性の議論でHV-AUCが使われている一方，レジュメ内で指標の意味を明示していなかったため
- 反映した内容:
- HV-AUCを「各世代のアーカイブHV推移曲線の下側面積」と説明した
- 本稿ではウォームアップ後の平均的なHV水準として扱い，進化過程全体の収束性を表す指標であることを明記した
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を実行し，8ページのPDF生成を確認した
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft.tex` を2回実行し，6ページのPDF生成と参照更新を確認した

### 2026-06-12 | GP性能評価におけるHV-AUC関連文献の調査

- 何をしたか: GP / MOGP の性能評価において `HV-AUC` またはHV推移曲線の面積・平均HVに相当する評価を用いている文献を調査した
- なぜそうしたか: レジュメでHV-AUCを収束性指標として使っているため，既存研究で同様の指標が使われているか確認する必要があったため
- 調査結果:
- `genetic programming` かつ `HV-AUC` という名称で直接一致する文献は確認できなかった
- 一方，Harrison et al. (2025) は MOGP / GP-GOMEA の性能評価で `Average Hypervolume per generation` と `Average Hypervolume over time` を比較しており，HV推移から収束性・時間方向の性能差を見る近接事例として有用であると判断した
- 反映した内容:
- Harrison et al. (2025) を [R28] として `references/README.md` と参考文献章に追加した
- PDF `references/A Better Multi-Objective GP-GOMEA - But do we Need it.pdf` を保存した
- メタデータノート `references/A Better Multi-Objective GP-GOMEA - But do we Need it.md` を作成した
- 検索ログ `reference_candidates/hv_auc_gp/search_log.md` を作成し，直接一致なし・近接文献ありという判断を記録した
- 注意:
- [R28] は `HV-AUC` の直接根拠ではなく，GP性能評価でHVを世代・時間方向に追う近接根拠として扱う

### 2026-06-12 | レジュメからHV-AUCを外し図3中心の収束性議論へ変更

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` と `notes/paper_8page_2col_draft.tex` から HV-AUC の表記，表の列，説明文を削除した
- なぜそうしたか: レジュメでは新しい補助指標を増やすより，図3のアーカイブHV世代推移だけを用いて収束性を直感的に説明する方が発表時に分かりやすいため
- 反映した内容:
- 結果表は `最終HV`, `最終多様性`, `warm-up後HV増加` に絞った
- 収束性の議論は，図3における \(g=30\), \(g=48\) の平均HV比較に基づき，提案手法が標準固定率より早く高いHV水準へ近づく傾向がある，という説明に整理した
- 考察とおわりにでは，HV-AUCに基づく主張を削除し，HV推移，最終HV，最終HVのばらつきに基づく表現へ変更した
- 今後の課題では，HV-AUCではなく `HV推移`, `到達世代`, `パレートフロントの領域別改善` を用いる方針にした

### 2026-06-12 | レジュメからアーカイブキー説明を削除

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の実験条件表から `アーカイブキー` の行を削除し，表直後のアーカイブキー補足文も削除した
- なぜそうしたか: レジュメではアーカイブキーの詳細まで説明すると主題から外れやすく，実験条件として提示する必要性が低いため
- 残した内容:
- 第3章のアーカイブ一般説明は，アーカイブHVや最終パレートアーカイブを理解するために必要なので残した
- 第5章・第6章のアーカイブHV，最終アーカイブ，パレートアーカイブの説明は評価結果に関わるため残した
- 検証:
- `rg -n "アーカイブキー|トポロジー \\+ ノード値|同一解" notes/paper_8page_2col_draft_expanded.tex` で該当表記が残っていないことを確認した
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を実行し，PDF生成を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 829760 bytes).` を確認した
- `rg` によるログ確認で，最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-06-12 | レジュメ図4の散布図マーカーを手法別に変更

- 何をしたか: `main_representative_pareto_front.png` の点の形を手法ごとに変更し，レジュメ図4とスライドで見分けやすくした
- なぜそうしたか: 色分けだけではスライド投影時に点の識別が難しいため，色は維持しつつマーカー形状でも手法を区別できるようにするため
- 反映した内容:
- `scripts/summarize_main_bo_current_friedman_results.py` に図4用の `MARKERS` を追加した
- 提案手法 `bogp_current` は丸 `o` のままにした
- 標準固定率は四角 `s`，高突然変異は上三角 `^`，高交叉はひし形 `D` にした
- 散布点に黒枠 `edgecolors="black"` と `linewidths=0.35` を追加した
- 図4専用ラベルとして `bogp_current` を `Proposed method` と表示するようにした
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/main_representative_pareto_front.png` を再生成し，レジュメ参照先の `paper_labelled_figures/main_representative_pareto_front.png` に反映した
- 検証:
- `view_image` で，提案手法が丸，標準固定率が四角，高突然変異が三角，高交叉がひし形になっていることを確認した
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を実行し，PDF生成を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 813581 bytes).` を確認した
- `rg` によるログ確認で，最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-06-12 | k結果図を棒グラフからHV・多様性・k時系列対応図へ変更

- 何をしたか: k の総登場回数を示す棒グラフをレジュメ・12分発表スライドの主図から外し，代表 seed=26 における `archive HV`, `population diversity`, `update period k` の世代推移を1枚にまとめた図へ差し替えた
- なぜそうしたか: 本研究の \(k\) は単なる選択カテゴリではなく「次回BO更新まで保持される制御周期」であるため，登場回数だけでは「どの探索状態で短周期・長周期が選ばれたか」を議論しにくい．HVや多様性の変化と同じ世代軸で見ることで，閉ループ制御としての意味を説明しやすくなるため
- 反映した内容:
- `scripts/summarize_main_bo_current_friedman_results.py` に `main_hv_diversity_k_alignment_seed26.png` を生成する処理を追加した
- 新図では，上段にアーカイブHV，中段にpopulation diversity，下段に選択後の区間に保持された \(k\) を階段グラフで表示した
- warm-up 境界 \(g=18\) を破線で表示し，制御更新位置を薄い縦線で示した
- `paper_labelled_figures/main_hv_diversity_k_alignment_seed26.png` にも同じ図を保存した
- `notes/paper_8page_2col_draft_expanded.tex` と `notes/paper_8page_2col_draft.tex` の「更新周期の選択傾向」節を差し替えた
- 考察では，単なる \(k=1\) の多さではなく，HV上昇区間・停滞区間・多様性低下区間における \(k\) の切り替わりを今後分析すべき点として整理した
- `scripts/build_bogp_12min_presentation.py`, `scripts/build_bogp_12min_presentation_dense.py`, `scripts/build_bogp_12min_presentation_dense_discussion.py` のkスライドを新図参照に変更した
- `notes/presentation_12min_20slides_structure.md` も，k選択回数グラフではなくHV・多様性・kの時系列対応図を使う方針に更新した
- 生成物:
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/main_hv_diversity_k_alignment_seed26.png`
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/paper_labelled_figures/main_hv_diversity_k_alignment_seed26.png`
- `slides/BOGP_12min_presentation.pptx`
- `slides/BOGP_12min_presentation_dense.pptx`
- `slides/BOGP_12min_presentation_dense_discussion.pptx`
- 検証:
- `.venv/bin/python scripts/summarize_main_bo_current_friedman_results.py --output-dir outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603` を実行し，新図生成を確認した
- `view_image` で，HV・多様性・kが同一世代軸で表示され，warm-up境界も確認できることを確認した
- `rg -n "main_k_selection_counts|k_selection_counts|K_COUNTS_FIG"` により，対象レジュメTeXと12分発表スライド生成スクリプトから棒グラフ参照が消えていることを確認した
- 詳細版・簡易版レジュメを `lualatex` で再コンパイルし，PDF生成と参照更新を確認した
- 12分発表PPTの通常版・dense版・discussion版を再生成した

### 2026-06-12 | 式(2)と確率的ゆらぎの説明資料をTeX化

- 何をしたか: レジュメの式(2) \(P_{g_{\ell+1}}=F(P_{g_\ell},u_\ell,\xi_\ell)\) について，後から確認しやすい独立したTeX補助資料を作成した
- なぜそうしたか: 発表準備中に「確率的ゆらぎ \(\xi_\ell\)」の意味を確認しやすくし，質問対応時にも一貫した説明ができるようにするため
- 作成したファイル:
- `notes/equation2_gp_plant_stochastic_fluctuation_explanation.tex`
- `notes/equation2_gp_plant_stochastic_fluctuation_explanation.pdf`
- 反映した内容:
- 式(2)をGPプラントとしての集団遷移式として説明した
- \(P_{g_\ell}\), \(u_\ell=(p_c,p_m,k)\), \(F\), \(\xi_\ell\) の意味を表に整理した
- \(\xi_\ell\) が親選択，交叉相手，交叉点，突然変異点，生成部分木，複製個体などの乱数要素をまとめた記号であることを説明した
- BOが制御するのは \(u_\ell\) であり，\(\xi_\ell\) は直接制御できない確率的なばらつきであることを明記した
- 発表時にそのまま読める短い説明例を追加した
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/equation2_gp_plant_stochastic_fluctuation_explanation.tex` を実行し，3ページのPDF生成を確認した
- PDFしおり用の数式警告を避けるため，見出しに `\texorpdfstring` を用い，最終コンパイルで警告が出ないことを確認した

### 2026-06-12 | レジュメ5.4節を図5の結果解釈中心に修正

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の5.4節「更新周期の選択傾向」を，図5の読み方説明中心から，アーカイブHV・集団多様性・更新周期 \(k\) の世代推移から読み取れる結果と示唆を述べる内容に差し替えた
- なぜそうしたか: 発表・レジュメでは，図の注意書きだけでなく「この結果から何が分かるか」を明確に示す必要があるため
- 反映した内容:
- 代表 seed=26 では，アーカイブHVが探索初期からウォームアップ終了付近まで大きく上昇し，その後は高い水準を保ちながら緩やかに改善する，という読み取りを追加した
- 集団多様性は初期に変動・低下するが，ウォームアップ後はおおむね安定し，後半ではやや回復する，という解釈を追加した
- 更新周期 \(k\) は \(1,3,5\) の間で固定せず切り替わっており，初期からウォームアップ境界付近では比較的長い周期も選ばれていることを記述した
- 図5だけでは \(k\) 選択の因果関係までは断定できないため，今後はHV改善量，多様性，停滞長などの状態変数と \(k\) の対応分析が必要である，という限界と次の課題を明記した
- ユーザー指定に従い，「補助情報として〜」で始まる \(k\) 選択回数と平均操作率の段落を削除した
- 図5キャプション中の `population diversity` を「集団多様性」に置き換えた
- 検証:
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を2回実行し，PDF生成を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 929457 bytes).` を確認した
- `rg` により，対象TeXから `補助情報として`, `1702回`, `816回`, `730回`, `1502回`, `population diversity` が消えていることを確認した
- 最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-06-12 | レジュメ6章の更新周期 k 考察を5.4節と整合する形に修正

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の6章「考察」末尾にある更新周期 \(k\) の段落を，5.4節の図5説明と重複しない総括寄りの内容に差し替えた
- なぜそうしたか: 5.4節でアーカイブHV・集団多様性・\(k\) の世代推移を詳しく説明したため，6章では同じ説明を繰り返すのではなく，\(k\) を探索状態と対応づけて評価すべきという考察に役割を分けるため
- 反映した内容:
- 「短い更新周期が多く用いられている」という選択回数寄りの表現を削除した
- \(k\) は単独の選択頻度ではなく，HV改善や集団多様性の変化と対応づけて評価する必要があると整理した
- 図5の代表 seed では，初期からウォームアップ境界付近で比較的長い周期も選ばれ，その区間でアーカイブHVが大きく改善したことを短く述べた
- 後半には短い周期で状態を観測し直すような挙動も見られるが，代表 seed に基づく観察であるため，因果関係や全seedでの一般傾向としては断定しない表現にした
- 今後の課題として，複数 seed にわたる状態変数と \(k\) の関係分析を明記した
- 検証:
- 差し替え直後の本文ではPDFが9ページになったため，6章側の段落をさらに圧縮し，5.4節とのバランスを保ちながら8ページ以内に戻した
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を2回実行し，PDF生成と参照更新を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 929845 bytes).` を確認した
- `rg` により，対象TeXとログから `短い更新周期が多く用いられている`, `population diversity`, `補助情報として` が消えていることを確認した
- 最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-06-12 | レジュメの seed 表記を「実行回数」と「乱数シード」に整理

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` において，実験反復数を意味していた `seed` / `乱数シード` 表現を `実行回数`，`回の実行`，`同一実行条件内` へ置き換えた
- なぜそうしたか: 実験を何回繰り返したかは本来 `trial` や `run` に相当する概念であり，`seed` は乱数発生器の初期値・乱数状態を指すため，意味を分けた方が論文表現として自然であるため
- 反映した内容:
- 実験条件表の `乱数シード数 & 100` を `実行回数 & 100` に変更した
- `複数乱数シードによる比較` を `複数回のアルゴリズム実行による比較` に変更した
- `乱数シード内の最終HV差分` を `同一実行条件内の最終HV差分` に変更した
- `70個の乱数シードで勝ち` など，反復回数を表す表現を `70回の実行で勝ち` などへ変更した
- `各乱数シードで最良の固定率` を `各実行で最良の固定率` に変更した
- 再現用の乱数値や代表例を指す箇所は `代表乱数シード26` のように残した
- 出力ファイルパス中の `seed100` や `seed26` は既存生成物への参照であるため変更しなかった
- 参考にした考え方:
- レジュメ参考文献 [8] のシンボリック回帰比較研究では，実験反復は `trials` / `repeated trials` と表現され，乱数状態は `random state` や `seed` として扱われていたため，本研究でも「実行回数」と「乱数シード」を分けて記述する方針にした
- 検証:
- `rg -n "seed|乱数シード|シード|実行回数|同一実行条件|回の実行|実行別" notes/paper_8page_2col_draft_expanded.tex` により，実験反復を意味する `seed` 表現が残っていないことを確認した
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を2回実行し，PDF生成と参照更新を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 928835 bytes).` を確認した
- `rg -n "Warning|Overfull|Undefined|Rerun" notes/paper_8page_2col_draft_expanded.log` により，最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-06-12 | レジュメ参考文献[11] PDF確認と保存

- 何をしたか: ユーザー添付PDF `/Users/kakemyo/Downloads/3300148.pdf` を読み込み，レジュメ参考文献[11] `Quality Evaluation of Solution Sets in Multiobjective Optimisation: A Survey` であることを確認した
- 確認内容:
- 抽出本文の1ページ目に `Quality Evaluation of Solution Sets in Multiobjective Optimisation: A Survey`，著者 `Miqing Li and Xin Yao`，`ACM Comput. Surv. 52, 2, Article 26`，DOI `10.1145/3300148` が記載されていることを確認した
- 本文は38ページで，レジュメ参考文献欄の `ACM Computing Surveys, vol. 52, no. 2, 2019` と一致した
- レジュメで参照している「多目的解集合の評価では，収束性，広がり，均一性など複数の観点が存在する」という説明は，本文2.2節の `convergence, spread, uniformity, and cardinality` の整理に基づくものであり妥当であると判断した
- HVに関する補足として，本文3.6.5節ではHVが広く用いられる品質指標であり，Pareto dominance 改善に敏感である一方，参照点設定や高次元での計算量に注意が必要と説明されていることを確認した
- 保存先:
- `references/Quality Evaluation of Solution Sets in Multiobjective Optimisation - A Survey.pdf`

### 2026-06-12 | レジュメ参考文献[12] PDF確認と保存

- 何をしたか: ユーザー添付PDF `/Users/kakemyo/Downloads/3453474.pdf` を読み込み，レジュメ参考文献[12] `The Hypervolume Indicator: Computational Problems and Algorithms` であることを確認した
- 確認内容:
- 抽出本文の1ページ目に `The Hypervolume Indicator: Computational Problems and Algorithms`，著者 `Andreia P. Guerreiro, Carlos M. Fonseca, and Luís Paquete`，`ACM Computing Surveys, Vol. 54, No. 6, Article 119`，DOI `10.1145/3453474` が記載されていることを確認した
- 本文は42ページで，レジュメ参考文献欄の `ACM Computing Surveys, 2021` と一致した
- レジュメで参照している「HVは参照点に対してパレート解集合が支配する領域の大きさ」という説明は，本文2.2節 Definition 2.1 の hypervolume indicator 定義に基づくものであり妥当であると判断した
- レジュメで参照している「HVは収束性と多様性を同時に反映する代表的な指標」という説明は，本文1章の `proximity to the Pareto front, diversity, and spread` を同時に考慮するという説明に基づくものであり妥当であると判断した
- 注意点:
- 本論文の主眼はHVの計算問題・貢献度・部分集合選択アルゴリズムの総説であり，HVの評価指標としての包括的な性質説明は参考文献[11]と併用して説明するのが適切である
- 保存先:
- `references/The Hypervolume Indicator - Computational Problems and Algorithms.pdf`

### 2026-06-12 | レジュメ参考文献[15] PDF確認と保存

- 何をしたか: ユーザー添付PDF `/Users/kakemyo/Downloads/NIPS-2011-contextual-gaussian-process-bandit-optimization-Paper.pdf` を読み込み，レジュメ参考文献[15] `Contextual Gaussian Process Bandit Optimization` であることを確認した
- 確認内容:
- PDFメタデータと本文1ページ目に `Contextual Gaussian Process Bandit Optimization`，著者 `Andreas Krause, Cheng Soon Ong`，`Advances in Neural Information Processing Systems 24`，ページ `2447--2455` が記載されていることを確認した
- 本文2章で，各ラウンドに文脈 \(z_t\) を受け取り，行動 \(s_t\) を選び，報酬 \(y_t=f(s_t,z_t)+\epsilon_t\) を観測する設定が定義されていることを確認した
- 本文では，報酬関数を行動・文脈の直積空間 \(S\times Z\) 上のガウス過程としてモデル化していることを確認した
- 本文3章では，文脈付きの制御則として `CGP-UCB` が提案され，EIではなくUCB型の獲得規則を用いていることを確認した
- 本文5章では，文脈空間と行動空間のカーネルを積・和などで組み合わせる composite kernel の考え方が示されていることを確認した
- レジュメでの使い方の判断:
- レジュメの「Krause and Ong の手法をそのまま用いるのではなく，各時点で文脈を観測し，その文脈のもとで行動を選ぶ考え方の根拠として位置づける」という説明は正しい
- 本研究では獲得関数にEIを使うため，[15] はEIの根拠ではなく，状態 \(x_\ell\) を文脈，制御入力 \(u_\ell=(p_c,p_m,k)\) を行動，報酬 \(r_\ell\) を観測値とみなす文脈条件付き最適化の枠組みの根拠として使うのが適切である
- 保存先:
- `references/Contextual Gaussian Process Bandit Optimization.pdf`

### 2026-06-12 | レジュメ用 BibTeX 情報の不足項目追記

- 何をしたか: ユーザー添付の `/Users/kakemyo/Downloads/library (1).bib` に，レジュメで用いた参考文献の不足情報を追記した
- 追記方針:
- 既に存在する著者，タイトル，掲載先，年などは重複して書き直さず，不足していた DOI，巻号，Article番号，ページ，numpages，出版社，arXiv 情報のみを追加した
- DOI がある文献には DOI を追加した
- La Cava et al. (2021) は arXiv 番号と URL を追加した
- Krause and Ong (2011) は NeurIPS 巻数，ページ，出版社を追加した
- 確認:
- BibTeX エントリ数は既存の制御系文献2件を含めて18件であることを確認した
- レジュメ文献16件のうち，DOI が確認できる14件には DOI が入っていることを確認した

### 2026-06-13 | レジュメ用参考文献PDFの集約

- 何をしたか: レジュメで用いた参考文献[1]〜[16]のPDFを `reference_for_seminar/` に集約した
- なぜそうしたか: 小発表・レジュメ確認時に，本文中の参考文献番号とPDFをすぐ対応づけて確認できるようにするため
- 保存方針:
- ファイル名の先頭に `01_` から `16_` までの番号を付け，レジュメの参考文献番号と対応させた
- `references/` に保存済みのPDFに加え，問題設定文献として `reference_candidates/problem_settings/` に保存していたPDFも同じフォルダへコピーした
- 検証:
- `find reference_for_seminar -maxdepth 1 -type f -name "*.pdf" | wc -l` により，PDFが16件あることを確認した

### 2026-06-12 | レジュメ本文の英語表記を日本語へ統一

- 何をしたか: `notes/paper_8page_2col_draft_expanded.tex` の本文中に残っていた英語表記を，日本語表記へ統一した
- なぜそうしたか: レジュメ全体で `Pareto archive` や `warm-up` のような英語表記が混在していると，発表資料としての読みやすさと表記統一性が下がるため
- 反映した内容:
- `Pareto archive` を「パレートアーカイブ」に統一した
- `warm-up` を「ウォームアップ」に統一した
- ファイルパス，画像ファイル名，LaTeXラベル，参考文献タイトル中の英語は，参照や文献情報として必要なため変更しなかった
- 検証:
- `rg` により，本文対象語として `Pareto archive`, `Pareto front`, `warm-up`, `population diversity`, `symbolic regression`, `crowding distance` などが残っていないことを確認した
- 検索結果に残った英語は画像ファイルパスのみであることを確認した
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` を2回実行し，PDF生成と参照更新を確認した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 928203 bytes).` を確認した
- 最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-06-13 | 12分発表用スライド日本語版 v1 の作成

- 何をしたか: レジュメ内容と本実験結果をもとに，12分発表用の日本語版スライドを新規作成した
- 作成物:
- `scripts/build_bogp_12min_presentation_story_jp_v1.py`
- `slides/BOGP_12min_presentation_story_jp_v1.pptx`
- なぜそうしたか:
- 既存スライドは1枚あたりの情報量が多く，先行研究との差分，新規性，結果の解釈が伝わりにくかったため
- 12分発表ではレジュメ全体を網羅するのではなく，「固定率ではなく状態依存閉ループ制御として扱う」という研究の立ち位置を明確に示す必要があるため
- 後で英語版へ翻訳しやすいように，短文・主張単位の構成にした
- 構成:
- 本編12枚とBackup 6枚の計18枚とした
- 本編は，背景，多目的GPの課題，先行研究との差分，研究目的，提案手法，実験設定，結果，今後の方針の順に整理した
- 結果説明は「標準固定率GPには改善」「高突然変異固定率GPには平均HVでまだ届かない」という誠実な流れにした
- Backupには，BOの基本，アーカイブと現在集団，Pareto front詳細，更新周期 \(k\)，真の式の構成要素分析を置いた
- 使用した主な数値:
- 提案法の最終アーカイブHV平均は 0.802，標準固定率GPは 0.783，高突然変異固定率GPは 0.808 として説明した
- 提案法の最終HV標準偏差は 0.022，標準固定率GPは 0.055 として，seed間の安定性を説明した
- 同一実行条件内比較では，提案法が標準固定率GPに 70勝2分28敗であったことを示した
- 検証:
- `python3 scripts/build_bogp_12min_presentation_story_jp_v1.py` によりPPTX生成を確認した
- `unzip -t slides/BOGP_12min_presentation_story_jp_v1.pptx` によりPPTXに破損がないことを確認した
- PPTX内のスライド数が18枚であることを確認した
- スライドタイトル一覧を抽出し，本編12枚が「背景→課題→先行研究との差分→研究目的→提案手法→実験→結果→まとめ」の流れになっていることを確認した

### 2026-06-13 | Presentations プラグイン版 12分発表スライドの再生成

- 何をしたか: ユーザー指定の `@presentations` に従い，直近の12分発表用スライド作成計画を Presentations プラグインの artifact-tool ワークフローで再実行した
- 作成物:
- `scripts/build_bogp_12min_presentation_story_jp_plugin_v1.mjs`
- `slides/BOGP_12min_presentation_story_jp_plugin_v1.pptx`
- `outputs/manual-20260613-bogp-12min-jp/presentations/bogp-12min-story-jp/preview/contact-sheet.png`
- `outputs/manual-20260613-bogp-12min-jp/presentations/bogp-12min-story-jp/artifact-build-manifest.json`
- なぜそうしたか:
- 前回版はリポジトリ既存の直接OOXML生成方式で作成したが，今回はユーザーが `@presentations` を明示したため，プラグイン推奨の artifact-tool によるPPTX出力・PNGプレビュー・コンタクトシート確認まで行う必要があった
- 既存の `BOGP_12min_presentation_story_jp_v1.pptx` は残し，プラグイン版として `BOGP_12min_presentation_story_jp_plugin_v1.pptx` を別名で作成した
- 反映した内容:
- 本編12枚，補足6枚の合計18枚構成とした
- ストーリーは「多目的GPの目的→固定率の課題→先行研究との差分→研究目的→閉ループ制御→実験→結果→今後の方針」の順に整理した
- 日本語版として，`Backup` を「補足」，`Pareto front` を「パレートフロント」，`GP Plant` を「GPプラント」へ寄せた
- 結果は，提案法が標準固定率GPに対して改善する一方，高突然変異固定率GPには平均HVでまだ届かないという誠実な説明にした
- 検証:
- `PYTHON=.venv/bin/python node scripts/build_bogp_12min_presentation_story_jp_plugin_v1.mjs` により，PPTX，プレビューPNG，コンタクトシート，レイアウトJSONを生成した
- `unzip -t slides/BOGP_12min_presentation_story_jp_plugin_v1.pptx` によりPPTXに破損がないことを確認した
- PPTX内のスライド数が18枚であることを確認した
- スライドタイトル一覧を抽出し，本編12枚と補足6枚が意図した順序になっていることを確認した
- `outputs/manual-20260613-bogp-12min-jp/presentations/bogp-12min-story-jp/preview/contact-sheet.png` を目視確認し，大きな図切れや極端な文字はみ出しがないことを確認した
- QAスコアカード `outputs/manual-20260613-bogp-12min-jp/presentations/bogp-12min-story-jp/qa/comeback-scorecard.txt` を作成し，40/45 とした

### 2026-06-13 | 結果章を拡張した12分発表スライドの作成

- 何をしたか: 直近の構成修正案に従い，12分発表用スライドを「導入→提案手法→結果・考察→結論」の流れで再構成し，結果章を拡張した
- 作成物:
- `slides/BOGP_12min_presentation_story_jp_results_expanded_v1.pptx`
- `outputs/manual-20260613-bogp-12min-jp-results-expanded/presentations/bogp-12min-story-jp-results-expanded/preview/contact-sheet.png`
- `outputs/manual-20260613-bogp-12min-jp-results-expanded/presentations/bogp-12min-story-jp-results-expanded/artifact-build-manifest.json`
- 変更した生成スクリプト:
- `scripts/build_bogp_12min_presentation_story_jp_plugin_v1.mjs`
- なぜそうしたか:
- 以前の構成では，結果章が「最終指標」と「強い固定率との比較課題」に寄っており，世代推移や更新周期 \(k\) の挙動を説明する流れが弱かったため
- 提案法の中心メッセージである「操作率だけでなく更新周期 \(k\) も状態依存に制御する」ことを，結果スライド内で視覚的に示す必要があったため
- 反映した内容:
- 本編は14枚，補足は5枚の計19枚とした
- Slide 4 の関連研究は，文献[1]の「遺伝的演算子の適応」と文献[2]の「木構造に応じた操作率変更」に絞り，本研究との差分ではなく「残る課題」へ接続する構成にした
- Slide 7 では報酬設計を数式ではなく，「より良い解集合に進んだか + 多様性を保てたか - 頻繁に制御しすぎていないか」という言葉で説明する形にした
- Slide 10 にレジュメ図3相当のアーカイブHV世代推移を追加し，ウォームアップ後も提案法が標準固定率より高いHV水準を維持する傾向を説明できるようにした
- Slide 11 にレジュメ図5相当の代表seedにおけるHV・多様性・更新周期 \(k\) の対応図を追加し，\(k\) が固定ではなく区間ごとに切り替わることを示した
- Slide 12 では，高突然変異固定率が平均HVで最良であることを示し，現行BO制御器には改善余地があるという誠実な課題提示にした
- 検証:
- `PYTHON=.venv/bin/python node scripts/build_bogp_12min_presentation_story_jp_plugin_v1.mjs` によりPPTX，プレビューPNG，コンタクトシート，レイアウトJSONを生成した
- `unzip -t slides/BOGP_12min_presentation_story_jp_results_expanded_v1.pptx` によりPPTXに破損がないことを確認した
- PPTX内に slide1 から slide19 までが含まれており，計19枚であることを確認した
- `outputs/manual-20260613-bogp-12min-jp-results-expanded/presentations/bogp-12min-story-jp-results-expanded/preview/contact-sheet.png` を目視確認し，追加したSlide 10とSlide 11の図がスライド内に収まっていることを確認した

### 2026-06-14 | 図5のスライド掲載用ラベル拡大

- 何をしたか: 12分発表スライドの結果3で用いるレジュメ図5について，スライド投影時に読みやすいよう，タイトル，軸ラベル，目盛ラベル，注記の文字サイズを大きくしたスライド用PNGを作成した
- 作成物:
- `scripts/make_slide_k_alignment_figure.py`
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/paper_labelled_figures/main_hv_diversity_k_alignment_seed26_slide.png`
- 更新したPPTX:
- `slides/BOGP_12min_presentation_story_jp_results_expanded_v1.pptx`
- なぜそうしたか:
- 元の図5はレジュメ本文に貼るには十分だったが，スライド内で縮小表示するとタイトルや縦軸ラベルが小さく，発表時に読み取りにくい可能性があったため
- 既存のレジュメ用図を上書きせず，スライド用に別名PNGを作ることで，論文・レジュメ用図と発表用図を使い分けられるようにするため
- 反映した内容:
- matplotlib の `Agg` バックエンドで，seed 26 の `generation_metrics.jsonl` と `control_records.jsonl` から同じ内容の図を再描画した
- 図タイトル，軸ラベル，目盛ラベル，ウォームアップ境界注記を大きくし，線幅とマーカーもやや太くした
- `scripts/build_bogp_12min_presentation_story_jp_plugin_v1.mjs` の図参照を `main_hv_diversity_k_alignment_seed26_slide.png` に変更した
- 検証:
- `.venv/bin/python scripts/make_slide_k_alignment_figure.py` によりスライド用PNGを生成した
- `PYTHON=.venv/bin/python node scripts/build_bogp_12min_presentation_story_jp_plugin_v1.mjs` によりPPTXを再生成した
- `outputs/manual-20260613-bogp-12min-jp-results-expanded/presentations/bogp-12min-story-jp-results-expanded/preview/slide-11.png` を確認し，図が切れずに配置されていることを確認した
- `unzip -t slides/BOGP_12min_presentation_story_jp_results_expanded_v1.pptx` によりPPTXに破損がないことを確認した

### 2026-06-14 | 図2・図3のスライド掲載用ラベル拡大

- 何をしたか: 12分発表スライドの結果1・結果2で用いるレジュメ図2・図3について，スライド投影時に読みやすいよう，タイトル，軸ラベル，目盛ラベル，凡例の文字サイズを大きくしたスライド用PNGを作成した
- 作成物:
- `scripts/make_slide_result_figures.py`
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/paper_labelled_figures/main_final_hv_diversity_slide.png`
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/paper_labelled_figures/main_hv_mean_progress_slide.png`
- 更新したPPTX:
- `slides/BOGP_12min_presentation_story_jp_results_expanded_v1.pptx`
- なぜそうしたか:
- 元の図2・図3はレジュメ本文向けであり，スライド上ではタイトルやラベルが小さく見えやすかったため
- 既存のレジュメ用図を上書きせず，発表用に別名PNGを作ることで，用途別に図を使い分けられるようにするため
- 反映した内容:
- 図2では，最終アーカイブHVと最終多様性の棒グラフについて，軸ラベルとタイトルを拡大し，手法名を短いラベルにして読みやすくした
- 図3では，アーカイブHV世代推移について，軸ラベル，タイトル，凡例を拡大し，線幅もやや太くした
- `scripts/build_bogp_12min_presentation_story_jp_plugin_v1.mjs` の図参照を `main_final_hv_diversity_slide.png` と `main_hv_mean_progress_slide.png` に変更した
- 検証:
- `.venv/bin/python scripts/make_slide_result_figures.py` によりスライド用PNGを生成した
- `PYTHON=.venv/bin/python node scripts/build_bogp_12min_presentation_story_jp_plugin_v1.mjs` によりPPTXを再生成した
- `outputs/manual-20260613-bogp-12min-jp-results-expanded/presentations/bogp-12min-story-jp-results-expanded/preview/slide-09.png` と `slide-10.png` を確認し，図が切れずに配置されていることを確認した
- `unzip -t slides/BOGP_12min_presentation_story_jp_results_expanded_v1.pptx` によりPPTXに破損がないことを確認した

### 2026-06-15 | 修正後の図5に合わせたスライド用ラベル再拡大

- 何をしたか: 修正後のレジュメ図5に合わせ，12分発表スライドの結果3で用いる図5を再度スライド用に調整した
- 更新したファイル:
- `outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/paper_labelled_figures/main_hv_diversity_k_alignment_seed26_slide.png`
- `slides/BOGP_12min_presentation_story_jp_results_expanded_v1.pptx`
- `outputs/manual-20260613-bogp-12min-jp-results-expanded/presentations/bogp-12min-story-jp-results-expanded/preview/slide-11.png`
- なぜそうしたか:
- レジュメ図5のタイトルが `Representative seed=26: HV, diversity, and held update period k` に修正されたため，スライド用図も同じ表記へ合わせる必要があった
- スライド投影時の可読性をさらに上げるため，タイトル，軸ラベル，目盛ラベル，ウォームアップ境界注記を前回より少し大きくした
- 反映した内容:
- `scripts/make_slide_k_alignment_figure.py` のタイトル表記から `bo_current` を外し，修正後レジュメ図5と整合させた
- 図タイトル，軸ラベル，目盛ラベル，注記，線幅，マーカーサイズを拡大した
- 現在のPresentationsプラグイン環境では旧artifact-toolビルド補助スクリプトが利用できなかったため，既存PPTX内でSlide 11が参照する `ppt/media/image3.png` のみを新しい図5PNGへ差し替えた
- 検証:
- `.venv/bin/python scripts/make_slide_k_alignment_figure.py` によりスライド用図5を再生成した
- `unzip -t slides/BOGP_12min_presentation_story_jp_results_expanded_v1.pptx` によりPPTXに破損がないことを確認した
- PPTXから抽出した `ppt/media/image3.png` と新しいスライド用図5PNGが `cmp` で一致することを確認した
- `outputs/manual-20260613-bogp-12min-jp-results-expanded/presentations/bogp-12min-story-jp-results-expanded/preview/slide-11.png` を更新し，スライド上の図配置と可読性を確認した

### 2026-06-15 | レジュメ図5タイトルから bo_current 表記を削除

- 何をしたか: レジュメ図5 `main_hv_diversity_k_alignment_seed26.png` の画像内タイトルから `bo_current` 表記を削除した
- なぜそうしたか: 図5はレジュメ・発表で用いる代表乱数シードの制御履歴図であり，実装上の手法IDである `bo_current` がタイトルに残っていると読者向けの図として不自然なため
- 反映した内容:
- `scripts/summarize_main_bo_current_friedman_results.py` の図5タイトルを `Representative bo_current seed=...` から `Representative seed=...` に変更した
- `.venv/bin/python scripts/summarize_main_bo_current_friedman_results.py --output-dir outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603 --report-path notes/main_bo_current_friedman_report.tex` を実行し，図5を再生成した
- レジュメ参照先の `paper_labelled_figures/main_hv_diversity_k_alignment_seed26.png` も同名で更新した
- 検証:
- `view_image` で図5タイトルが `Representative seed=26: HV, diversity, and held update period k` になっていることを確認した
- `.TinyTeX/bin/universal-darwin/lualatex -interaction=nonstopmode -halt-on-error -output-directory=notes notes/paper_8page_2col_draft_expanded.tex` によりレジュメPDFを再生成した
- LaTeX ログ上で `Output written on paper_8page_2col_draft_expanded.pdf (8 pages, 926498 bytes).` を確認した
- 最終ログに未定義参照，LaTeX warning，overfull warning が出ていないことを確認した

### 2026-09-03 | 修論本実験の長期探索型問題候補を再設計

- 何をしたか: 現行Friedman-I実験がBO warm-up中に大半のHV改善を終えていたことを定量確認し、既存のNiehaus/Oh由来候補を残したまま、長期探索型MOGP問題と実験構成を再整理した
- 定量確認:
  - 提案法の平均archive HVは世代0で0.452491、世代18で0.740278、世代78で0.802461
  - warm-up中に世代0～78の総HV改善量の約82.2%を得ていた
  - 現行warm-upは `k=1,1,3,3,5,5` で18 GP世代を消費し、`k`と探索時期が交絡する
- 作成物:
  - `notes/thesis_long_horizon_problem_setting_options.md`
  - `reference_candidates/problem_settings/long_horizon_mogp_search_log.md`
- 文献:
  - White et al. (2013)を[R29]として正式採用し、Vladislavleva-4、Korns-12等の難しい再現可能なbenchmark仕様を確認した
  - Liu et al. (2022)を[R30]として正式採用し、accuracy--size MOGPにおける小木の過剰複製とevolvability低下、Airfoil等の実験設定を確認した
  - 候補フォルダの原PDFは移動・削除せず、同一checksumのコピーを`references/`へ保存した
- 暫定方針:
  - 主合成候補をVladislavleva-4、機序stressをAirfoil、独立実データ候補をConcreteまたはCCPP、Friedman-Iを負の対照とする
  - 最終採否は提案法の勝敗を見ず、固定率だけのcontroller-blind pilotで `q_W`、`t_90`、post-warm-up改善、状態別の率反応を測って決める
  - 第一予算案はpopulation 100、warm-up 18世代、post-warm-up 300世代、合計318世代、初期集団込み31,900評価とする
  - 現行W18 sequentialはbaselineとして残し、counterbalanced W18、`k=1`短縮warm-up、warm-up replay固定率をablation候補とする
- 実装前提:
  - tabular SR adapter、固定split manifest、hard node cap 100、式とtest指標の保存、HV正規化・reference pointの固定が必要

### 2026-10-01 | 長期探索型問題設定の調査・構成案を再開し検証

- 対象: `notes/thesis_long_horizon_problem_setting_options.md`と文献調査ログ。既存のNiehaus/Oh由来候補、新規候補22項目、warm-up比較案を保持した。
- 保存済み本文で再確認し、元論文の条件と本研究への移植条件を分離した。[R24][R25][R29][R30]
- Niehausの最大100,000 tournamentsを本研究の世代数と同一視しないこと、分類の元データ・生成規則が本文だけでは確定しないことを明記した。[R24]
- Ohの固定GPの突然変異0.01とSAGP平衡点0.15の差を踏まえ、高突然変異・tuning済み固定との比較を維持した。[R25]
- 設計メモ内のNiehaus DOIとOh掲載誌・DOI、Harrisonのsynthetic定義の付録番号を訂正した。元文献メタデータとPDFは変更していない。
- 有限archiveの切り詰めでHVが低下し得るため、`t_90`を履歴最大HVの有限予算内改善量に対する到達時間として定義した。生HVも別保存する。
- test HVの誤差分母・linear scalingをtrain由来に固定し、split×seedの反復を独立30標本として扱わない統計手順へ補正した。
- 評価予算31,900は初期100＋318世代×100の評価スロットであり、キャッシュ・棄却・係数探索がある場合の実fitness呼出し数を別記録する方針を追記した。
- 検証: `.venv/bin/python -m pytest -q`で52 passed、matplotlib由来のdeprecation warnings 13件。
- 実行状況: 文献調査と実験設計の再確認を完了。新benchmarkによる予備実験は未実行であり、adapter・式保存・test評価等の実装を必要とする。

### 2026-10-01 | 問題設定用文献の取得・整理と5候補への絞り込み

- ユーザー依頼により`references/problem_settings/`を作成。採用済み[R10][R24][R25][R28][R29][R30]のPDF・メタデータを同一内容の閲覧コピーとして配置し、直下原本・旧候補資料・既存リンクを保持した。
- Zhang et al. (2025), *A Multi-Objective Genetic Programming with Size Diversity for Symbolic Regression Problem*をBrunel大学機関リポジトリから新規ダウンロード。accepted版4ページ、IEEE personal useの条件を確認し、原本とtopic copyを保存した。
- 上記論文は取得済みLH03として保留管理。事後的MSE外れ値除外を本研究の評価手順には採用しない。本文取得と正式採用を区別した。
- Vladislavleva原典LH01とNi AQ原典LH02を出版社・DOI・著者/大学ページ・機関リポジトリ・タイトルで再探索したが、ルールに合う全文を確保できず、完全タイトル・DOI等を手動取得リストへ記録した。
- 次に実装・固定率pilotへ進める候補をUBall5D、Airfoil、Concrete、CCPP、Korns-12の5件に絞り、採用理由・条件・注意点・他候補を保留する理由を`notes/thesis_problem_shortlist_5.md`に保存した。[R29][R30][R25]
- 以前の22案・Niehaus/Oh由来の案・warm-up比較案は保持。新しい問題でのGP実験は今回は実行していない。
- 検証: PDF7本の読込み、全原本/topic copyのSHA-256一致、9件のメタデータ、bundle/shortlist内ローカルリンク、5件の候補行、`git diff --check`を確認。新規PDFのタイトル・実験条件ページをレンダリングし判読可能なことを確認した。
- コード変更はないためpytestは再実行していない。コミット・pushは行っていない。

### 2026-10-01 | UBall5D・Airfoil・Concreteをセミナー条件で各3回実行

- ユーザー指定を優先し、最終セミナーレジュメの集団24・warm-up18＋本評価60＝総78世代で、3問題×4手法×seed0/1/2の計36実行を完了した。
- 訓練fitness呼出は初期24＋1872子評価＝1896/実行、合計68,256。BO制御器・報酬・遺伝演算・生存選択・関数集合は変更していない。
- UCI公式Airfoil/Concreteの元配布物を`data/problem_settings/raw/`へ保存。Concreteの同一入力重複34行は除外せず同partitionへまとめた。train-only X/y標準化、固定split/データseed/hashを記録した。
- UBallは[R29]のcanonical train1024/test5000と独立validation1024。GPの3seedは同一データ上の探索乱数反復である。
- adapterと検索に影響しない式記録用engineを実装し、各世代の訓練選択式を検索終了後にvalidation/testへ適用した。テストによる式選択はしていない。
- 提案法の最終HV平均: UBall0.798186、Airfoil0.829705、Concrete0.824499。高突然変異との差はそれぞれ+0.001094、+0.018369、−0.003884。
- Airfoilは提案法3回とも18世代後に改善し、うち2回は60世代以降もHV改善。固定標準にも後半改善があり、次の長期pilotの最優先。ただしtest誤差で固定標準を上回らず、n=3の優位確定ではない。
- UBallは提案法3回とも定数式・train NRMSE約1。現構成のまま長期主問題に採用しない。Concreteは提案法2回が18世代までで止まり、高突然変異2回には終盤改善があるため副検証として保持。
- 結果: `outputs/thesis_three_problem_pilot/seminar_conditions_seed3_20261001/`。詳細: `notes/thesis_three_problem_pilot_report.md`。
- focused tests 15件、全pytest 61件成功（既存Matplotlib非推奨warning13件）。36実行の世代・初期HV・子評価数・warm-up境界を確認し、q_W/t90を別JavaScript実装でも再計算一致。推移図を目視確認した。
- 本番採否用の120/318世代controller-blind screenは未実行。以前の5候補・22案・Niehaus/Oh由来案は保持した。コミット・pushは行っていない。

### 2026-10-07 | 指導教員共有用：3問題の予備実験と状態入力比較のレジュメ作成

- 何をしたか: 2026-10-01に実行済みのUBall5D・Airfoil・Concrete各3回の予備実験と、Friedman-Iの提案法／非文脈BO各100回の比較を、以前のレジュメと同じA4・10pt・2段組の新規LaTeX資料へまとめた。
- 成果物: `notes/supervisor_experiment_comparison_resume_20261007.tex`、同名PDF（7ページ）、`notes/supervisor_experiment_comparison_resume_20261007_source_bundle.zip`。
- 図表生成元: `scripts/build_supervisor_experiment_resume.py`。保存先は`notes/figures/supervisor_comparison_20261007/`。既存レジュメ・結果・制御器・問題設定は上書きしていない。今回、新しいGP実験は実行していない。
- なぜそうしたか: 初見の読者に、問題選定のための各3回の予備観察と、状態入力の有効性を切り分ける100回の比較を混同せず理解してもらうため。
- 反映内容: 簡単な研究目的、NSGA-II型GPとBOの分担、HV・NRMSE・構造多様性の意味、共通評価予算、問題の具体的内容と選定理由、前処理・分割・重複管理、結果表、世代推移・分布・対応比較・k選択割合、結果の限界、次の検証を記載した。
- 問題設定の文献: 保存済み本文を再確認し、[R29] White et al.のTable 5・6.1節をUBall5Dの式・標本仕様と選定の注意に、[R30] Liu et al.の3.1節・図1および6.1.2節・図3をAirfoilの小木偏重・早期停滞の背景に、Table 2・3をConcreteの多目的GP利用実績に使った。資料内は[1][2]で採番し、研究ノート番号との対応も記載した。
- データ出典: 取得済みUCIデータの保存メタデータを資料内[3][4]で引用した。今回の分割・標準化・小集団・世代数は本研究の条件であり、元論文の推奨条件や完全再現ではないことを明示した。参考文献原本と問題設定用フォルダは保持し、新しい文献は取得していない。
- 主要な整理: Airfoilは後半改善を観察できる継続検証候補、Concreteは早期停滞の副候補、UBall5Dは定数式への停滞を診断する候補とした。HVが約0.8でも定数式になり得ること、各3回で優位を確定できないこと、テスト誤差で問題を選ばないことを記載した。
- 状態入力比較の整理: 平均最終HV差+0.000191（対応95%信頼区間に0を含む）により平均性能の上乗せは未確認。一方、HV標準偏差約26%低減を支持する結果は報告し、短周期化や少量学習の影響は仮説として分けた。観測なしBOでも報酬観測・状態計測は継続していることを明記した。
- 検証: 3問題の36実行の世代履歴・最終HV・多様性・訓練誤差を保存集計と照合した。100組のウォームアップ一致、1872子評価、提案法と既存最終実験の全世代履歴一致を再確認し、対応平均差・信頼区間・t検定も再計算一致。照合結果は`source_validation.json`へ保存した。
- PDF確認: LuaLaTeXで最終版をコンパイルし、7ページ、未定義参照・warning・overfull・underfullなしを確認。Popplerで全7ページを描画し、日本語、表、凡例、キャプション、図の切れ、ページ配置を目視確認した。ソースZIPの内容検査も実施した。
- 実験エンジンには変更を加えていないため、全pytestは再実行していない。資料生成スクリプトの実行と上記数値照合・PDF確認で検証した。
- Git: branch `codex/premethod`、HEAD `46a8a43`。コミット・pushなし。新規資料・図表・生成スクリプトはローカルで未コミット、既存の未コミット変更と`outputs/`内の結果は保持した。
