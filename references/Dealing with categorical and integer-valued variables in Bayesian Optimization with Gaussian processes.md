# Dealing with categorical and integer-valued variables in Bayesian Optimization with Gaussian processes

- Reference ID: [R14]
- Classification: B: 設計根拠 / C: 比較対象
- Authors: Eduardo C. Garrido-Merchan, Daniel Hernandez-Lobato
- Year: 2020
- Journal: Neurocomputing
- Volume / Pages: 380, 20-35
- DOI: https://doi.org/10.1016/j.neucom.2019.11.004
- ScienceDirect: https://www.sciencedirect.com/science/article/pii/S0925231219315619
- CiNii: https://cir.nii.ac.jp/crid/1360865818715879936
- Access date: 2026-04-28
- Full-text status: PDF saved locally and body text checked on 2026-06-08.
- Local PDF: references/Dealing with categorical and integer-valued variables in Bayesian Optimization with Gaussian processes.pdf

## 概要

GP ベースの BO が本来は実数値入力を仮定するため、カテゴリ変数や整数変数を含む最適化では単純な丸めや one-hot encoding が不適切な挙動を生みうることを指摘し、離散・整数変数を扱うための共分散関数変換を提案している。

## 本研究での使い道

- 更新周期 `k` を連続実数として単純に surrogate へ入れない理由。
- `k` を有限離散集合として扱い、各 `k` に条件づけて `(p_c,p_m)` の EI を評価する設計の根拠。
- 将来、単一 surrogate で `k` を扱う場合には、離散変数用のカーネルや変換を検討すべきことの根拠。
- 現在の `k` ごとの surrogate 設計は、この論文が提案する変換そのものではないが、「離散・整数変数を連続変数と同じように扱うべきではない」という設計判断の根拠として使う。

## 参照した設計判断

- 初稿では `k` を数値特徴として 1 本の GP に押し込まず、`k` ごとに条件付き surrogate を持つ。
- `k` は `K = {k^(1), ..., k^(M)}` の有限集合から列挙する。
- 混合空間 BO の高度なカーネル設計は将来拡張として扱い、V1 では実装容易性と説明可能性を優先する。

## メモ

ScienceDirect では、GP が実数値入力を仮定するためカテゴリ・整数値変数を直接扱いにくいこと、単純な丸めや one-hot encoding が suboptimal になりうることが述べられている。2026-06-08 に添付 PDF の本文を確認し、整数値変数では acquisition 最適化後の単純丸め、カテゴリ変数では one-hot encoding が問題を生みうること、また離散値を考慮した変換を covariance / kernel 側に反映する必要があることを確認した。本研究ではこの問題を避けるため、更新周期 `k` を連続入力として単純に扱わず、離散列挙し、各 `k` ごとに条件付きに BO を行う設計を採る。
