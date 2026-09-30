# Efficient Global Optimization of Expensive Black-Box Functions

- Reference ID: [R13]
- Classification: A: 中核 / B: 設計根拠
- Authors: Donald R. Jones, Matthias Schonlau, William J. Welch
- Year: 1998
- Journal: Journal of Global Optimization
- Volume / Issue / Pages: 13(4), 455-492
- DOI: https://doi.org/10.1023/A:1008306431147
- CiNii: https://cir.nii.ac.jp/crid/1360292620670470656
- UBC metadata: https://r7-www1.stat.ubc.ca/efficient-global-optimization-expensive-black-box-functions
- Access date: 2026-04-28
- Full-text status: PDF saved locally and body text checked on 2026-06-08.
- Local PDF: references/Efficient Global Optimization of Expensive Black-Box Functions.pdf

## 概要

評価回数が限られる高コストな black-box 関数最適化に対し、応答曲面モデルを用いた Efficient Global Optimization (EGO) を提示した古典的文献である。Expected Improvement (EI) を用いた逐次的な評価点選択の根拠として広く参照される。

## 本研究での使い道

- BO 制御器の獲得関数を EI とする根拠。
- GP の各制御区間を高コストな 1 評価として扱い、少ない観測から次の行動を選ぶ設計の根拠。
- `EI_k(x_ell,p_c,p_m)` を最大化して次行動を選ぶ説明に使う。

## 参照した設計判断

- 初稿の獲得関数は EI に固定する。
- UCB / Thompson Sampling / entropy search などの比較は初稿では扱わず、BO 制御器の基本形を明確にする。
- GP を `k` 世代走らせて得られる区間報酬を expensive black-box evaluation とみなす。
- 初期設計点を space-filling design / Latin hypercube design として用意し、その後に surrogate と EI に基づいて逐次評価点を選ぶ説明の根拠にする。

## メモ

CiNii では DOI、Journal of Global Optimization 13(4), 455-492, 1998、および Springer PDF / fulltext リンクが確認できる。2026-06-08 に添付 PDF の本文を確認し、expected improvement、EI の閉形式、EGO algorithm、space-filling / Latin hypercube design による初期点生成の記述を確認した。BO の古典的根拠として、提案手法の獲得関数説明に利用する。
