# Contextual Gaussian Process Bandit Optimization

- Reference ID: [R12]
- Classification: A: 中核 / B: 設計根拠
- Authors: Andreas Krause, Cheng S. Ong
- Year: 2011
- Venue: Advances in Neural Information Processing Systems 24 (NIPS 2011)
- Official page: https://papers.nips.cc/paper/2011/hash/f3f1b7fc5a8779a9e618e1f23a7b7860-Abstract.html
- Paper PDF: https://papers.nips.cc/paper_files/paper/2011/file/f3f1b7fc5a8779a9e618e1f23a7b7860-Paper.pdf
- Access date: 2026-04-28
- Full-text status: 公式 NeurIPS ページおよび PDF で本文確認可能

## 概要

文脈付き bandit 問題として、各ラウンドで文脈を観測し、その文脈の下で行動を選ぶ問題を扱う。報酬関数を文脈と行動の結合空間上の Gaussian Process としてモデル化し、探索と活用を両立するアルゴリズムを提案している。

## 本研究での使い道

- 文脈付き BO を採用する理論的根拠。
- `x_ell` を観測してから `u_ell = (p_c,p_m,k)` を選ぶ、という状態条件付き制御の説明に使う。
- `f(x_ell,p_c,p_m,k)` を学習対象とし、非文脈 BO の `f(p_c,p_m,k)` と区別する根拠に使う。

## 参照した設計判断

- BO 制御器を、現在状態 `x_ell` を条件に行動を選択する文脈付き最適化として定義する。
- 文脈と行動の結合特徴 `z = [x,u]` を surrogate の入力とする。
- 非文脈 BO baseline との差分を「状態を条件に含めるかどうか」に置く。

## メモ

NeurIPS 公式ページでは、文脈を受け取り、行動を選び、文脈-行動空間上の平均 payoff を推定する問題設定が説明されている。本研究では獲得関数を UCB ではなく EI とするが、文脈付き BO という問題設定の根拠として参照する。
