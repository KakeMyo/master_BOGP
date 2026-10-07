# 論文用「提案手法」節ドラフト

- 作成日: 2026-04-28
- 目的: [proposed_method_spec_v1.md](/Users/kakemyo/Downloads/master_BOGP/notes/proposed_method_spec_v1.md) をもとに、論文本文へ流用できる「提案手法」節の文章下書きを作る

## 3. 提案手法

### 3.1 基本方針

本研究では、遺伝的プログラミングにおける交叉率 `p_c` と突然変異率 `p_m` を固定ハイパーパラメータとして扱うのではなく、進化過程の状態に応じて逐次更新される制御入力として扱う。さらに、操作率だけでなく次回更新までの世代数 `k` も制御対象に含めることで、どの値を使うかだけでなく、いつ再調整するかも状態依存で決める枠組みを採る。

この考え方に基づき、本研究では GP をプラント、外側のベイズ最適化を制御器とみなす閉ループ構造を導入する。提案法の本質は、固定率の置き換えにあるのではなく、探索状態に応じて操作強度と制御周期を同時に切り替える文脈付き制御として GP を定式化する点にある。

### 3.2 閉ループ制御としての定式化

世代 `g` における GP 集団を `P_g` とする。また、外側 BO による制御更新の回数を `\ell` で表す。提案法では、制御ステップ `\ell` において

$$
u_\ell = (p_{c,\ell}, p_{m,\ell}, k_\ell)
$$

を決定し、その値を `k_\ell` 世代の間保持して GP を進化させる。したがって、更新時点の世代番号は

$$
g_{\ell+1} = g_\ell + k_\ell
$$

で与えられる。GP の進化作用全体を `F`、確率的ゆらぎを `\xi_\ell` とすると、制御区間 `\ell` における集団遷移は

$$
P_{g_{\ell+1}} = F(P_{g_\ell}, u_\ell, \xi_\ell)
$$

と表せる。

この定式化では、GP 側は入力 `u_\ell` に対して状態を変化させるプラントとして扱われる。一方、BO 側は、現在の集団状態を観測し、その場面で有効と期待される `u_\ell` を出力する制御器として機能する。

### 3.3 状態ベクトル

外側 BO に渡す状態ベクトルを

$$
x_\ell =
\left[
\tau_\ell,\;
\widetilde{HV}_\ell,\;
\widetilde{\Delta HV}_\ell,\;
D_\ell,\;
\widetilde{L}_\ell,\;
\widetilde{s}_\ell
\right]^\top
$$

とする。ここで、`\tau_\ell` は進化段階、`\widetilde{HV}_\ell` は現在性能、`\widetilde{\Delta HV}_\ell` は直近の改善速度、`D_\ell` は探索多様性、`\widetilde{L}_\ell` は平均木サイズ、`\widetilde{s}_\ell` は停滞長を表す。

各成分は次のように定義する。

$$
\tau_\ell = \frac{g_\ell}{T}
$$

$$
\widetilde{HV}_\ell =
\mathrm{clip}
\left(
\frac{HV_\ell - HV_{\min}}{HV_{\max} - HV_{\min}},
0, 1
\right)
$$

$$
\widetilde{\Delta HV}_\ell =
\mathrm{clip}
\left(
\frac{HV_\ell - HV_{\ell-1}}{\delta_{HV}},
-1, 1
\right)
$$

$$
\widetilde{L}_\ell =
\mathrm{clip}
\left(
\frac{\bar{L}_\ell}{L_{\mathrm{ref}}},
0, 1
\right)
$$

$$
\widetilde{s}_\ell =
\mathrm{clip}
\left(
\frac{s_\ell}{s_{\max}},
0, 1
\right)
$$

多様性 `D_\ell` の第一候補としては構造多様性を用いる。これは交叉・突然変異が直接作用する対象がプログラム木構造であるためである。集団 `P_{g_\ell} = \{T_1,\dots,T_{N_\ell}\}` に対し、構造多様性を

$$
D_\ell
=
1
-
\frac{2}{N_\ell(N_\ell-1)}
\sum_{1 \le i < j \le N_\ell}
Sim_g(T_i,T_j)
$$

と定義する。ここで、2 個体 `T_i` と `T_j` の構造類似度 `Sim_g` は

$$
Sim_g(T_i,T_j)
=
\frac{|M(T_i,T_j)|}{|T_i| + |T_j| - |M(T_i,T_j)|}
$$

で与える。`\lvert M(T_i,T_j)\rvert` は両個体で共有される同型部分木の数である。

この状態ベクトルは、進化段階、性能水準、改善速度、探索性、複雑化、停滞を最小限の次元で同時に表すことを意図している。

### 3.4 行動と制約

本研究の行動は

$$
u_\ell = (p_{c,\ell}, p_{m,\ell}, k_\ell)
$$

である。すなわち、提案法は交叉率と突然変異率に加え、次回更新までの世代数 `k` も制御対象に含める。これにより、状態が安定している場面では更新を粗くし、状態変化が大きい場面では更新を密にする適応制御として手法を説明できる。

行動の探索空間は

$$
\mathcal{U}(x_\ell)
=
\left\{
(p_c,p_m,k)
\mid
p_c \in [p_c^{\min}, p_c^{\max}],
\;
p_m \in [p_m^{\min}, p_m^{\max}],
\;
k \in \mathcal{K},
\;
p_c + p_m \le 1
\right\}
$$

とする。ここで `p_c` と `p_m` は連続変数、`k` は有限離散集合 `\mathcal{K}` 上の離散変数として扱う。

### 3.5 報酬関数

BO が最大化する目的は、区間内の進捗を主としつつ、多様性維持を副次的に評価し、過剰な更新頻度を弱く抑制する単一スカラー報酬である。

ただし、`k` を行動に含める以上、単純な区間総 HV 改善量

$$
HV_{\ell+1} - HV_\ell
$$

をそのまま使うと、大きな `k` が有利になりやすい。そこで、進捗主項には世代あたり改善量を用いる。

$$
\Delta HV^{\mathrm{rate}}_\ell
=
\frac{HV_{\ell+1} - HV_\ell}{k_\ell}
$$

$$
\widetilde{\Delta HV}^{\mathrm{rate}}_\ell
=
\mathrm{clip}
\left(
\frac{\Delta HV^{\mathrm{rate}}_\ell}{\delta_{HV}^{\mathrm{rate}}},
-1, 1
\right)
$$

多様性項には区間終点の 1 点ではなく、区間平均多様性を用いる。

$$
\bar{D}_\ell
=
\frac{1}{k_\ell}
\sum_{j=1}^{k_\ell}
D_{\ell,j}
$$

多様性は高ければ高いほど良いとは限らないため、世代進行に応じた目標多様性

$$
D^\ast(\tau)
=
D_{\mathrm{start}}
-
(D_{\mathrm{start}} - D_{\mathrm{end}})\tau
$$

を設定し、その整合度を

$$
S_D(\bar{D}_\ell,\tau_{\ell+1})
=
\exp
\left(
-
\left(
\frac{\bar{D}_\ell - D^\ast(\tau_{\ell+1})}{\sigma_D}
\right)^2
\right)
$$

で評価する。

制御更新コスト項は

$$
C_k(k_\ell)
=
\frac{k_{\max} - k_\ell}{k_{\max} - k_{\min}}
$$

とする。`k` が小さいほど頻繁に BO を実行するため、コストは大きくなる。

以上より、最終報酬は

$$
r_\ell
=
w_p \widetilde{\Delta HV}^{\mathrm{rate}}_\ell
+
w_d S_D(\bar{D}_\ell,\tau_{\ell+1})
-
w_c C_k(k_\ell)
$$

とする。ここで `w_p > w_d > w_c` を基本方針とし、本研究では性能改善と多様性維持の両立を主張の中心に置く。

### 3.6 文脈付き BO による制御則

制御器は標準的なガウス過程ベースの文脈付き BO とする。入力は状態と行動を連結した

$$
z_\ell = [x_\ell, u_\ell]
$$

であり、履歴データを

$$
\mathcal{D}_n = \{(z_i, r_i)\}_{i=1}^{n}
$$

とする。BO は

$$
r_\ell = f(z_\ell) + \varepsilon_\ell
$$

を学習し、現在状態 `x_\ell` を固定したうえで

$$
u_\ell^\ast
=
\arg\max_{u \in \mathcal{U}(x_\ell)}
\mathrm{EI}(x_\ell, u \mid \mathcal{D}_\ell)
$$

により次行動を選ぶ。

ここで重要なのは、本研究が最適化しているのが

$$
f(p_c,p_m,k)
$$

ではなく、

$$
f(x_\ell,p_c,p_m,k)
$$

である点である。すなわち、同じ行動であっても、現在の探索状態が異なれば良し悪しが変わることを前提にしている。この点が、非文脈 BO との差分の中心である。

また、本研究では `k` を先に選んでから `(p_c,p_m)` を決める階層型ではなく、`(p_c,p_m,k)` を 1 つの行動として混合空間上で同時に最適化する。これにより、提案法は「操作強度と更新周期を同時に切り替える状態依存制御」として定義できる。

### 3.7 アルゴリズム

提案法の処理手順を Algorithm 1 に示す。

1. 初期集団を生成し、`g_0 = 0`、`\ell = 0` とする。
2. 更新時点の集団 `P_{g_\ell}` から状態 `x_\ell` を観測する。
3. warm-up 期間であれば初期設計点から `(p_c,p_m,k)` を選ぶ。
4. それ以降は、BO が `\mathrm{EI}(x_\ell,u)` を最大にする `u_\ell = (p_c,p_m,k)` を選ぶ。
5. `u_\ell` を固定し、GP を `k_\ell` 世代だけ進化させる。
6. 次更新時点の集団 `P_{g_{\ell+1}}` と区間要約統計 `HV_{\ell+1}`, `\Delta HV^{rate}_\ell`, `\bar{D}_\ell`, `C_k(k_\ell)` を得る。
7. 報酬 `r_\ell` を計算し、`(x_\ell,u_\ell,r_\ell)` を履歴へ追加する。
8. 終了条件を満たすまで `\ell \leftarrow \ell + 1` として繰り返す。

以上により、提案法は GP の進化状態を観測しながら、操作率と制御周期を逐次調整する状態依存・閉ループ制御として実現される。
